import json
import zipfile
import shutil
import os
from pathlib import Path
from typing import Dict, Any, Optional

from src.foundation.logging import logger
from src.foundation.types import Result
from src.modules.character.schema import CharacterProfile
from src.foundation.paths.manager import PathManager

class ARTRCCLoader:
    """
    Loader for .artrcc (A.R.T.R. Character Card) format.
    Format: ZIP archive containing:
      - character.json: Serialized CharacterProfile
      - assets/: Directory containing images
    """
    def __init__(self):
        self.paths = PathManager.get_instance()

    def load(self, file_path: Path, character_name_override: str = None) -> Result[Dict[str, Any]]:
        """
        Extracts .artrcc file to characters_data/{name}/.
        Returns the profile data and metadata.
        """
        try:
            if not file_path.exists():
                return Result.fail(f"File not found: {file_path}")

            with zipfile.ZipFile(file_path, 'r') as z:
                if 'character.json' not in z.namelist():
                    return Result.fail("Invalid .artrcc: character.json not found.")

                # Read Profile
                with z.open('character.json') as f:
                    profile_data = json.loads(f.read().decode('utf-8'))

                # Determine Name / ID
                # Priority: Override > Profile ID > Profile Name > Filename
                char_id = character_name_override
                if not char_id:
                    char_id = profile_data.get('id')
                if not char_id:
                    # Sanitize name
                    raw_name = profile_data.get('name', 'Unknown')
                    char_id = "".join([c for c in raw_name if c.isalnum() or c in (' ', '-', '_')]).strip()
                
                if not char_id:
                    char_id = file_path.stem

                # Setup Directories
                char_root = self.paths.get_characters_dir() / char_id
                assets_dir = char_root / "assets"
                
                if char_root.exists():
                    logger.warning(f"Character directory '{char_id}' already exists. Overwriting...")

                char_root.mkdir(parents=True, exist_ok=True)
                assets_dir.mkdir(parents=True, exist_ok=True)

                # Extract Assets
                asset_map = {}
                for zip_info in z.infolist():
                    if zip_info.filename.startswith("assets/") and not zip_info.is_dir():
                        filename = os.path.basename(zip_info.filename)
                        if not filename: continue
                        
                        target_path = assets_dir / filename
                        with z.open(zip_info) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        
                        # Rebuild Asset Map Key
                        # Assuming the profile.asset_map in JSON has keys that match filenames?
                        # Or we need to reconstruct? 
                        # .artrcc should preserve the map.
                        # We will update the map with ABSOLUTE paths later.
                        # For now, we rely on the profile_data's map being correct relative to keys.
                        
                # Update Profile Data with new Absolute Paths if necessary?
                # Actually importer typically handles this.
                # But here we stick to the pattern: Return data, let importer/manager finalize.
                
                # However, ARTRCC format implies we trust the mapping.
                # We should verify asset_map in profile_data matches extracted files?
                
                return Result.ok({
                    "profile_dict": profile_data,
                    "character_root": str(char_root),
                    "character_id": char_id
                })

        except Exception as e:
            logger.error(f"ARTRCC Load Error: {e}")
            return Result.fail(str(e))

class ARTRCCSaver:
    """
    Saver for .artrcc format.
    Packs CharacterProfile and Assets into ZIP.
    """
    
    @staticmethod
    def save(profile: CharacterProfile, target_path: Path) -> Result[bool]:
        """
        Saves profile to .artrcc zip file.
        """
        try:
            # 1. Prepare Data
            profile_dict = profile.model_dump()
            
            # Sanitize Asset Map (Privacy: Convert Absolute Paths to Filenames)
            if "asset_map" in profile_dict and profile_dict["asset_map"]:
                new_map = {}
                for k, v in profile_dict["asset_map"].items():
                    # We store only the filename.
                    # The Loader will assume files are in assets/ folder.
                    new_map[k] = Path(v).name
                profile_dict["asset_map"] = new_map

            # 2. Create ZIP
            with zipfile.ZipFile(target_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                # Write Profile
                z.writestr("character.json", json.dumps(profile_dict, indent=2, ensure_ascii=False))
                
                # Write Assets
                # profile.asset_map maps KEY -> ABSOLUTE PATH (Runtime)
                added_files = set()
                
                if profile.asset_map:
                    for key, abs_path_str in profile.asset_map.items():
                        abs_path = Path(abs_path_str)
                        if abs_path.exists():
                            # Usage: assets/filename
                            filename = abs_path.name
                            zip_entry_name = f"assets/{filename}"
                            
                            if zip_entry_name not in added_files:
                                z.write(abs_path, zip_entry_name)
                                added_files.add(zip_entry_name)
                        else:
                            logger.warning(f"Asset missing for export: {abs_path}")

                # Verify Default Image is included
                # default_image_path might be a key or path?
                # Schema says: default_image_path: str = ""
                # In CharXLoader it became a key.
                # If it's a key, it should be in asset_map.
                
            logger.info(f"Exported .artrcc to {target_path}")
            return Result.ok(True)

        except Exception as e:
            logger.error(f"ARTRCC Save Error: {e}")
            return Result.fail(str(e))
