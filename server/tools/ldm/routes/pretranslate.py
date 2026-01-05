"""
Pretranslation endpoints - Match TM entries to file rows.

Migrated from api.py lines 2313-2434
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.models import LDMFile, LDMProject
from server.tools.ldm.schemas import PretranslateRequest, PretranslateResponse
from server.tools.ldm.permissions import can_access_project

router = APIRouter(tags=["LDM"])


@router.post("/pretranslate", response_model=PretranslateResponse)
async def pretranslate_file(
    request: PretranslateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Pretranslate a file using selected engine.

    Engines:
    - standard: TM 5-tier cascade (hash + FAISS + ngram)
    - xls_transfer: XLS Transfer logic with code preservation
    - kr_similar: KR Similar logic with structure adaptation

    All engines use LOCAL processing (Qwen embeddings + FAISS).
    No external translation API required.

    Args:
        file_id: LDM file ID to pretranslate
        engine: "standard" | "xls_transfer" | "kr_similar"
        dictionary_id: TM ID (for standard) or dictionary ID (for xls/kr)
        threshold: Similarity threshold (default 0.92)
        skip_existing: Skip rows that already have translations (default True)

    Returns:
        PretranslateResponse with stats: matched, skipped, total, time_seconds
    """
    from server.tools.ldm.pretranslate import pretranslate_file as do_pretranslate

    logger.info(f"Pretranslate request: file_id={request.file_id}, engine={request.engine}, "
                f"dict_id={request.dictionary_id}, threshold={request.threshold}")

    # Validate engine
    valid_engines = ["standard", "xls_transfer", "kr_similar"]
    if request.engine not in valid_engines:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid engine. Must be one of: {valid_engines}"
        )

    # Verify file exists
    file_result = await db.execute(
        select(LDMFile).where(LDMFile.id == request.file_id)
    )
    file = file_result.scalar_one_or_none()

    if not file:
        # P9: Check if it's a local file in SQLite Offline Storage
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        local_file = offline_db.get_local_file(request.file_id)
        if not local_file:
            raise HTTPException(status_code=404, detail="File not found")
        # Use local file info
        file_name = local_file.get("name", "unknown")
        is_local_file = True
    else:
        # Verify project access (DESIGN-001: Public by default)
        if not await can_access_project(db, file.project_id, current_user):
            raise HTTPException(status_code=404, detail="File not found")
        file_name = file.name
        is_local_file = False

    # Run pretranslation in threadpool to avoid blocking
    # TASK-001: Add TrackedOperation for progress tracking
    # file_name already set above (from PostgreSQL file or SQLite local file)
    user_id = current_user["user_id"]
    username = current_user.get("username", "unknown")

    def _do_pretranslate():
        from server.utils.progress_tracker import TrackedOperation

        sync_db = next(get_db())
        try:
            with TrackedOperation(
                operation_name=f"Pretranslate: {file_name}",
                user_id=user_id,
                username=username,
                tool_name="LDM",
                function_name="pretranslate",
                parameters={
                    "file_id": request.file_id,
                    "engine": request.engine,
                    "dictionary_id": request.dictionary_id,
                    "threshold": request.threshold
                }
            ) as tracker:
                def progress_callback(current: int, total: int):
                    progress_pct = (current / total) * 100 if total > 0 else 0
                    tracker.update(progress_pct, f"Row {current}/{total}", current, total)

                result = do_pretranslate(
                    db=sync_db,
                    file_id=request.file_id,
                    engine=request.engine,
                    dictionary_id=request.dictionary_id,
                    threshold=request.threshold,
                    skip_existing=request.skip_existing,
                    progress_callback=progress_callback
                )
                return result
        finally:
            sync_db.close()

    try:
        result = await asyncio.to_thread(_do_pretranslate)

        return PretranslateResponse(
            file_id=result["file_id"],
            engine=result["engine"],
            matched=result["matched"],
            skipped=result["skipped"],
            total=result["total"],
            threshold=result["threshold"],
            time_seconds=result["time_seconds"]
        )

    except ValueError as e:
        logger.error(f"Pretranslation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pretranslation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pretranslation failed. Check server logs.")
