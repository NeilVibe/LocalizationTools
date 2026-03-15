"""
QA and Grammar check subsystem API tests.

Tests file-level QA (line, pattern, term checks), row-level QA, QA result
management (summary, resolve), and grammar/spelling check endpoints.
Grammar checks depend on LanguageTool server availability -- tests handle
503 gracefully.

Phase 25 Plan 08: AI Intelligence, Search, QA/Grammar E2E Tests
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
    assert_qa_issue,
)
from tests.api.helpers.constants import (
    KOREAN_TEXT_SAMPLES,
    VALID_QA_CHECK_TYPES,
    QA_ISSUE_FIELDS,
    QA_SUMMARY_FIELDS,
)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.qa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Grammar may be unavailable (LanguageTool not running)
GRAMMAR_ACCEPTABLE = {200, 503}


# =========================================================================
# File-Level QA
# =========================================================================


class TestFileQACheck:
    """POST /api/ldm/files/{file_id}/check-qa"""

    def test_qa_file_pattern_check(self, api, uploaded_xml_file_id):
        """Run pattern check on uploaded file."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        assert_status_ok(resp, "File pattern QA")
        data = resp.json()
        assert "file_id" in data
        assert "total_issues" in data
        assert isinstance(data["total_issues"], int)

    def test_qa_file_line_check(self, api, uploaded_xml_file_id):
        """Run line check (consistency) on file."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["line"], force=True)
        assert_status_ok(resp, "File line QA")
        data = resp.json()
        assert "rows_checked" in data

    def test_qa_file_term_check(self, api, uploaded_xml_file_id):
        """Run term check on file (may have no glossary)."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["term"], force=True)
        assert_status_ok(resp, "File term QA")
        data = resp.json()
        assert "total_issues" in data

    def test_qa_file_all_checks(self, api, uploaded_xml_file_id):
        """Run all QA checks combined."""
        resp = api.check_file_qa(
            uploaded_xml_file_id,
            checks=["pattern", "line", "term"],
            force=True,
        )
        assert_status_ok(resp, "File all QA checks")
        data = resp.json()
        assert "summary" in data
        assert "total_issues" in data
        assert "total_rows" in data
        assert "rows_checked" in data

    def test_qa_file_response_summary_structure(self, api, uploaded_xml_file_id):
        """Summary field has per-check-type breakdown."""
        resp = api.check_file_qa(
            uploaded_xml_file_id,
            checks=["pattern", "line"],
            force=True,
        )
        assert_status_ok(resp)
        data = resp.json()
        summary = data.get("summary", {})
        # Each requested check should appear in summary
        for check_type in ["pattern", "line"]:
            assert check_type in summary, (
                f"Missing '{check_type}' in summary: {list(summary.keys())}"
            )

    def test_qa_file_nonexistent(self, api):
        """QA on nonexistent file returns 404."""
        resp = api.check_file_qa(999999, checks=["pattern"])
        assert_status(resp, 404, "Nonexistent file QA")

    def test_qa_file_force_recheck(self, api, uploaded_xml_file_id):
        """Force=True rechecks previously checked rows."""
        # First check
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        # Second check with force
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        assert_status_ok(resp, "Force recheck")
        data = resp.json()
        assert data["rows_checked"] >= 0


# =========================================================================
# File QA Results
# =========================================================================


class TestFileQAResults:
    """GET /api/ldm/files/{file_id}/qa-results"""

    def test_qa_results_list(self, api, uploaded_xml_file_id):
        """Get QA results for file."""
        # Run QA first to ensure results exist
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        resp = api.get_file_qa_results(uploaded_xml_file_id)
        assert_status_ok(resp, "File QA results")
        data = resp.json()
        assert "issues" in data
        assert "total_count" in data
        assert isinstance(data["issues"], list)

    def test_qa_results_filter_by_type(self, api, uploaded_xml_file_id):
        """Filter QA results by check_type."""
        resp = api.get_file_qa_results(uploaded_xml_file_id, check_type="pattern")
        assert_status_ok(resp, "Filtered QA results")
        data = resp.json()
        # All returned issues should match the filter
        for issue in data.get("issues", []):
            assert issue["check_type"] == "pattern", (
                f"Expected check_type=pattern, got {issue['check_type']}"
            )

    def test_qa_results_issue_schema(self, api, uploaded_xml_file_id):
        """Each QA issue has required fields."""
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern", "line"], force=True)
        resp = api.get_file_qa_results(uploaded_xml_file_id)
        assert_status_ok(resp)
        data = resp.json()
        for issue in data.get("issues", [])[:5]:
            assert "id" in issue, f"Missing 'id' in issue: {issue}"
            assert "check_type" in issue, f"Missing 'check_type': {issue}"
            assert "severity" in issue, f"Missing 'severity': {issue}"
            assert "message" in issue, f"Missing 'message': {issue}"


# =========================================================================
# File QA Summary
# =========================================================================


class TestFileQASummary:
    """GET /api/ldm/files/{file_id}/qa-summary"""

    def test_qa_summary(self, api, uploaded_xml_file_id):
        """QA summary returns count per check type."""
        resp = api.get_file_qa_summary(uploaded_xml_file_id)
        assert_status_ok(resp, "QA summary")
        data = resp.json()
        assert "file_id" in data
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_qa_summary_fields(self, api, uploaded_xml_file_id):
        """Summary has per-type counts (line, term, pattern, etc)."""
        resp = api.get_file_qa_summary(uploaded_xml_file_id)
        assert_status_ok(resp)
        data = resp.json()
        for field in ["line", "term", "pattern"]:
            assert field in data, f"Missing '{field}' in summary: {list(data.keys())}"
            assert isinstance(data[field], int), f"'{field}' should be int"


# =========================================================================
# Row-Level QA
# =========================================================================


class TestRowQACheck:
    """POST /api/ldm/rows/{row_id}/check-qa"""

    def test_qa_row_check(self, api, uploaded_xml_file_id):
        """QA on single row returns issues list."""
        # Get a row ID from the uploaded file
        rows_resp = api.list_rows(uploaded_xml_file_id, limit=1)
        if rows_resp.status_code != 200:
            pytest.skip("Cannot get rows for QA test")
        rows_data = rows_resp.json()
        rows = rows_data.get("rows", [])
        if not rows:
            pytest.skip("No rows in uploaded file")

        row_id = rows[0]["id"]
        resp = api.check_row_qa(row_id, checks=["pattern"], force=True)
        assert_status_ok(resp, "Row QA check")
        data = resp.json()
        assert "row_id" in data
        assert "issues" in data
        assert "issue_count" in data

    def test_qa_row_response_schema(self, api, uploaded_xml_file_id):
        """Row QA response has correct schema."""
        rows_resp = api.list_rows(uploaded_xml_file_id, limit=1)
        if rows_resp.status_code != 200:
            pytest.skip("Cannot get rows")
        rows = rows_resp.json().get("rows", [])
        if not rows:
            pytest.skip("No rows available")

        row_id = rows[0]["id"]
        resp = api.check_row_qa(row_id, checks=["pattern", "line"], force=True)
        assert_status_ok(resp)
        data = resp.json()
        assert data["row_id"] == row_id
        for issue in data.get("issues", []):
            assert "check_type" in issue
            assert "severity" in issue
            assert "message" in issue

    def test_qa_row_nonexistent(self, api):
        """QA on nonexistent row returns 404."""
        resp = api.check_row_qa(999999, checks=["pattern"])
        assert_status(resp, 404, "Nonexistent row QA")


class TestRowQAResults:
    """GET /api/ldm/rows/{row_id}/qa-results"""

    def test_qa_row_results(self, api, uploaded_xml_file_id):
        """Get QA results for a row."""
        rows_resp = api.list_rows(uploaded_xml_file_id, limit=1)
        if rows_resp.status_code != 200:
            pytest.skip("Cannot get rows")
        rows = rows_resp.json().get("rows", [])
        if not rows:
            pytest.skip("No rows available")

        row_id = rows[0]["id"]
        resp = api.get_row_qa_results(row_id)
        assert_status_ok(resp, "Row QA results")
        data = resp.json()
        assert "row_id" in data
        assert "issues" in data


# =========================================================================
# QA Issue Resolution
# =========================================================================


class TestQAResolve:
    """POST /api/ldm/qa-results/{result_id}/resolve"""

    def test_qa_resolve_nonexistent(self, api):
        """Resolve nonexistent QA issue returns 404."""
        resp = api.resolve_qa_issue(999999)
        assert_status(resp, 404, "Resolve nonexistent QA issue")

    def test_qa_resolve_issue(self, api, uploaded_xml_file_id):
        """Resolve a real QA issue if any exist."""
        # Run QA to generate issues
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern", "line"], force=True)
        results_resp = api.get_file_qa_results(uploaded_xml_file_id)
        if results_resp.status_code != 200:
            pytest.skip("Cannot get QA results")
        issues = results_resp.json().get("issues", [])
        if not issues:
            pytest.skip("No QA issues to resolve")

        result_id = issues[0]["id"]
        resp = api.resolve_qa_issue(result_id)
        assert resp.status_code in {200, 400}, (
            f"Unexpected status {resp.status_code}: {resp.text[:200]}"
        )


# =========================================================================
# QA Categories & Severity
# =========================================================================


class TestQACategories:
    """QA result category and severity validation."""

    def test_qa_categories_valid(self, api, uploaded_xml_file_id):
        """QA issues have valid check_type categories."""
        api.check_file_qa(
            uploaded_xml_file_id,
            checks=["pattern", "line", "term"],
            force=True,
        )
        resp = api.get_file_qa_results(uploaded_xml_file_id)
        if resp.status_code != 200:
            pytest.skip("Cannot get QA results")
        for issue in resp.json().get("issues", []):
            assert issue["check_type"] in VALID_QA_CHECK_TYPES, (
                f"Invalid check_type: {issue['check_type']}"
            )

    def test_qa_severity_levels(self, api, uploaded_xml_file_id):
        """QA issues have valid severity levels."""
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern", "line"], force=True)
        resp = api.get_file_qa_results(uploaded_xml_file_id)
        if resp.status_code != 200:
            pytest.skip("Cannot get QA results")
        valid_severities = {"warning", "error", "info"}
        for issue in resp.json().get("issues", []):
            assert issue["severity"] in valid_severities, (
                f"Invalid severity: {issue['severity']}"
            )

    def test_qa_issue_has_description(self, api, uploaded_xml_file_id):
        """Each QA issue has a human-readable message."""
        api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        resp = api.get_file_qa_results(uploaded_xml_file_id)
        if resp.status_code != 200:
            pytest.skip("Cannot get QA results")
        for issue in resp.json().get("issues", []):
            assert issue.get("message"), f"Empty message in issue: {issue}"
            assert len(issue["message"]) > 3, f"Message too short: {issue['message']}"


# =========================================================================
# Grammar
# =========================================================================


class TestGrammarStatus:
    """GET /api/ldm/grammar/status"""

    def test_grammar_status(self, api):
        """Grammar status returns availability info."""
        resp = api.grammar_status()
        assert resp.status_code in GRAMMAR_ACCEPTABLE, (
            f"Unexpected grammar status code: {resp.status_code}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "available" in data
            assert "server_url" in data


class TestGrammarCheckFile:
    """POST /api/ldm/files/{file_id}/check-grammar"""

    def test_grammar_check_file(self, api, uploaded_xml_file_id):
        """Grammar check on file returns results or 503."""
        resp = api.check_file_grammar(uploaded_xml_file_id)
        assert resp.status_code in GRAMMAR_ACCEPTABLE, (
            f"Unexpected grammar check code: {resp.status_code}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "file_id" in data
            assert "total_errors" in data
            assert "errors" in data
            assert isinstance(data["errors"], list)

    def test_grammar_check_response_schema(self, api, uploaded_xml_file_id):
        """Grammar response has complete schema when available."""
        resp = api.check_file_grammar(uploaded_xml_file_id)
        if resp.status_code == 200:
            data = resp.json()
            assert_json_fields(data, [
                "file_id", "language", "total_rows", "rows_checked",
                "rows_with_errors", "total_errors", "errors", "server_available",
            ])

    def test_grammar_check_nonexistent_file(self, api):
        """Grammar check on nonexistent file returns 404 or 503."""
        resp = api.check_file_grammar(999999)
        assert resp.status_code in {404, 503}


class TestGrammarCheckRow:
    """POST /api/ldm/rows/{row_id}/check-grammar"""

    def test_grammar_check_row(self, api, uploaded_xml_file_id):
        """Grammar check on single row."""
        rows_resp = api.list_rows(uploaded_xml_file_id, limit=1)
        if rows_resp.status_code != 200:
            pytest.skip("Cannot get rows")
        rows = rows_resp.json().get("rows", [])
        if not rows:
            pytest.skip("No rows available")

        row_id = rows[0]["id"]
        resp = api.check_row_grammar(row_id)
        assert resp.status_code in GRAMMAR_ACCEPTABLE

    def test_grammar_check_row_nonexistent(self, api):
        """Grammar check on nonexistent row returns 404 or 503."""
        resp = api.check_row_grammar(999999)
        assert resp.status_code in {404, 503}


# =========================================================================
# Edge Cases
# =========================================================================


class TestQAEdgeCases:
    """QA edge cases and special input."""

    def test_qa_special_characters(self, api, uploaded_xml_file_id):
        """QA on file with XML special characters does not crash."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        # The test XML has <br/> tags -- should not crash
        assert resp.status_code != 500, f"500 on special chars: {resp.text[:200]}"

    def test_qa_empty_checks_list(self, api, uploaded_xml_file_id):
        """Empty checks list should return quickly."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=[], force=True)
        # May return 200 with 0 issues or 422 for empty checks
        assert resp.status_code in {200, 422}

    def test_qa_brtag_validation(self, api, uploaded_xml_file_id):
        """QA on file with br-tags (test fixture has <br/> in TEST_002)."""
        resp = api.check_file_qa(uploaded_xml_file_id, checks=["pattern"], force=True)
        assert_status_ok(resp, "br-tag QA")
        # The check should complete without treating br-tags as errors
        data = resp.json()
        assert isinstance(data["total_issues"], int)
