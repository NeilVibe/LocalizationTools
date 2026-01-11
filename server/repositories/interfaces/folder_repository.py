"""
Folder Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class FolderRepository(ABC):
    """
    Folder repository interface.

    Both PostgreSQLFolderRepository and SQLiteFolderRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get folder by ID.

        Returns:
            Folder dict with: id, name, project_id, parent_id, created_at, updated_at.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_all(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all folders in a project.

        Args:
            project_id: Project to list folders for

        Returns:
            List of folder dicts.
        """
        ...

    @abstractmethod
    async def create(
        self,
        name: str,
        project_id: int,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new folder.

        Args:
            name: Folder name (will be auto-renamed if duplicate in same parent)
            project_id: Project this folder belongs to
            parent_id: Parent folder ID (None = root of project)

        Returns:
            Created folder dict with id.
        """
        ...

    @abstractmethod
    async def delete(self, folder_id: int) -> bool:
        """
        Delete a folder and all its contents.

        Note: This is the database-level delete. Soft delete (trash)
        is handled at the route level.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Folder-Specific Operations
    # =========================================================================

    @abstractmethod
    async def get_with_contents(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get folder with its subfolders and files.

        Returns:
            Folder dict with additional:
            - subfolders: List of {id, name, created_at}
            - files: List of {id, name, format, row_count, created_at}
            None if not found.
        """
        ...

    @abstractmethod
    async def rename(self, folder_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """
        Rename a folder.

        Args:
            folder_id: Folder to rename
            new_name: New name

        Returns:
            Updated folder dict, or None if not found.

        Raises:
            ValueError if name already exists in same parent.
        """
        ...

    @abstractmethod
    async def move(
        self,
        folder_id: int,
        parent_folder_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Move a folder to a different parent folder within same project.

        Args:
            folder_id: Folder to move
            parent_folder_id: New parent folder ID (None = project root)

        Returns:
            Updated folder dict, or None if not found.

        Raises:
            ValueError if trying to move folder into itself or its descendants.
        """
        ...

    @abstractmethod
    async def move_cross_project(
        self,
        folder_id: int,
        target_project_id: int,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Move a folder to a different project.
        Updates the folder and all its contents (subfolders, files).

        Args:
            folder_id: Folder to move
            target_project_id: Destination project ID
            target_parent_id: Parent folder in destination (None = root)

        Returns:
            Updated folder dict with new_name (may be auto-renamed).
            None if not found.
        """
        ...

    @abstractmethod
    async def copy(
        self,
        folder_id: int,
        target_project_id: Optional[int] = None,
        target_parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Copy a folder and all its contents to a different location.

        Args:
            folder_id: Folder to copy
            target_project_id: Destination project (None = same project)
            target_parent_id: Parent folder in destination (None = root)

        Returns:
            New folder dict with: new_folder_id, name, files_copied.
            None if source folder not found.
        """
        ...

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def check_name_exists(
        self,
        name: str,
        project_id: int,
        parent_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if folder name exists in parent.

        Args:
            name: Name to check
            project_id: Project to check within
            parent_id: Parent folder (None = root level)
            exclude_id: Folder ID to exclude (for rename operations)

        Returns:
            True if name exists, False otherwise.
        """
        ...

    @abstractmethod
    async def generate_unique_name(
        self,
        base_name: str,
        project_id: int,
        parent_id: Optional[int] = None
    ) -> str:
        """
        Generate a unique folder name.

        If base_name exists, appends _1, _2, etc.

        Args:
            base_name: Starting name
            project_id: Project to check within
            parent_id: Parent folder (None = root level)

        Returns:
            Unique name (may be same as base_name if not taken).
        """
        ...

    @abstractmethod
    async def get_children(self, folder_id: int) -> List[Dict[str, Any]]:
        """
        Get direct subfolders of a folder.

        Args:
            folder_id: Parent folder ID

        Returns:
            List of subfolder dicts.
        """
        ...

    @abstractmethod
    async def is_descendant(self, folder_id: int, potential_ancestor_id: int) -> bool:
        """
        Check if folder_id is a descendant of potential_ancestor_id.
        Used to prevent circular references when moving folders.

        Args:
            folder_id: Folder to check
            potential_ancestor_id: Potential ancestor folder

        Returns:
            True if folder_id is inside potential_ancestor_id, False otherwise.
        """
        ...

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search folders by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.

        Args:
            query: Search term (will match names containing this string)

        Returns:
            List of matching folder dicts with project_id, parent_id for path building.
        """
        ...
