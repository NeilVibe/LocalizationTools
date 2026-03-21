"""Character Codex schemas for Character encyclopedia API responses.

Phase 47: Character Codex UI -- Pydantic v2 models for character card grid,
detail view with knowledge resolution passes, filename-based categories,
and paginated character list.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from server.tools.ldm.schemas.codex_items import KnowledgePassEntry


# =============================================================================
# Character card (grid view)
# =============================================================================


class CharacterCardResponse(BaseModel):
    """Card grid data for a single character."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    desc_kr: Optional[str] = None
    category: Optional[str] = None
    race: Optional[str] = None
    gender: Optional[str] = None
    image_url: Optional[str] = None
    source_file: str = ""


# =============================================================================
# Character detail (full view)
# =============================================================================


class CharacterDetailResponse(BaseModel):
    """Full character detail including knowledge resolution and race/gender/age/job."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    desc_kr: Optional[str] = None
    category: Optional[str] = None
    race: Optional[str] = None
    gender: Optional[str] = None
    image_url: Optional[str] = None
    source_file: str = ""
    age: Optional[str] = None
    job: Optional[str] = None
    use_macro: str = ""
    knowledge_key: str = ""
    knowledge_pass_0: List[KnowledgePassEntry] = []
    knowledge_pass_1: List[KnowledgePassEntry] = []
    knowledge_pass_2: List[KnowledgePassEntry] = []
    related_entities: List[str] = []


# =============================================================================
# Category grouping
# =============================================================================


class CharacterCategoryItem(BaseModel):
    """One category tab entry."""

    category: str
    count: int


class CharacterCategoryResponse(BaseModel):
    """Response for categories endpoint."""

    categories: List[CharacterCategoryItem]
    total_characters: int


# =============================================================================
# Paginated list
# =============================================================================


class CharacterListResponse(BaseModel):
    """Paginated character list response."""

    characters: List[CharacterCardResponse]
    total: int
    offset: int
    limit: int
    has_more: bool
    category_filter: Optional[str] = None
