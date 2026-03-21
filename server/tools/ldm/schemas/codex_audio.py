"""Audio Codex schemas for Audio encyclopedia API responses.

Phase 48: Audio Codex UI -- Pydantic v2 models for audio card grid,
detail view, category tree from D20 export_path grouping,
and paginated audio list with streaming support.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# =============================================================================
# Audio card (grid view)
# =============================================================================


class AudioCardResponse(BaseModel):
    """Card grid data for a single audio entry."""

    event_name: str
    string_id: Optional[str] = None
    script_kr: Optional[str] = None
    script_eng: Optional[str] = None
    export_path: Optional[str] = None
    has_wem: bool = False
    xml_order: Optional[int] = None


# =============================================================================
# Audio detail (full view)
# =============================================================================


class AudioDetailResponse(BaseModel):
    """Full audio detail including WEM path and stream URL."""

    event_name: str
    string_id: Optional[str] = None
    script_kr: Optional[str] = None
    script_eng: Optional[str] = None
    export_path: Optional[str] = None
    has_wem: bool = False
    xml_order: Optional[int] = None
    wem_path: Optional[str] = None
    stream_url: Optional[str] = None


# =============================================================================
# Category tree (sidebar navigation)
# =============================================================================


class AudioCategoryNode(BaseModel):
    """Tree node for category sidebar built from D20 export_path grouping."""

    name: str
    full_path: str
    count: int = 0
    children: List[AudioCategoryNode] = []


class AudioCategoryTreeResponse(BaseModel):
    """Response for category tree endpoint."""

    categories: List[AudioCategoryNode]
    total_events: int


# =============================================================================
# Paginated list
# =============================================================================


class AudioListResponse(BaseModel):
    """Paginated audio list response."""

    items: List[AudioCardResponse]
    total: int
    offset: int
    limit: int
    has_more: bool
    category_filter: Optional[str] = None
