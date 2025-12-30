"""Project CRUD endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMProject
from server.tools.ldm.schemas import ProjectCreate, ProjectResponse, DeleteResponse

router = APIRouter(tags=["LDM"])


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """List all projects for current user."""
    user_id = current_user["user_id"]
    logger.info(f"Listing projects for user {user_id}")

    result = await db.execute(
        select(LDMProject).where(LDMProject.owner_id == current_user["user_id"])
    )
    projects = result.scalars().all()

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

    # UI-077 FIX: Check for duplicate project name for this user
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.owner_id == user_id,
            LDMProject.name == project.name
        )
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
        owner_id=current_user["user_id"]
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
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
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
    user_id = current_user["user_id"]

    # Get project
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == user_id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check for duplicate name
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.owner_id == user_id,
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
    result = await db.execute(
        select(LDMProject).where(
            LDMProject.id == project_id,
            LDMProject.owner_id == current_user["user_id"]
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    logger.info(f"Project deleted: id={project_id}")
    return {"message": "Project deleted"}
