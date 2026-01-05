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
from server.tools.ldm.permissions import can_access_platform, can_access_project, can_access_tm, can_access_file

router = APIRouter(tags=["LDM"])

# =============================================================================
# P9-ARCH: Offline Storage Platform Support in PostgreSQL
# =============================================================================

OFFLINE_STORAGE_PLATFORM_NAME = "Offline Storage"
OFFLINE_STORAGE_PROJECT_NAME = "Offline Storage"


async def ensure_offline_storage_platform(db: AsyncSession):
    """
    Ensure the Offline Storage platform exists in PostgreSQL.
    This allows TMs to be assigned to Offline Storage files.
    Returns the platform record.
    """
    # Check if it already exists
    result = await db.execute(
        select(LDMPlatform).where(LDMPlatform.name == OFFLINE_STORAGE_PLATFORM_NAME)
    )
    platform = result.scalar_one_or_none()

    if not platform:
        # Create the Offline Storage platform
        platform = LDMPlatform(
            name=OFFLINE_STORAGE_PLATFORM_NAME,
            description="Local files stored offline for translation",
            owner_id=1,  # System owner
            is_restricted=False
        )
        db.add(platform)
        await db.flush()  # Get the ID
        logger.info(f"P9-ARCH: Created Offline Storage platform in PostgreSQL (id={platform.id})")

    return platform


async def ensure_offline_storage_project(db: AsyncSession):
    """
    Ensure the Offline Storage project exists in PostgreSQL.
    Returns the project record.
    """
    platform = await ensure_offline_storage_platform(db)

    # Check if project exists
    result = await db.execute(
        select(LDMProject).where(
            and_(
                LDMProject.platform_id == platform.id,
                LDMProject.name == OFFLINE_STORAGE_PROJECT_NAME
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        project = LDMProject(
            name=OFFLINE_STORAGE_PROJECT_NAME,
            description="Local files stored offline",
            platform_id=platform.id,
            owner_id=1,
            is_restricted=False
        )
        db.add(project)
        await db.flush()
        logger.info(f"P9-ARCH: Created Offline Storage project in PostgreSQL (id={project.id})")

    return project


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
    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get TM
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
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
    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

    # Get TM
    result = await db.execute(
        select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
    )
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Validate: only one scope can be set
    scope_count = sum([1 for x in [platform_id, project_id, folder_id] if x is not None])
    if scope_count > 1:
        raise HTTPException(status_code=400, detail="Only one scope can be set (platform, project, or folder)")

    # Validate scope exists and user has access (DESIGN-001: Public by default)
    scope_name = "unassigned"
    if folder_id:
        from server.tools.ldm.permissions import can_access_folder
        if not await can_access_folder(db, folder_id, current_user):
            raise HTTPException(status_code=404, detail="Folder not found")
        result = await db.execute(
            select(LDMFolder).where(LDMFolder.id == folder_id)
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        scope_name = f"folder:{folder.name}"
    elif project_id:
        if not await can_access_project(db, project_id, current_user):
            raise HTTPException(status_code=404, detail="Project not found")
        scope_name = f"project:{project_id}"
    elif platform_id:
        if not await can_access_platform(db, platform_id, current_user):
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
    # Verify TM access (DESIGN-001: Public by default)
    if not await can_access_tm(db, tm_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

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

    # P9: Local files have no TM assignments (return empty)
    if not file:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            return []  # Local files don't have TMs
        raise HTTPException(status_code=404, detail="File not found")

    # Verify file access (DESIGN-001: Public by default)
    if not await can_access_file(db, file_id, current_user):
        raise HTTPException(status_code=404, detail="Resource not found")

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
    from server.tools.ldm.permissions import get_accessible_platforms, get_accessible_tms

    # DESIGN-001: Get accessible TMs for this user (not just owned)
    accessible_tms = await get_accessible_tms(db, current_user)
    accessible_tm_ids = {tm.id for tm in accessible_tms}

    # Get all TM assignments for accessible TMs
    result = await db.execute(
        select(LDMTMAssignment)
        .options(
            selectinload(LDMTMAssignment.tm),
            selectinload(LDMTMAssignment.platform),
            selectinload(LDMTMAssignment.project),
            selectinload(LDMTMAssignment.folder)
        )
        .join(LDMTranslationMemory)
        .where(LDMTranslationMemory.id.in_(accessible_tm_ids))
    )
    assignments = result.scalars().all()

    # Get TMs without assignments (truly unassigned)
    assigned_tm_ids = {a.tm_id for a in assignments}
    unassigned_tms = [tm for tm in accessible_tms if tm.id not in assigned_tm_ids]

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

    # DESIGN-001: Get accessible platforms (not just owned)
    platforms = await get_accessible_platforms(db, current_user, include_projects=True)

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

    # P9-ARCH: Ensure Offline Storage platform is always in the tree
    # This allows users to assign TMs to offline files
    offline_platform = await ensure_offline_storage_platform(db)
    await db.commit()  # Commit if created

    # Check if Offline Storage is already in the tree
    offline_in_tree = any(p["name"] == OFFLINE_STORAGE_PLATFORM_NAME for p in tree["platforms"])

    if not offline_in_tree:
        # Add Offline Storage platform with its project
        offline_project = await ensure_offline_storage_project(db)
        await db.commit()

        offline_platform_data = {
            "id": offline_platform.id,
            "name": offline_platform.name,
            "tms": [
                {
                    "tm_id": a.tm_id,
                    "tm_name": a.tm.name,
                    "is_active": a.is_active
                }
                for a in assignments if a.platform_id == offline_platform.id
            ],
            "projects": [
                {
                    "id": offline_project.id,
                    "name": offline_project.name,
                    "tms": [
                        {
                            "tm_id": a.tm_id,
                            "tm_name": a.tm.name,
                            "is_active": a.is_active
                        }
                        for a in assignments if a.project_id == offline_project.id
                    ],
                    "folders": []
                }
            ]
        }
        # Insert at beginning so it's prominent
        tree["platforms"].insert(0, offline_platform_data)

    return tree
