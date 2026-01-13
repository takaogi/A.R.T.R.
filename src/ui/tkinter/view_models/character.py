
import os
import shutil
from pathlib import Path
from typing import List, Optional
import tkinter as tk
import asyncio
import glob

from src.core.controller import CoreController
from src.modules.character.loader import CharXLoader
from src.modules.character.schema import CharacterProfile
from src.modules.character.creator import CharacterCreatorService
from src.foundation.paths.manager import PathManager

class CharacterViewModel:
    """
    Manages state for Character Views.
    Bridge between UI and Backend.
    """
    def __init__(self, controller: CoreController):
        self.controller = controller
        self.creator_service = CharacterCreatorService(controller.config_manager, controller.llm_client)
        self.loader = CharXLoader()
        self.config_manager = controller.config_manager
        
        # State
        self.character_list: List[str] = []
        self.selected_character: Optional[str] = None
        self.current_file_id: Optional[str] = None # Tracks the active directory/ID tracking
        self.draft_profile: Optional[CharacterProfile] = None

    def scan_characters(self) -> List[str]:
        """Scans characters_data/ for available profiles."""
        base_dir = PathManager.get_instance().get_characters_dir()
        if not base_dir.exists():
            base_dir.mkdir(parents=True, exist_ok=True)
            
        # Strategy: Look for specific metadata file or just directory names?
        # A.R.T.R. V2: Each character is a directory with profile.json or .charx?
        # Let's assume directory name IS the character ID/Name.
        dirs = [d.name for d in base_dir.iterdir() if d.is_dir()]
        self.character_list = dirs
        return dirs

    def select_character(self, name: str):
        self.selected_character = name
        
    async def load_character_to_engine(self):
        """Loads the selected character into the active controller."""
        if not self.selected_character:
            return False
            
        # Call Controller
        # Assuming Controller knows how to load by name?
        # Controller.load_character expects (output_path or object).
        # We need to constructing path.
        
        # For now, let's load the profile JSON manually here or 
        # let Controller handle it. Controller.load_character implementation 
        # has TODO for file loading, so we might need to load it here.
        
        # Basic Load Logic:
        base_dir = PathManager.get_instance().get_characters_dir()
        profile_path = base_dir / self.selected_character / "profile.json"
        if profile_path.exists():
             with open(profile_path, "r", encoding="utf-8") as f:
                 json_str = f.read()
             profile = CharacterProfile.model_validate_json(json_str)
             await self.controller.load_character(
                 profile_obj=profile, 
                 directory_name=self.selected_character
             )
             return True
        return False

    async def generate_draft(self, raw_text: str, current_data: dict = None) -> bool:
        """Generates a draft profile using AI."""
        profile = await self.creator_service.generate_profile(raw_text, existing_profile=current_data)
        if profile:
            self.draft_profile = profile
            return True
        return False
        

    async def import_character(self, path: str, file_id: str) -> bool:
        """
        Direct Import from .charx/.json.
        1. Load & Extract (via Loader) -> data/characters/{file_id}
        2. Convert (via Creator) -> Profile
        3. Save (Profile.json) -> data/characters/{file_id}/profile.json
        """
        # 1. Load Raw (Assets extracted to file_id directory by override)
        load_res = self.loader.load_raw(Path(path), character_name_override=file_id)
        if not load_res.success:
            print(f"Import Failed: {load_res.error}")
            return False
            
        data = load_res.data
        raw_json = data["raw_json"]
        # safe_name = data["character_name"] # Should match file_id now
        asset_map = data.get("asset_map")
        
        # 2. Generate Profile from Raw Dict
        # We pass raw_json as `raw_source` and inject `asset_map`
        profile = await self.creator_service.generate_profile(raw_source=raw_json, asset_map=asset_map)
        
        if profile:
            self.draft_profile = profile
            # 3. Save to the specific directory (file_id)
            return self.save_draft(file_id)
            
        return False

    async def load_raw_data_for_creator(self, path: str) -> Optional[dict]:
        """
        Loads .charx and returns generated Draft Profile (as dict) for filling the UI form.
        """
        load_res = self.loader.load_raw(Path(path))
        if not load_res.success:
            print(f"Load Failed: {load_res.error}")
            return None
            
        data = load_res.data
        raw_json = data["raw_json"]
        
        # Generate Draft from Raw Dict
        profile = await self.creator_service.generate_profile(raw_source=raw_json)
        
        if profile:
            self.draft_profile = profile
            # Track the ID determined by Loader (character_name = directory name)
            self.current_file_id = data.get("character_name")
            return profile.model_dump()
            
        return None
    
    def save_draft(self, file_id: str) -> bool:
        if not self.draft_profile:
            return False
            
        # Validate ID (Simple check)
        # Assuming caller passed valid ID, but let's be safe
        safe_id = "".join(c for c in file_id if c.isalnum() or c in ('_', '-')).strip()
        if not safe_id:
            print("Invalid File ID")
            return False
            
        target_dir = PathManager.get_instance().get_characters_dir() / safe_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_file_id = safe_id
        
        # Save Profile
        with open(target_dir / "profile.json", "w", encoding="utf-8") as f:
            f.write(self.draft_profile.model_dump_json(indent=2))
            
        return True

    def get_model_name_for_strategy(self, strategy: str) -> str:
        """Lookups configured model name for a strategy (e.g. 'character_generate')."""
        try:
            profile = self.controller.llm_client.router.get_profile(strategy)
            return f"{profile.model_name} ({profile.provider})"
        except:
            return "Unknown Model"

    def delete_character(self, directory_name: str) -> bool:
        """Permanently deletes a character directory."""
        if not directory_name:
            return False
            
        base_dir = PathManager.get_instance().get_characters_dir()
        target = base_dir / directory_name
        
        if not target.exists():
            return False
            
        try:
            shutil.rmtree(target)
            
            # If deleted character was selected, clear selection
            if self.selected_character == directory_name:
                self.selected_character = None
                
            return True
        except Exception as e:
            print(f"Delete Failed: {e}")
            return False
