"""
Row Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple


class RowRepository(ABC):
    """
    Row repository interface.

    Both PostgreSQLRowRepository and SQLiteRowRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, row_id: int) -> Optional[Dict[str, Any]]:
        """
        Get row by ID.

        Returns:
            Row dict with: id, file_id, row_num, string_id, source, target,
            status, extra_data, created_at, updated_at.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_with_file(self, row_id: int) -> Optional[Dict[str, Any]]:
        """
        Get row with file info (for permission checks).

        Returns:
            Row dict with file_id, file_name, project_id included.
            None if not found.
        """
        ...

    @abstractmethod
    async def create(
        self,
        file_id: int,
        row_num: int,
        source: str,
        target: str = "",
        string_id: Optional[str] = None,
        status: str = "pending",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a single row.

        Returns:
            Created row dict with id.
        """
        ...

    @abstractmethod
    async def update(
        self,
        row_id: int,
        target: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a row's target text or status.

        Args:
            row_id: Row to update
            target: New target text (None = don't change)
            status: New status (None = don't change)
            updated_by: User ID who made the update

        Returns:
            Updated row dict, or None if not found.
        """
        ...

    @abstractmethod
    async def delete(self, row_id: int) -> bool:
        """
        Delete a row.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    @abstractmethod
    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk create rows for a file.

        Args:
            file_id: File to add rows to
            rows: List of row dicts with: row_num, source, target, string_id, etc.

        Returns:
            Count of rows created.
        """
        ...

    @abstractmethod
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk update multiple rows.

        Args:
            updates: List of dicts with: id, target, status

        Returns:
            Count of rows updated.
        """
        ...

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def get_for_file(
        self,
        file_id: int,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        search_mode: str = "contain",
        search_fields: str = "source,target",
        status: Optional[str] = None,
        filter_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated rows for a file with search/filter.

        Args:
            file_id: File ID
            page: Page number (1-indexed)
            limit: Results per page
            search: Search term (optional)
            search_mode: contain, exact, not_contain, fuzzy
            search_fields: Comma-separated: string_id, source, target
            status: Filter by status (optional)
            filter_type: all, confirmed, unconfirmed, qa_flagged

        Returns:
            Tuple of (rows_list, total_count)
        """
        ...

    @abstractmethod
    async def get_all_for_file(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all rows for a file (no pagination, for export).

        Args:
            file_id: File ID
            status_filter: Optional status filter (reviewed, translated, etc.)

        Returns:
            All rows for the file.
        """
        ...

    @abstractmethod
    async def count_for_file(self, file_id: int) -> int:
        """
        Count rows in a file.

        Returns:
            Total row count.
        """
        ...

    # =========================================================================
    # History Operations
    # =========================================================================

    @abstractmethod
    async def add_edit_history(
        self,
        row_id: int,
        user_id: int,
        old_target: Optional[str],
        new_target: Optional[str],
        old_status: Optional[str],
        new_status: Optional[str]
    ) -> None:
        """
        Record edit history for a row.
        """
        ...

    @abstractmethod
    async def get_edit_history(
        self,
        row_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get edit history for a row.

        Returns:
            List of history entries, newest first.
        """
        ...
