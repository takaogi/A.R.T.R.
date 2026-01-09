from typing import Dict, Any, Callable, Optional, List, Union
from src.utils.logger import logger
from src.systems.memory.core_memory import CoreMemoryManager
from src.systems.memory.archival_memory import ArchivalMemory
from src.systems.memory.conversation import ConversationManager
try:
    from . import schemas
    ActionType = schemas.ActionType
    SCHEMA_AVAILABLE = True
except ImportError:
    SCHEMA_AVAILABLE = False
    ActionType = Any

from src.tools.web_search_client import WebSearchClient

class ToolDispatcher:
    def __init__(self, 
                 core_memory: CoreMemoryManager,
                 archival_memory: ArchivalMemory,
                 conversation: ConversationManager,
                 emotion_callback: Optional[Callable] = None,
                 affection_callback: Optional[Callable] = None
                 ):
        
        self.core_memory = core_memory
        self.archival_memory = archival_memory
        self.conversation = conversation
        self.emotion_callback = emotion_callback
        self.affection_callback = affection_callback
        
        self.web_search_client = WebSearchClient()
        
        # Tool Registry
        self.tools = {
            "wait_for_user": self._tool_wait_for_user,
            "send_message": self._tool_send_message,
            "emotion_update": self._tool_emotion_update,
            "affection_update": self._tool_affection_update,
            "core_memory_append": self._tool_core_memory_append,
            "core_memory_replace": self._tool_core_memory_replace,
            "archival_memory_insert": self._tool_archival_memory_insert,
            "archival_memory_update": self._tool_archival_memory_update,
            "archival_memory_search": self._tool_archival_memory_search,
            "conversation_search": self._tool_conversation_search,
            "web_search": self._tool_web_search,
            "change_vision_focus": self._tool_change_vision_focus,
        }

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool by name with arguments.
        Returns a dictionary containing 'result' (str) and 'heartbeat' (bool).
        """
        if tool_name not in self.tools:
            return {"result": f"Error: Tool '{tool_name}' not found.", "heartbeat": True}
        
        try:
            handler = self.tools[tool_name]
            import inspect
            if inspect.iscoroutinefunction(handler):
                return await handler(**args)
            else:
                return handler(**args)
                
        except Exception as e:
            logger.error(f"Tool execution failed ({tool_name}): {e}")
            return {"result": f"Error executing {tool_name}: {str(e)}", "heartbeat": True}

    async def dispatch_action(self, action: ActionType) -> Dict[str, Any]:
        """
        Executes a strongly-typed Action object from src.tools.schemas.
        """
        if not SCHEMA_AVAILABLE:
            raise ImportError("src.systems.core.tools.schemas not found.")
            
        tool_name = action.tool_name
        params = action.parameters.model_dump()
        
        return await self.execute(tool_name, params)

    # --- Tool Handlers ---

    def _tool_wait_for_user(self):
        """Standard turn end."""
        return {"result": "Waiting for user input.", "heartbeat": False}

    def _tool_send_message(self, content_en: str):
        """Send message to user (queued)."""
        return {"result": f"Message sent: {content_en}", "heartbeat": True, "action": "send_message", "content": content_en}

    def _tool_emotion_update(self, delta_v: float = 0, delta_a: float = 0, delta_d: float = 0, reason: str = ""):
        if self.emotion_callback:
            self.emotion_callback(delta_v, delta_a, delta_d, reason)
            return {"result": f"Emotion updated ({delta_v}, {delta_a}, {delta_d}). Reason: {reason}", "heartbeat": True}
        return {"result": "Emotion System not connected.", "heartbeat": True}

    def _tool_affection_update(self, delta: float, reason: str):
        if self.affection_callback:
            self.affection_callback(delta, reason)
            return {"result": f"Affection updated by {delta}. Reason: {reason}", "heartbeat": True}
        return {"result": "Affection System not connected.", "heartbeat": True}

    def _tool_core_memory_append(self, label: str, content: str):
        self.core_memory.append_to_block(label, content)
        return {"result": f"Appended to Core Memory '{label}'.", "heartbeat": True}

    def _tool_core_memory_replace(self, label: str, old_content: str, new_content: str):
        self.core_memory.replace_content(label, old_content, new_content)
        return {"result": f"Replaced content in Core Memory '{label}'.", "heartbeat": True}

    def _tool_archival_memory_insert(self, content: str):
        mem_id = self.archival_memory.add_memory(content)
        return {"result": f"Memory stored. ID: {mem_id}", "heartbeat": True}

    def _tool_archival_memory_update(self, id: str, content: str):
        self.archival_memory.update_memory(id, content)
        action = "Deleted" if not content else "Updated"
        return {"result": f"Memory {id} {action}.", "heartbeat": True}

    def _tool_archival_memory_search(self, query: str):
        results = self.archival_memory.search(query)
        res_str = "\n".join([f"[{m['score']:.2f}] {m['memory']['text']} (ID: {m['memory'].get('id')})" for m in results])
        if not res_str: res_str = "No relevant memories found."
        return {"result": res_str, "heartbeat": True}

    def _tool_conversation_search(self, query: str, count: int = 10):
        RECENT_MESSAGE_LIMIT = 50
        history = self.conversation.get_history()
        
        if len(history) <= RECENT_MESSAGE_LIMIT:
            return {"result": "History is short; all messages should be in current context.", "heartbeat": True}
            
        target_history = history[:-RECENT_MESSAGE_LIMIT]
        matches = []
        for msg in reversed(target_history):
            if query.lower() in msg['content'].lower():
                matches.append(f"{msg['role']}: {msg['content']}")
                if len(matches) >= count: break
        
        res_str = "\n".join(matches) if matches else "No matches found in older conversation history."
        return {"result": res_str, "heartbeat": True}

    async def _tool_web_search(self, query: str, reason: str, engine: str = "auto"):
         result = await self.web_search_client.perform_search(query, engine)
         return {"result": result, "heartbeat": True}

    def _tool_change_vision_focus(self, path: str):
         return {"result": f"Vision focus changed to {path}.", "heartbeat": True}
