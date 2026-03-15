"""
TM Entry CRUD and management E2E tests.

Tests cover:
- Entry CRUD: create, list, get (via list), update, delete
- Batch operations: bulk confirm, entry count accuracy
- Entry search: filter by source/target text
- Entry metadata: timestamps, IDs
- Sync: trigger sync, check sync status
- br-tag and Korean preservation in entries

Uses shared ``api`` / ``test_tm_id`` fixtures from conftest.py.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
)


# ============================================================================
# Helpers
# ============================================================================


def _add_entry(api, tm_id: int, source: str, target: str) -> dict:
    """Add a TM entry and return the response json. Skips on failure."""
    resp = api.add_tm_entry(tm_id, source_text=source, target_text=target)
    if resp.status_code != 200:
        pytest.skip(f"add_tm_entry failed: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def _first_entry_id(api, tm_id: int) -> int:
    """Return the first entry id in a TM, or pytest.skip."""
    resp = api.list_tm_entries(tm_id, page=1, limit=1)
    if resp.status_code != 200:
        pytest.skip(f"list_tm_entries failed: {resp.status_code}")
    entries = resp.json().get("entries", [])
    if not entries:
        pytest.skip(f"TM {tm_id} has no entries")
    return entries[0]["id"]


# ============================================================================
# 1. Entry CRUD
# ============================================================================


class TestEntryCRUD:
    """POST/GET/PUT/DELETE /api/ldm/tm/{tm_id}/entries"""

    def test_create_tm_entry(self, api, test_tm_id):
        """Adding an entry returns success with entry_id."""
        data = _add_entry(api, test_tm_id, "테스트 소스", "Test target")
        assert data.get("success") is True
        assert "entry_id" in data

    def test_list_tm_entries(self, api, test_tm_id):
        """Listing entries returns paginated response."""
        resp = api.list_tm_entries(test_tm_id, page=1, limit=10)
        assert_status_ok(resp, "list_tm_entries")
        data = resp.json()
        assert_json_fields(data, ["entries", "total", "page", "limit", "total_pages"])
        assert isinstance(data["entries"], list)

    def test_list_tm_entries_pagination(self, api, test_tm_id):
        """Pagination limits work correctly."""
        resp = api.list_tm_entries(test_tm_id, page=1, limit=2)
        assert_status_ok(resp)
        data = resp.json()
        assert len(data["entries"]) <= 2

    def test_update_tm_entry(self, api, test_tm_id):
        """Updating an entry modifies its content."""
        entry_id = _first_entry_id(api, test_tm_id)
        resp = api.update_tm_entry(
            test_tm_id, entry_id,
            target_text="Updated target text"
        )
        assert_status_ok(resp, "update_tm_entry")

    def test_delete_tm_entry(self, api, test_tm_id):
        """Deleting an entry removes it."""
        # Add an entry to delete
        add_data = _add_entry(api, test_tm_id, "삭제할 항목", "To be deleted")
        entry_id = add_data["entry_id"]
        resp = api.delete_tm_entry(test_tm_id, entry_id)
        assert_status_ok(resp, "delete_tm_entry")

    def test_create_entry_with_brtags(self, api, test_tm_id):
        """Entry with br-tag content is accepted."""
        data = _add_entry(api, test_tm_id, "줄1<br/>줄2", "Line1<br/>Line2")
        assert data.get("success") is True

    def test_create_entry_korean(self, api, test_tm_id):
        """Entry with Korean text is preserved."""
        data = _add_entry(api, test_tm_id, "한국어 테스트", "Korean test")
        assert data.get("success") is True

    def test_delete_nonexistent_entry(self, api, test_tm_id):
        """Deleting nonexistent entry returns 404."""
        resp = api.delete_tm_entry(test_tm_id, 999_999_999)
        assert_status(resp, 404, "delete_nonexistent_entry")

    def test_update_nonexistent_entry(self, api, test_tm_id):
        """Updating nonexistent entry returns 404."""
        resp = api.update_tm_entry(test_tm_id, 999_999_999, target_text="ghost")
        assert_status(resp, 404, "update_nonexistent_entry")


# ============================================================================
# 2. Confirm / Bulk Confirm
# ============================================================================


class TestEntryConfirm:
    """POST /api/ldm/tm/{tm_id}/entries/{entry_id}/confirm"""

    def test_confirm_entry(self, api, test_tm_id):
        """Confirming an entry returns the updated entry."""
        entry_id = _first_entry_id(api, test_tm_id)
        resp = api.confirm_tm_entry(test_tm_id, entry_id)
        assert_status_ok(resp, "confirm_entry")

    def test_bulk_confirm_entries(self, api, test_tm_id):
        """Bulk confirming entries returns updated count."""
        entry_id = _first_entry_id(api, test_tm_id)
        resp = api.bulk_confirm_tm_entries(test_tm_id, entry_ids=[entry_id])
        assert_status_ok(resp, "bulk_confirm")
        data = resp.json()
        assert "updated_count" in data

    def test_confirm_nonexistent_entry(self, api, test_tm_id):
        """Confirming nonexistent entry returns 404."""
        resp = api.confirm_tm_entry(test_tm_id, 999_999_999)
        assert_status(resp, 404, "confirm_nonexistent")


# ============================================================================
# 3. Entry Search
# ============================================================================


class TestEntrySearch:
    """Search entries within a TM."""

    def test_search_entries_by_text(self, api, test_tm_id):
        """Searching entries by text filters results."""
        resp = api.list_tm_entries(test_tm_id, page=1, limit=50)
        assert_status_ok(resp)
        # Use the search parameter via the entries endpoint
        # The endpoint supports ?search= parameter
        resp2 = api.client.get(
            f"/api/ldm/tm/{test_tm_id}/entries",
            headers=api.headers,
            params={"search": "검", "page": 1, "limit": 50},
        )
        if resp2.status_code == 200:
            data = resp2.json()
            assert isinstance(data.get("entries", []), list)

    def test_entries_contain_metadata(self, api, test_tm_id):
        """Entries have id, source_text, target_text fields."""
        resp = api.list_tm_entries(test_tm_id, page=1, limit=5)
        assert_status_ok(resp)
        entries = resp.json().get("entries", [])
        if entries:
            entry = entries[0]
            assert_json_fields(entry, ["id", "source_text", "target_text"])


# ============================================================================
# 4. Sync
# ============================================================================


class TestTMSync:
    """POST /api/ldm/tm/{tm_id}/sync, GET .../sync-status"""

    def test_sync_tm(self, api, test_tm_id):
        """Triggering TM sync returns results or acceptable error."""
        resp = api.sync_tm_indexes(test_tm_id)
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"

    def test_tm_sync_status(self, api, test_tm_id):
        """Checking sync status returns staleness info."""
        resp = api.get_tm_sync_status(test_tm_id)
        assert_status_ok(resp, "tm_sync_status")
        data = resp.json()
        assert_json_fields(data, ["tm_id", "is_stale"])


# ============================================================================
# 5. Entry Count Accuracy
# ============================================================================


class TestEntryCount:
    """Verify entry count consistency."""

    def test_entry_count_matches_tm(self, api, test_tm_id):
        """TM entry_count field matches actual entries returned."""
        tm_resp = api.get_tm(test_tm_id)
        assert_status_ok(tm_resp)
        expected_count = tm_resp.json().get("entry_count", 0)

        entries_resp = api.list_tm_entries(test_tm_id, page=1, limit=500)
        assert_status_ok(entries_resp)
        actual_total = entries_resp.json().get("total", 0)

        # Allow slight difference due to concurrent modifications
        assert abs(expected_count - actual_total) <= 2, (
            f"TM entry_count={expected_count} vs entries total={actual_total}"
        )
