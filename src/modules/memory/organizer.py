from typing import List, Dict, Any, Optional
import numpy as np
import time
from datetime import datetime
from src.modules.memory.domain.store import SearchResult, VectorStore
from src.modules.llm_client.client import LLMClient
from src.foundation.logging import logger

class MemoryOrganizer:
    """
    Handles organization and formatting of memories.
    Responsibilities:
    - Relative Time Calculation (Dynamic Tagging)
    - Future: Memory Consolidation, Rewriting, Cleanup
    """
    
    def format_associations(self, memories: List[SearchResult]) -> List[str]:
        """
        Formats association results with dynamic time tags.
        Returns list of strings suitable for prompt injection.
        """
        formatted = []
        for m in memories:
            # Check for timestamp in metadata
            ts = m.metadata.get("timestamp") or m.metadata.get("created_at")
            time_tag = ""
            if ts:
                try:
                    time_tag = self._get_relative_time_tag(float(ts))
                except:
                    pass
            
            # Format: "[Today HH:MM] Memory" or "[Yesterday] Memory"
            prefix = f"[{time_tag}] " if time_tag else ""
            formatted.append(f"{prefix}{m.text} (Score: {m.score:.2f})")
            
        return formatted

    def _get_relative_time_tag(self, timestamp: float) -> str:
        """Calculates relative time tag (Today, Yesterday, etc)."""
        mem_dt = datetime.fromtimestamp(timestamp)
        now_dt = datetime.now()
        
        # Date difference
        today = now_dt.date()
        mem_date = mem_dt.date()
        delta_days = (today - mem_date).days
        
        if delta_days == 0:
            # Today: Show Time
            return f"Today {mem_dt.strftime('%H:%M')}"
        elif delta_days == 1:
            return "Yesterday"
        elif delta_days == 2:
            return "2 Days Ago"
        else:
            # Absolute Date
            return mem_dt.strftime('%Y-%m-%d')

    async def consolidate_memories(self, vector_store: VectorStore, llm_client: LLMClient):
        """
        Scans all archived memories, clusters them by similarity, and merges repetitions.
        Triggered periodically (e.g. daily).
        """
        logger.info("[Organizer] Starting Memory Consolidation...")
        
        # 1. Fetch All (Expensive!)
        # In production, use iterative scan or optimization.
        if hasattr(vector_store, 'get_all'):
            pass # Use get_all
        # Assuming ChromaVectorStore has get_all from previous step
        # But VectorStore abstract base class might not? 
        # We'll assume method exists or cast.
        
        try:
            memories = vector_store.get_all() # List[DistilledMemory]
        except AttributeError:
             logger.warning("[Organizer] VectorStore does not support get_all. Skipping consolidation.")
             return

        if len(memories) < 5:
            return # Too few to consolidate
            
        # 2. Cluster
        # Greedy Clustering
        # Create vectors array
        vectors = np.array([m['embedding'] for m in memories])
        ids = [m['id'] for m in memories]
        
        # Normalize just in case (though embeddings usually normalized)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms
        
        clusters = [] # List[List[index]]
        visited = set()
        
        similarity_threshold = 0.92 # High threshold for duplication
        
        for i in range(len(vectors)):
            if i in visited:
                continue
                
            current_cluster = [i]
            visited.add(i)
            
            # Compare with all others (inefficient O(N^2), but ok for <1000 items)
            # Dot product
            scores = np.dot(vectors, vectors[i])
            
            for j in range(len(vectors)):
                if j in visited:
                    continue
                
                if scores[j] > similarity_threshold:
                    current_cluster.append(j)
                    visited.add(j)
            
            if len(current_cluster) >= 3: # Only consolidate if 3+ items
                clusters.append(current_cluster)
        
        logger.info(f"[Organizer] Found {len(clusters)} clusters for merging.")
        
        # 3. Merge Strategies
        for cluster_indices in clusters:
            cluster_mems = [memories[idx] for idx in cluster_indices]
            
            try:
                # Resolve Strategy Profile
                override_profile = None
                try:
                    from src.foundation.config import ConfigManager
                    config_mgr = ConfigManager.get_instance()
                    if config_mgr._config:
                         strategy_name = config_mgr.config.llm_strategies.get("memory_consolidate")
                         if strategy_name:
                             override_profile = config_mgr.config.llm_profiles.get(strategy_name)
                except Exception as e:
                    logger.warning(f"[Organizer] Failed to resolve strategy for memory_consolidate: {e}")

                # Use LLMClient Standard Execution
                from src.modules.llm_client.prompts.memory_consolidate.schema import ConsolidatedMemory
                
                # Extract texts
                texts = [m['text'] for m in cluster_mems]

                res_llm = await llm_client.execute(
                    prompt_name="memory_consolidate", 
                    data={"memories": texts},
                    override_profile=override_profile
                )
                
                if not res_llm.success:
                    logger.error(f"[Organizer] LLM Consolidation Failed: {res_llm.error}")
                    continue

                # Parse Result
                content = res_llm.data.content
                if isinstance(content, ConsolidatedMemory):
                    new_text = content.consolidated_text
                elif isinstance(content, dict):
                     new_text = content.get("consolidated_text", "")
                else:
                     # Fallback JSON parse
                     import json
                     try:
                         data = json.loads(content)
                         new_text = data.get("consolidated_text", "")
                     except:
                         new_text = str(content) # Fallback to raw string if fail

                if not new_text:
                    logger.warning("[Organizer] Empty consolidation text. Skipping.")
                    continue
                
                # 4. Update Store
                # Add Consolidated
                # Metadata: Consolidate dates? Use range?
                # Use current time as 'consolidated_at'.
                # Maybe keep 'original_created_at' as range string?
                
                timestamps = []
                for m in cluster_mems:
                    ts = m['metadata'].get('timestamp') or m['metadata'].get('created_at')
                    if ts: timestamps.append(ts)
                
                meta = {
                    "type": "consolidated_habit",
                    "source_count": len(cluster_mems),
                    "created_at": time.time()
                }
                
                new_id = vector_store.add_documents([new_text], metadatas=[meta], ids=None)[0]
                
                # Delete Old
                old_ids = [m['id'] for m in cluster_mems]
                vector_store.delete(old_ids)
                
                logger.info(f"[Organizer] Consolidate: Merged {len(old_ids)} items -> '{new_text}'")
                
            except Exception as e:
                logger.error(f"[Organizer] Merge failed for cluster: {e}")
