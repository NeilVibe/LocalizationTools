"""Platform CRUD endpoints for TM Hierarchy System.

Repository Pattern: Uses PlatformRepository for database abstraction.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.database.models import LDMPlatform
from server.tools.ldm.permissions import (
    get_accessible_platforms,
    can_access_platform,
    grant_platform_access,
    revoke_platform_access,
    get_platform_access_list,
)
from server.repositories import PlatformRepository, get_platform_repository

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all platforms the user can access.
    DESIGN-001: Public by default - shows all public + owned + granted platforms.

    Note: Uses permission helper get_accessible_platforms which handles
    complex access control logic (public + owned + granted).
    """
    logger.debug(f"[PLATFORM] list_platforms called: user_id={current_user.get('user_id')}")

    # Use permission helper to get accessible platforms
    platforms = await get_accessible_platforms(db, current_user, include_projects=True)

    platform_list = [
        PlatformResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            project_count=len(p.projects) if p.projects else 0,
            is_restricted=p.is_restricted,
            owner_id=p.owner_id
        )
        for p in platforms
    ]

    logger.debug(f"[PLATFORM] list_platforms result: count={len(platform_list)}")
    return PlatformListResponse(platforms=platform_list, total=len(platform_list))


@router.post("/platforms", response_model=PlatformResponse, status_code=201)
async def create_platform(
    platform: PlatformCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Create a new platform.

    Repository Pattern: Uses PlatformRepository for database abstraction.
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Get a specific platform by ID.

    Repository Pattern: Uses PlatformRepository for database abstraction.
    """
    logger.debug(f"[PLATFORM] get called: platform_id={platform_id}, user_id={current_user.get('user_id')}")

    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        logger.debug(f"[PLATFORM] Access denied: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    # Use repository to get platform with project count
    platform = await repo.get_with_project_count(platform_id)

    if not platform:
        logger.warning(f"[PLATFORM] Not found: platform_id={platform_id}")
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """Update a platform (name or description).

    Repository Pattern: Uses PlatformRepository for database abstraction.
    """
    logger.debug(f"[PLATFORM] update called: platform_id={platform_id}, name={update.name}, user_id={current_user.get('user_id')}")

    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        logger.debug(f"[PLATFORM] Update access denied: platform_id={platform_id}")
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


@router.delete("/platforms/{platform_id}")
async def delete_platform(
    platform_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Delete a platform.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.
    Projects under this platform will have their platform_id set to NULL (unassigned).
    EXPLORER-009: Requires 'delete_platform' capability.

    Repository Pattern: Uses PlatformRepository for database abstraction.
    Note: Trash serialization remains here as it needs SQLAlchemy objects.
    """
    logger.debug(f"[PLATFORM] delete called: platform_id={platform_id}, permanent={permanent}, user_id={current_user.get('user_id')}")

    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        logger.debug(f"[PLATFORM] Delete access denied: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    # EXPLORER-009: Check capability for privileged operation
    from ..permissions import require_capability
    await require_capability(db, current_user, "delete_platform")

    # Get platform with project count for response
    platform = await repo.get_with_project_count(platform_id)

    if not platform:
        logger.warning(f"[PLATFORM] Delete target not found: platform_id={platform_id}")
        raise HTTPException(status_code=404, detail="Platform not found")

    platform_name = platform["name"]
    project_count = platform["project_count"]

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        # Note: Trash requires SQLAlchemy objects for serialization
        from .trash import move_to_trash, serialize_platform_for_trash
        result = await db.execute(
            select(LDMPlatform)
            .options(selectinload(LDMPlatform.projects))
            .where(LDMPlatform.id == platform_id)
        )
        platform_obj = result.scalar_one_or_none()

        if platform_obj:
            # Serialize platform data for restore (includes project references)
            platform_data = await serialize_platform_for_trash(db, platform_obj)

            # Move to trash
            await move_to_trash(
                db,
                item_type="platform",
                item_id=platform_obj.id,
                item_name=platform_obj.name,
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Assign a project to a platform (or unassign if platform_id is None).

    Repository Pattern: Uses PlatformRepository for database abstraction.
    """
    logger.debug(f"[PLATFORM] assign_project called: project_id={project_id}, platform_id={platform_id}, user_id={current_user.get('user_id')}")

    from server.tools.ldm.permissions import can_access_project

    # DESIGN-001: Check project access
    if not await can_access_project(db, project_id, current_user):
        logger.debug(f"[PLATFORM] Project access denied: project_id={project_id}")
        raise HTTPException(status_code=404, detail="Resource not found")

    # DESIGN-001: Check platform access if assigning
    if platform_id is not None:
        if not await can_access_platform(db, platform_id, current_user):
            logger.debug(f"[PLATFORM] Platform access denied for assignment: platform_id={platform_id}")
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
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: PlatformRepository = Depends(get_platform_repository)
):
    """
    Toggle restriction on a platform. Admin only.
    When restricted, only assigned users can access.

    Repository Pattern: Uses PlatformRepository for database abstraction.
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
