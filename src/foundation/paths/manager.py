import sys
import os
from pathlib import Path
from threading import Lock
from typing import Optional

class PathManager:
    """
    Manages application paths, ensuring compatibility between source run and frozen (exe) mode.
    Singleton to ensure consistent path resolution.
    """
    _instance: Optional['PathManager'] = None
    _lock: Lock = Lock()

    def __init__(self):
        self._root_dir: Path = self._determine_root_dir()

    @classmethod
    def get_instance(cls) -> 'PathManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _determine_root_dir(self) -> Path:
        """
        Determines the application root directory.
        Handles standard python script execution and PyInstaller 'frozen' state.
        """
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            # sys.executable points to the .exe file
            return Path(sys.executable).parent.resolve()
        else:
            # Running as script
            # Assumes this file is in src/foundation/paths/manager.py
            # Root is 3 levels up: src/foundation/paths -> src/foundation -> src -> root
            # Alternatively, use CWD if launched from root (safer for dev)
            return Path(os.getcwd()).resolve()

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    def get_log_dir(self) -> Path:
        path = self._root_dir / "data" / "logs"
        path.mkdir(exist_ok=True)
        return path

    def get_data_dir(self) -> Path:
        path = self._root_dir / "data"
        path.mkdir(exist_ok=True)
        return path

    def get_characters_dir(self) -> Path:
        path = self._root_dir / "characters_data"
        path.mkdir(exist_ok=True)
        return path
        
    def get_models_dir(self) -> Path:
        path = self._root_dir / "data" / "models"
        path.mkdir(exist_ok=True)
        return path

    def get_config_path(self, filename: str = "config.yaml") -> Path:
        return self._root_dir / filename
