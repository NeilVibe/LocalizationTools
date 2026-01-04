"""Trash/Recycle Bin endpoints for LDM - EXPLORER-008."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import (
    LDMProject, LDMFolder, LDMFile, LDMRow, LDMTrash, LDMPlatform
)

router = APIRouter(tags=["LDM"])

# Trash retention period (days)
TRASH_RETENTION_DAYS = 30


@router.get("/trash")
async def list_trash(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all items in the recycle bin for the current user.
    Returns items sorted by deletion date (newest first).
    """
    result = await db.execute(
        select(LDMTrash)
        .where(
            LDMTrash.deleted_by == current_user["user_id"],
            LDMTrash.status == "trashed"
        )
        .order_by(LDMTrash.deleted_at.desc())
    )
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "item_type": item.item_type,
                "item_id": item.item_id,
                "item_name": item.item_name,
                "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "parent_project_id": item.parent_project_id,
                "parent_folder_id": item.parent_folder_id
            }
            for item in items
        ],
        "count": len(items)
    }


@router.post("/trash/{trash_id}/restore")
async def restore_from_trash(
    trash_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Restore an item from the recycle bin.
    Recreates the item and all its contents from the stored snapshot.
    """
    # Get trash item
    result = await db.execute(
        select(LDMTrash).where(
            LDMTrash.id == trash_id,
            LDMTrash.deleted_by == current_user["user_id"],
            LDMTrash.status == "trashed"
        )
    )
    trash_item = result.scalar_one_or_none()

    if not trash_item:
        raise HTTPException(status_code=404, detail="Trash item not found")

    item_data = trash_item.item_data
    item_type = trash_item.item_type

    try:
        if item_type == "file":
            # Restore file and rows
            new_file = await _restore_file(db, item_data, trash_item.parent_project_id, trash_item.parent_folder_id)
            logger.success(f"File restored from trash: {new_file.name}")
            restored_id = new_file.id

        elif item_type == "folder":
            # Restore folder and all contents
            new_folder = await _restore_folder(db, item_data, trash_item.parent_project_id, trash_item.parent_folder_id)
            logger.success(f"Folder restored from trash: {new_folder.name}")
            restored_id = new_folder.id

        elif item_type == "project":
            # Restore project and all contents
            new_project = await _restore_project(db, item_data)
            logger.success(f"Project restored from trash: {new_project.name}")
            restored_id = new_project.id

        elif item_type == "platform":
            # Restore platform and all projects
            new_platform = await _restore_platform(db, item_data)
            logger.success(f"Platform restored from trash: {new_platform.name}")
            restored_id = new_platform.id

        else:
            raise HTTPException(status_code=400, detail=f"Unknown item type: {item_type}")

        # Mark trash item as restored
        trash_item.status = "restored"
        await db.commit()

        return {
            "success": True,
            "message": f"{item_type.capitalize()} restored successfully",
            "item_type": item_type,
            "restored_id": restored_id
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.delete("/trash/{trash_id}")
async def permanent_delete(
    trash_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Permanently delete an item from the recycle bin.
    This cannot be undone.
    """
    result = await db.execute(
        select(LDMTrash).where(
            LDMTrash.id == trash_id,
            LDMTrash.deleted_by == current_user["user_id"],
            LDMTrash.status == "trashed"
        )
    )
    trash_item = result.scalar_one_or_none()

    if not trash_item:
        raise HTTPException(status_code=404, detail="Trash item not found")

    await db.delete(trash_item)
    await db.commit()

    logger.info(f"Trash item permanently deleted: {trash_item.item_name}")
    return {"success": True, "message": "Item permanently deleted"}


@router.post("/trash/empty")
async def empty_trash(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Empty the entire recycle bin (permanently delete all items).
    EXPLORER-009: Requires 'empty_trash' capability.
    """
    # EXPLORER-009: Check capability for privileged operation
    from ..permissions import require_capability
    await require_capability(db, current_user, "empty_trash")

    result = await db.execute(
        delete(LDMTrash).where(
            LDMTrash.deleted_by == current_user["user_id"],
            LDMTrash.status == "trashed"
        )
    )
    await db.commit()

    count = result.rowcount
    logger.info(f"Trash emptied: {count} items permanently deleted")
    return {"success": True, "message": f"{count} items permanently deleted"}


# ============== Helper Functions ==============

async def move_to_trash(
    db: AsyncSession,
    item_type: str,
    item_id: int,
    item_name: str,
    item_data: dict,
    parent_project_id: Optional[int],
    parent_folder_id: Optional[int],
    deleted_by: int
):
    """
    Move an item to trash instead of deleting it.
    Called by the modified delete endpoints.
    """
    expires_at = datetime.utcnow() + timedelta(days=TRASH_RETENTION_DAYS)

    trash_item = LDMTrash(
        item_type=item_type,
        item_id=item_id,
        item_name=item_name,
        item_data=item_data,
        parent_project_id=parent_project_id,
        parent_folder_id=parent_folder_id,
        deleted_by=deleted_by,
        expires_at=expires_at,
        status="trashed"
    )

    db.add(trash_item)
    return trash_item


async def serialize_file_for_trash(db: AsyncSession, file: LDMFile) -> dict:
    """Serialize a file and its rows for trash storage."""
    # Get all rows for this file
    result = await db.execute(
        select(LDMRow).where(LDMRow.file_id == file.id)
    )
    rows = result.scalars().all()

    return {
        "name": file.name,
        "original_filename": file.original_filename,
        "format": file.format,
        "source_language": file.source_language,
        "target_language": file.target_language,
        "row_count": file.row_count,
        "extra_data": file.extra_data,
        "rows": [
            {
                "row_num": r.row_num,
                "string_id": r.string_id,
                "source": r.source,
                "target": r.target,
                "memo": r.memo,
                "status": r.status,
                "extra_data": r.extra_data
            }
            for r in rows
        ]
    }


async def serialize_folder_for_trash(db: AsyncSession, folder: LDMFolder) -> dict:
    """Serialize a folder and all its contents for trash storage."""
    # Get files in this folder
    result = await db.execute(
        select(LDMFile).where(LDMFile.folder_id == folder.id)
    )
    files = result.scalars().all()

    # Serialize each file
    files_data = []
    for file in files:
        files_data.append(await serialize_file_for_trash(db, file))

    # Get subfolders
    result = await db.execute(
        select(LDMFolder).where(LDMFolder.parent_id == folder.id)
    )
    subfolders = result.scalars().all()

    # Recursively serialize subfolders
    subfolders_data = []
    for subfolder in subfolders:
        subfolders_data.append(await serialize_folder_for_trash(db, subfolder))

    return {
        "name": folder.name,
        "files": files_data,
        "subfolders": subfolders_data
    }


async def serialize_project_for_trash(db: AsyncSession, project: LDMProject) -> dict:
    """Serialize a project and all its contents for trash storage."""
    # Get root folders (folders with no parent)
    result = await db.execute(
        select(LDMFolder).where(
            LDMFolder.project_id == project.id,
            LDMFolder.parent_id.is_(None)
        )
    )
    folders = result.scalars().all()

    folders_data = []
    for folder in folders:
        folders_data.append(await serialize_folder_for_trash(db, folder))

    # Get root files (files with no folder)
    result = await db.execute(
        select(LDMFile).where(
            LDMFile.project_id == project.id,
            LDMFile.folder_id.is_(None)
        )
    )
    files = result.scalars().all()

    files_data = []
    for file in files:
        files_data.append(await serialize_file_for_trash(db, file))

    return {
        "name": project.name,
        "description": project.description,
        "platform_id": project.platform_id,
        "is_restricted": project.is_restricted,
        "folders": folders_data,
        "files": files_data
    }


async def serialize_platform_for_trash(db: AsyncSession, platform: LDMPlatform) -> dict:
    """Serialize a platform and all its projects for trash storage."""
    # Get all projects in this platform
    result = await db.execute(
        select(LDMProject).where(LDMProject.platform_id == platform.id)
    )
    projects = result.scalars().all()

    projects_data = []
    for project in projects:
        projects_data.append(await serialize_project_for_trash(db, project))

    return {
        "name": platform.name,
        "description": platform.description,
        "is_restricted": platform.is_restricted,
        "projects": projects_data
    }


# ============== Restore Functions ==============

async def _restore_file(db: AsyncSession, data: dict, project_id: int, folder_id: Optional[int]) -> LDMFile:
    """Restore a file from trash data."""
    from server.tools.ldm.utils.naming import generate_unique_name

    # Generate unique name in case original name is taken
    name = await generate_unique_name(
        db, LDMFile, data["name"],
        project_id=project_id,
        folder_id=folder_id
    )

    new_file = LDMFile(
        name=name,
        original_filename=data.get("original_filename"),
        format=data.get("format"),
        source_language=data.get("source_language"),
        target_language=data.get("target_language"),
        row_count=len(data.get("rows", [])),
        project_id=project_id,
        folder_id=folder_id,
        extra_data=data.get("extra_data")
    )
    db.add(new_file)
    await db.flush()

    # Restore rows
    for row_data in data.get("rows", []):
        new_row = LDMRow(
            file_id=new_file.id,
            row_num=row_data["row_num"],
            string_id=row_data.get("string_id"),
            source=row_data.get("source"),
            target=row_data.get("target"),
            memo=row_data.get("memo"),
            status=row_data.get("status"),
            extra_data=row_data.get("extra_data")
        )
        db.add(new_row)

    return new_file


async def _restore_folder(db: AsyncSession, data: dict, project_id: int, parent_id: Optional[int]) -> LDMFolder:
    """Restore a folder and all its contents from trash data."""
    from server.tools.ldm.utils.naming import generate_unique_name

    # Generate unique name
    name = await generate_unique_name(
        db, LDMFolder, data["name"],
        project_id=project_id,
        parent_id=parent_id
    )

    new_folder = LDMFolder(
        name=name,
        project_id=project_id,
        parent_id=parent_id
    )
    db.add(new_folder)
    await db.flush()

    # Restore files in this folder
    for file_data in data.get("files", []):
        await _restore_file(db, file_data, project_id, new_folder.id)

    # Recursively restore subfolders
    for subfolder_data in data.get("subfolders", []):
        await _restore_folder(db, subfolder_data, project_id, new_folder.id)

    return new_folder


async def _restore_project(db: AsyncSession, data: dict) -> LDMProject:
    """Restore a project and all its contents from trash data."""
    from server.tools.ldm.utils.naming import generate_unique_name

    # Generate unique name
    name = await generate_unique_name(
        db, LDMProject, data["name"],
        platform_id=data.get("platform_id")
    )

    new_project = LDMProject(
        name=name,
        description=data.get("description"),
        platform_id=data.get("platform_id"),
        is_restricted=data.get("is_restricted", False)
    )
    db.add(new_project)
    await db.flush()

    # Restore root folders
    for folder_data in data.get("folders", []):
        await _restore_folder(db, folder_data, new_project.id, None)

    # Restore root files
    for file_data in data.get("files", []):
        await _restore_file(db, file_data, new_project.id, None)

    return new_project


async def _restore_platform(db: AsyncSession, data: dict) -> LDMPlatform:
    """Restore a platform and all its projects from trash data."""
    from server.tools.ldm.utils.naming import generate_unique_name

    # Generate unique name
    name = await generate_unique_name(
        db, LDMPlatform, data["name"]
    )

    new_platform = LDMPlatform(
        name=name,
        description=data.get("description"),
        is_restricted=data.get("is_restricted", False)
    )
    db.add(new_platform)
    await db.flush()

    # Restore projects
    for project_data in data.get("projects", []):
        # Update project data with new platform_id
        project_data["platform_id"] = new_platform.id
        await _restore_project(db, project_data)

    return new_platform
