"""Folder-related schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FolderCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    name: str


class FolderResponse(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int]
    name: str
    created_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility

    class Config:
        from_attributes = True
