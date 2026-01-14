"""
PostgreSQL Project Repository Implementation.

P10: FULL ABSTRACT + REPO Pattern

Implements ProjectRepository interface using SQLAlchemy async.
Permissions are baked INTO the repository.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from server.database.models import LDMProject, LDMFile, LDMFolder, LDMResourceAccess
from server.repositories.interfaces.project_repository import ProjectRepository


class PostgreSQLProjectRepository(ProjectRepository):
    """
    PostgreSQL implementation of ProjectRepository.

    P10: FULL ABSTRACT - Permissions are checked INSIDE the repository.
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    # =========================================================================
    # Permission Helpers (P10: Baked into repository)
    # =========================================================================

    def _is_admin(self) -> bool:
        """Check if current user is admin/superadmin."""
        return self.user.get("role") in ["admin", "superadmin"]

    async def _can_access_project(self, project_id: int) -> bool:
        """Check if current user can access project."""
        if not self.user:
            return False

        if self._is_admin():
            return True

        user_id = self.user.get("user_id")
        if not user_id:
            return False

        result = await self.db.execute(
            select(LDMProject.is_restricted, LDMProject.owner_id)
            .where(LDMProject.id == project_id)
        )
        row = result.first()
        if not row:
            return False

        is_restricted, owner_id = row

        if owner_id == user_id:
            return True

        if not is_restricted:
            return True

        result = await self.db.execute(
            select(LDMResourceAccess.id)
            .where(
                LDMResourceAccess.project_id == project_id,
                LDMResourceAccess.user_id == user_id
            )
        )
        return result.first() is not None

    def _project_to_dict(self, project: LDMProject) -> Dict[str, Any]:
        """Convert SQLAlchemy project to dict."""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
            "platform_id": project.platform_id,
            "is_restricted": project.is_restricted,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project by ID with permission check.

        P10: FULL ABSTRACT - Permission check baked in. Returns None if user lacks access.
        """
        # P10: Check permission first
        if not await self._can_access_project(project_id):
            logger.debug(f"[PROJECT_REPO] Access denied: user {self.user.get('user_id')} cannot access project {project_id}")
            return None

        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        return self._project_to_dict(project) if project else None

    async def get_all(
        self,
        platform_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all projects, optionally filtered by platform."""
        query = select(LDMProject)

        if platform_id is not None:
            query = query.where(LDMProject.platform_id == platform_id)

        query = query.order_by(LDMProject.name)
        result = await self.db.execute(query)
        projects = result.scalars().all()

        return [self._project_to_dict(p) for p in projects]

    async def create(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        platform_id: Optional[int] = None,
        is_restricted: bool = False
    ) -> Dict[str, Any]:
        """Create a new project."""
        # DB-002: Generate unique name
        unique_name = await self.generate_unique_name(name, platform_id)

        project = LDMProject(
            name=unique_name,
            description=description,
            owner_id=owner_id,
            platform_id=platform_id,
            is_restricted=is_restricted
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.commit()

        logger.info(f"Created project: id={project.id}, name='{unique_name}'")
        return self._project_to_dict(project)

    async def update(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_restricted: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update project fields."""
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if is_restricted is not None:
            project.is_restricted = is_restricted

        project.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(project)

        logger.info(f"Updated project: id={project_id}")
        return self._project_to_dict(project)

    async def delete(self, project_id: int) -> bool:
        """Delete a project."""
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return False

        await self.db.delete(project)
        await self.db.commit()

        logger.info(f"Deleted project: id={project_id}")
        return True

    # =========================================================================
    # Project-Specific Operations
    # =========================================================================

    async def rename(self, project_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Rename a project."""
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        # Check if name exists
        if await self.check_name_exists(new_name, project.platform_id, exclude_id=project_id):
            raise ValueError(f"A project named '{new_name}' already exists in this platform")

        old_name = project.name
        project.name = new_name
        project.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(project)

        logger.info(f"Renamed project: id={project_id}, '{old_name}' -> '{new_name}'")
        return self._project_to_dict(project)

    async def set_restriction(self, project_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """Set project restriction flag."""
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        project.is_restricted = is_restricted
        project.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(project)

        status = "restricted" if is_restricted else "public"
        logger.info(f"Project {project_id} set to {status}")
        return self._project_to_dict(project)

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def check_name_exists(
        self,
        name: str,
        platform_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Check if project name exists in platform."""
        query = select(func.count(LDMProject.id)).where(
            func.lower(LDMProject.name) == func.lower(name)
        )

        if platform_id is not None:
            query = query.where(LDMProject.platform_id == platform_id)
        else:
            query = query.where(LDMProject.platform_id.is_(None))

        if exclude_id is not None:
            query = query.where(LDMProject.id != exclude_id)

        result = await self.db.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def generate_unique_name(
        self,
        base_name: str,
        platform_id: Optional[int] = None
    ) -> str:
        """Generate a unique project name."""
        if not await self.check_name_exists(base_name, platform_id):
            return base_name

        counter = 1
        while True:
            new_name = f"{base_name}_{counter}"
            if not await self.check_name_exists(new_name, platform_id):
                logger.info(f"Auto-renamed duplicate project: '{base_name}' -> '{new_name}'")
                return new_name
            counter += 1

    async def get_with_stats(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project with file/folder counts."""
        project = await self.get(project_id)
        if not project:
            return None

        # Get file count
        file_result = await self.db.execute(
            select(func.count(LDMFile.id)).where(LDMFile.project_id == project_id)
        )
        file_count = file_result.scalar() or 0

        # Get folder count
        folder_result = await self.db.execute(
            select(func.count(LDMFolder.id)).where(LDMFolder.project_id == project_id)
        )
        folder_count = folder_result.scalar() or 0

        project["file_count"] = file_count
        project["folder_count"] = folder_count

        return project

    async def count(self, platform_id: Optional[int] = None) -> int:
        """Count projects, optionally filtered by platform."""
        query = select(func.count(LDMProject.id))

        if platform_id is not None:
            query = query.where(LDMProject.platform_id == platform_id)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search projects by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query.lower()}%"
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.name.ilike(search_term))
        )
        projects = result.scalars().all()

        return [self._project_to_dict(p) for p in projects]

    async def get_accessible(self) -> List[Dict[str, Any]]:
        """
        Get all projects accessible by the current user.

        P10: FULL ABSTRACT - Returns projects the user can access:
        - Admins: All projects
        - Regular users: Public projects + owned projects + projects with explicit access
        """
        from sqlalchemy import or_

        # Admins see all projects
        if self._is_admin():
            return await self.get_all()

        user_id = self.user.get("user_id")
        if not user_id:
            # No user = only public projects
            result = await self.db.execute(
                select(LDMProject)
                .where(LDMProject.is_restricted == False)
                .order_by(LDMProject.name)
            )
            projects = result.scalars().all()
            return [self._project_to_dict(p) for p in projects]

        # Get project IDs user has explicit access to
        access_result = await self.db.execute(
            select(LDMResourceAccess.project_id)
            .where(LDMResourceAccess.user_id == user_id)
        )
        accessible_ids = [row[0] for row in access_result.all()]

        # Build query: public OR owned OR explicit access
        query = select(LDMProject).where(
            or_(
                LDMProject.is_restricted == False,  # Public projects
                LDMProject.owner_id == user_id,     # Owned projects
                LDMProject.id.in_(accessible_ids) if accessible_ids else False  # Explicit access
            )
        ).order_by(LDMProject.name)

        result = await self.db.execute(query)
        projects = result.scalars().all()

        return [self._project_to_dict(p) for p in projects]
