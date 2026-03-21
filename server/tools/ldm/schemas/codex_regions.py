"""Region Codex schemas for Region encyclopedia API responses.

Phase 49: Region Codex UI + Interactive Map -- Pydantic v2 models for region
card grid, detail view with knowledge resolution passes, faction hierarchy tree,
and paginated region list.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel

from server.tools.ldm.schemas.codex_items import KnowledgePassEntry


# =============================================================================
# Faction tree sub-models
# =============================================================================


class FactionNodeItem(BaseModel):
    """Region node within a faction (leaf in faction tree)."""

    strkey: str
    name: str
    node_type: Optional[str] = None
    has_position: bool = False


class FactionNode(BaseModel):
    """Faction within a faction group."""

    strkey: str
    name: str
    region_count: int = 0
    regions: List[FactionNodeItem] = []


class FactionGroupNode(BaseModel):
    """Top-level faction group node."""

    strkey: str
    group_name: str
    faction_count: int = 0
    region_count: int = 0
    factions: List[FactionNode] = []


class FactionTreeResponse(BaseModel):
    """Response for faction tree endpoint."""

    groups: List[FactionGroupNode]
    total_groups: int
    total_factions: int
    total_regions: int


# =============================================================================
# Region card (grid view)
# =============================================================================


class RegionCardResponse(BaseModel):
    """Card grid data for a single region."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    display_name: Optional[str] = None
    node_type: Optional[str] = None
    world_position: Optional[Tuple[float, float, float]] = None
    faction_name: Optional[str] = None
    faction_group_name: Optional[str] = None
    image_url: Optional[str] = None
    source_file: str = ""


# =============================================================================
# Region detail (full view)
# =============================================================================


class RegionDetailResponse(BaseModel):
    """Full region detail including knowledge resolution and world position."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    display_name: Optional[str] = None
    node_type: Optional[str] = None
    world_position: Optional[Tuple[float, float, float]] = None
    faction_name: Optional[str] = None
    faction_group_name: Optional[str] = None
    image_url: Optional[str] = None
    source_file: str = ""
    knowledge_key: Optional[str] = None
    desc_kr: Optional[str] = None
    knowledge_pass_0: List[KnowledgePassEntry] = []
    knowledge_pass_1: List[KnowledgePassEntry] = []
    knowledge_pass_2: List[KnowledgePassEntry] = []
    related_entities: List[str] = []


# =============================================================================
# Paginated list
# =============================================================================


class RegionListResponse(BaseModel):
    """Paginated region list response."""

    items: List[RegionCardResponse]
    total: int
    offset: int
    limit: int
    has_more: bool
    faction_group_filter: Optional[str] = None
