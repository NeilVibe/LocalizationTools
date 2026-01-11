"""
TM Assignment endpoints for TM Hierarchy System.

P9-ARCH: Uses Repository Pattern for database abstraction.
- Online mode: PostgreSQLTMRepository (PostgreSQL)
- Offline mode: SQLiteTMRepository (local SQLite)

Routes use ONLY the repository interface. No direct DB access.
The repository is automatically selected based on user's mode (token-based detection).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_current_active_user_async

# Repository Pattern - ONLY import interface and factory
from server.repositories import TMRepository, AssignmentTarget, get_tm_repository

router = APIRouter(tags=["LDM"])


# =============================================================================
# Schemas
# =============================================================================

class TMAssignmentResponse(BaseModel):
    id: int
    tm_id: int
    tm_name: str
    platform_id: Optional[int] = None
    platform_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    folder_id: Optional[int] = None
    folder_name: Optional[str] = None
    is_active: bool
    priority: int
    scope: str  # "unassigned", "platform", "project", "folder"

    class Config:
        from_attributes = True


class ActiveTMResponse(BaseModel):
    """TM info for file viewer - shows active TMs in scope chain."""
    tm_id: int
    tm_name: str
    scope: str  # "platform", "project", "folder"
    scope_name: str  # Name of the platform/project/folder
    priority: int


# =============================================================================
# Assignment Management
# =============================================================================

@router.get("/tm/{tm_id}/assignment", response_model=Optional[TMAssignmentResponse])
async def get_tm_assignment(
    tm_id: int,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get the current assignment for a TM.

    P9-ARCH: Uses Repository Pattern - automatically selects PostgreSQL or SQLite
    based on user's online/offline mode.
    """
    # Get TM from repository (handles both PostgreSQL and SQLite)
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Get assignment from repository
    assignment = await repo.get_assignment(tm_id)

    if not assignment:
        # No assignment = Unassigned
        return TMAssignmentResponse(
            id=0,
            tm_id=tm_id,
            tm_name=tm.get("name", ""),
            is_active=False,
            priority=0,
            scope="unassigned"
        )

    # Determine scope
    if assignment.get("folder_id"):
        scope = "folder"
    elif assignment.get("project_id"):
        scope = "project"
    elif assignment.get("platform_id"):
        scope = "platform"
    else:
        scope = "unassigned"

    return TMAssignmentResponse(
        id=assignment.get("id", 0),
        tm_id=tm_id,
        tm_name=tm.get("name", ""),
        platform_id=assignment.get("platform_id"),
        platform_name=assignment.get("platform_name"),
        project_id=assignment.get("project_id"),
        project_name=assignment.get("project_name"),
        folder_id=assignment.get("folder_id"),
        folder_name=assignment.get("folder_name"),
        is_active=assignment.get("is_active", False),
        priority=assignment.get("priority", 0),
        scope=scope
    )


@router.patch("/tm/{tm_id}/assign")
async def assign_tm(
    tm_id: int,
    platform_id: Optional[int] = None,
    project_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Assign a TM to a platform, project, or folder.
    Only ONE scope can be set - others must be None.
    If all are None, TM is moved to "Unassigned".

    P9-ARCH: Uses Repository Pattern.
    - Online mode: PostgreSQL
    - Offline mode: SQLite
    Routes don't know which database - repository handles it.
    """
    # Get TM from repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Build assignment target
    target = AssignmentTarget(
        platform_id=platform_id,
        project_id=project_id,
        folder_id=folder_id
    )

    # Validate: only one scope can be set
    if target.scope_count() > 1:
        raise HTTPException(status_code=400, detail="Only one scope can be set (platform, project, or folder)")

    # Use repository for assignment - it handles validation internally
    try:
        result = await repo.assign(tm_id, target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Determine scope name for logging
    scope_name = "unassigned"
    if folder_id:
        scope_name = f"folder:{folder_id}"
    elif project_id:
        scope_name = f"project:{project_id}"
    elif platform_id:
        scope_name = f"platform:{platform_id}"

    logger.success(f"[TM-ASSIGN] TM {tm_id} assigned to {scope_name}")

    return {
        "success": True,
        "tm_id": tm_id,
        "platform_id": platform_id,
        "project_id": project_id,
        "folder_id": folder_id
    }


@router.patch("/tm/{tm_id}/activate")
async def activate_tm(
    tm_id: int,
    active: bool = True,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Activate or deactivate a TM at its assigned scope.

    P9-ARCH: Uses Repository Pattern - works with both PostgreSQL and SQLite.
    """
    # Get TM from repository
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Activate or deactivate using repository
    try:
        if active:
            result = await repo.activate(tm_id)
        else:
            result = await repo.deactivate(tm_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    status = "activated" if active else "deactivated"
    logger.success(f"[TM-ASSIGN] TM {tm_id} {status}")

    return {"success": True, "tm_id": tm_id, "is_active": active}


# =============================================================================
# TM Resolution for Files
# =============================================================================

@router.get("/files/{file_id}/active-tms", response_model=List[ActiveTMResponse])
async def get_active_tms_for_file(
    file_id: int,
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get all active TMs that apply to a file (resolved cascade).

    Returns TMs in priority order:
    1. Folder-level TMs (walking up folder tree)
    2. Project-level TMs
    3. Platform-level TMs

    P9-ARCH: Uses Repository Pattern - handles file resolution in both
    PostgreSQL (online) and SQLite (offline) modes.
    """
    # Get active TMs from repository (handles scope chain resolution)
    active_tms = await repo.get_active_for_file(file_id)

    # Convert to response model
    return [
        ActiveTMResponse(
            tm_id=tm.get("tm_id") or tm.get("id"),
            tm_name=tm.get("tm_name") or tm.get("name", "Unknown"),
            scope=tm.get("scope", "unknown"),
            scope_name=tm.get("scope_name", "Unknown"),
            priority=tm.get("priority", 0)
        )
        for tm in active_tms
    ]


# =============================================================================
# TM Explorer Tree (mirrors File Explorer)
# =============================================================================

@router.get("/tm-tree")
async def get_tm_tree(
    repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get TM tree structure that mirrors File Explorer.

    Returns:
    - Unassigned TMs
    - Platforms with their projects and folders (only those with TMs assigned)
    - Each node shows assigned TMs and their activation status

    P9-ARCH: Uses Repository Pattern - automatically builds correct tree
    for online (PostgreSQL) or offline (SQLite) mode.
    """
    # Repository handles all tree building logic for the appropriate database
    return await repo.get_tree()
