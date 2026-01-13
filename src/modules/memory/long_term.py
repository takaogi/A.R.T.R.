from typing import List, Dict, Any, Optional
from src.modules.memory.domain.store import VectorStore, SearchResult
from src.modules.memory.infrastructure.chroma_store import ChromaVectorStore
from src.modules.memory.infrastructure.embedding_service import E5OnnxEmbeddingService

class LongTermMemory:
    """
    Manages Long-Term / Archival Memory using Vector Store.
    """
    def __init__(self, vector_store: Optional[VectorStore] = None):
        # Default to Chroma+E5 if not provided
        if vector_store is None:
            # We lazy load the embedding service here to avoid heavy init if provided externally?
            # Actually, standard usage should be passing it in, but for convenience:
            embed = E5OnnxEmbeddingService() 
            vector_store = ChromaVectorStore(embedding_service=embed, collection_name="artr_archival")
            
        self.store = vector_store
        
    def save(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Save a text memory to the archive."""
        self.store.add_documents([text], [metadata or {}])
        
    def retrieve(self, query: str, top_k: int = 3, threshold: float = 0.0) -> List[SearchResult]:
        """
        Retrieve relevant memories. 
        Note: Threshold logic depends on score metric (L2 distance or similarity).
        Chroma returns Distance (lower is better).
        E5 Cosine similarity requires conversion or diff approach.
        For now, we just return top_k.
        """
        results = self.store.search(query, top_k=top_k)
        # Filter if meaningful threshold exists?
        # Assuming normalized embeddings and L2, score < ~1.0? 
        return results
