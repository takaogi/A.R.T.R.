from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# --- Sub-models ---

class RelationshipState(BaseModel):
    trust: float = Field(0.0, ge=-100.0, le=100.0, description="信頼度 (-100 to 100)")
    intimacy: float = Field(0.0, ge=-100.0, le=100.0, description="親密さ (-100 to 100)")
    impression: str = Field("", description="ユーザーに対する現在の認識・メモ")

class PacemakerState(BaseModel):
    auto_max_consecutive: int = Field(50, description="Max consecutive cognitive loops per trigger (0=Unlimited)")

class ScheduleEvent(BaseModel):
    """
    Scheduled Event.
    """
    id: str = Field(..., description="Unique ID (UUID)")
    title: str = Field(..., description="Event Title")
    description: str = Field("", description="Details")
    start_time: str = Field(..., description="ISO 8601 Datetime")
    is_notified: bool = Field(False, description="Whether the event has been triggered/notified")

# --- Core Models ---
class CharacterProfile(BaseModel):
    """
    Static Character Definition.
    Construction primarily via LLM Import Pipeline.
    """
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Tags, Creator, Version, etc.")
    
    # Identity
    name: str
    aliases: List[str] = Field(default_factory=list)
    appearance: str = Field("", description="Visual description for diffusion/RP")
    description: str = Field("", description="Brief Overview / Description (Creator's Notes)")
    
    # Persona
    # Persona
    surface_persona: str = Field("", description="Outward Persona (Behavior & Attitude)")
    inner_persona: str = Field("", description="Inner Persona (Thoughts & Motives)")
    speech_patterns: List[str] = Field(default_factory=list, description="Speech Patterns & Rules")
    
    # Narrative
    background_story: Optional[str] = Field("", description="生い立ち・過去")
    world_definition: Optional[str] = Field("", description="世界観設定 (Static)")
    initial_situation: Optional[str] = Field("", description="初期状況 (Scenario)")
    first_message: Optional[str] = Field("", description="最初の挨拶")
    
    # Examples
    speech_examples: List[str] = Field(default_factory=list, description="発話例 (セリフのみ)")
    
    # Assets
    default_image_path: str = ""
    asset_map: Dict[str, str] = Field(default_factory=dict)

class CharacterState(BaseModel):
    """
    Dynamic Character State.
    Mutable during session.
    """
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    pacemaker: PacemakerState = Field(default_factory=PacemakerState)
    schedule: List[ScheduleEvent] = Field(default_factory=list, description="Scheduled Events")
    
    # User Knowledge (Core Memory)
    user_profile: str = Field("", description="User profile and known facts (Core Memory)")
    
    active_objectives: List[str] = Field(default_factory=list, description="短期的目標")
    active_objectives: List[str] = Field(default_factory=list, description="短期的目標")
    current_expression: str = Field("neutral", description="Current visual expression")

class CharacterCard(BaseModel):
    """
    Root Entity for A.R.T.R Character Data.
    """
    profile: CharacterProfile
    state: CharacterState = Field(default_factory=CharacterState)
