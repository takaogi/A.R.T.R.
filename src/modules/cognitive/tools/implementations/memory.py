from src.modules.llm_client.prompts.cognitive.actions import RememberAction, RecallAction
from ..interface import BaseTool
from src.modules.memory.manager import MemoryManager
from src.foundation.logging import logger

class RememberTool(BaseTool[RememberAction]):
    def __init__(self, memory_manager: MemoryManager = None):
        self.memory = memory_manager

    def set_memory(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def execute(self, action: RememberAction):
        logger.info(f"[REMEMBER] {action.content}")
        # Use correct API method with Metadata
        from datetime import datetime
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "source": "cognitive_reflection"
        }
        self.memory.add_memory_to_ltm(action.content, metadata=metadata)
        return {"status": "success", "message": "Memory archived."}

class RecallTool(BaseTool[RecallAction]):
    def __init__(self, memory_manager: MemoryManager = None):
        self.memory = memory_manager

    def set_memory(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def execute(self, action: RecallAction):
        logger.info(f"[RECALL] Query: {action.query}")
        results = self.memory.recall(action.query)
        # Format results for LLM consumption
        formatted = [f"- {r.content} (Score: {r.score:.2f})" for r in results]
        return {"status": "success", "results": formatted}
