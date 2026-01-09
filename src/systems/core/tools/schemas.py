from typing import List, Literal, Union, Optional
from pydantic import BaseModel, Field

# --- Tool Parameter Models ---

class WaitForUserParams(BaseModel):
    pass

class SendMessageParams(BaseModel):
    content_en: str = Field(..., description="Message to user in English.")

class EmotionUpdateParams(BaseModel):
    delta_v: float = Field(..., ge=-1.0, le=1.0, description="Valence shift")
    delta_a: float = Field(..., ge=-1.0, le=1.0, description="Arousal shift")
    delta_d: float = Field(..., ge=-1.0, le=1.0, description="Dominance shift")
    reason: str = Field(..., description="Reason for the shift")

class AffectionUpdateParams(BaseModel):
    delta: float = Field(..., ge=-10.0, le=10.0, description="Affection shift")
    reason: str = Field(..., description="Reason for the shift")

class CoreMemoryAppendParams(BaseModel):
    label: str = Field(..., description="Target block label (e.g., 'human')")
    content: str = Field(..., description="Content to append")

class CoreMemoryReplaceParams(BaseModel):
    label: str = Field(..., description="Target block label")
    old_content: str = Field(..., description="Segment to replace (must match exactly)")
    new_content: str = Field(..., description="New content")

class ArchivalMemoryInsertParams(BaseModel):
    content: str = Field(..., description="Memory content to store")

class ArchivalMemoryUpdateParams(BaseModel):
    id: str = Field(..., description="UUID of memory to update")
    content: str = Field(..., description="New content (empty string to delete)")

class ArchivalMemorySearchParams(BaseModel):
    query: str = Field(..., description="Search query")

class ConversationSearchParams(BaseModel):
    query: str = Field(..., description="Search query")
    count: int = Field(10, description="Number of results")

class WebSearchParams(BaseModel):
    query: str = Field(..., description="Search query")
    reason: str = Field(..., description="Reason for searching")
    engine: Literal["openai", "google", "auto"] = Field("auto", description="Search engine strategy")

class ChangeVisionFocusParams(BaseModel):
    path: str = Field(..., description="Absolute path to focus on")

# --- Action Models (Tool Call Wrappers) ---

class ActionWaitForUser(BaseModel):
    tool_name: Literal["wait_for_user"]
    parameters: WaitForUserParams

class ActionSendMessage(BaseModel):
    tool_name: Literal["send_message"]
    parameters: SendMessageParams

class ActionEmotionUpdate(BaseModel):
    tool_name: Literal["emotion_update"]
    parameters: EmotionUpdateParams

class ActionAffectionUpdate(BaseModel):
    tool_name: Literal["affection_update"]
    parameters: AffectionUpdateParams

class ActionCoreMemoryAppend(BaseModel):
    tool_name: Literal["core_memory_append"]
    parameters: CoreMemoryAppendParams

class ActionCoreMemoryReplace(BaseModel):
    tool_name: Literal["core_memory_replace"]
    parameters: CoreMemoryReplaceParams

class ActionArchivalMemoryInsert(BaseModel):
    tool_name: Literal["archival_memory_insert"]
    parameters: ArchivalMemoryInsertParams

class ActionArchivalMemoryUpdate(BaseModel):
    tool_name: Literal["archival_memory_update"]
    parameters: ArchivalMemoryUpdateParams

class ActionArchivalMemorySearch(BaseModel):
    tool_name: Literal["archival_memory_search"]
    parameters: ArchivalMemorySearchParams

class ActionConversationSearch(BaseModel):
    tool_name: Literal["conversation_search"]
    parameters: ConversationSearchParams

class ActionWebSearch(BaseModel):
    tool_name: Literal["web_search"]
    parameters: WebSearchParams

class ActionChangeVisionFocus(BaseModel):
    tool_name: Literal["change_vision_focus"]
    parameters: ChangeVisionFocusParams

# Union of all Actions
ActionType = Union[
    ActionWaitForUser,
    ActionSendMessage,
    ActionEmotionUpdate,
    ActionAffectionUpdate,
    ActionCoreMemoryAppend,
    ActionCoreMemoryReplace,
    ActionArchivalMemoryInsert,
    ActionArchivalMemoryUpdate,
    ActionArchivalMemorySearch,
    ActionConversationSearch,
    ActionWebSearch,
    ActionChangeVisionFocus
]

# --- Top Level Response Model ---

class CoreResponse(BaseModel):
    internal_monologue: str = Field(..., description="Step-by-step reasoning in English.")
    actions: List[ActionType] = Field(..., description="List of actions (tools) to execute in parallel.")
