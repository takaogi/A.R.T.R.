import sys
from pathlib import Path
from loguru import logger
from src.utils.path_helper import get_data_dir

# Ensure logs directory exists
LOG_DIR = get_data_dir() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "artr.log"

def setup_logger():
    """
    Sets up the loguru logger config.
    """
    # Remove default handler
    logger.remove()

    # Console Handler (Colorized, Human readable)
    logger.add(
        sys.stdout, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # File Handler (Rotation, Retention, Encoding)
    logger.add(
        LOG_FILE,
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return logger

# Configure globally on import
setup_logger()

# Export 'logger' directly
__all__ = ["logger"]

