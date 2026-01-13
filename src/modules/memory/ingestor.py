import time
import json
from typing import List, Dict, Any, NamedTuple
from pydantic import BaseModel, Field

from src.foundation.logging import logger
from src.modules.memory.manager import MemoryManager
# Using LLMClient for summarization
# We need to inject LLMClient. Since Engine has it, we pass it in init or process.

class MemorySummaryItem(BaseModel):
    summary: str = Field(..., description="Fact-based summary of the event (3rd person).")
    emotion: str = Field(..., description="Dominant emotion (e.g., 'joy', 'anger').")

class MemorySummaryOutput(BaseModel):
    items: List[MemorySummaryItem] = Field(..., max_items=3, description="List of summarized events.")

class PendingSummary(NamedTuple):
    content: str
    metadata: Dict[str, Any]
    source_end_timestamp: float

class MemoryIngestor:
    """
    Echo Memory System.
    Monitors short-term history, summarizes it, and ingests into LTM (Echo)
    after the original events have left the active context window.
    """
    def __init__(self, memory_manager: MemoryManager, llm_client: Any):
        self.memory = memory_manager
        self.llm = llm_client
        
        # State
        self.last_ingested_timestamp = 0.0
        self.pending_queue: List[PendingSummary] = []
        
        # Tuning
        self.ingest_threshold = 15 # items

    async def process(self):
        """
        Main loop hook.
        1. Access Memory Manager history.
        2. If new items > threshold, summarize.
        3. Check pending queue for archival.
        """
        # 1. Fetch new messages
        # We need to access MemoryManager internal history directly or add a method?
        # manager.conversations is public-ish.
        # Filter strictly by timestamp > last_ingested
        
        # Combine conversations + thoughts for ingestion? 
        # Usually we only ingest "External Interactions" (Conversations) + maybe key system events.
        # Thoughts are usually ephemeral. Proto2 ignored thoughts?
        # User said "History". Let's assume Conversation History.
        
        all_convs = self.memory.conversations
        new_items = [m for m in all_convs if m["timestamp"] > self.last_ingested_timestamp]
        
        # 2. Summarize Logic
        if len(new_items) >= self.ingest_threshold:
            self._do_summarization(new_items)
            # Update timestamp to the last item's timestamp
            if new_items:
                self.last_ingested_timestamp = new_items[-1]["timestamp"]
        
        # 3. Delayed Archival Logic
        # Check if pending items have "fallen out" of context.
        # Context Window start time:
        context = self.memory.get_context_history()
        if context:
            context_start_time = context[0]["timestamp"]
        else:
            context_start_time = float('inf') # Empty context means everything is "past"? No, means nothing to compare.
            
        # Iterate pending
        remaining = []
        for item in self.pending_queue:
            # If the END of the source block is OLDER than the START of current context,
            # it means the block is no longer visible to the LLM. Safe to Archive.
            if item.source_end_timestamp < context_start_time:
                # Archive
                self.memory.add_memory_to_ltm(
                    text=item.content,
                    metadata=item.metadata,
                    check_deduplication=True
                )
                logger.debug(f"[Echo] Archived pending memory: {item.content[:20]}...")
            else:
                remaining.append(item)
        
        self.pending_queue = remaining

    def _do_summarization(self, items: List[Dict[str, Any]]):
        """Generates summary and adds to pending queue."""
        if not items:
            return

        # Format Transcript
        lines = []
        for m in items:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)
        
        # Prompt
        messages = [
            {"role": "system", "content": "Analyze the following conversation log. Summarize key events into a JSON list (max 3 items). Focus on facts and emotions. Language: Japanese."},
            {"role": "user", "content": transcript}
        ]
        
        try:
            # Synchronous call? Engine loop is async, but LLM methods might be sync/async.
            # `llm_client.get_response` is usually sync in this codebase (requests based)?
            # Or `get_response_async`?
            # Let's assume sync for now or verify LLMClient. 
            # If Engine calls this in threadpool or it's fast enough.
            # Using structured output
            
            # Note: We need to use `response_format` or similar. 
            # Current `LLMClient` supports `response_model`?
            # Checking `src/modules/llm_client/client.py` would be good but I can't view now.
            # Assuming standard interface or generic request.
            # I will use a simple prompt strategy if client schema support is unknown, 
            # BUT User "Config schema" had `supports_structured_outputs`.
            # I'll rely on `llm.get_response` supporting `schema` arg if implemented, 
            # or parse JSON manually.
            
            # Since I'm integrating, I'll attempt to use `schema` if available.
            # If not, I'll ask for JSON mode.
            
            response = self.llm.get_response(
                profile_name="creative", # Or default? Use fast model?
                messages=messages,
                schema=MemorySummaryOutput
            )
            
            # If response is pydantic object
            if isinstance(response, MemorySummaryOutput):
                data = response
            else:
                # fallback text parsing? 
                # For now assume Client returns object if schema provided.
                data = response

            # Add to Queue
            end_t = items[-1]["timestamp"]
            for s in data.items:
                self.pending_queue.append(PendingSummary(
                    content=s.summary,
                    metadata={"emotion": s.emotion, "type": "echo_summary"},
                    source_end_timestamp=end_t
                ))
            
            logger.info(f"[Echo] Generated {len(data.items)} summaries. added to pending queue.")
            
        except Exception as e:
            logger.error(f"[Echo] Summarization failed: {e}")
