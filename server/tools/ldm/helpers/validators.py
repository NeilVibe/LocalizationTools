"""
Validation helpers.

Common validation logic extracted from endpoints.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from server.database.models import LDMProject, LDMTranslationMemory


async def validate_project_access(
    db: AsyncSession,
    project_id: int,
    user_id: int
) -> LDMProject:
    """
    Validate user has access to project.

    Raises HTTPException 404 if not found or not owned by user.
    Returns the project if valid.
    """
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == user_id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


async def validate_tm_access(
    db: AsyncSession,
    tm_id: int,
    user_id: int
) -> LDMTranslationMemory:
    """
    Validate user has access to TM.

    Raises HTTPException 404 if not found or not owned by user.
    Returns the TM if valid.
    """
    result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.user_id == user_id
        )
    )
    tm = result.scalar_one_or_none()

    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    return tm
