"""
QAResultRepository Interface.

Repository Pattern: Abstract interface for QA result operations.
Both PostgreSQL and SQLite adapters implement this interface.

P10: FULL PARITY - QA results persist identically in both databases.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class QAResultRepository(ABC):
    """
    QA Result repository interface.

    FULL PARITY: Both PostgreSQL and SQLite persist QA results identically.
    """

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def get(self, result_id: int) -> Optional[Dict[str, Any]]:
        """Get QA result by ID."""
        ...

    @abstractmethod
    async def get_for_row(
        self,
        row_id: int,
        include_resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get QA results for a row.

        Args:
            row_id: Row ID
            include_resolved: If True, include resolved issues

        Returns:
            List of QA result dicts
        """
        ...

    @abstractmethod
    async def get_for_file(
        self,
        file_id: int,
        check_type: Optional[str] = None,
        include_resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get QA results for a file with optional check_type filter.

        Args:
            file_id: File ID
            check_type: Optional filter (pattern, line, term, etc.)
            include_resolved: If True, include resolved issues

        Returns:
            List of QA result dicts with row info
        """
        ...

    @abstractmethod
    async def get_summary(self, file_id: int) -> Dict[str, Any]:
        """
        Get QA summary for a file.

        Returns:
            Dict with counts per check_type and last_checked timestamp
        """
        ...

    # =========================================================================
    # Write Operations
    # =========================================================================

    @abstractmethod
    async def create(
        self,
        row_id: int,
        file_id: int,
        check_type: str,
        severity: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new QA result.

        Args:
            row_id: Row with the issue
            file_id: File containing the row
            check_type: Type of check (pattern, line, term, character, grammar)
            severity: error or warning
            message: Human-readable message
            details: Optional structured details

        Returns:
            Created QA result dict
        """
        ...

    @abstractmethod
    async def bulk_create(
        self,
        results: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk create QA results.

        Args:
            results: List of dicts with row_id, file_id, check_type, severity, message, details

        Returns:
            Count of results created
        """
        ...

    @abstractmethod
    async def resolve(
        self,
        result_id: int,
        resolved_by: int
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a QA result as resolved.

        Args:
            result_id: QA result ID
            resolved_by: User ID who resolved it

        Returns:
            Updated QA result dict, or None if not found
        """
        ...

    @abstractmethod
    async def delete_unresolved_for_row(self, row_id: int) -> int:
        """
        Delete all unresolved QA results for a row.
        Used before re-running QA checks.

        Returns:
            Count of deleted results
        """
        ...

    @abstractmethod
    async def delete_for_file(self, file_id: int) -> int:
        """
        Delete all QA results for a file.
        Used when file is deleted.

        Returns:
            Count of deleted results
        """
        ...

    # =========================================================================
    # Utility Operations
    # =========================================================================

    @abstractmethod
    async def count_unresolved_for_row(self, row_id: int) -> int:
        """Count unresolved QA issues for a row."""
        ...

    @abstractmethod
    async def update_row_qa_count(self, row_id: int) -> None:
        """
        Update the row's qa_flag_count field based on unresolved issues.
        Called after creating or resolving QA results.
        """
        ...
