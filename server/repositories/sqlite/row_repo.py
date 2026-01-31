"""
SQLite Row Repository.

Implements RowRepository interface using SQLite (offline mode).

ARCH-001: Schema-aware - works with both OFFLINE (offline_rows) and SERVER (ldm_rows) modes.
ASYNC MIGRATION (2026-01-31): Uses aiosqlite for true async operations.
"""

import time
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from server.repositories.interfaces.row_repository import RowRepository
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode


class SQLiteRowRepository(SQLiteBaseRepository, RowRepository):
    """
    SQLite implementation of RowRepository.

    ARCH-001: Schema-aware - uses _table() for dynamic table names.
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    def _normalize_row(self, row: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Normalize row dict to match PostgreSQL format."""
        if not row:
            return None

        result = {
            "id": row.get("id"),
            "file_id": row.get("file_id"),
            "row_num": row.get("row_num", 0),
            "string_id": row.get("string_id"),
            "source": row.get("source"),
            "target": row.get("target"),
            "status": row.get("status", "pending"),
            "qa_flag_count": row.get("qa_flag_count", 0),
            "extra_data": row.get("extra_data"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "updated_by": row.get("updated_by"),
        }

        # Only include sync_status for OFFLINE mode
        if self._has_column("sync_status"):
            result["sync_status"] = row.get("sync_status")

        # Parse extra_data if it's a string
        if isinstance(result["extra_data"], str):
            try:
                result["extra_data"] = json.loads(result["extra_data"])
            except (json.JSONDecodeError, TypeError):
                pass

        return result

    # =========================================================================
    # Core CRUD
    # =========================================================================

    async def get(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row by ID."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('rows')} WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()
            return self._normalize_row(dict(row)) if row else None

    async def get_with_file(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row with file info."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"""SELECT r.*, f.name as file_name, f.project_id
                   FROM {self._table('rows')} r
                   JOIN {self._table('files')} f ON r.file_id = f.id
                   WHERE r.id = ?""",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            result = self._normalize_row(dict(row))
            result["file_name"] = row["file_name"]
            result["project_id"] = row["project_id"]
            return result

    async def create(
        self,
        file_id: int,
        row_num: int,
        source: str,
        target: str = "",
        string_id: Optional[str] = None,
        status: str = "pending",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a single row."""
        row_id = -int(time.time() * 1000) % 1000000000
        extra_json = json.dumps(extra_data) if extra_data else None
        now = datetime.now().isoformat()

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                await conn.execute(
                    f"""INSERT INTO {self._table('rows')}
                       (id, server_id, file_id, server_file_id, row_num, string_id,
                        source, target, memo, status, extra_data, created_at, updated_at,
                        downloaded_at, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, ?, ?, '', ?, ?, ?, ?, datetime('now'), 'new')""",
                    (row_id, file_id, row_num, string_id, source, target, status, extra_json, now, now)
                )
            else:
                await conn.execute(
                    f"""INSERT INTO {self._table('rows')}
                       (id, file_id, row_num, string_id, source, target, memo, status,
                        extra_data, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?)""",
                    (row_id, file_id, row_num, string_id, source, target, status, extra_json, now, now)
                )

            # Update file row count
            await conn.execute(
                f"UPDATE {self._table('files')} SET row_count = row_count + 1 WHERE id = ?",
                (file_id,)
            )
            await conn.commit()

            logger.info(f"Created row: id={row_id}, file_id={file_id}, row_num={row_num}")

        return await self.get(row_id)

    async def update(
        self,
        row_id: int,
        target: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a row's target text or status."""
        async with self.db._get_async_connection() as conn:
            # Check if row exists
            cursor = await conn.execute(
                f"SELECT * FROM {self._table('rows')} WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            # Build update
            updates = ["updated_at = datetime('now')"]
            params = []

            if target is not None:
                updates.append("target = ?")
                params.append(target)

            if status is not None:
                updates.append("status = ?")
                params.append(status)
            elif target is not None and row["status"] == "pending" and target:
                # Auto-set status to translated if target is set and was pending
                updates.append("status = ?")
                params.append("translated")

            # For OFFLINE mode with synced files, mark as modified
            if self.schema_mode == SchemaMode.OFFLINE:
                # Check file sync status
                file_cursor = await conn.execute(
                    f"SELECT sync_status FROM {self._table('files')} WHERE id = ?",
                    (row["file_id"],)
                )
                file_row = await file_cursor.fetchone()
                if file_row and file_row["sync_status"] != "local":
                    updates.append("sync_status = 'modified'")

            params.append(row_id)

            await conn.execute(
                f"UPDATE {self._table('rows')} SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await conn.commit()

            logger.info(f"Updated row: id={row_id}, target_changed={target is not None}, status_changed={status is not None}")

        return await self.get(row_id)

    async def delete(self, row_id: int) -> bool:
        """Delete a row."""
        async with self.db._get_async_connection() as conn:
            # Get file_id before deleting
            cursor = await conn.execute(
                f"SELECT file_id FROM {self._table('rows')} WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            file_id = row["file_id"]

            # Delete the row
            await conn.execute(f"DELETE FROM {self._table('rows')} WHERE id = ?", (row_id,))

            # Update file row count
            await conn.execute(
                f"UPDATE {self._table('files')} SET row_count = row_count - 1 WHERE id = ? AND row_count > 0",
                (file_id,)
            )
            await conn.commit()

            logger.info(f"Deleted row: id={row_id}")
            return True

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """Bulk create rows for a file."""
        if not rows:
            return 0

        now = datetime.now().isoformat()
        async with self.db._get_async_connection() as conn:
            for idx, row_data in enumerate(rows):
                row_id = -int(time.time() * 1000 + idx) % 1000000000
                extra_json = json.dumps(row_data.get("extra_data")) if row_data.get("extra_data") else None

                if self.schema_mode == SchemaMode.OFFLINE:
                    await conn.execute(
                        f"""INSERT INTO {self._table('rows')}
                           (id, server_id, file_id, server_file_id, row_num, string_id,
                            source, target, memo, status, extra_data, created_at, updated_at,
                            downloaded_at, sync_status)
                           VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                        (
                            row_id,
                            file_id,
                            row_data.get("row_num", idx + 1),
                            row_data.get("string_id"),
                            row_data.get("source", ""),
                            row_data.get("target", ""),
                            row_data.get("memo", ""),
                            row_data.get("status", "pending"),
                            extra_json,
                            now,
                            now,
                        )
                    )
                else:
                    await conn.execute(
                        f"""INSERT INTO {self._table('rows')}
                           (id, file_id, row_num, string_id, source, target, memo,
                            status, extra_data, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            row_id,
                            file_id,
                            row_data.get("row_num", idx + 1),
                            row_data.get("string_id"),
                            row_data.get("source", ""),
                            row_data.get("target", ""),
                            row_data.get("memo", ""),
                            row_data.get("status", "pending"),
                            extra_json,
                            now,
                            now,
                        )
                    )

            # Update file row count
            await conn.execute(
                f"UPDATE {self._table('files')} SET row_count = ? WHERE id = ?",
                (len(rows), file_id)
            )
            await conn.commit()

        logger.info(f"Bulk created {len(rows)} rows for file_id={file_id}")
        return len(rows)

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update multiple rows."""
        count = 0
        async with self.db._get_async_connection() as conn:
            for update in updates:
                row_id = update.get("id")
                if not row_id:
                    continue

                # Build update
                update_parts = ["updated_at = datetime('now')"]
                params = []

                if "target" in update:
                    update_parts.append("target = ?")
                    params.append(update["target"])
                if "status" in update:
                    update_parts.append("status = ?")
                    params.append(update["status"])

                if len(update_parts) == 1:
                    continue  # Nothing to update besides timestamp

                params.append(row_id)

                cursor = await conn.execute(
                    f"UPDATE {self._table('rows')} SET {', '.join(update_parts)} WHERE id = ?",
                    params
                )
                if cursor.rowcount > 0:
                    count += 1

            await conn.commit()

        logger.info(f"Bulk updated {count} rows")
        return count

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_for_file(
        self,
        file_id: int,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        search_mode: str = "contain",
        search_fields: str = "source,target",
        status: Optional[str] = None,
        filter_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated rows for a file with search/filter."""
        offset = (page - 1) * limit

        async with self.db._get_async_connection() as conn:
            # Build base query
            base_query = f"FROM {self._table('rows')} WHERE file_id = ?"
            params = [file_id]

            # Apply status filter
            if status:
                base_query += " AND status = ?"
                params.append(status)

            # Apply filter type
            if filter_type:
                if filter_type == "confirmed":
                    base_query += " AND status IN ('approved', 'reviewed')"
                elif filter_type == "unconfirmed":
                    base_query += " AND status IN ('pending', 'translated')"
                elif filter_type == "qa_flagged":
                    base_query += " AND qa_flag_count > 0"

            # Apply search - SQLite LIKE for now (no pg_trgm)
            if search:
                fields = [f.strip() for f in search_fields.split(",")]
                valid_fields = {"string_id", "source", "target"}
                fields = [f for f in fields if f in valid_fields]
                if not fields:
                    fields = ["source", "target"]

                search_conditions = []
                for field in fields:
                    if search_mode == "exact":
                        search_conditions.append(f"LOWER({field}) = LOWER(?)")
                        params.append(search)
                    elif search_mode == "not_contain":
                        search_conditions.append(f"LOWER({field}) NOT LIKE LOWER(?)")
                        params.append(f"%{search}%")
                    else:  # contain (default)
                        search_conditions.append(f"LOWER({field}) LIKE LOWER(?)")
                        params.append(f"%{search}%")

                if search_mode == "not_contain":
                    base_query += f" AND ({' AND '.join(search_conditions)})"
                else:
                    base_query += f" AND ({' OR '.join(search_conditions)})"

            # Get total count
            count_cursor = await conn.execute(f"SELECT COUNT(*) as cnt {base_query}", params)
            count_result = await count_cursor.fetchone()
            total = count_result["cnt"] if count_result else 0

            # Get paginated rows
            query = f"SELECT * {base_query} ORDER BY row_num LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

        return [self._normalize_row(dict(r)) for r in rows], total

    async def get_all_for_file(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all rows for a file (no pagination)."""
        async with self.db._get_async_connection() as conn:
            if status_filter:
                if status_filter == "reviewed":
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('rows')} WHERE file_id = ? AND status IN ('reviewed', 'approved') ORDER BY row_num",
                        (file_id,)
                    )
                elif status_filter == "translated":
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('rows')} WHERE file_id = ? AND status IN ('translated', 'reviewed', 'approved') ORDER BY row_num",
                        (file_id,)
                    )
                else:
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('rows')} WHERE file_id = ? AND status = ? ORDER BY row_num",
                        (file_id, status_filter)
                    )
            else:
                cursor = await conn.execute(
                    f"SELECT * FROM {self._table('rows')} WHERE file_id = ? ORDER BY row_num",
                    (file_id,)
                )

            rows = await cursor.fetchall()
            return [self._normalize_row(dict(r)) for r in rows]

    async def count_for_file(self, file_id: int) -> int:
        """Count rows in a file."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) as cnt FROM {self._table('rows')} WHERE file_id = ?",
                (file_id,)
            )
            result = await cursor.fetchone()
            return result["cnt"] if result else 0

    # =========================================================================
    # History Operations
    # =========================================================================

    async def add_edit_history(
        self,
        row_id: int,
        user_id: int,
        old_target: Optional[str],
        new_target: Optional[str],
        old_status: Optional[str],
        new_status: Optional[str]
    ) -> None:
        """Record edit history for a row.

        Note: Edit history is not fully supported in offline mode.
        Changes are tracked via local_changes table for sync purposes.
        """
        # Offline mode uses local_changes table for tracking
        # Full edit history is only available in online mode
        pass

    async def get_edit_history(
        self,
        row_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get edit history for a row.

        Note: Edit history is not available in offline mode.
        Returns empty list.
        """
        # Edit history is only available in online mode
        return []

    # =========================================================================
    # Similarity Search (P10-REPO: PostgreSQL-specific - stub for SQLite)
    # =========================================================================

    async def suggest_similar(
        self,
        source: str,
        file_id: Optional[int] = None,
        project_id: Optional[int] = None,
        exclude_row_id: Optional[int] = None,
        threshold: float = 0.5,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Similarity search - not available in SQLite (pg_trgm is PostgreSQL-specific).
        Returns empty list for offline mode.
        """
        logger.debug(f"[ROW-REPO] Similarity search not available in SQLite")
        return []
