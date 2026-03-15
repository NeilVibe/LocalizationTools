"""
Merge endpoint -- merge corrections from source file into target file.

POST /api/ldm/files/{file_id}/merge

Transactional: computes all changes first, then bulk_update at once.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from server.utils.dependencies import get_current_active_user_async, get_db
from server.repositories.factory import get_row_repository

router = APIRouter(tags=["LDM"])


class MergeRequest(BaseModel):
    """Request body for merge endpoint."""

    source_file_id: int = Field(..., description="File ID containing corrections")
    match_mode: str = Field(
        default="cascade",
        description="Match mode: strict, stringid_only, strorigin_only, fuzzy, cascade",
    )
    threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Fuzzy match similarity threshold",
    )
    is_cjk: bool = Field(
        default=False,
        description="CJK language flag for postprocess pipeline",
    )


class MergeResponse(BaseModel):
    """Response from merge endpoint."""

    matched: int
    skipped: int
    total: int
    match_type_counts: dict
    rows_updated: int


@router.post("/files/{file_id}/merge", response_model=MergeResponse)
async def merge_files(
    file_id: int,
    request: MergeRequest,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Merge corrections from source file into target file.

    Uses TranslatorMergeService with 4 match modes + cascade.
    Merge is TRANSACTIONAL: all changes computed first, then bulk_update.

    Args:
        file_id: Target file ID (file to merge corrections INTO).
        request: MergeRequest with source_file_id, match_mode, threshold.

    Returns:
        MergeResponse with match counts and rows_updated.
    """
    from server.tools.ldm.services.translator_merge import TranslatorMergeService

    valid_modes = {"strict", "stringid_only", "strorigin_only", "fuzzy", "cascade"}
    if request.match_mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid match_mode '{request.match_mode}'. Must be one of: {sorted(valid_modes)}",
        )

    row_repo = get_row_repository()

    logger.info(
        "[MERGE] Merge request: target_file=%d, source_file=%d, mode=%s, threshold=%.2f",
        file_id,
        request.source_file_id,
        request.match_mode,
        request.threshold,
    )

    # Fetch source and target rows
    source_rows = await row_repo.get_by_file(request.source_file_id)
    if not source_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rows found for source file {request.source_file_id}",
        )

    target_rows = await row_repo.get_by_file(file_id)
    if not target_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rows found for target file {file_id}",
        )

    # Run merge (compute all changes)
    svc = TranslatorMergeService()
    result = svc.merge_files(
        source_rows=source_rows,
        target_rows=target_rows,
        match_mode=request.match_mode,
        threshold=request.threshold,
        is_cjk=request.is_cjk,
    )

    # Transactional bulk update
    rows_updated = 0
    if result.updated_rows:
        updates = [
            {"id": row["id"], "target": row["target"], "status": "translated"}
            for row in result.updated_rows
        ]
        rows_updated = await row_repo.bulk_update(updates)

    logger.info(
        "[MERGE] Complete: matched=%d, skipped=%d, total=%d, rows_updated=%d, types=%s",
        result.matched,
        result.skipped,
        result.total,
        rows_updated,
        result.match_type_counts,
    )

    return MergeResponse(
        matched=result.matched,
        skipped=result.skipped,
        total=result.total,
        match_type_counts=result.match_type_counts,
        rows_updated=rows_updated,
    )
