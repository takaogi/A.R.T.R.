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
    def get_tachie(cls, char_name: str, expression: str, asset_map: Dict[str, str] = None, default_image_path: str = None, max_height: int = 800) -> Optional[ImageTk.PhotoImage]:
        """
        Resolves character tachie path.
        Checks extensions: .png, .webp, .jpg
        Uses asset_map if provided.
        """
        # logging.info(f"AssetLoader: load tachie for {char_name}, expr={expression}, default={default_image_path}")
        
        base_dir = PathManager.get_instance().get_characters_dir() / char_name / "assets"
        target_path = None
        exts = [".png", ".webp", ".jpg", ".jpeg"]
        
        # 0. High Priority: default_image_path if expression is 'default'
        if expression == "default" and default_image_path:
            # Try as relative to assets first
            p = base_dir / default_image_path
            if p.exists():
                target_path = p
                # logging.debug(f"Found via default_image_path (assets): {p}")
            else:
                # Try appending extensions (Robustness for legacy imports/keys)
                for ext in exts:
                     p_ext = base_dir / f"{default_image_path}{ext}"
                     if p_ext.exists():
                         target_path = p_ext
                         # logging.debug(f"Found via default_image_path+ext: {p_ext}")
                         break

            if not target_path:
                # Try relative in char root
                p_root = base_dir.parent / default_image_path
                if p_root.exists():
                    target_path = p_root
                    # logging.debug(f"Found via default_image_path (root): {p_root}")
            
            if not target_path:
                pass
                # logging.warning(f"default_image_path '{default_image_path}' provided but file not found at {p} or {p_root}")

        # 1. Check Asset Map
        if not target_path and asset_map and expression in asset_map:
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
        
        # 3. Fallback to 'default', 'neutral', 'main', 'icon'
        if not target_path:
            for fallback in ["default", "neutral", "main", "icon"]:
                for ext in exts:
                    p = base_dir / f"{fallback}{ext}"
                    if p.exists():
                        target_path = p
                        break
                    
        if not target_path:
             logging.warning(f"AssetLoader: Could not find tachie for {char_name} (expr={expression}). Base: {base_dir}")
             return None
             
        # logging.debug(f"AssetLoader: Loaded {target_path}")
        return cls.load_image(target_path, size=(1000, max_height))
