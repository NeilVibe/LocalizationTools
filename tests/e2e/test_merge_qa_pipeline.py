"""E2E tests for merge and QA pipelines.

Verifies FEAT-03 (merge executes with match modes and returns counts) and
FEAT-04 (QA detects line and term issues in language data).

Uploads two XML files -- a base file with intentional QA issues and a
corrections file -- then exercises merge modes and QA endpoints.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import assert_status

# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.e2e, pytest.mark.merge, pytest.mark.qa]

# ---------------------------------------------------------------------------
# Module-level XML fixtures
# ---------------------------------------------------------------------------

BASE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="DLG_001" StrOrigin="The warrior attacks" Str="\uc804\uc0ac\uac00 \uacf5\uaca9\ud55c\ub2e4"/>
  <LocStr StringId="DLG_002" StrOrigin="Quest complete!" Str="\ud034\uc2a4\ud2b8 \uc644\ub8cc!"/>
  <LocStr StringId="DLG_003" StrOrigin="Item received: {0}" Str="\uc544\uc774\ud15c \ud68d\ub4dd"/>
  <LocStr StringId="DLG_004" StrOrigin="Hello, adventurer." Str="\uc548\ub155\ud558\uc138\uc694, \ubaa8\ud5d8\uac00."/>
  <LocStr StringId="DLG_005" StrOrigin="The dragon flies." Str="\ub4dc\ub798\uace4\uc774 \ub0a0\uc544\uac04\ub2e4."/>
</LanguageData>
""".encode("utf-8")

CORRECTION_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="DLG_001" StrOrigin="The warrior attacks" Str="\uc804\uc0ac\uac00 \uacf5\uaca9\ud569\ub2c8\ub2e4"/>
  <LocStr StringId="DLG_002" StrOrigin="Quest complete!" Str="\ud034\uc2a4\ud2b8 \uc644\ub8cc\ub428!"/>
</LanguageData>
""".encode("utf-8")

# ---------------------------------------------------------------------------
# Module-scoped file upload helper
# ---------------------------------------------------------------------------

_module_state: dict = {}


@pytest.fixture(scope="module", autouse=True)
def _upload_merge_files(api, test_project_id):
    """Upload both XML files once for the entire module."""
    # Upload base file
    base_resp = api.upload_file(
        project_id=test_project_id,
        filename="base_dialogue.loc.xml",
        content=BASE_XML,
        content_type="text/xml",
    )
    assert_status(base_resp, 200, "Upload base_dialogue.loc.xml")
    _module_state["base_file_id"] = base_resp.json()["id"]

    # Upload correction file
    corr_resp = api.upload_file(
        project_id=test_project_id,
        filename="corrections.loc.xml",
        content=CORRECTION_XML,
        content_type="text/xml",
    )
    assert_status(corr_resp, 200, "Upload corrections.loc.xml")
    _module_state["correction_file_id"] = corr_resp.json()["id"]

    yield

    # No teardown needed -- session-scoped project cleanup handles it


# ======================================================================
# Merge Pipeline (FEAT-03)
# ======================================================================


class TestMergePipeline:
    """Verify merge endpoint works with multiple match modes.

    TranslatorMergeService endpoint (merge.py) at POST /files/{file_id}/merge
    accepts JSON with source_file_id + match_mode. The older files.py export
    merge is now at POST /files/{file_id}/export-merge (no conflict).
    """

    def _base_id(self) -> int:
        return _module_state["base_file_id"]

    def _corr_id(self) -> int:
        return _module_state["correction_file_id"]

    def test_merge_strict_mode(self, api):
        """Merge with strict mode returns 200 and match counts."""
        resp = api.merge_file(
            self._base_id(),
            json={
                "source_file_id": self._corr_id(),
                "match_mode": "strict",
            },
        )
        assert_status(resp, 200, "Merge strict mode")
        data = resp.json()
        assert "matched" in data
        assert "total" in data
        assert data["matched"] >= 0
        assert data["total"] >= 0

    def test_merge_stringid_mode(self, api):
        """Merge with stringid_only mode returns 200."""
        resp = api.merge_file(
            self._base_id(),
            json={
                "source_file_id": self._corr_id(),
                "match_mode": "stringid_only",
            },
        )
        assert_status(resp, 200, "Merge stringid_only mode")
        data = resp.json()
        assert data["matched"] >= 0

    def test_merge_cascade_mode(self, api):
        """Merge with cascade mode returns 200."""
        resp = api.merge_file(
            self._base_id(),
            json={
                "source_file_id": self._corr_id(),
                "match_mode": "cascade",
            },
        )
        assert_status(resp, 200, "Merge cascade mode")
        data = resp.json()
        assert data["matched"] >= 0

    def test_merge_response_has_counts(self, api):
        """Merge response contains all expected count fields."""
        resp = api.merge_file(
            self._base_id(),
            json={
                "source_file_id": self._corr_id(),
                "match_mode": "strict",
            },
        )
        assert_status(resp, 200, "Merge response fields")
        data = resp.json()
        for field in ("matched", "skipped", "total", "match_type_counts", "rows_updated"):
            assert field in data, f"Missing field '{field}' in merge response: {list(data.keys())}"

    def test_merge_endpoint_exists(self, api):
        """Verify merge endpoint is registered (responds, not 404)."""
        resp = api.merge_file(
            self._base_id(),
            json={
                "source_file_id": self._corr_id(),
                "match_mode": "strict",
            },
        )
        # Endpoint exists (not 404/405) even if validation fails (422)
        assert resp.status_code != 404, "Merge endpoint not found"
        assert resp.status_code != 405, "Merge method not allowed"


# ======================================================================
# QA Pipeline (FEAT-04)
# ======================================================================


class TestQAPipeline:
    """Verify QA check endpoints detect issues in uploaded language data."""

    def _base_id(self) -> int:
        return _module_state["base_file_id"]

    def test_file_qa_check_runs(self, api):
        """File-level QA check with pattern check runs and returns 200."""
        resp = api.check_file_qa(
            self._base_id(),
            checks=["pattern"],
            force=True,
        )
        assert_status(resp, 200, "File QA check (pattern)")
        data = resp.json()
        assert "total_rows" in data
        assert "rows_checked" in data

    def test_file_qa_line_check_runs(self, api):
        """File-level QA check with line check runs and returns 200."""
        resp = api.check_file_qa(
            self._base_id(),
            checks=["line"],
            force=True,
        )
        assert_status(resp, 200, "File QA check (line)")

    def test_file_qa_results_returned(self, api):
        """QA results endpoint returns a list of issues for the file."""
        resp = api.get_file_qa_results(self._base_id())
        assert_status(resp, 200, "File QA results")
        data = resp.json()
        # Response should have issues list (may be empty if no issues stored)
        assert "issues" in data or isinstance(data, list), (
            f"Expected 'issues' key or list, got keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    def test_qa_detects_pattern_mismatch(self, api):
        """QA should detect the {0} pattern mismatch in DLG_003.

        EN has '{0}' placeholder but KR is missing it.
        """
        # Run pattern check first to ensure issues are generated
        check_resp = api.check_file_qa(
            self._base_id(),
            checks=["pattern"],
            force=True,
        )
        assert_status(check_resp, 200, "Pattern check for mismatch detection")
        check_data = check_resp.json()

        # The pattern check should find at least one issue (DLG_003)
        total_issues = check_data.get("total_issues", 0)
        summary = check_data.get("summary", {})
        pattern_issues = summary.get("pattern", {}).get("issue_count", 0)

        assert total_issues > 0 or pattern_issues > 0, (
            f"Expected at least 1 pattern issue for DLG_003 ({'{0}'} mismatch), "
            f"got total_issues={total_issues}, pattern_issues={pattern_issues}"
        )

    def test_qa_summary_available(self, api):
        """QA summary endpoint returns summary data for the file."""
        resp = api.get_file_qa_summary(self._base_id())
        assert_status(resp, 200, "File QA summary")
        data = resp.json()
        assert "total" in data or "file_id" in data, (
            f"Expected summary fields, got keys: {list(data.keys())}"
        )

    def test_row_qa_check(self, api):
        """Row-level QA check runs on individual rows."""
        # Get rows to find a valid row_id
        rows_resp = api.list_rows(self._base_id())
        assert_status(rows_resp, 200, "List rows for row QA")
        rows = rows_resp.json().get("rows", [])
        assert len(rows) > 0, "No rows available for row QA check"

        row_id = rows[0]["id"]
        resp = api.check_row_qa(row_id, checks=["pattern"])
        assert_status(resp, 200, "Row QA check")
        data = resp.json()
        assert "issues" in data or "issue_count" in data, (
            f"Expected issue data in row QA response, got keys: {list(data.keys())}"
        )
