from typing import Optional
from pydantic import BaseModel, Field

class CharacterProfile(BaseModel):
    name: str = Field(..., description="Character Name")
    description: str = Field(..., description="Detailed description of personality, appearance, and background.")
    first_message: str = Field(..., description="First greeting message when chat starts.")
    scenario: str = Field(..., description="The situation or context of the conversation.")
    example_dialogue: str = Field(..., description="Example conversation between User and Character.")
    system_prompt: str = Field(..., description="Additional system instructions or post-history instructions.")
    reflex_examples: str = Field(..., description="Examples of short, reflexive responses (for Reflex Layer).")
    white_room_path: str = Field("data/white_room", description="Path to the white room directory.")
    default_length: str = Field("1~2 sentences", description="Default length of responses (e.g., 'Short', 'Medium', '1 paragraph').")
