import json
from datetime import datetime
from typing import List, Dict, Optional
from src.utils.path_helper import get_data_dir
from src.utils.logger import logger

class ConversationManager:
    def __init__(self, char_name: str):
        safe_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '-', '_')).strip()
        self.storage_path = get_data_dir() / "characters" / safe_name / "conversation.json"
        
        self.history: List[Dict] = []
        self._ensure_storage()
        self.load()

    def _ensure_storage(self):
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.history = []
            self.save()

    def load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")
                self.history = []

    def save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")

    def add_message(self, role: str, content: str):
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.history.append(message)
        self.save()

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        if limit:
            return self.history[-limit:]
        return self.history

    def clear_history(self):
        self.history = []
        self.save()

    def render_history_text(self, limit: int = 10) -> str:
        """Render recent history as text for prompt."""
        recent = self.get_history(limit)
        lines = []
        for msg in recent:
            # Simple format: "Role: Content"
            # Map role to simpler names if needed
            r = msg['role'].capitalize()
            lines.append(f"{r}: {msg['content']}")
        return "\n".join(lines)
