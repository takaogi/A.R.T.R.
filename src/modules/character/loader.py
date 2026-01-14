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
                    "default_image_key": default_image_key,
                    "default_image_filename": default_image_rel_path # Added explicit filename
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

        # 1. Identify default stem/keys (to exclude from prefix calc)
        default_stems = set()
        default_key_final = ""
        
        # Helper to get pure stem
        def get_stem(k):
            s = k
            while True:
                p = Path(s)
                if p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.json']:
                    s = p.stem
                else:
                    break
            return s

        # Pass 1: Identify Defaults
        for k, v in raw_map.items():
            is_default = False
            # Check by path
            if default_filename and (os.path.basename(v).lower() == os.path.basename(default_filename).lower()):
                is_default = True
            # Check by key convention
            elif k.lower() in ["default", "main"]:
                is_default = True
                
            if is_default:
                default_stems.add(get_stem(k))

        # Pass 2: Collect Stems for Prefix (Non-Defaults only)
        other_stems = []
        filename_keys = list(raw_map.keys())
        
        for k in filename_keys:
            stem = get_stem(k)
            if stem in default_stems:
                continue
            other_stems.append(stem)
        
        # 2. Calculate Prefix
        prefix = ""
        if len(other_stems) > 1:
            prefix = os.path.commonprefix(other_stems)
            
        # Refine prefix
        if prefix and len(prefix) >= 3:
             logger.debug(f"Detected common asset prefix: '{prefix}'")
        else:
            prefix = ""

        # 3. Build Optimized Map
        optimized_map = {}
        
        for k, v in raw_map.items():
            stem = get_stem(k)
            
            # Determine if this specific entry is a default image
            is_this_default = False
            if default_filename and (os.path.basename(v).lower() == os.path.basename(default_filename).lower()):
                is_this_default = True
            elif k.lower() in ["default", "main"]: # e.g. "main.png"
                 is_this_default = True

            new_key = stem
            if not is_this_default and prefix and stem.startswith(prefix):
                 new_key = stem[len(prefix):]
                 # Clean leading separator
                 if new_key and new_key[0] in ['_', '-', ' ']:
                     new_key = new_key[1:]
            
            # Conflict resolution? (Overwrite for now)
            optimized_map[new_key] = v
            
            if is_this_default:
                default_key_final = new_key

        return optimized_map, default_key_final
