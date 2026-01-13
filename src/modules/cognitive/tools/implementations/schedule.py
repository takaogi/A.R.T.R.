import uuid
from typing import Union, List, Any
from src.modules.llm_client.prompts.cognitive.actions import ScheduleEventAction, CheckScheduleAction, EditScheduleAction
from ..interface import BaseTool
from src.foundation.logging import logger
from src.modules.character.schema import ScheduleEvent

class ScheduleToolMixin:
    """Mixin to handle CharacterStateManager injection."""
    def set_manager(self, manager: Any):
        self.manager = manager

class ScheduleEventTool(BaseTool[ScheduleEventAction], ScheduleToolMixin):
    async def execute(self, action: ScheduleEventAction):
        if not hasattr(self, 'manager'):
             return {"status": "error", "message": "Manager not injected."}
        
        event = ScheduleEvent(
            id=str(uuid.uuid4()),
            title=action.content, # Using content as title for simplicity, or we can parse
            description=action.content,
            start_time=action.date, # YYYY-MM-DD HH:MM
            is_notified=False
        )
        self.manager.add_schedule_event(event)
        
        logger.info(f"[SCHEDULE_ADD] {action.date}: {action.content}")
        return {"status": "success", "message": f"Event '{action.content}' scheduled for {action.date}."}

class CheckScheduleTool(BaseTool[CheckScheduleAction], ScheduleToolMixin):
    async def execute(self, action: CheckScheduleAction):
        if not hasattr(self, 'manager'):
             return {"status": "error", "message": "Manager not injected."}
             
        # List all events? Or just upcoming?
        # For now, list all in state (maybe filter by time if list is long)
        events = self.manager.get_state().schedule
        # Simple format
        results = [f"- [{e.start_time}] {e.title} (Done: {e.is_notified})" for e in events]
        
        logger.info(f"[SCHEDULE_CHECK] Found {len(results)} events.")
        
        if not results:
             return {"status": "success", "results": "No scheduled events."}
             
        return {"status": "success", "results": "\n".join(results)}

class EditScheduleTool(BaseTool[EditScheduleAction], ScheduleToolMixin):
    async def execute(self, action: EditScheduleAction):
        if not hasattr(self, 'manager'):
             return {"status": "error", "message": "Manager not injected."}
        
        # 1. Find Event
        target = self.manager.find_event_by_content(action.target_content)
        if not target:
            return {"status": "error", "message": f"Event matching '{action.target_content}' not found."}
            
        # 2. Delete or Update
        if not action.content:
            # Delete
            if self.manager.remove_schedule_event(target.id):
                 logger.info(f"[SCHEDULE_DELETE] {target.title}")
                 return {"status": "success", "message": f"Event '{target.title}' deleted."}
            return {"status": "error", "message": "Failed to delete event."}
        else:
            # Update
            if self.manager.update_schedule_event(target.id, new_title=action.content, new_desc=action.content):
                logger.info(f"[SCHEDULE_EDIT] {target.title} -> {action.content}")
                return {"status": "success", "message": f"Event updated to '{action.content}'."}
            return {"status": "error", "message": "Failed to update event."}
