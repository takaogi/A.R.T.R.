import json
import os
import random
import uuid
import torch
import numpy as np
from typing import List, Dict, Optional
from src.systems.core.embedding import EmbeddingService
from src.utils.logger import logger

MEMORY_BASE_DIR = "data/characters"

class ArchivalMemory:
    def __init__(self, char_name: str):
        self.char_name = char_name
        self.file_path = os.path.join(MEMORY_BASE_DIR, char_name, "archival_memory.json")
        self.embedding_service = EmbeddingService() # Singleton
        self.memories: List[Dict] = []
        self._load_memories()

    def _load_memories(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data
                logger.info(f"Loaded {len(self.memories)} memories.")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
                self.memories = []
        else:
            self.memories = []

    def save_memories(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memories to {self.file_path}: {e}")

    def add_memory(self, text: str, metadata: Dict = None) -> str:
        """
        Adds a memory. Embedding is computed immediately.
        Returns the ID of the new memory.
        """
        if not text: return None
        
        # Get embedding (1D tensor or numpy)
        # Service returns tensor (CPU), we convert to list for JSON
        embedding_tensor = self.embedding_service.get_embedding(text, mode="passage")
        embedding_list = embedding_tensor.tolist()
            
        mem_id = str(uuid.uuid4())
        entry = {
            "id": mem_id,
            "text": text,
            "metadata": metadata or {},
            "embedding": embedding_list,
            "created_at": str(datetime.now().isoformat()) if 'datetime' in globals() else None 
        }

        self.memories.append(entry)
        self.save_memories()
        logger.info(f"Added memory {mem_id}: {text[:20]}...")
        return mem_id

    def update_memory(self, memory_id: str, content: str):
        """
        Updates memory content. If content is empty, deletes the memory.
        """
        if not content:
            self.delete_memory(memory_id)
            return

        for i, mem in enumerate(self.memories):
            if mem.get("id") == memory_id:
                # Update text and embedding
                mem["text"] = content
                
                embedding_tensor = self.embedding_service.get_embedding(content, mode="passage")
                mem["embedding"] = embedding_tensor.tolist()
                
                self.save_memories()
                logger.info(f"Updated memory {memory_id}.")
                return
        
        logger.warning(f"Memory {memory_id} not found for update.")

    def delete_memory(self, memory_id: str):
        original_len = len(self.memories)
        self.memories = [m for m in self.memories if m.get("id") != memory_id]
        
        if len(self.memories) < original_len:
            self.save_memories()
            logger.info(f"Deleted memory {memory_id}.")
        else:
            logger.warning(f"Memory {memory_id} not found for deletion.")

    def search(self, query_text: str, top_k: int = 3) -> List[Dict]:
        """
        Finds top_k relevant memories for the query.
        """
        if not self.memories:
            return []

        # Get query embedding
        query_tensor = self.embedding_service.get_embedding(query_text, mode="query")
        query_embed = query_tensor.numpy() # Shape (384,)

        # Stack memory embeddings
        # Filter out invalid ones if any
        valid_mems = [m for m in self.memories if "embedding" in m and m["embedding"]]
        if not valid_mems:
            return []
            
        mem_embeds = np.array([m["embedding"] for m in valid_mems]) # Shape (N, 384)
        
        # Calculate Cosine Similarity
        # (A . B) / (|A| * |B|)
        # Assuming Embeddings are already normalized by EmotionAnalyzer?
        # get_embedding does F.normalize(p=2). So length is 1.
        # So we just need Dot Product.
        
        scores = np.dot(mem_embeds, query_embed) # Shape (N,)
        
        # Usage of Mock Mode returns zeros, similarity will be 0.
        
        # Get top K indices
        # argsort is ascending, so we take last k and reverse
        if len(scores) < top_k:
            top_k = len(scores)
            
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.75: # Threshold for relevance?
                # Maybe lenient for now, or use a config.
                # Let's say 0.7 for E5 is usually good similarity.
                # But let's return it and filter in prompt or show score.
                # Let's set a minimal threshold to avoid noise.
                pass 
            
            # If mock mode (score 0), we might want to return random? 
            # Or just return nothing.
            # Or just return nothing.
            if self.embedding_service.mock_mode:
                 # Simple keyword match simulation
                 if query_text in valid_mems[idx]["text"]:
                     score = 1.0
            
            # Simple threshold
            if score > 0.4: # Very loose threshold for testing
                results.append({
                    "memory": valid_mems[idx],
                    "score": score
                })
        
        return results

    def get_random_memories(self, count: int = 3) -> List[Dict]:
        """
        Returns a random selection of memories.
        Useful for simulating spontaneous recollection.
        """
        if not self.memories:
            return []
        
        # If we have fewer memories than requested, return all (shuffled)
        if len(self.memories) <= count:
            shuffled = list(self.memories)
            random.shuffle(shuffled)
            return shuffled
            
        return random.sample(self.memories, count)
