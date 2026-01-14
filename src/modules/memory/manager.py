import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
from src.foundation.config import ConfigManager
from src.foundation.logging import logger
from src.modules.memory.infrastructure.openai_embedding import OpenAIEmbeddingService
from src.modules.memory.infrastructure.chroma_store import ChromaVectorStore
from src.modules.memory.domain.store import SearchResult
from src.modules.memory.organizer import MemoryOrganizer
from src.modules.memory.formatter import ConversationFormatter

class MemoryManager:
    """
    Manages short-term conversation, thoughts, and Long-Term Association Buffer.
    """
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        
        
        # Persistence
        self.persistence_path: Optional[Path] = None
        
        # Volatile Memory
        self.conversations: List[Dict[str, Any]] = []
        self.thoughts: List[Dict[str, Any]] = []
        
        # Association Buffer (Working Memory) - List of SearchResult
        self.association_buffer: List[SearchResult] = []
        
        # Organizer
        self.organizer = MemoryOrganizer()
        
        # Formatter
        self.formatter = ConversationFormatter()
        
        # Long-Term Infrastructure
        try:
            mem_config = self.config.config.memory
            provider = getattr(mem_config, "embedding_provider", "local")
            
            if provider == "local":
                from src.modules.memory.infrastructure.local_embedding import LocalEmbeddingService
                model_name = getattr(mem_config, "local_embedding_model", "intfloat/multilingual-e5-small")
                self.embedding_service = LocalEmbeddingService(model_name=model_name)
                logger.info(f"MemoryManager: Using Local Embedding ({model_name})")
            else:
                self.embedding_service = OpenAIEmbeddingService()
                logger.info("MemoryManager: Using OpenAI Embedding")
                
            self.vector_store = ChromaVectorStore(self.embedding_service)
            self._has_ltm = True
        except Exception as e:
            logger.error(f"MemoryManager: Failed to init LTM: {e}")
            self._has_ltm = False

    def add_interaction(self, role: str, content: str):
        """Adds a dialogue interaction."""
        entry = {"role": role, "content": content, "timestamp": time.time()}
        self.conversations.append(entry)
        self.save_history()

    def add_system_event(self, content: str):
        """Adds a system event (Tool Log)."""
        entry = {"role": "log", "content": content, "timestamp": time.time()}
        self.conversations.append(entry)
        self.save_history()

    def add_heartbeat_event(self, content: str):
        """Adds a heartbeat event (Pacemaker)."""
        entry = {"role": "heartbeat", "content": content, "timestamp": time.time()}
        self.conversations.append(entry)
        self.save_history()

    def add_thought(self, content: str):
        """Adds an internal thought."""
        entry = {"role": "thought", "content": content, "timestamp": time.time()}
        self.thoughts.append(entry)
        self.save_history()

    # --- Persistence ---
    
    def bind_persistence(self, path: Path):
        """Binds memory to a file path and loads existing history."""
        self.persistence_path = path
        self._load_history()

    def _load_history(self):
        """Loads history from JSON."""
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.conversations = data.get("conversations", [])
                self.thoughts = data.get("thoughts", [])
            logger.info(f"MemoryManager: Loaded history from {self.persistence_path}")
        except Exception as e:
            logger.error(f"MemoryManager: Failed to load history: {e}")

    def save_history(self):
        """Saves history to JSON."""
        if not self.persistence_path:
            return

        try:
            # Simple Write
            data = {
                "conversations": self.conversations,
                "thoughts": self.thoughts
            }
            # Ensure directory exists
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"MemoryManager: Failed to save history: {e}")

    def is_empty(self) -> bool:
        """Returns True if no conversations exist."""
        return len(self.conversations) == 0

    def get_last_timestamp(self) -> float:
        """Returns the timestamp of the last interaction or thought."""
        # Check both conversations and thoughts
        last_conv = self.conversations[-1].get("timestamp", 0) if self.conversations else 0
        last_thought = self.thoughts[-1].get("timestamp", 0) if self.thoughts else 0
        return max(last_conv, last_thought)

    def get_context_history(self) -> List[Dict[str, Any]]:
        """Retrieves merged history."""
        mem_config = self.config.config.memory
        conv_limit = mem_config.conversation_limit
        thought_limit = mem_config.thought_limit

        recent_convs = self.conversations[-conv_limit:] if conv_limit > 0 else []
        recent_thoughts = self.thoughts[-thought_limit:] if thought_limit > 0 else []

        merged = recent_convs + recent_thoughts
        merged.sort(key=lambda x: x.get("timestamp", 0))
        return merged

    def get_formatted_history_for_llm(self) -> List[Dict[str, Any]]:
        """
        Returns history formatted for LLM consumption (Merged Thoughts).
        """
        raw_history = self.get_context_history()
        return self.formatter.format_for_llm(raw_history)

    def get_context_text(self, limit: int = 5) -> str:
        """Returns raw text of recent N interactions for query context."""
        recent = self.conversations[-limit:]
        return "\n".join([f"{m['role']}: {m['content']}" for m in recent])

    def get_history_for_restore(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Returns processed history for UI restoration (Chat Console).
        - Filters out thoughts, logs, system events.
        - Merges outputs if needed (handled by formatter).
        """
        raw_history = self.get_context_history()
        # Limit raw history first? No, we filter then limit?
        # Formatter processes everything, then we slice?
        # Better: get_context_history already returns MERGED list (conversations + thoughts).
        # We pass everything to formatter, then take last N.
        
        restored = self.formatter.format_for_restore(raw_history)
        if limit > 0:
            return restored[-limit:]
        return restored

    # --- Association System ---

    def update_associations(self, query_text: str, mode: str = 'input'):
        """
        Updates the Association Buffer based on query.
        mode='input' (Semantic): Uses input + history.
        mode='random' (Pacemaker): Uses random retrieval.
        """
        if not self._has_ltm:
            return

        new_hits = []
        
        if mode == 'random':
            # Pacemaker Mode: Spontaneous Recall
            new_hits = self.vector_store.retrieve_random(count=3)
            logger.debug(f"[Association] Mode: Random. Hits: {len(new_hits)}")
            
            # Implementation of Hybrid Eviction (Pacemaker)
            # 1. Keep Top 2 RELEVANT old items (measured against current context)
            # 2. Add ALL new randoms (up to limit)
            
            if not self.association_buffer:
                self.association_buffer = new_hits
                return

            # Score existing buffer against CURRENT Context (User Input is likely empty if random trigger)
            # Use recent history as context query
            context_query = self.get_context_text(limit=3)
            if not context_query:
                context_query = "current situation"
            
            # We need to re-score buffer manually.
            # Using embedding service to get query vector, then dot product with buffer items?
            # Buffer items are SearchResult, they don't have embeddings attached usually to save space?
            # Chroma SearchResult usually just has ID, Text, Metadata. 
            # We can't re-score easily without re-fetching embeddings or storing them.
            # For efficiency in this script, let's just keep the *most recently added* ones if we can't score?
            # OR: Assume 'score' in buffer is stale.
            # If strictly following Proto2: "Score Existing Buffer against History".
            # This implies we need Embeddings. 
            
            # Workaround: Just keep Top 2 by their *original* score? No, likely irrelevant now.
            # Let's keep randomly 2 old ones? No.
            # Let's keep the *last* 2 added? (Recency).
            # "Hybrid Eviction: Keep Top 2 Relevant".
            # Since we can't easily re-score without cost, let's keep the top 2 from the buffer 
            # assuming the buffer was sorted by relevance to the *previous* state.
            
            # Simple Logic: Keep 2 Old + 3 New Randoms.
            keep_count = 2
            old_kept = self.association_buffer[:keep_count] # Buffer is usually sorted desc by score
            
            # Merge
            # Filter duplicates
            existing_ids = {m.id for m in old_kept}
            final_list = list(old_kept)
            
            for hit in new_hits:
                if hit.id not in existing_ids:
                    final_list.append(hit)
                    existing_ids.add(hit.id)
            
            # Truncate to 5
            self.association_buffer = final_list[:5]
            
        else:
            # Semantic Mode (Input Driven)
            # Query = Recent History (5) + Input
            history_context = self.get_context_text(limit=5)
            full_query = f"{history_context}\nUser Input: {query_text}"
            
            new_hits = self.vector_store.search(full_query, top_k=3)
            logger.debug(f"[Association] Mode: Semantic. Hits: {len(new_hits)}")
            
            # Merge with existing
            # We want to keep the most relevant OVERALL.
            # So we combine lists, unique them, and maybe re-score or just trust new search?
            # Actually, if we search with "Full Query", the new hits ARE the most relevant.
            # But maybe some old buffer items are still relevant?
            # Strategy: Add new hits to buffer. Unique. 
            # If > 5, we technically should re-score all against current query.
            # But the new search only returned Top 3.
            # Maybe the 4th best memory was in the buffer?
            # Safe bet: Just replace buffer with New Hits? 
            # No, we want to accumulate contexts.
            
            # Proto2: "Merge New Hits... Eviction: Re-score Everything if > 5"
            # Since we can't re-score easily (no embeddings), we will:
            # Append new hits to TOP. 
            # Truncate bottom.
            # This assumes New Hits > Old Buffer in relevance.
            
            # Filter duplicates
            existing_ids = {m.id for m in self.association_buffer}
            merged = []
            
            # Add New Hits first (Highest relevance presumably)
            for hit in new_hits:
                merged.append(hit)
                existing_ids.add(hit.id) # track added
            
            # Add Old Buffer items if not duplicates
            for item in self.association_buffer:
                if item.id not in existing_ids: # Using ID to check uniqueness
                     # Note: existing_ids set in this loop includes new_hits IDs
                     # But we need to check if item.id matches any new_hit.id
                     # wait, existing_ids initialized with what? 
                     # Logic fix:
                     pass 
            
            # Proper Merge:
            # 1. New Hits
            final_list = list(new_hits)
            seen_ids = {h.id for h in new_hits}
            
            # 2. Old Buffer (Append remaining)
            for item in self.association_buffer:
                if item.id not in seen_ids:
                    final_list.append(item)
                    seen_ids.add(item.id)
            
            # 3. Truncate
            self.association_buffer = final_list[:5]

            # 3. Truncate
            self.association_buffer = final_list[:5]

    def get_association_context(self) -> List[str]:
        """Returns text list of current associations using Organizer."""
        return self.organizer.format_associations(self.association_buffer)

    # --- LTM Management ---

    def add_memory_to_ltm(self, text: str, metadata: Dict[str, Any] = None, check_deduplication: bool = True) -> Optional[str]:
        """
        Adds memory to Vector Store.
        Supports Deduplication (Similarity Check).
        """
        if not self._has_ltm:
            return None

        if check_deduplication:
            is_dup = self.vector_store.check_similarity(text, threshold=0.85)
            if is_dup:
                logger.info(f"MemoryManager: Skipped duplicate memory: {text[:20]}...")
                return None

        # Add
        ids = self.vector_store.add_documents([text], metadatas=[metadata] if metadata else None)
        return ids[0] if ids else None
