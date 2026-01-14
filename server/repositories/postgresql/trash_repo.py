"""
PostgreSQL TrashRepository Implementation.

Full persistence of trash items in PostgreSQL.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from server.repositories.interfaces.trash_repository import TrashRepository
from server.database.models import LDMTrash


class PostgreSQLTrashRepository(TrashRepository):
    """
    PostgreSQL implementation of TrashRepository.

    P10: FULL ABSTRACT - User context baked in for ownership checks.
    Trash items are user-scoped (users only see their own trash).
    """

    def __init__(self, db: AsyncSession, user: Optional[dict] = None):
        self.db = db
        self.user = user or {}

    def _is_admin(self) -> bool:
        return self.user.get("role") in ["admin", "superadmin"]

    def _get_user_id(self) -> Optional[int]:
        return self.user.get("user_id")

    def _trash_to_dict(self, item: LDMTrash) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dict."""
        return {
            "id": item.id,
            "item_type": item.item_type,
            "item_id": item.item_id,
            "item_name": item.item_name,
            "item_data": item.item_data,
            "parent_project_id": item.parent_project_id,
            "parent_folder_id": item.parent_folder_id,
            "deleted_by": item.deleted_by,
            "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "status": item.status
        }

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get(self, trash_id: int) -> Optional[Dict[str, Any]]:
        """Get trash item by ID."""
        logger.debug(f"[TRASH] get: trash_id={trash_id}")

        result = await self.db.execute(
            select(LDMTrash).where(LDMTrash.id == trash_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            return None

        return self._trash_to_dict(item)

    async def get_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all trash items for a user."""
        logger.debug(f"[TRASH] get_for_user: user_id={user_id}")

        result = await self.db.execute(
            select(LDMTrash)
            .where(
                LDMTrash.deleted_by == user_id,
                LDMTrash.status == "trashed"
            )
            .order_by(LDMTrash.deleted_at.desc())
        )
        items = result.scalars().all()

        logger.debug(f"[TRASH] get_for_user result: user_id={user_id}, count={len(items)}")
        return [self._trash_to_dict(item) for item in items]

    async def get_expired(self) -> List[Dict[str, Any]]:
        """Get all expired trash items."""
        logger.debug("[TRASH] get_expired")

        now = datetime.utcnow()
        result = await self.db.execute(
            select(LDMTrash)
            .where(
                LDMTrash.expires_at < now,
                LDMTrash.status == "trashed"
            )
        )
        items = result.scalars().all()

        logger.debug(f"[TRASH] get_expired result: count={len(items)}")
        return [self._trash_to_dict(item) for item in items]

    # =========================================================================
    # Write Operations
    # =========================================================================

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
        """Add item to trash."""
        logger.debug(f"[TRASH] create: item_type={item_type}, item_id={item_id}, item_name={item_name}")

        expires_at = datetime.utcnow() + timedelta(days=retention_days)

        trash_item = LDMTrash(
            item_type=item_type,
            item_id=item_id,
            item_name=item_name,
            item_data=item_data,
            parent_project_id=parent_project_id,
            parent_folder_id=parent_folder_id,
            deleted_by=deleted_by,
            expires_at=expires_at,
            status="trashed"
        )

        self.db.add(trash_item)
        await self.db.flush()

        logger.success(f"[TRASH] Created: id={trash_item.id}, item_type={item_type}, item_name={item_name}")
        return self._trash_to_dict(trash_item)

    async def restore(self, trash_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Mark trash item as restored."""
        logger.debug(f"[TRASH] restore: trash_id={trash_id}, user_id={user_id}")

        result = await self.db.execute(
            select(LDMTrash).where(
                LDMTrash.id == trash_id,
                LDMTrash.deleted_by == user_id,
                LDMTrash.status == "trashed"
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            logger.warning(f"[TRASH] restore: not found trash_id={trash_id}")
            return None

        item.status = "restored"
        await self.db.flush()

        logger.success(f"[TRASH] Restored: id={trash_id}, item_name={item.item_name}")
        return self._trash_to_dict(item)

    async def permanent_delete(self, trash_id: int, user_id: int) -> bool:
        """Permanently delete a trash item."""
        logger.debug(f"[TRASH] permanent_delete: trash_id={trash_id}, user_id={user_id}")

        result = await self.db.execute(
            select(LDMTrash).where(
                LDMTrash.id == trash_id,
                LDMTrash.deleted_by == user_id,
                LDMTrash.status == "trashed"
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            logger.warning(f"[TRASH] permanent_delete: not found trash_id={trash_id}")
            return False

        await self.db.delete(item)
        await self.db.flush()

        logger.success(f"[TRASH] Permanently deleted: id={trash_id}")
        return True

    async def empty_for_user(self, user_id: int) -> int:
        """Empty all trash for a user."""
        logger.debug(f"[TRASH] empty_for_user: user_id={user_id}")

        result = await self.db.execute(
            delete(LDMTrash).where(
                LDMTrash.deleted_by == user_id,
                LDMTrash.status == "trashed"
            )
        )

        count = result.rowcount
        logger.success(f"[TRASH] Emptied for user: user_id={user_id}, count={count}")
        return count

    async def cleanup_expired(self) -> int:
        """Delete all expired trash items."""
        logger.debug("[TRASH] cleanup_expired")

        now = datetime.utcnow()
        result = await self.db.execute(
            delete(LDMTrash).where(
                LDMTrash.expires_at < now,
                LDMTrash.status == "trashed"
            )
        )

        count = result.rowcount
        logger.success(f"[TRASH] Cleaned up expired: count={count}")
        return count

    # =========================================================================
    # Utility Operations
    # =========================================================================

    async def count_for_user(self, user_id: int) -> int:
        """Count trash items for a user."""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(LDMTrash.id))
            .where(
                LDMTrash.deleted_by == user_id,
                LDMTrash.status == "trashed"
            )
        )
        return result.scalar() or 0
