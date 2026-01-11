"""Folder CRUD endpoints.

Repository Pattern: Uses FolderRepository for database abstraction.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMFolder
from server.tools.ldm.schemas import FolderCreate, FolderResponse, DeleteResponse
from server.tools.ldm.permissions import can_access_project
from server.repositories import FolderRepository, get_folder_repository

router = APIRouter(tags=["LDM"])


@router.get("/projects/{project_id}/folders", response_model=List[FolderResponse])
async def list_folders(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """List all folders in a project.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # Check access permission (includes project existence check)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    # Use repository to get folders
    folders = await repo.get_all(project_id)
    return folders


@router.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """Create a new folder in a project.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # Check access permission (includes project existence check)
    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    # Use repository to create folder (handles auto-rename for duplicates)
    new_folder = await repo.create(
        name=folder.name,
        project_id=folder.project_id,
        parent_id=folder.parent_id
    )

    logger.info(f"[FOLDERS] Folder created: id={new_folder['id']}, name='{new_folder['name']}'")
    return new_folder


@router.get("/folders/{folder_id}")
async def get_folder_contents(
    folder_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """Get folder details and its contents (subfolders + files).

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # Use repository to get folder with contents
    folder = await repo.get_with_contents(folder_id)

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check access permission
    if not await can_access_project(db, folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    return folder


@router.patch("/folders/{folder_id}/rename")
async def rename_folder(
    folder_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """Rename a folder.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # First get folder to check access
    folder = await repo.get(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    try:
        # Use repository to rename (handles uniqueness check)
        await repo.rename(folder_id, name)
        logger.success(f"[FOLDERS] Folder renamed: id={folder_id}, '{folder['name']}' -> '{name}'")
        return {"success": True, "folder_id": folder_id, "name": name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/folders/{folder_id}/move")
async def move_folder(
    folder_id: int,
    parent_folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """
    Move a folder to a different parent folder (or root of project if parent_folder_id is None).

    Used for drag-and-drop folder organization in FileExplorer.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # First get folder to check access
    folder = await repo.get(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    try:
        # Use repository to move (handles validation and circular reference checks)
        await repo.move(folder_id, parent_folder_id)
        logger.success(f"[FOLDERS] Folder moved: id={folder_id}, new_parent={parent_folder_id}")
        return {"success": True, "folder_id": folder_id, "parent_folder_id": parent_folder_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/folders/{folder_id}/move-cross-project")
async def move_folder_cross_project(
    folder_id: int,
    target_project_id: int,
    target_parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """
    EXPLORER-005: Move a folder to a different project.
    Updates the folder and all its contents (subfolders, files) to the new project.
    EXPLORER-009: Requires 'cross_project_move' capability.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # Get source folder
    folder = await repo.get(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check access to source project
    if not await can_access_project(db, folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check access to destination project
    if not await can_access_project(db, target_project_id, current_user):
        raise HTTPException(status_code=404, detail="Destination project not found")

    # EXPLORER-009: Check capability for cross-project move
    from ..permissions import require_capability
    await require_capability(db, current_user, "cross_project_move")

    source_project_id = folder["project_id"]

    try:
        # Use repository to move cross-project (handles validation and recursive updates)
        result = await repo.move_cross_project(folder_id, target_project_id, target_parent_id)

        logger.success(f"[FOLDERS] Folder moved cross-project: id={folder_id}, from project {source_project_id} to {target_project_id}")
        return {
            "success": True,
            "folder_id": folder_id,
            "new_name": result.get("new_name", result.get("name")),
            "target_project_id": target_project_id,
            "target_parent_id": target_parent_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/folders/{folder_id}/copy")
async def copy_folder(
    folder_id: int,
    target_project_id: Optional[int] = None,
    target_parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """
    Copy a folder and all its contents to a different location.
    EXPLORER-001: Ctrl+C/V folder operations.

    If target_project_id is None, copies to same project.
    If target_parent_id is None, copies to project root.
    Auto-renames if duplicate name exists.

    Repository Pattern: Uses FolderRepository for database abstraction.
    """
    # Get source folder
    source_folder = await repo.get(folder_id)
    if not source_folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, source_folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Folder not found")

    # Determine target project
    dest_project_id = target_project_id or source_folder["project_id"]

    # Check access permission for destination
    if target_project_id and target_project_id != source_folder["project_id"]:
        if not await can_access_project(db, target_project_id, current_user):
            raise HTTPException(status_code=404, detail="Destination project not found")

    # Use repository to copy folder (handles recursive copying)
    result = await repo.copy(folder_id, dest_project_id, target_parent_id)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to copy folder")

    logger.success(f"[FOLDERS] Folder copied: {source_folder['name']} -> {result['name']}, id={result['new_folder_id']}, files={result['files_copied']}")
    return {
        "success": True,
        "new_folder_id": result["new_folder_id"],
        "name": result["name"],
        "files_copied": result["files_copied"]
    }


@router.delete("/folders/{folder_id}", response_model=DeleteResponse)
async def delete_folder(
    folder_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: FolderRepository = Depends(get_folder_repository)
):
    """
    Delete a folder and all its contents.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.

    Repository Pattern: Uses FolderRepository for database abstraction.
    Note: Trash serialization remains here as it needs SQLAlchemy objects for complex nesting.
    """
    # Get folder for trash serialization
    folder = await repo.get(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder["project_id"], current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    folder_name = folder["name"]

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        # Note: Trash requires SQLAlchemy objects for serialization, so we get it again
        from .trash import move_to_trash, serialize_folder_for_trash
        result = await db.execute(
            select(LDMFolder).options(selectinload(LDMFolder.project)).where(
                LDMFolder.id == folder_id
            )
        )
        folder_obj = result.scalar_one_or_none()

        if folder_obj:
            # Serialize folder data for restore
            folder_data = await serialize_folder_for_trash(db, folder_obj)

            # Move to trash
            await move_to_trash(
                db,
                item_type="folder",
                item_id=folder_obj.id,
                item_name=folder_obj.name,
                item_data=folder_data,
                parent_project_id=folder_obj.project_id,
                parent_folder_id=folder_obj.parent_id,
                deleted_by=current_user["user_id"]
            )

    # Use repository to delete
    await repo.delete(folder_id)

    action = "permanently deleted" if permanent else "moved to trash"
    logger.info(f"[FOLDERS] Folder {action}: id={folder_id}, name='{folder_name}'")
    return {"message": f"Folder {action}"}
