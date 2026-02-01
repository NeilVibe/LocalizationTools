"""
Trash/Recycle Bin endpoints for LDM - EXPLORER-008.

P10: FULL ABSTRACT + REPO Pattern
- All endpoints use Repository Pattern with permissions baked in
- No direct DB access in route endpoints

P10-REPO: Migrated to Repository Pattern (2026-01-13)
- move_to_trash uses TrashRepository.create()
- _restore_* functions use entity repositories
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.repositories import (
    TrashRepository, get_trash_repository,
    FileRepository, get_file_repository,
    FolderRepository, get_folder_repository,
    ProjectRepository, get_project_repository,
    PlatformRepository, get_platform_repository,
    CapabilityRepository, get_capability_repository
)

router = APIRouter(tags=["LDM"])

# Trash retention period (days)
TRASH_RETENTION_DAYS = 30


@router.get("/trash")
async def list_trash(
    trash_repo: TrashRepository = Depends(get_trash_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all items in the recycle bin for the current user.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    Returns items sorted by deletion date (newest first).
    """
    logger.debug(f"[TRASH] list_trash: user_id={current_user['user_id']}")

    items = await trash_repo.get_for_user(current_user["user_id"])

    logger.debug(f"[TRASH] list_trash complete: count={len(items)}")

    return {
        "items": [
            {
                "id": item["id"],
                "item_type": item["item_type"],
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "deleted_at": item.get("deleted_at"),
                "expires_at": item.get("expires_at"),
                "parent_project_id": item.get("parent_project_id"),
                "parent_folder_id": item.get("parent_folder_id")
            }
            for item in items
        ],
        "count": len(items)
    }


@router.post("/trash/{trash_id}/restore")
async def restore_from_trash(
    trash_id: int,
    trash_repo: TrashRepository = Depends(get_trash_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    platform_repo: PlatformRepository = Depends(get_platform_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Restore an item from the recycle bin.

    P10: FULL ABSTRACT - Uses repositories for all entity creation.
    Recreates the item and all its contents from the stored snapshot.
    """
    logger.debug(f"[TRASH] restore_from_trash: trash_id={trash_id}")

    # Get trash item using repository
    trash_item = await trash_repo.get(trash_id)

    if not trash_item:
        raise HTTPException(status_code=404, detail="Trash item not found")

    if trash_item.get("deleted_by") != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Trash item not found")

    if trash_item.get("status") != "trashed":
        raise HTTPException(status_code=400, detail="Item is not in trash")

    item_data = trash_item["item_data"]
    item_type = trash_item["item_type"]

    try:
        if item_type == "file":
            # Restore file and rows (P10-REPO)
            new_file = await _restore_file(
                file_repo, item_data,
                trash_item.get("parent_project_id"),
                trash_item.get("parent_folder_id")
            )
            logger.success(f"[TRASH] File restored: {new_file['name']}")
            restored_id = new_file["id"]

        elif item_type == "folder":
            # Restore folder and all contents (P10-REPO)
            new_folder = await _restore_folder(
                file_repo, folder_repo, item_data,
                trash_item.get("parent_project_id"),
                trash_item.get("parent_folder_id")
            )
            logger.success(f"[TRASH] Folder restored: {new_folder['name']}")
            restored_id = new_folder["id"]

        elif item_type == "project":
            # Restore project and all contents (P10-REPO)
            new_project = await _restore_project(
                file_repo, folder_repo, project_repo, item_data,
                current_user["user_id"]
            )
            logger.success(f"[TRASH] Project restored: {new_project['name']}")
            restored_id = new_project["id"]

        elif item_type == "platform":
            # Restore platform and all projects (P10-REPO)
            new_platform = await _restore_platform(
                file_repo, folder_repo, project_repo, platform_repo, item_data,
                current_user["user_id"]
            )
            logger.success(f"[TRASH] Platform restored: {new_platform['name']}")
            restored_id = new_platform["id"]

        else:
            raise HTTPException(status_code=400, detail=f"Unknown item type: {item_type}")

        # Mark trash item as restored using repository
        await trash_repo.restore(trash_id, current_user["user_id"])

        logger.info(f"[TRASH] restore_from_trash complete: trash_id={trash_id}, restored_id={restored_id}")

        return {
            "success": True,
            "message": f"{item_type.capitalize()} restored successfully",
            "item_type": item_type,
            "restored_id": restored_id
        }

    except Exception as e:
        logger.error(f"[TRASH] Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.delete("/trash/{trash_id}")
async def permanent_delete(
    trash_id: int,
    trash_repo: TrashRepository = Depends(get_trash_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Permanently delete an item from the recycle bin.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    This cannot be undone.
    """
    logger.debug(f"[TRASH] permanent_delete: trash_id={trash_id}")

    deleted = await trash_repo.permanent_delete(trash_id, current_user["user_id"])

    if not deleted:
        raise HTTPException(status_code=404, detail="Trash item not found")

    logger.info(f"[TRASH] permanent_delete complete: trash_id={trash_id}")
    return {"success": True, "message": "Item permanently deleted"}


@router.post("/trash/empty")
async def empty_trash(
    trash_repo: TrashRepository = Depends(get_trash_repository),
    capability_repo: CapabilityRepository = Depends(get_capability_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Empty the entire recycle bin (permanently delete all items).

    P10: FULL ABSTRACT - Uses repository pattern with permissions baked in.
    EXPLORER-009: Requires 'empty_trash' capability.
    """
    logger.debug(f"[TRASH] empty_trash: user_id={current_user['user_id']}")

    # EXPLORER-009: Check capability via repository
    user_id = current_user.get("user_id")
    has_capability = await capability_repo.get_user_capability(user_id, "empty_trash")
    if not has_capability and current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="empty_trash capability required")

    count = await trash_repo.empty_for_user(current_user["user_id"])

    logger.info(f"[TRASH] empty_trash complete: count={count}")
    return {"success": True, "message": f"{count} items permanently deleted"}


# ============== Helper Functions ==============

async def move_to_trash(
    trash_repo: TrashRepository,
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

    P10-REPO: Uses TrashRepository.create() instead of direct model access.
    """
    trash_item = await trash_repo.create(
        item_type=item_type,
        item_id=item_id,
        item_name=item_name,
        item_data=item_data,
        deleted_by=deleted_by,
        parent_project_id=parent_project_id,
        parent_folder_id=parent_folder_id,
        retention_days=TRASH_RETENTION_DAYS
    )
    return trash_item


# ============== Restore Functions (P10-REPO) ==============

async def _restore_file(
    file_repo: FileRepository,
    data: dict,
    project_id: int,
    folder_id: Optional[int]
) -> Dict[str, Any]:
    """
    Restore a file from trash data.

    P10-REPO: Uses FileRepository for all operations.
    """
    # Generate unique name in case original name is taken
    name = await file_repo.generate_unique_name(
        data["name"],
        project_id=project_id,
        folder_id=folder_id
    )

    # Create file via repository
    new_file = await file_repo.create(
        name=name,
        original_filename=data.get("original_filename", name),
        format=data.get("format", "txt"),
        project_id=project_id,
        folder_id=folder_id,
        source_language=data.get("source_language", "ko"),
        target_language=data.get("target_language", "en"),
        extra_data=data.get("extra_data")
    )

    # Restore rows via repository
    rows = data.get("rows", [])
    if rows:
        await file_repo.add_rows(new_file["id"], rows)

    return new_file


async def _restore_folder(
    file_repo: FileRepository,
    folder_repo: FolderRepository,
    data: dict,
    project_id: int,
    parent_id: Optional[int]
) -> Dict[str, Any]:
    """
    Restore a folder and all its contents from trash data.

    P10-REPO: Uses FolderRepository and FileRepository for all operations.
    """
    # Generate unique name (FolderRepository handles auto-rename)
    name = await folder_repo.generate_unique_name(
        data["name"],
        project_id=project_id,
        parent_id=parent_id
    )

    # Create folder via repository
    new_folder = await folder_repo.create(
        name=name,
        project_id=project_id,
        parent_id=parent_id
    )

    # Restore files in this folder
    for file_data in data.get("files", []):
        await _restore_file(file_repo, file_data, project_id, new_folder["id"])

    # Recursively restore subfolders
    for subfolder_data in data.get("subfolders", []):
        await _restore_folder(file_repo, folder_repo, subfolder_data, project_id, new_folder["id"])

    return new_folder


async def _restore_project(
    file_repo: FileRepository,
    folder_repo: FolderRepository,
    project_repo: ProjectRepository,
    data: dict,
    owner_id: int
) -> Dict[str, Any]:
    """
    Restore a project and all its contents from trash data.

    P10-REPO: Uses ProjectRepository, FolderRepository, and FileRepository.
    """
    # Generate unique name
    name = await project_repo.generate_unique_name(
        data["name"],
        platform_id=data.get("platform_id")
    )

    # Create project via repository
    new_project = await project_repo.create(
        name=name,
        owner_id=owner_id,
        description=data.get("description"),
        platform_id=data.get("platform_id"),
        is_restricted=data.get("is_restricted", False)
    )

    # Restore root folders
    for folder_data in data.get("folders", []):
        await _restore_folder(file_repo, folder_repo, folder_data, new_project["id"], None)

    # Restore root files
    for file_data in data.get("files", []):
        await _restore_file(file_repo, file_data, new_project["id"], None)

    return new_project


async def _generate_unique_platform_name(platform_repo: PlatformRepository, base_name: str) -> str:
    """Generate a unique platform name by appending _1, _2, etc. if needed."""
    name = base_name
    counter = 1
    while await platform_repo.check_name_exists(name):
        name = f"{base_name}_{counter}"
        counter += 1
    return name


async def _restore_platform(
    file_repo: FileRepository,
    folder_repo: FolderRepository,
    project_repo: ProjectRepository,
    platform_repo: PlatformRepository,
    data: dict,
    owner_id: int
) -> Dict[str, Any]:
    """
    Restore a platform and all its projects from trash data.

    P10-REPO: Uses all entity repositories.
    """
    # Generate unique name (PlatformRepository doesn't have generate_unique_name)
    name = await _generate_unique_platform_name(platform_repo, data["name"])

    # Create platform via repository
    new_platform = await platform_repo.create(
        name=name,
        owner_id=owner_id,
        description=data.get("description"),
        is_restricted=data.get("is_restricted", False)
    )

    # Restore projects
    for project_data in data.get("projects", []):
        # Update project data with new platform_id
        project_data["platform_id"] = new_platform["id"]
        await _restore_project(file_repo, folder_repo, project_repo, project_data, owner_id)

    return new_platform
