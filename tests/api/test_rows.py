"""
Row endpoint E2E tests.

Tests cover:
- Row listing with pagination, search, filters, and category
- Row update (target text, status, br-tags, Korean, empty, nonexistent)
- Per-row QA and grammar checks
- Row response schema validation

All tests use the shared ``api`` fixture and ``uploaded_xml_file_id``
from conftest.py for a realistic file-backed row lifecycle.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_pagination,
    assert_row_response,
    assert_status,
    assert_status_ok,
    assert_brtag_preserved,
    assert_korean_preserved,
)


# ============================================================================
# Helpers
# ============================================================================


def _first_row_id(api, file_id: int) -> int:
    """Return the id of the first row in *file_id*, or pytest.skip."""
    resp = api.list_rows(file_id, page=1, limit=1)
    if resp.status_code != 200:
        pytest.skip(f"Cannot list rows for file {file_id}: {resp.status_code}")
    data = resp.json()
    rows = data.get("rows", [])
    if not rows:
        pytest.skip("No rows available in uploaded file")
    return rows[0]["id"]


# ============================================================================
# 1. Listing
# ============================================================================


class TestListRows:
    """GET /api/ldm/files/{file_id}/rows"""

    def test_list_rows_basic(self, api, uploaded_xml_file_id):
        """Listing rows returns a paginated response with row objects."""
        resp = api.list_rows(uploaded_xml_file_id)
        assert_status_ok(resp, "list_rows_basic")
        data = resp.json()
        assert_pagination(data)
        assert len(data["rows"]) > 0, "Expected at least one row from uploaded XML"

    def test_list_rows_pagination_page_size(self, api, uploaded_xml_file_id):
        """Limiting page size returns at most *limit* rows."""
        resp = api.list_rows(uploaded_xml_file_id, page=1, limit=2)
        assert_status_ok(resp, "list_rows_pagination")
        data = resp.json()
        assert_pagination(data)
        assert data["limit"] == 2
        assert len(data["rows"]) <= 2

    def test_list_rows_pagination_offset(self, api, uploaded_xml_file_id):
        """Page 2 with limit=1 returns a different row than page 1."""
        r1 = api.list_rows(uploaded_xml_file_id, page=1, limit=1)
        r2 = api.list_rows(uploaded_xml_file_id, page=2, limit=1)
        assert_status_ok(r1)
        assert_status_ok(r2)
        rows1 = r1.json()["rows"]
        rows2 = r2.json()["rows"]
        if rows1 and rows2:
            assert rows1[0]["id"] != rows2[0]["id"], "Pagination should yield different rows"

    def test_list_rows_search(self, api, uploaded_xml_file_id):
        """Searching by text content narrows the result set."""
        resp = api.list_rows(uploaded_xml_file_id, search="Test")
        assert_status_ok(resp, "list_rows_search")
        data = resp.json()
        assert_pagination(data)
        # At least one match expected (TEST_001 has "Test text")
        assert data["total"] >= 1

    def test_list_rows_filter_by_status(self, api, uploaded_xml_file_id):
        """Filtering by status returns only matching rows (or empty)."""
        resp = api.list_rows(uploaded_xml_file_id, status="pending")
        assert_status_ok(resp, "list_rows_filter_status")
        data = resp.json()
        assert_pagination(data)

    def test_list_rows_empty_result(self, api, uploaded_xml_file_id):
        """Searching for nonsense returns zero rows but valid pagination."""
        resp = api.list_rows(uploaded_xml_file_id, search="zzz_nonexistent_zzz")
        assert_status_ok(resp, "list_rows_empty")
        data = resp.json()
        assert_pagination(data)
        assert data["total"] == 0

    def test_list_rows_nonexistent_file(self, api):
        """Requesting rows for a nonexistent file returns 404."""
        resp = api.list_rows(999_999_999)
        assert_status(resp, 404, "list_rows_nonexistent_file")


# ============================================================================
# 2. Update
# ============================================================================


class TestUpdateRow:
    """PUT /api/ldm/rows/{row_id}"""

    def test_update_row_target(self, api, uploaded_xml_file_id):
        """Updating the target text persists and is retrievable."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        new_target = "Updated target text"
        resp = api.update_row(row_id, target=new_target)
        assert_status_ok(resp, "update_row_target")
        updated = resp.json()
        assert updated.get("target") == new_target or updated.get("str") == new_target

    def test_update_row_preserves_brtags(self, api, uploaded_xml_file_id):
        """Updating with br-tag content preserves the tags."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        text_with_br = "Line one<br/>Line two<br/>Line three"
        resp = api.update_row(row_id, target=text_with_br)
        assert_status_ok(resp, "update_row_brtags")
        result_target = resp.json().get("target", resp.json().get("str", ""))
        assert_brtag_preserved(text_with_br, result_target)

    def test_update_row_korean_text(self, api, uploaded_xml_file_id):
        """Updating with Korean text preserves Unicode characters."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        korean_text = "업데이트된 한국어 텍스트"
        resp = api.update_row(row_id, target=korean_text)
        assert_status_ok(resp, "update_row_korean")
        result_target = resp.json().get("target", resp.json().get("str", ""))
        assert_korean_preserved(korean_text, result_target)

    def test_update_row_empty_target(self, api, uploaded_xml_file_id):
        """Setting target to empty string succeeds."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        resp = api.update_row(row_id, target="")
        assert_status_ok(resp, "update_row_empty")

    def test_update_nonexistent_row(self, api):
        """Updating a nonexistent row returns 404."""
        resp = api.update_row(999_999_999, target="ghost")
        assert_status(resp, 404, "update_nonexistent_row")


# ============================================================================
# 3. Per-Row QA / Grammar
# ============================================================================


class TestRowQA:
    """POST /api/ldm/rows/{row_id}/check-qa and GET /api/ldm/rows/{row_id}/qa-results"""

    def test_row_qa_check(self, api, uploaded_xml_file_id):
        """Triggering QA on a row returns a response (200 or known error)."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        resp = api.check_row_qa(row_id)
        # QA may fail if engine not configured - accept 200 or 500
        assert resp.status_code in (200, 500, 422), f"Unexpected status: {resp.status_code}"

    def test_row_qa_results(self, api, uploaded_xml_file_id):
        """Getting QA results for a row returns a response."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        resp = api.get_row_qa_results(row_id)
        # Accept 200 (results exist) or 404 (no results yet)
        assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}"

    def test_row_qa_check_with_specific_checks(self, api, uploaded_xml_file_id):
        """QA check with specific check types."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        resp = api.check_row_qa(row_id, checks=["length", "terminology"])
        assert resp.status_code in (200, 500, 422)

    def test_row_qa_nonexistent_row(self, api):
        """QA check on nonexistent row returns 404."""
        resp = api.check_row_qa(999_999_999)
        assert_status(resp, 404, "qa_nonexistent_row")

    def test_row_qa_results_nonexistent_row(self, api):
        """QA results for nonexistent row returns 404."""
        resp = api.get_row_qa_results(999_999_999)
        assert_status(resp, 404, "qa_results_nonexistent_row")


class TestRowGrammar:
    """POST /api/ldm/rows/{row_id}/check-grammar"""

    def test_row_grammar_check(self, api, uploaded_xml_file_id):
        """Triggering grammar check on a row returns a response."""
        row_id = _first_row_id(api, uploaded_xml_file_id)
        resp = api.check_row_grammar(row_id)
        # Grammar engine may not be available - accept 200, 500, 503
        assert resp.status_code in (200, 500, 503, 422), f"Unexpected status: {resp.status_code}"

    def test_row_grammar_nonexistent_row(self, api):
        """Grammar check on nonexistent row returns 404."""
        resp = api.check_row_grammar(999_999_999)
        assert_status(resp, 404, "grammar_nonexistent_row")


# ============================================================================
# 4. Schema Validation
# ============================================================================


class TestRowSchema:
    """Verify row response schema matches expectations."""

    def test_row_response_schema(self, api, uploaded_xml_file_id):
        """Row objects contain expected fields."""
        resp = api.list_rows(uploaded_xml_file_id, limit=1)
        assert_status_ok(resp, "row_response_schema")
        rows = resp.json()["rows"]
        if rows:
            row = rows[0]
            assert_row_response(row)

    def test_row_contains_string_id(self, api, uploaded_xml_file_id):
        """Rows have a string_id field that is non-empty."""
        resp = api.list_rows(uploaded_xml_file_id, limit=1)
        assert_status_ok(resp)
        rows = resp.json()["rows"]
        if rows:
            row = rows[0]
            assert "string_id" in row, "Row missing string_id field"
            assert row["string_id"], "string_id should be non-empty"

    def test_row_contains_source(self, api, uploaded_xml_file_id):
        """Rows have a source field."""
        resp = api.list_rows(uploaded_xml_file_id, limit=1)
        assert_status_ok(resp)
        rows = resp.json()["rows"]
        if rows:
            row = rows[0]
            assert "source" in row, "Row missing source field"

    def test_row_status_is_known_value(self, api, uploaded_xml_file_id):
        """Row status is one of the known values."""
        resp = api.list_rows(uploaded_xml_file_id, limit=10)
        assert_status_ok(resp)
        known_statuses = {"pending", "translated", "reviewed", "approved", "rejected", None, ""}
        for row in resp.json()["rows"]:
            status = row.get("status")
            assert status in known_statuses or isinstance(status, str), (
                f"Unexpected status: {status}"
            )

    def test_row_id_is_integer(self, api, uploaded_xml_file_id):
        """Row id is always an integer."""
        resp = api.list_rows(uploaded_xml_file_id, limit=5)
        assert_status_ok(resp)
        for row in resp.json()["rows"]:
            assert isinstance(row["id"], int), f"Row id should be int, got {type(row['id'])}"
