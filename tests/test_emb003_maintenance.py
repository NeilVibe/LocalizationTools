"""
EMB-003: Test TM Maintenance Manager.

Tests login-time stale index check functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from server.tools.ldm.maintenance import TMMaintenanceManager, StaleTMInfo, MaintenanceResult
from server.tools.ldm.maintenance.schemas import SyncQueueItem
from server.tools.ldm.maintenance.manager import (
    _sync_queue,
    _sync_queue_lock,
    get_sync_queue_status,
)


class TestStaleTMInfo:
    """Test StaleTMInfo schema."""

    def test_create_stale_info(self):
        """Test creating StaleTMInfo."""
        info = StaleTMInfo(
            tm_id=1,
            tm_name="Test TM",
            indexed_at=datetime.utcnow() - timedelta(hours=1),
            updated_at=datetime.utcnow(),
            entry_count=100,
            indexed_entry_count=90,
            pending_changes=10,
            status="stale"
        )

        assert info.tm_id == 1
        assert info.tm_name == "Test TM"
        assert info.pending_changes == 10
        assert info.status == "stale"

    def test_never_indexed_status(self):
        """Test never_indexed status."""
        info = StaleTMInfo(
            tm_id=2,
            tm_name="New TM",
            indexed_at=None,
            updated_at=datetime.utcnow(),
            entry_count=50,
            indexed_entry_count=0,
            pending_changes=50,
            status="never_indexed"
        )

        assert info.indexed_at is None
        assert info.status == "never_indexed"


class TestMaintenanceResult:
    """Test MaintenanceResult schema."""

    def test_create_result(self):
        """Test creating MaintenanceResult."""
        result = MaintenanceResult(
            user_id=1,
            stale_tms=[
                StaleTMInfo(tm_id=1, tm_name="TM1", entry_count=100, status="stale"),
                StaleTMInfo(tm_id=2, tm_name="TM2", entry_count=50, status="never_indexed"),
            ],
            total_stale=2,
            queued_for_sync=1
        )

        assert result.user_id == 1
        assert result.total_stale == 2
        assert result.queued_for_sync == 1
        assert len(result.stale_tms) == 2
        assert result.checked_at is not None


class TestSyncQueueItem:
    """Test SyncQueueItem schema."""

    def test_create_queue_item(self):
        """Test creating SyncQueueItem."""
        item = SyncQueueItem(
            tm_id=1,
            user_id=1,
            priority=0,
            reason="manual"
        )

        assert item.tm_id == 1
        assert item.priority == 0
        assert item.reason == "manual"
        assert item.queued_at is not None


class TestTMMaintenanceManager:
    """Test TMMaintenanceManager class."""

    @pytest.fixture
    def mock_tm_repo(self):
        """Create mock TM repository."""
        repo = AsyncMock()
        repo.get.return_value = {
            "id": 1,
            "name": "Test TM",
            "updated_at": datetime.utcnow().isoformat(),
            "entry_count": 100
        }
        repo.get_all.return_value = [
            {
                "id": 1,
                "name": "TM 1",
                "updated_at": datetime.utcnow().isoformat(),
                "entry_count": 100
            },
            {
                "id": 2,
                "name": "TM 2",
                "updated_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "entry_count": 50
            }
        ]
        repo.count_entries.return_value = 100
        return repo

    @pytest.fixture
    def manager(self, mock_tm_repo, tmp_path):
        """Create TMMaintenanceManager with mock dependencies."""
        return TMMaintenanceManager(
            tm_repo=mock_tm_repo,
            user={"user_id": 1, "username": "testuser"},
            data_dir=tmp_path
        )

    @pytest.mark.asyncio
    async def test_find_stale_tms_no_metadata(self, manager, mock_tm_repo):
        """Test finding stale TMs when no metadata exists (never indexed)."""
        # No metadata files exist in tmp_path, so all TMs should be stale
        stale_tms = await manager.find_stale_tms()

        assert len(stale_tms) == 2
        assert all(tm.status == "never_indexed" for tm in stale_tms)

    @pytest.mark.asyncio
    async def test_find_stale_tms_with_metadata(self, manager, mock_tm_repo, tmp_path):
        """Test finding stale TMs with existing metadata."""
        import json

        # Create metadata for TM 1 (up to date)
        tm1_path = tmp_path / "1"
        tm1_path.mkdir()
        metadata1 = {
            "synced_at": datetime.utcnow().isoformat(),
            "entry_count": 100
        }
        (tm1_path / "metadata.json").write_text(json.dumps(metadata1))

        # TM 2 has no metadata, should be stale
        stale_tms = await manager.find_stale_tms()

        # Only TM 2 should be stale (no metadata)
        assert len(stale_tms) == 1
        assert stale_tms[0].tm_id == 2
        assert stale_tms[0].status == "never_indexed"

    @pytest.mark.asyncio
    async def test_on_user_login_auto_queue(self, manager, mock_tm_repo):
        """Test on_user_login queues stale TMs."""
        # Clear queue first
        with _sync_queue_lock:
            _sync_queue.clear()

        result = await manager.on_user_login(auto_queue=True)

        assert result.user_id == 1
        assert result.total_stale == 2
        assert result.queued_for_sync == 2

    @pytest.mark.asyncio
    async def test_on_user_login_no_auto_queue(self, manager, mock_tm_repo):
        """Test on_user_login without auto-queuing."""
        # Clear queue first
        with _sync_queue_lock:
            _sync_queue.clear()

        result = await manager.on_user_login(auto_queue=False)

        assert result.total_stale == 2
        assert result.queued_for_sync == 0

    def test_queue_background_sync(self, manager):
        """Test queuing TM for background sync."""
        # Clear queue first
        with _sync_queue_lock:
            _sync_queue.clear()

        queued = manager.queue_background_sync(tm_id=99, reason="test")

        assert queued is True

        status = get_sync_queue_status()
        assert status["queue_length"] == 1
        assert status["items"][0]["tm_id"] == 99

    def test_queue_background_sync_duplicate(self, manager):
        """Test that duplicate TMs aren't queued twice."""
        # Clear queue first
        with _sync_queue_lock:
            _sync_queue.clear()

        queued1 = manager.queue_background_sync(tm_id=100, reason="first")
        queued2 = manager.queue_background_sync(tm_id=100, reason="second")

        assert queued1 is True
        assert queued2 is False  # Should not queue duplicate

        status = get_sync_queue_status()
        assert status["queue_length"] == 1

    def test_get_sync_queue_status(self, manager):
        """Test getting sync queue status."""
        # Clear queue first
        with _sync_queue_lock:
            _sync_queue.clear()

        manager.queue_background_sync(tm_id=1, reason="test", priority=1)
        manager.queue_background_sync(tm_id=2, reason="test", priority=0)

        status = get_sync_queue_status()

        assert status["queue_length"] == 2
        # Should be sorted by priority (0 first)
        assert status["items"][0]["tm_id"] == 2
        assert status["items"][1]["tm_id"] == 1


# Clean up module-level state after tests
@pytest.fixture(autouse=True)
def cleanup_queue():
    """Clean up sync queue after each test."""
    yield
    with _sync_queue_lock:
        _sync_queue.clear()
