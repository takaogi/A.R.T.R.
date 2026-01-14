from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.foundation.types import Result

class LLMRequest(BaseModel):
    """Internal request object passed to providers."""
    messages: List[Dict[str, Any]]
    model: str
    temperature: float = 1.0
    reasoning_effort: str = "medium"
    json_schema: Optional[Any] = None  # Pydantic model class or dict (Native Structured Output)
    force_json_mode: bool = False      # Enforce {"type": "json_object"} (Generic JSON Mode)
    tools: Optional[List[Dict[str, Any]]] = None
    
    # Connection Overrides
    base_url: Optional[str] = None
    api_key: Optional[str] = None

class LLMResponse(BaseModel):
    """Raw response from provider."""
    content: Any # Str or Dict (if parsed)
    model_name: str
    usage: Dict[str, Any] = Field(default_factory=dict)
