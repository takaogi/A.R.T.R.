import sys
import os
import logging as std_logging

# Add project root to path
sys.path.append(os.getcwd())

from src.foundation.config import ConfigManager
from src.foundation.logging import setup_logger, logger

def verify_logging():
    print("--- Starting Logging Verification ---")

    # 1. Load Config
    config_manager = ConfigManager.get_instance()
    config = config_manager.load_config("config.yaml")
    print(f"[OK] Config loaded. Log Level: {config.system.log_level}")

    # 2. Setup Logger
    setup_logger(config)

    # 3. Test Loguru
    logger.debug("This is a DEBUG message from loguru.")
    logger.info("This is an INFO message from loguru.")
    logger.warning("This is a WARNING message from loguru.")
    logger.error("This is an ERROR message from loguru.")

    # 4. Test Standard Logging Interception
    std_logger = std_logging.getLogger("test_std_logger")
    std_logger.info("This is an INFO message from standard logging (should be intercepted).")
    std_logger.warning("This is a WARNING message from standard logging.")

    print("--- Check logs/artr.log for file output ---")

if __name__ == "__main__":
    verify_logging()
