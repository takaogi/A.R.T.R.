
import sys
import os
import shutil
import time
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.core.controller import CoreController
from src.modules.character.schema import CharacterProfile
from src.foundation.types import Result

# Mock Config
class MockConfig:
    def __init__(self):
        self.config = MagicMock()
        self.config.memory.conversation_limit = 10
        self.config.memory.thought_limit = 10
        self.config.memory.embedding_provider = "local" # or avoid calling it by mocking MM

async def test_session_init():
    print("Testing Session Initialization...")
    
    test_dir = Path("test_session_output")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    # Setup Paths
    # We need to mock PathManager to return our test_dir
    from src.foundation.paths.manager import PathManager
    
    # Mock singleton instance? 
    # Or just patch the method `get_characters_dir`
    
    # Real PathManager is a Singleton.
    pk = PathManager.get_instance()
    original_char_dir = pk.get_characters_dir
    
    # Override
    pk.get_characters_dir = lambda: test_dir
    
    # 1. Test First Message
    print("\n--- Test 1: First Message ---")
    
    controller = CoreController()
    # We need to init system to set up managers
    # But initialize_system loads config.yaml.
    # Let's mock the managers manually to avoid full system boot overhead/dependencies.
    
    from src.modules.memory.manager import MemoryManager
    
    # Init Managers
    controller.config_manager = MockConfig()
    controller.memory_manager = MemoryManager(controller.config_manager)
    
    # Mock Tool Registry
    mock_registry = MagicMock()
    mock_registry.get_tool.return_value = MagicMock() # Return a mock tool for any get_tool call
    controller.tool_registry = mock_registry
    
    # Don't need real LLM or Tools for this test
    controller._is_initialized = True 
    
    # Create Character
    char_id = "Alice"
    char_dir = test_dir / char_id
    char_dir.mkdir()
    
    profile = CharacterProfile(
        id=char_id,
        name="Alice", 
        first_message="Hello, I am Alice!",
        description="Test"
    )
    
    # Load Character (This triggers the logic)
    await controller.load_character(profile_obj=profile)
    
    # Verification
    history = controller.memory_manager.get_context_history()
    if len(history) == 1 and history[0]['role'] == 'assistant' and history[0]['content'] == "Hello, I am Alice!":
        print("PASS: First message inserted correctly.")
    else:
        print(f"FAIL: History state incorrect. Len={len(history)}")
        print(history)

    # 2. Test Resume (Short Time)
    print("\n--- Test 2: Resume (No Delay) ---")
    
    # Simulate reload
    # We keep the same memory persistence on disk (test_dir/Alice/history.json)
    # But we re-create controller/memory manager to simulate fresh start.
    
    controller2 = CoreController()
    controller2.config_manager = MockConfig()
    controller2.memory_manager = MemoryManager(controller2.config_manager)
    controller2.tool_registry = mock_registry
    controller2._is_initialized = True
    
    # Load again
    await controller2.load_character(profile_obj=profile)
    
    # Logic: "Resume Log" only if time passed?
    # Our implementation: always logs if > 0? 
    # Code: `delta_seconds = current_ts - last_ts`.
    # Since we just ran it, delta is tiny.
    # Code: `if last_ts > 0:` -> logs.
    
    history2 = controller2.memory_manager.get_context_history()
    # Should have: First Msg + "User entered... 0 minutes..."
    if len(history2) >= 2:
        last_entry = history2[-1]
        print(f"Log Entry: {last_entry['content']}")
        if "User entered the room" in last_entry['content']:
             print("PASS: Resume log inserted.")
        else:
             print("FAIL: Resume log missing.")
    else:
        print("FAIL: History length unexpected.")
        print(history2)

    # 3. Test Resume (Simulate Time Pass)
    print("\n--- Test 3: Resume (Time Passed) ---")
    
    # We hack the history file to set timestamp back 2 hours
    hist_path = char_dir / "history.json"
    import json
    with open(hist_path, "r") as f:
        data = json.load(f)
    
    # Hack last timestamp
    last_ts = time.time() - (2.5 * 3600) # 2.5 hours ago
    data['conversations'][-1]['timestamp'] = last_ts
    
    with open(hist_path, "w") as f:
        json.dump(data, f)
        
    # Reload
    controller3 = CoreController()
    controller3.config_manager = MockConfig()
    controller3.memory_manager = MemoryManager(controller3.config_manager)
    controller3.tool_registry = mock_registry
    controller3._is_initialized = True
    
    await controller3.load_character(profile_obj=profile)
    
    history3 = controller3.memory_manager.get_context_history()
    last_entry = history3[-1]
    print(f"Log Entry: {last_entry['content']}")
    
    if "2.5 hours" in last_entry['content']:
        print("PASS: Time calculation correct.")
    else:
        print("FAIL: Time calculation incorrect.")

    # Cleanup
    pk.get_characters_dir = original_char_dir
    # shutil.rmtree(test_dir)
    print("Test Complete.")

if __name__ == "__main__":
    asyncio.run(test_session_init())
