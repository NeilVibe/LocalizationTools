"""Project-related schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    platform_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_restricted: bool = False  # DESIGN-001

    class Config:
        from_attributes = True
