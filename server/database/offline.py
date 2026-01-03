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
