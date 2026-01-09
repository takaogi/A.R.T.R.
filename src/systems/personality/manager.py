import json
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from src.utils.path_helper import get_data_dir
from src.utils.logger import logger
from src.systems.personality.generator import PersonalityGenerator

class PersonalityManager:
    def __init__(self):
        self.characters_dir = get_data_dir() / "characters"
        # self.cache_dir is removed; we use per-character folder in characters_dir
        self.generator = PersonalityGenerator()

    def get_character_path(self, char_name: str) -> Path:
        # Simple sanitization
        safe_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '-', '_')).strip()
        return self.characters_dir / f"{safe_name}.json"

    
    def validate_cc(self, cc_data: Dict) -> bool:
        """
        Validates the structure of the Character Card.
        Returns True if valid, logs warning and returns False (or True with warning) otherwise.
        """
        required = ["name", "description", "first_message"]
        missing = [f for f in required if f not in cc_data or not cc_data[f]]
        
        if missing:
            logger.warning(f"CC Validation: Missing required fields: {missing}")
            # For now, we continue but warn. Strict validation might return False.
            return True 
        return True

    def load_character(self, char_name: str, progress_callback=None) -> Optional[Dict[str, Any]]:
        """
        Loads CC, checks hash, and regenerates assets if necessary.
        Returns the generated assets (Core/Reflex/Params).
        
        Args:
            char_name: Character name stem.
            progress_callback: Optional callable(str) for UI feedback.
        """
        if progress_callback: progress_callback(f"Loading character card '{char_name}'...")
        
        path = self.get_character_path(char_name)
        if not path.exists():
            logger.error(f"Character file not found: {path}")
            if progress_callback: progress_callback(f"Error: CC file not found.")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                cc_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load character JSON: {e}")
            if progress_callback: progress_callback(f"Error: Invalid JSON.")
            return None

        self.validate_cc(cc_data)

        # Calculate Hash
        current_hash = self._calculate_hash(cc_data)
        
        safe_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '-', '_')).strip()
        asset_dir = self.characters_dir / safe_name
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        meta_path = asset_dir / "metadata.json"
        
        needs_generation = True
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("hash") == current_hash:
                    needs_generation = False
                    logger.info(f"Character '{char_name}' hash matched. Using cached assets.")
                    if progress_callback: progress_callback("Hash matched. Loading cached assets...")
            except Exception:
                logger.warning("Failed to read metadata, forcing regeneration.")
        
        assets = {}
        if needs_generation:
            logger.info(f"Character '{char_name}' changed or new. Regenerating assets...")
            if progress_callback: progress_callback("Changes detected. Regenerating assets (This may take a while)...")
            
            # We run this synchronously for now
            assets = asyncio.run(self.generator.generate_all(cc_data))
            
            # Save assets
            self._save_assets(asset_dir, assets, current_hash)
            
            # --- AUTO-REVERSE SYNC (Forward Sync) ---
            # Automatically save generated high-level configs back to CC Source of Truth
            updated_cc = False
            
            # 1. System Params (Pacemaker / VAD)
            if "system_params" in assets:
                # Merge into CC
                # Check if existing is same
                if cc_data.get("system_params") != assets["system_params"]:
                    cc_data["system_params"] = assets["system_params"]
                    updated_cc = True
                    if progress_callback: progress_callback("Syncing generated system_params to CC...")

            # 2. Reaction Styles
            if "reaction_styles" in assets:
                if cc_data.get("reaction_styles") != assets["reaction_styles"]:
                    cc_data["reaction_styles"] = assets["reaction_styles"]
                    updated_cc = True
                    if progress_callback: progress_callback("Syncing generated reaction_styles to CC...")

            if updated_cc:
                try:
                    # Save CC
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(cc_data, f, indent=4, ensure_ascii=False)
                    # Recalculate hash and update metadata so we don't regenerate loop
                    new_hash = self._calculate_hash(cc_data)
                    with open(asset_dir / "metadata.json", "w", encoding="utf-8") as f:
                        json.dump({"hash": new_hash}, f, indent=2)
                    logger.info("Auto-Reverse Sync completed.")
                except Exception as e:
                    logger.error(f"Failed to auto-sync CC: {e}")
                    
        else:
            assets = self._load_assets(asset_dir)

        # Inject Raw CC Data for Translator Layer usage
        assets["raw_cc"] = cc_data

        return assets
    
    def _calculate_hash(self, data: Dict) -> str:
        # Canonical string representation
        dump = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    def _save_assets(self, path: Path, assets: Dict, hash_val: str):
        # Save individual components
        if "reflex_memory" in assets:
            with open(path / "reflex_memory.json", "w", encoding="utf-8") as f:
                json.dump(assets["reflex_memory"], f, indent=2, ensure_ascii=False)
        
        if "core_memory" in assets:
            with open(path / "core_memory.xml", "w", encoding="utf-8") as f:
                f.write(assets["core_memory"])
                
        if "system_params" in assets:
            with open(path / "system_params.json", "w", encoding="utf-8") as f:
                json.dump(assets["system_params"], f, indent=2, ensure_ascii=False)

        if "reaction_styles" in assets:
            with open(path / "reaction_styles.json", "w", encoding="utf-8") as f:
                json.dump(assets["reaction_styles"], f, indent=2, ensure_ascii=False)

        # Save Metadata
        with open(path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({"hash": hash_val}, f, indent=2)
            
    def _load_assets(self, path: Path) -> Dict:
        assets = {}
        try:
            if (path / "reflex_memory.json").exists():
                with open(path / "reflex_memory.json", "r", encoding="utf-8") as f:
                    assets["reflex_memory"] = json.load(f)
            
            if (path / "core_memory.xml").exists():
                with open(path / "core_memory.xml", "r", encoding="utf-8") as f:
                    assets["core_memory"] = f.read()

            if (path / "system_params.json").exists():
                with open(path / "system_params.json", "r", encoding="utf-8") as f:
                    assets["system_params"] = json.load(f)

            if (path / "reaction_styles.json").exists():
                with open(path / "reaction_styles.json", "r", encoding="utf-8") as f:
                    assets["reaction_styles"] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading cached assets: {e}")
        return assets
    async def sync_cc_from_core(self, char_name: str, core_xml: str):
        """
        Updates the Character Card JSON file based on the latest Core Memory XML.
        This closes the loop: CC -> Core Memory -> Evolve -> CC.
        """
        cc_path = self.get_character_path(char_name)
        if not cc_path.exists():
            logger.error(f"Cannot sync: CC file not found at {cc_path}")
            return

        try:
            with open(cc_path, "r", encoding="utf-8") as f:
                cc_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load existing CC for sync: {e}")
            return

        # 1. Reverse Generate (Get changes only)
        changes = await self.generator._reverse_generate_cc(cc_data, core_xml)
        
        if not changes:
            logger.info("No reverse sync changes detected.")
            return

        # 2. Apply Changes
        updated = False
        for key, value in changes.items():
            if value and cc_data.get(key) != value:
                logger.info(f"Reverse Sync: Updating {key}...")
                cc_data[key] = value
                updated = True
        
        # 3. Save if updated
        if updated:
            # Backup first? Maybe. For now just overwrite safely.
            try:
                # Update hash because we modified the source
                # Ideally we might want to update the metadata.json hash too, 
                # so the system doesn't think it needs to 'regenerate' assets again from this new CC 
                # (since the assets are technically the source of truth here).
                # But allowing regeneration is safer to ensure consistency.
                
                with open(cc_path, "w", encoding="utf-8") as f:
                    json.dump(cc_data, f, indent=4, ensure_ascii=False)
                logger.info(f"Character Card '{char_name}' updated via Reverse Sync.")
                
            except Exception as e:
                logger.error(f"Failed to save updated CC: {e}")
