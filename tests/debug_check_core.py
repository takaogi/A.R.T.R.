import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock

# Add src to path
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.systems.core.system_core import SystemCore
from src.tools.schemas import CoreResponse, ActionWaitForUser, WaitForUserParams
from src.utils.logger import logger

# Mocking LLMClient before importing/using ReasoningLoop if possible, 
# or patching it.
import src.systems.core.reasoning_loop as reasoning_module

async def main():
    logger.info("--- Starting SystemCore Verification (Mocked LLM) ---")
    
    char_name = "CoreTestChar"
    
    # --- Pre-Verification Setup ---
    # Ensure Dummy Character Exists
    from src.utils.path_helper import get_data_dir
    characters_dir = get_data_dir() / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    
    char_name = "CoreTestChar"
    char_json_path = characters_dir / f"{char_name}.json"
    
    cc_data = {
        "name": char_name,
        "description": "A test character.",
        "personality": "Helpful and logical.",
        "first_mes": "Hello."
    }
    
    import json
    import hashlib
    
    # Calculate Hash exactly as PersonalityManager does
    dump = json.dumps(cc_data, sort_keys=True, ensure_ascii=False)
    char_hash = hashlib.sha256(dump.encode("utf-8")).hexdigest()
    
    # Write Character Data
    with open(char_json_path, "w", encoding="utf-8") as f:
        json.dump(cc_data, f, indent=2, ensure_ascii=False)
            
    # Pre-create Assets to bypass Generation (and nested asyncio.run)
    asset_dir = characters_dir / char_name
    asset_dir.mkdir(parents=True, exist_ok=True)
    
    # Write Metadata
    with open(asset_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({"hash": char_hash}, f, indent=2)
        
    # Write Core Memory XML
    with open(asset_dir / "core_memory.xml", "w", encoding="utf-8") as f:
        f.write('<memory_blocks><block label="persona">Mock Persona</block></memory_blocks>')
        
    # Write Reflex (Empty list)
    with open(asset_dir / "reflex_memory.json", "w", encoding="utf-8") as f:
        json.dump([], f)
        
    # Write Params
    with open(asset_dir / "system_params.json", "w", encoding="utf-8") as f:
        json.dump({
            "pacemaker": {"base_interval_sec": 42, "probability": 0.99},
            "vad_baseline": {"valence": 0.1, "arousal": 0.2, "dominance": 0.3},
            "vad_volatility": {"valence": 1.5, "arousal": 0.5, "dominance": 2.0}
        }, f)

    # Write Reaction Styles
    with open(asset_dir / "reaction_styles.json", "w", encoding="utf-8") as f:
        json.dump({}, f)
    
    logger.info("Pre-created Character assets to bypass generation.")

    # Mock LLMClient GLOBAL PATCH
    # We patch the class method on the actual class from utils
    from src.utils.llm_client import LLMClient
    
    # We need to support both request_text (for Generator) and request_structured (for Core)
    # Mock request_text to return dummy strings
    original_text = LLMClient.request_text
    LLMClient.request_text = AsyncMock(return_value="Mocked Text Response")
    
    # Mock request_structured
    mock_response = CoreResponse(
        internal_monologue="I should wait for the user.",
        actions=[
            ActionWaitForUser(tool_name="wait_for_user", parameters=WaitForUserParams())
        ]
    )
    original_structured = LLMClient.request_structured
    LLMClient.request_structured = AsyncMock(return_value=mock_response)
    
    logger.info("Patched LLMClient globally.")

    try:
        # 1. Initialize SystemCore
        # Now safe to init
        core = SystemCore(char_name)

        # 3. Process Input
        user_input = "Hello, SystemCore."
        
        logger.info(f"Sending input: {user_input}")
        responses = await core.process_input(user_input)
        
        logger.info(f"Responses: {responses}")
        
        if LLMClient.request_structured.called:
            logger.success("ReasoningLoop successfully called LLMClient.")
        else:
            logger.error("LLMClient was NOT called.")
            
    finally:
        # Restore
        LLMClient.request_text = original_text
        LLMClient.request_structured = original_structured
        logger.info("Restored LLMClient.")

if __name__ == "__main__":
    asyncio.run(main())
