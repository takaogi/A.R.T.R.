from collections import deque
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import time

class MemoryItem(BaseModel):
    role: str
    content: str
    timestamp: float = 0.0
    metadata: Dict[str, Any] = {}

class ShortTermMemory:
    """
    Manages short-term context (Conversation, Thoughts).
    Uses a deque with maxlen to enforce context window window-like behavior.
    """
    def __init__(self, max_items: int = 20):
        self.buffer = deque(maxlen=max_items)
        
    def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        item = MemoryItem(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self.buffer.append(item)
        
    def get_all(self) -> List[MemoryItem]:
        return list(self.buffer)
        
    def clear(self):
        self.buffer.clear()
    
    def get_recent(self, k: int) -> List[MemoryItem]:
        """Get last k items."""
        if k >= len(self.buffer):
            return list(self.buffer)
        # deque slicing is not direct, convert to list
        return list(self.buffer)[-k:]
