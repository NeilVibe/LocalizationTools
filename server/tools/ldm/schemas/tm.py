"""Translation Memory related schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TMResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_lang: str
    target_lang: str
    entry_count: int
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TMUploadResponse(BaseModel):
    tm_id: int
    name: str
    entry_count: int
    status: str
    time_seconds: float
    rate_per_second: int


class TMSearchResult(BaseModel):
    source_text: str
    target_text: str
    similarity: float
    tier: int
    strategy: str


class TMSuggestion(BaseModel):
    """Single TM suggestion."""
    id: int
    source: str
    target: str
    file_id: int
    file_name: str
    similarity: float


class TMSuggestResponse(BaseModel):
    """Response from TM suggest endpoint."""
    suggestions: List[TMSuggestion]
    count: int


class LinkTMRequest(BaseModel):
    """Request to link TM to project."""
    tm_id: int
    priority: int = 0


class FileToTMRequest(BaseModel):
    """Request to convert file to TM."""
    name: str
    project_id: Optional[int] = None
    language: str = "en"
    description: Optional[str] = None
