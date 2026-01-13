from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np
from pydantic import BaseModel

class Embedding(BaseModel):
    vector: List[float]
    model: str
    
class EmbeddingService(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string (for search)."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents (for storage)."""
        pass
