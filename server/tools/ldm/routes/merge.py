"""
Merge endpoints -- translator merge and Game Dev merge.

POST /api/ldm/files/{file_id}/merge          -- Translator merge (corrections)
POST /api/ldm/files/{file_id}/gamedev-merge   -- Game Dev XML merge (tree diff)

Transactional: computes all changes first, then bulk_update at once.
"""

from __future__ import annotations

import base64

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from server.utils.dependencies import get_current_active_user_async, get_db
from server.repositories.factory import get_file_repository, get_row_repository

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
    row_repo=Depends(get_row_repository),
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

    logger.info(
        "[MERGE] Merge request: target_file=%d, source_file=%d, mode=%s, threshold=%.2f",
        file_id,
        request.source_file_id,
        request.match_mode,
        request.threshold,
    )

    # Fetch source and target rows
    source_rows = await row_repo.get_all_for_file(request.source_file_id)
    if not source_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rows found for source file {request.source_file_id}",
        )

    target_rows = await row_repo.get_all_for_file(file_id)
    if not target_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rows found for target file {file_id}",
        )

    # Run merge (compute all changes) -- CPU-bound, offload to thread
    svc = TranslatorMergeService()
    result = await asyncio.to_thread(
        svc.merge_files,
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


# =============================================================================
# Game Dev Merge
# =============================================================================


class GameDevMergeRequest(BaseModel):
    """Request body for Game Dev merge. No source_file_id -- current DB rows ARE the edits."""

    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max depth for tree diffing",
    )


class GameDevMergeResponse(BaseModel):
    """Response from Game Dev merge endpoint."""

    total_nodes: int
    changed_nodes: int
    added_nodes: int
    removed_nodes: int
    modified_attributes: int
    rows_updated: int
    output_xml: str  # Base64-encoded merged XML bytes


@router.post("/files/{file_id}/gamedev-merge", response_model=GameDevMergeResponse)
async def gamedev_merge_file(
    file_id: int,
    request: GameDevMergeRequest,
    current_user: dict = Depends(get_current_active_user_async),
    file_repo=Depends(get_file_repository),
    row_repo=Depends(get_row_repository),
):
    """Merge Game Dev XML by diffing original file against current DB rows.

    Uses GameDevMergeService for position-based tree diff + in-place apply.
    Merge is TRANSACTIONAL: compute diff, then bulk_update extra_data.

    Args:
        file_id: File ID to merge.
        request: GameDevMergeRequest with max_depth.

    Returns:
        GameDevMergeResponse with change counts and base64-encoded merged XML.
    """
    from server.tools.ldm.services.gamedev_merge import ChangeType, GameDevMergeService

    # Get file metadata
    file_meta = await file_repo.get(file_id)
    if not file_meta:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")

    # Get current rows
    current_rows = await row_repo.get_all_for_file(file_id)
    if not current_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No rows found for file {file_id}",
        )

    # Retrieve original XML content from file extra_data
    file_extra = file_meta.get("extra_data")
    if isinstance(file_extra, str):
        import json
        try:
            file_extra = json.loads(file_extra)
        except (json.JSONDecodeError, TypeError):
            file_extra = None

    original_xml_b64 = file_extra.get("original_content") if file_extra else None
    if not original_xml_b64:
        raise HTTPException(
            status_code=422,
            detail="Original XML content not available for diff. "
            "File must have original_content stored in extra_data.",
        )

    # Decode original XML from base64
    try:
        original_xml = base64.b64decode(original_xml_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to decode original_content: {exc}",
        )

    logger.info(
        "[GAMEDEV-MERGE] Merge request: file_id=%d, max_depth=%d, rows=%d",
        file_id,
        request.max_depth,
        len(current_rows),
    )

    # Run merge -- CPU-bound, offload to thread
    svc = GameDevMergeService()
    result = await asyncio.to_thread(
        svc.merge, original_xml, current_rows, max_depth=request.max_depth
    )

    # Build bulk_update list for rows with modified extra_data
    rows_updated = 0
    if result.changes:
        updates = []
        for change in result.changes:
            if change.change_type == ChangeType.MODIFIED:
                # Find the matching row by position and update its extra_data
                # with the new attribute values
                row_idx = change.position
                if row_idx < len(current_rows):
                    row = current_rows[row_idx]
                    new_extra = dict(row.get("extra_data") or {})
                    # Apply attribute changes to extra_data
                    attrs = dict(new_extra.get("attributes", {}))
                    for attr_change in change.attribute_changes:
                        if attr_change.new_value is None:
                            attrs.pop(attr_change.name, None)
                        else:
                            attrs[attr_change.name] = attr_change.new_value
                    new_extra["attributes"] = attrs
                    updates.append({
                        "id": row["id"],
                        "extra_data": new_extra,
                    })
        if updates:
            rows_updated = await row_repo.bulk_update(updates)

    # Encode output XML as base64
    output_xml_b64 = base64.b64encode(result.output_xml).decode("ascii")

    logger.info(
        "[GAMEDEV-MERGE] Complete: total=%d, changed=%d, added=%d, removed=%d, attrs=%d, updated=%d",
        result.total_nodes,
        result.changed_nodes,
        result.added_nodes,
        result.removed_nodes,
        result.modified_attributes,
        rows_updated,
    )

    return GameDevMergeResponse(
        total_nodes=result.total_nodes,
        changed_nodes=result.changed_nodes,
        added_nodes=result.added_nodes,
        removed_nodes=result.removed_nodes,
        modified_attributes=result.modified_attributes,
        rows_updated=rows_updated,
        output_xml=output_xml_b64,
    )
