import json
import zipfile
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from src.foundation.logging import logger
from src.foundation.paths.manager import PathManager
from src.foundation.types import Result

class CharXLoader:
    """
    Loader for RisuAI .charx (V3/V2) format.
    Handles ZIP extraction, Asset optimization, and RisuAI JSON extraction.
    Note: Does NOT perform LLM conversion (handled by Generator).
    """

    def __init__(self):
        self.paths = PathManager.get_instance()

    def load_raw(self, file_path: Path, character_name_override: str = None) -> Result[Dict[str, Any]]:
        """
        Extracts .charx file to characters_data/{name}/.
        Returns the raw RisuAI JSON data and the path to the character root.
        
        Args:
            file_path: Absolute path to .charx file
            character_name_override: Optional name to use for the directory. 
                                     If None, tries to guess from filename or internal JSON.
        """
        try:
            if not file_path.exists():
                return Result.fail(f"File not found: {file_path}")

            # 1. Temporary Extract to read card.json and determine name
            # We open as ZipFile
            with zipfile.ZipFile(file_path, 'r') as z:
                if 'card.json' not in z.namelist():
                    return Result.fail("Invalid .charx: card.json not found.")

                raw_json = json.loads(z.read('card.json').decode('utf-8'))
                
                # Determine Character Name (for directory)
                char_name = character_name_override
                if not char_name:
                    # Try data.name
                    char_name = raw_json.get('data', {}).get('name')
                
                if not char_name:
                    # Fallback to filename stem
                    char_name = file_path.stem

                # Sanitize name for filesystem
                safe_name = "".join([c for c in char_name if c.isalnum() or c in (' ', '-', '_')]).strip()
                if not safe_name:
                    safe_name = "Unknown_Character"

                # 2. Setup Target Directory
                char_root = self.paths.get_characters_dir() / safe_name
                assets_dir = char_root / "assets"
                
                if char_root.exists():
                    logger.warning(f"Character directory '{safe_name}' already exists. Overwriting...")
                    # Optional: Backup? For now, simple overwrite/merge logic.
                
                char_root.mkdir(parents=True, exist_ok=True)
                assets_dir.mkdir(parents=True, exist_ok=True)

                # 3. Extract & Build Raw Map
                raw_asset_map = self._extract_assets(z, assets_dir)
                
                # 4. Identify Default Image (Before optimization to match raw paths)
                default_image_rel_path = self._find_default_image(raw_json, raw_asset_map)
                
                # 5. Optimize Keys (Prefix Stripping)
                optimized_map, default_image_key = self._optimize_assets(raw_asset_map, default_image_rel_path)
                
                # 6. Return Raw Data + Metadata
                return Result.ok({
                    "raw_json": raw_json,
                    "character_root": str(char_root),
                    "character_name": safe_name,
                    "asset_map": optimized_map,
                    "default_image_key": default_image_key
                })

        except Exception as e:
            logger.error(f"CharX Load Error: {e}")
            return Result.fail(str(e))

    def _extract_assets(self, z: zipfile.ZipFile, assets_dir: Path) -> Dict[str, str]:
        """
        Extracts assets and returns map: {ZipFileName: AbsolutePath}
        """
        asset_map = {}
        files = [f for f in z.namelist() if f.startswith("assets/") and not f.endswith("/")]
        
        for zip_path in files:
            filename = os.path.basename(zip_path)
            if not filename: continue
            
            target_path = assets_dir / filename
            with z.open(zip_path) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
                
            asset_map[filename] = str(target_path.absolute())
            
        return asset_map

    def _find_default_image(self, json_data: Dict, raw_map: Dict[str, str]) -> Optional[str]:
        """
        Identifies the filename of the default image from RisuAI data.
        Returns the filename (key in raw_map) or None.
        """
        data = json_data.get('data', {})
        defined_assets = data.get('assets', [])
        
        # 1. Explicit Definition (type='icon' or name='main')
        for item in defined_assets:
            if item.get('type') == 'icon' or item.get('name') == 'main':
                uri = item.get('uri', '')
                # uri format: "embeded://assets/filename.png"
                if uri.startswith("embeded://assets/"):
                    filename = uri.replace("embeded://assets/", "")
                    if filename in raw_map:
                        return filename

        # 2. Heuristic (Check filenames in map)
        # Often RisuAI users just have one image, or name it 'main.png'
        candidates = ["main.png", "default.png", "icon.png"]
        for c in candidates:
            if c in raw_map:
                return c
                
        # 3. Fallback: Return first available if any
        if raw_map:
            # Sort to be deterministic
            sorted_keys = sorted(raw_map.keys())
            return sorted_keys[0]
            
        return None

    def _optimize_assets(self, raw_map: Dict[str, str], default_filename: str) -> Tuple[Dict[str, str], str]:
        """
        Strips common prefixes from filenames.
        Returns (OptimizedMap, DefaultImageKey).
        """
        if not raw_map:
            return {}, ""

        # Gather clean stems (no extension) to calculate prefix
        # We process keys: "MyChar_Smile.png" -> "MyChar_Smile"
        filename_keys = list(raw_map.keys())
        stems = [Path(f).stem for f in filename_keys]
        
        # Calculate common prefix
        prefix = os.path.commonprefix(stems)
        
        # Safety: Prefix must be reasonable length (>=3) to avoid stripping "S" from "Smile" if "Sad" exists (common "S"?)
        # Actually commonprefix of "Smile", "Sad" is "S". We don't want to strip "S".
        # Assuming format "CharacterName_Expression".
        # Valid prefix usually ends with _ or - or space, or is just the name.
        
        optimized_map = {}
        default_key = ""
        
        # Refine prefix: prefer ending with separator
        if len(stems) > 1 and len(prefix) >= 3:
            # Check if prefix looks like a name tag
            logger.debug(f"Detected common asset prefix: '{prefix}'")
        else:
            prefix = "" # Too short or no commonality

        for fname in filename_keys:
            stem = Path(fname).stem
            final_key = stem
            
            if prefix and stem.startswith(prefix):
                # Strip
                candidate = stem[len(prefix):]
                # If separator remains, strip it
                if candidate and candidate[0] in ['_', '-', ' ']:
                    candidate = candidate[1:]
                
                # If stripping resulted in empty or too short, revert
                if len(candidate) >= 2:
                    final_key = candidate
            
            # Add to map
            # Collision handling? If "Char_A.png" and "Char_A.jpg" -> "A" collision.
            # Overwrite for now (Loader implies latest wins or single format preferred)
            optimized_map[final_key] = raw_map[fname]
            
            # Check if this was the default image
            if fname == default_filename:
                default_key = final_key

        return optimized_map, default_key
