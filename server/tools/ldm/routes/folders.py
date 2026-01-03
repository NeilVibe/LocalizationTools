"""Folder CRUD endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMProject, LDMFolder
from server.tools.ldm.schemas import FolderCreate, FolderResponse, DeleteResponse
from server.tools.ldm.permissions import can_access_project, can_access_folder

router = APIRouter(tags=["LDM"])


@router.get("/projects/{project_id}/folders", response_model=List[FolderResponse])
async def list_folders(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List all folders in a project."""
    # Verify project exists
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    result = await db.execute(
        select(LDMFolder).where(LDMFolder.project_id == project_id)
    )
    folders = result.scalars().all()

    return folders


@router.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Create a new folder in a project."""
    # Verify project exists
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == folder.project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # DESIGN-001: Check for globally unique folder name (no duplicates anywhere)
    duplicate_query = select(LDMFolder).where(LDMFolder.name == folder.name)
    result = await db.execute(duplicate_query)
    existing_folder = result.scalar_one_or_none()
    if existing_folder:
        raise HTTPException(
            status_code=400,
            detail=f"A folder named '{folder.name}' already exists. Please use a different name."
        )

    new_folder = LDMFolder(
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        name=folder.name
    )

    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)

    logger.info(f"Folder created: id={new_folder.id}, name='{new_folder.name}'")
    return new_folder


@router.get("/folders/{folder_id}")
async def get_folder_contents(
    folder_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get folder details and its contents (subfolders + files)."""
    from server.database.models import LDMFile

    # Get folder with project info
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get subfolders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.parent_id == folder_id)
    )
    subfolders = result.scalars().all()

    # Get files in this folder
    result = await db.execute(
        select(LDMFile).where(LDMFile.folder_id == folder_id)
    )
    files = result.scalars().all()

    return {
        "id": folder.id,
        "name": folder.name,
        "project_id": folder.project_id,
        "parent_id": folder.parent_id,
        "subfolders": [
            {"id": f.id, "name": f.name, "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in subfolders
        ],
        "files": [
            {"id": f.id, "name": f.name, "format": f.format, "row_count": f.row_count,
             "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in files
        ]
    }


@router.patch("/folders/{folder_id}/rename")
async def rename_folder(
    folder_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Rename a folder."""
    # Get folder with project info
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # DESIGN-001: Check for globally unique folder name (no duplicates anywhere)
    duplicate_query = select(LDMFolder).where(
        LDMFolder.name == name,
        LDMFolder.id != folder_id
    )
    result = await db.execute(duplicate_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"A folder named '{name}' already exists. Please use a different name.")

    old_name = folder.name
    folder.name = name
    await db.commit()

    logger.success(f"Folder renamed: id={folder_id}, '{old_name}' -> '{name}'")
    return {"success": True, "folder_id": folder_id, "name": name}


@router.patch("/folders/{folder_id}/move")
async def move_folder(
    folder_id: int,
    parent_folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Move a folder to a different parent folder (or root of project if parent_folder_id is None).

    Used for drag-and-drop folder organization in FileExplorer.
    """
    # Get folder with project info
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Prevent moving folder into itself or its descendants
    if parent_folder_id is not None:
        # Check if target is the folder itself
        if parent_folder_id == folder_id:
            raise HTTPException(status_code=400, detail="Cannot move folder into itself")

        # Check if target folder exists and belongs to same project
        result = await db.execute(
            select(LDMFolder).where(
                LDMFolder.id == parent_folder_id,
                LDMFolder.project_id == folder.project_id
            )
        )
        target_folder = result.scalar_one_or_none()
        if not target_folder:
            raise HTTPException(status_code=404, detail="Target folder not found or invalid")

        # Check if target is a descendant of the folder being moved
        # (prevent circular references)
        current_parent = target_folder.parent_id
        while current_parent is not None:
            if current_parent == folder_id:
                raise HTTPException(status_code=400, detail="Cannot move folder into its own subfolder")
            result = await db.execute(
                select(LDMFolder.parent_id).where(LDMFolder.id == current_parent)
            )
            current_parent = result.scalar_one_or_none()

    # Update folder's parent_id
    folder.parent_id = parent_folder_id
    await db.commit()

    logger.success(f"Folder moved: id={folder_id}, new_parent={parent_folder_id}")
    return {"success": True, "folder_id": folder_id, "parent_folder_id": parent_folder_id}


@router.delete("/folders/{folder_id}", response_model=DeleteResponse)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a folder and all its contents."""
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    await db.delete(folder)
    await db.commit()

    logger.info(f"Folder deleted: id={folder_id}")
    return {"message": "Folder deleted"}
