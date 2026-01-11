"""
File Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class FileRepository(ABC):
    """
    File repository interface.

    Both PostgreSQLFileRepository and SQLiteFileRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file by ID.

        Returns:
            File dict with: id, name, original_filename, format, row_count,
            source_language, target_language, project_id, folder_id, extra_data,
            created_at, updated_at.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_all(
        self,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get files with optional filtering and pagination.

        Args:
            project_id: Filter by project (optional)
            folder_id: Filter by folder (optional)
            limit: Max files to return
            offset: Pagination offset

        Returns:
            List of file dicts.
        """
        ...

    @abstractmethod
    async def create(
        self,
        name: str,
        original_filename: str,
        format: str,
        project_id: int,
        folder_id: Optional[int] = None,
        source_language: str = "ko",
        target_language: str = "en",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create file record (without rows).

        Args:
            name: Display name
            original_filename: Original filename when uploaded
            format: File format (xlsx, txt, json, etc.)
            project_id: Parent project ID
            folder_id: Parent folder ID (optional)
            source_language: Source language code
            target_language: Target language code
            extra_data: Additional metadata (format-specific)

        Returns:
            Created file dict with id.
        """
        ...

    @abstractmethod
    async def delete(self, file_id: int, permanent: bool = False) -> bool:
        """
        Delete file (soft delete to trash by default).

        Args:
            file_id: File to delete
            permanent: If True, permanently delete. If False, move to trash.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # File Operations
    # =========================================================================

    @abstractmethod
    async def rename(self, file_id: int, new_name: str) -> Dict[str, Any]:
        """
        Rename file (validates uniqueness in parent).

        Args:
            file_id: File to rename
            new_name: New name for the file

        Returns:
            Updated file dict.

        Raises:
            ValueError: If name already exists in parent folder.
        """
        ...

    @abstractmethod
    async def move(
        self,
        file_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Move file to different folder (same project).

        Args:
            file_id: File to move
            target_folder_id: Target folder ID (None = project root)

        Returns:
            Updated file dict.

        Raises:
            ValueError: If name conflict in target folder.
        """
        ...

    @abstractmethod
    async def move_cross_project(
        self,
        file_id: int,
        target_project_id: int,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Move file to different project (with auto-rename if needed).

        Args:
            file_id: File to move
            target_project_id: Target project ID
            target_folder_id: Target folder ID (None = project root)

        Returns:
            Updated file dict (may have renamed if conflict).
        """
        ...

    @abstractmethod
    async def copy(
        self,
        file_id: int,
        target_project_id: Optional[int] = None,
        target_folder_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Copy file with all rows.

        Args:
            file_id: File to copy
            target_project_id: Target project (None = same project)
            target_folder_id: Target folder (None = same folder or root)

        Returns:
            New file dict (the copy).
        """
        ...

    @abstractmethod
    async def update_row_count(self, file_id: int, count: int) -> None:
        """
        Update file's row_count field.

        Args:
            file_id: File to update
            count: New row count
        """
        ...

    # =========================================================================
    # Row Operations (File-scoped)
    # =========================================================================

    @abstractmethod
    async def get_rows(
        self,
        file_id: int,
        offset: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get rows for file with pagination and optional status filter.

        Args:
            file_id: File ID
            offset: Pagination offset
            limit: Max rows to return
            status_filter: Filter by status (pending, translated, etc.)

        Returns:
            List of row dicts.
        """
        ...

    @abstractmethod
    async def add_rows(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk add rows to file.

        Args:
            file_id: File to add rows to
            rows: List of row dicts with: row_num, source, target, string_id, etc.

        Returns:
            Count of rows added.
        """
        ...

    @abstractmethod
    async def get_rows_for_export(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all rows for file export (no pagination).

        Args:
            file_id: File ID
            status_filter: Optional status filter

        Returns:
            All rows for the file (for export/download).
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
        folder_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if name exists in parent (DB-002 uniqueness).

        Args:
            name: Name to check
            project_id: Project context
            folder_id: Folder context (None = project root)
            exclude_id: Exclude this file ID from check (for rename)

        Returns:
            True if name exists, False if available.
        """
        ...

    @abstractmethod
    async def generate_unique_name(
        self,
        base_name: str,
        project_id: int,
        folder_id: Optional[int] = None
    ) -> str:
        """
        Generate unique name with _1, _2 suffix if needed.

        Args:
            base_name: Desired name
            project_id: Project context
            folder_id: Folder context

        Returns:
            Unique name (base_name if available, or base_name_1, _2, etc.)
        """
        ...

    @abstractmethod
    async def get_with_project(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file with project info (for downloads/exports).

        Returns:
            File dict with project_name included.
            None if not found.
        """
        ...

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search files by name (case-insensitive partial match).

        P10-SEARCH: Used by Explorer Search for unified search across entities.

        Args:
            query: Search term (will match names containing this string)

        Returns:
            List of matching file dicts with project_id, folder_id for path building.
        """
        ...
