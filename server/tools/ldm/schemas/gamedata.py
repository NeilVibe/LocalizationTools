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

    path: str
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
