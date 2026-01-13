
import sys
import os

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.modules.llm_client.prompts.cognitive.builder import CognitivePromptBuilder
from src.foundation.config import LLMProfile, LLMCapabilities
from src.modules.character.schema import CharacterProfile

def test_injection_integration():
    print("Testing CognitivePromptBuilder Injection Integration...")
    
    # 1. Setup
    builder = CognitivePromptBuilder()
    
    # Mock Profile - Fixed instantiation
    # LLMProfile(provider: str, model_name: str, ...)
    profile = LLMProfile(
        provider="openai",
        model_name="gpt-4",
        capabilities=LLMCapabilities(is_reasoning=False)
    )
    
    # Mock Data
    char_profile = CharacterProfile(
        name="TestChar",
        surface_persona="Friendly",
        inner_persona="Calculating",
        background_story="Born in testing.",
        speech_patterns=["User shortest words."],
        speech_examples=["Hello."],
        world_definition="A void.",
        initial_situation="Testing."
    )
    
    # History with 5 messages
    history = [
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 3"},
        {"role": "assistant", "content": "Msg 4"},
        {"role": "user", "content": "Msg 5"}
    ]
    
    data = {
        "profile": char_profile,
        "conversation_history": history,
        "rapport_state": {"trust": 0.5, "intimacy": 0.5},
        "current_time": "2025-01-01 12:00"
    }
    
    # 2. Execution (Default - Active Injection)
    # The new InjectionManager has default policy ACTIVE.
    # Depth 4: Context
    # Depth 1: Instruction
    # Depth 0: Response
    
    # We need to ensure the policy is what we expect for this test
    from src.modules.llm_client.prompts.cognitive.injection.manager import InjectionRequest
    
    # Override policy to be sure
    builder.injection_manager._injection_policy = [
        InjectionRequest(depth=4, component_key="context_block", role="system"),
        InjectionRequest(depth=1, component_key="instruction_block", role="system"),
        InjectionRequest(depth=0, component_key="response_block", role="system")
    ]
    
    try:
        messages = builder.build_messages(data, profile)
        print(f"Build successful. Total messages: {len(messages)}")
        
        # Original: System (1) + History (5) = 6
        # Injections: 3
        # Total Expect: 9
        
        # Verify Message Structure
        # Indices in History (Len 5):
        # 0: Msg 1
        # 1: Msg 2
        # 2: Msg 3
        # 3: Msg 4
        # 4: Msg 5
        
        # Target Index Calc:
        # Depth 4 -> 5 - 4 = 1. Insert at 1. 
        #   [M1, INJ_CTX, M2, M3, M4, M5]
        # Depth 1 -> 5 - 1 = 4. Insert at 4 (relative to original?).
        #   Actually insertions shift indices.
        #   Logic: Sorted by depth ASC (0, 1, 4).
        #   Depth 0 (Index 5): Insert at end. 
        #   Depth 1 (Index 4): Insert before last.
        #   Depth 4 (Index 1): Insert after first.
        
        # Let's trace loop:
        # Sorted Plan: Depth 0 (Response), Depth 1 (Instruction), Depth 4 (Context)
        # 1. Depth 0 -> Target Index 5. Insert at 5.
        #    History: [M1, M2, M3, M4, M5, INJ_RESP]
        # 2. Depth 1 -> Target Index 4. Insert at 4.
        #    History: [M1, M2, M3, M4, INJ_INST, M5, INJ_RESP]
        # 3. Depth 4 -> Target Index 1. Insert at 1.
        #    History: [M1, INJ_CTX, M2, M3, M4, INJ_INST, M5, INJ_RESP]
        
        # Final Structure:
        # 0: System
        # 1: M1 (User)
        # 2: INJ_CTX (System)
        # 3: M2 (Assistant)
        # 4: M3 (User)
        # 5: M4 (Assistant)
        # 6: INJ_INST (System)
        # 7: M5 (User)
        # 8: INJ_RESP (System)
        
        assert len(messages) == 9
        print("PASS: Message count matches expectation (9).")
        
        # Verify Roles and Keys
        msg_ctx = messages[2]
        msg_inst = messages[6]
        msg_resp = messages[8]
        
        print(f"Index 2 (Context): {msg_ctx['role']} - {msg_ctx['content'][:20]}...")
        assert msg_ctx['role'] == "system"
        assert "CONTINUUM" in msg_ctx['content']
        
        print(f"Index 6 (Instruction): {msg_inst['role']} - {msg_inst['content'][:20]}...")
        assert msg_inst['role'] == "system"
        assert "Language Protocol" in msg_inst['content']
        
        print(f"Index 8 (Response): {msg_resp['role']} - {msg_resp['content'][:20]}...")
        assert msg_resp['role'] == "system"
        assert "JSON Schema" in msg_resp['content']
        
        print("PASS: All injection blocks verified at correct positions.")

    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_injection_integration()
