"""
Row endpoints - List rows, update row, project tree.

Migrated from api.py lines 660-933
P10: DB Abstraction Layer - Uses repositories for FULL PARITY.
"""

import asyncio
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, get_db
from server.database.models import (
    LDMFile, LDMRow,
    LDMActiveTM, LDMTranslationMemory
)
from server.tools.ldm.schemas import PaginatedRows, RowResponse, RowUpdate
from server.tools.ldm.websocket import broadcast_cell_update
from server.tools.ldm.permissions import can_access_file, can_access_project
from server.repositories import (
    RowRepository, get_row_repository,
    ProjectRepository, get_project_repository,
    FolderRepository, get_folder_repository,
    FileRepository, get_file_repository
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================



async def _get_project_linked_tm(db: AsyncSession, project_id: int, user_id: int) -> Optional[int]:
    """
    FEAT-001: Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.
    """
    result = await db.execute(
        select(LDMActiveTM.tm_id)
        .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
        .where(
            LDMActiveTM.project_id == project_id,
            LDMTranslationMemory.owner_id == user_id  # User must own the TM
        )
        .order_by(LDMActiveTM.priority)
        .limit(1)
    )
    return result.scalar_one_or_none()





# =============================================================================
# Row Endpoints
# =============================================================================

@router.get("/files/{file_id}/rows", response_model=PaginatedRows)
async def list_rows(
    file_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    search_mode: Optional[str] = Query("contain", description="Search mode: contain, exact, not_contain, fuzzy"),
    search_fields: Optional[str] = Query("source,target", description="Comma-separated fields: string_id, source, target"),
    status: Optional[str] = None,
    filter: Optional[str] = Query(None, description="Filter: all, confirmed, unconfirmed, qa_flagged"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: RowRepository = Depends(get_row_repository)
):
    """Get paginated rows for a file.

    Search Modes:
    - contain: Text contains search term (default, case-insensitive)
    - exact: Exact match only (case-insensitive)
    - not_contain: Exclude rows containing term
    - fuzzy: Trigram similarity search using pg_trgm (ranked by similarity)

    Search Fields:
    - string_id, source, target (comma-separated)

    Filters:
    - all: All rows (default)
    - confirmed: status = 'approved' or 'reviewed'
    - unconfirmed: status = 'pending' or 'translated'
    - qa_flagged: qa_flag_count > 0

    Repository Pattern: Uses RowRepository for database abstraction.
    """
    # P9: Local files (negative IDs) skip permission checks - user's own files
    if file_id < 0:
        # Use SQLite repository directly for local files
        from server.repositories.sqlite.row_repo import SQLiteRowRepository
        local_repo = SQLiteRowRepository()
        rows, total = await local_repo.get_for_file(
            file_id=file_id,
            page=page,
            limit=limit,
            search=search,
            search_mode=search_mode or "contain",
            search_fields=search_fields or "source,target",
            status=status,
            filter_type=filter
        )
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        return PaginatedRows(
            rows=rows,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    # Check file exists in PostgreSQL for permission verification
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Verify file access for PostgreSQL files (DESIGN-001: Public by default)
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Use Repository Pattern for all row queries
    rows, total = await repo.get_for_file(
        file_id=file_id,
        page=page,
        limit=limit,
        search=search,
        search_mode=search_mode or "contain",
        search_fields=search_fields or "source,target",
        status=status,
        filter_type=filter
    )

    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return PaginatedRows(
        rows=rows,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.put("/rows/{row_id}", response_model=RowResponse)
async def update_row(
    row_id: int,
    update: RowUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: RowRepository = Depends(get_row_repository)
):
    """Update a row's target text or status (source is READ-ONLY).

    Repository Pattern: Uses RowRepository for database abstraction.
    """
    # P9: Local rows (negative IDs) skip permission checks - user's own files
    if row_id < 0:
        # Use SQLite repository directly for local rows
        from server.repositories.sqlite.row_repo import SQLiteRowRepository
        local_repo = SQLiteRowRepository()
        updated_row = await local_repo.update(
            row_id=row_id,
            target=update.target,
            status=update.status
        )
        if not updated_row:
            raise HTTPException(status_code=404, detail="Row not found")
        return updated_row

    # Get row with file info for permission check and TM auto-add
    result = await db.execute(
        select(LDMRow).options(
            selectinload(LDMRow.file).selectinload(LDMFile.project)
        ).where(LDMRow.id == row_id)
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Verify file access (DESIGN-001: Public by default)
    if not await can_access_file(db, row.file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Save history before update
    old_target = row.target
    old_status = row.status

    # Use repository to update the row
    updated_row = await repo.update(
        row_id=row_id,
        target=update.target,
        status=update.status,
        updated_by=current_user["user_id"]
    )

    if not updated_row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Add edit history via repository
    await repo.add_edit_history(
        row_id=row_id,
        user_id=current_user["user_id"],
        old_target=old_target,
        new_target=updated_row.get("target"),
        old_status=old_status,
        new_status=updated_row.get("status")
    )

    # Commit the history
    await db.commit()

    # Broadcast cell update to all viewers (real-time sync)
    try:
        await broadcast_cell_update(
            file_id=updated_row.get("file_id"),
            row_id=updated_row.get("id"),
            row_num=updated_row.get("row_num"),
            target=updated_row.get("target"),
            status=updated_row.get("status"),
            updated_by=current_user["user_id"],
            updated_by_username=current_user["username"]
        )
    except Exception as e:
        # WebSocket broadcast failure shouldn't fail the API call
        logger.warning(f"[ROWS] WebSocket broadcast failed for row {row_id}: {e}")

    # FEAT-001: Auto-add to linked TM if status is 'reviewed'
    tm_updated = False
    new_status = updated_row.get("status")
    source = updated_row.get("source")
    target = updated_row.get("target")
    if new_status == "reviewed" and source and target:
        try:
            # Get project's linked TM
            project_id = row.file.project_id
            linked_tm_id = await _get_project_linked_tm(db, project_id, current_user["user_id"])

            if linked_tm_id:
                # Add entry to TM in background thread
                def _add_to_tm():
                    sync_db = next(get_db())
                    try:
                        from server.tools.ldm.tm_manager import TMManager
                        tm_manager = TMManager(sync_db)
                        return tm_manager.add_entry(linked_tm_id, source, target)
                    finally:
                        sync_db.close()

                result = await asyncio.to_thread(_add_to_tm)

                if result:
                    # Trigger index rebuild in background
                    background_tasks.add_task(
                        _auto_sync_tm_indexes,
                        linked_tm_id,
                        current_user["user_id"]
                    )
                    tm_updated = True
                    logger.info(f"FEAT-001: Auto-added to TM {linked_tm_id}: row_id={row_id}")
        except Exception as e:
            # Don't fail the row update, just log warning
            logger.warning(f"[ROWS] FEAT-001: Auto-add to TM failed: {e}")

    user_id = current_user["user_id"]
    logger.info(f"Row updated: id={row_id}, user={user_id}, tm_updated={tm_updated}")
    return updated_row


# =============================================================================
# Project Tree (Full structure for File Explorer)
# =============================================================================

@router.get("/projects/{project_id}/tree")
async def get_project_tree(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    project_repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get full project tree structure (folders + files) for File Explorer.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    """
    logger.debug(f"[ROWS] get_project_tree: project_id={project_id}")

    # Verify project access (DESIGN-001: Public by default)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get project using repository
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all folders using repository
    folders = await folder_repo.get_all(project_id)

    # Get all files using repository (high limit to get all files)
    files = await file_repo.get_all(project_id=project_id, limit=10000)

    # Build lookup dicts for O(n) tree building instead of O(n*m)
    folders_by_parent = defaultdict(list)
    files_by_folder = defaultdict(list)

    for folder in folders:
        folders_by_parent[folder.get("parent_id")].append(folder)
    for file in files:
        files_by_folder[file.get("folder_id")].append(file)

    def build_tree(parent_id=None):
        tree = []

        # Add folders at this level (O(1) lookup)
        for folder in folders_by_parent.get(parent_id, []):
            tree.append({
                "type": "folder",
                "id": folder.get("id"),
                "name": folder.get("name"),
                "children": build_tree(folder.get("id"))
            })

        # Add files at this level (O(1) lookup)
        for file in files_by_folder.get(parent_id, []):
            tree.append({
                "type": "file",
                "id": file.get("id"),
                "name": file.get("name"),
                "format": file.get("format"),
                "row_count": file.get("row_count")
            })

        return tree

    logger.debug(f"[ROWS] get_project_tree complete: project_id={project_id}, folders={len(folders)}, files={len(files)}")

    return {
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description")
        },
        "tree": build_tree(None)
    }
