import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Dict, Any, List
from pydantic import BaseModel
from src.foundation.config import ConfigManager, LLMProfile
from src.modules.llm_client import LLMClient
from src.foundation.logging import setup_logger, logger

# Mock Builder
class SearchTestBuilder:
    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        return [{"role": "user", "content": data["query"]}]

    def build_schema(self, data: Dict[str, Any], profile: LLMProfile):
        class SearchResult(BaseModel):
            summary: str
            top_fact: str
        return SearchResult

async def verify_web_search():
    # Load Config
    cm = ConfigManager.get_instance()
    cm.load_config()
    setup_logger(cm.config)
    
    logger.info("Initializing Web Search Verification...")

    try:
        # Get 'web_search' profile
        if "web_search" not in cm.config.llm_profiles:
             raise KeyError("web_search profile missing in config")
        profile = cm.config.llm_profiles["web_search"]
        logger.info(f"Target Profile: {profile.provider}/{profile.model_name}")
    except Exception as e:
        logger.error(f"Profile 'web_search' not found: {e}")
        return

    client = LLMClient()
    
    # Test Data: Query that likely requires search
    data = {
        "query": "What is the capital of Japan and what is the current weather there? (Estimate if live search not avail)",
        # Explicitly enabling tool
        "tools": [{"type": "web_search"}]
    }
    
    logger.info("Executing Request...")
    res = await client.execute(
        prompt_name="DEBUG_SEARCH", # Ignored due to override
        data=data,
        override_builder=SearchTestBuilder(),
        override_profile=profile
    )
    
    if res.success:
        logger.info("SUCCESS!")
        logger.info(f"Model: {res.data.model_name}")
        logger.info(f"Content: {res.data.content}")
        # Validate if it looks like JSON (Structured Output)
        logger.info("Check if structured output worked:")
        logger.info(res.data.content)
    else:
        logger.error(f"FAILED: {res.error}")

if __name__ == "__main__":
    asyncio.run(verify_web_search())
