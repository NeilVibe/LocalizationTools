"""
Phase 45: MegaIndex API - Status, build trigger, entity lookup, and counts.

Exposes MegaIndex state to the frontend and provides endpoints for
triggering builds and looking up individual entities.

Endpoints:
- GET  /mega/status              -> dict sizes, build_time, built status
- POST /mega/build               -> trigger build with WebSocket progress, return stats
- GET  /mega/entity/{type}/{key} -> single entity lookup (404 if missing)
- GET  /mega/counts              -> entity type counts
"""
from __future__ import annotations

import asyncio
import dataclasses
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.utils.websocket import (
    emit_operation_start,
    emit_progress_update,
    emit_operation_complete,
    emit_operation_failed,
)
from ..services.mega_index import get_mega_index
from ..services.perforce_path_service import get_perforce_path_service

router = APIRouter(prefix="/mega", tags=["mega_index"])


class BuildRequest(BaseModel):
    """Optional body for build endpoint."""

    preload_langs: Optional[List[str]] = None
    trigger_reason: Optional[str] = None


# =============================================================================
# Shared helper: build MegaIndex with WebSocket progress tracking
# =============================================================================

async def build_megaindex_with_progress(
    preload_langs: Optional[List[str]] = None,
    trigger_reason: str = "Manual",
) -> dict:
    """Build MegaIndex with real-time WebSocket progress emission.

    Runs build in a thread (50+ seconds). Emits operation_start, progress_update
    per phase, and operation_complete/failed via WebSocket so the Task Manager
    can display a live progress bar.

    Thread-safe: concurrent builds are rejected by MegaIndex._build_lock.
    All WebSocket emissions are wrapped in try/except to prevent double-faults.

    Returns MegaIndex stats dict on success.
    """
    mi = get_mega_index()
    path_svc = get_perforce_path_service()
    status = path_svc.get_status()
    drive = status.get("drive", "?")
    branch = status.get("branch", "?")
    build_label = f"{drive}:/{branch}"
    was_built = mi._built

    operation_id = f"megaindex_{int(time.time())}"
    build_type = "REBUILD" if was_built else "BUILD"
    started_at_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    logger.info(
        f"[MEGAINDEX] {build_type} triggered ({trigger_reason}) on {build_label}"
    )

    # Emit operation start (non-fatal if WebSocket is down)
    try:
        await emit_operation_start({
            "operation_id": operation_id,
            "user_id": 0,
            "username": "system",
            "tool_name": "MegaIndex",
            "function_name": "build",
            "operation_name": f"MegaIndex {build_type} — {build_label}",
            "status": "running",
            "progress_percentage": 0.0,
            "started_at": started_at_str,
            "parameters": {
                "trigger_reason": trigger_reason,
                "drive": drive,
                "branch": branch,
                "build_type": build_type,
            },
        })
    except Exception as e:
        logger.warning(f"[MEGAINDEX] Failed to emit operation_start: {e}")

    # Thread-safe progress callback — called from build thread
    loop = asyncio.get_running_loop()

    def on_progress(phase: int, total: int, description: str, stats: str) -> None:
        pct = round((phase / total) * 100)
        future = asyncio.run_coroutine_threadsafe(
            emit_progress_update({
                "operation_id": operation_id,
                "user_id": 0,
                "username": "system",
                "tool_name": "MegaIndex",
                "function_name": "build",
                "operation_name": f"MegaIndex {build_type} — {build_label}",
                "status": "running",
                "progress_percentage": float(pct),
                "current_step": f"Phase {phase}/{total}: {description}",
                "total_steps": total,
                "completed_steps": phase,
            }),
            loop,
        )
        # Log emit failures but don't block the build
        def _on_emit_done(f: "asyncio.Future", _phase: int = phase) -> None:
            if not f.cancelled() and f.exception():
                logger.warning(f"[MEGAINDEX] Progress emit failed at phase {_phase}: {f.exception()}")

        future.add_done_callback(_on_emit_done)

    try:
        await asyncio.to_thread(
            mi.build, preload_langs=preload_langs, on_progress=on_progress
        )

        # Re-initialize MapDataService so image/audio lookups use new data
        try:
            from ..services.mapdata_service import get_mapdata_service
            mapdata = get_mapdata_service()
            mapdata.initialize(branch=branch, drive=drive)
            logger.info(
                f"[MEGAINDEX] MapDataService re-initialized after {build_type}: "
                f"{len(mapdata._strkey_to_image)} image chains"
            )
        except Exception as e:
            logger.error(
                f"[MEGAINDEX] MapDataService init after {build_type} FAILED: {e} "
                f"— image/audio lookups may be stale"
            )

        result_stats = mi.stats()

        try:
            await emit_operation_complete({
                "operation_id": operation_id,
                "user_id": 0,
                "username": "system",
                "tool_name": "MegaIndex",
                "function_name": "build",
                "operation_name": f"MegaIndex {build_type} — {build_label}",
                "status": "completed",
                "progress_percentage": 100.0,
                "current_step": f"Done in {mi._build_time:.1f}s",
                "total_steps": 7,
                "completed_steps": 7,
                "started_at": started_at_str,
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "parameters": {
                    "trigger_reason": trigger_reason,
                    "drive": drive,
                    "branch": branch,
                    "build_type": build_type,
                    "build_time": f"{mi._build_time:.1f}s",
                },
            })
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Failed to emit operation_complete: {e}")

        return result_stats

    except Exception as e:
        logger.error(f"[MEGAINDEX] {build_type} FAILED on {build_label}: {e}")
        try:
            await emit_operation_failed({
                "operation_id": operation_id,
                "user_id": 0,
                "username": "system",
                "tool_name": "MegaIndex",
                "function_name": "build",
                "operation_name": f"MegaIndex {build_type} — {build_label}",
                "status": "failed",
                "progress_percentage": 0.0,
                "error_message": str(e),
                "started_at": started_at_str,
            })
        except Exception as emit_err:
            logger.error(f"[MEGAINDEX] Failed to emit operation_failed: {emit_err}")
        raise


@router.get("/status")
async def mega_status():
    """
    Get MegaIndex status without triggering a build.

    Returns dict sizes, build_time, and built status.
    """
    mi = get_mega_index()
    return mi.stats()


@router.post("/build")
async def mega_build(
    body: Optional[BuildRequest] = None,
    _user=Depends(get_current_active_user_async),
):
    """
    Trigger MegaIndex build with real-time progress tracking.

    Emits WebSocket events (operation_start, progress_update, operation_complete)
    so the Task Manager shows a live progress bar with 7 phases.
    """
    preload_langs = body.preload_langs if body and body.preload_langs else None
    trigger_reason = body.trigger_reason if body and body.trigger_reason else "API"
    return await build_megaindex_with_progress(
        preload_langs=preload_langs,
        trigger_reason=trigger_reason,
    )


@router.get("/entity/{entity_type}/{strkey}")
async def mega_entity(entity_type: str, strkey: str):
    """
    Look up a single entity by type and StrKey.

    Returns entity data as JSON dict. Returns 404 if not found.
    """
    mi = get_mega_index()
    entity = mi.get_entity(entity_type, strkey)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_type}/{strkey}",
        )
    return dataclasses.asdict(entity)


@router.get("/counts")
async def mega_counts():
    """
    Get entity type counts.

    Does not trigger a build -- returns current state.
    """
    mi = get_mega_index()
    return mi.entity_counts()
