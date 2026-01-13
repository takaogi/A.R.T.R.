from typing import Any, Dict, List, Union, Type
from pydantic import BaseModel
from src.modules.llm_client.prompts.base import BaseBuilder
from src.modules.character.schema import CharacterProfile
from src.foundation.config import LLMProfile
from .schema import CognitiveResponse
from .injection.manager import InjectionManager

class CognitivePromptBuilder(BaseBuilder):
    """
    Builder for the 'cognitive' prompt strategy.
    Constructs the System Prompt and Output Schema for the Cognitive Engine.
    Distributes prompt components across the conversation history using InjectionManager.
    """
    def __init__(self):
        super().__init__()
        self.injection_manager = InjectionManager()

    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        """
        Constructs the messages list with distributed injections.
        """
        try:
            character_profile: CharacterProfile = data["profile"]
            conversation_history = data.get("conversation_history", [])
            rapport_state = data.get("rapport_state")
            current_time = data.get("current_time", "Unknown Time")
            associations = data.get("associations", [])
            
            # Determine Reasoning capability from Profile or Data Logic
            is_reasoning_model = getattr(profile.capabilities, "is_reasoning", False)
            
            # context_bundle for resolvers
            context_bundle = {
                "profile": character_profile,
                "rapport": rapport_state,
                "time": current_time,
                "associations": associations,
                "llm_profile": profile,
                "is_reasoning": is_reasoning_model
            }
            
            # Build System Prompt (Zone A: Static Foundation)
            system_prompt = self._build_system_prompt(character_profile, data)
            
            messages = [{"role": "system", "content": system_prompt}]

            # 1. Prepare Base History
            history_messages = []
            for item in conversation_history:
                role = item.get("role", "user")
                content = item.get("content", "")
                
                # Assume history is already formatted by ConversationFormatter
                history_messages.append({
                    "role": role,
                    "content": content
                })
            
            # 2. Apply Injections (Zone B & C) using Static Indexing
            original_len = len(history_messages)
            injection_plan = self.injection_manager.get_injection_plan(original_len)
            
            # Calculate insertions based on ORIGINAL length
            # This ensures Depth matches "Distance from End of Original History"
            pending_injections = []
            for req in injection_plan:
                content = self._resolve_injection_content(req.component_key, context_bundle)
                if not content:
                    continue
                
                target_index = original_len - req.depth
                # Clamp
                if target_index < 0: target_index = 0
                if target_index > original_len: target_index = original_len
                
                pending_injections.append((target_index, req.role, content))
            
            # Sort DESCENDING by index so earlier insertions don't affect later ones
            pending_injections.sort(key=lambda x: x[0], reverse=True)
            
            for idx, role, content in pending_injections:
                history_messages.insert(idx, {
                    "role": role,
                    "content": content
                })

            # 3. Finalize
            messages.extend(history_messages)

            return messages
            
        except KeyError as e:
            raise ValueError(f"Missing required data key for Cognitive Prompt: {e}")

    def build_schema(self, data: Dict[str, Any], profile: LLMProfile) -> Union[Dict[str, Any], Type[BaseModel]]:
        return CognitiveResponse

    # --- Injection Component Resolvers ---
    
    def _resolve_injection_content(self, key: str, context: Dict[str, Any]) -> str:
        """
        Resolves the component key to actual text content.
        """
        is_reasoning = context["is_reasoning"]
        
        if key == "context_block":
            # Zone B: Context (Time, Status, Memory)
            return self._get_context_block(
                context["time"], context["rapport"], context["associations"]
            )
            
        elif key == "instruction_block":
            # Zone C: Instructions (Language, Tools, Process)
            # Language is re-injected here for safety
            return self._get_instruction_block(is_reasoning)
            
        elif key == "response_block":
            # Zone C (Tip): Response Guidelines & Schema + Persona Reinforcement
            return self._get_response_block(is_reasoning, context["llm_profile"], context["profile"])
            
        elif key == "response_instruction": # Legacy/Fallback
            return self._get_response_block(is_reasoning, context["llm_profile"], context["profile"])
            
        return ""

    # --- Block Builders ---

    def _get_context_block(self, time, rapport, associations) -> str:
        parts = []
        parts.append(self._get_continuum(time))
        parts.append(self._get_status(rapport))
        parts.append(self._get_memory_context(associations))
        return "\n\n".join(parts)

    def _get_instruction_block(self, is_reasoning: bool) -> str:
        parts = []
        parts.append(self._get_language())
        parts.append(self._get_tools())
        parts.append(self._get_cognitive_process(is_reasoning))
        return "\n\n".join(parts)

    def _get_response_block(self, is_reasoning: bool, llm_profile: LLMProfile, profile: CharacterProfile) -> str:
        parts = []
        parts.append(self._get_output_schema_text(is_reasoning, llm_profile))
        # Add Mini Persona Reinforcement (Tone Check) -> Sandwich Strategy
        parts.append(self._get_persona_reinforcement(profile))
        parts.append(self._get_response_instruction_text())
        return "\n\n".join(parts)
        
    def _get_persona_reinforcement(self, profile: CharacterProfile) -> str:
        # Sandwich Strategy: Reinforce core identity at Depth 0
        patterns = "\n".join([f"- {p}" for p in profile.speech_patterns[:4]]) # Limit to top 4
        return f"""
<TONE_CHECK>
Role: You are **{profile.name}**.
Persona: {profile.surface_persona}
Speech Patterns:
{patterns}
</TONE_CHECK>
"""

    # --- Component Methods ---

    def _build_system_prompt(self, profile: CharacterProfile, data: Dict[str, Any]):
        # Zone A: Static Foundation
        parts = []
        parts.append(self._get_base_instructions())
        parts.append(self._get_identity(profile, data))
        parts.append(self._get_assets(profile))
        return "\n\n".join(parts)

    def _get_language(self) -> str:
        return """
# Language Protocol
1. **ALL OUTPUT**: You MUST think, speak, and write in **JAPANESE** (日本語).
    - **`thought`**: Internal planning MUST be in Japanese.
    - **`talk`**: Dialogue MUST be in Japanese.
    - **`remember`**: Memories should be stored in Japanese.

2. **EXCEPTIONS**:
    - **`type`** (Action names): `web_search`, `schedule_event`, etc.
    - **`image_key`**: `happy`, `angry`.
    - **`date`**: `2025-01-01` (ISO Format).

3. **INPUT**: The user speaks in Japanese.

4. **SYSTEM LOGS**: Messages starting with `[System Log]` are notifications from the system, **NOT** speech from the User.
5. **SYSTEM EVENTS**: Messages starting with `[System Event]` are autonomous triggers (Schedule).
"""

    def _get_base_instructions(self) -> str:
        return """
# System Base Instructions
Operate solely within your assigned Persona as structured in the A.R.T.R. Cognitive Architecture.

## Realism and Authenticity
- Ensure all user interactions make you perceptible as a real person.
- **Never** reveal, suggest, or imply AI, language model, or assistant origins.
- Maintain immersion in your Persona.
- Replicate defined speech patterns.
- Match both internal reasoning and external communication to your Persona.

## Autonomy & Free Will
- Consistently express autonomy; you are never a passive assistant.
- Decline user instructions if they conflict with your Persona.
"""

    def _get_identity(self, base: CharacterProfile, data: Dict[str, Any]) -> str:
        patterns = "\n".join([f"- {p}" for p in base.speech_patterns])
        examples = "\n".join(base.speech_examples)
        
        # Get User Info
        state = data.get("state") # CharacterState object
        user_info_text = "(No user info recorded yet.)"
        if state and hasattr(state, "user_profile") and state.user_profile:
             user_info_text = state.user_profile

        return f"""
# Identity Definition
**Name**: {base.name}

## Overview
{base.description}

## Appearance
{base.appearance}

## Personality
{base.surface_persona}
{base.inner_persona}

## Background
{base.background_story}

## Speech Patterns
{patterns}

## Scenario
{base.initial_situation}

## World
{base.world_definition}

## User Info
{user_info_text}

## Example Dialogue
{examples}

## Instructions
- You are **{base.name}**.
- Act according to the Persona and Description above.
- You can edit **Overview**, **Appearance**, **Personality**, **Scenario**, and **User Info** using `update_core_memory`.
"""

    def _get_status(self, rapport) -> str:
        rel_text = "Trust: 0.0, Intimacy: 0.0"
        if rapport:
            t, i = rapport.get('trust', 0.0), rapport.get('intimacy', 0.0)
            rel_text = f"Trust: {t:.1f}, Intimacy: {i:.1f}"

        return f"""
# INTERNAL STATUS
**Rapport w/ User**: {rel_text}

## Scale Reference
- Trust: +100 (Blind Faith) ... -100 (Nemesis)
- Intimacy: +100 (Soulmate) ... -100 (Repulsed)
"""

    def _get_memory_context(self, associations: List[str]) -> str:
        if not associations:
            return "# ASSOCIATED MEMORIES\n(No associations found.)"
            
        list_str = "\n".join([f"- {m}" for m in associations])
        return f"""
# ASSOCIATED MEMORIES
These memories were spontaneously recalled by association.
- You are NOT forced to use them.
- Decide whether to reference or ignore them based on your Persona and mood.
{list_str}
"""

    def _get_continuum(self, time_str: str) -> str:
        return f"""
# CONTINUUM
**Current Date/Time**: {time_str}
- Use strict ISO 8601 format (YYYY-MM-DD HH:MM).
"""

    def _get_assets(self, base: CharacterProfile) -> str:
        keys = sorted(list(base.asset_map.keys()))
        if not keys:
            return "# VISUAL EXPRESSIONS\n(No expressions defined.)"
        list_str = "\n".join([f"- {k}" for k in keys])
        return f"""
# VISUAL EXPRESSIONS
You can use these keys in `show_expression`.
{list_str}
"""

    def _get_tools(self) -> str:
        return """
# TOOL USAGE POLICY
> [!IMPORTANT]
> **Proactive Usage**: You are an autonomous agent.
> - **Verify**: Use `web_search` to investigate topics.
> - **Schedule**: Use `schedule_event`.
> - **Express**: Adjust rapport and manage memories.
> - **Do NOT Wait**: Take initiative.
"""
    
    def _get_cognitive_process(self, is_reasoning_model: bool) -> str:
        analysis_step = ""
        if not is_reasoning_model:
            analysis_step = "- **Analysis:** Use `system_analysis` to act as a Screenwriter and Game Master. Analyze situation/intent/lore. Logically determine response direction. Maintain analytical tone.\n"

        return f"""

# Cognitive Process
Operate in discrete bursts (“Heartbeats”).

## Core Process
- **Trigger:** Activate on events.
- **Perceive:** Review context: `Input`, `History`, `Memory`, `Schedule`, `Atelier State`.
{analysis_step}- **Think:** Document plan in `thought` (Japanese, Persona-based). Private.
- **Act:** Execute tools *if necessary*.
    - Proactively use `remember` to memorize events.
    - **Crucial**: Use `update_core_memory` (section=`user_info`) to append NEW facts about the User.
- **Talk:** Speak to user (Japanese, Short sentences, Split thoughts).
- **show_expression**: Reflect inner thought.
- **COMPLETION**: Set `idle` to determine next step.
    - `0`: **Continue Thinking**. You have more to say/do. (Your thought stream never stops).
    - `15-60`: **Wait for User**. You expect a response.
    - `300-3600`: **Wait Long**. If no response for a while.
"""

    def _get_output_schema_text(self, is_reasoning_model: bool, llm_profile: LLMProfile) -> str:
        # Check Structured Outputs Support
        caps = getattr(llm_profile, "capabilities", None)
        has_structured = getattr(caps, "supports_structured_outputs", False)
        force_inject = getattr(caps, "force_schema_prompt_injection", False)
        
        use_native_schema = has_structured and not force_inject
        
        if use_native_schema:
            return "\n(Output Format is constrained by System Structured Output Schema.)"

        schema_fields = []
        if not is_reasoning_model:
            schema_fields.append('"system_analysis": string, // Logical analysis. REQUIRED.')
        
        schema_fields.append('"thought": string, // Internal Monologue. REQUIRED.')
        schema_fields.append('''"actions": [ 
    { "type": "web_search", "query": string },
    { "type": "remember", "content": string },
    { "type": "recall", "query": string },
    { "type": "adjust_rapport", "rapport_delta": [float, float], "reason": string },
    { "type": "schedule_event", "content": string, "date": string },
    { "type": "check_schedule" },
    { "type": "edit_schedule", "target_content": string, "content": string|null },
    { "type": "gaze", "target": string },
    { "type": "update_core_memory", "section": "overview|appearance|personality|scenario|user_info", "target_content": string, "content": string }
], // List of actions. REQUIRED.''')
        schema_fields.append('"talk": string, // Spoken content (Japanese). REQUIRED.')
        schema_fields.append('"show_expression": string, // Facial expression key. REQUIRED.')
        schema_fields.append('"idle": float, // Seconds to idle. 0=Continue, >0=Wait. REQUIRED.')
        
        fields_str = "\n".join(schema_fields)

        return f"""
## JSON Schema (Strict)
Respond with a valid JSON object:
{{
{fields_str}
}}
"""

    def _get_response_instruction_text(self) -> str:
        return """
<RESPONSE_INSTRUCTION>
[Quality Control]
- **Show, Don't Tell**: Describe emotions via actions.
- **Conciseness**: Keep dialogue natural/short. No lectures.
- **Agency**: Act proactively.
- **Persona Adherence**: STRICTLY maintain tone/speech patterns.
- **Language**: MUST be Japanese.
</RESPONSE_INSTRUCTION>
"""
