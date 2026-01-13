from src.modules.llm_client.prompts.cognitive.actions import TalkAction, AdjustRapportAction
from ..interface import BaseTool
from src.foundation.logging import logger

class TalkTool(BaseTool[TalkAction]):
    async def execute(self, action: TalkAction):
        # TODO: Integrate with UI/Output System
        logger.info(f"[TALK] {action.content}")
        return {"status": "success", "message": "Spoken"}

class AdjustRapportTool(BaseTool[AdjustRapportAction]):
    def __init__(self):
        self.state_manager = None

    def set_manager(self, manager):
        self.state_manager = manager

    async def execute(self, action: AdjustRapportAction):
        if not self.state_manager:
            logger.warning("[RAPPORT] No StateManager configured. Action ignored.")
            return {"status": "error", "message": "State Manager not available"}

        # Unpack list [trust_delta, intimacy_delta]
        delta = action.rapport_delta
        t_delta = delta[0] if len(delta) > 0 else 0.0
        i_delta = delta[1] if len(delta) > 1 else 0.0

        self.state_manager.update_rapport(
            trust_delta=t_delta,
            intimacy_delta=i_delta
        )

        logger.info(f"[RAPPORT] Delta={action.rapport_delta} Reason={action.reason}")
        return {"status": "success", "message": "Rapport Adjusted"}
