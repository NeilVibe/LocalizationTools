"""Pretranslation related schemas."""

from pydantic import BaseModel


class PretranslateRequest(BaseModel):
    """Request for pretranslation."""
    file_id: int
    engine: str  # "standard" | "xls_transfer" | "kr_similar"
    dictionary_id: int
    threshold: float = 0.92
    skip_existing: bool = True


class PretranslateResponse(BaseModel):
    """Response from pretranslation."""
    file_id: int
    engine: str
    matched: int
    skipped: int
    total: int
    threshold: float
    time_seconds: float
