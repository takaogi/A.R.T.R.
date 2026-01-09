from typing import Optional, List
from pydantic import BaseModel, Field

class CharacterCardReverseMap(BaseModel):
    name: Optional[str] = Field(None, description="Updated name if changed.")
    description: Optional[str] = Field(None, description="Updated description (personality, appearance).")
    scenario: Optional[str] = Field(None, description="Updated scenario.")
    first_mes: Optional[str] = Field(None, description="Updated first message if context changed significantly.")
    mes_example: Optional[str] = Field(None, description="Updated example dialogue if speaking style changed.")
