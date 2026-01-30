"""
SQLite Row Repository.

Implements RowRepository interface using SQLite (offline mode).
Delegates to existing OfflineDatabase methods.

ASYNC MIGRATION (2026-01-31): Uses aiosqlite for true async operations.
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from server.repositories.interfaces.row_repository import RowRepository
from server.database.offline import get_offline_db


class SQLiteRowRepository(RowRepository):
    """
    SQLite implementation of RowRepository.

    Uses OfflineDatabase for all operations.
    This is the offline mode adapter.
    """

    def __init__(self):
        self.db = get_offline_db()

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
            # SQLite-specific fields
            "sync_status": row.get("sync_status"),
        }

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
        row = await self.db.get_row(row_id)
        return self._normalize_row(row)

    async def get_with_file(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get row with file info."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT r.*, f.name as file_name, f.project_id
                   FROM offline_rows r
                   JOIN offline_files f ON r.file_id = f.id
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
        import time
        from datetime import datetime

        async with self.db._get_async_connection() as conn:
            # Use negative row IDs for local rows
            row_id = -int(time.time() * 1000) % 1000000000

            extra_json = json.dumps(extra_data) if extra_data else None
            now = datetime.now().isoformat()

            await conn.execute(
                """INSERT INTO offline_rows
                   (id, server_id, file_id, server_file_id, row_num, string_id,
                    source, target, memo, status, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, 0, ?, 0, ?, ?, ?, ?, '', ?, ?, ?, ?, datetime('now'), 'new')""",
                (
                    row_id,
                    file_id,
                    row_num,
                    string_id,
                    source,
                    target,
                    status,
                    extra_json,
                    now,
                    now,
                )
            )

            # Update file row count
            await conn.execute(
                "UPDATE offline_files SET row_count = row_count + 1 WHERE id = ?",
                (file_id,)
            )
            await conn.commit()

            logger.info(f"Created row: id={row_id}, file_id={file_id}, row_num={row_num}")

        # Return created row
        row = await self.db.get_row(row_id)
        return self._normalize_row(row)

    async def update(
        self,
        row_id: int,
        target: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a row's target text or status."""
        async with self.db._get_async_connection() as conn:
            # Check if row exists and get file sync status
            cursor = await conn.execute(
                """SELECT r.*, f.sync_status as file_sync_status
                   FROM offline_rows r
                   JOIN offline_files f ON r.file_id = f.id
                   WHERE r.id = ?""",
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

            # For synced files, mark as modified; for local files, keep as-is
            if row["file_sync_status"] != "local":
                updates.append("sync_status = 'modified'")

            params.append(row_id)

            await conn.execute(
                f"UPDATE offline_rows SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await conn.commit()

            logger.info(f"Updated row: id={row_id}, target_changed={target is not None}, status_changed={status is not None}")

        # Return updated row
        updated_row = await self.db.get_row(row_id)
        return self._normalize_row(updated_row)

    async def delete(self, row_id: int) -> bool:
        """Delete a row."""
        async with self.db._get_async_connection() as conn:
            # Get file_id before deleting
            cursor = await conn.execute(
                "SELECT file_id FROM offline_rows WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            file_id = row["file_id"]

            # Delete the row
            await conn.execute("DELETE FROM offline_rows WHERE id = ?", (row_id,))

            # Update file row count
            await conn.execute(
                "UPDATE offline_files SET row_count = row_count - 1 WHERE id = ? AND row_count > 0",
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
        # Use existing method
        await self.db.add_rows_to_local_file(file_id, rows)
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
                    f"UPDATE offline_rows SET {', '.join(update_parts)} WHERE id = ?",
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

        # Get all rows first
        all_rows = await self.db.get_rows_for_file(file_id)

        # Apply search filter
        if search:
            fields = [f.strip() for f in search_fields.split(",")]
            valid_fields = {"string_id", "source", "target"}
            fields = [f for f in fields if f in valid_fields]
            if not fields:
                fields = ["source", "target"]

            filtered_rows = []
            search_lower = search.lower()

            for row in all_rows:
                match = False
                for field in fields:
                    value = row.get(field, "") or ""
                    value_lower = value.lower()

                    if search_mode == "exact":
                        if value_lower == search_lower:
                            match = True
                            break
                    elif search_mode == "not_contain":
                        if search_lower not in value_lower:
                            match = True
                        else:
                            match = False
                            break
                    else:  # contain (default)
                        if search_lower in value_lower:
                            match = True
                            break

                # For not_contain, all fields must not contain
                if search_mode == "not_contain":
                    if match:
                        filtered_rows.append(row)
                elif match:
                    filtered_rows.append(row)

            all_rows = filtered_rows

        # Apply status filter
        if status:
            all_rows = [r for r in all_rows if r.get("status") == status]

        # Apply filter type
        if filter_type:
            if filter_type == "confirmed":
                all_rows = [r for r in all_rows if r.get("status") in ["approved", "reviewed"]]
            elif filter_type == "unconfirmed":
                all_rows = [r for r in all_rows if r.get("status") in ["pending", "translated"]]
            elif filter_type == "qa_flagged":
                all_rows = [r for r in all_rows if (r.get("qa_flag_count") or 0) > 0]

        # Get total count before pagination
        total = len(all_rows)

        # Apply pagination
        paginated_rows = all_rows[offset:offset + limit]

        return [self._normalize_row(r) for r in paginated_rows], total

    async def get_all_for_file(
        self,
        file_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all rows for a file (no pagination)."""
        rows = await self.db.get_rows_for_file(file_id)

        if status_filter:
            if status_filter == "reviewed":
                rows = [r for r in rows if r.get("status") in ["reviewed", "approved"]]
            elif status_filter == "translated":
                rows = [r for r in rows if r.get("status") in ["translated", "reviewed", "approved"]]
            else:
                rows = [r for r in rows if r.get("status") == status_filter]

        return [self._normalize_row(r) for r in rows]

    async def count_for_file(self, file_id: int) -> int:
        """Count rows in a file."""
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) as cnt FROM offline_rows WHERE file_id = ?",
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
