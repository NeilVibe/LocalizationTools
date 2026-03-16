"""Codex schemas for Game World Codex encyclopedia.

Phase 19: Game World Codex -- entity registry, cross-references, semantic search.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


# =============================================================================
# Entity model
# =============================================================================


class CodexEntity(BaseModel):
    """A single entity in the Codex encyclopedia."""

    entity_type: str
    strkey: str
    name: str
    description: Optional[str] = None
    knowledge_key: Optional[str] = None
    image_texture: Optional[str] = None
    audio_key: Optional[str] = None
    source_file: str
    attributes: Dict[str, str] = {}
    related_entities: List[str] = []
    ai_image_url: Optional[str] = None


# =============================================================================
# Search models
# =============================================================================


class CodexSearchResult(BaseModel):
    """A single search result with similarity score."""

    entity: CodexEntity
    similarity: float
    match_type: str = "semantic"  # "semantic" or "exact"


class CodexSearchResponse(BaseModel):
    """Response for codex search endpoint."""

    results: List[CodexSearchResult]
    count: int
    search_time_ms: float


# =============================================================================
# List models
# =============================================================================


class CodexListResponse(BaseModel):
    """Response for codex list endpoint."""

    entities: List[CodexEntity]
    entity_type: str
    count: int
    total: int = 0
    has_more: bool = False
