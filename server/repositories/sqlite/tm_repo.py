"""
SQLite TM Repository.

Implements TMRepository interface using SQLite (offline.py).
This is the offline mode adapter.

ARCH-001: Schema-aware - works with both OFFLINE (offline_tms) and SERVER (ldm_translation_memories) modes.
LIMIT-001: FAISS-based search_similar() for offline TM suggestions.
"""

import asyncio
import threading
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from server.repositories.interfaces.tm_repository import TMRepository, AssignmentTarget
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode


# Module-level cache for TM indexes (LIMIT-001)
# Thread-safe with lock for concurrent access
_tm_index_cache: Dict[int, Dict[str, Any]] = {}
_tm_index_cache_lock = threading.Lock()
_TM_INDEX_CACHE_MAX_SIZE = 10  # Limit cache to prevent memory bloat


def clear_tm_index_cache(tm_id: Optional[int] = None) -> None:
    """
    Clear TM index cache. Called when TM entries are modified.

    Args:
        tm_id: Specific TM to clear, or None to clear all.
    """
    global _tm_index_cache
    with _tm_index_cache_lock:
        if tm_id is not None:
            if tm_id in _tm_index_cache:
                del _tm_index_cache[tm_id]
                logger.debug(f"[TM-REPO-SQLITE] Cleared cache for TM {tm_id}")
        else:
            _tm_index_cache.clear()
            logger.debug("[TM-REPO-SQLITE] Cleared all TM index cache")


class SQLiteTMRepository(SQLiteBaseRepository, TMRepository):
    """
    SQLite implementation of TMRepository.

    ARCH-001: Schema-aware - uses _table() for dynamic table names.
    Enables full offline TM support - same operations work without server.
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    def _tm_row_to_dict(self, row) -> Optional[Dict[str, Any]]:
        """Convert SQLite TM row to dict format."""
        if not row:
            return None
        # Defensive: convert sqlite3.Row to dict if needed
        if not isinstance(row, dict):
            row = dict(row)
        return {
            "id": row["id"],
            "name": row["name"],
            "source_lang": row.get("source_lang"),
            "target_lang": row.get("target_lang"),
            "entry_count": row.get("entry_count", 0),
            "status": row.get("status", "active"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """Get TM by ID from SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tms')} WHERE id = ?",
                (tm_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            tm = self._tm_row_to_dict(dict(row))

            # Add assignment info
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_assignments')} WHERE tm_id = ?",
                (tm_id,)
            )
            assignment = await cursor.fetchone()

            if assignment:
                assignment = dict(assignment)
                tm.update({
                    "assignment_id": assignment["id"],
                    "platform_id": assignment.get("platform_id"),
                    "project_id": assignment.get("project_id"),
                    "folder_id": assignment.get("folder_id"),
                    "is_active": bool(assignment.get("is_active", False)),
                })

            return tm

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all TMs from SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tms')} ORDER BY name"
            )
            rows = await cursor.fetchall()

            tms = []
            for row in rows:
                tm = self._tm_row_to_dict(dict(row))

                # Add assignment info
                assign_cursor = await conn.execute(
                    f"SELECT * FROM {self._table('tm_assignments')} WHERE tm_id = ?",
                    (row["id"],)
                )
                assignment = await assign_cursor.fetchone()

                if assignment:
                    assignment = dict(assignment)
                    tm.update({
                        "assignment_id": assignment["id"],
                        "platform_id": assignment.get("platform_id"),
                        "project_id": assignment.get("project_id"),
                        "folder_id": assignment.get("folder_id"),
                        "is_active": bool(assignment.get("is_active", False)),
                    })

                tms.append(tm)

            return tms

    async def create(
        self,
        name: str,
        source_lang: str = "ko",
        target_lang: str = "en",
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create new TM in SQLite."""
        tm_id = -int(time.time() * 1000) % 1000000000
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('tms')}
                       (id, server_id, name, source_lang, target_lang, entry_count, status,
                        created_at, updated_at, downloaded_at, sync_status)
                       VALUES (?, 0, ?, ?, ?, 0, 'ready', ?, ?, datetime('now'), 'local')""",
                    (tm_id, name, source_lang, target_lang, now, now)
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('tms')}
                       (id, name, source_lang, target_lang, entry_count, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, 0, 'ready', ?, ?)""",
                    (tm_id, name, source_lang, target_lang, now, now)
                )
            await conn.commit()

        logger.info(f"Created local TM: id={tm_id}, name='{name}'")
        return await self.get(tm_id)

    async def delete(self, tm_id: int) -> bool:
        """Delete TM from SQLite."""
        async with self.db._get_async_connection() as conn:
            # Delete entries
            await conn.execute(f"DELETE FROM {self._table('tm_entries')} WHERE tm_id = ?", (tm_id,))
            # Delete assignments
            await conn.execute(f"DELETE FROM {self._table('tm_assignments')} WHERE tm_id = ?", (tm_id,))
            # Delete TM
            cursor = await conn.execute(f"DELETE FROM {self._table('tms')} WHERE id = ?", (tm_id,))
            await conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted local TM {tm_id}")
            return deleted

    # =========================================================================
    # Assignment Operations
    # =========================================================================

    async def assign(self, tm_id: int, target: AssignmentTarget) -> Dict[str, Any]:
        """Assign TM to scope in SQLite."""
        if target.scope_count() > 1:
            raise ValueError("Only one scope can be set (platform, project, or folder)")

        now = datetime.now().isoformat()
        async with self.db._get_async_connection() as conn:
            # Check if assignment exists
            cursor = await conn.execute(
                f"SELECT id FROM {self._table('tm_assignments')} WHERE tm_id = ?",
                (tm_id,)
            )
            existing = await cursor.fetchone()

            if existing:
                # Update existing
                await conn.execute(
                    f"""UPDATE {self._table('tm_assignments')}
                       SET platform_id = ?, project_id = ?, folder_id = ?, assigned_at = ?
                       WHERE tm_id = ?""",
                    (target.platform_id, target.project_id, target.folder_id, now, tm_id)
                )
            else:
                # Create new
                assign_id = -int(time.time() * 1000) % 1000000000
                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('tm_assignments')}
                           (id, server_id, tm_id, server_tm_id, platform_id, project_id, folder_id,
                            is_active, assigned_at, downloaded_at, sync_status)
                           VALUES (?, 0, ?, 0, ?, ?, ?, 0, ?, datetime('now'), 'local')""",
                        (assign_id, tm_id, target.platform_id, target.project_id, target.folder_id, now)
                    )
                else:
                    await conn.execute(
                        f"""INSERT INTO {self._table('tm_assignments')}
                           (id, tm_id, platform_id, project_id, folder_id, is_active, assigned_at)
                           VALUES (?, ?, ?, ?, ?, 0, ?)""",
                        (assign_id, tm_id, target.platform_id, target.project_id, target.folder_id, now)
                    )

            await conn.commit()

        scope = "unassigned"
        if target.folder_id:
            scope = "folder"
        elif target.project_id:
            scope = "project"
        elif target.platform_id:
            scope = "platform"

        logger.info(f"Assigned local TM {tm_id} to {scope}")
        return await self.get(tm_id)

    async def unassign(self, tm_id: int) -> Dict[str, Any]:
        """Unassign TM in SQLite."""
        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"""UPDATE {self._table('tm_assignments')}
                   SET platform_id = NULL, project_id = NULL, folder_id = NULL, is_active = 0
                   WHERE tm_id = ?""",
                (tm_id,)
            )
            await conn.commit()
        return await self.get(tm_id)

    async def activate(self, tm_id: int) -> Dict[str, Any]:
        """Activate TM in SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_assignments')} WHERE tm_id = ?",
                (tm_id,)
            )
            assignment = await cursor.fetchone()

            if not assignment:
                raise ValueError("TM must be assigned before activation")

            assignment = dict(assignment)
            if (assignment.get("platform_id") is None and
                assignment.get("project_id") is None and
                assignment.get("folder_id") is None):
                raise ValueError("TM must be assigned to a scope before activation")

            await conn.execute(
                f"""UPDATE {self._table('tm_assignments')}
                   SET is_active = 1, activated_at = datetime('now')
                   WHERE tm_id = ?""",
                (tm_id,)
            )
            await conn.commit()
            logger.info(f"Activated local TM {tm_id}")

        return await self.get(tm_id)

    async def deactivate(self, tm_id: int) -> Dict[str, Any]:
        """Deactivate TM in SQLite."""
        async with self.db._get_async_connection() as conn:
            await conn.execute(
                f"UPDATE {self._table('tm_assignments')} SET is_active = 0 WHERE tm_id = ?",
                (tm_id,)
            )
            await conn.commit()
            logger.info(f"Deactivated local TM {tm_id}")

        return await self.get(tm_id)

    async def get_assignment(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """Get TM assignment from SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_assignments')} WHERE tm_id = ?",
                (tm_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Scope Queries
    # =========================================================================

    async def get_for_scope(
        self,
        platform_id: Optional[int] = None,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """Get TMs for scope from SQLite."""
        async with self.db._get_async_connection() as conn:
            query = f"""
                SELECT t.*, a.is_active, a.platform_id as a_platform_id,
                       a.project_id as a_project_id, a.folder_id as a_folder_id
                FROM {self._table('tms')} t
                JOIN {self._table('tm_assignments')} a ON t.id = a.tm_id
                WHERE 1=1
            """
            params = []

            if folder_id is not None:
                query += " AND a.folder_id = ?"
                params.append(folder_id)
            elif project_id is not None:
                query += " AND a.project_id = ?"
                params.append(project_id)
            elif platform_id is not None:
                query += " AND a.platform_id = ?"
                params.append(platform_id)

            if not include_inactive:
                query += " AND a.is_active = 1"

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            return [
                {
                    **self._tm_row_to_dict(dict(row)),
                    "is_active": bool(row["is_active"]),
                    "platform_id": row["a_platform_id"],
                    "project_id": row["a_project_id"],
                    "folder_id": row["a_folder_id"],
                }
                for row in rows
            ]

    async def get_active_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        """Get active TMs for file scope chain."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT folder_id, project_id FROM {self._table('files')} WHERE id = ?",
                (file_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return []

            folder_id = row["folder_id"]
            project_id = row["project_id"]

        results = []

        # Folder-level TMs
        if folder_id:
            folder_tms = await self.get_for_scope(folder_id=folder_id)
            for tm in folder_tms:
                tm["scope"] = "folder"
                results.append(tm)

        # Project-level TMs
        if project_id:
            project_tms = await self.get_for_scope(project_id=project_id)
            for tm in project_tms:
                tm["scope"] = "project"
                results.append(tm)

        return results

    # =========================================================================
    # TM Linking (Active TMs for Projects)
    # =========================================================================

    async def link_to_project(
        self,
        tm_id: int,
        project_id: int,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Link a TM to a project for auto-add on confirm."""
        async with self.db._get_async_connection() as conn:
            # Check if already linked
            cursor = await conn.execute(
                f"""SELECT id FROM {self._table('tm_assignments')}
                   WHERE tm_id = ? AND project_id = ? AND is_active = 1""",
                [tm_id, project_id]
            )
            existing = await cursor.fetchone()

            if existing:
                # Update priority
                await conn.execute(
                    f"""UPDATE {self._table('tm_assignments')}
                       SET priority = ?
                       WHERE tm_id = ? AND project_id = ? AND is_active = 1""",
                    [priority, tm_id, project_id]
                )
                await conn.commit()
                return {"tm_id": tm_id, "project_id": project_id, "priority": priority, "created": False}

            # Create new assignment with is_active=1
            assign_id = -int(time.time() * 1000) % 1000000000
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('tm_assignments')}
                       (id, server_id, tm_id, server_tm_id, project_id, priority, is_active, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, 1, 'local')""",
                    [assign_id, tm_id, project_id, priority]
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('tm_assignments')}
                       (id, tm_id, project_id, priority, is_active)
                       VALUES (?, ?, ?, ?, 1)""",
                    [assign_id, tm_id, project_id, priority]
                )
            await conn.commit()

            logger.info(f"[TM-REPO-SQLITE] Linked TM {tm_id} to project {project_id}")
            return {"tm_id": tm_id, "project_id": project_id, "priority": priority, "created": True}

    async def unlink_from_project(self, tm_id: int, project_id: int) -> bool:
        """Unlink a TM from a project."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""UPDATE {self._table('tm_assignments')}
                   SET is_active = 0
                   WHERE tm_id = ? AND project_id = ? AND is_active = 1""",
                [tm_id, project_id]
            )
            await conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"[TM-REPO-SQLITE] Unlinked TM {tm_id} from project {project_id}")
                return True
            return False

    async def get_linked_for_project(
        self,
        project_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the highest-priority linked TM for a project."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT t.*
                   FROM {self._table('tms')} t
                   JOIN {self._table('tm_assignments')} a ON t.id = a.tm_id
                   WHERE a.project_id = ? AND a.is_active = 1
                   ORDER BY a.priority LIMIT 1""",
                [project_id]
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return self._tm_row_to_dict(dict(row))

    async def get_all_linked_for_project(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Get all TMs linked to a project, ordered by priority."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT t.*, a.priority, a.assigned_at as linked_at
                   FROM {self._table('tms')} t
                   JOIN {self._table('tm_assignments')} a ON t.id = a.tm_id
                   WHERE a.project_id = ? AND a.is_active = 1
                   ORDER BY a.priority""",
                [project_id]
            )
            rows = await cursor.fetchall()

            return [
                {
                    "tm_id": row["id"],
                    "tm_name": row["name"],
                    "priority": row["priority"],
                    "status": dict(row).get("status", "active"),
                    "entry_count": dict(row).get("entry_count", 0),
                    "linked_at": row["linked_at"]
                }
                for row in rows
            ]

    # =========================================================================
    # TM Entries
    # =========================================================================

    async def add_entry(
        self,
        tm_id: int,
        source: str,
        target: str,
        string_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add entry to TM in SQLite."""
        entry_id = -int(time.time() * 1000) % 1000000000
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('tm_entries')}
                       (id, server_id, tm_id, server_tm_id, source_text, target_text, source_hash,
                        string_id, created_by, change_date, is_confirmed, downloaded_at, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, ?, 0, datetime('now'), 'local')""",
                    (entry_id, tm_id, source, target, source_hash, string_id, created_by, now)
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('tm_entries')}
                       (id, tm_id, source_text, target_text, source_hash, string_id, created_by,
                        change_date, is_confirmed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (entry_id, tm_id, source, target, source_hash, string_id, created_by, now)
                )

            # Update entry count
            await conn.execute(
                f"UPDATE {self._table('tms')} SET entry_count = entry_count + 1 WHERE id = ?",
                (tm_id,)
            )
            await conn.commit()

        # Invalidate FAISS cache for this TM (entries changed)
        clear_tm_index_cache(tm_id)

        return {
            "id": entry_id,
            "tm_id": tm_id,
            "source_text": source,
            "target_text": target,
            "source_hash": source_hash,
            "string_id": string_id,
            "created_by": created_by,
            "change_date": now,
            "is_confirmed": False,
        }

    async def add_entries_bulk(
        self,
        tm_id: int,
        entries: List[Dict[str, Any]]
    ) -> int:
        """Bulk add entries to TM in SQLite using executemany."""
        if not entries:
            return 0

        async with self.db._get_async_connection() as conn:
            now = datetime.now().isoformat()

            for idx, e in enumerate(entries):
                entry_id = -int(time.time() * 1000 + idx) % 1000000000
                source = e.get("source") or e.get("source_text", "")
                target = e.get("target") or e.get("target_text", "")
                source_hash = hashlib.sha256(source.encode()).hexdigest()

                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('tm_entries')}
                           (id, server_id, tm_id, server_tm_id, source_text, target_text, source_hash,
                            string_id, change_date, is_confirmed, downloaded_at, sync_status)
                           VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, 0, datetime('now'), 'local')""",
                        (entry_id, tm_id, source, target, source_hash, e.get("string_id"), now)
                    )
                else:
                    await conn.execute(
                        f"""INSERT INTO {self._table('tm_entries')}
                           (id, tm_id, source_text, target_text, source_hash, string_id, change_date, is_confirmed)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                        (entry_id, tm_id, source, target, source_hash, e.get("string_id"), now)
                    )

            # Update entry count
            await conn.execute(
                f"UPDATE {self._table('tms')} SET entry_count = entry_count + ? WHERE id = ?",
                (len(entries), tm_id)
            )
            await conn.commit()

            # Invalidate FAISS cache for this TM (entries changed)
            clear_tm_index_cache(tm_id)

            logger.info(f"Bulk added {len(entries)} entries to SQLite TM {tm_id}")
            return len(entries)

    async def get_entries(
        self,
        tm_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get TM entries from SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_entries')} WHERE tm_id = ? LIMIT ? OFFSET ?",
                (tm_id, limit, offset)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_entries(self, tm_id: int) -> List[Dict[str, Any]]:
        """
        Get all TM entries from SQLite for building indexes.

        LIMIT-002: Used by TMLoader for offline pretranslation support.
        """
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT id, tm_id, source_text, target_text, source_hash,
                           string_id, is_confirmed
                   FROM {self._table('tm_entries')} WHERE tm_id = ? ORDER BY id""",
                (tm_id,)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "tm_id": row["tm_id"],
                    "source_text": row["source_text"],
                    "target_text": row["target_text"],
                    "source_hash": row["source_hash"],
                    "string_id": row.get("string_id"),
                    "is_confirmed": bool(row.get("is_confirmed", 0)),
                }
                for row in rows
            ]

    async def search_entries(
        self,
        tm_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search TM entries in SQLite."""
        query_lower = query.lower()
        search_pattern = f"%{query_lower}%"

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT * FROM {self._table('tm_entries')}
                   WHERE tm_id = ? AND LOWER(source_text) LIKE ?
                   LIMIT ?""",
                (tm_id, search_pattern, limit)
            )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                entry = dict(row)
                source = entry.get("source_text", "")
                entry["match_score"] = 100 if query_lower == source.lower() else 80
                results.append(entry)

            return results

    async def delete_entry(self, entry_id: int) -> bool:
        """Delete TM entry from SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT tm_id FROM {self._table('tm_entries')} WHERE id = ?",
                (entry_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            tm_id = row["tm_id"]

            await conn.execute(f"DELETE FROM {self._table('tm_entries')} WHERE id = ?", (entry_id,))

            # Update entry count
            await conn.execute(
                f"""UPDATE {self._table('tms')}
                   SET entry_count = CASE WHEN entry_count > 0 THEN entry_count - 1 ELSE 0 END
                   WHERE id = ?""",
                (tm_id,)
            )
            await conn.commit()

            # Invalidate FAISS cache for this TM (entries changed)
            clear_tm_index_cache(tm_id)
            return True

    async def update_entry(
        self,
        entry_id: int,
        source_text: Optional[str] = None,
        target_text: Optional[str] = None,
        string_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update TM entry in SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_entries')} WHERE id = ?",
                (entry_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            updates = []
            params = []

            if source_text is not None:
                updates.append("source_text = ?")
                params.append(source_text)
                updates.append("source_hash = ?")
                params.append(hashlib.sha256(source_text.encode()).hexdigest())

            if target_text is not None:
                updates.append("target_text = ?")
                params.append(target_text)

            if string_id is not None:
                updates.append("string_id = ?")
                params.append(string_id)

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())

            if updated_by:
                updates.append("updated_by = ?")
                params.append(updated_by)

            params.append(entry_id)

            await conn.execute(
                f"UPDATE {self._table('tm_entries')} SET {', '.join(updates)} WHERE id = ?",
                params
            )

            # Update TM timestamp
            tm_id = row["tm_id"]
            await conn.execute(
                f"UPDATE {self._table('tms')} SET updated_at = datetime('now') WHERE id = ?",
                (tm_id,)
            )
            await conn.commit()

            # Invalidate FAISS cache for this TM (entries changed)
            clear_tm_index_cache(tm_id)

            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_entries')} WHERE id = ?",
                (entry_id,)
            )
            updated_row = await cursor.fetchone()

            logger.info(f"Updated SQLite TM entry {entry_id} by {updated_by}")
            return dict(updated_row) if updated_row else None

    async def confirm_entry(
        self,
        entry_id: int,
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Confirm/unconfirm TM entry in SQLite."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_entries')} WHERE id = ?",
                (entry_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            if confirm:
                await conn.execute(
                    f"""UPDATE {self._table('tm_entries')}
                       SET is_confirmed = 1, confirmed_at = datetime('now'), confirmed_by = ?
                       WHERE id = ?""",
                    (confirmed_by, entry_id)
                )
            else:
                await conn.execute(
                    f"""UPDATE {self._table('tm_entries')}
                       SET is_confirmed = 0, confirmed_at = NULL, confirmed_by = NULL
                       WHERE id = ?""",
                    (entry_id,)
                )
            await conn.commit()

            cursor = await conn.execute(
                f"SELECT * FROM {self._table('tm_entries')} WHERE id = ?",
                (entry_id,)
            )
            updated_row = await cursor.fetchone()

            logger.info(f"{'Confirmed' if confirm else 'Unconfirmed'} SQLite TM entry {entry_id} by {confirmed_by}")
            return dict(updated_row) if updated_row else None

    async def bulk_confirm_entries(
        self,
        tm_id: int,
        entry_ids: List[int],
        confirm: bool = True,
        confirmed_by: Optional[str] = None
    ) -> int:
        """Bulk confirm/unconfirm in SQLite."""
        if not entry_ids:
            return 0

        async with self.db._get_async_connection() as conn:
            placeholders = ",".join("?" * len(entry_ids))

            if confirm:
                await conn.execute(
                    f"""UPDATE {self._table('tm_entries')}
                       SET is_confirmed = 1, confirmed_at = datetime('now'), confirmed_by = ?
                       WHERE tm_id = ? AND id IN ({placeholders})""",
                    [confirmed_by, tm_id] + entry_ids
                )
            else:
                await conn.execute(
                    f"""UPDATE {self._table('tm_entries')}
                       SET is_confirmed = 0, confirmed_at = NULL, confirmed_by = NULL
                       WHERE tm_id = ? AND id IN ({placeholders})""",
                    [tm_id] + entry_ids
                )
            await conn.commit()

            cursor = await conn.execute(
                f"SELECT COUNT(*) as cnt FROM {self._table('tm_entries')} WHERE tm_id = ? AND id IN ({placeholders})",
                [tm_id] + entry_ids
            )
            result = await cursor.fetchone()
            updated_count = result["cnt"] if result else 0

            logger.info(f"Bulk {'confirmed' if confirm else 'unconfirmed'} {updated_count} entries in SQLite TM {tm_id}")
            return updated_count

    async def get_glossary_terms(
        self,
        tm_ids: List[int],
        max_length: int = 20,
        limit: int = 1000
    ) -> List[tuple]:
        """Get short TM entries as glossary terms for QA checks."""
        if not tm_ids:
            return []

        async with self.db._get_async_connection() as conn:
            placeholders = ",".join("?" * len(tm_ids))
            cursor = await conn.execute(
                f"""SELECT source_text, target_text
                   FROM {self._table('tm_entries')}
                   WHERE tm_id IN ({placeholders})
                     AND LENGTH(source_text) <= ?
                     AND source_text IS NOT NULL
                     AND target_text IS NOT NULL
                   LIMIT ?""",
                tm_ids + [max_length, limit]
            )
            rows = await cursor.fetchall()
            return [(row["source_text"], row["target_text"]) for row in rows]

    # =========================================================================
    # Tree Structure
    # =========================================================================

    async def get_tree(self) -> Dict[str, Any]:
        """Get TM tree structure for UI with folder hierarchy."""
        all_tms = await self.get_all()

        def transform_tm(tm: Dict) -> Dict:
            return {
                "tm_id": tm.get("id"),
                "tm_name": tm.get("name"),
                "entry_count": tm.get("entry_count", 0),
                "is_active": tm.get("is_active", False),
                "platform_id": tm.get("platform_id"),
                "project_id": tm.get("project_id"),
                "folder_id": tm.get("folder_id"),
                "source_lang": tm.get("source_lang"),
                "target_lang": tm.get("target_lang"),
            }

        unassigned = []
        by_platform = {}
        by_project = {}
        by_folder = {}

        for tm in all_tms:
            transformed = transform_tm(tm)
            if tm.get("folder_id"):
                by_folder.setdefault(tm["folder_id"], []).append(transformed)
            elif tm.get("project_id"):
                by_project.setdefault(tm["project_id"], []).append(transformed)
            elif tm.get("platform_id"):
                by_platform.setdefault(tm["platform_id"], []).append(transformed)
            else:
                unassigned.append(transformed)

        def build_folder_tree(folders: list, parent_id) -> list:
            result = []
            for folder in folders:
                if folder["parent_id"] == parent_id:
                    folder_dict = {
                        "id": folder["id"],
                        "name": folder["name"],
                        "tms": by_folder.get(folder["id"], []),
                        "children": build_folder_tree(folders, folder["id"])
                    }
                    result.append(folder_dict)
            return result

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('platforms')} ORDER BY name"
            )
            platforms = await cursor.fetchall()

            tree_platforms = []
            for p in platforms:
                # Skip synced Offline Storage platforms
                if p["name"] == "Offline Storage" and p["id"] != -1:
                    continue

                platform_dict = {
                    "id": p["id"],
                    "name": p["name"],
                    "tms": by_platform.get(p["id"], []),
                    "projects": []
                }

                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('projects')} WHERE platform_id = ?",
                    (p["id"],)
                )
                projects = await cursor.fetchall()

                for proj in projects:
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('folders')} WHERE project_id = ?",
                        (proj["id"],)
                    )
                    folders = await cursor.fetchall()

                    folder_tree = build_folder_tree([dict(f) for f in folders], None)

                    project_dict = {
                        "id": proj["id"],
                        "name": proj["name"],
                        "tms": by_project.get(proj["id"], []),
                        "folders": folder_tree
                    }
                    platform_dict["projects"].append(project_dict)

                tree_platforms.append(platform_dict)

            return {
                "unassigned": unassigned,
                "platforms": tree_platforms
            }

    # =========================================================================
    # Index Operations (P10-REPO)
    # =========================================================================

    async def get_indexes(self, tm_id: int) -> List[Dict[str, Any]]:
        """Get index status for a TM - not applicable in SQLite."""
        return []

    async def count_entries(self, tm_id: int) -> int:
        """Count entries in a TM."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM {self._table('tm_entries')} WHERE tm_id = ?",
                (tm_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    # =========================================================================
    # Advanced Search (P10-REPO: PostgreSQL-specific - stubs for SQLite)
    # =========================================================================

    async def search_exact(
        self,
        tm_id: int,
        source: str
    ) -> Optional[Dict[str, Any]]:
        """Hash-based exact match search in SQLite."""
        source_hash = hashlib.sha256(source.encode()).hexdigest()

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT source_text, target_text FROM {self._table('tm_entries')}
                   WHERE tm_id = ? AND source_hash = ?""",
                (tm_id, source_hash)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "source_text": row["source_text"],
                    "target_text": row["target_text"],
                    "similarity": 1.0,
                    "tier": 1,
                    "strategy": "perfect_whole_match"
                }
            return None

    async def search_similar(
        self,
        tm_id: int,
        source: str,
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        FAISS-based semantic search for SQLite offline mode.

        LIMIT-001: Uses TMSearcher with pre-built FAISS indexes for offline TM suggestions.
        Thread-safe with LRU-style cache eviction.
        """
        global _tm_index_cache

        if not source or not source.strip():
            return []

        try:
            # Check if indexes exist
            data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "ldm_tm"
            tm_path = data_dir / str(tm_id)

            if not tm_path.exists():
                logger.info(f"[TM-REPO-SQLITE] No FAISS index for TM {tm_id} (index not built)")
                return []

            # Load indexes (thread-safe cached for performance)
            with _tm_index_cache_lock:
                cache_hit = tm_id in _tm_index_cache
                if cache_hit:
                    indexes = _tm_index_cache[tm_id]

            if not cache_hit:
                def _load_indexes():
                    from server.tools.ldm.indexing.indexer import TMIndexer
                    # Create indexer for loading only
                    indexer = TMIndexer.__new__(TMIndexer)
                    indexer.data_dir = data_dir
                    indexer._engine = None
                    return indexer.load_indexes(tm_id)

                indexes = await asyncio.to_thread(_load_indexes)

                # Thread-safe cache update with LRU eviction
                with _tm_index_cache_lock:
                    # Evict oldest if cache full
                    if len(_tm_index_cache) >= _TM_INDEX_CACHE_MAX_SIZE:
                        oldest_key = next(iter(_tm_index_cache))
                        del _tm_index_cache[oldest_key]
                        logger.debug(f"[TM-REPO-SQLITE] Cache evicted TM {oldest_key}")

                    _tm_index_cache[tm_id] = indexes
                    logger.info(f"[TM-REPO-SQLITE] Cached FAISS indexes for TM {tm_id}")

            # Search using TMSearcher
            def _search():
                from server.tools.ldm.indexing.searcher import TMSearcher
                searcher = TMSearcher(indexes, threshold=threshold)
                return searcher.search(source, top_k=max_results, threshold=threshold)

            result = await asyncio.to_thread(_search)

            # Transform to PostgreSQL-compatible format
            suggestions = []
            for match in result.get("results", []):
                suggestions.append({
                    "source": match.get("source_text") or match.get("source_line", ""),
                    "target": match.get("target_text") or match.get("target_line", ""),
                    "similarity": round(float(match.get("score", 0)), 3),
                    "entry_id": match.get("entry_id"),
                    "tm_id": tm_id,
                    "file_name": "TM",
                })

            return suggestions[:max_results]

        except FileNotFoundError:
            logger.info(f"[TM-REPO-SQLITE] Index files not found for TM {tm_id}")
            return []
        except ImportError as e:
            logger.warning(f"[TM-REPO-SQLITE] FAISS unavailable: {e}")
            return []
        except Exception as e:
            logger.error(f"[TM-REPO-SQLITE] FAISS search failed: {e}")
            return []
