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
    """Single TM suggestion.

    For project row suggestions: id, file_id are set
    For TM entry suggestions: entry_id, tm_id are set
    """
    source: str
    target: str
    similarity: float
    file_name: str
    # Row-based suggestion fields
    row_id: Optional[int] = None
    file_id: Optional[int] = None
    # TM-based suggestion fields
    entry_id: Optional[int] = None
    tm_id: Optional[int] = None
    tm_name: Optional[str] = None  # P11-B: Show TM source in match results


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
