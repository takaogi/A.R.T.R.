
import sys
import os
import uuid
import asyncio
from datetime import datetime

# Fix Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.foundation.logging import logger
from src.modules.character.manager import CharacterStateManager
from src.modules.character.schema import ScheduleEvent

def verify_schedule():
    logger.info("--- Starting Schedule Tool Verification ---")
    
    # 1. Init Manager (Use a test char so we don't mess up main ones)
    test_char = "VerifyScheduleBot"
    manager = CharacterStateManager(test_char)
    
    # Clean up previous
    manager.state.schedule = []
    manager.save_state()
    
    # 2. Add Event
    eid = str(uuid.uuid4())
    evt = ScheduleEvent(
        id=eid,
        title="Existing Meeting",
        description="Discuss Project",
        start_time="2026-01-01 10:00",
        is_notified=False
    )
    manager.add_schedule_event(evt)
    logger.info("Added seed event: Existing Meeting")
    
    # 3. Test Find
    found = manager.find_event_by_content("Existing")
    if found and found.id == eid:
        logger.info("Find Success: Found by 'Existing'")
    else:
        logger.error("Find Failed!")
        return

    # 4. Test Update
    logger.info("Testing Update...")
    updated = manager.update_schedule_event(eid, new_title="Updated Meeting")
    if updated:
        e = manager.find_event_by_content("Updated")
        if e and e.title == "Updated Meeting":
             logger.info("Update Success: Title changed.")
        else:
             logger.error("Update Failed: Event not found or title mismatch.")
    else:
        logger.error("Update Failed: Return false.")
        
    # 5. Test Remove
    logger.info("Testing Remove...")
    removed = manager.remove_schedule_event(eid)
    if removed:
        e = manager.find_event_by_content("Updated")
        if not e:
            logger.info("Remove Success: Event gone.")
        else:
            logger.error("Remove Failed: Event still exists.")
    else:
        logger.error("Remove Failed: Return false.")
        
    # Cleanup (remove directory if empty/temp?) 
    # CharacterStateManager creates dir. We leave it for now.

if __name__ == "__main__":
    verify_schedule()
