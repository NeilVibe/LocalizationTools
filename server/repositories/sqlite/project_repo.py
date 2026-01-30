"""
SQLite Project Repository.

Implements ProjectRepository interface using SQLite (offline mode).
Delegates to existing OfflineDatabase methods.

ASYNC MIGRATION (2026-01-31): Uses aiosqlite for true async operations.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.project_repository import ProjectRepository
from server.database.offline import get_offline_db


class SQLiteProjectRepository(ProjectRepository):
    """
    SQLite implementation of ProjectRepository.

    Uses OfflineDatabase for all operations.
    This is the offline mode adapter.
    """

    def __init__(self):
        self.db = get_offline_db()

    def _normalize_project(self, project: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize project dict to match PostgreSQL format."""
        if not project:
            return None

        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "owner_id": project.get("owner_id"),
            "platform_id": project.get("platform_id"),
            "is_restricted": bool(project.get("is_restricted")),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at"),
            # SQLite-specific fields
            "sync_status": project.get("sync_status"),
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_projects WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()
            return self._normalize_project(dict(row)) if row else None

    async def get_all(
        self,
        platform_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all projects, optionally filtered by platform."""
        projects = await self.db.get_projects(platform_id)
        return [self._normalize_project(p) for p in projects]

    async def create(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        platform_id: Optional[int] = None,
        is_restricted: bool = False
    ) -> Dict[str, Any]:
        """Create a new project."""
        # Generate unique name
        unique_name = await self.generate_unique_name(name, platform_id)

        # Use negative IDs for local projects
        project_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                """INSERT INTO offline_projects
                   (id, server_id, name, description, platform_id, server_platform_id,
                    owner_id, is_restricted, created_at, updated_at, downloaded_at, sync_status)
                   VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                (
                    project_id,
                    unique_name,
                    description,
                    platform_id,
                    platform_id,
                    owner_id,
                    1 if is_restricted else 0,
                    now,
                    now,
                )
            )
            await conn.commit()

        logger.info(f"Created local project: id={project_id}, name='{unique_name}'")

        return await self.get(project_id)

    async def update(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_restricted: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update project fields."""
        project = await self.get(project_id)
        if not project:
            return None

        async with self.db._get_async_connection() as conn:
            updates = ["updated_at = datetime('now')"]
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if is_restricted is not None:
                updates.append("is_restricted = ?")
                params.append(1 if is_restricted else 0)

            params.append(project_id)

            await conn.execute(
                f"UPDATE offline_projects SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await conn.commit()

        logger.info(f"Updated project: id={project_id}")
        return await self.get(project_id)

    async def delete(self, project_id: int) -> bool:
        """Delete a project."""
        project = await self.get(project_id)
        if not project:
            return False

        async with self.db._get_async_connection() as conn:
            # Delete all files in project
            await conn.execute("DELETE FROM offline_rows WHERE file_id IN (SELECT id FROM offline_files WHERE project_id = ?)", (project_id,))
            await conn.execute("DELETE FROM offline_files WHERE project_id = ?", (project_id,))

            # Delete all folders in project
            await conn.execute("DELETE FROM offline_folders WHERE project_id = ?", (project_id,))

            # Delete the project
            await conn.execute("DELETE FROM offline_projects WHERE id = ?", (project_id,))
            await conn.commit()

        logger.info(f"Deleted project: id={project_id}")
        return True

    # =========================================================================
    # Project-Specific Operations
    # =========================================================================

    async def rename(self, project_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Rename a project."""
        project = await self.get(project_id)
        if not project:
            return None

        # Check if name exists
        if await self.check_name_exists(new_name, project.get("platform_id"), exclude_id=project_id):
            raise ValueError(f"A project named '{new_name}' already exists in this platform")

        old_name = project.get("name")

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                "UPDATE offline_projects SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, project_id)
            )
            await conn.commit()

        logger.info(f"Renamed project: id={project_id}, '{old_name}' -> '{new_name}'")
        return await self.get(project_id)

    async def set_restriction(self, project_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """Set project restriction flag."""
        project = await self.get(project_id)
        if not project:
            return None

        async with self.db._get_async_connection() as conn:
            await conn.execute(
                "UPDATE offline_projects SET is_restricted = ?, updated_at = datetime('now') WHERE id = ?",
                (1 if is_restricted else 0, project_id)
            )
            await conn.commit()

        status = "restricted" if is_restricted else "public"
        logger.info(f"Project {project_id} set to {status}")
        return await self.get(project_id)

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
        async with self.db._get_async_connection() as conn:
            if platform_id is None:
                query = """
                    SELECT COUNT(*) as cnt FROM offline_projects
                    WHERE LOWER(name) = LOWER(?) AND platform_id IS NULL
                """
                params = [name]
            else:
                query = """
                    SELECT COUNT(*) as cnt FROM offline_projects
                    WHERE LOWER(name) = LOWER(?) AND platform_id = ?
                """
                params = [name, platform_id]

            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)

            cursor = await conn.execute(query, params)
            result = await cursor.fetchone()
            return result["cnt"] > 0

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

        async with self.db._get_async_connection() as conn:
            # Get file count
            cursor = await conn.execute(
                "SELECT COUNT(*) as cnt FROM offline_files WHERE project_id = ?",
                (project_id,)
            )
            file_result = await cursor.fetchone()
            file_count = file_result["cnt"] if file_result else 0

            # Get folder count
            cursor = await conn.execute(
                "SELECT COUNT(*) as cnt FROM offline_folders WHERE project_id = ?",
                (project_id,)
            )
            folder_result = await cursor.fetchone()
            folder_count = folder_result["cnt"] if folder_result else 0

        project["file_count"] = file_count
        project["folder_count"] = folder_count

        return project

    async def count(self, platform_id: Optional[int] = None) -> int:
        """Count projects, optionally filtered by platform."""
        async with self.db._get_async_connection() as conn:
            if platform_id is None:
                cursor = await conn.execute(
                    "SELECT COUNT(*) as cnt FROM offline_projects"
                )
            else:
                cursor = await conn.execute(
                    "SELECT COUNT(*) as cnt FROM offline_projects WHERE platform_id = ?",
                    (platform_id,)
                )

            result = await cursor.fetchone()
            return result["cnt"] if result else 0

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search projects by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query}%"
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_projects WHERE name LIKE ? COLLATE NOCASE",
                (search_term,)
            )
            rows = await cursor.fetchall()

            return [self._normalize_project(dict(row)) for row in rows]

    async def get_accessible(self) -> List[Dict[str, Any]]:
        """
        Get all projects accessible by the current user.

        P10: FULL ABSTRACT - In offline mode, all projects are accessible (single user).
        """
        # Offline mode = single user = all projects are accessible
        return await self.get_all()
