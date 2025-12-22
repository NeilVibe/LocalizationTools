"""Sync to central server schemas."""

from typing import Optional
from pydantic import BaseModel


class SyncFileToCentralRequest(BaseModel):
    """Request body for syncing a local file to central PostgreSQL."""
    file_id: int  # File ID in local SQLite
    destination_project_id: int  # Project ID in central PostgreSQL


class SyncFileToCentralResponse(BaseModel):
    """Response for sync operation."""
    success: bool
    new_file_id: Optional[int] = None
    rows_synced: int = 0
    message: str


class SyncTMToCentralRequest(BaseModel):
    """Request body for syncing a local TM to central PostgreSQL."""
    tm_id: int  # TM ID in local SQLite


class SyncTMToCentralResponse(BaseModel):
    """Response for TM sync operation."""
    success: bool
    new_tm_id: Optional[int] = None
    entries_synced: int = 0
    message: str
