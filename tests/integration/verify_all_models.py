
import asyncio
import os
import sys
from typing import Dict, Any

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from src.foundation.config.manager import ConfigManager
from src.modules.llm_client.client import LLMClient
from src.modules.llm_client.prompts.character_convert.builder import CharacterConvertBuilder
from src.modules.llm_client.prompts.character_convert.schema import GeneratedProfile

# SAMPLE DATA
RAW_DATA = {
    "name": "Erika",
    "description": "A quiet librarian who loves ancient books. She wears glasses and a cardigan.",
    "personality": "Shy, Introverted, Intellectual. Secretly writes fantasy novels.",
    "first_mes": "Um... are you looking for a specific book? Please keep your voice down.",
    "mes_example": "<START>\nHi\n<END>\n<START>\nSsh!\n<END>",
    "scenario": "The city library at dusk."
}

async def verify_profile(name: str, profile: Any, client: LLMClient, builder: CharacterConvertBuilder) -> Dict[str, Any]:
    print(f"\n>>> TESTING PROFILE: [{name}]")
    print(f"    Model: {profile.model_name}")
    print(f"    Provider: {profile.provider}")
    print(f"    Strict Mode: {profile.capabilities.supports_structured_outputs}")
    
    try:
        result = await client.execute(
            prompt_name="test_verification",
            data={"raw_data": RAW_DATA},
            override_profile=profile,
            override_builder=builder
        )
        
        if not result.success:
            print(f"    [FAILED] Execution Error: {result.error}")
            return {"name": name, "status": "FAIL", "error": str(result.error)}
            
        # Try Parsing
        try:
            profile_data = GeneratedProfile.model_validate_json(result.data.content)
            print(f"    [SUCCESS] Parsed Correctly. Name='{profile_data.name}'")
            return {"name": name, "status": "PASS", "error": None}
        except Exception as e:
            print(f"    [FAILED] Parse Error: {e}")
            print(f"    Raw Content: {result.data.content[:100]}...")
            return {"name": name, "status": "PARSE_ERROR", "error": str(e)}
            
    except Exception as e:
        print(f"    [CRITICAL] Unexpected Exception: {e}")
        return {"name": name, "status": "CRITICAL", "error": str(e)}

async def main():
    load_dotenv()
    
    # Initialize Core Components
    config_mgr = ConfigManager.get_instance()
    # Ensure config loaded (reload to get latest yaml changes)
    config = config_mgr.load_config("config.yaml")
    
    client = LLMClient()
    builder = CharacterConvertBuilder()
    
    results = []
    
    print(f"--- STARTING VERIFICATION OF {len(config.llm_profiles)} MODELS ---")
    
    for pname, profile in config.llm_profiles.items():
        res = await verify_profile(pname, profile, client, builder)
        results.append(res)
        
    print("\n\n=============================================")
    print("       VERIFICATION SUMMARY REPORT")
    print("=============================================")
    for r in results:
        status = r["status"]
        mark = "✅" if status == "PASS" else "❌"
        print(f"{mark} {r['name']:<20} | {status:<12} | {r['error'] or ''}")
    print("=============================================")

if __name__ == "__main__":
    asyncio.run(main())
