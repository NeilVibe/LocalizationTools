"""
Project Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ProjectRepository(ABC):
    """
    Project repository interface.

    Both PostgreSQLProjectRepository and SQLiteProjectRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project by ID.

        Returns:
            Project dict with: id, name, description, owner_id, platform_id,
            is_restricted, created_at, updated_at.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_all(
        self,
        platform_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all projects, optionally filtered by platform.

        Args:
            platform_id: Optional filter by platform

        Returns:
            List of project dicts.
        """
        ...

    @abstractmethod
    async def create(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        platform_id: Optional[int] = None,
        is_restricted: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new project.

        Args:
            name: Project name (will be auto-renamed if duplicate)
            owner_id: Owner user ID
            description: Optional description
            platform_id: Optional platform ID
            is_restricted: Whether project is restricted (default False = public)

        Returns:
            Created project dict with id.
        """
        ...

    @abstractmethod
    async def update(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_restricted: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update project fields.

        Args:
            project_id: Project to update
            name: New name (None = don't change)
            description: New description (None = don't change)
            is_restricted: New restriction flag (None = don't change)

        Returns:
            Updated project dict, or None if not found.
        """
        ...

    @abstractmethod
    async def delete(self, project_id: int) -> bool:
        """
        Delete a project.

        Note: This is the database-level delete. Soft delete (trash)
        is handled at the route level.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Project-Specific Operations
    # =========================================================================

    @abstractmethod
    async def rename(self, project_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """
        Rename a project.

        Args:
            project_id: Project to rename
            new_name: New name

        Returns:
            Updated project dict, or None if not found.

        Raises:
            ValueError if name already exists in same platform.
        """
        ...

    @abstractmethod
    async def set_restriction(self, project_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """
        Set project restriction flag.

        Args:
            project_id: Project to update
            is_restricted: True = restricted (only assigned users), False = public

        Returns:
            Updated project dict, or None if not found.
        """
        ...

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def check_name_exists(
        self,
        name: str,
        platform_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if project name exists in platform.

        Args:
            name: Name to check
            platform_id: Platform to check within (None = root level)
            exclude_id: Project ID to exclude (for rename operations)

        Returns:
            True if name exists, False otherwise.
        """
        ...

    @abstractmethod
    async def generate_unique_name(
        self,
        base_name: str,
        platform_id: Optional[int] = None
    ) -> str:
        """
        Generate a unique project name.

        If base_name exists, appends _1, _2, etc.

        Args:
            base_name: Starting name
            platform_id: Platform to check within

        Returns:
            Unique name (may be same as base_name if not taken).
        """
        ...

    @abstractmethod
    async def get_with_stats(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project with file/folder counts.

        Returns:
            Project dict with additional: file_count, folder_count.
            None if not found.
        """
        ...

    @abstractmethod
    async def count(self, platform_id: Optional[int] = None) -> int:
        """
        Count projects, optionally filtered by platform.

        Returns:
            Project count.
        """
        ...

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search projects by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.

        Args:
            query: Search term (will match names containing this string)

        Returns:
            List of matching project dicts with platform_id for path building.
        """
        ...

    @abstractmethod
    async def get_accessible(self) -> List[Dict[str, Any]]:
        """
        Get all projects accessible by the current user.

        P10: FULL ABSTRACT - Returns projects the user can access:
        - Admins: All projects
        - Regular users: Public projects + owned projects + projects with explicit access

        Returns:
            List of accessible project dicts.
        """
        ...
