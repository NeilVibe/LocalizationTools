"""Project CRUD endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.database.models import LDMProject
from server.tools.ldm.schemas import ProjectCreate, ProjectResponse, DeleteResponse
from server.tools.ldm.permissions import (
    get_accessible_projects,
    can_access_project,
    grant_project_access,
    revoke_project_access,
    get_project_access_list,
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Schemas for Admin Access Control
# =============================================================================

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

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    List all projects the user can access.
    DESIGN-001: Public by default - shows all public + owned + granted projects.
    """
    user_id = current_user["user_id"]
    logger.info(f"Listing projects for user {user_id}")

    # Use permission helper to get accessible projects
    projects = await get_accessible_projects(db, current_user)

    return projects


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Create a new project."""
    user_id = current_user["user_id"]
    logger.info(f"Creating project '{project.name}' for user {user_id}")

    # DESIGN-001: Check for globally unique project name
    result = await db.execute(
        select(LDMProject).where(LDMProject.name == project.name)
    )
    existing_project = result.scalar_one_or_none()
    if existing_project:
        raise HTTPException(
            status_code=400,
            detail=f"A project named '{project.name}' already exists. Please use a different name."
        )

    new_project = LDMProject(
        name=project.name,
        description=project.description,
        owner_id=current_user["user_id"],
        is_restricted=False  # DESIGN-001: Public by default
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    logger.success(f"Project created: id={new_project.id}, name='{new_project.name}'")
    return new_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get a project by ID."""
    # DESIGN-001: Check access using permission helper
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.patch("/projects/{project_id}/rename")
async def rename_project(
    project_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Rename a project."""
    # DESIGN-001: Check access using permission helper
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # DESIGN-001: Check for globally unique name
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.name == name,
            LDMProject.id != project_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"A project named '{name}' already exists")

    old_name = project.name
    project.name = name
    await db.commit()

    logger.success(f"Project renamed: id={project_id}, '{old_name}' -> '{name}'")
    return {"success": True, "project_id": project_id, "name": name}


@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Delete a project and all its contents."""
    # DESIGN-001: Check access using permission helper
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    logger.info(f"Project deleted: id={project_id}")
    return {"message": "Project deleted"}


# =============================================================================
# DESIGN-001: Project Restriction Management (Admin Only)
# =============================================================================

@router.put("/projects/{project_id}/restriction")
async def set_project_restriction(
    project_id: int,
    is_restricted: bool,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Toggle restriction on a project. Admin only.
    When restricted, only assigned users can access.
    """
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_restricted = is_restricted
    await db.commit()

    status = "restricted" if is_restricted else "public"
    logger.success(f"Project {project_id} set to {status} by admin {admin['username']}")

    return {
        "success": True,
        "project_id": project_id,
        "is_restricted": is_restricted
    }


@router.get("/projects/{project_id}/access", response_model=List[AccessUserResponse])
async def list_project_access(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    List users with access to a restricted project. Admin only.
    """
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    access_list = await get_project_access_list(db, project_id)
    return [AccessUserResponse(**item) for item in access_list]


@router.post("/projects/{project_id}/access")
async def grant_project_access_endpoint(
    project_id: int,
    request: AccessGrantRequest,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Grant users access to a restricted project. Admin only.
    """
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    count = await grant_project_access(db, project_id, request.user_ids, admin["user_id"])

    return {
        "success": True,
        "project_id": project_id,
        "users_granted": count
    }


@router.delete("/projects/{project_id}/access/{user_id}")
async def revoke_project_access_endpoint(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Revoke user access from a restricted project. Admin only.
    """
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    revoked = await revoke_project_access(db, project_id, user_id)

    return {
        "success": revoked,
        "project_id": project_id,
        "user_id": user_id
    }
