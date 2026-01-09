import asyncio
import sys
from pathlib import Path

# Add src import path
sys.path.append(str(Path(__file__).parent))

from src.tools.web_search_client import WebSearchClient
from src.systems.core.prompt_builder import PromptBuilder
from src.systems.memory.core_memory import CoreMemoryManager
from src.utils.logger import logger

async def test_search():
    logger.info("--- Web Search Verification ---")
    
    client = WebSearchClient()
    
    # 1. Test Google Mock
    res_google = await client.perform_search("test query", engine="google")
    logger.info(f"Google Result: {res_google}")
    
    if "[Google Search Result]" in res_google:
        logger.success("Google strategy confirmed.")
    else:
        logger.error("Google strategy failed.")

    # 2. Test OpenAI (Mock call expectation or failure)
    # We expect it might fail or return error string if API key invalid/responses API missing
    # But as long as it routes correctly, pass.
    res_openai = await client.perform_search("test query", engine="openai")
    logger.info(f"OpenAI Result: {res_openai}")
    
    # It should not use Google mock
    if "[Google Search Result]" not in res_openai:
        logger.success("OpenAI strategy routing confirmed (output indicates successful attempt or API error).")
    else:
        logger.error("OpenAI strategy incorrectly fell back to Google or returned wrong format.")

def test_prompt_builder():
    logger.info("--- Prompt Builder Verification ---")
    
    cm = CoreMemoryManager("DebugChar")
    pb = PromptBuilder(cm)
    
    # 1. Test OpenAI Mode
    prompt_openai = pb.build_system_prompt(search_engine="openai")
    if "Engine: 5-nano" in prompt_openai:
        logger.success("Prompt built with OpenAI Search Module.")
    else:
        logger.error("Failed to inject OpenAI Search Module.")

    # 2. Test Google Mode
    prompt_google = pb.build_system_prompt(search_engine="google")
    if "Engine: Google Classic" in prompt_google:
        logger.success("Prompt built with Google Search Module.")
    else:
        logger.error("Failed to inject Google Search Module.")

if __name__ == "__main__":
    test_prompt_builder()
    asyncio.run(test_search())
