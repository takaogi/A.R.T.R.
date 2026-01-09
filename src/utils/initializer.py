import os
import shutil
from pathlib import Path
from src.utils.path_helper import get_base_path, get_data_dir
from src.utils.logger import logger

def initialize_app():
    """
    Perform initial checks and setup for the application.
    - Create necessary directories.
    - Create .env if missing.
    """
    logger.info("Initializing application environment...")
    
    base_path = get_base_path()
    data_dir = get_data_dir()
    
    # 1. Define required directories
    required_dirs = [
        data_dir,
        data_dir / "memories",
        data_dir / "memories" / "archival_chroma",
        data_dir / "white_room",
        data_dir / "characters",
        base_path / "logs",
        base_path / "designs"
    ]
    
    for d in required_dirs:
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {d}")
            except Exception as e:
                logger.error(f"Failed to create directory {d}: {e}")

    # 2. Check .env
    env_path = base_path / ".env"
    if not env_path.exists():
        logger.warning(".env not found. Creating default .env file.")
        create_default_env(env_path)
    else:
        logger.info(".env file found.")

def create_default_env(path: Path):
    """Create a default .env file."""
    content = """# === LLM Provider Settings ===
# Options: "openai", "local"
LLM_PROVIDER=openai

# === OpenAI Settings ===
# Required if LLM_PROVIDER=openai.
OPENAI_API_KEY=

# Core logic models (Smart)
OPENAI_MODEL_CORE=gpt-5-mini
OPENAI_MODEL_TRANSLATOR=gpt-5-mini

# Reflex logic model (Fast)
OPENAI_MODEL_REFLEX=gpt-5-nano

# Reasoning Effort (minimal, low, medium, high)
# Supported by GPT-5 models.
REASONING_EFFORT_REFLEX=minimal
REASONING_EFFORT_CORE=low
REASONING_EFFORT_TRANSLATOR=low

# Embedding model (for Memory System)
EMBEDDING_MODEL=text-embedding-3-small

# === Local LLM Settings ===
# Required if LLM_PROVIDER=local.
# Example for LM Studio: http://localhost:1234/v1
OPENAI_BASE_URL=http://localhost:1234/v1

# === Application Settings ===
# Enable debug logs
DEBUG=True
# Target language for system prompts
LANGUAGE=ja
"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Created default .env at {path}")
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
