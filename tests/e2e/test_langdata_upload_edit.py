"""E2E tests for language data upload -> parse -> edit -> save -> reload pipeline.

Tests the full LDM lifecycle using the mock showcase_dialogue.loc.xml fixture
(10 LocStr rows with Korean source text). Verifies upload returns correct row
count, rows contain expected columns and StringIds, edits persist on reload,
and the full pipeline works under SQLite backend.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tests.api.helpers.assertions import assert_status, assert_status_ok

# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.e2e, pytest.mark.langdata]

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "mock_gamedata"
    / "loc"
    / "showcase_dialogue.loc.xml"
)


# ======================================================================
# Upload tests (LDE2E-01)
# ======================================================================


class TestLangDataUpload:
    """Verify upload of .loc.xml returns correct metadata and rows."""

    @pytest.fixture(autouse=True, scope="class")
    def _upload_fixture(self, api, test_project_id):
        """Upload the showcase_dialogue fixture once for all tests in this class."""
        content = FIXTURE_PATH.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="showcase_dialogue.loc.xml",
            content=content,
            content_type="text/xml",
        )
        assert_status(resp, 200, "Upload showcase_dialogue.loc.xml")
        data = resp.json()
        # Store on class for other tests
        self.__class__._file_id = data["id"]
        self.__class__._upload_data = data

    def test_upload_loc_xml_returns_200(self):
        """Upload of mock .loc.xml returns 200 with correct row count (10 rows)."""
        data = self._upload_data
        assert "id" in data
        row_count = data.get("row_count", 0) or data.get("rows_imported", 0)
        assert row_count >= 10, f"Expected >= 10 rows, got {row_count}"

    def test_uploaded_rows_have_string_columns(self, api):
        """Uploaded file rows contain source and target columns with correct values."""
        resp = api.list_rows(self._file_id)
        assert_status(resp, 200, "List rows")
        data = resp.json()
        rows = data.get("rows", [])
        assert len(rows) >= 10, f"Expected >= 10 rows, got {len(rows)}"

        # Check first row has expected fields
        first_row = rows[0]
        assert "source" in first_row, f"Row missing 'source' field. Keys: {list(first_row.keys())}"
        assert "target" in first_row, f"Row missing 'target' field. Keys: {list(first_row.keys())}"

        # At least one row should have Korean source text
        korean_pattern = re.compile(r"[\uac00-\ud7af]")
        has_korean = any(
            korean_pattern.search(r.get("source", "") or "")
            for r in rows
        )
        assert has_korean, "No rows contain Korean source text"

    def test_uploaded_rows_contain_expected_stringids(self, api):
        """Rows contain expected StringIds from the fixture."""
        resp = api.list_rows(self._file_id)
        assert_status(resp, 200, "List rows for StringId check")
        rows = resp.json().get("rows", [])
        string_ids = {r.get("string_id") for r in rows}
        assert "DLG_VARON_01" in string_ids, f"DLG_VARON_01 not found in {string_ids}"
        assert "DLG_KIRA_01" in string_ids, f"DLG_KIRA_01 not found in {string_ids}"


# ======================================================================
# Edit persistence tests (LDE2E-02)
# ======================================================================


class TestLangDataEditPersistence:
    """Verify editing a row target persists on reload."""

    @pytest.fixture(autouse=True, scope="class")
    def _upload_for_edit(self, api, test_project_id):
        """Upload a fresh copy for edit tests."""
        content = FIXTURE_PATH.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="showcase_edit_test.loc.xml",
            content=content,
            content_type="text/xml",
        )
        assert_status(resp, 200, "Upload for edit test")
        data = resp.json()
        self.__class__._file_id = data["id"]

        # Get rows to find first row id
        rows_resp = api.list_rows(data["id"])
        assert_status(rows_resp, 200, "List rows for edit setup")
        rows = rows_resp.json().get("rows", [])
        assert len(rows) > 0, "No rows returned after upload"
        self.__class__._first_row = rows[0]

    def test_edit_target_persists_on_reload(self, api):
        """Editing a row target value and re-fetching shows the new value persisted."""
        row_id = self._first_row["id"]
        original_source = self._first_row.get("source")
        original_string_id = self._first_row.get("string_id")

        # Edit the target
        edit_resp = api.update_row(row_id, target="EDITED_VALUE_E2E")
        assert_status(edit_resp, 200, "Update row target")

        # Re-list rows and find the same row
        rows_resp = api.list_rows(self._file_id)
        assert_status(rows_resp, 200, "Re-list rows after edit")
        rows = rows_resp.json().get("rows", [])
        edited_row = next((r for r in rows if r["id"] == row_id), None)
        assert edited_row is not None, f"Row {row_id} not found after edit"
        assert edited_row["target"] == "EDITED_VALUE_E2E", (
            f"Expected 'EDITED_VALUE_E2E', got '{edited_row['target']}'"
        )

    def test_edit_preserves_other_fields(self, api):
        """After editing target, string_id and source remain unchanged."""
        row_id = self._first_row["id"]
        original_source = self._first_row.get("source")
        original_string_id = self._first_row.get("string_id")

        # Re-list and verify other fields unchanged
        rows_resp = api.list_rows(self._file_id)
        assert_status(rows_resp, 200, "Re-list rows for field preservation check")
        rows = rows_resp.json().get("rows", [])
        edited_row = next((r for r in rows if r["id"] == row_id), None)
        assert edited_row is not None, f"Row {row_id} not found"
        assert edited_row.get("string_id") == original_string_id, (
            f"string_id changed: {original_string_id} -> {edited_row.get('string_id')}"
        )
        assert edited_row.get("source") == original_source, (
            f"source changed: {original_source} -> {edited_row.get('source')}"
        )


# ======================================================================
# SQLite offline mode tests (LDE2E-04)
# ======================================================================


class TestLangDataSQLiteOffline:
    """Verify operations work under SQLite backend (no PostgreSQL)."""

    def test_sqlite_mode_active(self):
        """Confirm tests are running against SQLite (no postgres DATABASE_URL)."""
        db_url = os.environ.get("DATABASE_URL", "")
        assert "postgres" not in db_url.lower(), (
            f"Expected SQLite mode but DATABASE_URL contains postgres: {db_url}"
        )

    def test_full_pipeline_under_sqlite(self, api, test_project_id):
        """Full round-trip under SQLite: upload -> list -> edit -> re-list -> download -> delete."""
        # 1. Upload
        content = FIXTURE_PATH.read_bytes()
        upload_resp = api.upload_file(
            project_id=test_project_id,
            filename="showcase_sqlite_test.loc.xml",
            content=content,
            content_type="text/xml",
        )
        assert_status(upload_resp, 200, "SQLite upload")
        file_id = upload_resp.json()["id"]

        # 2. List rows
        rows_resp = api.list_rows(file_id)
        assert_status(rows_resp, 200, "SQLite list rows")
        rows = rows_resp.json().get("rows", [])
        assert len(rows) >= 10, f"Expected >= 10 rows, got {len(rows)}"

        # 3. Edit a row
        row_id = rows[0]["id"]
        edit_resp = api.update_row(row_id, target="SQLITE_EDIT_E2E")
        assert_status(edit_resp, 200, "SQLite edit row")

        # 4. Re-list and verify edit persisted
        rows_resp2 = api.list_rows(file_id)
        assert_status(rows_resp2, 200, "SQLite re-list after edit")
        rows2 = rows_resp2.json().get("rows", [])
        edited_row = next((r for r in rows2 if r["id"] == row_id), None)
        assert edited_row is not None, f"Row {row_id} not found after edit"
        assert edited_row["target"] == "SQLITE_EDIT_E2E"

        # 5. Download file
        dl_resp = api.download_file(file_id)
        assert_status(dl_resp, 200, "SQLite download")
        dl_content = dl_resp.text
        assert "DLG_VARON_01" in dl_content, "Downloaded content missing DLG_VARON_01"

        # 6. Delete file
        del_resp = api.delete_file(file_id, permanent=True)
        assert del_resp.status_code in (200, 204), f"Delete failed: {del_resp.status_code}"
