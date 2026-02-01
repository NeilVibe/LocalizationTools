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
    # TM Linking (Active TMs for Projects)
    # =========================================================================

    @abstractmethod
    async def link_to_project(
        self,
        tm_id: int,
        project_id: int,
        priority: int = 1
    ) -> Dict[str, Any]:
        """
        Link a TM to a project for auto-add on confirm.

        Creates an LDMActiveTM record linking the TM to the project.
        If link already exists, updates priority.

        Args:
            tm_id: TM ID to link
            project_id: Project ID to link to
            priority: Priority order (lower = higher priority)

        Returns:
            Dict with link info: {tm_id, project_id, priority, created: bool}
            'created' is True if new link, False if existing link was updated.
        """
        ...

    @abstractmethod
    async def unlink_from_project(self, tm_id: int, project_id: int) -> bool:
        """
        Unlink a TM from a project.

        Deletes the LDMActiveTM record.

        Returns:
            True if unlinked, False if not found.
        """
        ...

    @abstractmethod
    async def get_linked_for_project(
        self,
        project_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the highest-priority linked TM for a project.

        Args:
            project_id: Project ID to get linked TM for
            user_id: Optional user ID to filter by TM ownership

        Returns:
            TM dict or None if no TM linked.
        """
        ...

    @abstractmethod
    async def get_all_linked_for_project(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all TMs linked to a project, ordered by priority.

        Args:
            project_id: Project ID to get linked TMs for

        Returns:
            List of dicts with TM info and link details:
            {tm_id, tm_name, priority, status, entry_count, linked_at}
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
        Add single entry to TM.

        Returns:
            Created entry dict.
        """
        ...

    @abstractmethod
    async def add_entries_bulk(
        self,
        tm_id: int,
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk add entries to TM.

        High-performance bulk insert:
        - PostgreSQL: Uses COPY TEXT (20k+ entries/sec)
        - SQLite: Uses executemany (instant for 1000s)

        Args:
            tm_id: TM to add entries to
            entries: List of dicts with 'source'/'source_text' and 'target'/'target_text'

        Returns:
            Number of entries inserted.
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
    async def get_all_entries(self, tm_id: int) -> List[Dict[str, Any]]:
        """
        Get ALL entries for TM (no pagination).

        LIMIT-002: Used for building FAISS indexes in pretranslation.
        Returns all entries for the TM without pagination limits.

        Returns:
            List of entry dicts with: id, tm_id, source_text, target_text,
            source_hash, string_id, is_confirmed
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

    @abstractmethod
    async def update_entry(
        self,
        entry_id: int,
        source_text: Optional[str] = None,
        target_text: Optional[str] = None,
        string_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a TM entry.

        Args:
            entry_id: Entry to update
            source_text: New source text (if provided)
            target_text: New target text (if provided)
            string_id: New string ID (if provided)
            updated_by: Username who made the update

        Returns:
            Updated entry dict, or None if not found.
        """
        ...

    @abstractmethod
    async def confirm_entry(
        self,
        entry_id: int,
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Confirm or unconfirm a TM entry (memoQ-style workflow).

        Args:
            entry_id: Entry to confirm/unconfirm
            confirm: True to confirm, False to unconfirm
            confirmed_by: Username who confirmed

        Returns:
            Updated entry dict, or None if not found.
        """
        ...

    @abstractmethod
    async def bulk_confirm_entries(
        self,
        tm_id: int,
        entry_ids: List[int],
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> int:
        """
        Bulk confirm/unconfirm multiple TM entries.

        Args:
            tm_id: TM containing the entries
            entry_ids: List of entry IDs to confirm/unconfirm
            confirm: True to confirm, False to unconfirm
            confirmed_by: Username who confirmed

        Returns:
            Number of entries updated.
        """
        ...

    @abstractmethod
    async def get_glossary_terms(
        self,
        tm_ids: List[int],
        max_length: int = 20,
        limit: int = 1000
    ) -> List[tuple]:
        """
        Get short TM entries as glossary terms for QA checks.

        Args:
            tm_ids: List of TM IDs to get terms from
            max_length: Maximum source text length for glossary terms
            limit: Maximum number of terms to return

        Returns:
            List of (source, target) tuples
        """
        ...

    # =========================================================================
    # Index Operations (P10-REPO)
    # =========================================================================

    @abstractmethod
    async def get_indexes(self, tm_id: int) -> List[Dict[str, Any]]:
        """
        Get index status for a TM.

        Returns:
            List of index dicts with type, status, file_size, built_at.
        """
        ...

    @abstractmethod
    async def count_entries(self, tm_id: int) -> int:
        """
        Count entries in a TM.

        Returns:
            Entry count.
        """
        ...

    # =========================================================================
    # Advanced Search (P10-REPO: PostgreSQL-specific features)
    # =========================================================================

    @abstractmethod
    async def search_exact(
        self,
        tm_id: int,
        source: str
    ) -> Optional[Dict[str, Any]]:
        """
        Search for exact match in TM using hash-based O(1) lookup.

        Args:
            tm_id: TM to search in
            source: Source text to find exact match for

        Returns:
            Entry dict with source_text, target_text, or None if not found.
        """
        ...

    @abstractmethod
    async def search_similar(
        self,
        tm_id: int,
        source: str,
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar entries using pg_trgm similarity.

        Note: PostgreSQL-specific feature (pg_trgm extension).
        SQLite adapter returns empty list (similarity search not available offline).

        Args:
            tm_id: TM to search in
            source: Source text to find similar matches for
            threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum results to return

        Returns:
            List of entry dicts with source, target, similarity score.
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

    # =========================================================================
    # Name Validation (ARCH-002: Factory pattern compliance)
    # =========================================================================

    @abstractmethod
    async def check_name_exists(self, name: str) -> bool:
        """
        Check if a TM with the given name already exists.

        ARCH-002: This method replaces direct database access in routes,
        ensuring proper factory pattern usage for offline/online parity.

        Args:
            name: TM name to check for existence

        Returns:
            True if a TM with this name exists, False otherwise.
        """
        ...
