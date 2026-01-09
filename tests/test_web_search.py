import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.web_search_client import WebSearchClient
from src.utils.logger import logger
import logging

# Configure logger to show info
logging.basicConfig(level=logging.INFO)

async def test_search():
    client = WebSearchClient()
    logger.info("Initializing WebSearchClient test...")
    
    query = "What is the current weather in Tokyo?"
    logger.info(f"Querying: {query}")
    
    try:
        result = await client.perform_search(query, engine="openai")
        print("\n--- Search Result ---")
        print(result)
        print("---------------------\n")
    except Exception as e:
        logger.error(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
