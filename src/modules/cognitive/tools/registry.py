from typing import Dict, Any
from .interface import BaseTool
from src.modules.llm_client.prompts.cognitive.actions import BaseAction

class ToolRegistry:
    """
    Registry for execution of Cognitive Actions.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, action_type: str, tool: BaseTool):
        self._tools[action_type] = tool

    def get_tool(self, action_type: str) -> BaseTool:
        return self._tools.get(action_type)

    async def execute(self, action: BaseAction) -> Any:
        # action is a Pydantic model with a 'type' field (Literal)
        tool = self._tools.get(action.type)
        if not tool:
            return {"status": "error", "message": f"No tool registered for action type: {action.type}"}
        
        return await tool.execute(action)
