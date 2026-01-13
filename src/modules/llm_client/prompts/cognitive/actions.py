from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

# --- Base Action ---
class BaseAction(BaseModel):
    model_config = ConfigDict(extra='forbid')

# --- Communication ---
class TalkAction(BaseAction):
    type: Literal["talk"]
    content: str = Field(..., description="Content to speak to the user (Japanese). Keep it short (1-3 sentences) and conversational. Split long thoughts.")

class AdjustRapportAction(BaseAction):
    type: Literal["adjust_rapport"]
    rapport_delta: List[float] = Field(..., description="[Trust, Intimacy] delta. e.g. [0.5, 0.1]. Use proactively based on feelings.", min_items=2, max_items=2)
    reason: str = Field(..., description="Reason for the adjustment.")

# --- Memory & Knowledge ---
class RememberAction(BaseAction):
    type: Literal["remember"]
    content: str = Field(..., description="Content to store in archival memory (Long-term). Be proactive and store various details, facts, and observations.")

class RecallAction(BaseAction):
    type: Literal["recall"]
    query: str = Field(..., description="Query to search independent of current conversation.")

class WebSearchAction(BaseAction):
    type: Literal["web_search"]
    query: str = Field(..., description="Search query for real-time information.")

# --- Schedule ---
class ScheduleEventAction(BaseAction):
    type: Literal["schedule_event"]
    content: str = Field(..., description="Event description.")
    date: str = Field(..., description="YYYY-MM-DD HH:MM format.")

class CheckScheduleAction(BaseAction):
    type: Literal["check_schedule"]

class EditScheduleAction(BaseAction):
    type: Literal["edit_schedule"]
    target_content: str = Field(..., description="Original event content to identify.")
    content: Optional[str] = Field(..., description="New content (or None to delete).")

# --- Perception ---
class GazeAction(BaseAction):
    type: Literal["gaze"]
    target: str = Field(..., description="Target object or directory name.(wip)")

# --- Meta-Control ---
class UpdateCoreMemoryAction(BaseAction):
    type: Literal["update_core_memory"]
    section: Literal["overview", "appearance", "personality", "scenario", "user_info"] = Field(..., description="Target section: 'overview' (Description field), 'appearance', 'personality' (Personas), 'scenario', 'user_info'.")
    target_content: str = Field(..., description="Exact string match to replace. If empty (or not found), the new content is Appended.")
    content: str = Field(..., description="New content. For 'user_info', be proactive in recording new details.")

# --- Union Type for Polymorphism ---
Action = Union[
    AdjustRapportAction,
    RememberAction,
    RecallAction,
    WebSearchAction,
    ScheduleEventAction,
    CheckScheduleAction,
    EditScheduleAction,
    GazeAction,
    UpdateCoreMemoryAction
]
