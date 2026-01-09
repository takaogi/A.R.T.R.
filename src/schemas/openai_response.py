from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field

# --- Tool Parameter Schemas ---
# These correspond to the arguments defined in `design_tool_definitions.md`

class SendMessageParams(BaseModel):
    content_en: str = Field(..., description="Message to user in English. Translator will handle localization.")

class EmotionUpdateParams(BaseModel):
    delta_v: float = Field(..., ge=-0.2, le=0.2, description="Valence shift (-0.2 to 0.2)")
    delta_a: float = Field(..., ge=-0.2, le=0.2, description="Arousal shift (-0.2 to 0.2)")
    delta_d: float = Field(..., ge=-0.2, le=0.2, description="Dominance shift (-0.2 to 0.2)")
    reason: str = Field(..., description="Reason for the emotional shift")

class AffectionUpdateParams(BaseModel):
    delta: float = Field(..., ge=-10.0, le=10.0, description="Affection shift (-10.0 to 10.0)")
    reason: str = Field(..., description="Reason for the affection shift")

class InnerMindUpdateParams(BaseModel):
    policy: str = Field(..., description="New active policy or goal for the inner voice")
    ttl: int = Field(..., description="Time-to-live in turns for this policy")

class CoreMemoryUpdateParams(BaseModel):
    section: Literal["persona", "human"] = Field(..., description="Section of core memory to update")
    content: str = Field(..., description="Content to append or update/replace")

class ArchivalMemoryInsertParams(BaseModel):
    content: str = Field(..., description="Text content to store in long-term archival memory")

class ArchivalMemorySearchParams(BaseModel):
    query: str = Field(..., description="Query string to search archival memory")

class ConversationSearchParams(BaseModel):
    query: str = Field(..., description="Query string to search conversation history")
    count: int = Field(..., description="Number of results to return")

class WebSearchParams(BaseModel):
    query: str = Field(..., description="Query string for web search")

class CallColorAgentParams(BaseModel):
    agent_name: str = Field(..., description="Name of the specialized agent to call (e.g., 'blue', 'red')")
    instruction: str = Field(..., description="Instruction for the agent")

class ChangeVisionFocusParams(BaseModel):
    path: str = Field(..., description="Absolute path in the white room to focus on")

class WaitForUserParams(BaseModel):
    pass # No parameters needed

# --- Tool Call Wrappers ---
# We use a tagged union pattern for type safety and easy parsing

class ToolWaitForUser(BaseModel):
    tool_name: Literal["wait_for_user"]
    parameters: WaitForUserParams

class ToolSendMessage(BaseModel):
    tool_name: Literal["send_message"]
    parameters: SendMessageParams

class ToolEmotionUpdate(BaseModel):
    tool_name: Literal["emotion_update"]
    parameters: EmotionUpdateParams

class ToolAffectionUpdate(BaseModel):
    tool_name: Literal["affection_update"]
    parameters: AffectionUpdateParams

class ToolInnerMindUpdate(BaseModel):
    tool_name: Literal["inner_mind_update"]
    parameters: InnerMindUpdateParams

class ToolCoreMemoryUpdate(BaseModel):
    tool_name: Literal["core_memory_update"]
    parameters: CoreMemoryUpdateParams

class ToolArchivalMemoryInsert(BaseModel):
    tool_name: Literal["archival_memory_insert"]
    parameters: ArchivalMemoryInsertParams

class ToolArchivalMemorySearch(BaseModel):
    tool_name: Literal["archival_memory_search"]
    parameters: ArchivalMemorySearchParams

class ToolConversationSearch(BaseModel):
    tool_name: Literal["conversation_search"]
    parameters: ConversationSearchParams

class ToolWebSearch(BaseModel):
    tool_name: Literal["web_search"]
    parameters: WebSearchParams

class ToolCallColorAgent(BaseModel):
    tool_name: Literal["call_color_agent"]
    parameters: CallColorAgentParams

class ToolChangeVisionFocus(BaseModel):
    tool_name: Literal["change_vision_focus"]
    parameters: ChangeVisionFocusParams

# Union of all possible tools
ToolAction = Union[
    ToolWaitForUser,
    ToolSendMessage,
    ToolEmotionUpdate,
    ToolAffectionUpdate,
    ToolInnerMindUpdate,
    ToolCoreMemoryUpdate,
    ToolArchivalMemoryInsert,
    ToolArchivalMemorySearch,
    ToolConversationSearch,
    ToolWebSearch,
    ToolCallColorAgent,
    ToolChangeVisionFocus
]

# --- Root Response Schema ---

class ArtrResponse(BaseModel):
    """
    The structured output schema for A.R.T.R.'s Core Thinking Layer.
    Enforces a mandatory inner monologue followed by a list of actions (tools).
    """
    internal_monologue: str = Field(..., description="The internal thought process, reasoning, and planning before taking action. Must be in English.")
    actions: List[ToolAction] = Field(..., description="A list of tool actions to execute in parallel.")

