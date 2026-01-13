from pydantic import BaseModel, Field

class WebSearchResults(BaseModel):
    answer: str = Field(..., description="The direct answer to the query sourced from web search.")
    found_answer: bool = Field(..., description="Whether a satisfactory answer was found.")
