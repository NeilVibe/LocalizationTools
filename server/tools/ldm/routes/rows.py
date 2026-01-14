"""
Row endpoints - List rows, update row, project tree.

P10: FULL ABSTRACT + REPO Pattern
- All endpoints use Repository Pattern with permissions baked in
- No direct DB access in routes

Migrated from api.py lines 660-933
"""

import asyncio
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from loguru import logger

from server.utils.dependencies import get_current_active_user_async, get_db
from server.tools.ldm.schemas import PaginatedRows, RowResponse, RowUpdate
from server.tools.ldm.websocket import broadcast_cell_update
from server.repositories import (
    RowRepository, get_row_repository,
    ProjectRepository, get_project_repository,
    FolderRepository, get_folder_repository,
    FileRepository, get_file_repository,
    TMRepository, get_tm_repository
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================



async def _get_project_linked_tm(tm_repo: TMRepository, project_id: int, user_id: int) -> Optional[int]:
    """
    FEAT-001: Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.

    P10-REPO: Now uses TMRepository instead of direct DB.
    """
    tm = await tm_repo.get_linked_for_project(project_id, user_id)
    return tm["id"] if tm else None





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
    current_user: dict = Depends(get_current_active_user_async),
    repo: RowRepository = Depends(get_row_repository),
    file_repo: FileRepository = Depends(get_file_repository)
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

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
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

    # P10: Get file via repository (permissions checked inside - returns None if no access)
    file = await file_repo.get(file_id)

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

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
    current_user: dict = Depends(get_current_active_user_async),
    repo: RowRepository = Depends(get_row_repository),
    tm_repo: TMRepository = Depends(get_tm_repository)
):
    """Update a row's target text or status (source is READ-ONLY).

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
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

    # P10: Get row with file info via repository (permissions checked inside - returns None if no access)
    row = await repo.get_with_file(row_id)

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Save history before update
    old_target = row["target"]
    old_status = row["status"]

    # Use repository to update the row
    updated_row = await repo.update(
        row_id=row_id,
        target=update.target,
        status=update.status,
        updated_by=current_user["user_id"]
    )

    if not updated_row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Add edit history via repository (commits internally)
    await repo.add_edit_history(
        row_id=row_id,
        user_id=current_user["user_id"],
        old_target=old_target,
        new_target=updated_row.get("target"),
        old_status=old_status,
        new_status=updated_row.get("status")
    )

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
            # P10-REPO: Get project's linked TM via Repository Pattern
            project_id = row["project_id"]
            linked_tm_id = await _get_project_linked_tm(tm_repo, project_id, current_user["user_id"])

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
    project_repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get full project tree structure (folders + files) for File Explorer.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    logger.debug(f"[ROWS] get_project_tree: project_id={project_id}")

    # P10: Get project via repository (permissions checked inside - returns None if no access)
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
