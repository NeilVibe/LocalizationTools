"""Project-related schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    platform_id: Optional[int] = None  # P11-FIX: Allow creating project under a platform


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    platform_id: Optional[int] = None
    created_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility
    updated_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility
    is_restricted: bool = False  # DESIGN-001

    class Config:
        from_attributes = True
