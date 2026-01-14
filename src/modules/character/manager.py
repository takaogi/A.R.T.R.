import json
import os
from pathlib import Path
from typing import Optional
from src.foundation.logging import logger
from src.foundation.paths.manager import PathManager
from src.modules.character.schema import CharacterState, ScheduleEvent
from datetime import datetime

class CharacterStateManager:
    """
    Manages the dynamic state of a character (Rapport, Pacemaker, etc.).
    Handles persistence to 'state.json'.
    """

    def __init__(self, character_name: str):
        self.character_name = character_name
        self.paths = PathManager.get_instance()
        self.state_file, self.state = self._load_state()

    def _get_state_path(self) -> Path:
        """Returns the path to state.json for this character."""
        # Assuming character data is in characters_data/{name}/state.json
        char_root = self.paths.get_characters_dir() / self.character_name
        
        if not char_root.exists():
            # If root doesn't exist, we might be using a temp character or uninitialized
            # For now, warn and allow.
            logger.warning(f"Character root not found: {char_root}. Creating...")
            char_root.mkdir(parents=True, exist_ok=True)

        return char_root / "state.json"

    def _load_state(self) -> tuple[Path, CharacterState]:
        """Loads state from file or creates default."""
        path = self._get_state_path()
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return path, CharacterState(**data)
        except Exception as e:
            logger.error(f"Failed to load character state from {path}: {e}")
            # Fallback to default
        
        return path, CharacterState()

    def save_state(self):
        """Persists current state to file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                f.write(self.state.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save character state: {e}")

    # --- Actions ---

    def get_state(self) -> CharacterState:
        return self.state

    def update_rapport(self, trust_delta: float = 0.0, intimacy_delta: float = 0.0):
        """Updates rapport and saves."""
        r = self.state.relationship
        # Clamp values
        r.trust = max(-100.0, min(100.0, r.trust + trust_delta))
        r.intimacy = max(-100.0, min(100.0, r.intimacy + intimacy_delta))
        self.save_state()

    def update_impression(self, output: str):
        """Updates impression memo (optional)."""
        # Could analyze output to update impression? 
        # For now, simple setter if we had one.
        pass

    # New methods can be added here for Pacemaker etc.
    def add_schedule_event(self, event: ScheduleEvent):
        """Adds a scheduled event and saves."""
        self.state.schedule.append(event)
        self.save_state()

    def check_due_events(self) -> list[ScheduleEvent]:
        """
        Checks for unnotified events where start_time <= now.
        Marks them as notified and returns them.
        """
        now = datetime.now()
        due_events = []
        dirty = False
        
        for event in self.state.schedule:
            if not event.is_notified:
                try:
                    # Parse ISO 8601
                    event_time = datetime.fromisoformat(event.start_time)
                    if event_time <= now:
                        event.is_notified = True
                        due_events.append(event)
                        dirty = True
                except ValueError:
                    logger.error(f"Invalid date format for event {event.id}: {event.start_time}")
                    
        if dirty:
            self.save_state()
            
        return due_events

    def set_expression(self, expression: str):
        """Updates the current expression."""
        if expression and expression != self.state.current_expression:
            self.state.current_expression = expression
            self.save_state()

    def update_user_profile(self, info: str):
        """Updates the user profile (Core Memory)."""
        self.state.user_profile = info
        self.save_state()

    # --- Schedule Edit Methods ---
    def find_event_by_content(self, query: str) -> Optional[ScheduleEvent]:
        """Finds the first event containing query in title or description (case-insensitive)."""
        if not query:
            return None
            
        q = query.lower()
        for event in self.state.schedule:
            if q in event.title.lower() or q in event.description.lower():
                return event
        return None

    def remove_schedule_event(self, event_id: str) -> bool:
        """Removes an event by ID."""
        initial_len = len(self.state.schedule)
        self.state.schedule = [e for e in self.state.schedule if e.id != event_id]
        
        if len(self.state.schedule) < initial_len:
            self.save_state()
            return True
        return False

    def update_schedule_event(self, event_id: str, new_title: str = None, new_desc: str = None) -> bool:
        """Updates an event."""
        for event in self.state.schedule:
            if event.id == event_id:
                if new_title: event.title = new_title
                if new_desc: event.description = new_desc
                self.save_state()
                return True
        return False

    def export_character(self, output_path: str) -> bool:
        """Exports the character to .artrcc format at output_path."""
        from src.modules.character.schema import CharacterProfile
        from src.modules.character.artrcc_handler import ARTRCCSaver
        import json
        
        # 1. Load Profile
        char_root = self.paths.get_characters_dir() / self.character_name
        profile_path = char_root / "profile.json"
        
        if not profile_path.exists():
            logger.error(f"Cannot export: profile.json not found for {self.character_name}")
            return False
            
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            profile = CharacterProfile(**data)
            
            # 2. Inject Asset Map (Rebuild from disk to ensure latest)
            assets_dir = char_root / "assets"
            asset_map = {}
            if assets_dir.exists():
                for f in assets_dir.iterdir():
                    if f.is_file():
                        asset_map[f.name] = str(f.absolute())
            profile.asset_map = asset_map
            
            # 3. Save
            res = ARTRCCSaver.save(profile, Path(output_path))
            return res.success
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
