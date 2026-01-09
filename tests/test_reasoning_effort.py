import asyncio
import sys
import os
from pathlib import Path
from openai import AsyncOpenAI, OpenAIError

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.utils.logger import logger

from src.utils.llm_client import LLMClient

async def test_value(effort_value: str):
    print(f"\n--- Testing reasoning_effort='{effort_value}' ---")
    
    try:
        # Using LLMClient which handles the base_url logic correctly now
        response = await LLMClient.request_text(
            messages=[{"role": "user", "content": "Hello. Just say hi."}],
            model=settings.OPENAI_MODEL_CORE, # gpt-5-mini
            reasoning_effort=effort_value
        )
        print(f"SUCCESS: '{effort_value}' is accepted.")
        print(f"Response: {response}")
    except OpenAIError as e:
        print(f"FAILED: '{effort_value}' raised an error.")
        print(f"Error: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected exception for '{effort_value}': {e}")

async def main():
    print(f"Model: {settings.OPENAI_MODEL_CORE}")
    
    # Test 'none' (Documented)
    await test_value("none")
    
    # Test 'minimal' (User hypothesis)
    await test_value("minimal")
    
    # Test 'low' (Standard)
    await test_value("low")

if __name__ == "__main__":
    asyncio.run(main())
