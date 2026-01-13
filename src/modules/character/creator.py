
from typing import Optional, Dict, Any
from src.foundation.config import ConfigManager
from src.modules.llm_client.client import LLMClient
from src.modules.character.schema import CharacterProfile
from src.foundation.logging import logger

class CharacterCreatorService:
    """
    Backend service for AI-assisted character creation.
    Uses LLM to convert raw text/keywords into a structured CharacterProfile.
    """
    def __init__(self, config_manager: ConfigManager, llm_client: LLMClient):
        self.config_manager = config_manager
        self.llm_client = llm_client

    async def generate_profile(self, prompt_text: Optional[str] = None, 
                             existing_profile: Dict[str, Any] = None, 
                             raw_source: Dict[str, Any] = None,
                             asset_map: Dict[str, str] = None) -> Optional[CharacterProfile]:
        """
        Generates a character profile.
        - refine mode: existing_profile is set.
        - create mode (text): prompt_text is set.
        - create mode (dict): raw_source is set (CharX format).
        - asset_map: Optional map of expressions to inject.
        """
        mode = "refine" if existing_profile else "create"
        if raw_source: mode = "convert"
        
        logger.info(f"[Creator] Generating profile ({mode}).")
        
        # Prepare Data for PromptBuilder
        data = {}
        
        strategy = "character_convert"
        
        if existing_profile and prompt_text:
             strategy = "character_generate"
             data["existing_profile"] = existing_profile
             data["raw_text"] = prompt_text
             
        elif existing_profile:
            strategy = "character_convert"
            data["existing_profile"] = existing_profile
            data["instruction"] = prompt_text or "Optimize and complete."
            
        elif raw_source:
            strategy = "character_convert"
            data["raw_data"] = raw_source
            
        else:
            strategy = "character_generate"
            data["raw_text"] = prompt_text or ""
        
        logger.info(f"[Creator] Strategy: {strategy}, Mode: {mode}")
        
        result = await self.llm_client.execute(strategy, data)
        
        if not result.success:
            logger.error(f"[Creator] Generation failed: {result.error}")
            return None
            
        try:
            profile = CharacterProfile.model_validate_json(result.data.content)
            
            # Inject Asset Map if provided (e.g. from CharX extraction)
            if asset_map:
                profile.asset_map = asset_map
                
            return profile
            
        except Exception as e:
            logger.error(f"[Creator] Parse Error: {e}")
            return None
