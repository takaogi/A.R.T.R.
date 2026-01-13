
import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.foundation.config import ConfigManager
from src.modules.llm_client.client import LLMClient
from src.modules.character.creator import CharacterCreatorService

async def verify_creator():
    # Setup
    handler = logging.StreamHandler()
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    
    config = ConfigManager.get_instance()
    config.load_config("config.yaml")
    
    llm = LLMClient()
    creator = CharacterCreatorService(config, llm)
    
    print("\n--- Test 1: Creation from Raw Text ---")
    raw_text = "Name: Test-Chan. Personality: Types like a hacker. Likes energy drinks."
    profile = await creator.generate_profile(raw_text)
    if profile:
        print(f"Success! Name: {profile.name}")
        print(f"Persona: {profile.surface_persona}")
    else:
        print("Failed.")

    print("\n--- Test 2: Refinement (Partial Update) ---")
    if profile:
        current_data = profile.model_dump()
        # Simulate user changing description or asking for better personality
        instruction = "Add 'Tsundere' to personality traits."
        
        refined = await creator.generate_profile(instruction, existing_profile=current_data)
        if refined:
            print(f"Success! Name: {refined.name}")
            print(f"Refined Persona: {refined.surface_persona}")
            # print(f"Raw: {refined.model_dump_json(indent=2)}")
        else:
            print("Refinement Failed.")

if __name__ == "__main__":
    asyncio.run(verify_creator())
