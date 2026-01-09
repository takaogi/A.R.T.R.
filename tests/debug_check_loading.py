import sys
from pathlib import Path
from src.utils.logger import logger

# Add src import path
sys.path.append(str(Path(__file__).parent))

from src.layers.reflex import reflex_layer
from src.systems.core.system_core import SystemCore

def test_character_loading():
    logger.info("--- Testing Character Loading Flow ---")
    
    char_name = "DebugChar"
    
    # 1. Test Reflex Layer Delayed Init
    if reflex_layer.initialized:
        logger.error("Reflex Layer should NOT be initialized by default.")
    else:
        logger.success("Reflex Layer is uninitialized by default.")
        
    logger.info(f"Loading character '{char_name}' into Reflex Layer...")
    try:
        reflex_layer.load_character(char_name)
        if reflex_layer.initialized and reflex_layer.char_name == char_name:
            logger.success("Reflex Layer initialized successfully.")
            logger.error("Reflex Layer failed to initialize state.")
    except Exception as e:
        logger.error(f"Reflex Layer load_character failed: {e}")

    logger.info("--- Starting SystemCore Initialization Test (With Callback) ---")
    
    def test_callback(msg):
        logger.info(f"[UI FEEDBACK] {msg}")

    try:
        # 3. Initialize SystemCore
        # Pass callback to verify it propagates
        core = SystemCore(char_name, progress_callback=test_callback)
        
        logger.success("SystemCore initialized successfully.")
    except Exception as e:
        logger.error(f"SystemCore initialization failed: {e}")

if __name__ == "__main__":
    test_character_loading()
