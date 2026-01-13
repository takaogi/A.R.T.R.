from src.modules.llm_client.prompts.cognitive.actions import GazeAction
from ..interface import BaseTool
from src.foundation.logging import logger

class GazeTool(BaseTool[GazeAction]):
    async def execute(self, action: GazeAction):
        logger.info(f"[GAZE] Target: {action.target}")
        # TODO: Implement Directory/Screen inspection logic
        return {"status": "success", "message": f"Gazed at {action.target}"}
