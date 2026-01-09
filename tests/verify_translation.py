import asyncio
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.systems.core.system_core import SystemCore
from src.utils.logger import logger

# Configure logger to show info
logging.basicConfig(level=logging.INFO)

async def test_translation():
    char_name = "霧島 雪乃"
    logger.info(f"Initializing SystemCore for {char_name}...")
    
    # Initialize SystemCore
    system = SystemCore(char_name)
    
    # Wait a bit for async init (though SystemCore constructor is mostly sync except for loading specific things maybe?)
    # Actually SystemCore constr is sync, but some internal managers might do threads.
    # But usually for this test it's fine.
    
    # Force High Attention to trigger Core Mode
    logger.info("Boosting Attention to 1.0 to force Core Mode...")
    system.attention_manager.boost(1.0)
    
    user_input = "おはよう。調子はどう？"
    logger.info(f"Sending Input: {user_input}")
    
    try:
        # Process Input
        responses = await system.process_input(user_input)
        
        print("\n--- Final Responses ---")
        for r in responses:
            print(f">> {r}")
        print("-----------------------\n")
        
    except Exception as e:
        logger.error(f"Test Failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_translation())
