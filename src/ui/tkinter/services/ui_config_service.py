
import json
import os
from typing import Dict, List, Callable, Any

DEFAULT_CONFIG = {
    "background_color": "#ffffff",
    "typing_speed": 0.02,
    "user_text_color": "#4a90e2",
    "ai_text_color": "#50e3c2",
}

class UIConfigService:
    def __init__(self, config_path: str = "data/ui_config.json"):
        self.config_path = config_path
        self._config = DEFAULT_CONFIG.copy()
        self._observers: List[Callable[[Dict[str, str]], None]] = []
        self._load_config()

    def _load_config(self):
        """Loads configuration from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._config.update(loaded_config)
            except Exception as e:
                print(f"Error loading UI config: {e}")

    def save_config(self):
        """Saves current configuration to file."""
        ensure_dir(os.path.dirname(self.config_path))
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"Error saving UI config: {e}")

    def get_config(self) -> Dict[str, str]:
        return self._config.copy()

    def update_config(self, new_config: Dict[str, str]):
        """Updates configuration and notifies observers."""
        self._config.update(new_config)
        self._notify_observers()

    def subscribe(self, callback: Callable[[Dict[str, str]], None]):
        """Subscribes to layout changes."""
        self._observers.append(callback)
        # Immediately notify new subscriber
        callback(self._config)

    def _notify_observers(self):
        for callback in self._observers:
            callback(self._config)

def ensure_dir(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)
