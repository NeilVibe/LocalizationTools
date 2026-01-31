"""
TMLoader - Unified TM Entry Loading for Pretranslation.

LIMIT-002: Enables TM pretranslation in offline mode.

This module provides a unified interface for loading TM entries from either
PostgreSQL (online) or SQLite (offline), automatically detecting the correct
source based on TM ID and configuration.

Usage:
    from server.tools.shared.tm_loader import TMLoader

    # Async (recommended for routes)
    entries = await TMLoader.load_entries_async(tm_id)

    # Sync (for EmbeddingsManager compatibility - MUST be called from sync context)
    entries = TMLoader.load_entries(tm_id)

WARNING: load_entries() must NOT be called from async code (deadlock risk).
         Always use load_entries_async() in async contexts.
"""

import asyncio
from typing import List, Dict, Any, Literal
from loguru import logger


class TMLoader:
    """
    Unified TM entry loader for PostgreSQL and SQLite.

    Automatically detects the correct database source based on:
    - TM ID sign (negative = SQLite offline mode)
    - ACTIVE_DATABASE_TYPE config (for server mode)
    """

    @staticmethod
    def _detect_source(tm_id: int) -> Literal["postgresql", "sqlite_offline", "sqlite_server"]:
        """
        Detect which database source to use.

        Args:
            tm_id: Translation Memory ID

        Returns:
            "postgresql" - Online mode with PostgreSQL
            "sqlite_offline" - Offline mode with SQLite (tm_id < 0)
            "sqlite_server" - Server running with SQLite backend
        """
        # Negative IDs are always SQLite offline
        if tm_id < 0:
            return "sqlite_offline"

        # Check server configuration
        try:
            from server import config
            if getattr(config, 'ACTIVE_DATABASE_TYPE', None) == "sqlite":
                return "sqlite_server"
        except ImportError as e:
            logger.debug(f"[TMLoader] Could not import config: {e}")

        return "postgresql"

    @staticmethod
    async def load_entries_async(tm_id: int) -> List[Dict[str, Any]]:
        """
        Load all TM entries asynchronously.

        Args:
            tm_id: Translation Memory ID

        Returns:
            List of entry dicts with source_text, target_text, etc.
        """
        source = TMLoader._detect_source(tm_id)
        logger.info(f"[TMLoader] Loading TM {tm_id} from {source}")

        if source == "postgresql":
            return await TMLoader._load_from_postgresql(tm_id)
        else:
            return await TMLoader._load_from_sqlite(tm_id, source)

    @staticmethod
    def load_entries(tm_id: int) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for EmbeddingsManager compatibility.

        WARNING: This method MUST be called from a synchronous context only.
        Calling from async code will cause deadlock. Use load_entries_async() instead.

        Args:
            tm_id: Translation Memory ID

        Returns:
            List of entry dicts
        """
        # Check if we're in an async context - warn and fail fast
        try:
            asyncio.get_running_loop()
            # We're in an async context - this is dangerous!
            logger.warning(
                "[TMLoader] load_entries() called from async context! "
                "This may cause deadlock. Use load_entries_async() instead."
            )
            # Still try to run, but in a thread to avoid deadlock
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    TMLoader.load_entries_async(tm_id)
                )
                return future.result(timeout=120)
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            return asyncio.run(TMLoader.load_entries_async(tm_id))

    @staticmethod
    async def _load_from_postgresql(tm_id: int) -> List[Dict[str, Any]]:
        """Load entries from PostgreSQL using async session."""
        try:
            from server.utils.dependencies import get_async_db
            from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository

            # get_async_db is an async generator - iterate once
            async for db in get_async_db():
                repo = PostgreSQLTMRepository(db, user={})
                entries = await repo.get_all_entries(tm_id)
                logger.info(f"[TMLoader] Loaded {len(entries)} entries from PostgreSQL TM {tm_id}")
                return entries
                # Generator cleanup handles session close automatically

            return []
        except Exception as e:
            logger.error(f"[TMLoader] PostgreSQL load failed for TM {tm_id}: {e}")
            return []

    @staticmethod
    async def _load_from_sqlite(
        tm_id: int,
        source: Literal["sqlite_offline", "sqlite_server"]
    ) -> List[Dict[str, Any]]:
        """Load entries from SQLite using appropriate schema mode."""
        try:
            from server.repositories.sqlite.tm_repo import SQLiteTMRepository
            from server.repositories.sqlite.base import SchemaMode

            schema = SchemaMode.OFFLINE if source == "sqlite_offline" else SchemaMode.SERVER
            repo = SQLiteTMRepository(schema_mode=schema)
            entries = await repo.get_all_entries(tm_id)
            logger.info(f"[TMLoader] Loaded {len(entries)} entries from SQLite TM {tm_id} ({source})")
            return entries
        except Exception as e:
            logger.error(f"[TMLoader] SQLite load failed for TM {tm_id}: {e}")
            return []

    @staticmethod
    def clear_cache():
        """Clear TM index cache in SQLite repository."""
        try:
            from server.repositories.sqlite.tm_repo import clear_tm_index_cache
            clear_tm_index_cache()
            logger.info("[TMLoader] Cleared TM index cache")
        except ImportError:
            pass
