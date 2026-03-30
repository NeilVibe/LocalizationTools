"""Item Codex schemas for Item encyclopedia API responses.

Phase 46: Item Codex UI -- Pydantic v2 models for item card grid,
detail view with knowledge resolution passes, group hierarchy tree,
and bulk item list.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# =============================================================================
# Knowledge / Inspect sub-models
# =============================================================================


class KnowledgePassEntry(BaseModel):
    """One knowledge resolution entry (used in Passes 0/1/2)."""

    name: str
    desc: str
    source: str


class InspectDataEntry(BaseModel):
    """One InspectData entry from ItemEntry.inspect_entries."""

    desc: str
    knowledge_name: str
    knowledge_desc: str
    source: str


# =============================================================================
# Item card (grid view)
# =============================================================================


class ItemCardResponse(BaseModel):
    """Card grid data for a single item."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    desc_kr: Optional[str] = None
    group_name: Optional[str] = None
    group_key: Optional[str] = None
    image_urls: List[str] = []
    source_file: str = ""


# =============================================================================
# Item detail (full view)
# =============================================================================


class ItemDetailResponse(BaseModel):
    """Full item detail including knowledge resolution and InspectData."""

    strkey: str
    name_kr: str
    name_translated: Optional[str] = None
    desc_kr: Optional[str] = None
    group_name: Optional[str] = None
    group_key: Optional[str] = None
    image_urls: List[str] = []
    source_file: str = ""
    knowledge_key: str = ""
    knowledge_pass_0: List[KnowledgePassEntry] = []
    knowledge_pass_1: List[KnowledgePassEntry] = []
    knowledge_pass_2: List[KnowledgePassEntry] = []
    inspect_data: List[InspectDataEntry] = []
    related_entities: List[str] = []


# =============================================================================
# Group hierarchy tree
# =============================================================================


class ItemGroupTreeNode(BaseModel):
    """Hierarchy node for item group navigation."""

    strkey: str
    group_name: str
    parent_strkey: Optional[str] = None
    child_count: int = 0
    item_count: int = 0
    children: List[ItemGroupTreeNode] = []


class ItemGroupTreeResponse(BaseModel):
    """Response for group tree endpoint."""

    groups: List[ItemGroupTreeNode]
    total_groups: int
    total_items: int


# =============================================================================
# Bulk list
# =============================================================================


class ItemListResponse(BaseModel):
    """Bulk item list response."""

    items: List[ItemCardResponse]
    total: int
    group_filter: Optional[str] = None
