import logging
import sys
from pathlib import Path
from loguru import logger
from src.foundation.config import AppConfig

class InterceptHandler(logging.Handler):
    """Intercepts standard logging messages and redirects them to loguru."""
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logger(config: AppConfig):
    """
    Configures loguru logger based on AppConfig.
    - Removes default handlers.
    - Adds console handler.
    - Adds file handler with rotation.
    - Intercepts standard logging.
    """
    
    # 1. Remove default handlers
    logger.remove()

    # 2. Determine Log Level
    log_level = config.system.log_level.upper()

    # 3. Add Console Handler
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 4. Add File Handler
    # TODO: Use PathManager in future
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "artr.log"

    logger.add(
        str(log_file),
        rotation="10 MB",
        retention="1 week",
        level=log_level,
        encoding="utf-8"
    )

    # 5. Intercept Standard Logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0) # 0 = NOTSET (capture all)
    
    # Silence overly verbose libraries if needed (example)
    # logging.getLogger("uvicorn").setLevel(logging.WARNING)

    logger.info(f"Logger initialized. Level: {log_level}")
