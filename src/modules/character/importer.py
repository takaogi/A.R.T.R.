import json
from typing import Dict, Any
from src.foundation.logging import logger
from src.foundation.types import Result
from src.modules.llm_client.client import LLMClient
from src.modules.llm_client.prompts.character_convert.schema import GeneratedProfile
from src.modules.character.schema import CharacterProfile

class CharacterImporter:
    """
    Service to convert raw character data into A.R.T.R. CharacterProfile using LLM.
    Uses 'character_convert' prompt to sanitize and structure the data.
    """
    def __init__(self):
        self.llm = LLMClient()

    async def import_from_file(self, file_path: str, override_profile: Any = None) -> Result[CharacterProfile]:
        """
        Full workflow:
        1. Load/Extract raw data from file (.charx, .json, .png)
        2. Convert via LLM
        3. Save/Persist to Character Storage
        """
        from pathlib import Path
        from src.modules.character.loader import CharXLoader
        
        path_obj = Path(file_path)
        loader = CharXLoader()
        
        # 1. Load Raw
        # Supports .charx primarily for now
        if path_obj.suffix == '.charx':
            res_load = loader.load_raw(path_obj)
        else:
            return Result.fail(f"Unsupported file format: {path_obj.suffix}")
            
        if not res_load.success:
            return Result.fail(res_load.error)
            
        params = res_load.data
        raw_json = params['raw_json']
        # character_root = params['character_root'] # Path where assets are
        
        # 2. Convert
        res_convert = await self.generate_profile(raw_json, override_profile=override_profile)
        if not res_convert.success:
            return Result.fail(res_convert.error)
            
        profile = res_convert.data
        
        # 3. Finalize & Save
        # Save profile.json in the character root
        # Update profile with Asset Paths
        profile.default_image_path = params['default_image_key']
        profile.asset_map = params['asset_map']
        
        # Save to disk
        try:
             import json
             target_dir = Path(params['character_root'])
             profile_path = target_dir / "profile.json"
             
             with open(profile_path, 'w', encoding='utf-8') as f:
                 f.write(profile.model_dump_json(indent=2))
                 
             logger.info(f"Character Saved to: {profile_path}")
             return Result.ok(profile)
             
        except Exception as e:
            return Result.fail(f"Failed to save profile: {e}")

    async def generate_profile(self, raw_data: Dict[str, Any], override_profile: Any = None) -> Result[CharacterProfile]:
        """
        Executes the 'character_convert' prompt to generate a structured profile.
        Async execution.
        """
        logger.info("Starting LLM Character Conversion...")

        # Resolve Profile from Config if not overridden
        if not override_profile:
            try:
                from src.foundation.config import ConfigManager
                config_mgr = ConfigManager.get_instance()
                # Ensure config is loaded (it might be in some contexts, safe access)
                if config_mgr._config:
                    strategy_profile_name = config_mgr.config.llm_strategies.get("character_convert")
                    if strategy_profile_name:
                        override_profile = config_mgr.config.llm_profiles.get(strategy_profile_name)
            except Exception as e:
                logger.warning(f"Failed to resolve strategy profile for 'character_convert': {e}")
        
        # Execute LLM Request (Async)
        # We specify the prompt_name "character_convert" defined in Factory
        res_llm = await self.llm.execute("character_convert", data={"raw_data": raw_data}, override_profile=override_profile)
        
        if not res_llm.success:
            return Result.fail(f"LLM Conversion Failed: {res_llm.error}")
            
        llm_response = res_llm.data
        content = llm_response.content
        
        try:
            # 1. Parse into GeneratedProfile (Validation specific to LLM output)
            # LLM output might be a dict (if Parsed by provider), a Pydantic model, or string.
            if isinstance(content, GeneratedProfile):
                 gen_profile = content
            elif isinstance(content, dict):
                 gen_profile = GeneratedProfile.model_validate(content)
            else:
                 gen_profile = GeneratedProfile.model_validate_json(content)
            
            # 2. Map to CharacterProfile (Runtime Entity)
            # Map Optional fields (None) to Empty Strings ("")
            profile = CharacterProfile(
                name=gen_profile.name,
                aliases=gen_profile.aliases,
                appearance=gen_profile.appearance,
                
                surface_persona=gen_profile.surface_persona,
                inner_persona=gen_profile.inner_persona,
                speech_patterns=gen_profile.speech_patterns,
                
                background_story=gen_profile.background_story,
                world_definition=gen_profile.world_definition,
                initial_situation=gen_profile.initial_situation or "", # Handle None
                first_message=gen_profile.first_message or "",         # Handle None
                
                speech_examples=gen_profile.speech_examples,
                
                # Runtime fields (filled later)
                default_image_path="",
                asset_map={}
            )
            
            logger.info(f"Character Profile Converted: {profile.name}")
            return Result.ok(profile)
            
        except Exception as e:
            logger.error(f"Failed to parse converted profile: {e}")
            from src.modules.llm_client.utils.json_repair import JsonRepair
            # Fallback: Try repairing if basic parse failed
            try:
                logger.warning("Attempting JSON Repair...")
                repaired = JsonRepair.repair(str(content))
                gen_profile = GeneratedProfile.model_validate_json(repaired)
                
                profile = CharacterProfile(
                    name=gen_profile.name,
                    aliases=gen_profile.aliases,
                    appearance=gen_profile.appearance,
                    surface_persona=gen_profile.surface_persona,
                    inner_persona=gen_profile.inner_persona,
                    speech_patterns=gen_profile.speech_patterns,
                    background_story=gen_profile.background_story,
                    world_definition=gen_profile.world_definition,
                    initial_situation=gen_profile.initial_situation or "",
                    first_message=gen_profile.first_message or "",
                    speech_examples=gen_profile.speech_examples,
                    default_image_path="",
                    asset_map={}
                )
                logger.info(f"Character Profile Converted (Repaired): {profile.name}")
                return Result.ok(profile)
            except Exception as repair_e:
                return Result.fail(f"Parsing/Validation Error after Repair: {repair_e}")
