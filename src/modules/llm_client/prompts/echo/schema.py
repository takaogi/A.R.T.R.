from pydantic import BaseModel

class EchoSchema(BaseModel):
    """Schema for Echo response."""
    response: str
