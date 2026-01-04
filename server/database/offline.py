"""
P3 Offline/Online Mode - SQLite Database Manager

Handles local SQLite database for offline storage.
Provides methods for downloading, storing, and retrieving offline data.
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


class OfflineDatabase:
    """Manager for local SQLite offline storage."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize offline database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default: user's app data directory
            app_data = self._get_app_data_dir()
            db_path = os.path.join(app_data, "offline.db")

        self.db_path = db_path
        self._ensure_directory()
        self._init_schema()

    def _get_app_data_dir(self) -> str:
        """Get platform-specific app data directory."""
        import platform
        system = platform.system()

        if system == "Windows":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            return os.path.join(base, "LocaNext")
        elif system == "Darwin":  # macOS
            return os.path.expanduser("~/Library/Application Support/LocaNext")
        else:  # Linux
            return os.path.expanduser("~/.local/share/locanext")

    def _ensure_directory(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self):
        """Initialize database schema if needed."""
        schema_path = Path(__file__).parent / "offline_schema.sql"

        if not schema_path.exists():
            logger.error(f"Offline schema not found: {schema_path}")
            return

        with open(schema_path, "r") as f:
            schema_sql = f.read()

        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
            logger.debug(f"Offline database initialized: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Sync Metadata
    # =========================================================================

    def get_meta(self, key: str) -> Optional[str]:
        """Get sync metadata value."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM sync_meta WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set_meta(self, key: str, value: str):
        """Set sync metadata value."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))""",
                (key, value)
            )
            conn.commit()

    def get_last_sync(self) -> Optional[str]:
        """Get last sync timestamp."""
        return self.get_meta("last_sync")

    def set_last_sync(self):
        """Update last sync timestamp to now."""
        self.set_meta("last_sync", datetime.utcnow().isoformat())

    # =========================================================================
    # Platform Operations
    # =========================================================================

    def save_platform(self, platform: Dict[str, Any]) -> int:
        """Save a platform to offline storage."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO offline_platforms
                   (id, server_id, name, description, owner_id, is_restricted,
                    created_at, updated_at, downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                (
                    platform["id"],
                    platform["id"],  # server_id same as id on download
                    platform["name"],
                    platform.get("description"),
                    platform.get("owner_id"),
                    1 if platform.get("is_restricted") else 0,
                    platform.get("created_at"),
                    platform.get("updated_at"),
                )
            )
            conn.commit()
            return platform["id"]

    def get_platforms(self) -> List[Dict]:
        """Get all offline platforms."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_platforms ORDER BY name"
            ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Project Operations
    # =========================================================================

    def save_project(self, project: Dict[str, Any]) -> int:
        """Save a project to offline storage."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO offline_projects
                   (id, server_id, name, description, platform_id, server_platform_id,
                    owner_id, is_restricted, created_at, updated_at, downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                (
                    project["id"],
                    project["id"],
                    project["name"],
                    project.get("description"),
                    project.get("platform_id"),
                    project.get("platform_id"),
                    project.get("owner_id"),
                    1 if project.get("is_restricted") else 0,
                    project.get("created_at"),
                    project.get("updated_at"),
                )
            )
            conn.commit()
            return project["id"]

    def get_projects(self, platform_id: Optional[int] = None) -> List[Dict]:
        """Get offline projects, optionally filtered by platform."""
        with self._get_connection() as conn:
            if platform_id:
                rows = conn.execute(
                    "SELECT * FROM offline_projects WHERE platform_id = ? ORDER BY name",
                    (platform_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM offline_projects ORDER BY name"
                ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Folder Operations
    # =========================================================================

    def save_folder(self, folder: Dict[str, Any]) -> int:
        """Save a folder to offline storage."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO offline_folders
                   (id, server_id, name, project_id, server_project_id,
                    parent_id, server_parent_id, created_at, downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                (
                    folder["id"],
                    folder["id"],
                    folder["name"],
                    folder["project_id"],
                    folder["project_id"],
                    folder.get("parent_id"),
                    folder.get("parent_id"),
                    folder.get("created_at"),
                )
            )
            conn.commit()
            return folder["id"]

    def get_folders(self, project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
        """Get folders in a project, optionally filtered by parent."""
        with self._get_connection() as conn:
            if parent_id is None:
                rows = conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id IS NULL ORDER BY name""",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id = ? ORDER BY name""",
                    (project_id, parent_id)
                ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # File Operations
    # =========================================================================

    def save_file(self, file: Dict[str, Any]) -> int:
        """Save a file to offline storage."""
        extra_data = json.dumps(file.get("extra_data")) if file.get("extra_data") else None

        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO offline_files
                   (id, server_id, name, original_filename, format, row_count,
                    source_language, target_language, project_id, server_project_id,
                    folder_id, server_folder_id, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                (
                    file["id"],
                    file["id"],
                    file["name"],
                    file.get("original_filename", file["name"]),
                    file.get("format", "txt"),
                    file.get("row_count", 0),
                    file.get("source_language", "ko"),
                    file.get("target_language"),
                    file["project_id"],
                    file["project_id"],
                    file.get("folder_id"),
                    file.get("folder_id"),
                    extra_data,
                    file.get("created_at"),
                    file.get("updated_at"),
                )
            )
            conn.commit()
            return file["id"]

    def get_files(self, project_id: int, folder_id: Optional[int] = None) -> List[Dict]:
        """Get files in a project, optionally filtered by folder."""
        with self._get_connection() as conn:
            if folder_id is None:
                rows = conn.execute(
                    """SELECT * FROM offline_files
                       WHERE project_id = ? AND folder_id IS NULL ORDER BY name""",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM offline_files
                       WHERE project_id = ? AND folder_id = ? ORDER BY name""",
                    (project_id, folder_id)
                ).fetchall()
            return [dict(row) for row in rows]

    def get_file(self, file_id: int) -> Optional[Dict]:
        """Get a single file by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM offline_files WHERE id = ?", (file_id,)
            ).fetchone()
            return dict(row) if row else None

    def is_file_downloaded(self, server_file_id: int) -> bool:
        """Check if a file is already downloaded."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM offline_files WHERE server_id = ?",
                (server_file_id,)
            ).fetchone()
            return row is not None

    # =========================================================================
    # Row Operations
    # =========================================================================

    def save_rows(self, file_id: int, rows: List[Dict[str, Any]]):
        """Save multiple rows to offline storage (bulk insert)."""
        with self._get_connection() as conn:
            # Delete existing rows for this file first
            conn.execute("DELETE FROM offline_rows WHERE file_id = ?", (file_id,))

            # Insert new rows
            for row in rows:
                extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
                conn.execute(
                    """INSERT INTO offline_rows
                       (id, server_id, file_id, server_file_id, row_num, string_id,
                        source, target, memo, status, extra_data, created_at, updated_at,
                        downloaded_at, sync_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                    (
                        row["id"],
                        row["id"],
                        file_id,
                        file_id,
                        row.get("row_num", 0),
                        row.get("string_id"),
                        row.get("source"),
                        row.get("target"),
                        row.get("memo"),
                        row.get("status", "normal"),
                        extra_data,
                        row.get("created_at"),
                        row.get("updated_at"),
                    )
                )
            conn.commit()
            logger.debug(f"Saved {len(rows)} rows for file {file_id}")

    def get_rows(self, file_id: int) -> List[Dict]:
        """Get all rows for a file."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_rows WHERE file_id = ? ORDER BY row_num",
                (file_id,)
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    def update_row(self, row_id: int, field: str, value: Any) -> bool:
        """Update a single row field and track the change."""
        allowed_fields = {"target", "memo", "status"}
        if field not in allowed_fields:
            logger.warning(f"Cannot update field '{field}' - not editable")
            return False

        with self._get_connection() as conn:
            # Get current value
            row = conn.execute(
                f"SELECT {field}, server_id FROM offline_rows WHERE id = ?",
                (row_id,)
            ).fetchone()

            if not row:
                return False

            old_value = row[field]

            # Update the row
            conn.execute(
                f"""UPDATE offline_rows
                    SET {field} = ?, sync_status = 'modified', updated_at = datetime('now')
                    WHERE id = ?""",
                (value, row_id)
            )

            # Track the change
            conn.execute(
                """INSERT INTO local_changes
                   (entity_type, entity_id, server_id, change_type, field_name, old_value, new_value)
                   VALUES ('row', ?, ?, 'edit', ?, ?, ?)""",
                (row_id, row["server_id"], field, str(old_value), str(value))
            )

            conn.commit()
            return True

    # =========================================================================
    # Merge Operations (P3: Last-write-wins sync)
    # =========================================================================

    def get_row_by_server_id(self, server_id: int) -> Optional[Dict]:
        """Get a local row by its server ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM offline_rows WHERE server_id = ?",
                (server_id,)
            ).fetchone()
            if row:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                return d
            return None

    def get_modified_rows(self, file_id: int) -> List[Dict]:
        """Get all locally modified rows for a file."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM offline_rows
                   WHERE file_id = ? AND sync_status = 'modified'
                   ORDER BY row_num""",
                (file_id,)
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    def get_new_rows(self, file_id: int) -> List[Dict]:
        """Get all locally created rows for a file."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM offline_rows
                   WHERE file_id = ? AND sync_status = 'new'
                   ORDER BY row_num""",
                (file_id,)
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    def merge_row(self, server_row: Dict, file_id: int) -> str:
        """
        Merge a server row with local data using last-write-wins.

        Returns: 'updated', 'skipped', 'inserted'
        """
        local_row = self.get_row_by_server_id(server_row["id"])

        if local_row is None:
            # New row from server - insert it
            self._insert_row(server_row, file_id)
            return 'inserted'

        # Row exists locally
        if local_row["sync_status"] == 'synced':
            # No local changes - take server version
            self._update_row_from_server(server_row, local_row["id"])
            return 'updated'

        elif local_row["sync_status"] in ('modified', 'new'):
            # Local has changes - compare timestamps
            server_updated = server_row.get("updated_at") or ""
            local_updated = local_row.get("updated_at") or ""

            if server_updated > local_updated:
                # Server is newer - server wins, discard local changes
                self._update_row_from_server(server_row, local_row["id"])
                self._discard_local_changes(local_row["id"])
                logger.debug(f"Server wins for row {server_row['id']} (server: {server_updated} > local: {local_updated})")
                return 'updated'
            else:
                # Local is newer - keep local, will push later
                logger.debug(f"Local wins for row {server_row['id']} (local: {local_updated} >= server: {server_updated})")
                return 'skipped'

        return 'skipped'

    def _insert_row(self, row: Dict, file_id: int):
        """Insert a new row from server."""
        extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO offline_rows
                   (id, server_id, file_id, server_file_id, row_num, string_id,
                    source, target, memo, status, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                (
                    row["id"],
                    row["id"],
                    file_id,
                    file_id,
                    row.get("row_num", 0),
                    row.get("string_id"),
                    row.get("source"),
                    row.get("target"),
                    row.get("memo"),
                    row.get("status", "normal"),
                    extra_data,
                    row.get("created_at"),
                    row.get("updated_at"),
                )
            )
            conn.commit()

    def _update_row_from_server(self, server_row: Dict, local_id: int):
        """Update local row with server data."""
        extra_data = json.dumps(server_row.get("extra_data")) if server_row.get("extra_data") else None
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE offline_rows SET
                   source = ?, target = ?, memo = ?, status = ?,
                   extra_data = ?, updated_at = ?, sync_status = 'synced',
                   downloaded_at = datetime('now')
                   WHERE id = ?""",
                (
                    server_row.get("source"),
                    server_row.get("target"),
                    server_row.get("memo"),
                    server_row.get("status", "normal"),
                    extra_data,
                    server_row.get("updated_at"),
                    local_id,
                )
            )
            conn.commit()

    def _discard_local_changes(self, local_row_id: int):
        """Discard pending local changes for a row (server won)."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'discarded'
                   WHERE entity_type = 'row' AND entity_id = ? AND sync_status = 'pending'""",
                (local_row_id,)
            )
            conn.commit()

    def mark_row_synced(self, row_id: int):
        """Mark a row as synced after pushing to server."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE offline_rows
                   SET sync_status = 'synced'
                   WHERE id = ?""",
                (row_id,)
            )
            conn.commit()

    def delete_row(self, server_id: int):
        """Delete a local row (server deleted it)."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM offline_rows WHERE server_id = ?",
                (server_id,)
            )
            # Also discard any pending changes
            conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'discarded'
                   WHERE entity_type = 'row' AND server_id = ? AND sync_status = 'pending'""",
                (server_id,)
            )
            conn.commit()

    def get_local_row_server_ids(self, file_id: int) -> set:
        """Get set of server IDs for all local rows in a file."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT server_id FROM offline_rows WHERE file_id = ?",
                (file_id,)
            ).fetchall()
            return {row["server_id"] for row in rows}

    # =========================================================================
    # Change Tracking
    # =========================================================================

    def get_pending_changes(self) -> List[Dict]:
        """Get all pending changes to sync."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM local_changes
                   WHERE sync_status = 'pending'
                   ORDER BY changed_at"""
            ).fetchall()
            return [dict(row) for row in rows]

    def get_pending_change_count(self) -> int:
        """Get count of pending changes."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM local_changes WHERE sync_status = 'pending'"
            ).fetchone()
            return row["count"]

    def mark_change_synced(self, change_id: int):
        """Mark a change as synced."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'synced', synced_at = datetime('now')
                   WHERE id = ?""",
                (change_id,)
            )
            conn.commit()

    # =========================================================================
    # Sync Subscriptions
    # =========================================================================

    def add_subscription(self, entity_type: str, entity_id: int, entity_name: str,
                         auto_subscribed: bool = False) -> int:
        """Add or update a sync subscription."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sync_subscriptions
                   (entity_type, entity_id, entity_name, server_id, auto_subscribed, enabled, sync_status)
                   VALUES (?, ?, ?, ?, ?, 1, 'pending')""",
                (entity_type, entity_id, entity_name, entity_id, 1 if auto_subscribed else 0)
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM sync_subscriptions WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            ).fetchone()
            return row["id"] if row else 0

    def remove_subscription(self, entity_type: str, entity_id: int) -> bool:
        """Remove a sync subscription."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM sync_subscriptions WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            conn.commit()
            return True

    def get_subscriptions(self, entity_type: Optional[str] = None) -> List[Dict]:
        """Get all active sync subscriptions."""
        with self._get_connection() as conn:
            if entity_type:
                rows = conn.execute(
                    """SELECT * FROM sync_subscriptions
                       WHERE entity_type = ? AND enabled = 1
                       ORDER BY created_at DESC""",
                    (entity_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM sync_subscriptions
                       WHERE enabled = 1
                       ORDER BY entity_type, created_at DESC"""
                ).fetchall()
            return [dict(row) for row in rows]

    def is_subscribed(self, entity_type: str, entity_id: int) -> bool:
        """Check if an entity is subscribed for offline sync."""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT id FROM sync_subscriptions
                   WHERE entity_type = ? AND entity_id = ? AND enabled = 1""",
                (entity_type, entity_id)
            ).fetchone()
            return row is not None

    def update_subscription_status(self, entity_type: str, entity_id: int,
                                   status: str, error: Optional[str] = None):
        """Update sync status for a subscription."""
        with self._get_connection() as conn:
            if status == 'synced':
                conn.execute(
                    """UPDATE sync_subscriptions
                       SET sync_status = ?, last_sync_at = datetime('now'), error_message = NULL
                       WHERE entity_type = ? AND entity_id = ?""",
                    (status, entity_type, entity_id)
                )
            else:
                conn.execute(
                    """UPDATE sync_subscriptions
                       SET sync_status = ?, error_message = ?
                       WHERE entity_type = ? AND entity_id = ?""",
                    (status, error, entity_type, entity_id)
                )
            conn.commit()

    # =========================================================================
    # Translation Memory (SYNC-008)
    # =========================================================================

    def save_tm(self, tm: Dict[str, Any]) -> int:
        """Save or update a TM. Returns local ID."""
        server_id = tm.get("server_id", tm.get("id"))
        with self._get_connection() as conn:
            # Check if TM already exists
            existing = conn.execute(
                "SELECT id FROM offline_tms WHERE server_id = ?",
                (server_id,)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE offline_tms SET
                        name = ?, description = ?, source_lang = ?, target_lang = ?,
                        entry_count = ?, status = ?, mode = ?, owner_id = ?,
                        created_at = ?, updated_at = ?, indexed_at = ?,
                        downloaded_at = datetime('now')
                    WHERE server_id = ?
                """, (
                    tm["name"], tm.get("description"), tm.get("source_lang", "ko"),
                    tm.get("target_lang", "en"), tm.get("entry_count", 0),
                    tm.get("status", "ready"), tm.get("mode", "standard"),
                    tm.get("owner_id"), tm.get("created_at"), tm.get("updated_at"),
                    tm.get("indexed_at"), server_id
                ))
                conn.commit()
                return existing["id"]
            else:
                cursor = conn.execute("""
                    INSERT INTO offline_tms (
                        server_id, name, description, source_lang, target_lang,
                        entry_count, status, mode, owner_id, created_at, updated_at, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    server_id, tm["name"], tm.get("description"),
                    tm.get("source_lang", "ko"), tm.get("target_lang", "en"),
                    tm.get("entry_count", 0), tm.get("status", "ready"),
                    tm.get("mode", "standard"), tm.get("owner_id"),
                    tm.get("created_at"), tm.get("updated_at"), tm.get("indexed_at")
                ))
                conn.commit()
                return cursor.lastrowid

    def get_tms(self) -> List[Dict]:
        """Get all downloaded TMs."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM offline_tms ORDER BY name").fetchall()
            return [dict(row) for row in rows]

    def get_tm(self, server_id: int) -> Optional[Dict]:
        """Get a specific TM by server ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM offline_tms WHERE server_id = ?",
                (server_id,)
            ).fetchone()
            return dict(row) if row else None

    def save_tm_entry(self, entry: Dict[str, Any], local_tm_id: int) -> int:
        """Save a single TM entry. Returns local ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO offline_tm_entries (
                    server_id, tm_id, server_tm_id, source_text, target_text,
                    source_hash, string_id, created_by, change_date,
                    updated_at, updated_by, is_confirmed, confirmed_by, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["server_id"], local_tm_id, entry["server_tm_id"],
                entry["source_text"], entry.get("target_text"),
                entry["source_hash"], entry.get("string_id"),
                entry.get("created_by"), entry.get("change_date"),
                entry.get("updated_at"), entry.get("updated_by"),
                1 if entry.get("is_confirmed") else 0,
                entry.get("confirmed_by"), entry.get("confirmed_at")
            ))
            conn.commit()
            return cursor.lastrowid

    def save_tm_entries_bulk(self, entries: List[Dict], local_tm_id: int, server_tm_id: int):
        """Bulk save TM entries for efficiency."""
        with self._get_connection() as conn:
            for entry in entries:
                conn.execute("""
                    INSERT OR REPLACE INTO offline_tm_entries (
                        server_id, tm_id, server_tm_id, source_text, target_text,
                        source_hash, string_id, created_by, change_date,
                        updated_at, updated_by, is_confirmed, confirmed_by, confirmed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.get("id"), local_tm_id, server_tm_id,
                    entry.get("source_text"), entry.get("target_text"),
                    entry.get("source_hash"), entry.get("string_id"),
                    entry.get("created_by"), entry.get("change_date"),
                    entry.get("updated_at"), entry.get("updated_by"),
                    1 if entry.get("is_confirmed") else 0,
                    entry.get("confirmed_by"), entry.get("confirmed_at")
                ))
            conn.commit()
            logger.debug(f"Bulk saved {len(entries)} TM entries for TM {local_tm_id}")

    def get_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get all entries for a TM."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_tm_entry_count(self, local_tm_id: int) -> int:
        """Get entry count for a TM."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            ).fetchone()
            return row["count"]

    def merge_tm_entry(self, server_entry: Dict, local_tm_id: int) -> str:
        """
        Merge a TM entry using last-write-wins.
        Returns: 'updated', 'skipped', 'inserted'
        """
        with self._get_connection() as conn:
            # Check if entry exists locally
            local_entry = conn.execute(
                "SELECT * FROM offline_tm_entries WHERE server_id = ?",
                (server_entry.get("id"),)
            ).fetchone()

            if not local_entry:
                # New entry - insert
                self.save_tm_entry({
                    "server_id": server_entry.get("id"),
                    "server_tm_id": server_entry.get("tm_id"),
                    "source_text": server_entry.get("source_text"),
                    "target_text": server_entry.get("target_text"),
                    "source_hash": server_entry.get("source_hash"),
                    "string_id": server_entry.get("string_id"),
                    "created_by": server_entry.get("created_by"),
                    "change_date": server_entry.get("change_date"),
                    "updated_at": server_entry.get("updated_at"),
                    "updated_by": server_entry.get("updated_by"),
                    "is_confirmed": server_entry.get("is_confirmed"),
                    "confirmed_by": server_entry.get("confirmed_by"),
                    "confirmed_at": server_entry.get("confirmed_at")
                }, local_tm_id)
                return "inserted"

            local_entry = dict(local_entry)
            local_sync_status = local_entry.get("sync_status", "synced")

            # If local is synced, always take server
            if local_sync_status == "synced":
                conn.execute("""
                    UPDATE offline_tm_entries SET
                        source_text = ?, target_text = ?, source_hash = ?,
                        updated_at = ?, updated_by = ?, is_confirmed = ?,
                        confirmed_by = ?, confirmed_at = ?, sync_status = 'synced',
                        downloaded_at = datetime('now')
                    WHERE server_id = ?
                """, (
                    server_entry.get("source_text"), server_entry.get("target_text"),
                    server_entry.get("source_hash"), server_entry.get("updated_at"),
                    server_entry.get("updated_by"), 1 if server_entry.get("is_confirmed") else 0,
                    server_entry.get("confirmed_by"), server_entry.get("confirmed_at"),
                    server_entry.get("id")
                ))
                conn.commit()
                return "updated"

            # If local is modified, compare timestamps (last-write-wins)
            server_updated = server_entry.get("updated_at", "")
            local_updated = local_entry.get("updated_at", "")

            if server_updated > local_updated:
                # Server is newer - take server, discard local changes
                conn.execute("""
                    UPDATE offline_tm_entries SET
                        source_text = ?, target_text = ?, source_hash = ?,
                        updated_at = ?, updated_by = ?, is_confirmed = ?,
                        confirmed_by = ?, confirmed_at = ?, sync_status = 'synced',
                        downloaded_at = datetime('now')
                    WHERE server_id = ?
                """, (
                    server_entry.get("source_text"), server_entry.get("target_text"),
                    server_entry.get("source_hash"), server_entry.get("updated_at"),
                    server_entry.get("updated_by"), 1 if server_entry.get("is_confirmed") else 0,
                    server_entry.get("confirmed_by"), server_entry.get("confirmed_at"),
                    server_entry.get("id")
                ))
                conn.commit()
                return "updated"
            else:
                # Local is newer - keep local, will push later
                return "skipped"

    def get_modified_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get TM entries with pending changes."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM offline_tm_entries
                   WHERE tm_id = ? AND sync_status = 'modified'""",
                (local_tm_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def mark_tm_entry_synced(self, entry_id: int):
        """Mark a TM entry as synced."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE offline_tm_entries SET sync_status = 'synced' WHERE id = ?",
                (entry_id,)
            )
            conn.commit()

    def get_local_tm_entry_server_ids(self, local_tm_id: int) -> set:
        """Get set of server IDs for all local TM entries in a TM."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT server_id FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            ).fetchall()
            return {row["server_id"] for row in rows}

    def delete_tm_entry(self, server_id: int):
        """Delete a local TM entry (server deleted it)."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM offline_tm_entries WHERE server_id = ?",
                (server_id,)
            )
            conn.commit()

    def get_new_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get TM entries created locally (not yet on server)."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM offline_tm_entries
                   WHERE tm_id = ? AND sync_status = 'new'""",
                (local_tm_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Orphaned Files (P3-PHASE5: Offline Storage Fallback)
    # =========================================================================

    def mark_file_orphaned(self, file_id: int, reason: str = None):
        """
        Mark a file as orphaned (server path doesn't exist).

        This happens when:
        - File was created offline and has no server path
        - Server path was deleted while user was offline
        - Push failed to find destination
        """
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE offline_files
                   SET sync_status = 'orphaned', error_message = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (reason, file_id)
            )
            conn.commit()
            logger.info(f"Marked file {file_id} as orphaned: {reason}")

    def get_orphaned_files(self) -> List[Dict]:
        """Get all orphaned files (files without valid server path)."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM offline_files
                   WHERE sync_status = 'orphaned'
                   ORDER BY name"""
            ).fetchall()
            return [dict(row) for row in rows]

    def get_orphaned_file_count(self) -> int:
        """Get count of orphaned files."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM offline_files WHERE sync_status = 'orphaned'"
            ).fetchone()
            return row["count"]

    def unorphan_file(self, file_id: int, project_id: int, folder_id: int = None):
        """
        Move file out of orphaned state to a proper location.
        Called when user moves file from Offline Storage to a real folder.
        """
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE offline_files
                   SET project_id = ?, server_project_id = ?,
                       folder_id = ?, server_folder_id = ?,
                       sync_status = 'modified', error_message = NULL,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (project_id, project_id, folder_id, folder_id, file_id)
            )
            conn.commit()
            logger.info(f"Unorphaned file {file_id} to project {project_id}, folder {folder_id}")

    # =========================================================================
    # Utility
    # =========================================================================

    def get_stats(self) -> Dict[str, int]:
        """Get offline storage statistics."""
        with self._get_connection() as conn:
            stats = {}
            for table in ["offline_platforms", "offline_projects", "offline_folders",
                         "offline_files", "offline_rows"]:
                row = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[table.replace("offline_", "")] = row["count"]

            stats["pending_changes"] = self.get_pending_change_count()
            return stats

    def clear_all(self):
        """Clear all offline data (use with caution!)."""
        with self._get_connection() as conn:
            for table in ["local_changes", "offline_rows", "offline_files",
                         "offline_folders", "offline_projects", "offline_platforms"]:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
            logger.warning("All offline data cleared")


# Singleton instance
_offline_db: Optional[OfflineDatabase] = None


def get_offline_db() -> OfflineDatabase:
    """Get the singleton offline database instance."""
    global _offline_db
    if _offline_db is None:
        _offline_db = OfflineDatabase()
    return _offline_db
