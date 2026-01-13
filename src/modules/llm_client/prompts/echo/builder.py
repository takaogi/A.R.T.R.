from typing import Any, Dict, List, Union
from pydantic import BaseModel
from src.foundation.config import LLMProfile
from ..base import BaseBuilder
from .schema import EchoSchema

class Builder(BaseBuilder):
    """
    Builder for the 'echo' prompt.
    Simple echo bot that repeats input.
    """
    def build_messages(self, data: Dict[str, Any], profile: LLMProfile) -> List[Dict[str, Any]]:
        # Validate Data
        if "text" not in data:
            raise ValueError("Missing required key: 'text'")

        text = data["text"]
        
        # Example of Profile-based logic
        system_content = "You are an echo bot."
        if profile.provider == "local":
            system_content += " (Running Locally)"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Repeat this: {text}"}
        ]

    def build_schema(self, data: Dict[str, Any], profile: LLMProfile) -> Union[Dict[str, Any], type[BaseModel]]:
        return EchoSchema
