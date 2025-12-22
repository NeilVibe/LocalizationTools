"""Common schemas used across LDM endpoints."""

from pydantic import BaseModel


class DeleteResponse(BaseModel):
    """Standard response for delete operations."""
    message: str
