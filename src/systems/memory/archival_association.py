import numpy as np
import torch
from typing import List, Dict
from src.systems.memory.archival_memory import ArchivalMemory
from src.utils.logger import logger

class ArchivalAssociation:
    """
    Wrapper for 'Association' and 'Suggestion' from Archival Memories.
    Used by:
      - Pre-processing Layer (Reacting to user input)
      - Core Thinking Layer (Reacting to tool outputs or internal thoughts)
    """
    def __init__(self, memory_core: ArchivalMemory):
        self.memory_core = memory_core

    def associate(self, text: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieves relevant memories for the given text.
        Args:
            text: Query text (User input or Inner voice).
            top_k: Number of suggestions to return.
        Returns:
            List of memory dicts with scores.
        """
        # We could add logic here to filter out memories that are too old, 
        # or boost certain types of memories. 
        # For now, it's a direct proxy to search.
        results = self.memory_core.search(text, top_k=top_k)
        
        # Log association count for debug
        if results:
            logger.debug(f"ArchivalAssociation found {len(results)} matches.")
            
        return results
        
    def consolidate(self, current_memories: List[Dict], new_memories: List[Dict], context_text: str, limit: int = 10) -> List[Dict]:
        """
        Merges current and new memories, re-ranking them based on relevance to the context_text.
        Used to maintain a fixed-size pool of relevant memories during a conversation.
        """
        # 1. Merge and Deduplicate (by text content)
        # Use a dict keyed by text to ensure uniqueness
        merged_map = {}
        
        for m in current_memories:
            # Handle wrapper dict {memory: {...}, score: ...} or raw dict
            # Standard output from search/associate is {memory: {...}, score: ...}
            mem_data = m.get("memory", m)
            merged_map[mem_data["text"]] = m
            
        for m in new_memories:
            mem_data = m.get("memory", m)
            merged_map[mem_data["text"]] = m
            
        unique_memories = list(merged_map.values())
        
        # 2. Check Limit
        if len(unique_memories) <= limit:
            return unique_memories
            
        # 3. Contextual Re-ranking
        # Get context embedding
        context_embed = self.memory_core.embedding_service.get_embedding(context_text, mode="query")
        if isinstance(context_embed, torch.Tensor):
            context_embed = context_embed.cpu().numpy()
            
        # Calculate similarity for each memory
        scored_memories = []
        for item in unique_memories:
            mem_data = item.get("memory", item)
            # Ensure embedding exists
            if "embedding" not in mem_data or not mem_data["embedding"]:
                # If no embedding (e.g. mock), give low score or keep original?
                # If item has 'score' (from previous search), maybe use that?
                # But here we want context relevance.
                # If mock mode, simulate random score or keyword match
                sim = 0.0
                if self.memory_core.embedding_service.mock_mode:
                    # Simple heuristic: overlap
                    if context_text in mem_data["text"] or any(k in mem_data["text"] for k in ["リンゴ", "合言葉"]):
                         # Simulate relevance if known keywords present
                         sim = 0.9
                    else:
                        sim = 0.1
                elif item.get("score") is not None:
                     # Fallback to existing score if we can't compute new one?
                     # No, that score was for a specific query.
                     sim = 0.0
            else:
                mem_embed = np.array(mem_data["embedding"])
                sim = float(np.dot(mem_embed, context_embed))
                
            scored_memories.append({
                "memory": mem_data,
                "score": sim # New contextual score
            })
            
        # 4. Sort and Slice
        scored_memories.sort(key=lambda x: x["score"], reverse=True)
        return scored_memories[:limit]

    def add_memory(self, text: str, metadata: Dict = None):
        """
        Proxy to add memory (mostly for testing/seeding from Preprocessor context if needed).
        """
        self.memory_core.add_memory(text, metadata)

    def remember_random(self, count: int = 3) -> List[Dict]:
        """
        Recall random memories (spontaneous thought/recollection).
        """
        return self.memory_core.get_random_memories(count)
