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
        1. Load/Extract raw data from file (.charx, .json, .png, .artrcc)
        2. Convert via LLM (Skip for .artrcc)
        3. Save/Persist to Character Storage
        4. Auto-Generate .artrcc archive
        """
        from pathlib import Path
        from src.modules.character.loader import CharXLoader
        from src.modules.character.artrcc_handler import ARTRCCLoader, ARTRCCSaver
        
        path_obj = Path(file_path)
        
        # 1. Load Raw
        if path_obj.suffix == '.charx':
            loader = CharXLoader()
            res_load = loader.load_raw(path_obj)
            if not res_load.success:
                return Result.fail(res_load.error)
            params = res_load.data
            
            # 2. Convert (LLM)
            raw_json = params['raw_json']
            res_convert = await self.generate_profile(raw_json, override_profile=override_profile)
            if not res_convert.success:
                return Result.fail(res_convert.error)
            profile = res_convert.data
            # Update profile with Asset Paths
            # Use filename if available, else key (fallback)
            raw_filename = params.get('default_image_filename')
            if raw_filename:
                profile.default_image_path = raw_filename
            else:
                profile.default_image_path = params.get('default_image_key', "")
            
            profile.asset_map = params.get('asset_map', {})
            
            target_root = params['character_root'] # Where CharXLoader extracted assets

        elif path_obj.suffix == '.artrcc':
            # Direct Load (No LLM)
            loader = ARTRCCLoader()
            res_load = loader.load(path_obj)
            if not res_load.success:
                return Result.fail(res_load.error)
            
            data = res_load.data
            profile_dict = data['profile_dict']
            target_root = data['character_root']
            
            try:
                profile = CharacterProfile.model_validate(profile_dict)
            except Exception as e:
                return Result.fail(f"Invalid .artrcc profile: {e}")
                
        else:
            return Result.fail(f"Unsupported file format: {path_obj.suffix}")

        # 3. Finalize & Save
        try:
             target_dir = Path(target_root)
             profile_path = target_dir / "profile.json"
             
             with open(profile_path, 'w', encoding='utf-8') as f:
                 f.write(profile.model_dump_json(indent=2))
                 
             logger.info(f"Character Saved to: {profile_path}")
             
             # 4. Auto-Generate .artrcc
             # We want to ensure the .artrcc file exists in the character directory
             # Filename: {id}.artrcc
             artrcc_path = target_dir / f"{profile.id or target_dir.name}.artrcc"
             
             # Ensure profile has absolute paths in asset_map for Saver?
             # CharXLoader returns absolute paths in asset_map.
             # ARTRCCLoader extracts to assets_dir and returns profile_dict.
             # profile_dict might have relative paths/keys? 
             # ARTRCCSaver expects asset_map to have Absolute Paths if it reads from disk?
             # Wait, ARTRCCSaver: 
             # if profile.asset_map: for key, abs_path_str in profile.asset_map.items(): if Path(abs_path_str).exists()...
             
             # If we loaded from .artrcc, profile.asset_map in memory might just be keys if we validated from JSON?
             # We need to ensure asset_map points to the extracted assets in `target_dir/assets`.
             
             if path_obj.suffix == '.artrcc':
                 # Reconstruct asset_map to absolute paths
                 # Assuming keys match filenames in assets/
                 new_map = {}
                 assets_dir = target_dir / "assets"
                 if assets_dir.exists():
                     for f in assets_dir.iterdir():
                         if f.is_file():
                             new_map[f.name] = str(f.absolute())
                 profile.asset_map = new_map
                 # Save profile with updated map? No, we just need it for Saver.
                 # Actually we should update profile.json on disk with valid map?
                 # ARTRCC format usually just keys? 
                 # Let's keep runtime profile having absolute paths.
             
             # Save ARTRCC
             res_save = ARTRCCSaver.save(profile, artrcc_path)
             if res_save.success:
                 logger.info(f"Auto-Generated .artrcc: {artrcc_path}")
             else:
                 logger.warning(f"Failed to auto-generate .artrcc: {res_save.error}")

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
