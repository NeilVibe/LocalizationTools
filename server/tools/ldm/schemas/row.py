"""Row-related schemas."""

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
    updated_at: datetime
    # QA fields (P2: Auto-LQA)
    qa_checked_at: Optional[datetime] = None
    qa_flag_count: int = 0

    class Config:
        from_attributes = True


class RowUpdate(BaseModel):
    target: Optional[str] = None
    status: Optional[str] = None
