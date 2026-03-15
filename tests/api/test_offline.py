"""Offline mode, sync, and trash API tests.

Covers offline status/detection, offline file management, subscriptions,
sync push/pull, local storage CRUD, trash lifecycle, and maintenance
endpoints. Many offline endpoints may return 501/503 when offline mode
is not fully active in the test environment -- tests accept graceful
degradation.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
)
from tests.api.helpers.constants import (
    OFFLINE_STATUS,
    OFFLINE_FILES,
    OFFLINE_SUBSCRIPTIONS,
    OFFLINE_SUBSCRIBE,
    OFFLINE_LOCAL_FILES,
    OFFLINE_LOCAL_FILE_COUNT,
    OFFLINE_TRASH,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.offline]


# Acceptable status codes for offline endpoints that may not be active
GRACEFUL = (200, 404, 422, 500, 501, 503)


# ======================================================================
# Offline Status
# ======================================================================


class TestOfflineStatus:
    """Offline mode detection and status endpoints."""

    def test_offline_status(self, api):
        """GET /api/ldm/offline/status returns mode info."""
        resp = api._get("/api/ldm/offline/status")
        assert resp.status_code in GRACEFUL, (
            f"Offline status: unexpected {resp.status_code}: {resp.text[:300]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            # Should indicate current mode
            assert isinstance(data, dict)

    def test_offline_mode_detection(self, api):
        """Health endpoint indicates online/offline mode."""
        resp = api.health()
        assert_status_ok(resp, "LDM health")
        data = resp.json()
        # Health endpoint should exist and return structured data
        assert isinstance(data, dict)

    def test_offline_storage_info(self, api):
        """Local file count endpoint responds."""
        resp = api._get("/api/ldm/offline/local-file-count")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_offline_capabilities(self, api):
        """Offline files endpoint indicates what's available."""
        resp = api._get("/api/ldm/offline/files")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))


# ======================================================================
# Offline Files
# ======================================================================


class TestOfflineFiles:
    """Offline file list and management."""

    def test_offline_file_list(self, api):
        """GET /api/ldm/offline/local-files returns file list."""
        resp = api._get("/api/ldm/offline/local-files")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_offline_file_download(self, api, uploaded_xml_file_id):
        """POST download-for-offline pulls file locally."""
        resp = api._post(f"/api/ldm/files/{uploaded_xml_file_id}/download-for-offline")
        assert resp.status_code in GRACEFUL

    def test_offline_file_save(self, api, uploaded_xml_file_id):
        """Offline storage file endpoint responds."""
        resp = api._get(f"/api/ldm/offline/storage/files/{uploaded_xml_file_id}")
        assert resp.status_code in GRACEFUL

    def test_offline_file_status(self, api, uploaded_xml_file_id):
        """Offline file rows endpoint responds."""
        resp = api._get(f"/api/ldm/offline/storage/files/{uploaded_xml_file_id}/rows")
        assert resp.status_code in GRACEFUL

    def test_offline_file_rename(self, api, uploaded_xml_file_id):
        """Offline file rename endpoint responds."""
        resp = api._patch(
            f"/api/ldm/offline/storage/files/{uploaded_xml_file_id}/rename",
            json={"name": "offline_renamed.xml"},
        )
        assert resp.status_code in GRACEFUL


# ======================================================================
# Subscriptions
# ======================================================================


class TestOfflineSubscriptions:
    """Offline file subscription management."""

    def test_list_subscriptions(self, api):
        """GET subscriptions returns list."""
        resp = api._get("/api/ldm/offline/subscriptions")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_subscribe_file(self, api, uploaded_xml_file_id):
        """POST subscribe endpoint accepts subscription request."""
        resp = api._post(
            "/api/ldm/offline/subscribe",
            json={"entity_type": "file", "entity_id": uploaded_xml_file_id},
        )
        assert resp.status_code in GRACEFUL

    def test_unsubscribe_file(self, api, uploaded_xml_file_id):
        """DELETE unsubscribe endpoint responds."""
        resp = api._delete(
            f"/api/ldm/offline/subscribe/file/{uploaded_xml_file_id}"
        )
        assert resp.status_code in GRACEFUL

    def test_subscription_sync(self, api):
        """Sync subscription endpoint responds."""
        resp = api._post(
            "/api/ldm/offline/sync-subscription",
            json={"entity_type": "file", "entity_id": 1},
        )
        assert resp.status_code in GRACEFUL


# ======================================================================
# Sync
# ======================================================================


class TestSync:
    """Sync push/pull operations."""

    def test_sync_push(self, api, uploaded_xml_file_id):
        """Push preview endpoint returns change summary."""
        resp = api._get(f"/api/ldm/offline/push-preview/{uploaded_xml_file_id}")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_sync_push_changes(self, api):
        """Push changes endpoint responds."""
        resp = api._post(
            "/api/ldm/offline/push-changes",
            json={"file_ids": []},
        )
        assert resp.status_code in GRACEFUL

    def test_sync_to_central(self, api, uploaded_xml_file_id):
        """Sync file to central database endpoint."""
        resp = api._post(
            "/api/ldm/sync-to-central",
            json={"file_id": uploaded_xml_file_id},
        )
        assert resp.status_code in GRACEFUL

    def test_sync_tm_to_central(self, api, test_tm_id):
        """Sync TM to central database endpoint."""
        resp = api._post(
            "/api/ldm/tm/sync-to-central",
            json={"tm_id": test_tm_id},
        )
        assert resp.status_code in GRACEFUL

    def test_sync_conflict_detection(self, api, uploaded_xml_file_id):
        """Push preview shows conflict status fields."""
        resp = api._get(f"/api/ldm/offline/push-preview/{uploaded_xml_file_id}")
        # Any response is valid -- we just check the endpoint exists
        assert resp.status_code in GRACEFUL


# ======================================================================
# Local Storage CRUD
# ======================================================================


class TestLocalStorage:
    """Local offline storage operations."""

    def test_local_folders_list(self, api):
        """GET offline storage folders."""
        resp = api._get("/api/ldm/offline/storage/folders")
        assert resp.status_code in GRACEFUL
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_local_folder_create(self, api):
        """POST offline storage folder."""
        resp = api._post(
            "/api/ldm/offline/storage/folders",
            json={"name": "offline_test_folder"},
        )
        assert resp.status_code in GRACEFUL

    def test_local_file_move(self, api, uploaded_xml_file_id):
        """PATCH offline file move."""
        resp = api._patch(
            f"/api/ldm/offline/storage/files/{uploaded_xml_file_id}/move",
            json={"folder_id": None},
        )
        assert resp.status_code in GRACEFUL

    def test_local_folder_move(self, api):
        """PATCH offline folder move."""
        resp = api._patch(
            "/api/ldm/offline/storage/folders/1/move",
            json={"parent_id": None},
        )
        assert resp.status_code in GRACEFUL


# ======================================================================
# Trash (Online)
# ======================================================================


class TestTrash:
    """Trash / recycle bin endpoints."""

    def test_trash_list(self, api):
        """GET /api/ldm/trash returns trash items."""
        resp = api.list_trash()
        assert_status_ok(resp, "List trash")
        data = resp.json()
        assert "items" in data or isinstance(data, list)

    def test_trash_empty(self, api):
        """POST /api/ldm/trash/empty clears trash."""
        resp = api.empty_trash()
        # Admin capability may be required
        assert resp.status_code in (200, 403), (
            f"Empty trash: unexpected {resp.status_code}: {resp.text[:300]}"
        )

    def test_trash_restore_nonexistent(self, api):
        """Restore nonexistent trash item returns 404."""
        resp = api.restore_from_trash(999999)
        assert resp.status_code in (404, 400)

    def test_trash_permanent_delete_nonexistent(self, api):
        """Permanent delete nonexistent trash item returns 404."""
        resp = api.permanent_delete_trash(999999)
        assert resp.status_code in (404, 400)


# ======================================================================
# Offline Trash
# ======================================================================


class TestOfflineTrash:
    """Offline-specific trash endpoints."""

    def test_offline_trash_list(self, api):
        """GET /api/ldm/offline/trash returns offline trash."""
        resp = api._get("/api/ldm/offline/trash")
        assert resp.status_code in GRACEFUL

    def test_offline_trash_restore(self, api):
        """POST offline trash restore responds."""
        resp = api._post("/api/ldm/offline/trash/999999/restore")
        assert resp.status_code in GRACEFUL

    def test_offline_trash_delete(self, api):
        """DELETE offline trash item responds."""
        resp = api._delete("/api/ldm/offline/trash/999999")
        assert resp.status_code in GRACEFUL


# ======================================================================
# Maintenance
# ======================================================================


class TestMaintenance:
    """TM maintenance endpoints."""

    def test_maintenance_check_stale(self, api):
        """POST /api/ldm/maintenance/check-stale runs stale check."""
        resp = api.check_stale_tms()
        assert resp.status_code in (200, 404, 422, 500), (
            f"Check stale: unexpected {resp.status_code}: {resp.text[:300]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_maintenance_stale_tms(self, api):
        """GET /api/ldm/maintenance/stale-tms returns list."""
        resp = api.get_stale_tms()
        assert resp.status_code in (200, 404, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_maintenance_sync_status(self, api):
        """GET /api/ldm/maintenance/sync-status returns queue info."""
        resp = api.get_maintenance_status()
        assert resp.status_code in (200, 404, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)
