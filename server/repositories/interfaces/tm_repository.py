"""
TM Repository Interface.

This is the contract that both PostgreSQL and SQLite adapters must implement.
Routes use this interface - they never know which database they're talking to.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class AssignmentTarget:
    """Target for TM assignment. Only ONE should be set (or none for unassign)."""
    platform_id: Optional[int] = None
    project_id: Optional[int] = None
    folder_id: Optional[int] = None

    def is_unassigned(self) -> bool:
        """Check if this represents 'unassigned' (all None)."""
        return self.platform_id is None and self.project_id is None and self.folder_id is None

    def scope_count(self) -> int:
        """Count how many scopes are set (should be 0 or 1)."""
        return sum([1 for x in [self.platform_id, self.project_id, self.folder_id] if x is not None])


class TMRepository(ABC):
    """
    Translation Memory repository interface.

    Both PostgreSQLTMRepository and SQLiteTMRepository implement this EXACTLY.
    This guarantees offline parity - same operations work in both modes.
    """

    # =========================================================================
    # Core CRUD
    # =========================================================================

    @abstractmethod
    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get TM by ID.

        Returns:
            TM dict with: id, name, source_lang, target_lang, entry_count, status, etc.
            None if not found.
        """
        ...

    @abstractmethod
    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all TMs accessible to current user.

        Returns:
            List of TM dicts.
        """
        ...

    @abstractmethod
    async def create(
        self,
        name: str,
        source_lang: str = "ko",
        target_lang: str = "en",
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create new TM.

        Returns:
            Created TM dict.
        """
        ...

    @abstractmethod
    async def delete(self, tm_id: int) -> bool:
        """
        Delete TM and all its entries.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    @abstractmethod
    async def assign(self, tm_id: int, target: AssignmentTarget) -> Dict[str, Any]:
        """
        Assign TM to a platform/project/folder.

        Args:
            tm_id: TM to assign
            target: Where to assign (only one scope should be set)

        Returns:
            Updated TM dict with assignment info.
        """
        ...

    @abstractmethod
    async def unassign(self, tm_id: int) -> Dict[str, Any]:
        """
        Remove TM assignment (move to unassigned).

        Returns:
            Updated TM dict.
        """
        ...

    @abstractmethod
    async def activate(self, tm_id: int) -> Dict[str, Any]:
        """
        Activate TM (must be assigned first).

        Returns:
            Updated TM dict with is_active=True.

        Raises:
            ValueError: If TM is not assigned to any scope.
        """
        ...

    @abstractmethod
    async def deactivate(self, tm_id: int) -> Dict[str, Any]:
        """
        Deactivate TM.

        Returns:
            Updated TM dict with is_active=False.
        """
        ...

    @abstractmethod
    async def get_assignment(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current assignment for a TM.

        Returns:
            Assignment dict with platform_id, project_id, folder_id, is_active.
            None if TM is unassigned.
        """
        ...

    # =========================================================================
    # Scope Queries
    # =========================================================================

    @abstractmethod
    async def get_for_scope(
        self,
        platform_id: Optional[int] = None,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get TMs assigned to a specific scope.

        If all params are None, returns unassigned TMs.

        Returns:
            List of TM dicts with assignment info.
        """
        ...

    @abstractmethod
    async def get_active_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        """
        Get all active TMs that apply to a file (inherited from folder/project/platform).

        Returns:
            List of active TM dicts, ordered by priority.
        """
        ...

    # =========================================================================
    # TM Entries
    # =========================================================================

    @abstractmethod
    async def add_entry(
        self,
        tm_id: int,
        source: str,
        target: str,
        string_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add entry to TM.

        Returns:
            Created entry dict.
        """
        ...

    @abstractmethod
    async def get_entries(
        self,
        tm_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get TM entries with pagination.

        Returns:
            List of entry dicts.
        """
        ...

    @abstractmethod
    async def search_entries(
        self,
        tm_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search TM entries by source text.

        Returns:
            List of matching entry dicts with match_score.
        """
        ...

    @abstractmethod
    async def delete_entry(self, entry_id: int) -> bool:
        """
        Delete a TM entry.

        Returns:
            True if deleted, False if not found.
        """
        ...

    # =========================================================================
    # Tree Structure (for UI)
    # =========================================================================

    @abstractmethod
    async def get_tree(self) -> Dict[str, Any]:
        """
        Get full TM tree structure for UI.

        Returns:
            Dict with:
            - unassigned: List of unassigned TMs
            - platforms: List of platforms with nested projects/folders/TMs
        """
        ...
