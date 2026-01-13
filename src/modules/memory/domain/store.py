from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SearchResult(BaseModel):
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> List[str]:
        """Add documents to the store. Returns list of document IDs."""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search for semantic neighbors."""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]):
        """Delete documents by ID."""
        pass
