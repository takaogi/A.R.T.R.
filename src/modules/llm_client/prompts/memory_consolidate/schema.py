from pydantic import BaseModel, Field

class ConsolidatedMemory(BaseModel):
    consolidated_text: str = Field(..., description="The unified, concise fact merged from multiple repetitive memories.")
