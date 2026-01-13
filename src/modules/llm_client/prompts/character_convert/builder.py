from typing import Any, Dict, List
from src.modules.llm_client.prompts.base import BaseBuilder
from src.modules.llm_client.router import ModelRouter
from src.foundation.types import Result
from .schema import GeneratedProfile

class CharacterConvertBuilder(BaseBuilder):
    """
    Constructs prompt to convert raw character data (RisuAI/TavernAI) into A.R.T.R. GeneratedProfile.
    """
    
    def build_messages(self, data: Dict[str, Any], profile: Any) -> List[Dict[str, str]]:
        # Schema Injection Logic
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
                desc = details.get('description', '')
                desc = desc.replace('\n', ' ')
                fields_desc.append(f"- **{prop}**: {desc}")
            
            schema_block = "\n".join(fields_desc)
            schema_text = f"""
        # JSON Output Schema (Strict Adherence)
        You MUST output a valid JSON object matching the following fields:
        
        {schema_block}
            """

        # --- Refinement Mode ---
        if "existing_profile" in data:
            existing = data["existing_profile"]
            instruction = data.get("instruction", "Optimize and complete the profile.")
            
            system_content = f"""
        You are an expert "Character Data Refiner".
        You will receive an existing A.R.T.R. Profile (JSON) and an instruction.
        
        # Goal
        {instruction}
        
        # Rules
        1. **Respect Existing Data**: Do not overwrite existing fields unless they are empty, generic, or the instruction explicitly asks to change them.
        2. **Fill Missing Gaps**: If a field is empty (or has placeholder logic), generate appropriate content based on the rest of the profile.
        3. **Consistency**: Ensure the new values align with the existing `name` and `personality`.
        4. **Language**: Japanese.
        
        {schema_text}
        
        Output valid JSON only.
            """
            
            user_content = f"""
        # Existing Profile (JSON)
        ```json
        {existing}
        ```
        
        # Instruction
        {instruction}
            """
            
            return [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]

        # --- Legacy Mode (Convert from Raw) ---
        raw = data.get("raw_data", {})
        if "data" in raw and isinstance(raw["data"], dict):
            raw = raw["data"]
        
        def sanitize(text: Any) -> Any:
            if not isinstance(text, str): return text
            text = text.replace("{{user}}", "（ユーザー）")
            text = text.replace("{{User}}", "（ユーザー）")
            return text

        name = raw.get("name", "Unknown")
        desc = sanitize(raw.get("description", "N/A"))
        pers = sanitize(raw.get("personality", "N/A"))
        first = sanitize(raw.get("first_mes", "N/A"))
        example = sanitize(raw.get("mes_example", "N/A"))
        scenario = sanitize(raw.get("scenario", "N/A"))
        
        system_content = f"""
        You are an expert "Character Data Converter".
        Analyze the provided "Raw Character Data (RisuAI format)" holistically and restructure it into an A.R.T.R. Profile (Japanese JSON).

        # Source Data Info
        - **Format**: RisuAI / TavernAI Character Card
        - **Language**: Mixed (English/Japanese/etc.)

        # Conversion Rules (CRITICAL)
        1. **Holistic Optimization & Relocation**:
           - Do not be bound by the original field boundaries.
           - Example: If `description` contains dialogue, move it to `speech_examples`.
           - Example: If `personality` contains visual descriptions, move it to `appearance`.
        
        2. **Overview (Description) Generation**:
           - Create a `description` (Overview) that summarizes the character's core concept, role, and key traits.
           - This serves as the "Creator's Notes" or high-level summary.
           - **Length Target**: up to **~500 Japanese characters**. Can be detailed.

        3. **Summarization & Length Limit**:
           - Summarize text fields (e.g., `background_story`) to **~500 Japanese characters**.
           - Condense long text into dense, information-rich sentences. Use bullet points if effective.
           - Remove redundancy.

        4. **Output Language**:
           - ALL values must be in **Japanese**. Translate if the source is English.

        5. **Multi-dimensional Persona (Outward & Inner)**:
           - Describe the character's personality in two dimensions:
             - `surface_persona`: External expression. How they act, speak, and treat others.
             - `inner_persona`: Internal process. What they think, feel, or desire privately.
           - Treat these as layers of a complex individual, not necessarily conflicting opposites.
           - **Constraint**: Write ONLY what is explicitly stated or clearly inferred from behavior. **Do NOT hallucinate** or invent deep psychological complexes if they are not present in the source.

        6. **Speech Examples extraction**:
           - Extract character quotes from ALL fields into the `speech_examples` list.
           - Remove XML tags, scenario descriptions, or user dialogue. Keep only the character's lines.

        7. **Normalization**:
           - `world_definition`: Summarize world rules/terms.
           - `speech_patterns`: List sentence endings (e.g., "〜だわ") or pronouns (e.g., "Ore").
           
        8. **Ignore Technical Artifacts**:
           - Ignore obviously command-like syntax (e.g. `/toggle`, `[... instruction ...]`, `{{...}}`).
           - Do NOT translate them; simply exclude them unless they are part of the character's explicit dialogue or behavior.
        {schema_text}
        
        Synthesize all information, optimizing for the A.R.T.R. format. Output JSON only.
        """

        user_content = ""
        if "raw_text" in raw:
            # Unstructured Text Mode
            source_text = raw["raw_text"]
            user_content = f"""
        # Raw Source Text
        {source_text}
        
        Please analyze this text and construct a full character profile.
            """
        else:
            # Structured RisuAI Mode
            user_content = f"""
        # Raw Character Data (Source)
        ---
        **Name**: {name}

        **[Description]**
        {desc}

        **[Personality]**
        {pers}

        **[Scenario]**
        {scenario}

        **[First Message]**
        {first}

        **[Dialogue Examples (mes_example)]**
        {example}
        ---

        Please convert and optimize this raw data into the definition of A.R.T.R. format.
            """
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

    def build_schema(self, data: Dict[str, Any], profile: Any):
        return GeneratedProfile
