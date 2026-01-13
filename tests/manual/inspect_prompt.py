
import sys
import os

# Adjust path to src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock
from src.modules.llm_client.prompts.cognitive.builder import CognitivePromptBuilder
from src.modules.character.schema import CharacterProfile
from src.foundation.config.schema import LLMProfile, LLMCapabilities

def main():
    print("=== Inspecting Cognitive Prompt ===")
    
    # 1. Setup Mocks
    # Character Profile
    char_profile = CharacterProfile(
        name="Aria",
        surface_persona="A helpful assistant.",
        inner_persona="Actually a sophisticated AI.",
        background_story="Created in a lab.",
        speech_patterns=["Speak clearly.", "Use polite Japanese."],
        speech_examples=["Hello.", "How are you?"],
        world_definition="Digital World.",
        initial_situation="Standing by.",
        asset_map={"neutral": "img.png"}
    )
    
    # LLM Profile (Standard)
    llm_profile = LLMProfile(
        provider="openai",
        model_name="gpt-4",
        capabilities=LLMCapabilities(supports_structured_outputs=True)
    )
    
    # Data Bundle
    data = {
        "profile": char_profile,
        "conversation_history": [
            {"role": "user", "content": f"Message {i}"} for i in range(10)
        ],
        "rapport_state": {"trust": 10.0, "intimacy": 5.0},
        "current_time": "2026-01-13 14:00:00",
        "associations": ["Memory A", "Memory B"]
    }
    
    # 2. Build
    builder = CognitivePromptBuilder()
    
    # PATCH: Force Injection Policy to verify content
    from src.modules.llm_client.prompts.cognitive.injection.manager import InjectionRequest
    builder.injection_manager._injection_policy = [
        InjectionRequest(depth=0, component_key="response_block", role="system"),
        InjectionRequest(depth=5, component_key="instruction_block", role="system"),
    ]
    
    messages = builder.build_messages(data, llm_profile)
    
    # 3. Print
    print(f"\nTotal Messages: {len(messages)}")
    for i, msg in enumerate(messages):
        role = msg['role'].upper()
        content = msg['content']
        preview = content[:50].replace('\n', ' ') + "..." if len(content) > 50 else content
        print(f"[{i}] {role}: {preview}")
        
        # If it contains "Cognitive Process", print full
        if "Cognitive Process" in content:
            print("\n--- [Cognitive Process Found] ---")
            print(content)
            print("-------------------------------\n")
            
if __name__ == "__main__":
    main()
