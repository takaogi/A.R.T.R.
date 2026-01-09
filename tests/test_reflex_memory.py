import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.layers.reflex import reflex_layer
from src.systems.memory.conversation import ConversationManager
from src.systems.memory.core_memory import CoreMemoryManager

async def test_reflex_flow():
    print("Testing Reflex Layer Memory Integration...")
    
    # 1. Check Core Memory
    core_mgr = CoreMemoryManager()
    print(f"Core Memory loaded: {len(core_mgr.blocks)} blocks.")
    assert len(core_mgr.blocks) >= 2, "Core Memory should have at least 2 default blocks"
    print("Core Memory check passed.")
    
    # 2. Process Input
    print("Sending input 'こんにちは' to Reflex Layer...")
    # Mock LLMClient to avoid actual API calls if needed, but for now let's hope it fails gracefully or we have API key
    # If no API Key, it might log error but still update conversation history?
    # Actually process_input calls LLMClient.request_text using settings.OPENAI_MODEL_REFLEX.
    # If NO API KEY, LLMClient might raise error. 
    # ReflexLayer catches exception and returns "..."
    
    response = await reflex_layer.process_input("こんにちは")
    print(f"Response: {response}")
    
    # 3. Check Conversation History
    conv_mgr = ConversationManager()
    history = conv_mgr.get_history()
    print(f"Conversation History: {len(history)} messages.")
    
    valid = False
    for msg in history:
        if msg['content'] == "こんにちは" and msg['role'] == "user":
            valid = True
            break
    
    if valid:
        print("Conversation History check passed (User input found).")
    else:
        print("Conversation History check FAILED (User input not found).")
        
    print("Test Complete.")

if __name__ == "__main__":
    asyncio.run(test_reflex_flow())
