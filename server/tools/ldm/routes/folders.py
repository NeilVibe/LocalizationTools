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

    # DB-002: Per-parent unique names with auto-rename
    from server.tools.ldm.utils.naming import generate_unique_name
    folder_name = await generate_unique_name(
        db, LDMFolder, folder.name,
        project_id=folder.project_id,
        parent_id=folder.parent_id
    )

    new_folder = LDMFolder(
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        name=folder_name  # DB-002: Use auto-renamed name
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

    # DB-002: Per-parent unique names
    from server.tools.ldm.utils.naming import check_name_exists
    if await check_name_exists(
        db, LDMFolder, name,
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        exclude_id=folder_id
    ):
        raise HTTPException(status_code=400, detail=f"A folder named '{name}' already exists in this location. Please use a different name.")

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


@router.post("/folders/{folder_id}/copy")
async def copy_folder(
    folder_id: int,
    target_project_id: Optional[int] = None,
    target_parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Copy a folder and all its contents to a different location.
    EXPLORER-001: Ctrl+C/V folder operations.

    If target_project_id is None, copies to same project.
    If target_parent_id is None, copies to project root.
    Auto-renames if duplicate name exists.
    """
    # Get source folder
    result = await db.execute(
        select(LDMFolder).options(selectinload(LDMFolder.project)).where(
            LDMFolder.id == folder_id
        )
    )
    source_folder = result.scalar_one_or_none()

    if not source_folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not await can_access_project(db, source_folder.project_id, current_user):
        raise HTTPException(status_code=404, detail="Folder not found")

    # Determine target project
    dest_project_id = target_project_id or source_folder.project_id

    # Check access permission for destination
    if target_project_id and target_project_id != source_folder.project_id:
        if not await can_access_project(db, target_project_id, current_user):
            raise HTTPException(status_code=404, detail="Destination project not found")

    # Generate unique name for copy
    from server.tools.ldm.utils.naming import generate_unique_name
    new_name = await generate_unique_name(
        db, LDMFolder, source_folder.name,
        project_id=dest_project_id,
        parent_id=target_parent_id
    )

    # Create copy of folder
    new_folder = LDMFolder(
        name=new_name,
        project_id=dest_project_id,
        parent_id=target_parent_id
    )
    db.add(new_folder)
    await db.flush()

    # Copy all files in this folder
    result = await db.execute(
        select(LDMFile).where(LDMFile.folder_id == folder_id)
    )
    files = result.scalars().all()

    copied_files = 0
    for file in files:
        # Generate unique name for each file
        file_name = await generate_unique_name(
            db, LDMFile, file.name,
            project_id=dest_project_id,
            folder_id=new_folder.id
        )

        new_file = LDMFile(
            name=file_name,
            original_filename=file.original_filename,
            format=file.format,
            source_language=file.source_language,
            target_language=file.target_language,
            row_count=file.row_count,
            project_id=dest_project_id,
            folder_id=new_folder.id,
            extra_data=file.extra_data
        )
        db.add(new_file)
        await db.flush()

        # Copy rows for this file
        from server.database.models import LDMRow
        result = await db.execute(
            select(LDMRow).where(LDMRow.file_id == file.id)
        )
        rows = result.scalars().all()
        for row in rows:
            new_row = LDMRow(
                file_id=new_file.id,
                row_num=row.row_num,
                string_id=row.string_id,
                source=row.source,
                target=row.target,
                memo=row.memo,
                status=row.status,
                extra_data=row.extra_data
            )
            db.add(new_row)
        copied_files += 1

    # Recursively copy subfolders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.parent_id == folder_id)
    )
    subfolders = result.scalars().all()

    for subfolder in subfolders:
        # Recursive copy (simplified - calls this same logic)
        await _copy_folder_recursive(db, subfolder.id, dest_project_id, new_folder.id, current_user)

    await db.commit()
    await db.refresh(new_folder)

    logger.success(f"Folder copied: {source_folder.name} -> {new_folder.name}, id={new_folder.id}, files={copied_files}")
    return {
        "success": True,
        "new_folder_id": new_folder.id,
        "name": new_folder.name,
        "files_copied": copied_files
    }


async def _copy_folder_recursive(db, folder_id: int, dest_project_id: int, dest_parent_id: int, current_user: dict):
    """Helper function to recursively copy folder contents."""
    from server.tools.ldm.utils.naming import generate_unique_name
    from server.database.models import LDMRow

    result = await db.execute(
        select(LDMFolder).where(LDMFolder.id == folder_id)
    )
    source_folder = result.scalar_one_or_none()
    if not source_folder:
        return

    # Generate unique name
    new_name = await generate_unique_name(
        db, LDMFolder, source_folder.name,
        project_id=dest_project_id,
        parent_id=dest_parent_id
    )

    # Create copy
    new_folder = LDMFolder(
        name=new_name,
        project_id=dest_project_id,
        parent_id=dest_parent_id
    )
    db.add(new_folder)
    await db.flush()

    # Copy files
    result = await db.execute(
        select(LDMFile).where(LDMFile.folder_id == folder_id)
    )
    files = result.scalars().all()

    for file in files:
        file_name = await generate_unique_name(
            db, LDMFile, file.name,
            project_id=dest_project_id,
            folder_id=new_folder.id
        )

        new_file = LDMFile(
            name=file_name,
            original_filename=file.original_filename,
            format=file.format,
            source_language=file.source_language,
            target_language=file.target_language,
            row_count=file.row_count,
            project_id=dest_project_id,
            folder_id=new_folder.id,
            extra_data=file.extra_data
        )
        db.add(new_file)
        await db.flush()

        # Copy rows
        result = await db.execute(
            select(LDMRow).where(LDMRow.file_id == file.id)
        )
        rows = result.scalars().all()
        for row in rows:
            new_row = LDMRow(
                file_id=new_file.id,
                row_num=row.row_num,
                string_id=row.string_id,
                source=row.source,
                target=row.target,
                memo=row.memo,
                status=row.status,
                extra_data=row.extra_data
            )
            db.add(new_row)

    # Copy subfolders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.parent_id == folder_id)
    )
    subfolders = result.scalars().all()

    for subfolder in subfolders:
        await _copy_folder_recursive(db, subfolder.id, dest_project_id, new_folder.id, current_user)


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
