import asyncio
import time
import re
from typing import Optional, Dict, Any, List
from src.foundation.config import ConfigManager
from src.modules.character.schema import CharacterProfile
from src.modules.llm_client.client import LLMClient
from src.modules.cognitive.pacemaker import Pacemaker
from src.modules.memory.ingestor import MemoryIngestor
from src.modules.cognitive.tools.registry import ToolRegistry
from src.modules.llm_client.prompts.cognitive.schema import CognitiveResponse, Action

from src.modules.memory.manager import MemoryManager
from src.modules.character.manager import CharacterStateManager

class CognitiveEngine:
    """
    Core engine that drives the character's cognitive process.
    Manages the 'Heartbeat' loop of Perception -> Analysis -> Action.
    """
    def __init__(self, 
                 llm_client: LLMClient, 
                 tool_registry: ToolRegistry,
                 profile: CharacterProfile,
                 config_manager: ConfigManager,
                 memory_manager: MemoryManager,
                 character_manager: CharacterStateManager):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.profile = profile
        self.config = config_manager
        
        # Components
        self.memory_manager = memory_manager
        self.state_manager = character_manager
        
        # Echo Ingestor
        self.ingestor = MemoryIngestor(self.memory_manager, self.llm_client)
        
        # Inject Manager into Tools (Specifically AdjustRapport)
        rapport_tool = self.tool_registry.get_tool("adjust_rapport")
        if rapport_tool:
            # Check if tool has set_manager method (It should if it's AdjustRapportTool)
            if hasattr(rapport_tool, "set_manager"):
                rapport_tool.set_manager(self.state_manager)
            else:
                 print(f"[Engine] Warning: adjust_rapport tool does not accept state manager.")
        
        # Inject MemoryManager into Memory Tools
        for tool_name in ["remember", "recall"]:
            mem_tool = self.tool_registry.get_tool(tool_name)
            if mem_tool:
                if hasattr(mem_tool, "set_memory"):
                    mem_tool.set_memory(self.memory_manager)

        # Inject Dependencies into Knowledge Tools (WebSearch)
        search_tool = self.tool_registry.get_tool("web_search")
        if search_tool:
            if hasattr(search_tool, "set_config"):
                search_tool.set_config(self.config)
            if hasattr(search_tool, "set_llm_client"):
                search_tool.set_llm_client(self.llm_client)

        # Inject Manager into Schedule Tools AND Core Memory Tool
        for tool_name in ["schedule_event", "check_schedule", "edit_schedule", "update_core_memory"]:
            tool = self.tool_registry.get_tool(tool_name)
            if tool and hasattr(tool, "set_manager"):
                tool.set_manager(self.state_manager)

        self.running = False
        self._current_task: Optional[asyncio.Task] = None
        self._wakeup_task: Optional[asyncio.Task] = None
        self.last_user_input_time: float = 0.0

    # --- Public API for Triggers ---

    async def start_user_turn(self, user_input: str):
        """
        Public API: Called when User sends input.
        1. Interrupts current thinking (if any).
        2. Logs input.
        3. Starts new cognitive cycle.
        """
        # 1. Update Association Buffer (Semantic)
        self.memory_manager.update_associations(user_input, mode='input')
        self.last_user_input_time = time.time()

        # 2. Cancel current task
        if self._current_task and not self._current_task.done():
            print(f"[Engine] Interrupting current thought for User Input.")
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass
        
        # 3. Cancel Wakeup Task (User input supersedes wait)
        if self._wakeup_task and not self._wakeup_task.done():
            self._wakeup_task.cancel()
            
        # 3. Add to Memory
        self.memory_manager.add_interaction("user", user_input)
        
        # 4. Start new loop
        self._current_task = asyncio.create_task(self._run_cognitive_loop(trigger="user_input"))
        await self._current_task 

    async def trigger_system_event(self, event_text: str, wait_duration: float = 0.0, log_to_memory: bool = True):
        """
        Public API: Called by Pacemaker or System.
        1. Logs event ([System Event]) - OPTIONAL via log_to_memory.
        2. IF Idle: Starts cognitive cycle.
        3. IF Thinking: Do NOTHING (Input is queued in history).
        """
        # 1. Update Association Buffer (Random - Pacemaker)
        # Only if trigger is pacemaker related? Text usually contains "[System Event]"
        self.memory_manager.update_associations(event_text, mode='random')

        # 2. Add to Memory (System Log)
        if log_to_memory:
            # Check if event_text already starts with [System Event] or [System Log] to avoid double prefixing in some viewers
            # MemoryManager.add_heartbeat_event likely adds role='heartbeat' which formatter handles.
            # So we just pass the text.
            self.memory_manager.add_heartbeat_event(event_text)

        # 3. Check if we should interrupt or ignore
        if self._current_task and not self._current_task.done():
            print(f"[Engine] System Event received during thought. Queued in history.")
            return # Don't interrupt. Next cycle will see it.
            
        # 3b. Cancel Wakeup Task (System Event supersedes IDLE wait)
        if self._wakeup_task and not self._wakeup_task.done():
            self._wakeup_task.cancel()
        
        # 4. Start Cycle
        # 4. Start Cycle
        print(f"[Engine] System Event triggering wake-up.")
        
        # If log_to_memory is True, the event is in history -> Pass 0.0 to loop to suppress duplicate "Time passed" ephemeral.
        # If log_to_memory is False (Ephemeral Only), pass duration -> Loop generates "X seconds passed" ephemeral.
        loop_wait_duration = wait_duration if not log_to_memory else 0.0
        
        self._current_task = asyncio.create_task(self._run_cognitive_loop(trigger="system_event", last_wait_duration=loop_wait_duration))

    # --- Internal Logic ---

    async def _run_cognitive_loop(self, trigger: str = "internal", last_wait_duration: float = 0.0):
        """
        Executes the cognitive cycle repeatedly until Idle > 0 or Limit reached.
        """
        loop_count = 0
        state = self.state_manager.get_state()
        max_loops = state.pacemaker.auto_max_consecutive # Default 50
        
        last_actions_taken = True 
        
        while True:
            # Check Limit (0 = Unlimited)
            if max_loops > 0 and loop_count >= max_loops:
                print(f"[Engine] Max consecutive loops ({max_loops}) reached. Forcing wait.")
                self._schedule_wakeup(300.0) # Force long wait
                break
            
            # Prepare Ephemeral Messages
            ephemeral_messages: List[Dict[str, Any]] = []
            if loop_count == 0:
                # First loop: Check previous wait duration
                
                # Calculate total silence
                total_silence = 0.0
                if self.last_user_input_time > 0:
                    total_silence = time.time() - self.last_user_input_time
                
                silence_info = f"(Total {total_silence:.1f}s since last User Input)"
                
                # Guidance Logic based on Silence
                guidance_msg = ""
                
                # Rules: (Threshold Seconds, Message) - Checked in descending order
                guidance_rules = [
                    (300, "[System Guidance]: It has been over 5 minutes since the last user interaction. You should consider reducing your activity frequency (e.g. Wait Long)."),
                    (60,  "[System Guidance]: It has been over 1 minute since the last user interaction. You should prioritize your own interests, hobbies, or autonomous goals instead of waiting for the user.")
                ]
                
                for threshold, msg in sorted(guidance_rules, key=lambda x: x[0], reverse=True):
                    if total_silence > threshold:
                        guidance_msg = msg
                        break

                if trigger == "user_input":
                    # User spoke. No need for system prompt guidance.
                    pass
                if last_wait_duration <= 10.0:
                    # Short wait or immediate -> Continue
                    # User Request: Delete "Continue thinking" message ("Delete existence")
                    pass 
                else:
                    # Long wait -> Report time passed
                    # User Request: Prioritize Total Time
                    content = f"[System]: User has been silent for {total_silence:.1f} seconds. (Last wait: {last_wait_duration}s)"
                    if guidance_msg:
                        content += f" {guidance_msg}"
                    ephemeral_messages.append({"role": "user", "content": content})
            else:
                # Subsequent loops (Idle=0)
                # User Request: "Do not insert 'Continue thinking' every time."
                # Removed the spammy message. The cycle itself is enough.
                pass

            # Execute Step
            result = await self._execute_cognitive_cycle(ephemeral_messages=ephemeral_messages)
            
            loop_count += 1
            response: CognitiveResponse = result.get("response")

            if not response:
                print("[Engine] Cycle returned no response (Error or Empty). Stopping loop.")
                break
            
            if response.talk:
                print(f"[Engine] Response Talk: {response.talk}")
            print(f"[Engine] Response Idle: {response.idle}")

            # Handle Idle
            if response.idle == 0:
                # Continue Immediately
                last_wait_duration = 0.0 # Reset for next loop check
                continue
            else:
                # Wait
                print(f"[Engine] Idle requested: {response.idle}s")
                self._schedule_wakeup(response.idle)
                break

    async def _execute_cognitive_cycle(self, ephemeral_messages: List[Dict[str, Any]] = None):
        """
        Internal: Executes a single cognitive step (Perceive -> Think -> Act).
        Trigger input is already in History.
        ephemeral_messages: Optional list of messages to inject into context ONLY for this turn.
        """
        # No arguments needed, fetches from History
        
        # 1. History is already updated by trigger methods

        # 2. Build Context
        context_data = self._build_context_data(ephemeral_messages)

        # 3. LLM Execution (Cognitive Process)
        # We pass 'cognitive' as the prompt name to verify usage of CognitivePromptBuilder
        try:
            # Resolve Profile from Strategy Config
            profile_name = self.config.config.llm_strategies.get("cognitive")
            llm_profile = self.config.config.llm_profiles.get(profile_name) if profile_name else None
            
            if not llm_profile:
                print(f"[Engine] Warning: No profile configured for 'cognitive' strategy. Using router default.")

            result = await self.llm_client.execute(
                prompt_name="cognitive",
                data=context_data,
                override_profile=llm_profile
            )
            
            if not result.success:
                 print(f"[Engine] LLM Client Error: {result.error}")
                 return {"status": "error", "error": result.error}
            
            # Parse Response
            # content is guaranteed to be valid JSON if using Strict Mode Structured Outputs
            try:
                response = CognitiveResponse.model_validate_json(result.data.content)
            except Exception as e:
                print(f"[Engine] JSON Parse Error: {e} \nContent: {result.data.content}")
                return {"status": "error", "error": f"JSON Parse Error: {e}"}

        except Exception as e:
            # Fallback / Error Handling needed here
            print(f"[Engine] Unexpected Error: {e}")
            return {"status": "error", "error": str(e)}

        # 4. State Updates (Internal) - Persist thoughts
        self._log_thought(response.thought)
        if response.system_analysis:
            self._log_analysis(response.system_analysis)
            
        # Update Expression
        if response.show_expression:
            self.state_manager.set_expression(response.show_expression)

        # 5. Execute Action List
        execution_results = []
        should_yield = False
        
        # Tools that should NOT result in a system log entry (Silent Tools)
        SILENT_TOOLS = ["remember", "update_core_memory", "check_schedule", "gaze", "adjust_rapport"]
        # Tools that ALWAYS force Idle=0 (Interactive/Next-Step needed)
        INTERACTIVE_TOOLS = ["web_search", "schedule_event", "edit_schedule"]

        has_interactive_action = False
        tool_outputs = []

        # Execute actions from the 'actions' list
        for action in response.actions:
            # Execute tool
            result = await self.tool_registry.execute(action)
            execution_results.append({"action": action.type, "result": result})
            
            if action.type in INTERACTIVE_TOOLS:
                has_interactive_action = True

            # Determine Logging
            if result.get("status") == "success":
                # For specific tools (WebSearch, Recall), result content is important.
                if action.type not in SILENT_TOOLS:
                    msg = result.get("message") or str(result.get("results"))
                    # If interactive, collect to outputs instead of immediate log?
                    # The user wants "Single System Log" for interactive tools? "あるときは必ず一枠にまとめて"
                    if action.type in INTERACTIVE_TOOLS:
                         tool_outputs.append(f"Action '{action.type}' executed: {msg}")
                    else:
                         self.memory_manager.add_system_event(f"Action '{action.type}' executed: {msg}")
                else:
                    print(f"[Engine] Silent Tool '{action.type}' executed. No log added.")
            else:
                 # Error always logs
                 err = result.get("message") or result.get("error")
                 self.memory_manager.add_system_event(f"Action '{action.type}' failed: {err}")

        # Batch Interactive Outputs
        if tool_outputs:
            combined_msg = "\n".join(tool_outputs)
            self.memory_manager.add_system_event(combined_msg)

        # 6. Process 'Talk' (Mandatory Field)
        if response.talk:
            self.memory_manager.add_interaction("assistant", response.talk)

        # 7. Override Idle for Interactive Actions
        if has_interactive_action:
            print(f"[Engine] Interactive Action detected. Forcing Idle=0.")
            response.idle = 0

        return {
            "status": "success",
            "response": response,
            "results": execution_results
        }

        return {
            "status": "success",
            "response": response,
            "results": execution_results
        }

    def _schedule_wakeup(self, duration: float):
        """Schedules a system event to wake up the engine after duration."""
        async def wakeup():
            await asyncio.sleep(duration)
            # Use log_to_memory=False to ensure "Wait timeout" is ephemeral
            await self.trigger_system_event(f"Wait timeout ({duration}s). Resume thinking.", wait_duration=duration, log_to_memory=False)
        
        self._wakeup_task = asyncio.create_task(wakeup())

    def _build_context_data(self, ephemeral_messages: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Constructs the dictionary expected by CognitivePromptBuilder.
        """
        # Retrieve merged history (This call might be redundant if using formatted_history below, keeping as per existing pattern)
        merged_history = self.memory_manager.get_context_history()
        
        # Get Base History
        history = self.memory_manager.get_formatted_history_for_llm()
        
        # Inject Ephemeral Messages (e.g. System Notifications for this turn only)
        if ephemeral_messages:
            print(f"[Engine] Injecting {len(ephemeral_messages)} ephemeral messages.")
            history.extend(ephemeral_messages)

        # In a real impl, retrieve time and rapport from modules
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        prompt_data = {
            "profile": self.profile,
            "state": self.state_manager.get_state(),
            "time": current_time,
            "conversation_history": history,
            "associations": self.memory_manager.get_association_context() # Inject Associations
        }
        return prompt_data

    def _log_thought(self, text: str):
        # Save to MemoryManager
        self.memory_manager.add_thought(text)

    def _log_analysis(self, text: str):
         # In future, save to Trace Log or separate analysis log
         # For now, maybe just treat as thought or ignore? 
         # User requested separating thought and conversation. Analysis is meta-thought.
         # Let's log it as a thought with a prefix if we want to see it, or keep it separate.
         # For now, I'll NOT add it to the thought stream to keep the inner voice pure.
         pass 
