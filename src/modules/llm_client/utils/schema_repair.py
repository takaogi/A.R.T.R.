from typing import Any, Dict, Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
from src.foundation.logging import logger
from src.foundation.types import Result

T = TypeVar("T", bound=BaseModel)

class SchemaValidator:
    """
    Utilities for validating and repairing Dicts against a Pydantic Schema.
    """

    @staticmethod
    def validate_and_repair(data: Any, schema: Type[T]) -> Result[T]:
        """
        Attempts to validate data against schema.
        If validation fails, tries basic repairs (like casting).
        """
        try:
            # 1. Direct Validation
            model = schema.model_validate(data)
            return Result.ok(model)
        except ValidationError as e:
            logger.warning(f"Schema Validation Failed: {e}. Attempting repair...")
            
            # 2. Attempt Repair (Very basic for now)
            # Example: properties might be nested in a 'properties' key or similar wrapping
            # Or strings might need to be cast to int
            
            # TODO: Implement robust repair logic (e.g. asking LLM to fix it, or heuristic patching)
            # For now, we returns the error.
            return Result.fail(f"Validation Error: {e}")
