from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class Result(BaseModel, Generic[T]):
    """
    Standardized result type for application operations.
    Enforces explicit success/failure handling.
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def ok(cls, data: T = None) -> "Result[T]":
        """Create a successful result."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        """Create a failed result."""
        return cls(success=False, error=error)
        
    def unwrap(self) -> T:
        """
        Returns data if success, raises RuntimeError if failed.
        Useful when you are sure (or want to crash) on failure.
        """
        if not self.success:
            raise RuntimeError(f"Called unwrap on failed Result: {self.error}")
        return self.data
