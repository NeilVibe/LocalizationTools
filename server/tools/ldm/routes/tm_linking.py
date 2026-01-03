"""
TM Linking endpoints - Link TMs to projects for auto-add on confirm.

FEAT-001: Project-TM Linking API
Migrated from api.py lines 732-1086
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMProject, LDMTranslationMemory, LDMActiveTM
from server.tools.ldm.schemas import LinkTMRequest
from server.tools.ldm.permissions import can_access_project, can_access_tm

router = APIRouter(tags=["LDM"])


# =============================================================================
# Helper Functions
# =============================================================================

async def get_project_linked_tm(db: AsyncSession, project_id: int, user_id: int) -> Optional[int]:
    """
    FEAT-001: Get the highest-priority linked TM for a project.
    Returns tm_id or None if no TM linked.
    """
    result = await db.execute(
        select(LDMActiveTM.tm_id)
        .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
        .where(
            LDMActiveTM.project_id == project_id,
            LDMTranslationMemory.owner_id == user_id  # User must own the TM
        )
        .order_by(LDMActiveTM.priority)
        .limit(1)
    )
    return result.scalar_one_or_none()


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/projects/{project_id}/link-tm")
async def link_tm_to_project(
    project_id: int,
    request: LinkTMRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    FEAT-001: Link a TM to a project for auto-add on confirm.
    All confirmed cells (Ctrl+S) in this project will auto-add to this TM.
    """
    user_id = current_user["user_id"]

    # Verify project access (DESIGN-001: Public by default)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get project for response
    project_result = await db.execute(
        select(LDMProject).where(LDMProject.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, request.tm_id, current_user):
        raise HTTPException(status_code=404, detail="TM not found")

    # Get TM for response
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == request.tm_id)
    )
    tm = tm_result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Check if link already exists
    existing_result = await db.execute(
        select(LDMActiveTM).where(
            LDMActiveTM.project_id == project_id,
            LDMActiveTM.tm_id == request.tm_id
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        # TM already linked - return 400
        raise HTTPException(status_code=400, detail="TM already linked to this project")

    # Create new link
    link = LDMActiveTM(
        tm_id=request.tm_id,
        project_id=project_id,
        priority=request.priority,
        activated_by=user_id
    )
    db.add(link)
    await db.commit()

    logger.info(f"FEAT-001: Linked TM to project: project={project_id}, tm={request.tm_id}, priority={request.priority}")
    return {"status": "linked", "project_id": project_id, "tm_id": request.tm_id, "tm_name": tm.name, "priority": request.priority}


@router.delete("/projects/{project_id}/link-tm/{tm_id}")
async def unlink_tm_from_project(
    project_id: int,
    tm_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """FEAT-001: Remove TM link from project."""
    user_id = current_user["user_id"]

    # Verify project access (DESIGN-001: Public by default)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Find and delete link
    link_result = await db.execute(
        select(LDMActiveTM).where(
            LDMActiveTM.project_id == project_id,
            LDMActiveTM.tm_id == tm_id
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="TM link not found")

    await db.delete(link)
    await db.commit()

    logger.info(f"FEAT-001: Unlinked TM from project: project={project_id}, tm={tm_id}")
    return {"status": "unlinked", "message": "TM unlinked from project", "project_id": project_id, "tm_id": tm_id}


@router.get("/projects/{project_id}/linked-tms")
async def get_linked_tms(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """FEAT-001: Get all TMs linked to a project, ordered by priority."""
    user_id = current_user["user_id"]

    # Verify project access (DESIGN-001: Public by default)
    if not await can_access_project(db, project_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get all linked TMs with TM details
    result = await db.execute(
        select(LDMActiveTM, LDMTranslationMemory)
        .join(LDMTranslationMemory, LDMActiveTM.tm_id == LDMTranslationMemory.id)
        .where(LDMActiveTM.project_id == project_id)
        .order_by(LDMActiveTM.priority)
    )
    links = result.all()

    linked_tms = [
        {
            "tm_id": link.LDMActiveTM.tm_id,
            "tm_name": link.LDMTranslationMemory.name,
            "priority": link.LDMActiveTM.priority,
            "status": link.LDMTranslationMemory.status,
            "entry_count": link.LDMTranslationMemory.entry_count,
            "linked_at": link.LDMActiveTM.activated_at.isoformat() if link.LDMActiveTM.activated_at else None
        }
        for link in links
    ]

    return linked_tms
