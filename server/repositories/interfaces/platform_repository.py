"""
Platform Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class PlatformRepository(ABC):
    """
    Platform repository interface.

    Both PostgreSQLPlatformRepository and SQLitePlatformRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """
        Get platform by ID.

        Returns:
            Platform dict with: id, name, description, owner_id, is_restricted,
            created_at, updated_at.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all platforms.

        Returns:
            List of platform dicts.
        """
        ...

    @abstractmethod
    async def create(
        self,
        name: str,
        owner_id: int,
        description: Optional[str] = None,
        is_restricted: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new platform.

        Args:
            name: Platform name (must be globally unique)
            owner_id: Owner user ID
            description: Optional description
            is_restricted: Whether platform is restricted (default False = public)

        Returns:
            Created platform dict with id.

        Raises:
            ValueError if name already exists.
        """
        ...

    @abstractmethod
    async def update(
        self,
        platform_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update platform fields.

        Args:
            platform_id: Platform to update
            name: New name (None = don't change)
            description: New description (None = don't change)

        Returns:
            Updated platform dict, or None if not found.

        Raises:
            ValueError if new name already exists.
        """
        ...

    @abstractmethod
    async def delete(self, platform_id: int) -> bool:
        """
        Delete a platform.

        Note: This is the database-level delete. Soft delete (trash)
        is handled at the route level. Projects will have platform_id
        set to NULL.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Platform-Specific Operations
    # =========================================================================

    @abstractmethod
    async def get_with_project_count(self, platform_id: int) -> Optional[Dict[str, Any]]:
        """
        Get platform with project count.

        Returns:
            Platform dict with additional: project_count.
            None if not found.
        """
        ...

    @abstractmethod
    async def set_restriction(self, platform_id: int, is_restricted: bool) -> Optional[Dict[str, Any]]:
        """
        Set platform restriction flag.

        Args:
            platform_id: Platform to update
            is_restricted: True = restricted (only assigned users), False = public

        Returns:
            Updated platform dict, or None if not found.
        """
        ...

    @abstractmethod
    async def assign_project(
        self,
        project_id: int,
        platform_id: Optional[int]
    ) -> bool:
        """
        Assign a project to a platform (or unassign if platform_id is None).

        Args:
            project_id: Project to assign
            platform_id: Platform to assign to (None = unassign)

        Returns:
            True if successful, False if project not found.
        """
        ...

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def check_name_exists(
        self,
        name: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if platform name exists globally.

        Args:
            name: Name to check
            exclude_id: Platform ID to exclude (for rename operations)

        Returns:
            True if name exists, False otherwise.
        """
        ...

    @abstractmethod
    async def count(self) -> int:
        """
        Count all platforms.

        Returns:
            Platform count.
        """
        ...

    @abstractmethod
    async def get_projects(self, platform_id: int) -> List[Dict[str, Any]]:
        """
        Get all projects in a platform.

        Args:
            platform_id: Platform to get projects for

        Returns:
            List of project dicts (id, name, description).
        """
        ...

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search platforms by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.

        Args:
            query: Search term (will match names containing this string)

        Returns:
            List of matching platform dicts.
        """
        ...
