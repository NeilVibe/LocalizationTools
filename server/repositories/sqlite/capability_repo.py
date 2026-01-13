"""
SQLite Capability Repository Implementation.
P10-REPO: Stub for offline mode - capabilities are online-only.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from server.repositories.interfaces.capability_repository import CapabilityRepository


class SQLiteCapabilityRepository(CapabilityRepository):
    """
    SQLite implementation of CapabilityRepository.
    Note: Capabilities are admin-only and don't apply in offline mode.
    All methods return empty/False to gracefully handle offline scenarios.
    """

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Offline mode: No user management."""
        return None

    async def get_capability(self, capability_id: int) -> Optional[Dict[str, Any]]:
        """Offline mode: No capabilities."""
        return None

    async def get_user_capability(
        self, user_id: int, capability_name: str
    ) -> Optional[Dict[str, Any]]:
        """Offline mode: No capabilities."""
        return None

    async def grant_capability(
        self,
        user_id: int,
        capability_name: str,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Offline mode: Cannot grant capabilities."""
        raise NotImplementedError("Capabilities cannot be granted in offline mode")

    async def revoke_capability(self, capability_id: int) -> bool:
        """Offline mode: Cannot revoke capabilities."""
        return False

    async def list_all_capabilities(self) -> List[Dict[str, Any]]:
        """Offline mode: No capabilities."""
        return []

    async def list_user_capabilities(self, user_id: int) -> List[Dict[str, Any]]:
        """Offline mode: No capabilities."""
        return []
