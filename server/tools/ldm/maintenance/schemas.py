"""
EMB-003: Maintenance schemas.

Pydantic models for TM maintenance operations.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class StaleTMInfo(BaseModel):
    """Information about a stale TM that needs sync."""
    tm_id: int
    tm_name: str
    indexed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    entry_count: int = 0
    indexed_entry_count: int = 0
    pending_changes: int = 0
    status: str = "stale"  # stale, never_indexed, sync_queued

    class Config:
        from_attributes = True


class MaintenanceResult(BaseModel):
    """Result from maintenance check or sync operation."""
    user_id: int
    stale_tms: List[StaleTMInfo] = []
    total_stale: int = 0
    queued_for_sync: int = 0
    checked_at: datetime = None

    def __init__(self, **data):
        if data.get("checked_at") is None:
            data["checked_at"] = datetime.utcnow()
        super().__init__(**data)

    class Config:
        from_attributes = True


class SyncQueueItem(BaseModel):
    """Item in the background sync queue."""
    tm_id: int
    user_id: int
    priority: int = 0  # Lower = higher priority
    queued_at: datetime = None
    reason: str = "stale"  # stale, manual, login_check

    def __init__(self, **data):
        if data.get("queued_at") is None:
            data["queued_at"] = datetime.utcnow()
        super().__init__(**data)

    class Config:
        from_attributes = True
