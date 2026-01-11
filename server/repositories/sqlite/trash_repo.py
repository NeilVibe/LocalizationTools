"""
SQLite TrashRepository Implementation.

P10: FULL PARITY - Trash persists in SQLite identically to PostgreSQL.
No stubs, no ephemeral, no shortcuts.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.trash_repository import TrashRepository
from server.database.offline import get_offline_db


class SQLiteTrashRepository(TrashRepository):
    """
    SQLite implementation of TrashRepository.

    FULL PARITY: Identical behavior to PostgreSQL.
    Uses offline_trash table for persistence.
    """

    def __init__(self):
        self.db = get_offline_db()

    def _row_to_dict(self, row: dict) -> Dict[str, Any]:
        """Convert SQLite row to dict."""
        item_data = row.get("item_data")
        if isinstance(item_data, str):
            item_data = json.loads(item_data)

        return {
            "id": row["id"],
            "item_type": row["item_type"],
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "item_data": item_data,
            "parent_project_id": row.get("parent_project_id"),
            "parent_folder_id": row.get("parent_folder_id"),
            "deleted_by": row.get("deleted_by"),
            "deleted_at": row.get("deleted_at"),
            "expires_at": row.get("expires_at"),
            "status": row.get("status", "trashed")
        }

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get(self, trash_id: int) -> Optional[Dict[str, Any]]:
        """Get trash item by ID."""
        logger.debug(f"[TRASH-SQLITE] get: trash_id={trash_id}")

        conn = self.db._get_connection()
        row = conn.execute(
            "SELECT * FROM offline_trash WHERE id = ?",
            (trash_id,)
        ).fetchone()

        if not row:
            return None

        return self._row_to_dict(dict(row))

    async def get_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all trash items for a user."""
        logger.debug(f"[TRASH-SQLITE] get_for_user: user_id={user_id}")

        conn = self.db._get_connection()
        rows = conn.execute(
            """SELECT * FROM offline_trash
               WHERE deleted_by = ? AND status = 'trashed'
               ORDER BY deleted_at DESC""",
            (user_id,)
        ).fetchall()

        items = [self._row_to_dict(dict(r)) for r in rows]
        logger.debug(f"[TRASH-SQLITE] get_for_user result: user_id={user_id}, count={len(items)}")
        return items

    async def get_expired(self) -> List[Dict[str, Any]]:
        """Get all expired trash items."""
        logger.debug("[TRASH-SQLITE] get_expired")

        now = datetime.utcnow().isoformat()
        conn = self.db._get_connection()
        rows = conn.execute(
            """SELECT * FROM offline_trash
               WHERE expires_at < ? AND status = 'trashed'""",
            (now,)
        ).fetchall()

        items = [self._row_to_dict(dict(r)) for r in rows]
        logger.debug(f"[TRASH-SQLITE] get_expired result: count={len(items)}")
        return items

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
        logger.debug(f"[TRASH-SQLITE] create: item_type={item_type}, item_id={item_id}, item_name={item_name}")

        conn = self.db._get_connection()
        deleted_at = datetime.utcnow().isoformat()
        expires_at = (datetime.utcnow() + timedelta(days=retention_days)).isoformat()
        item_data_json = json.dumps(item_data)

        cursor = conn.execute("""
            INSERT INTO offline_trash
            (item_type, item_id, item_name, item_data, parent_project_id, parent_folder_id,
             deleted_by, deleted_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'trashed')
        """, (item_type, item_id, item_name, item_data_json, parent_project_id,
              parent_folder_id, deleted_by, deleted_at, expires_at))

        trash_id = cursor.lastrowid
        conn.commit()

        logger.success(f"[TRASH-SQLITE] Created: id={trash_id}, item_type={item_type}, item_name={item_name}")

        return {
            "id": trash_id,
            "item_type": item_type,
            "item_id": item_id,
            "item_name": item_name,
            "item_data": item_data,
            "parent_project_id": parent_project_id,
            "parent_folder_id": parent_folder_id,
            "deleted_by": deleted_by,
            "deleted_at": deleted_at,
            "expires_at": expires_at,
            "status": "trashed"
        }

    async def restore(self, trash_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Mark trash item as restored."""
        logger.debug(f"[TRASH-SQLITE] restore: trash_id={trash_id}, user_id={user_id}")

        conn = self.db._get_connection()

        # Get item first
        row = conn.execute(
            """SELECT * FROM offline_trash
               WHERE id = ? AND deleted_by = ? AND status = 'trashed'""",
            (trash_id, user_id)
        ).fetchone()

        if not row:
            logger.warning(f"[TRASH-SQLITE] restore: not found trash_id={trash_id}")
            return None

        # Mark as restored
        conn.execute(
            "UPDATE offline_trash SET status = 'restored' WHERE id = ?",
            (trash_id,)
        )
        conn.commit()

        result = self._row_to_dict(dict(row))
        result["status"] = "restored"

        logger.success(f"[TRASH-SQLITE] Restored: id={trash_id}, item_name={result['item_name']}")
        return result

    async def permanent_delete(self, trash_id: int, user_id: int) -> bool:
        """Permanently delete a trash item."""
        logger.debug(f"[TRASH-SQLITE] permanent_delete: trash_id={trash_id}, user_id={user_id}")

        conn = self.db._get_connection()

        # Check exists
        row = conn.execute(
            """SELECT id FROM offline_trash
               WHERE id = ? AND deleted_by = ? AND status = 'trashed'""",
            (trash_id, user_id)
        ).fetchone()

        if not row:
            logger.warning(f"[TRASH-SQLITE] permanent_delete: not found trash_id={trash_id}")
            return False

        conn.execute("DELETE FROM offline_trash WHERE id = ?", (trash_id,))
        conn.commit()

        logger.success(f"[TRASH-SQLITE] Permanently deleted: id={trash_id}")
        return True

    async def empty_for_user(self, user_id: int) -> int:
        """Empty all trash for a user."""
        logger.debug(f"[TRASH-SQLITE] empty_for_user: user_id={user_id}")

        conn = self.db._get_connection()

        # Count first
        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM offline_trash WHERE deleted_by = ? AND status = 'trashed'",
            (user_id,)
        ).fetchone()
        count = count_row["count"] if count_row else 0

        # Delete
        conn.execute(
            "DELETE FROM offline_trash WHERE deleted_by = ? AND status = 'trashed'",
            (user_id,)
        )
        conn.commit()

        logger.success(f"[TRASH-SQLITE] Emptied for user: user_id={user_id}, count={count}")
        return count

    async def cleanup_expired(self) -> int:
        """Delete all expired trash items."""
        logger.debug("[TRASH-SQLITE] cleanup_expired")

        now = datetime.utcnow().isoformat()
        conn = self.db._get_connection()

        # Count first
        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM offline_trash WHERE expires_at < ? AND status = 'trashed'",
            (now,)
        ).fetchone()
        count = count_row["count"] if count_row else 0

        # Delete
        conn.execute(
            "DELETE FROM offline_trash WHERE expires_at < ? AND status = 'trashed'",
            (now,)
        )
        conn.commit()

        logger.success(f"[TRASH-SQLITE] Cleaned up expired: count={count}")
        return count

    # =========================================================================
    # Utility Operations
    # =========================================================================

    async def count_for_user(self, user_id: int) -> int:
        """Count trash items for a user."""
        conn = self.db._get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as count FROM offline_trash WHERE deleted_by = ? AND status = 'trashed'",
            (user_id,)
        ).fetchone()
        return row["count"] if row else 0
