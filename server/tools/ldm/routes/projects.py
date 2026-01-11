"""Project CRUD endpoints.

Repository Pattern: Uses ProjectRepository for database abstraction.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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
from server.repositories import ProjectRepository, get_project_repository

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
    P9: Includes "Offline Storage" as virtual project (id=0) if local files exist.
    """
    user_id = current_user["user_id"]
    logger.info(f"[PROJECTS] Listing projects for user {user_id}")

    # Use permission helper to get accessible projects
    projects = await get_accessible_projects(db, current_user)

    # P9: Offline Storage is shown in File Explorer tree, not as a project
    # Local files are accessed via the "Offline Storage" node in the explorer

    return projects


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """Create a new project.

    Repository Pattern: Uses ProjectRepository for database abstraction.
    """
    user_id = current_user["user_id"]
    logger.info(f"[PROJECTS] Creating project '{project.name}' for user {user_id}")

    # Use repository to create project (handles auto-rename for duplicates)
    new_project = await repo.create(
        name=project.name,
        owner_id=user_id,
        description=project.description,
        platform_id=project.platform_id if hasattr(project, 'platform_id') else None,
        is_restricted=False  # DESIGN-001: Public by default
    )

    logger.success(f"[PROJECTS] Project created: id={new_project['id']}, name='{new_project['name']}'")
    return new_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """Get a project by ID.

    Repository Pattern: Uses ProjectRepository for database abstraction.
    """
    # DESIGN-001: Check access using permission helper
    # Returns False for both non-existent AND no access (security: don't reveal existence)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    # Use repository to get project
    project = await repo.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.patch("/projects/{project_id}/rename")
async def rename_project(
    project_id: int,
    name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """Rename a project.

    Repository Pattern: Uses ProjectRepository for database abstraction.
    """
    # DESIGN-001: Check access using permission helper
    # Returns False for both non-existent AND no access (security: don't reveal existence)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Use repository to rename (handles uniqueness check)
        project = await repo.rename(project_id, name)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        logger.success(f"[PROJECTS] Project renamed: id={project_id}, new name='{name}'")
        return {"success": True, "project_id": project_id, "name": name}
    except ValueError as e:
        # Raised when name already exists
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """
    Delete a project and all its contents.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.
    EXPLORER-009: Requires 'delete_project' capability.

    Repository Pattern: Uses ProjectRepository for database abstraction.
    """
    # DESIGN-001: Check access using permission helper
    # Returns False for both non-existent AND no access (security: don't reveal existence)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    # EXPLORER-009: Check capability for privileged operation
    from ..permissions import require_capability
    await require_capability(db, current_user, "delete_project")

    # Get project for trash serialization (needs full SQLAlchemy object for trash)
    result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        from .trash import move_to_trash, serialize_project_for_trash

        # Serialize project data for restore
        project_data = await serialize_project_for_trash(db, project)

        # Move to trash
        await move_to_trash(
            db,
            item_type="project",
            item_id=project.id,
            item_name=project.name,
            item_data=project_data,
            parent_project_id=None,
            parent_folder_id=None,
            deleted_by=current_user["user_id"]
        )

    # Use repository to delete
    await repo.delete(project_id)

    action = "permanently deleted" if permanent else "moved to trash"
    logger.info(f"[PROJECTS] Project {action}: id={project_id}, name='{project_name}'")
    return {"message": f"Project {action}"}


# =============================================================================
# DESIGN-001: Project Restriction Management (Admin Only)
# =============================================================================

@router.put("/projects/{project_id}/restriction")
async def set_project_restriction(
    project_id: int,
    is_restricted: bool,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """
    Toggle restriction on a project. Admin only.
    When restricted, only assigned users can access.

    Repository Pattern: Uses ProjectRepository for database abstraction.
    """
    # Use repository to set restriction
    project = await repo.set_restriction(project_id, is_restricted)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    status = "restricted" if is_restricted else "public"
    logger.success(f"[PROJECTS] Project {project_id} set to {status} by admin {admin['username']}")

    return {
        "success": True,
        "project_id": project_id,
        "is_restricted": is_restricted
    }


@router.get("/projects/{project_id}/access", response_model=List[AccessUserResponse])
async def list_project_access(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """
    List users with access to a restricted project. Admin only.

    Repository Pattern: Uses ProjectRepository for existence check.
    """
    # Use repository to verify project exists
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    access_list = await get_project_access_list(db, project_id)
    return [AccessUserResponse(**item) for item in access_list]


@router.post("/projects/{project_id}/access")
async def grant_project_access_endpoint(
    project_id: int,
    request: AccessGrantRequest,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """
    Grant users access to a restricted project. Admin only.

    Repository Pattern: Uses ProjectRepository for existence check.
    """
    # Use repository to verify project exists
    project = await repo.get(project_id)
    if not project:
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
    admin: dict = Depends(require_admin_async),
    repo: ProjectRepository = Depends(get_project_repository)
):
    """
    Revoke user access from a restricted project. Admin only.

    Repository Pattern: Uses ProjectRepository for existence check.
    """
    # Use repository to verify project exists
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    revoked = await revoke_project_access(db, project_id, user_id)

    return {
        "success": revoked,
        "project_id": project_id,
        "user_id": user_id
    }
