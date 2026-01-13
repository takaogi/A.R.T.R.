from src.modules.memory.formatter import ConversationFormatter
import json

def test_formatter():
    formatter = ConversationFormatter()
    
    # Test Case 1: Sequential Thought + Talk (Should Merge)
    history_1 = [
        {"role": "user", "content": "Hello"},
        {"role": "thought", "content": "I should say hi back."},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    # Test Case 2: Split Thoughts (Should Merge all into one assistant block)
    history_2 = [
        {"role": "user", "content": "Complex question"},
        {"role": "thought", "content": "Analyzing part 1..."},
        {"role": "thought", "content": "Analyzing part 2..."},
        {"role": "assistant", "content": "Here is the answer."}
    ]
    
    # Test Case 3: Interruption by System Log (Should break merge if strictly ordered, but log is usually user-side)
    # If Log comes after thought but before talk? (Unlikely in engine flow, but possible if queued)
    # Formatter logic: closes buffer on non-assistant role.
    history_3 = [
        {"role": "thought", "content": "Thinking..."},
        {"role": "log", "content": "Tool Result: 42"},
        {"role": "assistant", "content": "The answer is 42."}
    ]
    
    # Test Case 4: Heartbeat (Should be System Event)
    history_4 = [
        {"role": "heartbeat", "content": "Time passed."}
    ]
    
    print("--- Case 1: Merge ---")
    res1 = formatter.format_for_llm(history_1)
    print(json.dumps(res1, indent=2, ensure_ascii=False))
    
    print("\n--- Case 2: Multi-Thought Merge ---")
    res2 = formatter.format_for_llm(history_2)
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    
    print("\n--- Case 3: Interruption ---")
    res3 = formatter.format_for_llm(history_3)
    print(json.dumps(res3, indent=2, ensure_ascii=False))

    print("\n--- Case 4: Heartbeat ---")
    res4 = formatter.format_for_llm(history_4)
    print(json.dumps(res4, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        test_formatter()
        print("\n[SUCCESS] Formatter test ran without errors.")
    except Exception as e:
        print(f"\n[FAILURE] {e}")
