import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.path_helper import get_base_path
# Load .env manually to be sure
env_path = get_base_path() / ".env"
load_dotenv(dotenv_path=env_path)

print(f"--- Config Diagnosis ---")
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL')}")
key = os.getenv('OPENAI_API_KEY')
print(f"OPENAI_API_KEY: {key[:8]}... if key else 'None'")
print(f"OPENAI_MODEL_CORE: {os.getenv('OPENAI_MODEL_CORE')}")

if os.getenv("OPENAI_BASE_URL") and "localhost" in os.getenv("OPENAI_BASE_URL"):
    print("\n[WARNING] OPENAI_BASE_URL is set to localhost. If you are using OpenAI Service, this should be empty or commented out.")
