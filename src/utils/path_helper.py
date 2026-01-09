import sys
import os
from pathlib import Path

def get_base_path() -> Path:
    """
    Get the base path of the application.
    Handles both development environment and PyInstaller frozen environment (_MEIPASS).
    """
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in a normal Python environment
        # Assuming this file is in src/utils/path_helper.py
        # project_root/src/utils/path_helper.py -> project_root
        base_path = Path(__file__).parent.parent.parent.resolve()
    
    return base_path

def get_data_dir() -> Path:
    """Returns the path to the data directory."""
    return get_base_path() / "data"

def get_src_dir() -> Path:
    """Returns the path to the src directory."""
    if getattr(sys, 'frozen', False):
         return get_base_path() / "src"
    else:
         return get_base_path() / "src"

def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to a resource, works for dev and for PyInstaller
    """
    return get_base_path() / relative_path
