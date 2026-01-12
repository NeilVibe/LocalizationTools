"""
TM Entry endpoints - CRUD operations for individual TM entries.

P11-FIX: ALL endpoints now use Repository Pattern for database abstraction.
- Online mode: PostgreSQLTMRepository (PostgreSQL)
- Offline mode: SQLiteTMRepository (SQLite)

Clean separation achieved - no more direct database access in routes!
Migrated from api.py lines 1366-1722, 1820-1870, 2153-2201
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from loguru import logger

from server.utils.dependencies import get_current_active_user_async, get_db
from server.database.models import LDMTranslationMemory

# Repository Pattern imports - ALL DB access goes through here
from server.repositories import TMRepository, get_tm_repository

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================

def _auto_sync_tm_indexes(tm_id: int, user_id: int):
    """
    Background task to auto-sync TM indexes after entry modifications.
    Model2Vec is fast (~29k sentences/sec), so this runs quickly.

    BUG-032/BUG-034: Now also updates TM status to 'ready' after successful sync.
    TASK-002: Tracked in active_operations with silent=True (no toast).
    DESIGN-001: Access check is done before calling this task.
    """
    from server.tools.ldm.tm_indexer import TMSyncManager
    from server.utils.progress_tracker import TrackedOperation

    sync_db = next(get_db())
    try:
        # DESIGN-001: Access check done before this task is called
        # Just verify TM still exists
        tm = sync_db.query(LDMTranslationMemory).filter(
            LDMTranslationMemory.id == tm_id
        ).first()

        if not tm:
            logger.warning(f"[TM-ENTRY] [TM-ENTRY] Auto-sync skipped: TM {tm_id} not found")
            return

        # TASK-002: Track auto-sync with silent=True (no toast, but visible in Task Manager)
        with TrackedOperation(
            f"Auto-sync TM: {tm.name}",
            user_id,
            tool_name="LDM",
            function_name="auto_sync_tm",
            silent=True,  # NO toast for quick auto-updates
            parameters={"tm_id": tm_id, "tm_name": tm.name}
        ) as op:
            sync_manager = TMSyncManager(sync_db, tm_id)
            result = sync_manager.sync()

            # BUG-032/BUG-034: Update TM status to 'ready' after successful sync
            tm.status = "ready"
            tm.updated_at = datetime.utcnow()
            sync_db.commit()

            op.update(100, f"Synced: +{result['stats']['insert']} entries")

        logger.info(
            f"Auto-sync TM {tm_id}: INSERT={result['stats']['insert']}, "
            f"UPDATE={result['stats']['update']}, time={result['time_seconds']:.2f}s, status=ready"
        )
    except Exception as e:
        logger.error(f"[TM-ENTRY] [TM-ENTRY] Auto-sync failed for TM {tm_id}: {e}")
    finally:
        sync_db.close()


# =============================================================================
# TM Viewer Endpoints (FEAT-003)
# =============================================================================

@router.get("/tm/{tm_id}/entries")
async def get_tm_entries(
    tm_id: int,
    page: int = 1,
    limit: int = 100,
    sort_by: str = "id",
    sort_order: str = "asc",
    search: Optional[str] = None,
    metadata_field: Optional[str] = None,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get paginated TM entries for TM Viewer.

    P11-FIX: Uses Repository Pattern for offline/online mode support.

    Query params:
    - page: Page number (1-indexed)
    - limit: Items per page (max 500)
    - sort_by: Field to sort by (id, source_text, target_text, string_id, created_at)
    - sort_order: asc or desc
    - search: Search term (searches source, target, and string_id)
    """
    # Get TM via repository (works for both PostgreSQL and SQLite)
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Validate and cap limit
    limit = min(limit, 500)
    page = max(page, 1)
    offset = (page - 1) * limit

    # Get entries via repository
    if search:
        # Use search method for filtered results
        entries = await repo.search_entries(tm_id, search, limit=limit)
        total = len(entries)
        total_pages = 1
    else:
        # Use paginated get_entries
        entries = await repo.get_entries(tm_id, offset=offset, limit=limit)
        # Get total count from TM entry_count
        total = tm.get("entry_count", 0)
        total_pages = (total + limit - 1) // limit if total > 0 else 1

    # Format entries for response
    formatted_entries = [
        {
            "id": e.get("id"),
            "source_text": e.get("source_text"),
            "target_text": e.get("target_text"),
            "string_id": e.get("string_id"),
            "created_at": e.get("created_at") if isinstance(e.get("created_at"), str) else (e.get("created_at").isoformat() if e.get("created_at") else None)
        }
        for e in entries
    ]

    return {
        "entries": formatted_entries,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "search": search,
        "tm_name": tm.get("name")
    }


@router.post("/tm/{tm_id}/entries")
async def add_tm_entry(
    tm_id: int,
    source_text: str = Form(...),
    target_text: str = Form(...),
    background_tasks: BackgroundTasks = None,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Add a single entry to a Translation Memory (Adaptive TM).

    P9-ARCH: Uses Repository Pattern - adds to PostgreSQL (online)
    or SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    Q-001: Auto-syncs TM indexes after add.
    """
    logger.info(f"[TM-ENTRY] Adding TM entry: tm_id={tm_id}, source={source_text[:30]}...")

    # Verify TM exists using repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Add entry using repository
    entry = await repo.add_entry(
        tm_id=tm_id,
        source=source_text,
        target=target_text,
        created_by=current_user.get("username", "unknown")
    )

    if not entry:
        raise HTTPException(status_code=500, detail="Failed to add entry")

    # Get updated TM to return entry count
    updated_tm = await repo.get(tm_id)
    entry_count = updated_tm.get("entry_count", 0) if updated_tm else 0

    logger.success(f"[TM-ENTRY] [TM-ENTRY] TM entry added: tm_id={tm_id}, total entries={entry_count}")

    # Q-001: Auto-sync indexes in background (only for PostgreSQL mode)
    # TODO: Add index sync for SQLite mode
    if background_tasks:
        background_tasks.add_task(_auto_sync_tm_indexes, tm_id, current_user["user_id"])

    return {
        "success": True,
        "tm_id": tm_id,
        "entry_id": entry.get("id"),
        "entry_count": entry_count
    }


@router.put("/tm/{tm_id}/entries/{entry_id}")
async def update_tm_entry(
    tm_id: int,
    entry_id: int,
    source_text: Optional[str] = None,
    target_text: Optional[str] = None,
    string_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Update a single TM entry (for inline editing in TM Viewer).

    P11-FIX: Uses Repository Pattern - works for both PostgreSQL (online)
    and SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    Q-001: Auto-syncs TM indexes after update.
    """
    # Verify TM exists using repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Update entry using repository
    username = current_user.get("username", "unknown")
    updated_entry = await repo.update_entry(
        entry_id=entry_id,
        source_text=source_text,
        target_text=target_text,
        string_id=string_id,
        updated_by=username
    )

    if not updated_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    logger.info(f"[TM-ENTRY] Updated TM entry: tm_id={tm_id}, entry_id={entry_id}, by={username}")

    # Q-001: Auto-sync indexes in background
    if background_tasks:
        background_tasks.add_task(_auto_sync_tm_indexes, tm_id, current_user["user_id"])

    return updated_entry


@router.delete("/tm/{tm_id}/entries/{entry_id}")
async def delete_tm_entry(
    tm_id: int,
    entry_id: int,
    background_tasks: BackgroundTasks = None,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Delete a single TM entry.

    P9-ARCH: Uses Repository Pattern - deletes from PostgreSQL (online)
    or SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    Q-001: Auto-syncs TM indexes after delete.
    """
    # Verify TM exists using repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Delete entry using repository
    deleted = await repo.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")

    logger.info(f"[TM-ENTRY] Deleted TM entry: tm_id={tm_id}, entry_id={entry_id}")

    # Q-001: Auto-sync indexes in background (only for PostgreSQL mode)
    if background_tasks:
        background_tasks.add_task(_auto_sync_tm_indexes, tm_id, current_user["user_id"])

    return {"message": "Entry deleted", "entry_id": entry_id}


# =============================================================================
# Confirm/Unconfirm endpoints (BUG-020: memoQ-style workflow)
# =============================================================================

@router.post("/tm/{tm_id}/entries/{entry_id}/confirm")
async def confirm_tm_entry(
    tm_id: int,
    entry_id: int,
    confirm: bool = True,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    BUG-020: Confirm or unconfirm a TM entry (memoQ-style workflow).

    P11-FIX: Uses Repository Pattern - works for both PostgreSQL (online)
    and SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    """
    # Verify TM exists using repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    username = current_user.get("username", "unknown")

    # Confirm/unconfirm entry using repository
    updated_entry = await repo.confirm_entry(
        entry_id=entry_id,
        confirm=confirm,
        confirmed_by=username
    )

    if not updated_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    logger.info(f"[TM-ENTRY] {'Confirmed' if confirm else 'Unconfirmed'} TM entry: tm_id={tm_id}, entry_id={entry_id}, by={username}")

    return updated_entry


@router.post("/tm/{tm_id}/entries/bulk-confirm")
async def bulk_confirm_tm_entries(
    tm_id: int,
    entry_ids: List[int],
    confirm: bool = True,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    BUG-020: Bulk confirm/unconfirm multiple TM entries.

    P11-FIX: Uses Repository Pattern - works for both PostgreSQL (online)
    and SQLite (offline) based on user's mode.
    DESIGN-001: Public by default.
    """
    # Verify TM exists using repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    username = current_user.get("username", "unknown")

    # Bulk confirm/unconfirm using repository
    updated_count = await repo.bulk_confirm_entries(
        tm_id=tm_id,
        entry_ids=entry_ids,
        confirm=confirm,
        confirmed_by=username
    )

    logger.info(f"[TM-ENTRY] Bulk {'confirmed' if confirm else 'unconfirmed'} {updated_count} TM entries: tm_id={tm_id}, by={username}")

    return {
        "updated_count": updated_count,
        "action": "confirmed" if confirm else "unconfirmed"
    }
