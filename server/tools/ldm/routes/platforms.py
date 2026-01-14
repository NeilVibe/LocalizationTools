"""Platform CRUD endpoints for TM Hierarchy System.

P10: FULL ABSTRACT + REPO Pattern
- Main endpoints use Repository Pattern with permissions baked in
- Admin access management endpoints use get_async_db (complex access grants)
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

# P10: get_async_db only needed for admin access management routes (3 remaining)
from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
# P10: Access management functions still use db directly (admin-only)
from server.tools.ldm.permissions import (
    grant_platform_access,
    revoke_platform_access,
    get_platform_access_list,
)
from server.repositories import (
    PlatformRepository, get_platform_repository,
    ProjectRepository, get_project_repository,
    FolderRepository, get_folder_repository,
    FileRepository, get_file_repository,
    TrashRepository, get_trash_repository,
    CapabilityRepository, get_capability_repository
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Schemas
# =============================================================================

class PlatformCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PlatformResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    project_count: int = 0
    is_restricted: bool = False  # DESIGN-001
    owner_id: Optional[int] = None  # For admin UI

    class Config:
        from_attributes = True


class PlatformListResponse(BaseModel):
    platforms: List[PlatformResponse]
    total: int


class AccessGrantRequest(BaseModel):
    """Request to grant access to users."""
    user_ids: List[int]


class AccessUserResponse(BaseModel):
    """User with access to a resource."""
    user_id: int
    username: str
    full_name: Optional[str] = None
    access_level: str = "full"
    granted_at: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/platforms", response_model=PlatformListResponse)
async def list_platforms(
    repo: PlatformRepository = Depends(get_platform_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all platforms the user can access.
    DESIGN-001: Public by default - shows all public + owned + granted platforms.

    P10: FULL ABSTRACT - Uses PlatformRepository.get_accessible() with permissions baked in.
    """
    logger.debug(f"[PLATFORM] list_platforms called: user_id={current_user.get('user_id')}")

    # P10: Use repository to get accessible platforms (permissions baked in)
    platforms = await repo.get_accessible(include_projects=True)

    platform_list = [
        PlatformResponse(
            id=p["id"],
            name=p["name"],
            description=p.get("description"),
            project_count=p.get("project_count", 0),
            is_restricted=p.get("is_restricted", False),
            owner_id=p.get("owner_id")
        )
        for p in platforms
    ]

    logger.debug(f"[PLATFORM] list_platforms result: count={len(platform_list)}")
    return PlatformListResponse(platforms=platform_list, total=len(platform_list))


@router.post("/platforms", response_model=PlatformResponse, status_code=201)
async def create_platform(
    platform: PlatformCreate,
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Create a new platform.

    P10: FULL ABSTRACT - Uses PlatformRepository for all operations.
    """
    logger.debug(f"[PLATFORM] create called: name='{platform.name}', user_id={current_user.get('user_id')}")

    try:
        # Use repository to create platform (handles uniqueness check)
        new_platform = await repo.create(
            name=platform.name,
            owner_id=current_user["user_id"],
            description=platform.description,
            is_restricted=False  # DESIGN-001: Public by default
        )

        logger.success(f"[PLATFORM] Created: id={new_platform['id']}, name='{platform.name}'")

        return PlatformResponse(
            id=new_platform["id"],
            name=new_platform["name"],
            description=new_platform["description"],
            project_count=0,
            is_restricted=new_platform["is_restricted"],
            owner_id=new_platform["owner_id"]
        )
    except ValueError as e:
        logger.warning(f"[PLATFORM] Create failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/platforms/{platform_id}", response_model=PlatformResponse)
async def get_platform(
    platform_id: int,
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Get a specific platform by ID.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    logger.debug(f"[PLATFORM] get called: platform_id={platform_id}, user_id={current_user.get('user_id')}")

    # P10: Get platform via repository (permissions checked inside - returns None if no access)
    platform = await repo.get_with_project_count(platform_id)

    if not platform:
        logger.debug(f"[PLATFORM] Not found or access denied: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    return PlatformResponse(
        id=platform["id"],
        name=platform["name"],
        description=platform["description"],
        project_count=platform["project_count"],
        is_restricted=platform["is_restricted"],
        owner_id=platform["owner_id"]
    )


@router.patch("/platforms/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: int,
    update: PlatformUpdate,
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Update a platform (name or description).

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    logger.debug(f"[PLATFORM] update called: platform_id={platform_id}, name={update.name}, user_id={current_user.get('user_id')}")

    # P10: First check access via repository
    existing = await repo.get(platform_id)
    if not existing:
        logger.debug(f"[PLATFORM] Update access denied or not found: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    try:
        # Use repository to update platform (handles uniqueness check)
        platform = await repo.update(
            platform_id,
            name=update.name,
            description=update.description
        )

        if not platform:
            logger.warning(f"[PLATFORM] Update target not found: platform_id={platform_id}")
            raise HTTPException(status_code=404, detail="Platform not found")

        logger.success(f"[PLATFORM] Updated: id={platform_id}, name='{platform['name']}'")

        # Get project count for response
        platform_with_count = await repo.get_with_project_count(platform_id)

        return PlatformResponse(
            id=platform["id"],
            name=platform["name"],
            description=platform["description"],
            project_count=platform_with_count["project_count"] if platform_with_count else 0,
            is_restricted=platform["is_restricted"],
            owner_id=platform["owner_id"]
        )
    except ValueError as e:
        logger.warning(f"[PLATFORM] Update failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Trash Serialization Helpers (P10-REPO: Repository-based)
# =============================================================================

async def _serialize_file_for_trash_repo(
    file_repo: FileRepository,
    file_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serialize a file and its rows for trash storage.
    P10-REPO: Uses FileRepository instead of direct SQLAlchemy.
    """
    rows = await file_repo.get_rows_for_export(file_dict["id"])

    return {
        "name": file_dict["name"],
        "original_filename": file_dict.get("original_filename"),
        "format": file_dict.get("format"),
        "source_language": file_dict.get("source_language"),
        "target_language": file_dict.get("target_language"),
        "row_count": file_dict.get("row_count", len(rows)),
        "extra_data": file_dict.get("extra_data"),
        "rows": [
            {
                "row_num": r.get("row_num"),
                "string_id": r.get("string_id"),
                "source": r.get("source"),
                "target": r.get("target"),
                "status": r.get("status"),
                "extra_data": r.get("extra_data")
            }
            for r in rows
        ]
    }


async def _serialize_folder_for_trash_repo(
    folder_repo: FolderRepository,
    file_repo: FileRepository,
    folder_id: int,
    folder_name: str
) -> Dict[str, Any]:
    """
    Serialize a folder and all its contents for trash storage.
    P10-REPO: Uses FolderRepository and FileRepository.
    """
    folder_with_contents = await folder_repo.get_with_contents(folder_id)

    if not folder_with_contents:
        return {"name": folder_name, "files": [], "subfolders": []}

    files_data = []
    for file_dict in folder_with_contents.get("files", []):
        full_file = await file_repo.get(file_dict["id"])
        if full_file:
            file_data = await _serialize_file_for_trash_repo(file_repo, full_file)
            files_data.append(file_data)

    subfolders_data = []
    for subfolder in folder_with_contents.get("subfolders", []):
        subfolder_data = await _serialize_folder_for_trash_repo(
            folder_repo, file_repo,
            subfolder["id"], subfolder["name"]
        )
        subfolders_data.append(subfolder_data)

    return {
        "name": folder_name,
        "files": files_data,
        "subfolders": subfolders_data
    }


async def _serialize_project_for_trash_repo(
    project_repo: ProjectRepository,
    folder_repo: FolderRepository,
    file_repo: FileRepository,
    project_id: int
) -> Dict[str, Any]:
    """
    Serialize a project and all its contents for trash storage.
    P10-REPO: Uses all entity repositories.
    """
    project = await project_repo.get(project_id)
    if not project:
        return {}

    all_folders = await folder_repo.get_all(project_id)
    root_folders = [f for f in all_folders if f.get("parent_id") is None]

    folders_data = []
    for folder in root_folders:
        folder_data = await _serialize_folder_for_trash_repo(
            folder_repo, file_repo,
            folder["id"], folder["name"]
        )
        folders_data.append(folder_data)

    all_files = await file_repo.get_all(project_id=project_id, limit=10000)
    root_files = [f for f in all_files if f.get("folder_id") is None]

    files_data = []
    for file_dict in root_files:
        file_data = await _serialize_file_for_trash_repo(file_repo, file_dict)
        files_data.append(file_data)

    return {
        "name": project["name"],
        "description": project.get("description"),
        "platform_id": project.get("platform_id"),
        "is_restricted": project.get("is_restricted", False),
        "folders": folders_data,
        "files": files_data
    }


async def _serialize_platform_for_trash_repo(
    platform_repo: PlatformRepository,
    project_repo: ProjectRepository,
    folder_repo: FolderRepository,
    file_repo: FileRepository,
    platform_id: int
) -> Dict[str, Any]:
    """
    Serialize a platform and all its projects for trash storage.
    P10-REPO: Uses all entity repositories.
    """
    platform = await platform_repo.get(platform_id)
    if not platform:
        return {}

    # Get all projects in this platform
    all_projects = await project_repo.get_all(platform_id=platform_id)

    projects_data = []
    for project in all_projects:
        project_data = await _serialize_project_for_trash_repo(
            project_repo, folder_repo, file_repo,
            project["id"]
        )
        projects_data.append(project_data)

    return {
        "name": platform["name"],
        "description": platform.get("description"),
        "is_restricted": platform.get("is_restricted", False),
        "projects": projects_data
    }


@router.delete("/platforms/{platform_id}")
async def delete_platform(
    platform_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    trash_repo: TrashRepository = Depends(get_trash_repository),
    capability_repo: CapabilityRepository = Depends(get_capability_repository)
):
    """
    Delete a platform.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.
    Projects under this platform will have their platform_id set to NULL (unassigned).
    EXPLORER-009: Requires 'delete_platform' capability.

    P10: FULL ABSTRACT - Uses Repository Pattern with permissions baked in.
    """
    logger.debug(f"[PLATFORM] delete called: platform_id={platform_id}, permanent={permanent}, user_id={current_user.get('user_id')}")

    # P10: Check access via repository
    platform_check = await repo.get(platform_id)
    if not platform_check:
        logger.debug(f"[PLATFORM] Delete access denied or not found: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    # EXPLORER-009: Check capability for privileged operation via repository
    user_id = current_user.get("user_id")
    has_capability = await capability_repo.get_user_capability(user_id, "delete_platform")
    if not has_capability and current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="delete_platform capability required")

    # Get platform with project count for response
    platform = await repo.get_with_project_count(platform_id)

    if not platform:
        logger.warning(f"[PLATFORM] Delete target not found: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    platform_name = platform["name"]
    project_count = platform["project_count"]

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        from .trash import move_to_trash

        # Serialize platform data using repository-based helper (P10-REPO)
        platform_data = await _serialize_platform_for_trash_repo(
            repo, project_repo, folder_repo, file_repo, platform_id
        )

        # Move to trash (P10-REPO: uses TrashRepository)
        await move_to_trash(
            trash_repo,
            item_type="platform",
            item_id=platform["id"],
            item_name=platform["name"],
            item_data=platform_data,
            parent_project_id=None,
            parent_folder_id=None,
            deleted_by=current_user["user_id"]
        )

    # Use repository to delete (handles unassigning projects)
    await repo.delete(platform_id)

    action = "permanently deleted" if permanent else "moved to trash"
    logger.success(f"[PLATFORM] Deleted ({action}): id={platform_id}, name='{platform_name}', projects_unassigned={project_count}")

    return {
        "success": True,
        "platform_id": platform_id,
        "projects_unassigned": project_count
    }


# =============================================================================
# Project-Platform Assignment
# =============================================================================

@router.patch("/projects/{project_id}/platform")
async def assign_project_to_platform(
    project_id: int,
    platform_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository),
    project_repo: ProjectRepository = Depends(get_project_repository)
):
    """
    Assign a project to a platform (or unassign if platform_id is None).

    P10: FULL ABSTRACT - Permission checks via repositories.
    """
    logger.debug(f"[PLATFORM] assign_project called: project_id={project_id}, platform_id={platform_id}, user_id={current_user.get('user_id')}")

    # P10: Check project access via repository
    project = await project_repo.get(project_id)
    if not project:
        logger.debug(f"[PLATFORM] Project access denied or not found: project_id={project_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    # P10: Check platform access if assigning
    if platform_id is not None:
        platform = await repo.get(platform_id)
        if not platform:
            logger.debug(f"[PLATFORM] Platform access denied or not found: platform_id={platform_id}")
            raise HTTPException(status_code=404, detail="Platform not found")

    # Use repository to assign project
    success = await repo.assign_project(project_id, platform_id)

    if not success:
        logger.warning(f"[PLATFORM] Assignment failed: project_id={project_id}, platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Project or platform not found")

    action = f"assigned to platform {platform_id}" if platform_id else "unassigned from platform"
    logger.success(f"[PLATFORM] Project {project_id} {action}")

    return {
        "success": True,
        "project_id": project_id,
        "platform_id": platform_id
    }


# =============================================================================
# DESIGN-001: Platform Restriction Management (Admin Only)
# =============================================================================

@router.put("/platforms/{platform_id}/restriction")
async def set_platform_restriction(
    platform_id: int,
    is_restricted: bool,
    admin: dict = Depends(require_admin_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Toggle restriction on a platform. Admin only.
    When restricted, only assigned users can access.

    P10: FULL ABSTRACT - Admin routes bypass permission checks but use repository.
    """
    logger.debug(f"[PLATFORM] set_restriction called: platform_id={platform_id}, is_restricted={is_restricted}, admin={admin['username']}")

    # Use repository to set restriction
    platform = await repo.set_restriction(platform_id, is_restricted)

    if not platform:
        logger.warning(f"[PLATFORM] Platform not found for restriction toggle: id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    status = "restricted" if is_restricted else "public"
    logger.success(f"[PLATFORM] Platform {platform_id} set to {status} by admin {admin['username']}")

    return {
        "success": True,
        "platform_id": platform_id,
        "is_restricted": is_restricted
    }


@router.get("/platforms/{platform_id}/access", response_model=List[AccessUserResponse])
async def list_platform_access(
    platform_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    List users with access to a restricted platform. Admin only.

    Repository Pattern: Uses PlatformRepository for existence check.
    """
    logger.debug(f"[PLATFORM] list_access called: platform_id={platform_id}, admin={admin['username']}")

    # Use repository to check existence
    platform = await repo.get(platform_id)
    if not platform:
        logger.warning(f"[PLATFORM] Platform not found for access list: id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    access_list = await get_platform_access_list(db, platform_id)
    logger.debug(f"[PLATFORM] Access list retrieved: platform_id={platform_id}, users={len(access_list)}")
    return [AccessUserResponse(**item) for item in access_list]


@router.post("/platforms/{platform_id}/access")
async def grant_platform_access_endpoint(
    platform_id: int,
    request: AccessGrantRequest,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Grant users access to a restricted platform. Admin only.

    Repository Pattern: Uses PlatformRepository for existence check.
    """
    logger.debug(f"[PLATFORM] grant_access called: platform_id={platform_id}, user_ids={request.user_ids}, admin={admin['username']}")

    # Use repository to check existence
    platform = await repo.get(platform_id)
    if not platform:
        logger.warning(f"[PLATFORM] Platform not found for access grant: id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    count = await grant_platform_access(db, platform_id, request.user_ids, admin["user_id"])
    logger.success(f"[PLATFORM] Access granted: platform_id={platform_id}, users_granted={count}")

    return {
        "success": True,
        "platform_id": platform_id,
        "users_granted": count
    }


@router.delete("/platforms/{platform_id}/access/{user_id}")
async def revoke_platform_access_endpoint(
    platform_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Revoke user access from a restricted platform. Admin only.

    Repository Pattern: Uses PlatformRepository for existence check.
    """
    logger.debug(f"[PLATFORM] revoke_access called: platform_id={platform_id}, user_id={user_id}, admin={admin['username']}")

    # Use repository to check existence
    platform = await repo.get(platform_id)
    if not platform:
        logger.warning(f"[PLATFORM] Platform not found for access revoke: id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    revoked = await revoke_platform_access(db, platform_id, user_id)
    if revoked:
        logger.success(f"[PLATFORM] Access revoked: platform_id={platform_id}, user_id={user_id}")
    else:
        logger.debug(f"[PLATFORM] No access to revoke: platform_id={platform_id}, user_id={user_id}")

    return {
        "success": revoked,
        "platform_id": platform_id,
        "user_id": user_id
    }
