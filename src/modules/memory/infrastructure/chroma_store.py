import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
import numpy as np
from src.foundation.logging import logger
from src.foundation.paths.manager import PathManager
from src.modules.memory.domain.store import VectorStore, SearchResult
from src.modules.memory.domain.embedding import EmbeddingService
from typing import TypedDict

class DistilledMemory(TypedDict):
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]

class ChromaVectorStore(VectorStore):
    def __init__(self, embedding_service: EmbeddingService, collection_name: str = "artr_memory"):
        self.embedding_service = embedding_service
        
        # Initialize Persistent Client
        db_path = PathManager.get_instance().get_data_dir() / "chromadb"
        self.client = chromadb.PersistentClient(path=str(db_path))
        
        # Get or Create Collection
        # We don't pass embedding_function because we handle embeddings manually to support E5 asymmetry
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info(f"ChromaVectorStore initialized at {db_path} (Collection: {collection_name})")

    def add_documents(self, documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> List[str]:
        if not documents:
            return []
            
        count = len(documents)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(count)]
        # metadatas is None is acceptable for Chroma. Do not force empty dicts.
            
        # 1. Generate Embeddings (As "Passage")
        embeddings = self.embedding_service.embed_documents(documents)
        
        # 2. Add to Chroma
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.debug(f"Added {count} documents to memory.")
        return ids

    def search(self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        # 1. Generate Embedding (As "Query")
        query_vec = self.embedding_service.embed_query(query)
        
        # 2. Query Chroma
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            where=filter
        )
        
        # 3. Format Results
        # Chroma returns lists of lists (for multiple queries)
        # results['ids'][0], results['documents'][0], etc.
        
        search_results = []
        if results['ids']:
            ids = results['ids'][0]
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            dists = results['distances'][0] # Chroma returns distances (L2 default) 
            
            for i in range(len(ids)):
                # Convert L2 distance to Score (approx) if needed, or just return distance
                # E5 normalized usually uses Cosine. Chroma default is L2?
                # Normalized vectors L2 is related to Cosine. 
                # Score: Low distance = High similarity.
                
                search_results.append(SearchResult(
                    id=ids[i],
                    text=docs[i] if docs[i] else "",
                    score=dists[i],
                    metadata=metas[i] if metas[i] else {}
                ))
        
        return search_results

    def delete(self, ids: List[str]):
        self.collection.delete(ids=ids)

    def retrieve_random(self, count: int = 3) -> List[SearchResult]:
        """
        Retrieves "random" memories using a random vector query.
        This simulates spontaneous neural firing.
        """
        # 1. Generate Random Vector (Dimension must match model)
        # OpenAI text-embedding-3-small is 1536 dim
        dim = 1536 
        # TODO: Get dim from embedding service? Service API doesn't expose it easily.
        # But we can assume or try to get it. 
        # For now hardcode 1536 or generic approach?
        # Let's generate a vector of appropriate size. 
        # If we fail, Chroma will error.
        
        # Safe approach: Embed a dummy text to get dimension
        dummy_vec = self.embedding_service.embed_query("dummy")
        dim = len(dummy_vec)
        
        # Generate random normalized vector
        rand_vec = np.random.normal(size=dim)
        norm = np.linalg.norm(rand_vec)
        if norm > 0:
            rand_vec = (rand_vec / norm).tolist()
        else:
            rand_vec = rand_vec.tolist()
            
        # 2. Query
        return self.search_by_vector(rand_vec, top_k=count)

    def search_by_vector(self, vector: List[float], top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Performs search using a raw vector."""
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filter
        )
        return self._format_results(results)

    def get_all(self) -> List[DistilledMemory]:    
        """Returns all memories (ID, text, embedding, metadata). Expensive."""
        # Chroma .get() supports include=['embeddings', 'metadatas', 'documents']
        # But limit is default 10? Need to specify larger limit or n_results.
        # Actually .get() is not .query(). .get() retrieves by ID or slice.
        # .get() will return everything if no limit is set? Just set big limit?
        # A.R.T.R expects reasonably sized memories.
        
        data = self.collection.get(include=['embeddings', 'metadatas', 'documents'])
        # data format: {'ids': [], 'embeddings': [], ...}
        
        results = []
        if data['ids']:
            ids = data['ids']
            docs = data['documents']
            metas = data['metadatas']
            embs = data['embeddings']
            
            for i in range(len(ids)):
                results.append({
                    "id": ids[i],
                    "text": docs[i],
                    "embedding": embs[i],
                    "metadata": metas[i]
                })
        return results


    def check_similarity(self, text: str, threshold: float = 0.85) -> bool:
        """
        Checks if a similar text already exists in the store.
        Returns True if max similarity > threshold.
        """
        vector = self.embedding_service.embed_query(text)
        results = self.search_by_vector(vector, top_k=1)
        
        if not results:
            return False
            
        # Chroma returns distance. Convert to similarity?
        # OpenAI embeddings + Cosine Distance:
        # Distance = 1 - CosineSimilarity (usually in Chroma default)
        # So Similarity = 1 - Distance
        # If distance is small, similarity is high.
        # Threshold 0.85 similarity => Distance < 0.15
        
        # Verify Chroma distance metric. Default is 'l2' or 'cosine'?
        # If we didn't specify, default is 'l2' for some versions or 'cosine'.
        # Assuming 'cosine' for text.
        # Let's check similarity carefully.
        
        best_hit = results[0]
        # Assuming distance is Cosine Distance (0 to 2):
        # 0 = Identical
        # If distance < (1 - threshold), then it's a duplicate.
        
        sim_score = 1.0 - best_hit.score # Rough approximation if cosine
        # If l2 (euclidean) on normalized vectors: L2^2 = 2(1-cos)
        # For now, let's treat low score as high similarity.
        
        # Let's assume threshold check:
        # If score (distance) is very low -> Duplicate.
        duplicate_dist = 1.0 - threshold
        if best_hit.score < duplicate_dist:
             logger.debug(f"Duplicate detected: {text[:20]}... matches {best_hit.text[:20]}... (Dist: {best_hit.score:.3f})")
             return True
             
        return False

    def _format_results(self, results) -> List[SearchResult]:
        search_results = []
        if results['ids']:
            ids = results['ids'][0]
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            dists = results['distances'][0]
            
            for i in range(len(ids)):
                search_results.append(SearchResult(
                    id=ids[i],
                    text=docs[i] if docs[i] else "",
                    score=dists[i],
                    metadata=metas[i] if metas[i] else {}
                ))
        return search_results
