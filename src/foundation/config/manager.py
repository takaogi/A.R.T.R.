import os
import yaml
from threading import Lock
from typing import Optional
from dotenv import load_dotenv  # Add this import
from .schema import AppConfig

class ConfigManager:
    """Singleton Manager for loading and accessing AppConfig."""
    _instance: Optional['ConfigManager'] = None
    _lock: Lock = Lock()

    def __init__(self):
        self._config: Optional[AppConfig] = None

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load_config(self, config_path: str = "config.yaml") -> AppConfig:
        """Loads configuration from a YAML file."""
        # Load environment variables from .env file
        load_dotenv()
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f) or {}
            
            # Validate with Pydantic
            self._config = AppConfig(**raw_data)
            return self._config
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    @property
    def config(self) -> AppConfig:
        if self._config is None:
             raise RuntimeError("Configuration has not been loaded. Call load_config() first.")
        return self._config
