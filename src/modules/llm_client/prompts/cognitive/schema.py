from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .actions import Action

class CognitiveResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    """
    Schema for the Cognitive Cycle Output.
    """
    # Dynamic Field: "system_analysis"
    # In Pydantic, to exclude it from Schema, we'd need to create the class dynamically.
    # For now, we define it as Optional. 
    # The PromptBuilder will Instruct the LLM to UNCLUDE/EXCLUDE it.
    # The Schema sent to OpenAI will have it as Optional.
    system_analysis: Optional[str] = Field(..., description="Logical analysis (Chain of Thought).")
    
    thought: str = Field(..., description="Internal Monologue (Your Persona's Voice).")

    actions: List[Action] = Field(..., description="List of actions to execute.")

    talk: str = Field(..., description="Content to speak to the user (Japanese). Keep it short (1-3 sentences) and conversational. Split long thoughts.")

    show_expression: str = Field(..., description="Facial expression key (e.g., 'neutral', 'happy').")

    idle: float = Field(..., description="Seconds to idle. 0=Continue Thinking, >0=Wait for Input (e.g. 15-60).")
    