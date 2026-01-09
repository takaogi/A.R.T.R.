import json
from pathlib import Path
from src.utils.logger import logger
from src.utils.path_helper import get_data_dir

class AffectionManager:
    """
    Manages the user's Affection (Likability/Love) level.
    Affection reflects the long-term relationship depth.
    Range: -100.0 to 100.0
    """
    
    def __init__(self, char_name: str):
        self.char_name = char_name
        self.data_dir = get_data_dir() / "characters" / char_name
        self.file_path = self.data_dir / "affection.json"
        
        self.current = 0.0
        self.max_history = 0.0
        self.history = []
        
        self.load()

    def load(self):
        """Load affection state from disk."""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current = data.get("current", 0.0)
                    self.max_history = data.get("max_history", 0.0)
                    self.history = data.get("history", [])
                logger.info(f"Affection loaded: {self.current} (Max: {self.max_history})")
            except Exception as e:
                logger.error(f"Failed to load affection for {self.char_name}: {e}")
        else:
            logger.info(f"No existing affection file for {self.char_name}. Starting at 0.0.")

    def save(self):
        """Save affection state to disk."""
        data = {
            "current": self.current,
            "max_history": self.max_history,
            "history": self.history[-50:] # Keep last 50 entries
        }
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Affection saved for {self.char_name}.")
        except Exception as e:
            logger.error(f"Failed to save affection for {self.char_name}: {e}")

    def update(self, delta: float, reason: str):
        """
        Update affection by delta.
        Clamp between -100 and 100.
        """
        if delta == 0:
            return

        old_val = self.current
        # Apply update
        self.current += delta
        
        # Clamp
        self.current = max(-100.0, min(100.0, self.current))
        
        # Update Stats
        if self.current > self.max_history:
            self.max_history = self.current
            
        # Log History
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "delta": delta,
            "new_value": self.current,
            "reason": reason
        }
        self.history.append(entry)
        
        logger.info(f"Affection Updated: {old_val:.2f} -> {self.current:.2f} (Delta: {delta}). Reason: {reason}")
        
        self.save()

    def get_level_description(self) -> str:
        """Returns a string description of the current affection level."""
        val = self.current
        if val >= 90: return "Soulmate (Love)"
        if val >= 70: return "In Love"
        if val >= 50: return "Best Friend"
        if val >= 30: return "Close Friend"
        if val >= 10: return "Friend"
        if val >= -10: return "Acquaintance"
        if val >= -30: return "Wary"
        if val >= -50: return "Hostile"
        return "Enemy"

    def get_deep_vad_modifier(self) -> float:
        """
        Returns a scalar (-0.3 to +0.3) to shift Deep VAD Valence based on Affection.
        Affection -100 -> -0.3 shift
        Affection +100 -> +0.3 shift
        """
        return (self.current / 100.0) * 0.3
