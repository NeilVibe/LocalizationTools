"""
EMB-003: TM Maintenance Manager.

Login-time stale index check and background sync management.
Works with BOTH online (PostgreSQL) and offline (SQLite) modes
using the Repository Pattern.

Architecture:
- TMMaintenanceManager uses repositories (never direct DB access)
- on_user_login() is called after successful auth
- find_stale_tms() compares indexed_at vs updated_at
- background_sync() queues TMs for async sync
"""

import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from .schemas import StaleTMInfo, MaintenanceResult, SyncQueueItem


# Module-level sync queue (thread-safe)
_sync_queue: List[SyncQueueItem] = []
_sync_queue_lock = threading.Lock()
_sync_in_progress: Dict[int, bool] = {}  # tm_id -> is_syncing


def get_sync_queue_status() -> Dict[str, Any]:
    """Get current sync queue status (for monitoring)."""
    with _sync_queue_lock:
        return {
            "queue_length": len(_sync_queue),
            "items": [item.model_dump() for item in _sync_queue],
            "in_progress": list(_sync_in_progress.keys())
        }


class TMMaintenanceManager:
    """
    TM Maintenance Manager.

    EMB-003: Handles login-time stale index checks and background sync.

    Usage:
        # After successful login (in auth routes)
        manager = TMMaintenanceManager(tm_repo, user)
        result = await manager.on_user_login()

        # Result contains list of stale TMs that were queued for sync
        for tm in result.stale_tms:
            logger.info(f"TM {tm.tm_name} queued for sync")

    Repository Pattern:
        This manager uses TMRepository for ALL database operations.
        It never imports database models or sessions directly.
        This ensures it works in both online and offline modes.
    """

    def __init__(
        self,
        tm_repo,  # TMRepository - PostgreSQL or SQLite
        user: dict,
        data_dir: Optional[Path] = None
    ):
        """
        Initialize TMMaintenanceManager.

        Args:
            tm_repo: TMRepository instance (from factory)
            user: Current user dict (from auth)
            data_dir: Path to TM index storage (default: server/data/ldm_tm)
        """
        self.tm_repo = tm_repo
        self.user = user
        self.user_id = user.get("user_id", 0)
        self.username = user.get("username", "unknown")

        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "ldm_tm"

    # =========================================================================
    # Public API
    # =========================================================================

    async def on_user_login(self, auto_queue: bool = True) -> MaintenanceResult:
        """
        Called after user successfully logs in.

        Checks all accessible TMs for stale indexes and optionally
        queues them for background sync.

        Args:
            auto_queue: If True, automatically queue stale TMs for sync

        Returns:
            MaintenanceResult with list of stale TMs
        """
        logger.info(f"[EMB-003] Login-time TM check for user {self.username} (id={self.user_id})")

        try:
            # Find all stale TMs accessible to this user
            stale_tms = await self.find_stale_tms()

            result = MaintenanceResult(
                user_id=self.user_id,
                stale_tms=stale_tms,
                total_stale=len(stale_tms),
                queued_for_sync=0
            )

            if stale_tms and auto_queue:
                # Queue stale TMs for background sync
                for tm in stale_tms:
                    queued = self.queue_background_sync(
                        tm_id=tm.tm_id,
                        reason="login_check",
                        priority=1  # Lower priority than manual sync
                    )
                    if queued:
                        result.queued_for_sync += 1

                logger.info(
                    f"[EMB-003] Queued {result.queued_for_sync}/{result.total_stale} "
                    f"stale TMs for background sync"
                )

            return result

        except Exception as e:
            logger.error(f"[EMB-003] Login-time TM check failed: {e}")
            # Don't fail login on maintenance errors
            return MaintenanceResult(
                user_id=self.user_id,
                stale_tms=[],
                total_stale=0,
                queued_for_sync=0
            )

    async def find_stale_tms(self, tm_ids: Optional[List[int]] = None) -> List[StaleTMInfo]:
        """
        Find TMs with stale indexes.

        Compares indexed_at (from local metadata.json) vs updated_at (from DB).
        A TM is stale if:
        - It has never been indexed (no metadata.json)
        - indexed_at < updated_at (DB was modified after last sync)
        - Entry counts don't match

        Args:
            tm_ids: Optional list of specific TMs to check.
                    If None, checks all TMs accessible to user.

        Returns:
            List of StaleTMInfo for stale TMs
        """
        stale_tms: List[StaleTMInfo] = []

        try:
            # Get TMs to check
            if tm_ids:
                # Check specific TMs
                tms = []
                for tm_id in tm_ids:
                    tm = await self.tm_repo.get(tm_id)
                    if tm:
                        tms.append(tm)
            else:
                # Check all accessible TMs
                tms = await self.tm_repo.get_all()

            logger.debug(f"[EMB-003] Checking {len(tms)} TMs for staleness")

            for tm in tms:
                stale_info = await self._check_tm_staleness(tm)
                if stale_info:
                    stale_tms.append(stale_info)

            logger.info(f"[EMB-003] Found {len(stale_tms)} stale TMs out of {len(tms)} checked")

        except Exception as e:
            logger.error(f"[EMB-003] Error finding stale TMs: {e}")

        return stale_tms

    def queue_background_sync(
        self,
        tm_id: int,
        reason: str = "stale",
        priority: int = 0
    ) -> bool:
        """
        Queue a TM for background sync.

        Does NOT block - adds to queue and returns immediately.
        Background worker processes queue asynchronously.

        Args:
            tm_id: TM ID to sync
            reason: Why this sync was requested
            priority: Lower = higher priority (0 is highest)

        Returns:
            True if queued, False if already in queue/syncing
        """
        with _sync_queue_lock:
            # Check if already queued or syncing
            if tm_id in _sync_in_progress:
                logger.debug(f"[EMB-003] TM {tm_id} already syncing, skipping queue")
                return False

            for item in _sync_queue:
                if item.tm_id == tm_id:
                    logger.debug(f"[EMB-003] TM {tm_id} already in queue, skipping")
                    return False

            # Add to queue
            queue_item = SyncQueueItem(
                tm_id=tm_id,
                user_id=self.user_id,
                priority=priority,
                reason=reason
            )
            _sync_queue.append(queue_item)

            # Sort by priority (lower first)
            _sync_queue.sort(key=lambda x: x.priority)

            logger.info(f"[EMB-003] Queued TM {tm_id} for background sync (reason={reason})")
            return True

    async def background_sync(self, tm_id: int) -> Dict[str, Any]:
        """
        Trigger background sync for a single TM.

        This is called by the background worker to actually perform the sync.
        Uses TMSyncManager from indexing module.

        Args:
            tm_id: TM ID to sync

        Returns:
            Sync result dict
        """
        from server.tools.ldm.indexing.sync_manager import TMSyncManager
        from server.utils.dependencies import get_db

        logger.info(f"[EMB-003] Starting background sync for TM {tm_id}")

        # Mark as in progress
        _sync_in_progress[tm_id] = True

        try:
            # Get sync DB session (sync manager requires sync session)
            sync_db = next(get_db())
            try:
                sync_manager = TMSyncManager(sync_db, tm_id)
                result = await asyncio.to_thread(sync_manager.sync)

                logger.success(
                    f"[EMB-003] Background sync complete for TM {tm_id}: "
                    f"INSERT={result['stats']['insert']}, UPDATE={result['stats']['update']}"
                )
                return result

            finally:
                sync_db.close()

        except Exception as e:
            logger.error(f"[EMB-003] Background sync failed for TM {tm_id}: {e}")
            return {
                "tm_id": tm_id,
                "status": "error",
                "error": str(e)
            }

        finally:
            # Remove from in-progress
            _sync_in_progress.pop(tm_id, None)

            # Remove from queue if present
            with _sync_queue_lock:
                _sync_queue[:] = [item for item in _sync_queue if item.tm_id != tm_id]

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _check_tm_staleness(self, tm: Dict[str, Any]) -> Optional[StaleTMInfo]:
        """
        Check if a single TM's indexes are stale.

        Args:
            tm: TM dict from repository

        Returns:
            StaleTMInfo if stale, None if up-to-date
        """
        tm_id = tm.get("id")
        tm_name = tm.get("name", f"TM-{tm_id}")

        # Get local index metadata
        metadata = self._load_index_metadata(tm_id)

        # Get DB entry count
        db_entry_count = await self.tm_repo.count_entries(tm_id)

        # Parse timestamps
        indexed_at = None
        indexed_entry_count = 0

        if metadata:
            indexed_at_str = metadata.get("synced_at") or metadata.get("built_at")
            if indexed_at_str:
                try:
                    indexed_at = datetime.fromisoformat(indexed_at_str.replace('Z', '+00:00'))
                except Exception:
                    pass
            indexed_entry_count = metadata.get("entry_count", 0)

        # Parse DB updated_at
        updated_at = None
        tm_updated_at = tm.get("updated_at")
        if tm_updated_at:
            if isinstance(tm_updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(tm_updated_at.replace('Z', '+00:00'))
                except Exception:
                    pass
            elif isinstance(tm_updated_at, datetime):
                updated_at = tm_updated_at

        # Determine staleness
        is_stale = False
        status = "current"
        pending_changes = 0

        if indexed_at is None:
            # Never indexed
            is_stale = True
            status = "never_indexed"
            pending_changes = db_entry_count

        elif updated_at and updated_at.replace(tzinfo=None) > indexed_at.replace(tzinfo=None):
            # DB updated after last sync
            is_stale = True
            status = "stale"
            pending_changes = max(1, abs(db_entry_count - indexed_entry_count))

        elif db_entry_count != indexed_entry_count:
            # Entry count mismatch (sanity check)
            is_stale = True
            status = "stale"
            pending_changes = abs(db_entry_count - indexed_entry_count)

        if is_stale:
            return StaleTMInfo(
                tm_id=tm_id,
                tm_name=tm_name,
                indexed_at=indexed_at,
                updated_at=updated_at,
                entry_count=db_entry_count,
                indexed_entry_count=indexed_entry_count,
                pending_changes=pending_changes,
                status=status
            )

        return None

    def _load_index_metadata(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """
        Load index metadata from local storage.

        Args:
            tm_id: TM ID

        Returns:
            Metadata dict or None if not found
        """
        metadata_path = self.data_dir / str(tm_id) / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[EMB-003] Failed to load metadata for TM {tm_id}: {e}")
            return None


# =============================================================================
# Background Worker (optional - can be run in separate thread/process)
# =============================================================================

async def process_sync_queue(max_concurrent: int = 2):
    """
    Background worker to process the sync queue.

    Can be run as a startup task or in a separate process.

    Args:
        max_concurrent: Maximum concurrent syncs
    """
    logger.info(f"[EMB-003] Sync queue worker started (max_concurrent={max_concurrent})")

    while True:
        try:
            # Check queue
            items_to_process = []
            with _sync_queue_lock:
                # Get items not already syncing
                available = [
                    item for item in _sync_queue
                    if item.tm_id not in _sync_in_progress
                ]
                items_to_process = available[:max_concurrent]

            if items_to_process:
                # Process in parallel
                tasks = []
                for item in items_to_process:
                    # Create manager for this sync (minimal - no user context needed)
                    from server.repositories.sqlite.tm_repo import SQLiteTMRepository
                    from server.repositories.sqlite.base import SchemaMode

                    # Use SQLite repo for background sync (works offline)
                    tm_repo = SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)
                    manager = TMMaintenanceManager(
                        tm_repo=tm_repo,
                        user={"user_id": item.user_id, "username": "background_worker"}
                    )
                    tasks.append(manager.background_sync(item.tm_id))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Sleep before next check
            await asyncio.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"[EMB-003] Sync queue worker error: {e}")
            await asyncio.sleep(10)
