"""Platform CRUD endpoints for TM Hierarchy System."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMPlatform, LDMProject

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

    class Config:
        from_attributes = True


class PlatformListResponse(BaseModel):
    platforms: List[PlatformResponse]
    total: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/platforms", response_model=PlatformListResponse)
async def list_platforms(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all platforms for the current user.
    Includes project count for each platform.
    """
    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(LDMPlatform.owner_id == current_user["user_id"])
        .order_by(LDMPlatform.name)
    )
    platforms = result.scalars().all()

    platform_list = [
        PlatformResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            project_count=len(p.projects) if p.projects else 0
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
    # Check for duplicate name
    result = await db.execute(
        select(LDMPlatform).where(
            LDMPlatform.owner_id == current_user["user_id"],
            LDMPlatform.name == platform.name
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Platform '{platform.name}' already exists")

    new_platform = LDMPlatform(
        name=platform.name,
        description=platform.description,
        owner_id=current_user["user_id"]
    )
    db.add(new_platform)
    await db.commit()
    await db.refresh(new_platform)

    logger.success(f"Platform created: id={new_platform.id}, name='{platform.name}'")

    return PlatformResponse(
        id=new_platform.id,
        name=new_platform.name,
        description=new_platform.description,
        project_count=0
    )


@router.get("/platforms/{platform_id}", response_model=PlatformResponse)
async def get_platform(
    platform_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get a specific platform by ID."""
    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(
            LDMPlatform.id == platform_id,
            LDMPlatform.owner_id == current_user["user_id"]
        )
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        description=platform.description,
        project_count=len(platform.projects) if platform.projects else 0
    )


@router.patch("/platforms/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: int,
    update: PlatformUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Update a platform (name or description)."""
    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(
            LDMPlatform.id == platform_id,
            LDMPlatform.owner_id == current_user["user_id"]
        )
    )
    platform = result.scalar_one_or_none()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Check for duplicate name if renaming
    if update.name and update.name != platform.name:
        result = await db.execute(
            select(LDMPlatform).where(
                LDMPlatform.owner_id == current_user["user_id"],
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
        project_count=len(platform.projects) if platform.projects else 0
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
    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects))
        .where(
            LDMPlatform.id == platform_id,
            LDMPlatform.owner_id == current_user["user_id"]
        )
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
    # Get project
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify platform exists if assigning
    if platform_id is not None:
        result = await db.execute(
            select(LDMPlatform).where(
                LDMPlatform.id == platform_id,
                LDMPlatform.owner_id == current_user["user_id"]
            )
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
