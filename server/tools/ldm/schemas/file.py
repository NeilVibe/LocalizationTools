"""File-related schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from .row import RowResponse


class FileResponse(BaseModel):
    id: int
    project_id: Optional[int]  # P9: None for local files in Offline Storage
    folder_id: Optional[int]
    name: str
    original_filename: str
    format: str
    row_count: int
    source_language: str
    target_language: Optional[str]
    created_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility
    updated_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility

    class Config:
        from_attributes = True


class PaginatedRows(BaseModel):
    rows: List[RowResponse]
    total: int
    page: int
    limit: int
    total_pages: int
