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
        # Format: {'component_key': {'depth': int, 'role': str}}
        # Currently empty as per requirements.
        self._injection_policy = [
            # Example:
            # InjectionRequest(depth=2, component_key="response_instruction", role="system"),
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
            # Basic validation: cannot inject deeper than history exists
            # We allow depth 0 (end) up to history_length (start)
            if request.depth <= history_length:
                valid_injections.append(request)
                
        # Sort by depth descending (so inserting from end doesn't mess up indices if processed sequentially)
        # However, builder handles insertion logic, so we just return the plan.
        return valid_injections
