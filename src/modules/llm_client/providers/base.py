from abc import ABC, abstractmethod
from src.foundation.types import Result
from ..schema import LLMRequest, LLMResponse

class BaseLLMProvider(ABC):
    @abstractmethod
    async def execute(self, request: LLMRequest) -> Result[LLMResponse]:
        pass
