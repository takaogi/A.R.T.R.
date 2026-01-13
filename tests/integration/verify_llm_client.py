import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.foundation.config import ConfigManager
from src.foundation.logging import setup_logger
from src.modules.llm_client import LLMClient

def verify_llm_client():
    print("--- Starting LLMClient (Refactored) Verification ---")
    
    # 0. Setup
    cm = ConfigManager.get_instance()
    config = cm.load_config("config.yaml")
    setup_logger(config)
    
    client = LLMClient()
    
    # 1. Execute 'echo' prompt
    print("\n[Test 1] Executing 'echo' prompt...")
    # 'echo' prompt requires 'text' key
    res = client.execute("echo", {"text": "Refactoring is fun!"})
    
    if res.success:
        print(f"[SUCCESS] Content: {res.data.content}")
        print(f"[SUCCESS] Model Used: {res.data.model_name}")
    else:
        print(f"[FAIL] Error: {res.error}")
        if "api_key" in str(res.error).lower():
             print("(Expected API Key error)")

    # 2. Test Router/Config (Implicitly tested above, but double check bad prompt)
    print("\n[Test 2] Testing unknown prompt...")
    res_unknown = client.execute("unknown_prompt")
    if not res_unknown.success:
        print(f"[OK] Caught error: {res_unknown.error}")

if __name__ == "__main__":
    verify_llm_client()
