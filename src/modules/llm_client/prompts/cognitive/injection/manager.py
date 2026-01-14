from typing import List, NamedTuple

class InjectionRequest(NamedTuple):
    depth: int
    component_key: str
    role: str = "system"  # Default role for injected messages

class InjectionManager:
    """
    Manages the policy for distributed prompt injection.
    Decides 'what' content should be injected at 'which' depth in the conversation history.
    """
    def __init__(self):
        # Configuration for injections
        self._injection_policy = [
            # Zone C: Instructions (Cognitive Process) -> Depth 3
            # User Request: "Cognitive Process" only, at Depth 3.
            InjectionRequest(depth=3, component_key="instruction_block", role="system"),
            
            # Zone C (Response): Schema & Tone -> Depth 3
            # Appears AFTER Cognitive Process (Logical Flow)
            InjectionRequest(depth=3, component_key="response_block", role="system"),
            
            # All other blocks (Context, Language, Tools, Assets, Safety) 
            # are removed from here and will be handled by the Static System Prompt.
        ]

    def get_injection_plan(self, history_length: int) -> List[InjectionRequest]:
        """
        Returns a list of injections applicable for the given history length.
        
        Args:
            history_length: The number of messages in the current history.
            
        Returns:
            List of InjectionRequest objects sorted by depth (deepest first recommended for processing).
        """
        valid_injections = []
        
        for request in self._injection_policy:
            # We allow injections even if history is short (Builder clamps to index 0)
            valid_injections.append(request)
                
        # Sort by depth descending (so inserting from end doesn't mess up indices if processed sequentially)
        # However, builder handles insertion logic, so we just return the plan.
        return valid_injections
