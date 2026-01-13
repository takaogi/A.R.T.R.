from typing import List, Dict, Any, Optional

class ConversationFormatter:
    """
    Handles formatting of conversation history for LLM consumption and UI restoration.
    """
    
    def format_for_llm(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formats history for LLM Context.
        - Merges sequential 'thought' and 'assistant' (talk) messages into a single 'assistant' message.
        - Maps 'log' / 'heartbeat' to 'user' messages with prefixes.
        - Preserves 'user' messages as is.
        """
        formatted_messages = []
        
        # Buffer for merging sequential assistant outputs (thoughts and talks)
        # Structure: {'role': 'assistant', 'content': ''}
        current_merge_buffer = None
        
        for item in history:
            role = item.get("role", "unknown")
            content = item.get("content", "")
            
            # --- 1. Handle Assistant-side Roles (Thought / Assistant / Talk) ---
            if role in ["thought", "assistant"]:
                if current_merge_buffer is None:
                    # Start new buffer
                    current_merge_buffer = {"role": "assistant", "content": ""}
                
                # Append content
                if role == "thought":
                    # Wrap thought in tags
                    current_merge_buffer["content"] += f"<thought>{content}</thought>"
                else:
                    # Assistant talk - invoke directly (assuming sanitized)
                    current_merge_buffer["content"] += content
                    
            # --- 2. Handle User-side Roles (User / Log / Heartbeat) ---
            else:
                # If we have a pending buffer, flush it first
                if current_merge_buffer:
                    formatted_messages.append(current_merge_buffer)
                    current_merge_buffer = None
                
                # Process current user item
                if role == "user":
                    formatted_messages.append({"role": "user", "content": content})
                elif role == "log":
                    formatted_messages.append({"role": "user", "content": f"[System Log]: {content}"})
                elif role == "heartbeat":
                    formatted_messages.append({"role": "user", "content": f"[System Event]: {content}"})
                else:
                    # Generic fallback
                    formatted_messages.append({"role": "user", "content": f"[{role}]: {content}"})
        
        # Flush remaining buffer at the end
        if current_merge_buffer:
            formatted_messages.append(current_merge_buffer)
            
        return formatted_messages

    def format_for_restore(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formats history for UI restoration (e.g. Chat Console).
        - Returns ONLY user-visible messages ('user', 'assistant').
        - Filters out 'system', 'log', 'heartbeat', 'thought'.
        """
        restored = []
        for item in history:
            role = item.get("role", "unknown")
            # Filter out internal/system roles
            if role in ["system", "log", "heartbeat", "thought"]:
                continue
            
            # Pass through visible roles
            if role in ["user", "assistant"]:
                restored.append(item.copy())
                
        return restored
