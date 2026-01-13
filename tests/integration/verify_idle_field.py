
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Mock heavy dependencies BEFORE importing engine
sys.modules["chromadb"] = MagicMock()
sys.modules["src.foundation.config"] = MagicMock()
# Mock Memory Manager dependencies to avoid Import Errors
sys.modules["src.modules.memory.infrastructure.chroma_store"] = MagicMock()

# Adjust path to src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now import
try:
    from src.modules.cognitive.engine import CognitiveEngine
    from src.modules.llm_client.prompts.cognitive.schema import CognitiveResponse, Action
except ImportError as e:
    print(f"Import Error even with mocks: {e}")
    # Fallback: We might need to mock more
    sys.exit(1)

async def main():
    print("=== Testing Idle Field Logic ===")
    
    # Mocks
    mock_llm = MagicMock()
    mock_tools = MagicMock()
    mock_profile = MagicMock()
    mock_config = MagicMock()
    mock_memory = MagicMock()
    mock_state = MagicMock()
    
    # Setup State (Pacemaker Config)
    mock_stat = MagicMock()
    mock_stat.pacemaker.auto_max_consecutive = 5 # Small limit for test
    mock_state.get_state.return_value = mock_stat
    
    mock_memory.get_context_history.return_value = []
    mock_memory.get_formatted_history_for_llm.return_value = []
    mock_memory.get_association_context.return_value = []
    
    # --- Sequence 1: Idle=0 (Continue) x2, then Idle=10 (Wait) ---
    response_continue = CognitiveResponse(
        system_analysis="Analysis",
        thought="Thinking...",
        actions=[],
        talk="Still thinking...",
        show_expression="neutral",
        idle=0.0
    )
    
    response_wait = CognitiveResponse(
        system_analysis="Analysis",
        thought="Waiting...",
        actions=[],
        talk="Waiting now.",
        show_expression="neutral",
        idle=10.0
    )
    
    r1 = MagicMock(); r1.success=True; r1.data.content = response_continue.model_dump_json()
    r2 = MagicMock(); r2.success=True; r2.data.content = response_continue.model_dump_json()
    r3 = MagicMock(); r3.success=True; r3.data.content = response_wait.model_dump_json()
    
    mock_llm.execute = AsyncMock(side_effect=[r1, r2, r3])
    mock_tools.execute = AsyncMock(return_value={"status": "success"})
    
    # Init Engine
    engine = CognitiveEngine(mock_llm, mock_tools, mock_profile, mock_config, mock_memory, mock_state)
    engine.trigger_system_event = AsyncMock()
    
    # Run
    print("Running Cognitive Loop (Idle Logic)...")
    await engine._run_cognitive_loop(trigger="test")
    
    # Verify
    print(f"Loop finished. LLM Executions: {mock_llm.execute.call_count}")
    
    if mock_llm.execute.call_count == 3:
        print("[PASS] Engine looped 3 times.")
        
        # Verify Ephemeral Message Injection in the FIRST call
        # Call args: (prompt_name="cognitive", data={...})
        # Check data['conversation_history']
        first_call_args = mock_llm.execute.call_args_list[0]
        # execute(prompt_name=..., data=...)
        # We need to find 'data' arg. It is likely kwargs.
        kwargs = first_call_args.kwargs
        data = kwargs.get('data')
        history = data.get('conversation_history', [])
        
        # We expect [System]: Continue thinking... at the end?
        # Since mock_memory returns [], it should be the ONLY message.
        if history and "Continue thinking" in history[-1]['content']:
             print("[PASS] Ephemeral 'Continue thinking' message injected.")
        else:
             print("[FAIL] Ephemeral message missing or incorrect.")
             print(f"History: {history}")
    else:
        print(f"[FAIL] Expected 3 calls, got {mock_llm.execute.call_count}")

    if engine._wakeup_task:
        print("[PASS] Wakeup task created.")
        engine._wakeup_task.cancel()
    else:
        print("[FAIL] Wakeup task NOT created.")

    # --- Test 2: Max Consecutive ---
    print("\n--- Testing Max Consecutive Limit ---")
    mock_llm.execute.reset_mock()
    engine._wakeup_task = None
    
    # Infinite loop
    r_inf = MagicMock(); r_inf.success=True; r_inf.data.content = response_continue.model_dump_json()
    mock_llm.execute = AsyncMock(return_value=r_inf)
    
    await engine._run_cognitive_loop(trigger="test")
    
    print(f"Loop finished. LLM Executions: {mock_llm.execute.call_count}")
    
    if mock_llm.execute.call_count == 5:
        print("[PASS] Engine stopped at limit (5).")
    else:
        print(f"[FAIL] Expected 5 calls, got {mock_llm.execute.call_count}")
        
    
    if engine._wakeup_task:
        print("[PASS] Wakeup task created (Force Wait).")
        # Test Interruption by System Event
        print("\n--- Testing System Event Interruption ---")
        task = engine._wakeup_task
        # It's a real task, we can't easily mock valid property unless we mock create_task.
        # But we can verify if it gets cancelled.
        # Call trigger_system_event while task is running.
        
        # Reset mock_llm for this new run
        mock_llm.execute.reset_mock()
        mock_llm.execute.return_value = MagicMock(success=True, data=MagicMock(content=response_continue.model_dump_json()))

        # RESTORE real trigger_system_event to test logic
        # We need to un-mock it.
        # Since we set it on the instance 'engine.trigger_system_event = AsyncMock()', we can just delete it from dict?
        del engine.trigger_system_event
        # Assuming the class method is still there. 
        
        await engine.trigger_system_event("Test Schedule Event")
        
        if task.cancelled():
            print("[PASS] Previous wakeup task was CANCELLED by System Event.")
        else:
            # Note: task.cancel() schedules cancellation. detailed check might be needed.
            # But usually cancelled() returns True immediately after cancel() is called? 
            # No, strictly speaking it depends on loop. But let's check.
            # If not, we might need simple await asyncio.sleep(0) to let loop process.
            await asyncio.sleep(0)
            if task.cancelled():
                 print("[PASS] Previous wakeup task was CANCELLED by System Event (after yield).")
            else:
                 print(f"[FAIL] Wakeup task NOT cancelled. Done state: {task.done()}")
        
    else:
        print("[FAIL] Wakeup task NOT created on limit.")
        
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(main())
