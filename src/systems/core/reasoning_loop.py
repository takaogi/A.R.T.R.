import json
import asyncio
from typing import List, Dict, Any, Optional
from src.utils.logger import logger
from src.utils.llm_client import LLMClient
from src.config import settings
from src.systems.core.prompt_builder import PromptBuilder
from src.systems.core.tools.dispatcher import ToolDispatcher
from src.systems.core.tools.schemas import CoreResponse, ActionSendMessage

class ReasoningLoop:
    """
    Manages the recursive thinking process of the Core Layer.
    Executes the OODA loop: Observe (Prompt) -> Orient/Decide (LLM) -> Act (Tools).
    """
    
    MAX_STEPS = 10  # Safety limit for recursion
    
    def __init__(self, 
                 dispatcher: ToolDispatcher,
                 prompt_builder: PromptBuilder,
                 model_name: str = None):
        self.dispatcher = dispatcher
        self.prompt_builder = prompt_builder
        self.model_name = model_name or settings.OPENAI_MODEL_CORE

    async def execute(self, 
                      user_input: str, 
                      conversation_manager: Any, # Avoid type hint circular dependency if any
                      pre_process_data: Dict, 
                      associated_memories: List[Dict]) -> List[str]:
        """
        Runs the thinking loop.
        Returns a list of assistant responses (content_en) generated during the loop.
        """
        
        # 1. Build Initial Prompts
        system_prompt = self.prompt_builder.build_system_prompt()
        user_message_content = self.prompt_builder.build_user_context(
            user_input, conversation_manager, pre_process_data, associated_memories
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content}
        ]
        
        step_count = 0
        assistant_replies = []
        
        while step_count < self.MAX_STEPS:
            step_count += 1
            logger.info(f"--- Thinking Step {step_count} ---")
            
            try:
                # 2. Call LLM
                response_obj: CoreResponse = await LLMClient.request_structured(
                    messages=messages,
                    response_model=CoreResponse,
                    model=self.model_name,
                    # reasoning_effort="medium" # e.g. for o1/o3 models if supported
                )
                
                # Log Internal Monologue
                logger.debug(f"Monologue: {response_obj.internal_monologue}")
                
                # 3. Add Assistant Response to History (as JSON string)
                # We need to serialize it so the model sees what it outputted
                # model_dump_json() is standard Pydantic V2
                response_json = response_obj.model_dump_json()
                messages.append({"role": "assistant", "content": response_json})
                
                # 4. Execute Actions
                heartbeat = True # Default to True unless tools say otherwise (wait_for_user)
                tool_outputs = []
                
                for action in response_obj.actions:
                    # Capture sent messages for return
                    if action.tool_name == "send_message":
                        assistant_replies.append(action.parameters.content_en)
                    
                    # Execute
                    result = await self.dispatcher.dispatch_action(action)
                    
                    # Check Heartbeat
                    if not result.get("heartbeat", True):
                        heartbeat = False
                    
                    # Format Output
                    tool_out = f"Tool '{action.tool_name}' Output: {result.get('result', 'Done')}"
                    tool_outputs.append(tool_out)
                    logger.info(f"Action Executed: {tool_out}")

                # 5. Append Tool Outputs to History
                if tool_outputs:
                    # Combine all tool outputs into one observation message
                    obs_content = "\n".join(tool_outputs)
                    messages.append({"role": "user", "content": f"Observation:\n{obs_content}"})
                
                # 6. Check Loop Termination
                if not heartbeat:
                    logger.info("Heartbeat stopped. Yielding to user.")
                    break
                    
            except Exception as e:
                logger.error(f"Error in Reasoning Loop: {e}")
                # In robust system, maybe retry or yield error?
                # For now, break to avoid infinite error loops
                break
                
        return assistant_replies
