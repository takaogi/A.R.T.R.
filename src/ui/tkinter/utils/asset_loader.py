from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageTk
import logging
from src.foundation.paths.manager import PathManager

class AssetLoader:
    """
    Manages loading and resizing of UI assets (Images).
    """
    _cache: Dict[str, ImageTk.PhotoImage] = {}
    
    @classmethod
    def load_image(cls, path: Path, size: tuple[int, int] = None) -> Optional[ImageTk.PhotoImage]:
        """
        Loads an image from path, optionally resizes it.
        Returns ImageTk.PhotoImage compatible with Tkinter.
        """
        key = f"{path}_{size}"
        if key in cls._cache:
            return cls._cache[key]
            
        if not path.exists():
            return None
            
        try:
            img = Image.open(path)
            
            if size:
                # Resize maintaining aspect ratio? Or fit?
                # For Tachie, usually fit height.
                # Here we do simple resize for now.
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
            tk_img = ImageTk.PhotoImage(img)
            cls._cache[key] = tk_img
            return tk_img
        except Exception as e:
            logging.error(f"Failed to load image {path}: {e}")
            return None

    @classmethod
    def get_tachie(cls, char_name: str, expression: str, asset_map: Dict[str, str] = None, max_height: int = 800) -> Optional[ImageTk.PhotoImage]:
        """
        Resolves character tachie path.
        Checks extensions: .png, .webp, .jpg
        Uses asset_map if provided.
        """
        base_dir = PathManager.get_instance().get_characters_dir() / char_name / "assets"
        target_path = None
        exts = [".png", ".webp", ".jpg", ".jpeg"]
        
        # 1. Check Asset Map
        if asset_map and expression in asset_map:
            mapped_filename = asset_map[expression]
            # Mapped filename might have extension or not
            p = base_dir / mapped_filename
            if p.exists():
                target_path = p
            else:
                 # Try appending extensions if missing
                 for ext in exts:
                     p_ext = base_dir / f"{mapped_filename}{ext}"
                     if p_ext.exists():
                         target_path = p_ext
                         break
        
        # 2. Direct Filename Match (Fallback or if no map)
        if not target_path:
            for ext in exts:
                p = base_dir / f"{expression}{ext}"
                if p.exists():
                    target_path = p
                    break
        
        # 3. Fallback to 'default' or 'neutral'
        if not target_path:
            for fallback in ["default", "neutral"]:
                for ext in exts:
                    p = base_dir / f"{fallback}{ext}"
                    if p.exists():
                        target_path = p
                        break
                    
        if not target_path:
             return None
             
        return cls.load_image(target_path, size=(1000, max_height))
