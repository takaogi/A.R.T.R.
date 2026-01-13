from typing import Any, Dict, List, Union, Type
from pydantic import BaseModel
from src.modules.llm_client.prompts.base import BaseBuilder
from src.foundation.config import LLMProfile
from .schema import WebSearchResults

class WebSearchSummaryBuilder(BaseBuilder):
    """
    Builder for 'web_search_summary' prompt.
    """
    
    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        query = data.get("query")
        if not query:
            raise ValueError("Missing 'query' in data.")
            
        system_content = """You are an AI search engine. 
Use the provided 'web_search' tool to find the answer.
Provide a direct, concise answer to the query based on the search results.
If you cannot answer, indicate so."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Query: {query}"}
        ]

    def build_schema(self, data: Dict[str, Any], profile: LLMProfile) -> Union[Dict[str, Any], Type[BaseModel]]:
        return WebSearchResults
