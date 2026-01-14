"""
PostgreSQL Capability Repository Implementation.
P10-REPO: Admin capability management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.database.models import User, UserCapability
from server.repositories.interfaces.capability_repository import CapabilityRepository


class PostgreSQLCapabilityRepository(CapabilityRepository):
    """
    PostgreSQL implementation of CapabilityRepository.

    P10: FULL ABSTRACT - User context baked in for admin checks.
    Capability management is admin-only.
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    def _is_admin(self) -> bool:
        return self.user.get("role") in ["admin", "superadmin"]

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }

    async def get_capability(self, capability_id: int) -> Optional[Dict[str, Any]]:
        """Get capability grant by ID."""
        result = await self.db.execute(
            select(UserCapability).where(UserCapability.id == capability_id)
        )
        cap = result.scalar_one_or_none()
        if not cap:
            return None
        return {
            "id": cap.id,
            "user_id": cap.user_id,
            "capability_name": cap.capability_name,
            "granted_by": cap.granted_by,
            "granted_at": cap.granted_at,
            "expires_at": cap.expires_at
        }

    async def get_user_capability(
        self, user_id: int, capability_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific capability for a user."""
        result = await self.db.execute(
            select(UserCapability).where(
                UserCapability.user_id == user_id,
                UserCapability.capability_name == capability_name
            )
        )
        cap = result.scalar_one_or_none()
        if not cap:
            return None
        return {
            "id": cap.id,
            "user_id": cap.user_id,
            "capability_name": cap.capability_name,
            "granted_by": cap.granted_by,
            "granted_at": cap.granted_at,
            "expires_at": cap.expires_at
        }

    async def grant_capability(
        self,
        user_id: int,
        capability_name: str,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Grant a capability to a user."""
        capability = UserCapability(
            user_id=user_id,
            capability_name=capability_name,
            granted_by=granted_by,
            expires_at=expires_at
        )
        self.db.add(capability)
        await self.db.commit()
        await self.db.refresh(capability)
        return {
            "id": capability.id,
            "user_id": capability.user_id,
            "capability_name": capability.capability_name,
            "granted_by": capability.granted_by,
            "granted_at": capability.granted_at,
            "expires_at": capability.expires_at
        }

    async def revoke_capability(self, capability_id: int) -> bool:
        """Revoke a capability grant."""
        result = await self.db.execute(
            select(UserCapability).where(UserCapability.id == capability_id)
        )
        capability = result.scalar_one_or_none()
        if not capability:
            return False
        await self.db.delete(capability)
        await self.db.commit()
        return True

    async def list_all_capabilities(self) -> List[Dict[str, Any]]:
        """List all capability grants with user info."""
        result = await self.db.execute(
            select(UserCapability, User.username)
            .join(User, UserCapability.user_id == User.user_id)
            .order_by(UserCapability.user_id, UserCapability.capability_name)
        )
        rows = result.all()
        return [
            {
                "id": cap.id,
                "user_id": cap.user_id,
                "username": username,
                "capability_name": cap.capability_name,
                "granted_by": cap.granted_by,
                "granted_at": cap.granted_at,
                "expires_at": cap.expires_at
            }
            for cap, username in rows
        ]

    async def list_user_capabilities(self, user_id: int) -> List[Dict[str, Any]]:
        """List capabilities for a specific user."""
        result = await self.db.execute(
            select(UserCapability).where(UserCapability.user_id == user_id)
        )
        caps = result.scalars().all()
        return [
            {
                "id": cap.id,
                "user_id": cap.user_id,
                "capability_name": cap.capability_name,
                "granted_by": cap.granted_by,
                "granted_at": cap.granted_at,
                "expires_at": cap.expires_at
            }
            for cap in caps
        ]
