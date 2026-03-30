"""Character Codex schemas for Character encyclopedia API responses.

Phase 47: Character Codex UI -- Pydantic v2 models for character card grid,
detail view with knowledge resolution passes, filename-based categories,
and bulk character list.
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
    image_urls: List[str] = []
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
    image_urls: List[str] = []
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
# Bulk list
# =============================================================================


class CharacterListResponse(BaseModel):
    """Bulk character list response."""

    characters: List[CharacterCardResponse]
    total: int
    category_filter: Optional[str] = None
