from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from src.foundation.config import LLMProfile
from pydantic import BaseModel

class BaseBuilder(ABC):
    """
    Abstract Base Class for Prompt Strategies.
    Each prompt (e.g., 'story_gen', 'chat') must implement this.
    """

    @abstractmethod
    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        """
        Constructs the list of messages (System, User, etc.) based on data and model profile.
        Allows for model-specific logic (e.g., different system prompt for Local vs OpenAI).
        """
        pass

    @abstractmethod
    def build_schema(self, data: Dict[str, Any], profile: LLMProfile) -> Optional[Union[Dict[str, Any], type[BaseModel]]]:
        """
        Constructs the JSON schema for Structured Outputs.
        Returns None if natural language output is desired.
        """
        pass
