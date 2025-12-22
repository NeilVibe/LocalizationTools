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

    class Config:
        from_attributes = True


class RowUpdate(BaseModel):
    target: Optional[str] = None
    status: Optional[str] = None
