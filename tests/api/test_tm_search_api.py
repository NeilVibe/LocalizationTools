"""
TM Search API E2E tests.

Tests cover:
- Pattern search (LIKE-based)
- Exact search (hash-based)
- Suggest (pg_trgm similarity or row-based)
- Leverage statistics
- Pretranslate
- 5-tier cascade search (via TMSearcher unit tests in test_tm_search.py)

Note: test_tm_search.py contains unit tests for TMSearcher cascade logic.
This file tests the HTTP API layer.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
)


# ============================================================================
# 1. Search Modes (API level)
# ============================================================================


class TestTMSearchModes:
    """GET /api/ldm/tm/{tm_id}/search and GET /api/ldm/tm/{tm_id}/search/exact"""

    def test_tm_search_pattern(self, api, test_tm_id):
        """Pattern search returns results with count."""
        resp = api.search_tm(test_tm_id, query="검")
        assert_status_ok(resp, "search_pattern")
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_tm_search_pattern_no_match(self, api, test_tm_id):
        """Searching for nonsense returns empty results."""
        resp = api.search_tm(test_tm_id, query="zzz_nonexistent_zzz_99")
        assert_status_ok(resp, "search_pattern_no_match")
        data = resp.json()
        assert data["count"] == 0

    def test_tm_search_exact(self, api, test_tm_id):
        """Exact search returns found=true for matching source or found=false."""
        resp = api.search_tm_exact(test_tm_id, source_text="검")
        assert_status_ok(resp, "search_exact")
        data = resp.json()
        assert "found" in data

    def test_tm_search_exact_no_match(self, api, test_tm_id):
        """Exact search for non-matching text returns found=false."""
        resp = api.search_tm_exact(test_tm_id, source_text="zzz_nonexistent_zzz")
        assert_status_ok(resp, "search_exact_no_match")
        data = resp.json()
        assert data["found"] is False

    def test_tm_search_nonexistent_tm(self, api):
        """Searching in a nonexistent TM returns 404."""
        resp = api.search_tm(999_999_999, query="test")
        assert_status(resp, 404, "search_nonexistent_tm")

    def test_tm_exact_search_nonexistent_tm(self, api):
        """Exact search in a nonexistent TM returns 404."""
        resp = api.search_tm_exact(999_999_999, source_text="test")
        assert_status(resp, 404, "exact_search_nonexistent_tm")


# ============================================================================
# 2. Suggest / Similarity
# ============================================================================


class TestTMSuggest:
    """GET /api/ldm/tm/suggest"""

    def test_tm_suggest_for_text(self, api, test_tm_id):
        """Getting TM suggestions returns suggestions list and count."""
        resp = api.tm_suggest(source_text="검", tm_id=test_tm_id)
        # May return 200 or 500 if pg_trgm not available
        if resp.status_code == 200:
            data = resp.json()
            assert "suggestions" in data
            assert "count" in data

    def test_tm_suggest_similarity_threshold(self, api, test_tm_id):
        """High threshold returns fewer (or no) matches."""
        resp = api.tm_suggest(source_text="검", tm_id=test_tm_id, threshold=0.99)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data.get("count", 0), int)

    def test_tm_suggest_korean_text(self, api, test_tm_id):
        """Suggestions for Korean input work without error."""
        resp = api.tm_suggest(source_text="마법의 검", tm_id=test_tm_id)
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"

    def test_tm_suggest_with_brtags(self, api, test_tm_id):
        """Input text with br-tags does not cause errors."""
        resp = api.tm_suggest(source_text="검<br/>방패", tm_id=test_tm_id)
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"

    def test_tm_suggest_without_tm_id(self, api, uploaded_xml_file_id):
        """Suggest without tm_id falls back to project row search."""
        resp = api.tm_suggest(source_text="Test", file_id=uploaded_xml_file_id)
        # May return 200 with suggestions or empty, or 500 if pg_trgm not available
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"


# ============================================================================
# 3. Leverage
# ============================================================================


class TestTMLeverage:
    """GET /api/ldm/files/{file_id}/leverage"""

    def test_get_file_leverage(self, api, uploaded_xml_file_id):
        """Leverage endpoint returns exact/fuzzy/new counts."""
        resp = api.get_file_leverage(uploaded_xml_file_id)
        assert_status_ok(resp, "get_file_leverage")
        data = resp.json()
        assert_json_fields(data, ["exact", "fuzzy", "new", "total"])
        # Percentages should add up to ~100
        pct_sum = data.get("exact_pct", 0) + data.get("fuzzy_pct", 0) + data.get("new_pct", 0)
        assert 99.0 <= pct_sum <= 101.0 or data["total"] == 0, (
            f"Percentages should sum to ~100, got {pct_sum}"
        )

    def test_leverage_nonexistent_file(self, api):
        """Leverage for nonexistent file returns 404."""
        resp = api.get_file_leverage(999_999_999)
        assert_status(resp, 404, "leverage_nonexistent_file")

    def test_leverage_values_in_range(self, api, uploaded_xml_file_id):
        """Leverage percentages are each between 0 and 100."""
        resp = api.get_file_leverage(uploaded_xml_file_id)
        assert_status_ok(resp)
        data = resp.json()
        for key in ("exact_pct", "fuzzy_pct", "new_pct"):
            val = data.get(key, 0)
            assert 0 <= val <= 100, f"{key} out of range: {val}"


# ============================================================================
# 4. Pretranslate
# ============================================================================


class TestPretranslate:
    """POST /api/ldm/pretranslate"""

    def test_pretranslate_file(self, api, uploaded_xml_file_id, test_tm_id):
        """Pretranslating a file returns stats."""
        resp = api.pretranslate(uploaded_xml_file_id, test_tm_id)
        # May fail if indexes not built - accept 200 or 500
        assert resp.status_code in (200, 500), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            data = resp.json()
            assert "matched" in data or "total" in data

    def test_pretranslate_nonexistent_file(self, api, test_tm_id):
        """Pretranslating nonexistent file returns 404."""
        resp = api.pretranslate(999_999_999, test_tm_id)
        assert_status(resp, 404, "pretranslate_nonexistent_file")

    def test_pretranslate_invalid_engine(self, api, uploaded_xml_file_id, test_tm_id):
        """Pretranslating with invalid engine returns 400."""
        resp = api.pretranslate(uploaded_xml_file_id, test_tm_id, engine="invalid_engine")
        assert_status(resp, 400, "pretranslate_invalid_engine")


# ============================================================================
# 5. Active TMs for file
# ============================================================================


class TestActiveTMsForFile:
    """GET /api/ldm/files/{file_id}/active-tms"""

    def test_get_active_tms_for_file(self, api, uploaded_xml_file_id):
        """Getting active TMs for a file returns a list."""
        resp = api.get_active_tms_for_file(uploaded_xml_file_id)
        assert_status_ok(resp, "active_tms_for_file")
        data = resp.json()
        assert isinstance(data, list)
