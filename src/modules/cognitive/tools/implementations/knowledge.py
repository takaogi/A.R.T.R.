import os
import httpx
from src.modules.llm_client.prompts.cognitive.actions import WebSearchAction
from ..interface import BaseTool
from src.foundation.logging import logger
from src.foundation.config import ConfigManager
from typing import Optional, Any

class WebSearchTool(BaseTool[WebSearchAction]):
    def __init__(self, config_manager: ConfigManager = None, llm_client: Any = None):
        self.config = config_manager
        self.llm_client = llm_client

    def set_config(self, config: ConfigManager):
        self.config = config

    def set_llm_client(self, client: Any):
        self.llm_client = client

    async def execute(self, action: WebSearchAction):
        if not self.config:
            return {"status": "error", "message": "Config not initialized"}

        search_cfg = self.config.config.search
        use_llm = search_cfg.use_llm_search
        
        # 1. Try LLM Search (Natural Language via 'web_search' profile)
        # 1. Try LLM Search (Natural Language via 'web_search' profile)
        if use_llm and self.llm_client:
            try:
                # Resolve Strategy Profile
                override_profile = None
                try:
                    if self.config.config:
                        strategy_name = self.config.config.llm_strategies.get("web_search_summary")
                        if strategy_name:
                            override_profile = self.config.config.llm_profiles.get(strategy_name)
                except Exception as e:
                    logger.warning(f"[WEB_SEARCH] Failed to resolve strategy for web_search_summary: {e}")

                # Execute LLM Basic Search/Answer
                res_llm = await self.llm_client.execute(
                    prompt_name="web_search_summary",
                    data={
                        "query": action.query, 
                        "tools": [{"type": "web_search"}] # Enable Response API Internal Tool
                    },
                    override_profile=override_profile
                )

                if res_llm.success:
                    # Parse
                    from src.modules.llm_client.prompts.web_search_summary.schema import WebSearchResults
                    content = res_llm.data.content
                    
                    found_answer = False
                    answer_text = ""
                    
                    if isinstance(content, WebSearchResults):
                         found_answer = content.found_answer
                         answer_text = content.answer
                    elif isinstance(content, dict):
                         found_answer = content.get("found_answer", False)
                         answer_text = content.get("answer", "")
                    else:
                         # Fallback JSON
                         import json
                         try:
                             d = json.loads(content)
                             found_answer = d.get("found_answer", False)
                             answer_text = d.get("answer", "")
                         except:
                             answer_text = str(content)
                             # Hueristic: If length > 20, assume found?
                             found_answer = True 

                    if found_answer:
                        return {"status": "success", "results": f"[LLM Answer] {answer_text}"}
                    else:
                        logger.info(f"[WEB_SEARCH] LLM could not answer. Fallback to Google.")

                
            except Exception as e:
                logger.error(f"LLM Search failed: {e}")

        # 2. Google Custom Search (Fallback/Primary if LLM search skipped)
        api_key = os.getenv(search_cfg.google_api_key_env)
        cse_id = search_cfg.google_cse_id
        
        if not api_key or not cse_id:
             return {"status": "error", "message": "Google Search API Key or CSE ID missing."}
             
        logger.info(f"[WEB_SEARCH] Google CSE Query: {action.query}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": action.query,
            "num": 3 # Limit results
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("items", [])
                formatted_results = []
                for item in items:
                    title = item.get("title", "No Title")
                    snippet = item.get("snippet", "No Snippet")
                    link = item.get("link", "")
                    formatted_results.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}\n")
                
                if not formatted_results:
                    return {"status": "success", "results": "No results found."}
                    
                return {"status": "success", "results": "\n---\n".join(formatted_results)}
                
        except Exception as e:
            logger.error(f"Google Search Error: {e}")
            return {"status": "error", "message": f"Search failed: {str(e)}"}
