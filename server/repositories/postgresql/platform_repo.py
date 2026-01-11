"""
PostgreSQL Platform Repository Implementation.

Implements PlatformRepository interface using SQLAlchemy async.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from loguru import logger

from server.database.models import LDMPlatform, LDMProject
from server.repositories.interfaces.platform_repository import PlatformRepository


class PostgreSQLPlatformRepository(PlatformRepository):
    """PostgreSQL implementation of PlatformRepository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _platform_to_dict(self, platform: LDMPlatform, project_count: int = 0) -> Dict[str, Any]:
        """Convert SQLAlchemy platform to dict."""
        return {
            "id": platform.id,
            "name": platform.name,
            "description": platform.description,
            "owner_id": platform.owner_id,
            "is_restricted": platform.is_restricted,
            "project_count": project_count,
            "created_at": platform.created_at.isoformat() if platform.created_at else None,
            "updated_at": platform.updated_at.isoformat() if platform.updated_at else None,
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """Get platform by ID."""
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.id == platform_id)
        )
        platform = result.scalar_one_or_none()
        return self._platform_to_dict(platform) if platform else None

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all platforms."""
        result = await self.db.execute(
            select(LDMPlatform).order_by(LDMPlatform.name)
        )
        platforms = result.scalars().all()
        return [self._platform_to_dict(p) for p in platforms]

    async def create(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        is_restricted: bool = False
    ) -> Dict[str, Any]:
        """Create a new platform."""
        # Check for globally unique name
        if await self.check_name_exists(name):
            raise ValueError(f"Platform '{name}' already exists")

        platform = LDMPlatform(
            name=name,
            description=description,
            owner_id=owner_id,
            is_restricted=is_restricted
        )
        self.db.add(platform)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(platform)

        logger.info(f"Created platform: id={platform.id}, name='{name}'")
        return self._platform_to_dict(platform)

    async def update(
        self,
        platform_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update platform fields."""
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.id == platform_id)
        )
        platform = result.scalar_one_or_none()

        if not platform:
            return None

        # Check for unique name if renaming
        if name is not None and name != platform.name:
            if await self.check_name_exists(name, exclude_id=platform_id):
                raise ValueError(f"Platform '{name}' already exists")
            platform.name = name

        if description is not None:
            platform.description = description

        platform.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(platform)

        logger.info(f"Updated platform: id={platform_id}")
        return self._platform_to_dict(platform)

    async def delete(self, platform_id: int) -> bool:
        """Delete a platform."""
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.id == platform_id)
        )
        platform = result.scalar_one_or_none()

        if not platform:
            return False

        await self.db.delete(platform)
        await self.db.commit()

        logger.info(f"Deleted platform: id={platform_id}")
        return True

    # =========================================================================
    # Platform-Specific Operations
    # =========================================================================

    async def get_with_project_count(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """Get platform with project count."""
        result = await self.db.execute(
            select(LDMPlatform)
            .options(selectinload(LDMPlatform.projects))
            .where(LDMPlatform.id == platform_id)
        )
        platform = result.scalar_one_or_none()

        if not platform:
            return None

        project_count = len(platform.projects) if platform.projects else 0
        return self._platform_to_dict(platform, project_count)

    async def set_restriction(self, platform_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """Set platform restriction flag."""
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.id == platform_id)
        )
        platform = result.scalar_one_or_none()

        if not platform:
            return None

        platform.is_restricted = is_restricted
        platform.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(platform)

        status = "restricted" if is_restricted else "public"
        logger.info(f"Platform {platform_id} set to {status}")
        return self._platform_to_dict(platform)

    async def assign_project(
        self,
        project_id: int,
        platform_id: Optional[int]
    ) -> bool:
        """Assign a project to a platform."""
        result = await self.db.execute(
            select(LDMProject).where(LDMProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return False

        # Verify platform exists if assigning
        if platform_id is not None:
            result = await self.db.execute(
                select(LDMPlatform).where(LDMPlatform.id == platform_id)
            )
            if not result.scalar_one_or_none():
                return False

        project.platform_id = platform_id
        project.updated_at = datetime.utcnow()

        await self.db.commit()

        action = f"assigned to platform {platform_id}" if platform_id else "unassigned"
        logger.info(f"Project {project_id} {action}")
        return True

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def check_name_exists(
        self,
        name: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Check if platform name exists globally."""
        query = select(func.count(LDMPlatform.id)).where(
            func.lower(LDMPlatform.name) == func.lower(name)
        )

        if exclude_id is not None:
            query = query.where(LDMPlatform.id != exclude_id)

        result = await self.db.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def count(self) -> int:
        """Count all platforms."""
        result = await self.db.execute(
            select(func.count(LDMPlatform.id))
        )
        return result.scalar() or 0

    async def get_projects(self, platform_id: int) -> List[Dict[str, Any]]:
        """Get all projects in a platform."""
        result = await self.db.execute(
            select(LDMProject)
            .where(LDMProject.platform_id == platform_id)
            .order_by(LDMProject.name)
        )
        projects = result.scalars().all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
            }
            for p in projects
        ]

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search platforms by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query.lower()}%"
        result = await self.db.execute(
            select(LDMPlatform).where(LDMPlatform.name.ilike(search_term))
        )
        platforms = result.scalars().all()

        return [self._platform_to_dict(p) for p in platforms]
