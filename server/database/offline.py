"""
P3 Offline/Online Mode - SQLite Database Manager

Handles local SQLite database for offline storage.
Provides methods for downloading, storing, and retrieving offline data.

ASYNC MIGRATION (2026-01-31):
- Uses aiosqlite for true async database operations
- Initialization uses sync sqlite3 (runs once at startup)
- All runtime operations use async aiosqlite
"""

import sqlite3
import aiosqlite
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from loguru import logger


class OfflineDatabase:
    """Manager for local SQLite offline storage with async support."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize offline database.

        Note: Uses sync sqlite3 for schema initialization (runs once at startup).
        All runtime operations use async aiosqlite.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default: user's app data directory
            app_data = self._get_app_data_dir()
            db_path = os.path.join(app_data, "offline.db")

        self.db_path = db_path
        self._ensure_directory()
        self._init_schema_sync()  # Sync init at startup

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

    # P9-ARCH: Well-known IDs for Offline Storage
    OFFLINE_STORAGE_PLATFORM_ID = -1
    OFFLINE_STORAGE_PROJECT_ID = -1

    def _init_schema_sync(self):
        """Initialize database schema if needed (SYNC - runs at startup only)."""
        schema_path = Path(__file__).parent / "offline_schema.sql"

        if not schema_path.exists():
            logger.error(f"Offline schema not found: {schema_path}")
            return

        with open(schema_path, "r") as f:
            schema_sql = f.read()

        # Use sync connection for startup initialization
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.debug(f"Offline database initialized: {self.db_path}")
        finally:
            conn.close()

        # P9-ARCH: Create Offline Storage platform and project (sync)
        self._ensure_offline_storage_project_sync()

    def _ensure_offline_storage_project_sync(self):
        """
        P9-ARCH: Create the Offline Storage platform and project if they don't exist.
        SYNC version - used only during initialization.

        This makes Offline Storage a real project in the SQLite database,
        so TMs can be assigned to it and all existing logic works naturally.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Check if Offline Storage platform exists
            platform = conn.execute(
                "SELECT id FROM offline_platforms WHERE id = ?",
                (self.OFFLINE_STORAGE_PLATFORM_ID,)
            ).fetchone()

            if not platform:
                # Create Offline Storage platform
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO offline_platforms (id, server_id, name, description, owner_id, is_restricted, created_at, updated_at, sync_status)
                    VALUES (?, 0, 'Offline Storage', 'Local files stored offline', 0, 0, ?, ?, 'local')
                """, (self.OFFLINE_STORAGE_PLATFORM_ID, now, now))
                logger.info("P9-ARCH: Created Offline Storage platform")

            # Check if Offline Storage project exists
            project = conn.execute(
                "SELECT id FROM offline_projects WHERE id = ?",
                (self.OFFLINE_STORAGE_PROJECT_ID,)
            ).fetchone()

            if not project:
                # Create Offline Storage project
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO offline_projects (id, server_id, name, description, platform_id, server_platform_id, owner_id, is_restricted, created_at, updated_at, sync_status)
                    VALUES (?, 0, 'Offline Storage', 'Local files stored offline', ?, 0, 0, 0, ?, ?, 'local')
                """, (self.OFFLINE_STORAGE_PROJECT_ID, self.OFFLINE_STORAGE_PLATFORM_ID, now, now))
                logger.info("P9-ARCH: Created Offline Storage project")

            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SYNC database connection with row factory.

        DEPRECATED: Use _get_async_connection() for async operations.
        Kept for backward compatibility during migration.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @asynccontextmanager
    async def _get_async_connection(self):
        """Get ASYNC database connection with row factory.

        Usage:
            async with self._get_async_connection() as conn:
                async with conn.execute("SELECT * FROM table") as cursor:
                    rows = await cursor.fetchall()
        """
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    # =========================================================================
    # Sync Metadata
    # =========================================================================

    async def get_meta(self, key: str) -> Optional[str]:
        """Get sync metadata value."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM sync_meta WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row["value"] if row else None

    async def set_meta(self, key: str, value: str):
        """Set sync metadata value."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                """INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))""",
                (key, value)
            )
            await conn.commit()

    # =========================================================================
    # P9-ARCH: Offline Storage Project
    # =========================================================================

    async def get_offline_storage_project(self) -> Dict:
        """
        P9-ARCH: Get the Offline Storage project info.

        This is the "virtual" project that holds all local files.
        TMs can be assigned to this project to work with offline files.
        """
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_projects WHERE id = ?",
                (self.OFFLINE_STORAGE_PROJECT_ID,)
            )
            project = await cursor.fetchone()
            return dict(project) if project else None

    async def get_offline_storage_platform(self) -> Dict:
        """
        P9-ARCH: Get the Offline Storage platform info.
        """
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_platforms WHERE id = ?",
                (self.OFFLINE_STORAGE_PLATFORM_ID,)
            )
            platform = await cursor.fetchone()
            return dict(platform) if platform else None

    async def get_last_sync(self) -> Optional[str]:
        """Get last sync timestamp."""
        return await self.get_meta("last_sync")

    async def set_last_sync(self):
        """Update last sync timestamp to now."""
        await self.set_meta("last_sync", datetime.utcnow().isoformat())

    # =========================================================================
    # Platform Operations
    # =========================================================================

    async def save_platform(self, platform: Dict[str, Any]) -> int:
        """Save a platform to offline storage."""
        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()
            return platform["id"]

    async def get_platforms(self) -> List[Dict]:
        """Get all offline platforms."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_platforms ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Project Operations
    # =========================================================================

    async def save_project(self, project: Dict[str, Any]) -> int:
        """Save a project to offline storage."""
        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()
            return project["id"]

    async def get_projects(self, platform_id: Optional[int] = None) -> List[Dict]:
        """Get offline projects, optionally filtered by platform."""
        async with self._get_async_connection() as conn:
            if platform_id:
                cursor = await conn.execute(
                    "SELECT * FROM offline_projects WHERE platform_id = ? ORDER BY name",
                    (platform_id,)
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM offline_projects ORDER BY name"
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Folder Operations
    # =========================================================================

    async def save_folder(self, folder: Dict[str, Any]) -> int:
        """Save a folder to offline storage."""
        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()
            return folder["id"]

    async def get_folders(self, project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
        """Get folders in a project, optionally filtered by parent."""
        async with self._get_async_connection() as conn:
            if parent_id is None:
                cursor = await conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id IS NULL ORDER BY name""",
                    (project_id,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id = ? ORDER BY name""",
                    (project_id, parent_id)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_local_folder(self, name: str, parent_id: int = None) -> int:
        """
        P9: Create a new folder directly in Offline Storage (local-only).

        This is for folders created while working in Offline Storage.
        They have no server reference and live only in Offline Storage
        until the user goes online and moves them to a real project.

        sync_status='local' means "never been on server".

        Returns the new folder ID (negative to avoid conflicts with server IDs).
        """
        import time
        from datetime import datetime

        now = datetime.now().isoformat()
        offline_project_id = self.OFFLINE_STORAGE_PROJECT_ID

        async with self._get_async_connection() as conn:
            # Check for duplicate names in same parent
            if parent_id is None:
                cursor = await conn.execute(
                    """SELECT name FROM offline_folders
                       WHERE project_id = ? AND parent_id IS NULL AND name = ?""",
                    (offline_project_id, name)
                )
            else:
                cursor = await conn.execute(
                    """SELECT name FROM offline_folders
                       WHERE project_id = ? AND parent_id = ? AND name = ?""",
                    (offline_project_id, parent_id, name)
                )

            # Auto-rename if duplicate exists
            final_name = name
            if await cursor.fetchone():
                counter = 1
                while True:
                    final_name = f"{name}_{counter}"
                    if parent_id is None:
                        cursor = await conn.execute(
                            """SELECT name FROM offline_folders
                               WHERE project_id = ? AND parent_id IS NULL AND name = ?""",
                            (offline_project_id, final_name)
                        )
                    else:
                        cursor = await conn.execute(
                            """SELECT name FROM offline_folders
                               WHERE project_id = ? AND parent_id = ? AND name = ?""",
                            (offline_project_id, parent_id, final_name)
                        )
                    if not await cursor.fetchone():
                        break
                    counter += 1
                logger.info(f"Auto-renamed duplicate folder: '{name}' → '{final_name}'")

            # Use negative IDs to avoid conflicts with real server IDs
            # Fix: Negate AFTER modulo (Python modulo with positive divisor returns positive)
            folder_id = -(int(time.time() * 1000) % 1000000000)

            await conn.execute(
                """INSERT INTO offline_folders
                   (id, server_id, name, project_id, server_project_id,
                    parent_id, server_parent_id, created_at, downloaded_at, sync_status)
                   VALUES (?, NULL, ?, ?, NULL, ?, NULL, ?, datetime('now'), 'local')""",
                (folder_id, final_name, offline_project_id, parent_id, now)
            )
            await conn.commit()
            logger.info(f"Created local folder: id={folder_id}, name='{final_name}', parent={parent_id}")
            return folder_id, final_name

    async def get_local_folders(self, parent_id: int = None) -> List[Dict]:
        """Get local folders in Offline Storage."""
        async with self._get_async_connection() as conn:
            if parent_id is None:
                cursor = await conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id IS NULL AND sync_status = 'local'
                       ORDER BY name""",
                    (self.OFFLINE_STORAGE_PROJECT_ID,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT * FROM offline_folders
                       WHERE project_id = ? AND parent_id = ? AND sync_status = 'local'
                       ORDER BY name""",
                    (self.OFFLINE_STORAGE_PROJECT_ID, parent_id)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_local_folder(self, folder_id: int, permanent: bool = False) -> bool:
        """
        P9-BIN-001: Delete a local folder from Offline Storage.

        Only works for local folders (sync_status='local').
        By default, moves to trash (soft delete). Use permanent=True for hard delete.
        Also deletes all files and subfolders inside.
        Returns True if deleted, False if folder not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify folder is local before deleting
            cursor = await conn.execute(
                "SELECT * FROM offline_folders WHERE id = ?",
                (folder_id,)
            )
            folder_row = await cursor.fetchone()

            if not folder_row:
                logger.warning(f"Cannot delete: folder {folder_id} not found")
                return False

            if folder_row["sync_status"] != "local":
                logger.warning(f"Cannot delete: folder {folder_id} is not local (status={folder_row['sync_status']})")
                return False

            if not permanent:
                # P9-BIN-001: Soft delete - serialize folder and contents to trash
                folder_data = await self._serialize_local_folder_for_trash_async(conn, folder_id)
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()

                await conn.execute(
                    """INSERT INTO offline_trash
                       (item_type, item_id, item_name, item_data, parent_folder_id, expires_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'trashed')""",
                    ('local-folder', folder_id, folder_row['name'], json.dumps(folder_data),
                     folder_row['parent_id'], expires_at)
                )
                logger.info(f"Moved local folder {folder_id} ('{folder_row['name']}') to trash")

            # Delete files in this folder first
            await conn.execute("DELETE FROM offline_rows WHERE file_id IN (SELECT id FROM offline_files WHERE folder_id = ?)", (folder_id,))
            await conn.execute("DELETE FROM offline_files WHERE folder_id = ?", (folder_id,))

            # Delete subfolders recursively (simplified - deletes all with this parent)
            await conn.execute("DELETE FROM offline_folders WHERE parent_id = ?", (folder_id,))

            # Delete the folder itself
            await conn.execute("DELETE FROM offline_folders WHERE id = ?", (folder_id,))
            await conn.commit()

            action = "permanently deleted" if permanent else "moved to trash"
            logger.info(f"Local folder {folder_id} {action}")
            return True

    async def _serialize_local_folder_for_trash_async(self, conn, folder_id: int) -> dict:
        """P9-BIN-001: Serialize a local folder and all its contents for trash storage."""
        cursor = await conn.execute(
            "SELECT * FROM offline_folders WHERE id = ?",
            (folder_id,)
        )
        folder_row = await cursor.fetchone()

        # Get all files in this folder
        cursor = await conn.execute(
            "SELECT * FROM offline_files WHERE folder_id = ?",
            (folder_id,)
        )
        files = await cursor.fetchall()

        files_data = []
        for file in files:
            cursor = await conn.execute(
                "SELECT * FROM offline_rows WHERE file_id = ? ORDER BY row_num",
                (file['id'],)
            )
            rows = await cursor.fetchall()
            files_data.append({
                "file": dict(file),
                "rows": [dict(r) for r in rows]
            })

        # Get subfolders (recursive)
        cursor = await conn.execute(
            "SELECT * FROM offline_folders WHERE parent_id = ?",
            (folder_id,)
        )
        subfolders = await cursor.fetchall()

        subfolders_data = []
        for subfolder in subfolders:
            subfolders_data.append(await self._serialize_local_folder_for_trash_async(conn, subfolder['id']))

        return {
            "folder": dict(folder_row),
            "files": files_data,
            "subfolders": subfolders_data
        }

    async def rename_local_folder(self, folder_id: int, new_name: str) -> bool:
        """
        P9: Rename a local folder in Offline Storage.

        Only works for local folders (sync_status='local').
        Returns True if renamed, False if folder not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify folder is local before renaming
            cursor = await conn.execute(
                "SELECT sync_status FROM offline_folders WHERE id = ?",
                (folder_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Cannot rename: folder {folder_id} not found")
                return False

            if row["sync_status"] != "local":
                logger.warning(f"Cannot rename: folder {folder_id} is not local (status={row['sync_status']})")
                return False

            await conn.execute(
                "UPDATE offline_folders SET name = ? WHERE id = ?",
                (new_name, folder_id)
            )
            await conn.commit()
            logger.info(f"Renamed local folder {folder_id} to '{new_name}'")
            return True

    # =========================================================================
    # File Operations
    # =========================================================================

    async def save_file(self, file: Dict[str, Any]) -> int:
        """Save a file to offline storage."""
        extra_data = json.dumps(file.get("extra_data")) if file.get("extra_data") else None

        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()
            return file["id"]

    async def get_files(self, project_id: int, folder_id: Optional[int] = None) -> List[Dict]:
        """Get files in a project, optionally filtered by folder."""
        async with self._get_async_connection() as conn:
            if folder_id is None:
                cursor = await conn.execute(
                    """SELECT * FROM offline_files
                       WHERE project_id = ? AND folder_id IS NULL ORDER BY name""",
                    (project_id,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT * FROM offline_files
                       WHERE project_id = ? AND folder_id = ? ORDER BY name""",
                    (project_id, folder_id)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_file(self, file_id: int) -> Optional[Dict]:
        """Get a single file by ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_files WHERE id = ?", (file_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def is_file_downloaded(self, server_file_id: int) -> bool:
        """Check if a file is already downloaded."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT id FROM offline_files WHERE server_id = ?",
                (server_file_id,)
            )
            row = await cursor.fetchone()
            return row is not None

    # =========================================================================
    # Row Operations
    # =========================================================================

    async def save_rows(self, file_id: int, rows: List[Dict[str, Any]]):
        """Save multiple rows to offline storage (bulk insert)."""
        async with self._get_async_connection() as conn:
            # Delete existing rows for this file first
            await conn.execute("DELETE FROM offline_rows WHERE file_id = ?", (file_id,))

            # Insert new rows
            for row in rows:
                extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
                await conn.execute(
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
            await conn.commit()
            logger.debug(f"Saved {len(rows)} rows for file {file_id}")

    async def get_rows(self, file_id: int) -> List[Dict]:
        """Get all rows for a file."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_rows WHERE file_id = ? ORDER BY row_num",
                (file_id,)
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    async def update_row(self, row_id: int, field: str, value: Any) -> bool:
        """Update a single row field and track the change."""
        allowed_fields = {"target", "memo", "status"}
        if field not in allowed_fields:
            logger.warning(f"Cannot update field '{field}' - not editable")
            return False

        async with self._get_async_connection() as conn:
            # Get current value
            cursor = await conn.execute(
                f"SELECT {field}, server_id FROM offline_rows WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            old_value = row[field]

            # Update the row
            await conn.execute(
                f"""UPDATE offline_rows
                    SET {field} = ?, sync_status = 'modified', updated_at = datetime('now')
                    WHERE id = ?""",
                (value, row_id)
            )

            # Track the change
            await conn.execute(
                """INSERT INTO local_changes
                   (entity_type, entity_id, server_id, change_type, field_name, old_value, new_value)
                   VALUES ('row', ?, ?, 'edit', ?, ?, ?)""",
                (row_id, row["server_id"], field, str(old_value), str(value))
            )

            await conn.commit()
            return True

    # =========================================================================
    # Merge Operations (P3: Last-write-wins sync)
    # =========================================================================

    async def get_row_by_server_id(self, server_id: int) -> Optional[Dict]:
        """Get a local row by its server ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_rows WHERE server_id = ?",
                (server_id,)
            )
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                return d
            return None

    async def get_modified_rows(self, file_id: int) -> List[Dict]:
        """Get all locally modified rows for a file."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_rows
                   WHERE file_id = ? AND sync_status = 'modified'
                   ORDER BY row_num""",
                (file_id,)
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    async def get_new_rows(self, file_id: int) -> List[Dict]:
        """Get all locally created rows for a file."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_rows
                   WHERE file_id = ? AND sync_status = 'new'
                   ORDER BY row_num""",
                (file_id,)
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                result.append(d)
            return result

    async def merge_row(self, server_row: Dict, file_id: int) -> str:
        """
        Merge a server row with local data using last-write-wins.

        Returns: 'updated', 'skipped', 'inserted'
        """
        local_row = await self.get_row_by_server_id(server_row["id"])

        if local_row is None:
            # New row from server - insert it
            await self._insert_row(server_row, file_id)
            return 'inserted'

        # Row exists locally
        if local_row["sync_status"] == 'synced':
            # No local changes - take server version
            await self._update_row_from_server(server_row, local_row["id"])
            return 'updated'

        elif local_row["sync_status"] in ('modified', 'new'):
            # Local has changes - compare timestamps
            server_updated = server_row.get("updated_at") or ""
            local_updated = local_row.get("updated_at") or ""

            if server_updated > local_updated:
                # Server is newer - server wins, discard local changes
                await self._update_row_from_server(server_row, local_row["id"])
                await self._discard_local_changes(local_row["id"])
                logger.debug(f"Server wins for row {server_row['id']} (server: {server_updated} > local: {local_updated})")
                return 'updated'
            else:
                # Local is newer - keep local, will push later
                logger.debug(f"Local wins for row {server_row['id']} (local: {local_updated} >= server: {server_updated})")
                return 'skipped'

        return 'skipped'

    async def merge_rows_batch(self, server_rows: List[Dict], file_id: int) -> Dict[str, int]:
        """
        OPTIMIZED: Merge multiple server rows in a single transaction.

        This is 100x faster than calling merge_row() per row because:
        1. Single connection for all operations
        2. Batch fetch of local rows upfront
        3. Single commit at the end

        Returns: {'inserted': N, 'updated': N, 'skipped': N}
        """
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}

        if not server_rows:
            return stats

        async with self._get_async_connection() as conn:
            # Step 1: Fetch ALL local rows for this file in ONE query
            cursor = await conn.execute(
                "SELECT * FROM offline_rows WHERE file_id = ?",
                (file_id,)
            )
            local_rows_raw = await cursor.fetchall()

            # Build lookup dict by server_id
            local_by_server_id = {}
            for row in local_rows_raw:
                d = dict(row)
                if d.get("extra_data"):
                    d["extra_data"] = json.loads(d["extra_data"])
                local_by_server_id[d["server_id"]] = d

            # Step 2: Process all server rows
            for server_row in server_rows:
                server_id = server_row["id"]
                local_row = local_by_server_id.get(server_id)
                extra_data = json.dumps(server_row.get("extra_data")) if server_row.get("extra_data") else None

                if local_row is None:
                    # INSERT new row
                    await conn.execute(
                        """INSERT INTO offline_rows
                           (id, server_id, file_id, server_file_id, row_num, string_id,
                            source, target, memo, status, extra_data, created_at, updated_at,
                            downloaded_at, sync_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                        (
                            server_row["id"], server_row["id"], file_id, file_id,
                            server_row.get("row_num", 0), server_row.get("string_id"),
                            server_row.get("source"), server_row.get("target"),
                            server_row.get("memo"), server_row.get("status", "normal"),
                            extra_data, server_row.get("created_at"), server_row.get("updated_at"),
                        )
                    )
                    stats['inserted'] += 1

                elif local_row["sync_status"] == 'synced':
                    # UPDATE - no local changes, take server version
                    await conn.execute(
                        """UPDATE offline_rows SET
                           source = ?, target = ?, memo = ?, status = ?,
                           extra_data = ?, updated_at = ?, sync_status = 'synced',
                           downloaded_at = datetime('now')
                           WHERE id = ?""",
                        (
                            server_row.get("source"), server_row.get("target"),
                            server_row.get("memo"), server_row.get("status", "normal"),
                            extra_data, server_row.get("updated_at"), local_row["id"]
                        )
                    )
                    stats['updated'] += 1

                elif local_row["sync_status"] in ('modified', 'new'):
                    # Conflict - compare timestamps
                    server_updated = server_row.get("updated_at") or ""
                    local_updated = local_row.get("updated_at") or ""

                    if server_updated > local_updated:
                        # Server wins
                        await conn.execute(
                            """UPDATE offline_rows SET
                               source = ?, target = ?, memo = ?, status = ?,
                               extra_data = ?, updated_at = ?, sync_status = 'synced',
                               downloaded_at = datetime('now')
                               WHERE id = ?""",
                            (
                                server_row.get("source"), server_row.get("target"),
                                server_row.get("memo"), server_row.get("status", "normal"),
                                extra_data, server_row.get("updated_at"), local_row["id"]
                            )
                        )
                        # Also clear local changes record
                        await conn.execute(
                            "DELETE FROM local_changes WHERE entity_type = 'row' AND entity_id = ?",
                            (local_row["id"],)
                        )
                        stats['updated'] += 1
                    else:
                        # Local wins - skip
                        stats['skipped'] += 1
                else:
                    stats['skipped'] += 1

            # Step 3: Single commit for ALL operations
            await conn.commit()

        return stats

    async def _insert_row(self, row: Dict, file_id: int):
        """Insert a new row from server."""
        extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()

    async def _update_row_from_server(self, server_row: Dict, local_id: int):
        """Update local row with server data."""
        extra_data = json.dumps(server_row.get("extra_data")) if server_row.get("extra_data") else None
        async with self._get_async_connection() as conn:
            await conn.execute(
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
            await conn.commit()

    async def _discard_local_changes(self, local_row_id: int):
        """Discard pending local changes for a row (server won)."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'discarded'
                   WHERE entity_type = 'row' AND entity_id = ? AND sync_status = 'pending'""",
                (local_row_id,)
            )
            await conn.commit()

    async def mark_row_synced(self, row_id: int):
        """Mark a row as synced after pushing to server."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                """UPDATE offline_rows
                   SET sync_status = 'synced'
                   WHERE id = ?""",
                (row_id,)
            )
            await conn.commit()

    async def delete_row(self, server_id: int):
        """Delete a local row (server deleted it)."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                "DELETE FROM offline_rows WHERE server_id = ?",
                (server_id,)
            )
            # Also discard any pending changes
            await conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'discarded'
                   WHERE entity_type = 'row' AND server_id = ? AND sync_status = 'pending'""",
                (server_id,)
            )
            await conn.commit()

    async def get_local_row_server_ids(self, file_id: int) -> set:
        """Get set of server IDs for all local rows in a file."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT server_id FROM offline_rows WHERE file_id = ?",
                (file_id,)
            )
            rows = await cursor.fetchall()
            return {row["server_id"] for row in rows}

    # =========================================================================
    # Change Tracking
    # =========================================================================

    async def get_pending_changes(self) -> List[Dict]:
        """Get all pending changes to sync."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM local_changes
                   WHERE sync_status = 'pending'
                   ORDER BY changed_at"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_pending_change_count(self) -> int:
        """Get count of pending changes."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM local_changes WHERE sync_status = 'pending'"
            )
            row = await cursor.fetchone()
            return row["count"]

    async def mark_change_synced(self, change_id: int):
        """Mark a change as synced."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                """UPDATE local_changes
                   SET sync_status = 'synced', synced_at = datetime('now')
                   WHERE id = ?""",
                (change_id,)
            )
            await conn.commit()

    # =========================================================================
    # Sync Subscriptions
    # =========================================================================

    async def add_subscription(self, entity_type: str, entity_id: int, entity_name: str,
                         auto_subscribed: bool = False) -> int:
        """Add or update a sync subscription."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                """INSERT OR REPLACE INTO sync_subscriptions
                   (entity_type, entity_id, entity_name, server_id, auto_subscribed, enabled, sync_status)
                   VALUES (?, ?, ?, ?, ?, 1, 'pending')""",
                (entity_type, entity_id, entity_name, entity_id, 1 if auto_subscribed else 0)
            )
            await conn.commit()
            cursor = await conn.execute(
                "SELECT id FROM sync_subscriptions WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            row = await cursor.fetchone()
            return row["id"] if row else 0

    async def remove_subscription(self, entity_type: str, entity_id: int) -> bool:
        """Remove a sync subscription."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                "DELETE FROM sync_subscriptions WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            await conn.commit()
            return True

    async def get_subscriptions(self, entity_type: Optional[str] = None) -> List[Dict]:
        """Get all active sync subscriptions."""
        async with self._get_async_connection() as conn:
            if entity_type:
                cursor = await conn.execute(
                    """SELECT * FROM sync_subscriptions
                       WHERE entity_type = ? AND enabled = 1
                       ORDER BY created_at DESC""",
                    (entity_type,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT * FROM sync_subscriptions
                       WHERE enabled = 1
                       ORDER BY entity_type, created_at DESC"""
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def is_subscribed(self, entity_type: str, entity_id: int) -> bool:
        """Check if an entity is subscribed for offline sync."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT id FROM sync_subscriptions
                   WHERE entity_type = ? AND entity_id = ? AND enabled = 1""",
                (entity_type, entity_id)
            )
            row = await cursor.fetchone()
            return row is not None

    async def update_subscription_status(self, entity_type: str, entity_id: int,
                                   status: str, error: Optional[str] = None):
        """Update sync status for a subscription."""
        async with self._get_async_connection() as conn:
            if status == 'synced':
                await conn.execute(
                    """UPDATE sync_subscriptions
                       SET sync_status = ?, last_sync_at = datetime('now'), error_message = NULL
                       WHERE entity_type = ? AND entity_id = ?""",
                    (status, entity_type, entity_id)
                )
            else:
                await conn.execute(
                    """UPDATE sync_subscriptions
                       SET sync_status = ?, error_message = ?
                       WHERE entity_type = ? AND entity_id = ?""",
                    (status, error, entity_type, entity_id)
                )
            await conn.commit()

    # =========================================================================
    # Translation Memory (SYNC-008)
    # =========================================================================

    async def save_tm(self, tm: Dict[str, Any]) -> int:
        """Save or update a TM. Returns local ID."""
        server_id = tm.get("server_id", tm.get("id"))
        async with self._get_async_connection() as conn:
            # Check if TM already exists
            cursor = await conn.execute(
                "SELECT id FROM offline_tms WHERE server_id = ?",
                (server_id,)
            )
            existing = await cursor.fetchone()

            if existing:
                await conn.execute("""
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
                await conn.commit()
                return existing["id"]
            else:
                cursor = await conn.execute("""
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
                await conn.commit()
                return cursor.lastrowid

    async def get_tms(self) -> List[Dict]:
        """Get all downloaded TMs."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute("SELECT * FROM offline_tms ORDER BY name")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_tm(self, server_id: int) -> Optional[Dict]:
        """Get a specific TM by server ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_tms WHERE server_id = ?",
                (server_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_tm_entry(self, entry: Dict[str, Any], local_tm_id: int) -> int:
        """
        Save a single TM entry. Returns local ID.

        P9-ARCH: Works for both synced entries (from server) and local-only entries.
        For local entries, server_id and server_tm_id will be None.
        """
        async with self._get_async_connection() as conn:
            cursor = await conn.execute("""
                INSERT OR REPLACE INTO offline_tm_entries (
                    server_id, tm_id, server_tm_id, source_text, target_text,
                    source_hash, string_id, created_by, change_date,
                    updated_at, updated_by, is_confirmed, confirmed_by, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get("server_id"),  # None for local entries
                local_tm_id,
                entry.get("server_tm_id"),  # None for local entries
                entry.get("source_text"),
                entry.get("target_text"),
                entry.get("source_hash"),
                entry.get("string_id"),
                entry.get("created_by"),
                entry.get("change_date"),
                entry.get("updated_at"),
                entry.get("updated_by"),
                1 if entry.get("is_confirmed") else 0,
                entry.get("confirmed_by"),
                entry.get("confirmed_at")
            ))
            await conn.commit()
            return cursor.lastrowid

    async def save_tm_entries_bulk(self, entries: List[Dict], local_tm_id: int, server_tm_id: int):
        """Bulk save TM entries for efficiency."""
        async with self._get_async_connection() as conn:
            for entry in entries:
                await conn.execute("""
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
            await conn.commit()
            logger.debug(f"Bulk saved {len(entries)} TM entries for TM {local_tm_id}")

    async def get_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get all entries for a TM."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_tm_entry_count(self, local_tm_id: int) -> int:
        """Get entry count for a TM."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            )
            row = await cursor.fetchone()
            return row["count"]

    async def merge_tm_entry(self, server_entry: Dict, local_tm_id: int) -> str:
        """
        Merge a TM entry using last-write-wins.
        Returns: 'updated', 'skipped', 'inserted'
        """
        async with self._get_async_connection() as conn:
            # Check if entry exists locally
            cursor = await conn.execute(
                "SELECT * FROM offline_tm_entries WHERE server_id = ?",
                (server_entry.get("id"),)
            )
            local_entry = await cursor.fetchone()

            if not local_entry:
                # New entry - insert
                await self.save_tm_entry({
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
                await conn.execute("""
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
                await conn.commit()
                return "updated"

            # If local is modified, compare timestamps (last-write-wins)
            server_updated = server_entry.get("updated_at", "")
            local_updated = local_entry.get("updated_at", "")

            if server_updated > local_updated:
                # Server is newer - take server, discard local changes
                await conn.execute("""
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
                await conn.commit()
                return "updated"
            else:
                # Local is newer - keep local, will push later
                return "skipped"

    async def get_modified_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get TM entries with pending changes."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_tm_entries
                   WHERE tm_id = ? AND sync_status = 'modified'""",
                (local_tm_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_tm_entry_synced(self, entry_id: int):
        """Mark a TM entry as synced."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                "UPDATE offline_tm_entries SET sync_status = 'synced' WHERE id = ?",
                (entry_id,)
            )
            await conn.commit()

    async def get_local_tm_entry_server_ids(self, local_tm_id: int) -> set:
        """Get set of server IDs for all local TM entries in a TM."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT server_id FROM offline_tm_entries WHERE tm_id = ?",
                (local_tm_id,)
            )
            rows = await cursor.fetchall()
            return {row["server_id"] for row in rows}

    async def delete_tm_entry(self, server_id: int):
        """Delete a local TM entry (server deleted it)."""
        async with self._get_async_connection() as conn:
            await conn.execute(
                "DELETE FROM offline_tm_entries WHERE server_id = ?",
                (server_id,)
            )
            await conn.commit()

    async def get_new_tm_entries(self, local_tm_id: int) -> List[Dict]:
        """Get TM entries created locally (not yet on server)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_tm_entries
                   WHERE tm_id = ? AND sync_status = 'new'""",
                (local_tm_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # TM Assignment (Full Offline Support)
    # =========================================================================

    async def assign_local_tm(
        self,
        tm_id: int,
        platform_id: Optional[int] = None,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None
    ) -> Dict:
        """
        Assign a TM to a platform/project/folder in SQLite.
        This enables full offline TM operations.
        """
        async with self._get_async_connection() as conn:
            now = datetime.now().isoformat()

            # Check if assignment already exists
            cursor = await conn.execute(
                """SELECT id FROM offline_tm_assignments
                   WHERE tm_id = ? AND
                         (platform_id = ? OR (platform_id IS NULL AND ? IS NULL)) AND
                         (project_id = ? OR (project_id IS NULL AND ? IS NULL)) AND
                         (folder_id = ? OR (folder_id IS NULL AND ? IS NULL))""",
                (tm_id, platform_id, platform_id, project_id, project_id, folder_id, folder_id)
            )
            existing = await cursor.fetchone()

            if existing:
                # Update existing assignment
                await conn.execute(
                    """UPDATE offline_tm_assignments
                       SET is_active = 1, sync_status = 'modified'
                       WHERE id = ?""",
                    (existing['id'],)
                )
                assignment_id = existing['id']
            else:
                # Create new assignment
                cursor = await conn.execute(
                    """INSERT INTO offline_tm_assignments
                       (server_id, tm_id, server_tm_id, platform_id, project_id, folder_id,
                        is_active, priority, assigned_at, sync_status)
                       VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, 'local')""",
                    (0, tm_id, 0, platform_id, project_id, folder_id, now)
                )
                assignment_id = cursor.lastrowid

            await conn.commit()
            logger.info(f"Assigned TM {tm_id} locally: platform={platform_id}, project={project_id}, folder={folder_id}")

            return {
                'id': assignment_id,
                'tm_id': tm_id,
                'platform_id': platform_id,
                'project_id': project_id,
                'folder_id': folder_id,
                'is_active': True,
                'sync_status': 'local'
            }

    async def unassign_local_tm(self, tm_id: int) -> bool:
        """Remove TM assignment (move to unassigned)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """UPDATE offline_tm_assignments
                   SET platform_id = NULL, project_id = NULL, folder_id = NULL,
                       is_active = 0, sync_status = 'modified'
                   WHERE tm_id = ?""",
                (tm_id,)
            )
            await conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Unassigned TM {tm_id} locally")
                return True
            return False

    async def get_local_tm_assignment(self, tm_id: int) -> Optional[Dict]:
        """Get the current assignment for a TM."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_tm_assignments
                   WHERE tm_id = ? AND is_active = 1
                   ORDER BY id DESC LIMIT 1""",
                (tm_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_local_tm_assignments_for_scope(
        self,
        platform_id: Optional[int] = None,
        project_id: Optional[int] = None,
        folder_id: Optional[int] = None
    ) -> List[Dict]:
        """Get all TM assignments for a given scope."""
        async with self._get_async_connection() as conn:
            # Build query based on scope
            if folder_id:
                cursor = await conn.execute(
                    """SELECT a.*, t.name as tm_name, t.entry_count
                       FROM offline_tm_assignments a
                       JOIN offline_tms t ON a.tm_id = t.id
                       WHERE a.folder_id = ? AND a.is_active = 1""",
                    (folder_id,)
                )
            elif project_id:
                cursor = await conn.execute(
                    """SELECT a.*, t.name as tm_name, t.entry_count
                       FROM offline_tm_assignments a
                       JOIN offline_tms t ON a.tm_id = t.id
                       WHERE a.project_id = ? AND a.is_active = 1""",
                    (project_id,)
                )
            elif platform_id:
                cursor = await conn.execute(
                    """SELECT a.*, t.name as tm_name, t.entry_count
                       FROM offline_tm_assignments a
                       JOIN offline_tms t ON a.tm_id = t.id
                       WHERE a.platform_id = ? AND a.is_active = 1""",
                    (platform_id,)
                )
            else:
                # Unassigned TMs
                cursor = await conn.execute(
                    """SELECT a.*, t.name as tm_name, t.entry_count
                       FROM offline_tm_assignments a
                       JOIN offline_tms t ON a.tm_id = t.id
                       WHERE a.platform_id IS NULL AND a.project_id IS NULL
                             AND a.folder_id IS NULL AND a.is_active = 1"""
                )

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_local_tm(self, name: str, source_lang: str = 'ko', target_lang: str = 'en') -> Dict:
        """Create a new TM locally (for offline use)."""
        async with self._get_async_connection() as conn:
            now = datetime.now().isoformat()
            cursor = await conn.execute(
                """INSERT INTO offline_tms
                   (server_id, name, source_lang, target_lang, entry_count,
                    status, mode, created_at, updated_at, sync_status)
                   VALUES (0, ?, ?, ?, 0, 'ready', 'standard', ?, ?, 'local')""",
                (name, source_lang, target_lang, now, now)
            )
            tm_id = cursor.lastrowid
            await conn.commit()
            logger.info(f"Created local TM: {name} (id={tm_id})")

            return {
                'id': tm_id,
                'server_id': 0,
                'name': name,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'entry_count': 0,
                'status': 'ready',
                'sync_status': 'local'
            }

    async def get_all_local_tms(self) -> List[Dict]:
        """Get all TMs (both synced and local-only)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT t.*, a.platform_id, a.project_id, a.folder_id, a.is_active
                   FROM offline_tms t
                   LEFT JOIN offline_tm_assignments a ON t.id = a.tm_id AND a.is_active = 1
                   ORDER BY t.name"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Orphaned Files (P3-PHASE5: Offline Storage Fallback)
    # =========================================================================

    async def mark_file_orphaned(self, file_id: int, reason: str = None):
        """
        Mark a file as orphaned (server path doesn't exist).

        This happens when:
        - File was created offline and has no server path
        - Server path was deleted while user was offline
        - Push failed to find destination
        """
        async with self._get_async_connection() as conn:
            await conn.execute(
                """UPDATE offline_files
                   SET sync_status = 'orphaned', error_message = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (reason, file_id)
            )
            await conn.commit()
            logger.info(f"Marked file {file_id} as orphaned: {reason}")

    async def get_local_files(self) -> List[Dict]:
        """Get all local files (files in Offline Storage, never synced to server)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_files
                   WHERE sync_status = 'local'
                   ORDER BY name"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_local_file(self, file_id: int) -> Optional[Dict]:
        """P9: Get a single local file by ID."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_files WHERE id = ?",
                (file_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_rows_for_file(self, file_id: int) -> List[Dict]:
        """P9: Get all rows for a file from SQLite."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM offline_rows
                   WHERE file_id = ?
                   ORDER BY row_num""",
                (file_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_row(self, row_id: int) -> Optional[Dict]:
        """P9: Get a single row by ID from SQLite."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_rows WHERE id = ?",
                (row_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_local_file_count(self) -> int:
        """Get count of local files in Offline Storage."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM offline_files WHERE sync_status = 'local'"
            )
            row = await cursor.fetchone()
            return row["count"]

    async def assign_local_file(self, file_id: int, project_id: int, folder_id: int = None):
        """
        Assign a local file to a server project/folder.
        Called when user moves file from Offline Storage to a real folder.
        Changes sync_status from 'local' to 'modified' (ready to sync).
        """
        async with self._get_async_connection() as conn:
            await conn.execute(
                """UPDATE offline_files
                   SET project_id = ?, server_project_id = ?,
                       folder_id = ?, server_folder_id = ?,
                       sync_status = 'modified', error_message = NULL,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (project_id, project_id, folder_id, folder_id, file_id)
            )
            await conn.commit()
            logger.info(f"Assigned local file {file_id} to project {project_id}, folder {folder_id}")

    async def create_local_file(
        self,
        name: str,
        original_filename: str,
        file_format: str = "txt",
        source_language: str = "ko",
        target_language: str = None,
        extra_data: Dict = None,
        folder_id: int = None  # P9-FIX: Support creating files inside local folders
    ) -> int:
        """
        P9: Create a new file directly in Offline Storage (local-only).

        This is for files created/imported while in offline mode.
        They have no server reference and live only in Offline Storage
        until the user goes online and moves them to a real project.

        P9-ARCH: Uses OFFLINE_STORAGE_PROJECT_ID to properly assign files to the
        Offline Storage project. This allows TMs to be assigned to this project.

        sync_status='local' means "never been on server" (different from 'orphaned'
        which means "was synced but lost server link").

        P9-FIX: Enforces unique filename within same folder (auto-rename if duplicate).

        Args:
            folder_id: Optional local folder ID to place file in. If None, file is at root.
        """
        import time

        extra_json = json.dumps(extra_data) if extra_data else None
        now = datetime.now().isoformat()

        # P9-ARCH: Use the Offline Storage project for local files
        offline_project_id = self.OFFLINE_STORAGE_PROJECT_ID

        async with self._get_async_connection() as conn:
            # P9-FIX: Check for duplicate names within SAME FOLDER (per-folder unique)
            # Uses same pattern as naming.py: test.txt → test_1.txt → test_2.txt
            final_name = name

            # Query differs based on whether folder_id is provided
            if folder_id is None:
                cursor = await conn.execute(
                    """SELECT name FROM offline_files
                       WHERE project_id = ? AND folder_id IS NULL AND name = ?""",
                    (offline_project_id, name)
                )
            else:
                cursor = await conn.execute(
                    """SELECT name FROM offline_files
                       WHERE project_id = ? AND folder_id = ? AND name = ?""",
                    (offline_project_id, folder_id, name)
                )

            if await cursor.fetchone():
                # Duplicate exists, generate unique name matching naming.py pattern
                if '.' in name and not name.startswith('.'):
                    base_name, ext = name.rsplit('.', 1)
                    ext = f".{ext}"
                else:
                    base_name = name
                    ext = ""

                counter = 1
                while True:
                    final_name = f"{base_name}_{counter}{ext}"
                    if folder_id is None:
                        cursor = await conn.execute(
                            """SELECT name FROM offline_files
                               WHERE project_id = ? AND folder_id IS NULL AND name = ?""",
                            (offline_project_id, final_name)
                        )
                    else:
                        cursor = await conn.execute(
                            """SELECT name FROM offline_files
                               WHERE project_id = ? AND folder_id = ? AND name = ?""",
                            (offline_project_id, folder_id, final_name)
                        )
                    if not await cursor.fetchone():
                        break
                    counter += 1
                logger.info(f"Auto-renamed duplicate: '{name}' → '{final_name}'")

            # Use negative IDs to avoid conflicts with real server IDs
            # Each new local file gets a unique negative ID based on timestamp
            # Fix: Negate AFTER modulo (Python modulo with positive divisor returns positive)
            file_id = -(int(time.time() * 1000) % 1000000000)  # Negative, unique

            # P9-ARCH: Use the Offline Storage project ID instead of 0
            # P9-FIX: Support placing files in local folders
            await conn.execute(
                """INSERT INTO offline_files
                   (id, server_id, name, original_filename, format, row_count,
                    source_language, target_language, project_id, server_project_id,
                    folder_id, server_folder_id, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, 0, ?, ?, ?, 0, ?, ?, ?, 0, ?, NULL, ?, ?, ?, datetime('now'), 'local')""",
                (
                    file_id,
                    final_name,  # P9-FIX: Use auto-renamed name
                    original_filename,
                    file_format,
                    source_language,
                    target_language,
                    offline_project_id,  # P9-ARCH: Use Offline Storage project
                    folder_id,  # P9-FIX: Place in specified folder (or NULL for root)
                    extra_json,
                    now,
                    now,
                )
            )
            await conn.commit()
            folder_info = f", folder_id={folder_id}" if folder_id else " (at root)"
            logger.info(f"P9-FIX: Created local file '{final_name}' in Offline Storage (id={file_id}{folder_info})")
            # P9-FIX: Return both id and name (name may be auto-renamed)
            return {"id": file_id, "name": final_name, "folder_id": folder_id}

    async def add_rows_to_local_file(self, file_id: int, rows: List[Dict]):
        """
        P9: Add rows to a local file in Offline Storage.

        Rows are created with sync_status='new' since they don't exist on server.
        """
        import time

        async with self._get_async_connection() as conn:
            for i, row in enumerate(rows):
                # Use negative row IDs to avoid conflicts
                # Fix: Negate AFTER modulo (Python modulo with positive divisor returns positive)
                row_id = -(int(time.time() * 1000 + i) % 1000000000)

                extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
                now = datetime.now().isoformat()

                await conn.execute(
                    """INSERT INTO offline_rows
                       (id, server_id, file_id, server_file_id, row_num, string_id,
                        source, target, memo, status, extra_data, created_at, updated_at,
                        downloaded_at, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'new')""",
                    (
                        row_id,
                        file_id,
                        row.get("row_num", i + 1),
                        row.get("string_id"),
                        row.get("source", ""),
                        row.get("target", ""),
                        row.get("memo", ""),
                        row.get("status", "normal"),
                        extra_data,
                        now,
                        now,
                    )
                )

            # Update file row count
            await conn.execute(
                "UPDATE offline_files SET row_count = row_count + ? WHERE id = ?",
                (len(rows), file_id)
            )
            await conn.commit()
            logger.info(f"Added {len(rows)} rows to local file {file_id}")

    async def update_row_in_local_file(self, row_id: int, target: str = None, memo: str = None, status: str = None) -> bool:
        """
        P9: Update a row in a local file (Offline Storage).

        Unlike update_row() for synced files, this doesn't set sync_status='modified'
        because local files don't have a server counterpart to sync with.
        """
        async with self._get_async_connection() as conn:
            # Verify row exists and belongs to a local file
            cursor = await conn.execute(
                """SELECT r.id, f.sync_status as file_sync_status
                   FROM offline_rows r
                   JOIN offline_files f ON r.file_id = f.id
                   WHERE r.id = ?""",
                (row_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Row {row_id} not found")
                return False

            if row["file_sync_status"] != "local":
                logger.warning(f"Row {row_id} is not in a local file - use update_row() instead")
                return False

            # Build update
            updates = []
            params = []
            if target is not None:
                updates.append("target = ?")
                params.append(target)
            if memo is not None:
                updates.append("memo = ?")
                params.append(memo)
            if status is not None:
                updates.append("status = ?")
                params.append(status)

            if not updates:
                return True  # Nothing to update

            updates.append("updated_at = datetime('now')")
            params.append(row_id)

            await conn.execute(
                f"UPDATE offline_rows SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await conn.commit()
            logger.info(f"Updated row {row_id} in local file")
            return True

    async def delete_local_file(self, file_id: int, permanent: bool = False) -> bool:
        """
        P9-BIN-001: Delete a local file from Offline Storage.

        Only works for local files (sync_status='local').
        By default, moves to trash (soft delete). Use permanent=True for hard delete.
        Returns True if deleted, False if file not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify file is local before deleting
            cursor = await conn.execute(
                "SELECT * FROM offline_files WHERE id = ?",
                (file_id,)
            )
            file_row = await cursor.fetchone()

            if not file_row:
                logger.warning(f"Cannot delete: file {file_id} not found")
                return False

            if file_row["sync_status"] != "local":
                logger.warning(f"Cannot delete: file {file_id} is not local (status={file_row['sync_status']})")
                return False

            if not permanent:
                # P9-BIN-001: Soft delete - serialize and move to trash
                file_data = await self._serialize_local_file_for_trash_async(conn, file_id)
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()

                await conn.execute(
                    """INSERT INTO offline_trash
                       (item_type, item_id, item_name, item_data, parent_folder_id, expires_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'trashed')""",
                    ('local-file', file_id, file_row['name'], json.dumps(file_data),
                     file_row['folder_id'], expires_at)
                )
                logger.info(f"Moved local file {file_id} ('{file_row['name']}') to trash")

            # Delete rows first (cascade)
            await conn.execute("DELETE FROM offline_rows WHERE file_id = ?", (file_id,))
            # Delete file
            await conn.execute("DELETE FROM offline_files WHERE id = ?", (file_id,))
            await conn.commit()

            action = "permanently deleted" if permanent else "moved to trash"
            logger.info(f"Local file {file_id} {action}")
            return True

    async def _serialize_local_file_for_trash_async(self, conn, file_id: int) -> dict:
        """P9-BIN-001: Serialize a local file and its rows for trash storage."""
        cursor = await conn.execute(
            "SELECT * FROM offline_files WHERE id = ?",
            (file_id,)
        )
        file_row = await cursor.fetchone()

        cursor = await conn.execute(
            "SELECT * FROM offline_rows WHERE file_id = ? ORDER BY row_num",
            (file_id,)
        )
        rows = await cursor.fetchall()

        return {
            "file": dict(file_row),
            "rows": [dict(r) for r in rows]
        }

    async def rename_local_file(self, file_id: int, new_name: str) -> bool:
        """
        P9: Rename a local file in Offline Storage.

        Only works for local files (sync_status='local').
        Returns True if renamed, False if file not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify file is local before renaming
            cursor = await conn.execute(
                "SELECT sync_status FROM offline_files WHERE id = ?",
                (file_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Cannot rename: file {file_id} not found")
                return False

            if row["sync_status"] != "local":
                logger.warning(f"Cannot rename: file {file_id} is not local (status={row['sync_status']})")
                return False

            now = datetime.now().isoformat()
            await conn.execute(
                "UPDATE offline_files SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, now, file_id)
            )
            await conn.commit()
            logger.info(f"Renamed local file {file_id} to '{new_name}'")
            return True

    async def move_local_file(self, file_id: int, target_folder_id: int = None) -> bool:
        """
        P9: Move a local file to a different folder within Offline Storage.

        Only works for local files (sync_status='local').
        target_folder_id can be:
        - None: Move to root of Offline Storage
        - int: Move into the specified local folder

        Returns True if moved, False if file not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify file is local before moving
            cursor = await conn.execute(
                "SELECT sync_status, name FROM offline_files WHERE id = ?",
                (file_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Cannot move: file {file_id} not found")
                return False

            if row["sync_status"] != "local":
                logger.warning(f"Cannot move: file {file_id} is not local (status={row['sync_status']})")
                return False

            # Verify target folder exists and is local (if specified)
            if target_folder_id is not None:
                cursor = await conn.execute(
                    "SELECT sync_status FROM offline_folders WHERE id = ?",
                    (target_folder_id,)
                )
                folder_row = await cursor.fetchone()

                if not folder_row:
                    logger.warning(f"Cannot move: target folder {target_folder_id} not found")
                    return False

                if folder_row["sync_status"] != "local":
                    logger.warning(f"Cannot move: target folder {target_folder_id} is not local")
                    return False

            now = datetime.now().isoformat()
            await conn.execute(
                "UPDATE offline_files SET folder_id = ?, updated_at = ? WHERE id = ?",
                (target_folder_id, now, file_id)
            )
            await conn.commit()
            target_desc = f"folder {target_folder_id}" if target_folder_id else "root"
            logger.info(f"Moved local file {file_id} ('{row['name']}') to {target_desc}")
            return True

    async def move_local_folder(self, folder_id: int, target_parent_id: int = None) -> bool:
        """
        P9: Move a local folder to a different parent folder within Offline Storage.

        Only works for local folders (sync_status='local').
        target_parent_id can be:
        - None: Move to root of Offline Storage
        - int: Move into the specified local folder

        Returns True if moved, False if folder not found or not local.
        """
        async with self._get_async_connection() as conn:
            # Verify folder is local before moving
            cursor = await conn.execute(
                "SELECT sync_status, name FROM offline_folders WHERE id = ?",
                (folder_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Cannot move: folder {folder_id} not found")
                return False

            if row["sync_status"] != "local":
                logger.warning(f"Cannot move: folder {folder_id} is not local (status={row['sync_status']})")
                return False

            # Prevent moving folder into itself or its descendants
            if target_parent_id is not None:
                if target_parent_id == folder_id:
                    logger.warning(f"Cannot move: folder {folder_id} cannot be moved into itself")
                    return False

                # Check if target is a descendant of this folder
                check_id = target_parent_id
                while check_id is not None:
                    cursor = await conn.execute(
                        "SELECT parent_id FROM offline_folders WHERE id = ?",
                        (check_id,)
                    )
                    check_row = await cursor.fetchone()
                    if not check_row:
                        break
                    if check_row["parent_id"] == folder_id:
                        logger.warning(f"Cannot move: folder {folder_id} cannot be moved into its descendant")
                        return False
                    check_id = check_row["parent_id"]

                # Verify target folder exists and is local
                cursor = await conn.execute(
                    "SELECT sync_status FROM offline_folders WHERE id = ?",
                    (target_parent_id,)
                )
                folder_row = await cursor.fetchone()

                if not folder_row:
                    logger.warning(f"Cannot move: target folder {target_parent_id} not found")
                    return False

                if folder_row["sync_status"] != "local":
                    logger.warning(f"Cannot move: target folder {target_parent_id} is not local")
                    return False

            await conn.execute(
                "UPDATE offline_folders SET parent_id = ? WHERE id = ?",
                (target_parent_id, folder_id)
            )
            await conn.commit()
            target_desc = f"folder {target_parent_id}" if target_parent_id else "root"
            logger.info(f"Moved local folder {folder_id} ('{row['name']}') to {target_desc}")
            return True

    # =========================================================================
    # Utility
    # =========================================================================

    async def get_stats(self) -> Dict[str, int]:
        """Get offline storage statistics."""
        async with self._get_async_connection() as conn:
            stats = {}
            for table in ["offline_platforms", "offline_projects", "offline_folders",
                         "offline_files", "offline_rows"]:
                cursor = await conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                row = await cursor.fetchone()
                stats[table.replace("offline_", "")] = row["count"]

            stats["pending_changes"] = await self.get_pending_change_count()
            return stats

    async def clear_all(self):
        """Clear all offline data (use with caution!)."""
        async with self._get_async_connection() as conn:
            for table in ["local_changes", "offline_rows", "offline_files",
                         "offline_folders", "offline_projects", "offline_platforms"]:
                await conn.execute(f"DELETE FROM {table}")
            await conn.commit()
            logger.warning("All offline data cleared")

    async def search_local_files(self, query: str) -> List[Dict]:
        """
        P9: Search ALL files in SQLite by name.

        Used by the search endpoint in offline mode.
        Searches all files: local, synced, and modified.
        """
        async with self._get_async_connection() as conn:
            # Case-insensitive LIKE search
            search_term = f"%{query}%"
            cursor = await conn.execute(
                """SELECT id, name, format, row_count, created_at, sync_status
                   FROM offline_files
                   WHERE name LIKE ? COLLATE NOCASE
                   ORDER BY name
                   LIMIT 50""",
                (search_term,)
            )
            rows = await cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "format": row["format"],
                    "row_count": row["row_count"],
                    "created_at": row["created_at"],
                    "sync_status": row["sync_status"]
                }
                for row in rows
            ]

    async def search_all(self, query: str) -> Dict[str, List[Dict]]:
        """
        P9: Search ALL offline data - platforms, projects, folders, files.
        Returns dict with keys: platforms, projects, folders, files
        """
        search_term = f"%{query}%"
        result = {"platforms": [], "projects": [], "folders": [], "files": []}

        async with self._get_async_connection() as conn:
            # Platforms
            cursor = await conn.execute(
                "SELECT id, name FROM offline_platforms WHERE name LIKE ? COLLATE NOCASE LIMIT 20",
                (search_term,)
            )
            for row in await cursor.fetchall():
                result["platforms"].append({"id": row["id"], "name": row["name"]})

            # Projects with platform name
            cursor = await conn.execute(
                """SELECT p.id, p.name, p.platform_id, pl.name as platform_name
                   FROM offline_projects p
                   LEFT JOIN offline_platforms pl ON p.platform_id = pl.id
                   WHERE p.name LIKE ? COLLATE NOCASE LIMIT 20""",
                (search_term,)
            )
            for row in await cursor.fetchall():
                result["projects"].append({
                    "id": row["id"], "name": row["name"],
                    "platform_id": row["platform_id"], "platform_name": row["platform_name"]
                })

            # Folders with project name
            cursor = await conn.execute(
                """SELECT f.id, f.name, f.project_id, p.name as project_name
                   FROM offline_folders f
                   LEFT JOIN offline_projects p ON f.project_id = p.id
                   WHERE f.name LIKE ? COLLATE NOCASE LIMIT 20""",
                (search_term,)
            )
            for row in await cursor.fetchall():
                result["folders"].append({
                    "id": row["id"], "name": row["name"],
                    "project_id": row["project_id"], "project_name": row["project_name"]
                })

            # Files with project name
            cursor = await conn.execute(
                """SELECT f.id, f.name, f.sync_status, f.project_id, p.name as project_name
                   FROM offline_files f
                   LEFT JOIN offline_projects p ON f.project_id = p.id
                   WHERE f.name LIKE ? COLLATE NOCASE LIMIT 50""",
                (search_term,)
            )
            for row in await cursor.fetchall():
                result["files"].append({
                    "id": row["id"], "name": row["name"],
                    "sync_status": row["sync_status"],
                    "project_id": row["project_id"], "project_name": row["project_name"]
                })

        return result

    # =========================================================================
    # P9-BIN-001: Local Trash Operations
    # =========================================================================

    async def list_local_trash(self) -> List[Dict]:
        """P9-BIN-001: List all items in local trash (not expired)."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                """SELECT id, item_type, item_id, item_name, parent_folder_id,
                          deleted_at, expires_at, status
                   FROM offline_trash
                   WHERE status = 'trashed'
                   ORDER BY deleted_at DESC"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_local_trash_item(self, trash_id: int) -> Optional[Dict]:
        """P9-BIN-001: Get a specific trash item."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_trash WHERE id = ?",
                (trash_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def restore_from_local_trash(self, trash_id: int) -> dict:
        """
        P9-BIN-001: Restore an item from local trash.

        Returns dict with item_type and item_id, or None if not found/failed.
        """
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_trash WHERE id = ? AND status = 'trashed'",
                (trash_id,)
            )
            trash_row = await cursor.fetchone()

            if not trash_row:
                logger.warning(f"Cannot restore: trash item {trash_id} not found or not trashed")
                return None

            item_type = trash_row['item_type']
            item_id = trash_row['item_id']
            item_data = json.loads(trash_row['item_data'])

            try:
                if item_type == 'local-file':
                    await self._restore_local_file_async(conn, item_data)
                elif item_type == 'local-folder':
                    await self._restore_local_folder_async(conn, item_data)
                else:
                    logger.error(f"Unknown trash item type: {item_type}")
                    return None

                # Mark as restored
                await conn.execute(
                    "UPDATE offline_trash SET status = 'restored' WHERE id = ?",
                    (trash_id,)
                )
                await conn.commit()
                logger.info(f"Restored {item_type} '{trash_row['item_name']}' from trash")
                return {
                    "item_type": item_type,
                    "item_id": item_id
                }

            except Exception as e:
                logger.error(f"Failed to restore from trash: {e}")
                return None

    async def _restore_local_file_async(self, conn, item_data: dict):
        """P9-BIN-001: Restore a local file from trash data."""
        file_info = item_data['file']
        rows_info = item_data['rows']

        # Re-insert file
        await conn.execute(
            """INSERT INTO offline_files
               (id, server_id, name, original_filename, format, row_count,
                source_language, target_language, project_id, server_project_id,
                folder_id, server_folder_id, extra_data, created_at, updated_at,
                downloaded_at, sync_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_info['id'], file_info['server_id'], file_info['name'],
             file_info['original_filename'], file_info['format'], file_info['row_count'],
             file_info['source_language'], file_info['target_language'],
             file_info['project_id'], file_info['server_project_id'],
             file_info['folder_id'], file_info['server_folder_id'],
             file_info['extra_data'], file_info['created_at'], file_info['updated_at'],
             file_info['downloaded_at'], file_info['sync_status'])
        )

        # Re-insert rows
        for row in rows_info:
            await conn.execute(
                """INSERT INTO offline_rows
                   (id, server_id, file_id, server_file_id, row_num, string_id,
                    source, target, memo, status, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row['id'], row['server_id'], row['file_id'], row['server_file_id'],
                 row['row_num'], row['string_id'], row['source'], row['target'],
                 row['memo'], row['status'], row['extra_data'], row['created_at'],
                 row['updated_at'], row['downloaded_at'], row['sync_status'])
            )

    async def _restore_local_folder_async(self, conn, item_data: dict):
        """P9-BIN-001: Restore a local folder from trash data (recursive)."""
        folder_info = item_data['folder']
        files_data = item_data.get('files', [])
        subfolders_data = item_data.get('subfolders', [])

        # Re-insert folder
        await conn.execute(
            """INSERT INTO offline_folders
               (id, server_id, name, project_id, server_project_id,
                parent_id, server_parent_id, created_at, downloaded_at, sync_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (folder_info['id'], folder_info['server_id'], folder_info['name'],
             folder_info['project_id'], folder_info['server_project_id'],
             folder_info['parent_id'], folder_info['server_parent_id'],
             folder_info['created_at'], folder_info['downloaded_at'], folder_info['sync_status'])
        )

        # Restore files in this folder
        for file_data in files_data:
            await self._restore_local_file_async(conn, file_data)

        # Restore subfolders recursively
        for subfolder_data in subfolders_data:
            await self._restore_local_folder_async(conn, subfolder_data)

    async def permanent_delete_from_local_trash(self, trash_id: int) -> bool:
        """P9-BIN-001: Permanently delete an item from local trash."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT item_name FROM offline_trash WHERE id = ?",
                (trash_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            await conn.execute("DELETE FROM offline_trash WHERE id = ?", (trash_id,))
            await conn.commit()
            logger.info(f"Permanently deleted '{row['item_name']}' from local trash")
            return True

    async def empty_local_trash(self) -> int:
        """P9-BIN-001: Empty all items from local trash. Returns count of deleted items."""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM offline_trash WHERE status = 'trashed'"
            )
            count = cursor.rowcount
            await conn.commit()
            logger.info(f"Emptied local trash: {count} items permanently deleted")
            return count

    async def purge_expired_local_trash(self) -> int:
        """P9-BIN-001: Delete expired trash items (past 30 days). Returns count deleted."""
        async with self._get_async_connection() as conn:
            now = datetime.now().isoformat()
            cursor = await conn.execute(
                """DELETE FROM offline_trash
                   WHERE status = 'trashed' AND expires_at < ?""",
                (now,)
            )
            count = cursor.rowcount
            await conn.commit()
            if count > 0:
                logger.info(f"Purged {count} expired items from local trash")
            return count


# Singleton instance
_offline_db: Optional[OfflineDatabase] = None


def get_offline_db() -> OfflineDatabase:
    """Get the singleton offline database instance."""
    global _offline_db
    if _offline_db is None:
        _offline_db = OfflineDatabase()
    return _offline_db
