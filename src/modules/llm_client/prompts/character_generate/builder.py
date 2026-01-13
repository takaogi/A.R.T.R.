from typing import Any, Dict, List
import json
from src.modules.llm_client.prompts.base import BaseBuilder
from src.modules.llm_client.prompts.character_convert.schema import GeneratedProfile

class CharacterGenerateBuilder(BaseBuilder):
    """
    Prompt Builder for Text-to-Character Generation.
    Supports "Context-Aware Filling": Preserves existing fields if provided.
    """

    def build_messages(self, data: Dict[str, Any], profile: Any) -> List[Dict[str, str]]:
        # 1. Schema Injection
        schema_text = ""
        should_inject = True
        
        if hasattr(profile, 'capabilities'):
            if profile.capabilities.supports_structured_outputs:
                should_inject = False
                if profile.capabilities.force_schema_prompt_injection:
                    should_inject = True
                    
        if should_inject:
            schema_def = GeneratedProfile.model_json_schema()
            fields_desc = []
            for prop, details in schema_def.get('properties', {}).items():
                desc = details.get('description', '').replace('\n', ' ')
                fields_desc.append(f"- **{prop}**: {desc}")
            schema_block = "\n".join(fields_desc)
            schema_text = f"""
        # JSON Output Schema
        You MUST output a valid JSON object matching:
        {schema_block}
            """

        # 2. System Prompt
        system_content = f"""
        You are an expert Character Designer and Creative Writer.
        Your task is to design a unique, detailed, and psychologically consistent character based on the user's request.
        
        # Core Objectives
        1. **Creative Completion**: If the user request is vague (e.g., "A hacker girl"), you MUST invent specific details (Name, Appearance, Backstory) to make the character vivid and unique.
        2. **Psychological Depth**: Explicitly define `surface_persona` (how they act) vs `inner_persona` (what they think).
        3. **Language**: All output must be in **Japanese**.
        4. **Examples**: Generate 3-5 distinct `speech_examples` that perfectly capture their tone.
        
        # Context Awareness (CRITICAL)
        - You may receive a "Fixed Context" JSON.
        - **Rule**: You MUST PRESERVE the values in the Fixed Context. Do not change them.
        - **Goal**: Fill in the MISSING gaps in the Fixed Context to match the preserved values.
        
        {schema_text}
        
        Output JSON only.
        """

        # 3. User Prompt construction
        user_request = data.get("raw_text", "")
        existing_profile = data.get("existing_profile", {})
        
        # Filter empty context
        valid_context = {k: v for k, v in existing_profile.items() if v}
        context_block = ""
        
        if valid_context:
            context_str = json.dumps(valid_context, ensure_ascii=False, indent=2)
            context_block = f"""
        # Fixed Context (DO NOT CHANGE THESE VALUES)
        The user has already defined these fields. You must fill the REST of the profile to match this context.
        ```json
        {context_str}
        ```
            """
        
        user_content = f"""
        # User Request
        {user_request}
        
        {context_block}
        
        Please generate the complete character profile.
        """
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    def build_schema(self, data: Dict[str, Any], profile: Any):
        return GeneratedProfile
