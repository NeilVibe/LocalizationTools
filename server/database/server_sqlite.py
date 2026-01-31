"""
Server SQLite Database - Fallback Database for Server Mode.

ARCH-001: This module provides a SQLite database connection for when the server
falls back to SQLite mode (when PostgreSQL is unavailable).

Unlike OfflineDatabase (which uses offline_* tables), this connects to the
server's SQLite that uses ldm_* tables - the same schema as PostgreSQL.

The key difference:
- OfflineDatabase: Electron app's local offline storage (offline_platforms, etc.)
- ServerSQLiteDatabase: Server fallback when PostgreSQL unavailable (ldm_platforms, etc.)
"""

import sqlite3
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from loguru import logger

from server import config


class ServerSQLiteDatabase:
    """
    SQLite database connection for server fallback mode.

    Uses the same ldm_* tables as PostgreSQL, not the offline_* tables.
    The schema is initialized by db_setup.py when SQLite mode is detected,
    so this class only needs to provide the connection.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize server SQLite database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses config.SQLITE_DATABASE_PATH.
        """
        if db_path is None:
            db_path = str(config.SQLITE_DATABASE_PATH)

        self.db_path = db_path
        logger.debug(f"[SERVER-SQLITE] Using database: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get SYNC database connection with row factory.

        DEPRECATED: Use _get_async_connection() for async operations.
        Kept for backward compatibility.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @asynccontextmanager
    async def _get_async_connection(self):
        """
        Get ASYNC database connection with row factory.

        This is the same interface as OfflineDatabase, so SQLite repositories
        can use either database with the same code pattern.

        Usage:
            async with self._get_async_connection() as conn:
                cursor = await conn.execute("SELECT * FROM ldm_projects WHERE id = ?", (id,))
                row = await cursor.fetchone()
        """
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()


# Module-level singleton (matches offline.py pattern)
_server_sqlite_db: Optional[ServerSQLiteDatabase] = None


def get_server_sqlite_db() -> ServerSQLiteDatabase:
    """
    Get the server SQLite database singleton.

    This mirrors get_offline_db() from server.database.offline but for
    server-mode SQLite (ldm_* tables instead of offline_* tables).

    Returns:
        ServerSQLiteDatabase singleton instance.
    """
    global _server_sqlite_db
    if _server_sqlite_db is None:
        _server_sqlite_db = ServerSQLiteDatabase()
    return _server_sqlite_db


def reset_server_sqlite_db():
    """Reset the server SQLite database singleton (for testing)."""
    global _server_sqlite_db
    _server_sqlite_db = None
