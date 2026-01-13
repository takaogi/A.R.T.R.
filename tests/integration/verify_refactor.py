import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

# Mock Environment for simpler execution if needed
# But we try to rely on current files as much as possible.

try:
    # Attempt imports
    from src.modules.memory.organizer import MemoryOrganizer
    from src.modules.cognitive.tools.implementations.knowledge import WebSearchTool
    from src.modules.llm_client.prompts.cognitive.actions import WebSearchAction
    from src.foundation.config import ConfigManager
    from src.foundation.types.result import Result
    print("[Success] Modules imported successfully.")
except Exception as e:
    print(f"[Fatal Error] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

async def test_organizer():
    print("\n--- Testing Memory Organizer ---")
    
    # Setup Mocks
    llm_client = MagicMock()
    # Mock successful execute result with 'content' object that behaves like a schema model
    mock_content = MagicMock()
    mock_content.consolidated_text = "Consolidated Habit."
    # Also allow it to be a dict or json string for robustness check, but here we test primary path (Schema Object)
    
    mock_result = Result.ok(MagicMock(content=mock_content))
    llm_client.execute = AsyncMock(return_value=mock_result)

    vector_store = MagicMock()
    # Mock input memories
    vector_store.get_all.return_value = [
        {'id': '1', 'text': 'I ate toast', 'embedding': [1.0, 0.0, 0.0], 'metadata': {'created_at': 100}},
        {'id': '2', 'text': 'I ate toast', 'embedding': [0.99, 0.01, 0.0], 'metadata': {'created_at': 101}},
        {'id': '3', 'text': 'I ate toast', 'embedding': [0.98, 0.02, 0.0], 'metadata': {'created_at': 102}},
        {'id': '3b', 'text': 'I ate toast', 'embedding': [0.98, 0.01, 0.01], 'metadata': {'created_at': 102.5}}, # Added for count > 5
        {'id': '4', 'text': 'Unrelated', 'embedding': [0.0, 1.0, 0.0], 'metadata': {'created_at': 103}},
        {'id': '5', 'text': 'Unrelated 2', 'embedding': [0.0, 1.0, 0.1], 'metadata': {'created_at': 104}},
    ]
    vector_store.delete = MagicMock()
    vector_store.add_documents = MagicMock(return_value=['new_id_123'])

    organizer = MemoryOrganizer()
    
    # Mock Config
    config_mock = MagicMock()
    config_mock.config.llm_strategies = {"memory_consolidate": "test_profile_c"}
    config_mock.config.llm_profiles = {"test_profile_c": "PROFILE_OBJ"}
    
    # Patch ConfigManager instance
    original_instance = ConfigManager._instance
    ConfigManager._instance = config_mock

    try:
        await organizer.consolidate_memories(vector_store, llm_client)
        
        # Verify
        if llm_client.execute.called:
            args, kwargs = llm_client.execute.call_args
            print("[Pass] llm_client.execute called.")
            
            p_name = kwargs.get('prompt_name')
            data = kwargs.get('data')
            profile = kwargs.get('override_profile')
            
            if p_name == "memory_consolidate":
                print("[Pass] prompt_name is 'memory_consolidate'")
            else:
                print(f"[Fail] prompt_name is '{p_name}'")
                
            if "memories" in data and len(data["memories"]) >= 3:
                print(f"[Pass] Data contains correct number of memories ({len(data['memories'])} clustered).")
            else:
                print(f"[Fail] Data mismatch: {data}")
                
            if profile == "PROFILE_OBJ":
                print("[Pass] Profile resolved correctly from config.")
            else:
                print(f"[Fail] Profile resolution failed: {profile}")
        else:
            print("[Fail] llm_client.execute was NOT called (Clustering failed?).")
            
    except Exception as e:
        print(f"[Error] Execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ConfigManager._instance = original_instance

async def test_web_search():
    print("\n--- Testing Web Search Tool ---")
    
    llm_client = MagicMock()
    
    # Mock content as Schema Object
    mock_content = MagicMock()
    mock_content.answer = "The answer is 42."
    mock_content.found_answer = True
    
    mock_result = Result.ok(MagicMock(content=mock_content))
    llm_client.execute = AsyncMock(return_value=mock_result)

    config_mgr = MagicMock()
    config_mgr.config.search.use_llm_search = True
    config_mgr.config.search.google_api_key_env = "TEST_KEY"
    config_mgr.config.search.google_cse_id = "TEST_CSE"
    config_mgr.config.llm_strategies = {"web_search_summary": "test_profile_w"}
    config_mgr.config.llm_profiles = {"test_profile_w": "PROFILE_OBJ_W"}

    tool = WebSearchTool(config_manager=config_mgr, llm_client=llm_client)
    
    # Fixed: Provide 'type' field
    action = WebSearchAction(type="web_search", query="Meaning of life")
    
    try:
        result = await tool.execute(action)
        print(f"Tool Result: {result}")
        
        if llm_client.execute.called:
            args, kwargs = llm_client.execute.call_args
            print("[Pass] llm_client.execute called.")
            
            p_name = kwargs.get('prompt_name')
            data = kwargs.get('data')
            
            if p_name == "web_search_summary":
                print("[Pass] prompt_name is 'web_search_summary'")
            else:
                print(f"[Fail] prompt_name is '{p_name}'")
                
            tools = data.get('tools')
            if tools and isinstance(tools, list) and tools[0].get('type') == 'web_search':
                print("[Pass] 'web_search' tool passed in data.")
            else:
                print(f"[Fail] Tools parameter missing or incorrect: {tools}")
                
            if "LLM Answer" in result.get("results", ""):
                 print("[Pass] Result contains LLM answer.")
            else:
                 print(f"[Fail] Result format unexpected: {result}")

        else:
            print("[Fail] llm_client.execute NOT called.")
            
    except Exception as e:
        print(f"[Error] WebSearch execution failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_organizer()
    await test_web_search()

if __name__ == "__main__":
    asyncio.run(main())
