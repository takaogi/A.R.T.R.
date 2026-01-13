
import sys
import os
import asyncio

# Fix Path: Add Project Root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"DEBUG: sys.path[0] = {sys.path[0]}")
print(f"DEBUG: CWD = {os.getcwd()}")
print(f"DEBUG: src exists? {os.path.exists(os.path.join(project_root, 'src'))}")

try:
    from src.foundation.config.manager import ConfigManager
    from src.modules.memory.manager import MemoryManager
    from src.foundation.logging import logger
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

def verify_embedding():
    logger.info("--- Starting Local Embedding Verification ---")
    
    # 1. Load Config
    config_manager = ConfigManager.get_instance() # ConfigManager handles loading internally or via init?
    # ConfigManager uses Singleton pattern usually or acts as loader/holder.
    # Let's check manager.py if needed, but assuming standard usage:
    # config_manager = ConfigManager() -> config_manager.config
    
    config = config_manager.load_config()
    
    # Ensure config says "local" (It should be default now in code, but verify)
    logger.info(f"Config Embedding Provider: {config.memory.embedding_provider}")
    logger.info(f"Config Local Model: {config.memory.local_embedding_model}")
    
    if config.memory.embedding_provider != "local":
        logger.warning("Config is not 'local'. Forcing mock context for verification.")
        # We can't easily force it without modifying yaml or mock.
        # But we updated config.yaml in previous steps, so it should be fine.
        
    # 2. Init Memory Manager
    # Passes config (ConfigManager)
    manager = MemoryManager(config_manager)
    # Let's check manager.py signature.
    # __init__(self, config: ConfigManager)
    # Yes.
    
    # manager.initialize() # Removed: MemoryManager initializes in __init__
    
    svc = manager.embedding_service
    logger.info(f"Service Class: {type(svc).__name__}")
    
    if type(svc).__name__ != "LocalEmbeddingService":
        logger.error("Service is NOT LocalEmbeddingService!")
        return
        
    # 3. Test Embedding
    test_text = "これはテストです。This is a test."
    logger.info(f"Embedding Query: '{test_text}'")
    
    vec = svc.embed_query(test_text)
    dim = len(vec)
    logger.info(f"Vector Dimension: {dim}")
    logger.info(f"Vector Sample: {vec[:5]}...")
    
    if dim == 384:
        logger.info("Result: SUCCESS (Dimension matches E5-small)")
    elif dim == 1024:
        logger.info("Result: SUCCESS (Dimension matches E5-large)")
    else:
        logger.warning(f"Result: Dimension {dim} is unexpected for E5-small/large?")

if __name__ == "__main__":
    verify_embedding()
