"""
EMB-003: TM Maintenance Routes.

Login-time stale index check and background sync endpoints.
These endpoints use the Repository Pattern and work in both online/offline modes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.repositories import TMRepository, get_tm_repository
from server.tools.ldm.maintenance import TMMaintenanceManager, StaleTMInfo, MaintenanceResult
from server.tools.ldm.maintenance.manager import get_sync_queue_status


router = APIRouter(tags=["LDM-Maintenance"])


# =============================================================================
# EMB-003: Login-time Stale Index Check
# =============================================================================

@router.post("/maintenance/check-stale", response_model=MaintenanceResult)
async def check_stale_tms(
    auto_queue: bool = True,
    tm_ids: Optional[List[int]] = None,
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Check for TMs with stale indexes.

    EMB-003: Called after login to check if any TM indexes need sync.
    This is a quick check that compares timestamps - does not do actual sync.

    Works in BOTH online and offline modes via Repository Pattern.

    Args:
        auto_queue: If True, automatically queue stale TMs for background sync
        tm_ids: Optional list of specific TM IDs to check (default: all accessible)

    Returns:
        MaintenanceResult with list of stale TMs
    """
    logger.info(
        f"[EMB-003] Checking stale TMs for user {current_user['username']} "
        f"(auto_queue={auto_queue}, specific_tms={tm_ids})"
    )

    manager = TMMaintenanceManager(
        tm_repo=tm_repo,
        user=current_user
    )

    if tm_ids:
        # Check specific TMs
        stale_tms = await manager.find_stale_tms(tm_ids=tm_ids)
        result = MaintenanceResult(
            user_id=current_user["user_id"],
            stale_tms=stale_tms,
            total_stale=len(stale_tms),
            queued_for_sync=0
        )

        if stale_tms and auto_queue:
            for tm in stale_tms:
                if manager.queue_background_sync(tm.tm_id, reason="manual_check"):
                    result.queued_for_sync += 1
    else:
        # Full login check (all accessible TMs)
        result = await manager.on_user_login(auto_queue=auto_queue)

    return result


@router.get("/maintenance/stale-tms", response_model=List[StaleTMInfo])
async def get_stale_tms(
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get list of TMs with stale indexes (without queuing sync).

    Quick status check - useful for UI indicators showing which TMs need sync.
    """
    manager = TMMaintenanceManager(
        tm_repo=tm_repo,
        user=current_user
    )

    return await manager.find_stale_tms()


# =============================================================================
# Background Sync Management
# =============================================================================

@router.post("/maintenance/sync/{tm_id}")
async def queue_tm_sync(
    tm_id: int,
    priority: int = 0,
    background_tasks: BackgroundTasks = None,
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Queue a specific TM for background sync.

    Does NOT block - adds to sync queue and returns immediately.
    Use GET /maintenance/sync-status to check progress.

    Args:
        tm_id: TM ID to sync
        priority: Sync priority (0 = highest, used for manual requests)

    Returns:
        Queue status
    """
    # Verify TM exists and user has access
    tm = await tm_repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    manager = TMMaintenanceManager(
        tm_repo=tm_repo,
        user=current_user
    )

    queued = manager.queue_background_sync(
        tm_id=tm_id,
        reason="manual",
        priority=priority
    )

    if queued:
        logger.info(f"[EMB-003] TM {tm_id} queued for sync by {current_user['username']}")

        # Optionally trigger immediate sync via background task
        if background_tasks:
            background_tasks.add_task(_run_sync, manager, tm_id)

        return {
            "status": "queued",
            "tm_id": tm_id,
            "message": f"TM '{tm['name']}' queued for background sync"
        }
    else:
        return {
            "status": "already_queued",
            "tm_id": tm_id,
            "message": f"TM '{tm['name']}' is already in sync queue or syncing"
        }


@router.get("/maintenance/sync-status")
async def get_maintenance_status(
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get current sync queue status.

    Shows:
    - Items in queue
    - Currently syncing TMs
    """
    return get_sync_queue_status()


@router.delete("/maintenance/sync/{tm_id}")
async def cancel_tm_sync(
    tm_id: int,
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Cancel a queued sync (cannot cancel in-progress sync).

    Returns:
        Status of cancellation
    """
    from server.tools.ldm.maintenance.manager import _sync_queue, _sync_queue_lock, _sync_in_progress

    if tm_id in _sync_in_progress:
        return {
            "status": "in_progress",
            "tm_id": tm_id,
            "message": "Cannot cancel - sync is already in progress"
        }

    with _sync_queue_lock:
        original_len = len(_sync_queue)
        _sync_queue[:] = [item for item in _sync_queue if item.tm_id != tm_id]
        removed = original_len - len(_sync_queue)

    if removed > 0:
        logger.info(f"[EMB-003] TM {tm_id} sync cancelled by {current_user['username']}")
        return {
            "status": "cancelled",
            "tm_id": tm_id,
            "message": "Sync cancelled"
        }
    else:
        return {
            "status": "not_found",
            "tm_id": tm_id,
            "message": "TM was not in sync queue"
        }


# =============================================================================
# Helper Functions
# =============================================================================

async def _run_sync(manager: TMMaintenanceManager, tm_id: int):
    """Background task to run sync."""
    try:
        await manager.background_sync(tm_id)
    except Exception as e:
        logger.error(f"[EMB-003] Background sync failed for TM {tm_id}: {e}")
