"""Row-related schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RowResponse(BaseModel):
    id: int
    file_id: int
    row_num: int
    string_id: Optional[str]
    source: Optional[str]
    target: Optional[str]
    status: str
    updated_at: Optional[datetime] = None  # P9: Optional for SQLite compatibility
    # QA fields (P2: Auto-LQA)
    qa_checked_at: Optional[datetime] = None
    qa_flag_count: int = 0
    # CTX-07: Translation source indicator ("human", "ai", "tm", or null)
    translation_source: Optional[str] = None
    # P16: Content category (Item, Character, Skill, etc.)
    category: Optional[str] = None

    class Config:
        from_attributes = True


class RowUpdate(BaseModel):
    target: Optional[str] = None
    status: Optional[str] = None
