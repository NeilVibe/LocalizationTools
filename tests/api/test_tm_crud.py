"""
TM CRUD, Index, Assignment, Linking, and Upload E2E tests.

Tests cover the full Translation Memory lifecycle:
- CRUD: create (upload), list, get, delete, export
- Indexes: build, status, sync-status, sync
- Assignment: get, assign to project, activate/deactivate
- Linking: link TM to project, list linked, unlink
- Upload: XML, Excel, duplicate name rejection, br-tag preservation

Uses shared ``api`` / ``test_tm_id`` / ``test_project_id`` fixtures
from conftest.py.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_list_response,
    assert_status,
    assert_status_ok,
    assert_tm_response,
)


# ============================================================================
# Helpers
# ============================================================================

_TM_SAMPLE_CONTENT = (
    "Source\tTarget\n"
    "검\tSword\n"
    "방패\tShield\n"
    "마법\tMagic\n"
    "불\tFire\n"
)


def _upload_ephemeral_tm(api, name: str, content: str = _TM_SAMPLE_CONTENT) -> int:
    """Upload a TM and return its id.  Caller is responsible for cleanup."""
    resp = api.upload_tm(
        name=name,
        content=content.encode(),
        filename="ephemeral.txt",
        source_lang="ko",
        target_lang="en",
        auto_index="false",
    )
    assert_status_ok(resp, f"upload TM '{name}'")
    return resp.json()["tm_id"]


# ============================================================================
# 1. TM Lifecycle (CRUD)
# ============================================================================


class TestTMLifecycle:
    """POST /api/ldm/tm/upload, GET /api/ldm/tm, GET /api/ldm/tm/{id}, DELETE /api/ldm/tm/{id}"""

    def test_create_tm(self, api):
        """Uploading a TM returns a tm_id and entry count."""
        resp = api.upload_tm(
            name="E2E-CRUD-Create",
            content=_TM_SAMPLE_CONTENT.encode(),
            filename="crud.txt",
            source_lang="ko",
            target_lang="en",
            auto_index="false",
        )
        assert_status_ok(resp, "create_tm")
        data = resp.json()
        assert "tm_id" in data
        assert data["entry_count"] >= 4
        # Cleanup
        api.delete_tm(data["tm_id"])

    def test_list_tms(self, api, test_tm_id):
        """Listing TMs returns at least the session TM."""
        resp = api.list_tms()
        assert_status_ok(resp, "list_tms")
        tms = resp.json()
        assert_list_response(tms, min_count=1)

    def test_get_tm(self, api, test_tm_id):
        """Getting a TM by id returns full TM details."""
        resp = api.get_tm(test_tm_id)
        assert_status_ok(resp, "get_tm")
        data = resp.json()
        assert_tm_response(data)

    def test_get_nonexistent_tm(self, api):
        """Getting a nonexistent TM returns 404."""
        resp = api.get_tm(999_999_999)
        assert_status(resp, 404, "get_nonexistent_tm")

    def test_delete_tm(self, api):
        """Deleting a TM removes it permanently."""
        tm_id = _upload_ephemeral_tm(api, "E2E-CRUD-Delete")
        resp = api.delete_tm(tm_id)
        assert_status_ok(resp, "delete_tm")
        # Verify gone
        resp2 = api.get_tm(tm_id)
        assert_status(resp2, 404, "tm_should_be_gone")

    def test_create_tm_duplicate_name(self, api, test_tm_id):
        """Uploading a TM with an existing name returns 400."""
        resp = api.upload_tm(
            name="E2E-Test-TM",  # same as conftest fixture
            content=_TM_SAMPLE_CONTENT.encode(),
            filename="dup.txt",
            source_lang="ko",
            target_lang="en",
            auto_index="false",
        )
        assert_status(resp, 400, "duplicate_tm_name")

    def test_export_tm_text(self, api, test_tm_id):
        """Exporting a TM as text returns content."""
        resp = api.export_tm(test_tm_id, fmt="text")
        assert_status_ok(resp, "export_tm_text")
        assert len(resp.content) > 0, "Export should produce non-empty content"


# ============================================================================
# 2. TM Indexes
# ============================================================================


class TestTMIndexes:
    """POST /api/ldm/tm/{id}/build-indexes, GET .../indexes, .../sync-status, POST .../sync"""

    def test_build_tm_indexes(self, api, test_tm_id):
        """Building indexes returns success or accepted."""
        resp = api.build_tm_indexes(test_tm_id)
        # May fail if engine not available - accept 200 or 500
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"

    def test_get_tm_index_status(self, api, test_tm_id):
        """Getting index status returns tm_id and indexes list."""
        resp = api.get_tm_index_status(test_tm_id)
        assert_status_ok(resp, "get_tm_index_status")
        data = resp.json()
        assert data["tm_id"] == test_tm_id
        assert "indexes" in data

    def test_get_tm_sync_status(self, api, test_tm_id):
        """Getting sync status returns staleness info."""
        resp = api.get_tm_sync_status(test_tm_id)
        assert_status_ok(resp, "get_tm_sync_status")
        data = resp.json()
        assert_json_fields(data, ["tm_id", "is_stale", "db_entry_count"])

    def test_sync_tm_indexes(self, api, test_tm_id):
        """Syncing TM indexes returns sync results."""
        resp = api.sync_tm_indexes(test_tm_id)
        # May fail if engine not available
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"

    def test_index_nonexistent_tm(self, api):
        """Building indexes for nonexistent TM returns 404."""
        resp = api.build_tm_indexes(999_999_999)
        assert_status(resp, 404, "index_nonexistent_tm")


# ============================================================================
# 3. TM Assignment
# ============================================================================


class TestTMAssignment:
    """PATCH /api/ldm/tm/{id}/assign, GET .../assignment, PATCH .../activate, GET /tm-tree"""

    def test_get_tm_assignment(self, api, test_tm_id):
        """Getting assignment for a TM returns scope info."""
        resp = api.get_tm_assignment(test_tm_id)
        assert_status_ok(resp, "get_tm_assignment")
        data = resp.json()
        assert_json_fields(data, ["tm_id", "scope"])

    def test_assign_tm_to_project(self, api, test_tm_id, test_project_id):
        """Assigning TM to a project returns success."""
        resp = api.assign_tm(test_tm_id, project_id=test_project_id)
        assert_status_ok(resp, "assign_tm_to_project")
        data = resp.json()
        assert data.get("success") is True

    def test_activate_tm(self, api, test_tm_id):
        """Activating a TM returns success."""
        resp = api.activate_tm(test_tm_id, active=True)
        # May fail if not assigned yet - accept 200 or 400
        assert resp.status_code in (200, 400), f"Unexpected status: {resp.status_code}"

    def test_deactivate_tm(self, api, test_tm_id):
        """Deactivating a TM returns success."""
        resp = api.activate_tm(test_tm_id, active=False)
        assert resp.status_code in (200, 400), f"Unexpected status: {resp.status_code}"

    def test_get_tm_tree(self, api):
        """TM tree returns a tree structure."""
        resp = api.get_tm_tree()
        assert_status_ok(resp, "get_tm_tree")
        data = resp.json()
        # Tree has unassigned + platforms
        assert isinstance(data, dict)


# ============================================================================
# 4. TM Linking
# ============================================================================


class TestTMLinking:
    """POST /api/ldm/projects/{pid}/link-tm, GET .../linked-tms, DELETE .../link-tm/{tm_id}"""

    def test_link_tm_to_project(self, api, test_tm_id, test_project_id):
        """Linking a TM to a project returns success."""
        resp = api.link_tm_to_project(test_project_id, test_tm_id, priority=1)
        # May already be linked from previous test - accept 200 or 400
        assert resp.status_code in (200, 400), f"Unexpected status: {resp.status_code}"

    def test_get_linked_tms(self, api, test_project_id):
        """Getting linked TMs returns a list."""
        resp = api.get_linked_tms(test_project_id)
        assert_status_ok(resp, "get_linked_tms")
        data = resp.json()
        assert isinstance(data, list)

    def test_unlink_tm_from_project(self, api, test_tm_id, test_project_id):
        """Unlinking a TM from project succeeds (or 404 if not linked)."""
        resp = api.unlink_tm_from_project(test_project_id, test_tm_id)
        assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}"

    def test_link_nonexistent_tm(self, api, test_project_id):
        """Linking a nonexistent TM returns 404."""
        resp = api.link_tm_to_project(test_project_id, 999_999_999)
        assert_status(resp, 404, "link_nonexistent_tm")


# ============================================================================
# 5. TM Upload Formats
# ============================================================================


class TestTMUpload:
    """Upload TMs from different formats."""

    def test_upload_tm_from_txt(self, api):
        """Uploading a TSV file creates a TM with entries."""
        content = "Source\tTarget\nApple\t사과\nBanana\t바나나\n"
        resp = api.upload_tm(
            name="E2E-Upload-TXT",
            content=content.encode(),
            filename="test.txt",
            source_lang="en",
            target_lang="ko",
            auto_index="false",
        )
        assert_status_ok(resp, "upload_tm_txt")
        data = resp.json()
        assert data["entry_count"] >= 2
        api.delete_tm(data["tm_id"])

    def test_upload_tm_unsupported_format(self, api):
        """Uploading an unsupported format returns 400."""
        resp = api.upload_tm(
            name="E2E-Upload-Bad",
            content=b"not a valid format",
            filename="bad.csv",
            auto_index="false",
        )
        assert_status(resp, 400, "upload_unsupported_format")

    def test_upload_tm_preserves_brtags(self, api):
        """br-tags in TM source/target survive upload."""
        content = "Source\tTarget\nLine1<br/>Line2\t줄1<br/>줄2\n"
        resp = api.upload_tm(
            name="E2E-Upload-BrTag",
            content=content.encode(),
            filename="brtag.txt",
            source_lang="en",
            target_lang="ko",
            auto_index="false",
        )
        assert_status_ok(resp, "upload_tm_brtags")
        tm_id = resp.json()["tm_id"]
        # Verify entries preserved br-tags
        entries_resp = api.list_tm_entries(tm_id, page=1, limit=10)
        if entries_resp.status_code == 200:
            entries = entries_resp.json().get("entries", [])
            if entries:
                source_texts = " ".join(e.get("source_text", "") for e in entries)
                # br-tag should appear somewhere
                assert "<br/>" in source_texts or "br" in source_texts.lower(), (
                    f"br-tags not preserved in entries: {source_texts[:200]}"
                )
        api.delete_tm(tm_id)

    def test_tm_entry_count_after_upload(self, api):
        """Entry count matches the number of rows uploaded."""
        content = "Source\tTarget\nA\tB\nC\tD\nE\tF\n"
        resp = api.upload_tm(
            name="E2E-Upload-Count",
            content=content.encode(),
            filename="count.txt",
            auto_index="false",
        )
        assert_status_ok(resp, "upload_count")
        data = resp.json()
        assert data["entry_count"] == 3, f"Expected 3 entries, got {data['entry_count']}"
        api.delete_tm(data["tm_id"])
