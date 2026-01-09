import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.systems.memory.core_memory import CoreMemoryManager
from src.systems.memory.archival_memory import ArchivalMemory
from src.systems.memory.conversation import ConversationManager
from src.systems.core.tools.dispatcher import ToolDispatcher
from src.utils.logger import logger

async def main():
    logger.info("--- Starting Tool Dispatcher Verification ---")
    
    char_name = "ToolTestChar"
    
    # 1. Init Systems
    logger.info("Initializing Systems...")
    try:
        core_mem = CoreMemoryManager(char_name)
        arch_mem = ArchivalMemory(char_name)
        conv_man = ConversationManager(char_name)
        
        # 2. Init Dispatcher
        dispatcher = ToolDispatcher(core_mem, arch_mem, conv_man)
        
        # 3. Test Archival Memory
        logger.info("--- Testing Archival Memory Tools ---")
        res = await dispatcher.execute("archival_memory_insert", {"content": "Test Memory 1"})
        logger.info(f"Insert Res: {res}")
        
        if isinstance(res, dict) and "result" in res:
             import re
             id_match = re.search(r"ID: ([a-f0-9\-]+)", res["result"])
             if id_match:
                 mem_id = id_match.group(1)
                 res = await dispatcher.execute("archival_memory_search", {"query": "Test"})
                 logger.info(f"Search Res: {res}")
                 
                 # Update
                 res = await dispatcher.execute("archival_memory_update", {"id": mem_id, "content": "Updated Memory 1"})
                 logger.info(f"Update Res: {res}")
                 
                 # Delete (Update with empty)
                 res = await dispatcher.execute("archival_memory_update", {"id": mem_id, "content": ""})
                 logger.info(f"Delete Res: {res}")
             else:
                 logger.error("Failed to extract memory ID.")
        
        # 4. Test Core Memory Surgical Replace
        logger.info("--- Testing Core Memory Replace ---")
        core_mem.update_block("persona", "Name: Unit-01\nRole: Assistant")
        block = core_mem.get_block("persona")
        logger.info(f"Initial Persona: {block.value}")
        
        res = await dispatcher.execute("core_memory_replace", {
            "label": "persona", 
            "old_content": "Unit-01", 
            "new_content": "Unit-02"
        })
        logger.info(f"Replace Res: {res}")
        
        block = core_mem.get_block("persona")
        logger.info(f"New Persona Content: {block.value}")
        
        if "Unit-02" in block.value and "Unit-01" not in block.value:
            logger.success("Surgical replacement successful.")
        else:
            logger.error(f"Verification failed. Content: {block.value}")

        # 5. Heartbeat Check
        logger.info("--- Testing Heartbeat ---")
        res = await dispatcher.execute("wait_for_user", {})
        logger.info(f"Wait Res: {res} (Expect Heartbeat False)")
        
        res = await dispatcher.execute("send_message", {"content_en": "Hello"})
        logger.info(f"Send Res: {res} (Expect Heartbeat True)")

        # 6. Schema & Dispatch Action Check
        logger.info("--- Testing Schema Dispatch ---")
        try:
            from src.systems.core.tools.schemas import ActionSendMessage, SendMessageParams
            action_obj = ActionSendMessage(
                tool_name="send_message",
                parameters=SendMessageParams(content_en="Hello from Schema!")
            )
            res = await dispatcher.dispatch_action(action_obj)
            logger.info(f"Schema Dispatch Res: {res}")
            if res.get('content') == "Hello from Schema!":
                logger.success("Schema-based dispatch successful.")
            else:
                logger.error("Schema dispatch content mismatch.")
        except ImportError:
            logger.warning("Schemas module not found, skipping schema test.")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
