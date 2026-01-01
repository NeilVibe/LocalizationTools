"""TM Assignment endpoints for TM Hierarchy System."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import (
    LDMTranslationMemory, LDMTMAssignment, LDMPlatform,
    LDMProject, LDMFolder, LDMFile
)

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Get the current assignment for a TM."""
    # Verify TM ownership
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Get assignment
    result = await db.execute(
        select(LDMTMAssignment)
        .options(
            selectinload(LDMTMAssignment.platform),
            selectinload(LDMTMAssignment.project),
            selectinload(LDMTMAssignment.folder)
        )
        .where(LDMTMAssignment.tm_id == tm_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        # No assignment = Unassigned
        return TMAssignmentResponse(
            id=0,
            tm_id=tm_id,
            tm_name=tm.name,
            is_active=False,
            priority=0,
            scope="unassigned"
        )

    # Determine scope
    if assignment.folder_id:
        scope = "folder"
        scope_name = assignment.folder.name if assignment.folder else None
    elif assignment.project_id:
        scope = "project"
        scope_name = assignment.project.name if assignment.project else None
    elif assignment.platform_id:
        scope = "platform"
        scope_name = assignment.platform.name if assignment.platform else None
    else:
        scope = "unassigned"
        scope_name = None

    return TMAssignmentResponse(
        id=assignment.id,
        tm_id=tm_id,
        tm_name=tm.name,
        platform_id=assignment.platform_id,
        platform_name=assignment.platform.name if assignment.platform else None,
        project_id=assignment.project_id,
        project_name=assignment.project.name if assignment.project else None,
        folder_id=assignment.folder_id,
        folder_name=assignment.folder.name if assignment.folder else None,
        is_active=assignment.is_active,
        priority=assignment.priority,
        scope=scope
    )


@router.patch("/tm/{tm_id}/assign")
async def assign_tm(
    tm_id: int,
    platform_id: Optional[int] = None,
    project_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Assign a TM to a platform, project, or folder.
    Only ONE scope can be set - others must be None.
    If all are None, TM is moved to "Unassigned".
    """
    # Verify TM ownership
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Validate: only one scope can be set
    scope_count = sum([1 for x in [platform_id, project_id, folder_id] if x is not None])
    if scope_count > 1:
        raise HTTPException(status_code=400, detail="Only one scope can be set (platform, project, or folder)")

    # Validate scope exists and belongs to user
    scope_name = "unassigned"
    if folder_id:
        result = await db.execute(
            select(LDMFolder).options(selectinload(LDMFolder.project)).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()
        if not folder or folder.project.owner_id != current_user["user_id"]:
            raise HTTPException(status_code=404, detail="Folder not found")
        scope_name = f"folder:{folder.name}"
    elif project_id:
        result = await db.execute(
            select(LDMProject).where(
                LDMProject.id == project_id,
                LDMProject.owner_id == current_user["user_id"]
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")
        scope_name = f"project:{project_id}"
    elif platform_id:
        result = await db.execute(
            select(LDMPlatform).where(
                LDMPlatform.id == platform_id,
                LDMPlatform.owner_id == current_user["user_id"]
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Platform not found")
        scope_name = f"platform:{platform_id}"

    # Get or create assignment
    result = await db.execute(
        select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
    )
    assignment = result.scalar_one_or_none()

    if assignment:
        # Update existing
        assignment.platform_id = platform_id
        assignment.project_id = project_id
        assignment.folder_id = folder_id
        assignment.assigned_at = datetime.utcnow()
        assignment.assigned_by = current_user["user_id"]
    else:
        # Create new
        assignment = LDMTMAssignment(
            tm_id=tm_id,
            platform_id=platform_id,
            project_id=project_id,
            folder_id=folder_id,
            is_active=False,
            priority=0,
            assigned_by=current_user["user_id"]
        )
        db.add(assignment)

    await db.commit()

    logger.success(f"TM {tm_id} assigned to {scope_name}")

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """Activate or deactivate a TM at its assigned scope."""
    # Verify TM ownership
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="TM not found")

    # Get assignment
    result = await db.execute(
        select(LDMTMAssignment).where(LDMTMAssignment.tm_id == tm_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=400, detail="TM must be assigned to a scope before activation")

    # Validate assignment has actual scope (not just record with all NULLs)
    if not any([assignment.platform_id, assignment.project_id, assignment.folder_id]):
        raise HTTPException(status_code=400, detail="TM must be assigned to a platform, project, or folder before activation")

    assignment.is_active = active
    assignment.activated_at = datetime.utcnow() if active else None
    await db.commit()

    status = "activated" if active else "deactivated"
    logger.success(f"TM {tm_id} {status}")

    return {"success": True, "tm_id": tm_id, "is_active": active}


# =============================================================================
# TM Resolution for Files
# =============================================================================

@router.get("/files/{file_id}/active-tms", response_model=List[ActiveTMResponse])
async def get_active_tms_for_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get all active TMs that apply to a file (resolved cascade).

    Returns TMs in priority order:
    1. Folder-level TMs (walking up folder tree)
    2. Project-level TMs
    3. Platform-level TMs

    This is what the file viewer uses to show "Active TM" indicator.
    """
    # Get file with relationships
    result = await db.execute(
        select(LDMFile)
        .options(
            selectinload(LDMFile.folder),
            selectinload(LDMFile.project).selectinload(LDMProject.platform)
        )
        .where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.project.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    active_tms = []

    # 1. Walk up folder tree
    folder = file.folder
    folder_ids = []
    while folder:
        folder_ids.append(folder.id)
        # Get parent folder
        if folder.parent_id:
            result = await db.execute(
                select(LDMFolder).where(LDMFolder.id == folder.parent_id)
            )
            folder = result.scalar_one_or_none()
        else:
            folder = None

    # Get folder-level active TMs
    if folder_ids:
        result = await db.execute(
            select(LDMTMAssignment)
            .options(selectinload(LDMTMAssignment.tm), selectinload(LDMTMAssignment.folder))
            .where(
                LDMTMAssignment.folder_id.in_(folder_ids),
                LDMTMAssignment.is_active == True
            )
            .order_by(LDMTMAssignment.priority)
        )
        for assignment in result.scalars().all():
            active_tms.append(ActiveTMResponse(
                tm_id=assignment.tm_id,
                tm_name=assignment.tm.name,
                scope="folder",
                scope_name=assignment.folder.name if assignment.folder else "Unknown",
                priority=assignment.priority
            ))

    # 2. Project-level TMs
    result = await db.execute(
        select(LDMTMAssignment)
        .options(selectinload(LDMTMAssignment.tm), selectinload(LDMTMAssignment.project))
        .where(
            LDMTMAssignment.project_id == file.project_id,
            LDMTMAssignment.is_active == True
        )
        .order_by(LDMTMAssignment.priority)
    )
    for assignment in result.scalars().all():
        active_tms.append(ActiveTMResponse(
            tm_id=assignment.tm_id,
            tm_name=assignment.tm.name,
            scope="project",
            scope_name=assignment.project.name if assignment.project else "Unknown",
            priority=assignment.priority
        ))

    # 3. Platform-level TMs
    if file.project.platform_id:
        result = await db.execute(
            select(LDMTMAssignment)
            .options(selectinload(LDMTMAssignment.tm), selectinload(LDMTMAssignment.platform))
            .where(
                LDMTMAssignment.platform_id == file.project.platform_id,
                LDMTMAssignment.is_active == True
            )
            .order_by(LDMTMAssignment.priority)
        )
        for assignment in result.scalars().all():
            active_tms.append(ActiveTMResponse(
                tm_id=assignment.tm_id,
                tm_name=assignment.tm.name,
                scope="platform",
                scope_name=assignment.platform.name if assignment.platform else "Unknown",
                priority=assignment.priority
            ))

    return active_tms


# =============================================================================
# TM Explorer Tree (mirrors File Explorer)
# =============================================================================

@router.get("/tm-tree")
async def get_tm_tree(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get TM tree structure that mirrors File Explorer.

    Returns:
    - Unassigned TMs
    - Platforms with their projects and folders (only those with TMs assigned)
    - Each node shows assigned TMs and their activation status
    """
    user_id = current_user["user_id"]

    # Get all TM assignments for this user's TMs
    result = await db.execute(
        select(LDMTMAssignment)
        .options(
            selectinload(LDMTMAssignment.tm),
            selectinload(LDMTMAssignment.platform),
            selectinload(LDMTMAssignment.project),
            selectinload(LDMTMAssignment.folder)
        )
        .join(LDMTranslationMemory)
        .where(LDMTranslationMemory.owner_id == user_id)
    )
    assignments = result.scalars().all()

    # Get TMs without assignments (truly unassigned)
    result = await db.execute(
        select(LDMTranslationMemory)
        .outerjoin(LDMTMAssignment)
        .where(
            LDMTranslationMemory.owner_id == user_id,
            LDMTMAssignment.id == None
        )
    )
    unassigned_tms = result.scalars().all()

    # Also get TMs with assignment but all scope fields NULL
    unassigned_from_assignments = [
        a for a in assignments
        if a.platform_id is None and a.project_id is None and a.folder_id is None
    ]

    # Build tree structure
    tree = {
        "unassigned": [
            {
                "tm_id": tm.id,
                "tm_name": tm.name,
                "is_active": False
            }
            for tm in unassigned_tms
        ] + [
            {
                "tm_id": a.tm_id,
                "tm_name": a.tm.name,
                "is_active": a.is_active
            }
            for a in unassigned_from_assignments
        ],
        "platforms": []
    }

    # Get all platforms
    result = await db.execute(
        select(LDMPlatform)
        .options(selectinload(LDMPlatform.projects).selectinload(LDMProject.folders))
        .where(LDMPlatform.owner_id == user_id)
        .order_by(LDMPlatform.name)
    )
    platforms = result.scalars().all()

    for platform in platforms:
        platform_data = {
            "id": platform.id,
            "name": platform.name,
            "tms": [
                {
                    "tm_id": a.tm_id,
                    "tm_name": a.tm.name,
                    "is_active": a.is_active
                }
                for a in assignments if a.platform_id == platform.id
            ],
            "projects": []
        }

        for project in platform.projects:
            project_data = {
                "id": project.id,
                "name": project.name,
                "tms": [
                    {
                        "tm_id": a.tm_id,
                        "tm_name": a.tm.name,
                        "is_active": a.is_active
                    }
                    for a in assignments if a.project_id == project.id
                ],
                "folders": []
            }

            # Build folder tree (recursive helper)
            def build_folder_tree(folders, parent_id=None):
                result = []
                for folder in folders:
                    if folder.parent_id == parent_id:
                        folder_data = {
                            "id": folder.id,
                            "name": folder.name,
                            "tms": [
                                {
                                    "tm_id": a.tm_id,
                                    "tm_name": a.tm.name,
                                    "is_active": a.is_active
                                }
                                for a in assignments if a.folder_id == folder.id
                            ],
                            "children": build_folder_tree(folders, folder.id)
                        }
                        result.append(folder_data)
                return result

            project_data["folders"] = build_folder_tree(project.folders)
            platform_data["projects"].append(project_data)

        tree["platforms"].append(platform_data)

    return tree
