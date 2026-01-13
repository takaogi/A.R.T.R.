from typing import Any, Dict, List, Union, Type
from pydantic import BaseModel
from src.modules.llm_client.prompts.base import BaseBuilder
from src.foundation.config import LLMProfile
from .schema import ConsolidatedMemory

class MemoryConsolidateBuilder(BaseBuilder):
    """
    Builder for 'memory_consolidate' prompt.
    Consolidates multiple repetitive memory texts into a single concise fact.
    """
    
    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        memories = data.get("memories", [])
        if not memories:
            raise ValueError("Missing 'memories' list in data.")
            
        texts = [f"- {m}" for m in memories]
        text_block = "\n".join(texts)
        
        system_content = """The following are repetitive AI memories. Consolidate them into a single concise fact identifying the habit or frequency. 
E.g. "I ate toast" x5 -> "I frequently eat toast for breakfast."
Output JSON with 'consolidated_text'. Analysis/Reasoning is NOT required."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": text_block}
        ]

    def build_schema(self, data: Dict[str, Any], profile: LLMProfile) -> Union[Dict[str, Any], Type[BaseModel]]:
        return ConsolidatedMemory
