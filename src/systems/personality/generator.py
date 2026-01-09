from typing import Dict, Any, List
from pydantic import BaseModel, Field
from src.utils.llm_client import LLMClient
from src.config import settings
from src.utils.logger import logger

class PersonalityGenerator:
    """
    Handles LLM prompts to generate derived personality assets from Character Card.
    """
    
    async def generate_all(self, cc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates parallel generation of all assets.
        """
        logger.info("Starting recursive personality generation...")
        
        # Parallel execution could be done here with asyncio.gather
        # For trace clarity, we'll do sequential or simple gather
        
        # 1. Reflex Memory (Japanese, short)
        reflex_memory = await self._generate_reflex(cc_data)
        
        # 2. Core Memory (English+Japanese, XML)
        core_memory = await self._generate_core(cc_data)
        
        # 3. System Params (JSON)
        system_params = await self._generate_params(cc_data)

        # 4. Reaction Styles (JSON)
        reaction_styles = await self._generate_reaction_styles(cc_data)
        
        return {
            "reflex_memory": reflex_memory,
            "core_memory": core_memory,
            "system_params": system_params,
            "reaction_styles": reaction_styles
        }

    def _format_cc(self, cc: Dict) -> str:
        """
        Formats the entire Character Card into a readable YAML-like string for LLM context.
        Excludes technical parameters (system_params, reaction_styles) to keep context focused on personality.
        """
        lines = []
        exclude_keys = {"system_params", "reaction_styles"}
        for k, v in cc.items():
            if k in exclude_keys:
                continue
            if v and isinstance(v, (str, int, float, list)):
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    async def _generate_reflex(self, cc: Dict) -> Dict:
        """
        Generates lightweight context for Reflex Layer (Japanese).
        """
        cc_text = self._format_cc(cc)
        prompt = f"""
Analyze the Character Card data and summarize it for a 'Reflex Layer' (Low-latency, instinctual response system).
Target Language: JAPANESE (Regardless of input language)

Input Data:
{cc_text}

Task:
1. Define the 'Tone' (口調) in 1 short sentence (e.g. "ぶっきらぼうだが、根は優しい").
2. Extract or generate 3-5 'Catchphrases' or typical short reactions.
3. Summarize 'Self-Definition' (私は誰か) in 1 sentence.

Output Format (JSON):
{{
  "tone": "...",
  "self_definition": "...",
  "catchphrases": ["...", "..."]
}}
"""
        class ReflexSchema(BaseModel):
            tone: str
            self_definition: str
            catchphrases: List[str]

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_TRANSLATOR,
                response_model=ReflexSchema,
                reasoning_effort="low"
            )
            return response.model_dump()
        except Exception as e:
            logger.error(f"Reflex Generation failed: {e}")
            return {"tone": "Error", "catchphrases": []}

    async def update_reflex(self, current_data: Dict, old_core: str, new_core: str) -> Dict:
        """
        Partially updates Reflex Memory based on changes in Core Memory.
        """
        prompt = f"""
The Core Memory of the character has changed. Update the Reflex Memory setup to reflect these changes if necessary.
Target Language: JAPANESE

Current Reflex Memory:
{current_data}

Old Core Memory:
{old_core}

New Core Memory:
{new_core}

Task:
Identify changes in the Core Memory (e.g. new relationships, changed personality traits) and update the Reflex Memory fields ONLY if they are affected.
If no relevant change, keep values as is.

Output Format (JSON): same struct as Current Reflex Memory.
"""
        class ReflexSchema(BaseModel):
            tone: str
            self_definition: str
            catchphrases: List[str]

        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_TRANSLATOR,
                response_model=ReflexSchema,
                reasoning_effort="low"
            )
            return response.model_dump()
        except Exception as e:
            logger.error(f"Reflex Update failed: {e}")
            return current_data

    async def _generate_core(self, cc: Dict) -> str:
        """
        Generates heavy context for Core Thinking Layer (English optimized + Japanese nuances).
        Output: XML string.
        """
        cc_text = self._format_cc(cc)
        prompt = f"""
You are the architect of the 'Core Memory' for an advanced AI.
Your task is to convert the Character Card into a structured XML format used for deep reasoning.
The content should be primarily in ENGLISH for optimal reasoning performance, but specific Japanese nuances (names, unique terms, speech patterns) should be preserved or noted in parentheses.

Input Data:
{cc_text}

Output Format (XML):
<core_memory>
  <persona>
    <name>...</name>
    <traits>... (Comma separated characteristics)</traits>
    <motivation>... (What drives this character?)</motivation>
    <speaking_style>... (Detailed analysis of how they speak)</speaking_style>
    <background>... (History and lore)</background>
  </persona>
  <scenario>
    <current_situation>...</current_situation>
    <relationship_with_user>...</relationship_with_user>
  </scenario>
  <directives>
    ... (Any system prompts or behavioral constraints)
  </directives>
</core_memory>

Ensure the XML is valid and contains NO other text.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_text(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                reasoning_effort="medium"
            )
            cleaned = response.replace("```xml", "").replace("```", "").strip()
            return cleaned
        except Exception as e:
            logger.error(f"Core Generation failed: {e}")
            return "<error>Generation Failed</error>"

    async def update_core(self, current_xml: str, old_cc: Dict, new_cc: Dict) -> str:
        """
        Partially updates Core Memory XML based on Character Card changes.
        """
        old_cc_text = self._format_cc(old_cc)
        new_cc_text = self._format_cc(new_cc)
        
        prompt = f"""
The Character Card source data has changed. Update the Core Memory XML to reflect these changes.

Current Core Memory XML:
{current_xml}

Old Character Card:
{old_cc_text}

New Character Card:
{new_cc_text}

Task:
Compare Old and New CC. Identify meaningful changes (e.g. name change, new scenario details).
Update the XML content to match the New CC.
Keep unchanged sections (like detailed personality analysis if unrelated to the change) as close to the original as possible.
Ensure the output is valid XML <core_memory>...</core_memory>.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_text(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                reasoning_effort="medium"
            )
            cleaned = response.replace("```xml", "").replace("```", "").strip()
            return cleaned
        except Exception as e:
            logger.error(f"Core Update failed: {e}")
            return current_xml

    async def _generate_params(self, cc: Dict) -> Dict:
        """
        Derives numerical system parameters from personality.
        Respects existing settings in cc['system_params'] if present.
        """
        from src.schemas.personality import SystemParameterSchema
        
        # Check for existing params
        existing_params = cc.get('system_params', {})
        
        # If fully defined? (Simple heuristic: check if major keys exist)
        if existing_params and "pacemaker" in existing_params and "vad_baseline" in existing_params:
             # We assume if it's there, it's trusted.
             return existing_params

        cc_text = self._format_cc(cc)
        prompt = f"""
Analyze the character's personality and determine the appropriate system configuration values.

Input Personality:
{cc_text}

Existing/Partial Settings (RESPECT THESE VALUES IF PRESENT):
{existing_params}

Rules:
1. Pacemaker (Spontaneity Interval in seconds):
   - Min: 10s, Max: 300s (5 minutes).
   - Base/Standard: 30-60s.
   - Examples:
     - Hyperactive/Anxious: 10-30s.
     - Talkative/Energetic: 30-60s.
     - Normal/Calm: 60-120s.
     - Quiet/Depressed/Passive: 180-300s.
   - Variance: 
     - 0.0 (Mechanical/Exact) to 1.0 (Highly chaotic/random timing).
     - Standard: 0.2 to 0.5.

2. VAD Baseline (Mood State -1.0 to 1.0):
   - Unless specific extreme personality, keep within -0.4 to 0.4.
   - Valence: -1.0 (Sad/Dark) ... 0 ... 1.0 (Happy/Bright)
   - Arousal: -1.0 (Calm/Sleepy) ... 0 ... 1.0 (Excited/Active)
   - Dominance: -1.0 (Submissive) ... 0 ... 1.0 (Dominant)

3. VAD Volatility (Sensitivity 0.1 to 3.0):
   - How easily the mood changes. 1.0 is standard.
   - Keep within 0.5 to 1.5 usually.
   - 0.1: Stone-faced, unmovable.
   - 3.0: Extremely unstable, mood swings.

Output JSON conforming to schema.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                response_model=SystemParameterSchema,
                reasoning_effort="low"
            )
            return response.model_dump()
        except Exception as e:
            logger.error(f"Params Generation failed: {e}")
            # Return safe default matching schema
            return {
                "pacemaker": {"base_interval_sec": 60, "variance": 0.2},
                "vad_baseline": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
                "vad_volatility": {"valence": 1.0, "arousal": 1.0, "dominance": 1.0}
            }

    async def update_params(self, current_data: Dict, old_core: str, new_core: str) -> Dict:
        """
        Partially updates System Params based on Core Memory changes.
        """
        from src.schemas.personality import SystemParameterSchema
        
        prompt = f"""
The Core Memory of the character has changed. Update the System Parameters (Pacemaker, VAD) if the personality or mood baseline implies a change.

Current Params:
{current_data}

Old Core Memory:
{old_core}

New Core Memory:
{new_core}

Task:
Adjust params only if the Core Memory change suggests a shift in spontaneity or base mood/volatility.
Otherwise return current values.

Rules:
1. Pacemaker (Spontaneity Interval in seconds):
   - Min: 10s, Max: 300s (5 minutes).
   - Base/Standard: 30-60s.
   - Examples:
     - Hyperactive/Anxious: 10-30s.
     - Talkative/Energetic: 30-60s.
     - Normal/Calm: 60-120s.
     - Quiet/Depressed/Passive: 180-300s.
   - Variance: 
     - 0.0 (Mechanical/Exact) to 1.0 (Highly chaotic/random timing).
     - Standard: 0.2 to 0.5.

2. VAD Baseline (Mood State -1.0 to 1.0):
   - Unless specific extreme personality, keep within -0.4 to 0.4.
   - Valence: -1.0 (Sad/Dark) ... 0 ... 1.0 (Happy/Bright)
   - Arousal: -1.0 (Calm/Sleepy) ... 0 ... 1.0 (Excited/Active)
   - Dominance: -1.0 (Submissive) ... 0 ... 1.0 (Dominant)

3. VAD Volatility (Sensitivity 0.1 to 3.0):
   - How easily the mood changes. 1.0 is standard.
   - Keep within 0.5 to 1.5 usually.
   - 0.1: Stone-faced, unmovable.
   - 3.0: Extremely unstable, mood swings.

Output JSON conforming to schema.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                response_model=SystemParameterSchema,
                reasoning_effort="low"
            )
            return response.model_dump()
        except Exception as e:
            logger.error(f"Params Update failed: {e}")
            return current_data

    async def _generate_reaction_styles(self, cc: Dict) -> Dict[str, str]:
        """
        Maps each Intent Anchor to a specific reaction style.
        Respects existing styles in cc['reaction_styles'].
        """
        from pydantic import BaseModel, Field
        from src.config.reaction_styles import REACTION_STYLE_DB, get_options_for_anchor
        
        cc_text = self._format_cc(cc)
        existing_styles = cc.get('reaction_styles', {})
        
        unique_anchors = sorted(list(set(v.anchor for v in REACTION_STYLE_DB.values())))

        # If all anchors are present, skip generation
        if all(a in existing_styles for a in unique_anchors):
            return existing_styles

        class ReactionStyleItem(BaseModel):
            anchor: str = Field(..., description="The Anchor Key (e.g., 'agree', 'deny')")
            style: str = Field(..., description="The Selected Style Option")

        class ReactionStyleResponse(BaseModel):
            items: List[ReactionStyleItem] = Field(..., description="List of selected styles for each anchor")

        prompt = f"""
For each Conversation Anchor, select the ONE most appropriate reaction style for the character from the provided options.

Character Context:
{cc_text}

EXISTING SELECTIONS (MUST BE PRESERVED):
{existing_styles}

Task: Choose one option for each anchor. If an anchor is already in EXISTING SELECTIONS, you MUST use that value unless it contradicts available options.
"""
        for anchor in unique_anchors:
            options = get_options_for_anchor(anchor)
            formatted_ops = []
            for op in options:
                desc = REACTION_STYLE_DB[op].description
                formatted_ops.append(f"{op} ({desc})")
            
            prompt += f"\n### {anchor}\nOptions:\n"
            for fop in formatted_ops:
                prompt += f"- {fop}\n"

        prompt += "\nOutput a JSON object containing a list of items, where each item has 'anchor' and 'style'."

        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                response_model=ReactionStyleResponse,
                reasoning_effort="low"
            )
            # Convert List Back to Dict
            generated_map = {item.anchor: item.style for item in response.items}
            
            # Merge with current to be safe (in case LLM misses keys)
            final_map = generated_map
            final_map.update(existing_styles) 
            return final_map
        except Exception as e:
            logger.error(f"Reaction Style Generation failed: {e}")
            return {a: existing_styles.get(a, get_options_for_anchor(a)[0]) for a in unique_anchors}

    async def update_reaction_styles(self, current_data: Dict[str, str], old_core: str, new_core: str) -> Dict[str, str]:
        """
        Partially updates Reaction Styles based on Core Memory changes.
        """
        from pydantic import BaseModel, Field
        from src.config.reaction_styles import REACTION_STYLE_DB, get_options_for_anchor
        
        unique_anchors = sorted(list(set(v.anchor for v in REACTION_STYLE_DB.values())))
        
        class ReactionStyleItem(BaseModel):
            anchor: str
            style: str

        class ReactionStyleResponse(BaseModel):
            items: List[ReactionStyleItem]

        prompt = f"""
The Core Memory has changed. Update the Reaction Styles only if the personality shift requires it.

Current Styles:
{current_data}

Old Core Memory:
{old_core}

New Core Memory:
{new_core}

Task:
Review each anchor. If the new core memory implies a different reaction style is more appropriate, change it. Otherwise keep it.
"""
        # Re-list options (needed for LLM to know what to switch TO)
        for anchor in unique_anchors:
            options = get_options_for_anchor(anchor)
            formatted_ops = []
            for op in options:
                desc = REACTION_STYLE_DB[op].description
                formatted_ops.append(f"{op} ({desc})")
            
            prompt += f"\n### {anchor}\nOptions:\n"
            for fop in formatted_ops:
                prompt += f"- {fop}\n"

        prompt += "\nOutput a JSON object with a list of items (anchor, style)."

        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                response_model=ReactionStyleResponse,
                reasoning_effort="low"
            )
            # Merge with current to be safe (in case LLM misses keys)
            updated = current_data.copy()
            generated_map = {item.anchor: item.style for item in response.items}
            updated.update(generated_map)
            return updated
        except Exception as e:
            logger.error(f"Reaction Style Update failed: {e}")
            return current_data


    async def _reverse_generate_cc(self, cc_data: Dict, core_xml: str) -> Dict[str, Any]:
        """
        Reverse-engineers Character Card fields from Core Memory XML.
        Used when the Core Memory has evolved significantly and we want to persist changes back to the source CC.
        """
        from src.schemas.cc_reverse_map import CharacterCardReverseMap
        
        current_desc = cc_data.get("description", "")
        current_scenario = cc_data.get("scenario", "")
        
        prompt = f"""
The Core Memory (XML) representing the character's internal state has evolved.
We need to update the source Character Card (JSON) to match this new internal state.

Current Core Memory XML:
{core_xml}

Old Character Card Description:
{current_desc}

Old Character Card Scenario:
{current_scenario}

Task:
1. Compare the Core Memory with the Old CC fields.
2. If there are significant deviations (e.g. personality growth, relationship changes, scenario progression), GENERATE UPDATED FIELDS.
3. If a field is still accurate, return null/None for that field to preserve exact original text.
4. "description" should summarize persona, traits, and background.
5. "scenario" should summarize the current situation and relationship.

Output JSON conforming to schema.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await LLMClient.request_structured(
                messages=messages,
                model=settings.OPENAI_MODEL_CORE,
                response_model=CharacterCardReverseMap,
                reasoning_effort="medium"
            )
            
            # Construct the update dict, filtering out Nones
            changes = response.model_dump(exclude_none=True)
            return changes
        except Exception as e:
            logger.error(f"Reverse CC Generation failed: {e}")
            return {}
