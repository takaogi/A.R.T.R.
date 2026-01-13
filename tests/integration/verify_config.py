import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.foundation.config import ConfigManager

def verify_config():
    print("--- Starting Config Verification ---")
    
    # 1. Initialize Manager
    manager = ConfigManager.get_instance()
    print("[OK] ConfigManager initialized.")
    
    # 2. Load Config
    try:
        config = manager.load_config("config.yaml")
        print(f"[OK] Config loaded successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to load config: {e}")
        return

    # 3. Access Values
    print(f"System Debug Mode: {config.system.debug_mode}")
    print(f"Active Profile: {config.system.active_profile}")
    
    if "gpt-5.2-high" in config.llm_profiles:
        profile = config.llm_profiles["gpt-5.2-high"]
        print(f"Profile 'gpt-5.2-high' Model: {profile.model_name}")
        print(f"Profile 'gpt-5.2-high' Temp: {profile.parameters.temperature}")
    else:
        print("[FAIL] 'gpt-5.2-high' profile not found.")

    # 4. Global Access Check
    manager2 = ConfigManager.get_instance()
    if manager is manager2:
        print("[OK] Singleton pattern verified.")
    else:
        print("[FAIL] Singleton pattern failed.")

if __name__ == "__main__":
    verify_config()
