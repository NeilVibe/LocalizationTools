"""Settings related schemas."""

from typing import Optional
from pydantic import BaseModel


class EmbeddingEngineInfo(BaseModel):
    """Info about an available embedding engine."""
    id: str
    name: str
    description: str
    dimension: int
    memory_mb: int
    default: bool


class EmbeddingEngineResponse(BaseModel):
    """Response for current engine."""
    current_engine: str
    engine_name: str
    warning: Optional[str] = None  # Warning message when switching to slower engine


class SetEngineRequest(BaseModel):
    """Request to change embedding engine."""
    engine: str
