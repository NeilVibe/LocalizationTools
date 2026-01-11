"""
TrashRepository Interface.

Repository Pattern: Abstract interface for trash/recycle bin operations.
Both PostgreSQL and SQLite adapters implement this interface.

P10: FULL PARITY - Trash persists identically in both databases.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class TrashRepository(ABC):
    """
    Trash repository interface.

    FULL PARITY: Both PostgreSQL and SQLite persist trash identically.
    """

    # =========================================================================
    # Query Operations
    # =========================================================================

    @abstractmethod
    async def get(self, trash_id: int) -> Optional[Dict[str, Any]]:
        """Get trash item by ID."""
        ...

    @abstractmethod
    async def get_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all trash items for a user.

        Args:
            user_id: User ID who deleted the items

        Returns:
            List of trash item dicts, sorted by deleted_at DESC
        """
        ...

    @abstractmethod
    async def get_expired(self) -> List[Dict[str, Any]]:
        """
        Get all expired trash items (for cleanup).

        Returns:
            List of trash items where expires_at < now
        """
        ...

    # =========================================================================
    # Write Operations
    # =========================================================================

    @abstractmethod
    async def create(
        self,
        item_type: str,
        item_id: int,
        item_name: str,
        item_data: Dict[str, Any],
        deleted_by: int,
        parent_project_id: Optional[int] = None,
        parent_folder_id: Optional[int] = None,
        retention_days: int = 30
    ) -> Dict[str, Any]:
        """
        Add item to trash.

        Args:
            item_type: Type of item (file, folder, project, platform)
            item_id: Original item ID
            item_name: Display name
            item_data: Full serialized data for restore
            deleted_by: User ID who deleted
            parent_project_id: Project the item belonged to
            parent_folder_id: Folder the item was in
            retention_days: Days before auto-expire

        Returns:
            Created trash item dict
        """
        ...

    @abstractmethod
    async def restore(self, trash_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Mark trash item as restored.

        Args:
            trash_id: Trash item ID
            user_id: User ID requesting restore (must match deleted_by)

        Returns:
            Updated trash item dict with item_data for restore, or None if not found
        """
        ...

    @abstractmethod
    async def permanent_delete(self, trash_id: int, user_id: int) -> bool:
        """
        Permanently delete a trash item.

        Args:
            trash_id: Trash item ID
            user_id: User ID requesting delete (must match deleted_by)

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def empty_for_user(self, user_id: int) -> int:
        """
        Empty all trash for a user (permanent delete all).

        Args:
            user_id: User ID

        Returns:
            Count of items deleted
        """
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Delete all expired trash items.

        Returns:
            Count of items deleted
        """
        ...

    # =========================================================================
    # Utility Operations
    # =========================================================================

    @abstractmethod
    async def count_for_user(self, user_id: int) -> int:
        """Count trash items for a user."""
        ...
