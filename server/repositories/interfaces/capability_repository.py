"""
Capability Repository Interface.
P10-REPO: Admin capability management abstraction.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class CapabilityRepository(ABC):
    """
    Repository interface for user capability management.
    Note: This is primarily online-only (admin functionality).
    """

    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        ...

    @abstractmethod
    async def get_capability(self, capability_id: int) -> Optional[Dict[str, Any]]:
        """Get capability grant by ID."""
        ...

    @abstractmethod
    async def get_user_capability(
        self, user_id: int, capability_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific capability for a user."""
        ...

    @abstractmethod
    async def grant_capability(
        self,
        user_id: int,
        capability_name: str,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Grant a capability to a user."""
        ...

    @abstractmethod
    async def revoke_capability(self, capability_id: int) -> bool:
        """Revoke a capability grant."""
        ...

    @abstractmethod
    async def list_all_capabilities(self) -> List[Dict[str, Any]]:
        """List all capability grants with user info."""
        ...

    @abstractmethod
    async def list_user_capabilities(self, user_id: int) -> List[Dict[str, Any]]:
        """List capabilities for a specific user."""
        ...
