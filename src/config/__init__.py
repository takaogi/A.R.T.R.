import os
from pathlib import Path
from dotenv import load_dotenv
from src.utils.path_helper import get_base_path, get_data_dir
from src.utils.constants import APP_NAME, VERSION

# Load .env file
# We look for .env in the project root
env_path = get_base_path() / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    # --- Meta ---
    APP_NAME = APP_NAME
    VERSION = VERSION

    # --- Paths ---
    BASE_PATH = get_base_path()
    DATA_DIR = get_data_dir()
    CHARACTERS_DIR = DATA_DIR / "characters"
    MEMORIES_DIR = DATA_DIR / "memories"
    WHITE_ROOM_DIR_PATH_DEFAULT = DATA_DIR / "white_room"
    
    # --- LLM Settings ---
    # Default to OpenAI if not specified
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai") 
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") # For Local LLM (e.g. http://localhost:1234/v1)
    
    OPENAI_MODEL_REFLEX = os.getenv("OPENAI_MODEL_REFLEX", "gpt-5-nano") # Fast model
    OPENAI_MODEL_CORE = os.getenv("OPENAI_MODEL_CORE", "gpt-5-mini")     # Smart model
    OPENAI_MODEL_TRANSLATOR = os.getenv("OPENAI_MODEL_TRANSLATOR", "gpt-5-mini")
    
    # Reasoning Effort (minimal, low, medium, high)
    # Defaulting Reflex to 'minimal' (speed) and Core to 'medium' (intelligence)
    REASONING_EFFORT_REFLEX = os.getenv("REASONING_EFFORT_REFLEX", "minimal")
    REASONING_EFFORT_CORE = os.getenv("REASONING_EFFORT_CORE", "low")
    REASONING_EFFORT_TRANSLATOR = os.getenv("REASONING_EFFORT_TRANSLATOR", "low")
    # Embedding Model
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # --- System Settings ---
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    LANGUAGE = os.getenv("LANGUAGE", "ja") # Target language for Reflex/Translator
    
    # --- Attention System ---
    ATTENTION_DECAY_RATE = float(os.getenv("ATTENTION_DECAY_RATE", "0.005"))
    ATTENTION_BOOST_DEFAULT = float(os.getenv("ATTENTION_BOOST_DEFAULT", "0.5"))
    ATTENTION_THRESHOLD = float(os.getenv("ATTENTION_THRESHOLD", "0.3"))

    
    def __init__(self):
        # Validation
        if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            # We don't raise error instantly to allow for UI-based setting later, 
            # but usually this is fatal for headless runs.
            pass

settings = Config()

# Export reaction_styles if needed, or just let users import from .reaction_styles
from . import reaction_styles