import asyncio
import random
from typing import Callable, Optional, Any
from src.foundation.logging import logger
from src.modules.character.manager import CharacterStateManager

class Pacemaker:
    """
    Manages the autonomous heartbeat loop of the Cognitive Engine.
    Triggered by time intervals defined in the character's state.
    """
    def __init__(self, 
                 state_manager: CharacterStateManager, 
                 callback: Callable[[str], Any]):
        """
        Args:
            state_manager: Source of truth for pulse_interval.
            callback: Async function to call on tick (accepts trigger message).
        """
        self.state_manager = state_manager
        self.callback = callback
        self.running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Starts the pacemaker loop."""
        if self.running:
            return
        self.running = True
        self._consecutive_ticks = 0
        self._current_random_offset = 0.0
        self._task = asyncio.create_task(self._loop())
        logger.info("[Pacemaker] Started.")



    def stop(self):
        """Stops the pacemaker loop."""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("[Pacemaker] Stopped.")

    async def _loop(self):
        """
        Main loop. Checks schedule events.
        """
        while self.running:
            try:
                # 1. Check Schedule (Every loop - 1s precision)
                due_events = self.state_manager.check_due_events()
                for event in due_events:
                    logger.info(f"[Pacemaker] Triggering Scheduled Event: {event.title}")
                    if self.callback:
                        try:
                            msg = f"Scheduled Event '{event.title}' is starting now. ({event.description})"
                            await self.callback(msg)
                        except Exception as cb_err:
                            logger.error(f"[Pacemaker] Callback error (Schedule): {cb_err}")

                # 2. Sleep (Precision 1s)
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Pacemaker] Error in loop: {e}")
                await asyncio.sleep(5.0) # Backoff on error
