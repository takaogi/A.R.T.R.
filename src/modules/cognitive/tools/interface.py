from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from src.modules.llm_client.prompts.cognitive.actions import BaseAction

T = TypeVar("T", bound=BaseAction)

class BaseTool(ABC, Generic[T]):
    """
    Abstract Base Class for a Cognitive Tool.
    Handles the execution of a specific Action.
    """
    
    @abstractmethod
    async def execute(self, action: T) -> Any:
        pass
