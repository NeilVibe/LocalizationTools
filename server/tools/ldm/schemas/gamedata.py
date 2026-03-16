"""Gamedata schemas for Game Dev Grid file explorer.

Phase 18: Game Dev Grid -- folder browsing, XML entity parsing, attribute editing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# =============================================================================
# Browse schemas
# =============================================================================


class FileNode(BaseModel):
    """A single XML file in the folder tree."""

    name: str
    path: str
    size: int
    entity_count: int


class FolderNode(BaseModel):
    """A folder in the folder tree (recursive)."""

    name: str
    path: str
    folders: List[FolderNode] = []
    files: List[FileNode] = []


# Rebuild model to resolve forward references
FolderNode.model_rebuild()


class FolderTreeResponse(BaseModel):
    """Response for browse endpoint."""

    root: FolderNode
    base_path: str


class BrowseRequest(BaseModel):
    """Request for browse endpoint."""

    path: str = ""
    max_depth: int = 4


# =============================================================================
# Column detection schemas
# =============================================================================


class ColumnHint(BaseModel):
    """Describes a column detected in an XML entity."""

    key: str
    label: str
    editable: bool = False


class FileColumnsRequest(BaseModel):
    """Request for columns endpoint."""

    xml_path: str


class FileColumnsResponse(BaseModel):
    """Response for columns endpoint."""

    columns: List[ColumnHint]
    editable_attrs: List[str]


# =============================================================================
# Save schemas
# =============================================================================


class GameDevSaveRequest(BaseModel):
    """Request for save endpoint."""

    xml_path: str
    entity_index: int
    attr_name: str
    new_value: str


class GameDevSaveResponse(BaseModel):
    """Response for save endpoint."""

    success: bool
    message: str


# =============================================================================
# Rows schemas (VirtualGrid-compatible)
# =============================================================================


class GameDataRowsRequest(BaseModel):
    """Request for rows endpoint -- paginated entity rows from an XML file."""

    xml_path: str
    page: int = 1
    limit: int = 50
    search: str = ""


class GameDataRow(BaseModel):
    """A single entity row for the VirtualGrid."""

    id: int
    row_num: int
    string_id: str
    source: str
    target: str
    status: str
    extra_data: Dict[str, Any]


class GameDataRowsResponse(BaseModel):
    """Response for rows endpoint -- paginated rows for VirtualGrid."""

    rows: List[GameDataRow]
    total: int
    page: int
    limit: int
    total_pages: int


# =============================================================================
# Tree schemas (hierarchical XML tree view)
# =============================================================================


class TreeNode(BaseModel):
    """A node in the hierarchical XML tree."""

    node_id: str  # unique ID within the tree (e.g., "root_0_child_2")
    tag: str  # XML element name (e.g., "SkillTreeInfo", "SkillNode")
    attributes: Dict[str, Any] = {}  # all XML attributes
    children: List[TreeNode] = []
    parent_id: Optional[str] = None  # back-reference for navigation
    editable_attrs: List[str] = []  # from EDITABLE_ATTRS mapping


# Rebuild model to resolve forward references for TreeNode
TreeNode.model_rebuild()


class TreeRequest(BaseModel):
    """Request for tree endpoint."""

    path: str
    max_depth: int = -1  # -1 = unlimited


class GameDataTreeResponse(BaseModel):
    """Response for tree endpoint -- hierarchical tree."""

    roots: List[TreeNode]
    file_path: str
    entity_type: str  # tag name of root's children (e.g., "SkillTreeInfo")
    node_count: int


class FolderTreeDataRequest(BaseModel):
    """Request for folder tree endpoint."""

    path: str
    max_depth: int = -1


class FolderTreeDataResponse(BaseModel):
    """Response for folder tree endpoint -- combined tree of all XML files."""

    files: List[GameDataTreeResponse]
    base_path: str
    total_nodes: int


# =============================================================================
# Index schemas (Phase 29: Multi-Tier Indexing)
# =============================================================================


class IndexBuildRequest(BaseModel):
    """Request for index build endpoint."""

    path: str  # folder path


class IndexBuildResponse(BaseModel):
    """Response for index build endpoint."""

    entity_count: int
    whole_lookup_count: int
    line_lookup_count: int
    whole_embeddings_count: int
    line_embeddings_count: int
    ac_terms_count: int
    build_time_ms: int
    status: str


class IndexSearchRequest(BaseModel):
    """Request for index search endpoint."""

    query: str
    top_k: int = 5
    threshold: float = 0.92


class IndexSearchResult(BaseModel):
    """A single search result from cascade search."""

    entity_name: str
    entity_desc: str
    node_id: str
    tag: str
    file_path: str
    score: float
    match_type: str


class IndexSearchResponse(BaseModel):
    """Response for index search endpoint."""

    tier: int
    tier_name: str
    results: List[IndexSearchResult]
    perfect_match: bool


class DetectEntitiesRequest(BaseModel):
    """Request for entity detection endpoint."""

    text: str


class IndexStatusResponse(BaseModel):
    """Response for index status endpoint."""

    ready: bool
    entity_count: int
    build_time_ms: int
    ac_terms_count: int
    whole_lookup_count: int
    line_lookup_count: int
