"""
TM Index endpoints - Build indexes, sync indexes, check status.

Migrated from api.py lines 1937-2015, 2017-2149, 2207-2306
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.models import LDMTranslationMemory, LDMTMEntry, LDMTMIndex
from server.tools.ldm.permissions import can_access_tm

router = APIRouter(tags=["LDM"])


@router.post("/tm/{tm_id}/build-indexes")
async def build_tm_indexes(
    tm_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Build FAISS indexes for a Translation Memory.

    Creates:
    - whole_text_lookup (hash index for Tier 1 exact match)
    - line_lookup (hash index for Tier 3 line match)
    - whole.index (FAISS HNSW for Tier 2 semantic search)
    - line.index (FAISS HNSW for Tier 4 line-by-line search)

    This is required before using the 5-Tier Cascade TM search.
    Building indexes can take several minutes for large TMs (50k+ entries).

    Returns operation_id for progress tracking via WebSocket/TaskManager.
    """
    from server.tools.ldm.tm_indexer import TMIndexer
    from server.utils.progress_tracker import TrackedOperation

    logger.info(f"Building TM indexes: tm_id={tm_id}, user={current_user['user_id']}")

    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get TM
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = tm_result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    tm_name = tm.name  # Capture for use in executor

    # Run indexing in threadpool to avoid blocking event loop
    def _build_indexes():
        sync_db = next(get_db())
        try:
            # Create operation for progress tracking
            with TrackedOperation(
                operation_name=f"Build TM Indexes: {tm_name}",
                user_id=current_user["user_id"],
                username=current_user.get("username", "unknown"),
                tool_name="LDM",
                function_name="build_tm_indexes",
                total_steps=4,
                parameters={"tm_id": tm_id}
            ) as tracker:
                # Build indexes with progress callback
                def progress_callback(stage: str, current: int, total: int):
                    progress_pct = (current / total) * 100 if total > 0 else 0
                    tracker.update(progress_pct, stage, current, total)

                indexer = TMIndexer(sync_db)
                result = indexer.build_indexes(tm_id, progress_callback=progress_callback)

                logger.success(f"TM indexes built: tm_id={tm_id}, entries={result['entry_count']}")
                return result
        finally:
            sync_db.close()

    try:
        result = await asyncio.to_thread(_build_indexes)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid TM configuration")
    except Exception as e:
        logger.error(f"TM index build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Index build failed. Check server logs.")


@router.get("/tm/{tm_id}/indexes")
async def get_tm_index_status(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get index status for a Translation Memory.

    Returns list of indexes and their status.
    """
    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get TM
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Get indexes
    result = await db.execute(
        select(LDMTMIndex).where(LDMTMIndex.tm_id == tm_id)
    )
    indexes = result.scalars().all()

    return {
        "tm_id": tm_id,
        "tm_status": tm.status,
        "indexes": [
            {
                "type": idx.index_type,
                "status": idx.status,
                "file_size": idx.file_size,
                "built_at": idx.built_at.isoformat() if idx.built_at else None
            }
            for idx in indexes
        ]
    }


# ============================================================================
# FEAT-004: TM Sync Protocol (2025-12-18)
# ============================================================================

@router.get("/tm/{tm_id}/sync-status")
async def get_tm_sync_status(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check if TM indexes are stale (DB has newer changes than local indexes).

    Returns:
        - is_stale: True if DB was updated after last sync
        - pending_changes: Estimated number of changes (0 if up-to-date)
        - last_synced: When indexes were last synced
        - tm_updated_at: When TM was last modified in DB
    """
    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get TM
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Check local metadata
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "ldm_tm" / str(tm_id)
    metadata_path = data_dir / "metadata.json"

    last_synced = None
    synced_entry_count = 0

    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            last_synced = metadata.get("synced_at")
            synced_entry_count = metadata.get("entry_count", 0)
        except Exception as e:
            logger.warning(f"Failed to read TM metadata: {e}")

    # Get current DB entry count
    result = await db.execute(
        select(func.count()).select_from(LDMTMEntry).where(LDMTMEntry.tm_id == tm_id)
    )
    db_entry_count = result.scalar() or 0

    # Determine if stale
    is_stale = False
    pending_changes = 0

    if last_synced is None:
        # Never synced
        is_stale = True
        pending_changes = db_entry_count
    elif tm.updated_at:
        # Compare timestamps
        try:
            synced_dt = datetime.fromisoformat(last_synced.replace('Z', '+00:00'))
            if tm.updated_at.replace(tzinfo=None) > synced_dt.replace(tzinfo=None):
                is_stale = True
                # Estimate pending changes (rough: diff in counts + assume some updates)
                pending_changes = max(1, abs(db_entry_count - synced_entry_count))
        except Exception:
            is_stale = True
            pending_changes = db_entry_count

    return {
        "tm_id": tm_id,
        "is_stale": is_stale,
        "pending_changes": pending_changes,
        "last_synced": last_synced,
        "tm_updated_at": tm.updated_at.isoformat() if tm.updated_at else None,
        "db_entry_count": db_entry_count,
        "synced_entry_count": synced_entry_count
    }


@router.post("/tm/{tm_id}/sync")
async def sync_tm_indexes(
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Smart sync TM indexes with DB.

    Uses TMSyncManager for efficient sync:
    - Only re-embeds INSERT/UPDATE entries
    - Copies existing embeddings for UNCHANGED entries
    - Rebuilds FAISS/hash indexes at the end

    TASK-002: Tracked with toast (manual operation).

    Returns:
        Sync results including stats (insert, update, delete, unchanged)
    """
    from server.tools.ldm.tm_indexer import TMSyncManager
    from server.utils.progress_tracker import TrackedOperation

    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get TM
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    tm_name = tm.name
    user_id = current_user["user_id"]
    username = current_user["username"]

    logger.info(f"Starting TM sync for TM {tm_id} (user: {username})")

    # Run sync in threadpool to avoid blocking
    # BUG-033: Also update TM status after successful sync
    # TASK-002: Track with TrackedOperation (shows toast for manual operations)
    def _sync_tm():
        sync_db = next(get_db())
        try:
            # TASK-002: Track manual sync (NOT silent - shows toast)
            with TrackedOperation(
                f"Sync TM: {tm_name}",
                user_id,
                username=username,
                tool_name="LDM",
                function_name="sync_tm_indexes",
                # silent=False (default) - shows toast for manual operations
                parameters={"tm_id": tm_id, "tm_name": tm_name}
            ) as op:
                op.update(10, "Loading TM data...")
                sync_manager = TMSyncManager(sync_db, tm_id)

                op.update(30, "Computing changes...")
                result = sync_manager.sync()

                op.update(90, "Updating TM status...")
                # BUG-033/BUG-034: Update TM status to 'ready' after successful sync
                tm_record = sync_db.query(LDMTranslationMemory).filter(
                    LDMTranslationMemory.id == tm_id
                ).first()
                if tm_record:
                    tm_record.status = "ready"
                    tm_record.updated_at = datetime.utcnow()
                    sync_db.commit()

                op.update(100, f"Synced: +{result['stats']['insert']}, ~{result['stats']['update']}")

            return result
        finally:
            sync_db.close()

    try:
        result = await asyncio.to_thread(_sync_tm)

        logger.success(
            f"TM {tm_id} sync complete: "
            f"INSERT={result['stats']['insert']}, UPDATE={result['stats']['update']}, "
            f"UNCHANGED={result['stats']['unchanged']}, time={result['time_seconds']}s, status=ready"
        )

        return result

    except Exception as e:
        import traceback
        error_detail = f"TM sync failed: {str(e)}"
        error_traceback = traceback.format_exc()
        logger.error(f"TM sync failed for TM {tm_id}: {e}\n{error_traceback}")
        # Include traceback in response for debugging (CI can see this in test output)
        raise HTTPException(
            status_code=500,
            detail=f"{error_detail}\n\nTraceback:\n{error_traceback}"
        )
