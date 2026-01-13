from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from ...character.schema import CharacterProfile

class PromptContext(BaseModel):
    """
    Data Transfer Object containing all necessary context to build the System Prompt.
    """
    profile: CharacterProfile
    
    # Memory Context (Raw strings or structured objects, prompt manager will format)
    conversation_history: List[Dict[str, Any]] # [{"role": "user", "content": "...", "timestamp": ...}]
    thought_history: List[Dict[str, Any]]      # [{"content": "...", "timestamp": ...}]
    
    # World/Status Context
    current_time: str
    rapport_state: Optional[Dict[str, float]] = None # {"trust": 0.0, "intimacy": 0.0}
    
    # Flags
    is_reasoning_model: bool = False
