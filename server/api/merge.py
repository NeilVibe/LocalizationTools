"""
Merge API - Phase 58

Provides merge preview (dry-run) and execute endpoints for the
QuickTranslate-based transfer engine. Preview is synchronous,
execute uses SSE streaming for real-time progress.

Endpoints:
    POST /api/merge/preview  - Dry-run merge, returns match summary
    POST /api/merge/execute  - Real merge with SSE progress streaming
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from server.utils.perf_timer import PerfTimer
from server.api.settings import translate_wsl_path
from server.services.transfer_adapter import (
    execute_transfer,
    execute_multi_language_transfer,
    MATCH_MODES,
)


# ============================================================================
# Models
# ============================================================================


class MergePreviewRequest(BaseModel):
    """Request body for merge preview (dry-run)."""

    source_path: str
    target_path: str
    export_path: str
    match_mode: str = "strict"
    only_untranslated: bool = False
    stringid_all_categories: bool = False
    multi_language: bool = False


class MergePreviewResponse(BaseModel):
    """Response from merge preview (dry-run)."""

    files_processed: int = 0
    total_corrections: int = 0
    total_matched: int = 0
    total_updated: int = 0
    total_not_found: int = 0
    total_skipped: int = 0
    total_skipped_translated: int = 0
    overwrite_warnings: list[str] = []
    errors: list[str] = []
    per_language: dict | None = None
    scan: dict | None = None


class MergeExecuteRequest(BaseModel):
    """Request body for merge execution (Plan 02 will use this)."""

    source_path: str
    target_path: str
    export_path: str
    match_mode: str = "strict"
    only_untranslated: bool = False
    stringid_all_categories: bool = False
    multi_language: bool = False


# ============================================================================
# Merge guard (prevents concurrent merges)
# ============================================================================

_merge_in_progress: bool = False


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/merge", tags=["Merge"])


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/preview", response_model=MergePreviewResponse)
async def preview_merge(body: MergePreviewRequest):
    """Dry-run merge preview.

    Returns match summary without writing any files.
    Supports single-language and multi-language modes.
    """
    # Validate match_mode
    if body.match_mode not in MATCH_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid match_mode '{body.match_mode}'. Must be one of: {list(MATCH_MODES.keys())}",
        )

    # Translate paths for WSL/DEV_MODE
    translated_source = translate_wsl_path(body.source_path)
    translated_target = translate_wsl_path(body.target_path)
    translated_export = translate_wsl_path(body.export_path)

    logger.info(
        "Merge preview: mode={}, multi_language={}, source={}",
        body.match_mode,
        body.multi_language,
        translated_source,
    )

    try:
        if body.multi_language:
            # Multi-language: scan + dry-run all languages
            with PerfTimer("merge_preview", match_mode=body.match_mode, multi_language=True):
                result = await asyncio.to_thread(
                    execute_multi_language_transfer,
                    source_path=translated_source,
                    target_path=translated_target,
                    export_path=translated_export,
                    match_mode=body.match_mode,
                    only_untranslated=body.only_untranslated,
                    stringid_all_categories=body.stringid_all_categories,
                    dry_run=True,
                )
            return MergePreviewResponse(
                total_matched=result.get("total_matched", 0),
                total_skipped=result.get("total_skipped", 0),
                errors=[str(e) for e in result.get("errors", [])],
                per_language=result.get("per_language"),
                scan=result.get("scan"),
            )
        else:
            # Single-language dry-run
            with PerfTimer("merge_preview", match_mode=body.match_mode, multi_language=False):
                result = await asyncio.to_thread(
                    execute_transfer,
                    source_path=translated_source,
                    target_path=translated_target,
                    export_path=translated_export,
                    match_mode=body.match_mode,
                    only_untranslated=body.only_untranslated,
                    stringid_all_categories=body.stringid_all_categories,
                    dry_run=True,
                )

            # Extract overwrite warnings from file_results
            overwrite_warnings: list[str] = []
            if not body.only_untranslated:
                file_results = result.get("file_results", {})
                for fname, fdata in file_results.items():
                    if isinstance(fdata, dict):
                        matched = fdata.get("matched", 0)
                        if matched > 0:
                            overwrite_warnings.append(
                                f"{fname}: {matched} entries will be overwritten"
                            )

            return MergePreviewResponse(
                files_processed=result.get("files_processed", 0),
                total_corrections=result.get("total_corrections", 0),
                total_matched=result.get("total_matched", 0),
                total_updated=result.get("total_updated", 0),
                total_not_found=result.get("total_not_found", 0),
                total_skipped=result.get("total_skipped", 0),
                total_skipped_translated=result.get("total_skipped_translated", 0),
                overwrite_warnings=overwrite_warnings,
                errors=[str(e) for e in result.get("errors", [])],
            )

    except Exception as exc:
        logger.error("Merge preview failed: {}", exc)
        return MergePreviewResponse(errors=[str(exc)])


@router.post("/execute")
async def execute_merge(body: MergeExecuteRequest):
    """Execute merge with SSE streaming progress.

    Runs the actual merge in a background thread, streaming per-file
    progress events to the frontend in real-time, and sends a completion
    summary when done.

    SSE event types:
        progress - Per-file progress message (plain text)
        log      - Log message with level (JSON: {message, level})
        complete - Final result summary (JSON dict with all counters)
        error    - Error message (plain text), terminates stream
        ping     - Keepalive sent if no events for 30 seconds
    """
    global _merge_in_progress

    # Guard: prevent concurrent merges
    if _merge_in_progress:
        return JSONResponse(
            status_code=409,
            content={"error": "A merge is already in progress"},
        )

    # Validate match_mode
    if body.match_mode not in MATCH_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid match_mode '{body.match_mode}'. Must be one of: {list(MATCH_MODES.keys())}",
        )

    # Translate paths for WSL/DEV_MODE
    translated_source = translate_wsl_path(body.source_path)
    translated_target = translate_wsl_path(body.target_path)
    translated_export = translate_wsl_path(body.export_path)

    logger.info(
        "Merge execute: mode={}, multi_language={}, source={}",
        body.match_mode,
        body.multi_language,
        translated_source,
    )

    # Queue for piping progress from sync thread to async SSE generator
    queue: asyncio.Queue = asyncio.Queue()

    # Callbacks run in sync thread -- MUST use put_nowait (not put)
    def progress_cb(message: str):
        queue.put_nowait({"event": "progress", "data": message})

    def log_cb(message: str, level: str = "info"):
        queue.put_nowait({"event": "log", "data": json.dumps({"message": message, "level": level})})

    async def run_transfer():
        """Run blocking transfer in thread, signal completion via queue."""
        global _merge_in_progress
        _merge_in_progress = True
        try:
            if body.multi_language:
                with PerfTimer("merge_execute", match_mode=body.match_mode, multi_language=True):
                    result = await asyncio.to_thread(
                        execute_multi_language_transfer,
                        source_path=translated_source,
                        target_path=translated_target,
                        export_path=translated_export,
                        match_mode=body.match_mode,
                        only_untranslated=body.only_untranslated,
                        stringid_all_categories=body.stringid_all_categories,
                        dry_run=False,
                        progress_callback=progress_cb,
                        log_callback=log_cb,
                    )
            else:
                with PerfTimer("merge_execute", match_mode=body.match_mode, multi_language=False):
                    result = await asyncio.to_thread(
                        execute_transfer,
                        source_path=translated_source,
                        target_path=translated_target,
                        export_path=translated_export,
                        match_mode=body.match_mode,
                        only_untranslated=body.only_untranslated,
                        stringid_all_categories=body.stringid_all_categories,
                        dry_run=False,
                        progress_callback=progress_cb,
                        log_callback=log_cb,
                    )
            queue.put_nowait({"event": "complete", "data": json.dumps(result, default=str)})
        except Exception as exc:
            logger.error("Merge execute failed: {}", exc)
            queue.put_nowait({"event": "error", "data": str(exc)})
        finally:
            _merge_in_progress = False

    async def event_generator():
        """Async generator yielding SSE events from the queue."""
        task = asyncio.create_task(run_transfer())
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "keepalive"}
                continue
            yield msg
            if msg["event"] in ("complete", "error"):
                break
        await task  # Ensure task finishes cleanly

    return EventSourceResponse(event_generator())
