"""
LDM Permission Helpers - Public by Default with Optional Restrictions.

DESIGN-001: Transform from "private by default" to "public by default".

Access Rules:
1. Admins/Superadmins: Full access to everything (bypass all restrictions)
2. Public resources (is_restricted=False): All authenticated users can access
3. Restricted resources (is_restricted=True): Only assigned users + owner can access
4. Inheritance: Project inherits platform restriction (if platform is restricted,
   user must have platform access to access any project under it)
5. TMs: Inherit restriction from their assigned project/platform (no own setting)
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from server.database.models import (
    LDMPlatform,
    LDMProject,
    LDMFolder,
    LDMFile,
    LDMTranslationMemory,
    LDMResourceAccess,
    LDMTMAssignment,
)
from loguru import logger


def is_admin(user: dict) -> bool:
    """Check if user has admin/superadmin role."""
    return user.get("role") in ["admin", "superadmin"]


# =============================================================================
# Platform Access
# =============================================================================

async def can_access_platform(
    db: AsyncSession,
    platform_id: int,
    user: dict
) -> bool:
    """
    Check if user can access a platform.

    Returns True if:
    - User is admin/superadmin
    - Platform is public (is_restricted=False)
    - User owns the platform
    - User has explicit access grant
    """
    if is_admin(user):
        return True

    user_id = user["user_id"]

    # Get platform info with single query
    result = await db.execute(
        select(LDMPlatform.is_restricted, LDMPlatform.owner_id)
        .where(LDMPlatform.id == platform_id)
    )
    row = result.first()

    if not row:
        return False  # Platform doesn't exist

    is_restricted, owner_id = row

    # Public platform - everyone can access
    if not is_restricted:
        return True

    # Owner always has access
    if owner_id == user_id:
        return True

    # Check explicit access grant
    result = await db.execute(
        select(LDMResourceAccess.id)
        .where(
            LDMResourceAccess.platform_id == platform_id,
            LDMResourceAccess.user_id == user_id
        )
    )
    return result.first() is not None


async def get_accessible_platforms(
    db: AsyncSession,
    user: dict,
    include_projects: bool = False
) -> List[LDMPlatform]:
    """
    Get all platforms the user can access.

    Args:
        db: Database session
        user: Current user dict
        include_projects: If True, eagerly load projects relationship
    """
    if is_admin(user):
        # Admins see everything
        query = select(LDMPlatform)
        if include_projects:
            query = query.options(selectinload(LDMPlatform.projects))
        result = await db.execute(query.order_by(LDMPlatform.name))
        return list(result.scalars().all())

    user_id = user["user_id"]

    # Get platforms that are:
    # 1. Public (is_restricted=False), OR
    # 2. Owned by user, OR
    # 3. User has explicit access
    query = (
        select(LDMPlatform)
        .outerjoin(
            LDMResourceAccess,
            (LDMResourceAccess.platform_id == LDMPlatform.id) &
            (LDMResourceAccess.user_id == user_id)
        )
        .where(
            or_(
                LDMPlatform.is_restricted == False,  # noqa: E712
                LDMPlatform.owner_id == user_id,
                LDMResourceAccess.id.isnot(None)
            )
        )
    )

    if include_projects:
        query = query.options(selectinload(LDMPlatform.projects))

    result = await db.execute(query.order_by(LDMPlatform.name))
    return list(result.scalars().unique().all())


# =============================================================================
# Project Access
# =============================================================================

async def can_access_project(
    db: AsyncSession,
    project_id: int,
    user: dict
) -> bool:
    """
    Check if user can access a project.

    Checks both project-level restriction AND platform inheritance.
    If project's platform is restricted, user must have platform access too.
    """
    if is_admin(user):
        return True

    user_id = user["user_id"]

    # Get project with platform info
    result = await db.execute(
        select(
            LDMProject.is_restricted,
            LDMProject.owner_id,
            LDMProject.platform_id
        )
        .where(LDMProject.id == project_id)
    )
    row = result.first()

    if not row:
        return False  # Project doesn't exist

    is_restricted, owner_id, platform_id = row

    # Owner always has access
    if owner_id == user_id:
        return True

    # Check project-level restriction
    if is_restricted:
        # Check explicit project access
        result = await db.execute(
            select(LDMResourceAccess.id)
            .where(
                LDMResourceAccess.project_id == project_id,
                LDMResourceAccess.user_id == user_id
            )
        )
        if result.first() is None:
            return False

    # Check platform-level restriction (inheritance)
    if platform_id:
        if not await can_access_platform(db, platform_id, user):
            return False

    # Project is accessible
    return True


async def get_accessible_projects(
    db: AsyncSession,
    user: dict,
    platform_id: Optional[int] = None
) -> List[LDMProject]:
    """
    Get all projects the user can access.

    Args:
        db: Database session
        user: Current user dict
        platform_id: Optional filter by platform
    """
    if is_admin(user):
        query = select(LDMProject)
        if platform_id:
            query = query.where(LDMProject.platform_id == platform_id)
        result = await db.execute(query.order_by(LDMProject.name))
        return list(result.scalars().all())

    user_id = user["user_id"]

    # For regular users, we need to check:
    # 1. Project is public AND platform is public (or no platform)
    # 2. User owns the project
    # 3. User has explicit project access
    # 4. User has platform access (for projects under restricted platforms)

    # First, get all accessible platform IDs
    accessible_platform_result = await db.execute(
        select(LDMPlatform.id)
        .outerjoin(
            LDMResourceAccess,
            (LDMResourceAccess.platform_id == LDMPlatform.id) &
            (LDMResourceAccess.user_id == user_id)
        )
        .where(
            or_(
                LDMPlatform.is_restricted == False,  # noqa: E712
                LDMPlatform.owner_id == user_id,
                LDMResourceAccess.id.isnot(None)
            )
        )
    )
    accessible_platform_ids = [row[0] for row in accessible_platform_result.all()]

    # Now get projects
    query = (
        select(LDMProject)
        .outerjoin(
            LDMResourceAccess,
            (LDMResourceAccess.project_id == LDMProject.id) &
            (LDMResourceAccess.user_id == user_id)
        )
        .where(
            or_(
                # Public project under accessible platform or no platform
                (LDMProject.is_restricted == False) &  # noqa: E712
                (
                    LDMProject.platform_id.is_(None) |
                    LDMProject.platform_id.in_(accessible_platform_ids)
                ),
                # Owned project
                LDMProject.owner_id == user_id,
                # Explicit project access
                LDMResourceAccess.id.isnot(None)
            )
        )
    )

    if platform_id:
        query = query.where(LDMProject.platform_id == platform_id)

    result = await db.execute(query.order_by(LDMProject.name))
    return list(result.scalars().unique().all())


# =============================================================================
# File/Folder Access (via Project)
# =============================================================================

async def can_access_file(
    db: AsyncSession,
    file_id: int,
    user: dict
) -> bool:
    """
    Check if user can access a file via its project.
    """
    if is_admin(user):
        return True

    # Get project_id from file
    result = await db.execute(
        select(LDMFile.project_id)
        .where(LDMFile.id == file_id)
    )
    row = result.first()

    if not row:
        return False

    return await can_access_project(db, row[0], user)


async def can_access_folder(
    db: AsyncSession,
    folder_id: int,
    user: dict
) -> bool:
    """
    Check if user can access a folder via its project.
    """
    if is_admin(user):
        return True

    # Get project_id from folder
    result = await db.execute(
        select(LDMFolder.project_id)
        .where(LDMFolder.id == folder_id)
    )
    row = result.first()

    if not row:
        return False

    return await can_access_project(db, row[0], user)


# =============================================================================
# TM Access (inherits from assigned project/platform)
# =============================================================================

async def can_access_tm(
    db: AsyncSession,
    tm_id: int,
    user: dict
) -> bool:
    """
    Check if user can access a TM.

    TMs inherit access from their assigned project/platform via LDMTMAssignment.
    If TM is not assigned anywhere, only owner and admins can access.
    """
    if is_admin(user):
        return True

    user_id = user["user_id"]

    # Get TM owner
    result = await db.execute(
        select(LDMTranslationMemory.owner_id)
        .where(LDMTranslationMemory.id == tm_id)
    )
    row = result.first()

    if not row:
        return False  # TM doesn't exist

    owner_id = row[0]

    # Owner always has access
    if owner_id == user_id:
        return True

    # Check TM assignment - find what it's assigned to
    result = await db.execute(
        select(LDMTMAssignment.platform_id, LDMTMAssignment.project_id, LDMTMAssignment.folder_id)
        .where(LDMTMAssignment.tm_id == tm_id, LDMTMAssignment.is_active == True)  # noqa: E712
    )
    assignment = result.first()

    if not assignment:
        # TM not assigned anywhere - only owner/admin can access
        return False

    platform_id, project_id, folder_id = assignment

    # Check access based on assignment scope
    if folder_id:
        return await can_access_folder(db, folder_id, user)
    elif project_id:
        return await can_access_project(db, project_id, user)
    elif platform_id:
        return await can_access_platform(db, platform_id, user)

    return False


async def get_accessible_tms(
    db: AsyncSession,
    user: dict
) -> List[LDMTranslationMemory]:
    """
    Get all TMs the user can access.

    For admins: all TMs
    For users: owned TMs + TMs assigned to accessible platforms/projects
    """
    if is_admin(user):
        result = await db.execute(
            select(LDMTranslationMemory).order_by(LDMTranslationMemory.name)
        )
        return list(result.scalars().all())

    user_id = user["user_id"]

    # Get accessible platforms and projects first
    accessible_platforms = await get_accessible_platforms(db, user)
    accessible_projects = await get_accessible_projects(db, user)

    platform_ids = [p.id for p in accessible_platforms]
    project_ids = [p.id for p in accessible_projects]

    # Get folder IDs from accessible projects
    folder_result = await db.execute(
        select(LDMFolder.id).where(LDMFolder.project_id.in_(project_ids))
    )
    folder_ids = [row[0] for row in folder_result.all()]

    # Get TMs that are:
    # 1. Owned by user, OR
    # 2. Assigned to accessible platform/project/folder
    query = (
        select(LDMTranslationMemory)
        .outerjoin(LDMTMAssignment, LDMTMAssignment.tm_id == LDMTranslationMemory.id)
        .where(
            or_(
                LDMTranslationMemory.owner_id == user_id,
                (LDMTMAssignment.is_active == True) &  # noqa: E712
                (
                    LDMTMAssignment.platform_id.in_(platform_ids) |
                    LDMTMAssignment.project_id.in_(project_ids) |
                    LDMTMAssignment.folder_id.in_(folder_ids)
                )
            )
        )
    )

    result = await db.execute(query.order_by(LDMTranslationMemory.name))
    return list(result.scalars().unique().all())


# =============================================================================
# Access Grant Management (Admin Only)
# =============================================================================

async def grant_platform_access(
    db: AsyncSession,
    platform_id: int,
    user_ids: List[int],
    granted_by: int
) -> int:
    """
    Grant access to a restricted platform for multiple users.
    Returns count of new grants created.
    """
    created = 0
    for user_id in user_ids:
        # Check if grant already exists
        result = await db.execute(
            select(LDMResourceAccess.id)
            .where(
                LDMResourceAccess.platform_id == platform_id,
                LDMResourceAccess.user_id == user_id
            )
        )
        if result.first() is None:
            grant = LDMResourceAccess(
                platform_id=platform_id,
                user_id=user_id,
                granted_by=granted_by
            )
            db.add(grant)
            created += 1

    if created > 0:
        await db.commit()
        logger.info(f"Granted platform {platform_id} access to {created} users")

    return created


async def revoke_platform_access(
    db: AsyncSession,
    platform_id: int,
    user_id: int
) -> bool:
    """
    Revoke access to a restricted platform for a user.
    Returns True if grant was removed, False if it didn't exist.
    """
    result = await db.execute(
        select(LDMResourceAccess)
        .where(
            LDMResourceAccess.platform_id == platform_id,
            LDMResourceAccess.user_id == user_id
        )
    )
    grant = result.scalar_one_or_none()

    if grant:
        await db.delete(grant)
        await db.commit()
        logger.info(f"Revoked platform {platform_id} access from user {user_id}")
        return True

    return False


async def grant_project_access(
    db: AsyncSession,
    project_id: int,
    user_ids: List[int],
    granted_by: int
) -> int:
    """
    Grant access to a restricted project for multiple users.
    Returns count of new grants created.
    """
    created = 0
    for user_id in user_ids:
        # Check if grant already exists
        result = await db.execute(
            select(LDMResourceAccess.id)
            .where(
                LDMResourceAccess.project_id == project_id,
                LDMResourceAccess.user_id == user_id
            )
        )
        if result.first() is None:
            grant = LDMResourceAccess(
                project_id=project_id,
                user_id=user_id,
                granted_by=granted_by
            )
            db.add(grant)
            created += 1

    if created > 0:
        await db.commit()
        logger.info(f"Granted project {project_id} access to {created} users")

    return created


async def revoke_project_access(
    db: AsyncSession,
    project_id: int,
    user_id: int
) -> bool:
    """
    Revoke access to a restricted project for a user.
    Returns True if grant was removed, False if it didn't exist.
    """
    result = await db.execute(
        select(LDMResourceAccess)
        .where(
            LDMResourceAccess.project_id == project_id,
            LDMResourceAccess.user_id == user_id
        )
    )
    grant = result.scalar_one_or_none()

    if grant:
        await db.delete(grant)
        await db.commit()
        logger.info(f"Revoked project {project_id} access from user {user_id}")
        return True

    return False


async def get_platform_access_list(
    db: AsyncSession,
    platform_id: int
) -> List[dict]:
    """
    Get list of users with access to a restricted platform.
    """
    from server.database.models import User

    result = await db.execute(
        select(LDMResourceAccess, User)
        .join(User, User.user_id == LDMResourceAccess.user_id)
        .where(LDMResourceAccess.platform_id == platform_id)
    )

    access_list = []
    for grant, user in result.all():
        access_list.append({
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "access_level": grant.access_level,
            "granted_at": grant.granted_at.isoformat() if grant.granted_at else None
        })

    return access_list


async def get_project_access_list(
    db: AsyncSession,
    project_id: int
) -> List[dict]:
    """
    Get list of users with access to a restricted project.
    """
    from server.database.models import User

    result = await db.execute(
        select(LDMResourceAccess, User)
        .join(User, User.user_id == LDMResourceAccess.user_id)
        .where(LDMResourceAccess.project_id == project_id)
    )

    access_list = []
    for grant, user in result.all():
        access_list.append({
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "access_level": grant.access_level,
            "granted_at": grant.granted_at.isoformat() if grant.granted_at else None
        })

    return access_list
