"""
SQLite Platform Repository.

Implements PlatformRepository interface using SQLite (offline mode).
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.platform_repository import PlatformRepository
from server.database.offline import get_offline_db


class SQLitePlatformRepository(PlatformRepository):
    """
    SQLite implementation of PlatformRepository.

    Uses OfflineDatabase for all operations.
    This is the offline mode adapter.
    """

    def __init__(self):
        self.db = get_offline_db()

    def _normalize_platform(self, platform: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize platform dict to match PostgreSQL format."""
        if not platform:
            return None

        return {
            "id": platform.get("id"),
            "name": platform.get("name"),
            "description": platform.get("description"),
            "owner_id": platform.get("owner_id"),
            "is_restricted": bool(platform.get("is_restricted")),
            "project_count": platform.get("project_count", 0),
            "created_at": platform.get("created_at"),
            "updated_at": platform.get("updated_at"),
            # SQLite-specific fields
            "sync_status": platform.get("sync_status"),
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """Get platform by ID."""
        with self.db._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM offline_platforms WHERE id = ?",
                (platform_id,)
            ).fetchone()
            return self._normalize_platform(dict(row)) if row else None

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all platforms."""
        with self.db._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_platforms ORDER BY name"
            ).fetchall()
            return [self._normalize_platform(dict(row)) for row in rows]

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

        # Use negative IDs for local platforms
        platform_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()

        with self.db._get_connection() as conn:
            conn.execute(
                """INSERT INTO offline_platforms
                   (id, server_id, name, description, owner_id, is_restricted,
                    created_at, updated_at, downloaded_at, sync_status)
                   VALUES (?, 0, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                (
                    platform_id,
                    name,
                    description,
                    owner_id,
                    1 if is_restricted else 0,
                    now,
                    now,
                )
            )
            conn.commit()

        logger.info(f"Created local platform: id={platform_id}, name='{name}'")
        return await self.get(platform_id)

    async def update(
        self,
        platform_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update platform fields."""
        platform = await self.get(platform_id)
        if not platform:
            return None

        # Check for unique name if renaming
        if name is not None and name != platform.get("name"):
            if await self.check_name_exists(name, exclude_id=platform_id):
                raise ValueError(f"Platform '{name}' already exists")

        with self.db._get_connection() as conn:
            updates = ["updated_at = datetime('now')"]
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)

            params.append(platform_id)

            conn.execute(
                f"UPDATE offline_platforms SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()

        logger.info(f"Updated platform: id={platform_id}")
        return await self.get(platform_id)

    async def delete(self, platform_id: int) -> bool:
        """Delete a platform."""
        platform = await self.get(platform_id)
        if not platform:
            return False

        with self.db._get_connection() as conn:
            # Unassign projects (set platform_id to NULL)
            conn.execute(
                "UPDATE offline_projects SET platform_id = NULL WHERE platform_id = ?",
                (platform_id,)
            )

            # Delete the platform
            conn.execute("DELETE FROM offline_platforms WHERE id = ?", (platform_id,))
            conn.commit()

        logger.info(f"Deleted platform: id={platform_id}")
        return True

    # =========================================================================
    # Platform-Specific Operations
    # =========================================================================

    async def get_with_project_count(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """Get platform with project count."""
        platform = await self.get(platform_id)
        if not platform:
            return None

        with self.db._get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) as cnt FROM offline_projects WHERE platform_id = ?",
                (platform_id,)
            ).fetchone()
            project_count = result["cnt"] if result else 0

        platform["project_count"] = project_count
        return platform

    async def set_restriction(self, platform_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """Set platform restriction flag."""
        platform = await self.get(platform_id)
        if not platform:
            return None

        with self.db._get_connection() as conn:
            conn.execute(
                "UPDATE offline_platforms SET is_restricted = ?, updated_at = datetime('now') WHERE id = ?",
                (1 if is_restricted else 0, platform_id)
            )
            conn.commit()

        status = "restricted" if is_restricted else "public"
        logger.info(f"Platform {platform_id} set to {status}")
        return await self.get(platform_id)

    async def assign_project(
        self,
        project_id: int,
        platform_id: Optional[int]
    ) -> bool:
        """Assign a project to a platform."""
        with self.db._get_connection() as conn:
            # Check project exists
            project = conn.execute(
                "SELECT id FROM offline_projects WHERE id = ?",
                (project_id,)
            ).fetchone()

            if not project:
                return False

            # Verify platform exists if assigning
            if platform_id is not None:
                platform = conn.execute(
                    "SELECT id FROM offline_platforms WHERE id = ?",
                    (platform_id,)
                ).fetchone()
                if not platform:
                    return False

            conn.execute(
                "UPDATE offline_projects SET platform_id = ?, updated_at = datetime('now') WHERE id = ?",
                (platform_id, project_id)
            )
            conn.commit()

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
        with self.db._get_connection() as conn:
            query = "SELECT COUNT(*) as cnt FROM offline_platforms WHERE LOWER(name) = LOWER(?)"
            params = [name]

            if exclude_id is not None:
                query += " AND id != ?"
                params.append(exclude_id)

            result = conn.execute(query, params).fetchone()
            return result["cnt"] > 0

    async def count(self) -> int:
        """Count all platforms."""
        with self.db._get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) as cnt FROM offline_platforms"
            ).fetchone()
            return result["cnt"] if result else 0

    async def get_projects(self, platform_id: int) -> List[Dict[str, Any]]:
        """Get all projects in a platform."""
        with self.db._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description FROM offline_projects WHERE platform_id = ? ORDER BY name",
                (platform_id,)
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                }
                for row in rows
            ]

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search platforms by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.
        """
        search_term = f"%{query}%"
        with self.db._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_platforms WHERE name LIKE ? COLLATE NOCASE",
                (search_term,)
            ).fetchall()

            return [self._normalize_platform(dict(row)) for row in rows]
