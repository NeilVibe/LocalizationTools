"""Project CRUD endpoints.

Repository Pattern: Uses ProjectRepository for database abstraction.

P10-REPO: Migrated to Repository Pattern (2026-01-13)
- All endpoints use Repository Pattern
- Trash serialization uses repository-based helpers
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.tools.ldm.schemas import ProjectCreate, ProjectResponse, DeleteResponse
from server.tools.ldm.permissions import (
    get_accessible_projects,
    can_access_project,
    grant_project_access,
    revoke_project_access,
    get_project_access_list,
)
from server.repositories import (
    ProjectRepository, get_project_repository,
    FolderRepository, get_folder_repository,
    FileRepository, get_file_repository,
    TrashRepository, get_trash_repository
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
    # P11-FIX: platform_id now properly passed from ProjectCreate schema
    new_project = await repo.create(
        name=project.name,
        owner_id=user_id,
        description=project.description,
        platform_id=project.platform_id,  # Now correctly received from schema
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
    # Get project details
    project = await project_repo.get(project_id)
    if not project:
        return {}

    # Get all folders in project
    all_folders = await folder_repo.get_all(project_id)

    # Filter for root folders (parent_id is None)
    root_folders = [f for f in all_folders if f.get("parent_id") is None]

    # Serialize root folders
    folders_data = []
    for folder in root_folders:
        folder_data = await _serialize_folder_for_trash_repo(
            folder_repo, file_repo,
            folder["id"], folder["name"]
        )
        folders_data.append(folder_data)

    # Get all files in project
    all_files = await file_repo.get_all(project_id=project_id, limit=10000)

    # Filter for root files (folder_id is None)
    root_files = [f for f in all_files if f.get("folder_id") is None]

    # Serialize root files
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


# =============================================================================
# Delete Endpoint
# =============================================================================

@router.delete("/projects/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: int,
    permanent: bool = Query(False, description="If true, permanently delete instead of moving to trash"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    trash_repo: TrashRepository = Depends(get_trash_repository)
):
    """
    Delete a project and all its contents.
    EXPLORER-008: By default, moves to trash (soft delete). Use permanent=true for hard delete.
    EXPLORER-009: Requires 'delete_project' capability.

    P10-REPO: Uses Repository Pattern for all operations including trash serialization.
    """
    # DESIGN-001: Check access using permission helper
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Project not found")

    # EXPLORER-009: Check capability for privileged operation
    from ..permissions import require_capability
    await require_capability(db, current_user, "delete_project")

    # Get project using repository
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project["name"]

    if not permanent:
        # EXPLORER-008: Soft delete - move to trash
        from .trash import move_to_trash

        # Serialize project data using repository-based helper (P10-REPO)
        project_data = await _serialize_project_for_trash_repo(
            repo, folder_repo, file_repo, project_id
        )

        # Move to trash (P10-REPO: uses TrashRepository)
        await move_to_trash(
            trash_repo,
            item_type="project",
            item_id=project["id"],
            item_name=project["name"],
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
