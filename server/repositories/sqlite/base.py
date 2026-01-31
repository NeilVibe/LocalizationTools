"""
SQLite Repository Base - Schema-Aware Infrastructure.

ARCH-001: This module provides TRUE layer abstraction for SQLite repositories.
Repositories can operate in two modes:
- OFFLINE: Uses offline_* tables (Electron app offline mode)
- SERVER: Uses ldm_* tables (server SQLite fallback when PostgreSQL unavailable)

The factory chooses the mode. Repositories stay PURE - no config checks inside.
"""

from enum import Enum
from typing import Optional
from loguru import logger


class SchemaMode(Enum):
    """
    Schema mode determines which table prefix to use.

    OFFLINE: Uses offline_* tables (offline_platforms, offline_projects, etc.)
             This is the Electron app's local SQLite database for offline work.

    SERVER: Uses ldm_* tables (ldm_platforms, ldm_projects, etc.)
            This is the server's SQLite fallback when PostgreSQL is unavailable.
    """
    OFFLINE = "offline"
    SERVER = "server"


# Table name mapping from base name to actual table names
# Format: base_name -> (offline_name, server_name)
TABLE_MAP = {
    "platforms": ("offline_platforms", "ldm_platforms"),
    "projects": ("offline_projects", "ldm_projects"),
    "folders": ("offline_folders", "ldm_folders"),
    "files": ("offline_files", "ldm_files"),
    "rows": ("offline_rows", "ldm_rows"),
    "tms": ("offline_tms", "ldm_translation_memories"),
    "tm_entries": ("offline_tm_entries", "ldm_tm_entries"),
    "tm_assignments": ("offline_tm_assignments", "ldm_tm_assignments"),
    "qa_results": ("offline_qa_results", "ldm_qa_results"),
    "trash": ("offline_trash", "ldm_trash"),
}


class SQLiteBaseRepository:
    """
    Base class for all SQLite repositories with schema-aware table names.

    Subclasses inherit:
    - schema_mode: Which schema to use (OFFLINE or SERVER)
    - db: Lazy-loaded database connection
    - _table(): Method to get the correct table name for current mode

    Usage:
        class SQLiteProjectRepository(SQLiteBaseRepository, ProjectRepository):
            def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
                super().__init__(schema_mode)

            async def get(self, project_id: int):
                async with self.db._get_async_connection() as conn:
                    cursor = await conn.execute(
                        f"SELECT * FROM {self._table('projects')} WHERE id = ?",
                        (project_id,)
                    )
                    ...
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        """
        Initialize with schema mode.

        Args:
            schema_mode: OFFLINE for offline_* tables, SERVER for ldm_* tables.
                        Defaults to OFFLINE for backwards compatibility.
        """
        self.schema_mode = schema_mode
        self._db = None
        logger.debug(f"[SQLITE-BASE] Initialized with schema_mode={schema_mode.value}")

    @property
    def db(self):
        """
        Lazy-load database connection based on schema mode.

        OFFLINE mode: Uses OfflineDatabase (Electron app's local SQLite)
        SERVER mode: Uses ServerSQLiteDatabase (server fallback SQLite)
        """
        if self._db is None:
            if self.schema_mode == SchemaMode.OFFLINE:
                from server.database.offline import get_offline_db
                self._db = get_offline_db()
            else:
                from server.database.server_sqlite import get_server_sqlite_db
                self._db = get_server_sqlite_db()
        return self._db

    def _table(self, base_name: str) -> str:
        """
        Get the correct table name for the current schema mode.

        Args:
            base_name: Base table name (e.g., "projects", "files", "rows")

        Returns:
            Full table name with correct prefix:
            - OFFLINE: "offline_projects"
            - SERVER: "ldm_projects"

        Example:
            sql = f"SELECT * FROM {self._table('projects')} WHERE id = ?"
        """
        if base_name in TABLE_MAP:
            offline_name, server_name = TABLE_MAP[base_name]
            if self.schema_mode == SchemaMode.OFFLINE:
                return offline_name
            else:
                return server_name
        else:
            # Fallback: add prefix based on mode
            if self.schema_mode == SchemaMode.OFFLINE:
                fallback = f"offline_{base_name}"
            else:
                fallback = f"ldm_{base_name}"
            logger.warning(f"[SQLITE-BASE] Table '{base_name}' not in TABLE_MAP, using fallback: {fallback}")
            return fallback

    def _has_column(self, column_name: str) -> bool:
        """
        Check if a column exists in current schema mode.

        Some columns only exist in OFFLINE mode (e.g., sync_status, server_id).
        Use this to conditionally include columns in queries.

        Args:
            column_name: Name of the column to check

        Returns:
            True if column exists in current schema mode
        """
        # Columns that only exist in OFFLINE mode
        OFFLINE_ONLY_COLUMNS = {
            "server_id",
            "sync_status",
            "downloaded_at",
            "server_platform_id",
            "server_project_id",
            "server_file_id",
            "server_folder_id",
            "server_tm_id",
            "server_parent_id",
        }

        if column_name in OFFLINE_ONLY_COLUMNS:
            return self.schema_mode == SchemaMode.OFFLINE

        # All other columns exist in both modes
        return True
