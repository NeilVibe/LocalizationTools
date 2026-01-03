"""Platform CRUD endpoints for TM Hierarchy System."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.database.models import LDMPlatform, LDMProject
from server.tools.ldm.permissions import (
    get_accessible_platforms,
    can_access_platform,
    grant_platform_access,
    revoke_platform_access,
    get_platform_access_list,
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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all platforms the user can access.
    DESIGN-001: Public by default - shows all public + owned + granted platforms.
    """
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

    return PlatformListResponse(platforms=platform_list, total=len(platform_list))


@router.post("/platforms", response_model=PlatformResponse, status_code=201)
async def create_platform(
    platform: PlatformCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Create a new platform."""
    # DESIGN-001: Check for globally unique name (no duplicates anywhere)
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.name == platform.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Platform '{platform.name}' already exists")

    new_platform = LDMPlatform(
        name=platform.name,
        description=platform.description,
        owner_id=current_user["user_id"],
        is_restricted=False  # DESIGN-001: Public by default
    )
    db.add(new_platform)
    await db.commit()
    await db.refresh(new_platform)

    logger.success(f"Platform created: id={new_platform.id}, name='{platform.name}'")

    return PlatformResponse(
        id=new_platform.id,
        name=new_platform.name,
        description=new_platform.description,
        project_count=0,
        is_restricted=new_platform.is_restricted,
        owner_id=new_platform.owner_id
    )


@router.get("/platforms/{platform_id}", response_model=PlatformResponse)
async def get_platform(
    platform_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get a specific platform by ID."""
    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(LDMPlatform.id == platform_id)
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        description=platform.description,
        project_count=len(platform.projects) if platform.projects else 0,
        is_restricted=platform.is_restricted,
        owner_id=platform.owner_id
    )


@router.patch("/platforms/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: int,
    update: PlatformUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Update a platform (name or description)."""
    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(LDMPlatform.id == platform_id)
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # DESIGN-001: Check for globally unique name if renaming
    if update.name and update.name != platform.name:
        result = await db.execute(
            select(LDMPlatform).where(
                LDMPlatform.name == update.name,
                LDMPlatform.id != platform_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Platform '{update.name}' already exists")
        platform.name = update.name

    if update.description is not None:
        platform.description = update.description

    await db.commit()
    await db.refresh(platform)

    logger.success(f"Platform updated: id={platform_id}")

    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        description=platform.description,
        project_count=len(platform.projects) if platform.projects else 0,
        is_restricted=platform.is_restricted,
        owner_id=platform.owner_id
    )


@router.delete("/platforms/{platform_id}")
async def delete_platform(
    platform_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Delete a platform.
    Projects under this platform will have their platform_id set to NULL (unassigned).
    """
    # DESIGN-001: Check access using permission helper
    if not await can_access_platform(db, platform_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(LDMPlatform.id == platform_id)
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    project_count = len(platform.projects) if platform.projects else 0

    # Projects will be unassigned (platform_id set to NULL via ON DELETE SET NULL)
    await db.delete(platform)
    await db.commit()

    logger.success(f"Platform deleted: id={platform_id}, name='{platform.name}', projects_unassigned={project_count}")

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
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Assign a project to a platform (or unassign if platform_id is None).
    """
    from server.tools.ldm.permissions import can_access_project

    # DESIGN-001: Check project access
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # DESIGN-001: Check platform access if assigning
    if platform_id is not None:
        if not await can_access_platform(db, platform_id, current_user):
            raise HTTPException(status_code=403, detail="Access denied to platform")

        result = await db.execute(
            select(LDMPlatform).where(LDMPlatform.id == platform_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Platform not found")

    project.platform_id = platform_id
    await db.commit()

    action = f"assigned to platform {platform_id}" if platform_id else "unassigned from platform"
    logger.success(f"Project {project_id} {action}")

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
    admin: dict = Depends(require_admin_async)
):
    """
    Toggle restriction on a platform. Admin only.
    When restricted, only assigned users can access.
    """
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.id == platform_id)
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    platform.is_restricted = is_restricted
    await db.commit()

    status = "restricted" if is_restricted else "public"
    logger.success(f"Platform {platform_id} set to {status} by admin {admin['username']}")

    return {
        "success": True,
        "platform_id": platform_id,
        "is_restricted": is_restricted
    }


@router.get("/platforms/{platform_id}/access", response_model=List[AccessUserResponse])
async def list_platform_access(
    platform_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    List users with access to a restricted platform. Admin only.
    """
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.id == platform_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Platform not found")

    access_list = await get_platform_access_list(db, platform_id)
    return [AccessUserResponse(**item) for item in access_list]


@router.post("/platforms/{platform_id}/access")
async def grant_platform_access_endpoint(
    platform_id: int,
    request: AccessGrantRequest,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Grant users access to a restricted platform. Admin only.
    """
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.id == platform_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Platform not found")

    count = await grant_platform_access(db, platform_id, request.user_ids, admin["user_id"])

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
    admin: dict = Depends(require_admin_async)
):
    """
    Revoke user access from a restricted platform. Admin only.
    """
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.id == platform_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Platform not found")

    revoked = await revoke_platform_access(db, platform_id, user_id)

    return {
        "success": revoked,
        "platform_id": platform_id,
        "user_id": user_id
    }
