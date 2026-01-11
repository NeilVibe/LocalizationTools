"""
TM Entry endpoints - CRUD operations for individual TM entries.

P9-ARCH: Uses Repository Pattern for database abstraction.
- Online mode: PostgreSQLTMRepository
- Offline mode: SQLiteTMRepository

Note: Some complex operations (update, confirm, bulk-confirm) still use direct
database access for now - these can be migrated to repository pattern later.

Migrated from api.py lines 1366-1722, 1820-1870, 2153-2201
"""

import hashlib
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, or_
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.db_utils import normalize_text_for_hash
from server.database.models import LDMTranslationMemory, LDMTMEntry
from server.tools.ldm.permissions import can_access_tm

# Repository Pattern imports
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get paginated TM entries for TM Viewer (DESIGN-001: Public by default).

    Query params:
    - page: Page number (1-indexed)
    - limit: Items per page (max 500)
    - sort_by: Field to sort by (id, source_text, target_text, string_id, created_at)
    - sort_order: asc or desc
    - search: Search term (searches source, target, and string_id)
    """
    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    tm_result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = tm_result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Validate and cap limit
    limit = min(limit, 500)
    page = max(page, 1)
    offset = (page - 1) * limit

    # Build query
    query = select(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                LDMTMEntry.source_text.ilike(search_pattern),
                LDMTMEntry.target_text.ilike(search_pattern),
                LDMTMEntry.string_id.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Apply sorting
    sort_column = {
        "id": LDMTMEntry.id,
        "source_text": LDMTMEntry.source_text,
        "target_text": LDMTMEntry.target_text,
        "string_id": LDMTMEntry.string_id,
        "created_at": LDMTMEntry.created_at
    }.get(sort_by, LDMTMEntry.id)

    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute
    result = await db.execute(query)
    entries = result.scalars().all()

    # Format entries
    formatted_entries = [
        {
            "id": e.id,
            "source_text": e.source_text,
            "target_text": e.target_text,
            "string_id": e.string_id,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in entries
    ]

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "entries": formatted_entries,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "search": search,
        "tm_name": tm.name
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Update a single TM entry (for inline editing in TM Viewer, DESIGN-001: Public by default).
    Q-001: Auto-syncs TM indexes after update.
    """
    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    tm_result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = tm_result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Find entry
    entry_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.id == entry_id,
            LDMTMEntry.tm_id == tm_id
        )
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Update fields if provided
    if source_text is not None:
        entry.source_text = source_text
        # Recalculate hash
        normalized = normalize_text_for_hash(source_text)
        entry.source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    if target_text is not None:
        entry.target_text = target_text

    if string_id is not None:
        entry.string_id = string_id

    # BUG-020: Track who made the update
    entry.updated_at = datetime.utcnow()
    entry.updated_by = current_user.get("username", "unknown")

    # Mark TM as updated (triggers index rebuild on next pretranslate)
    tm.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(entry)

    logger.info(f"[TM-ENTRY] Updated TM entry: tm_id={tm_id}, entry_id={entry_id}, by={current_user.get('username')}")

    # Q-001: Auto-sync indexes in background
    if background_tasks:
        background_tasks.add_task(_auto_sync_tm_indexes, tm_id, current_user["user_id"])

    return {
        "id": entry.id,
        "source_text": entry.source_text,
        "target_text": entry.target_text,
        "string_id": entry.string_id,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "updated_by": entry.updated_by,
        "is_confirmed": entry.is_confirmed,
        "confirmed_at": entry.confirmed_at.isoformat() if entry.confirmed_at else None,
        "confirmed_by": entry.confirmed_by
    }


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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    BUG-020: Confirm or unconfirm a TM entry (memoQ-style workflow, DESIGN-001: Public by default).

    When user approves a translation, it gets marked as confirmed with metadata.
    """
    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Find entry
    entry_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.id == entry_id,
            LDMTMEntry.tm_id == tm_id
        )
    )
    entry = entry_result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    username = current_user.get("username", "unknown")

    if confirm:
        entry.is_confirmed = True
        entry.confirmed_at = datetime.utcnow()
        entry.confirmed_by = username
    else:
        entry.is_confirmed = False
        entry.confirmed_at = None
        entry.confirmed_by = None

    await db.commit()
    await db.refresh(entry)

    logger.info(f"[TM-ENTRY] {'Confirmed' if confirm else 'Unconfirmed'} TM entry: tm_id={tm_id}, entry_id={entry_id}, by={username}")

    return {
        "id": entry.id,
        "source_text": entry.source_text,
        "target_text": entry.target_text,
        "string_id": entry.string_id,
        "is_confirmed": entry.is_confirmed,
        "confirmed_at": entry.confirmed_at.isoformat() if entry.confirmed_at else None,
        "confirmed_by": entry.confirmed_by
    }


@router.post("/tm/{tm_id}/entries/bulk-confirm")
async def bulk_confirm_tm_entries(
    tm_id: int,
    entry_ids: List[int],
    confirm: bool = True,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    BUG-020: Bulk confirm/unconfirm multiple TM entries (DESIGN-001: Public by default).
    """
    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    username = current_user.get("username", "unknown")
    now = datetime.utcnow()

    if confirm:
        stmt = update(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.id.in_(entry_ids)
        ).values(
            is_confirmed=True,
            confirmed_at=now,
            confirmed_by=username
        )
    else:
        stmt = update(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.id.in_(entry_ids)
        ).values(
            is_confirmed=False,
            confirmed_at=None,
            confirmed_by=None
        )

    result = await db.execute(stmt)
    await db.commit()

    updated_count = result.rowcount

    logger.info(f"[TM-ENTRY] Bulk {'confirmed' if confirm else 'unconfirmed'} {updated_count} TM entries: tm_id={tm_id}, by={username}")

    return {
        "updated_count": updated_count,
        "action": "confirmed" if confirm else "unconfirmed"
    }
