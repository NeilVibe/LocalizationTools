"""
TM Linking endpoints - Link TMs to projects for auto-add on confirm.

P10: FULL ABSTRACT + REPO Pattern
- All endpoints use Repository Pattern with permissions baked in
- No direct DB access in routes

FEAT-001: Project-TM Linking API
Migrated from api.py lines 732-1086
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas import LinkTMRequest
from server.repositories.interfaces.project_repository import ProjectRepository
from server.repositories.interfaces.tm_repository import TMRepository
from server.repositories.factory import get_project_repository, get_tm_repository

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================

async def get_project_linked_tm(tm_repo: TMRepository, project_id: int, user_id: int) -> Optional[int]:
    """
    FEAT-001: Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.

    P10-REPO: Now uses TMRepository instead of direct DB.
    """
    tm = await tm_repo.get_linked_for_project(project_id, user_id)
    return tm["id"] if tm else None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/projects/{project_id}/link-tm")
async def link_tm_to_project(
    project_id: int,
    request: LinkTMRequest,
    project_repo: ProjectRepository = Depends(get_project_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    FEAT-001: Link a TM to a project for auto-add on confirm.
    All confirmed cells (Ctrl+S) in this project will auto-add to this TM.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    # P10: Get project via repository (permissions checked inside - returns None if no access)
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # P10: Get TM via repository (permissions checked inside - returns None if no access)
    tm = await tm_repo.get(request.tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # P10: Link TM to project using Repository
    result = await tm_repo.link_to_project(request.tm_id, project_id, request.priority)

    # Check if link already existed
    if not result.get("created", True):
        raise HTTPException(status_code=400, detail="TM already linked to this project")

    logger.info(f"[TM-LINK] FEAT-001: Linked TM to project: project={project_id}, tm={request.tm_id}, priority={request.priority}")
    return {"status": "linked", "project_id": project_id, "tm_id": request.tm_id, "tm_name": tm["name"], "priority": request.priority}


@router.delete("/projects/{project_id}/link-tm/{tm_id}")
async def unlink_tm_from_project(
    project_id: int,
    tm_id: int,
    project_repo: ProjectRepository = Depends(get_project_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    FEAT-001: Remove TM link from project.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    # P10: Get project via repository (permissions checked inside - returns None if no access)
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # P10: Unlink TM from project using Repository
    unlinked = await tm_repo.unlink_from_project(tm_id, project_id)
    if not unlinked:
        raise HTTPException(status_code=404, detail="TM link not found")

    logger.info(f"[TM-LINK] FEAT-001: Unlinked TM from project: project={project_id}, tm={tm_id}")
    return {"status": "unlinked", "message": "TM unlinked from project", "project_id": project_id, "tm_id": tm_id}


@router.get("/projects/{project_id}/linked-tms")
async def get_linked_tms(
    project_id: int,
    project_repo: ProjectRepository = Depends(get_project_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    FEAT-001: Get all TMs linked to a project, ordered by priority.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    # P10: Get project via repository (permissions checked inside - returns None if no access)
    project = await project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # P10: Get all linked TMs using Repository
    linked_tms = await tm_repo.get_all_linked_for_project(project_id)

    return linked_tms
