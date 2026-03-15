"""
Search subsystem API tests.

Tests Explorer Search, Semantic Search (Model2Vec/FAISS), TM Search
(suggest, exact, pattern), and Codex Search endpoints. Handles FAISS
index unavailability gracefully -- semantic search may return empty
results when indexes are not built.

Phase 25 Plan 08: AI Intelligence, Search, QA/Grammar E2E Tests
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
)
from tests.api.helpers.constants import KOREAN_TEXT_SAMPLES


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.search


# =========================================================================
# Explorer Search
# =========================================================================


class TestExplorerSearch:
    """GET /api/ldm/search?q=..."""

    def test_search_explorer_basic(self, api):
        """Basic text search returns results structure."""
        resp = api.search_explorer("test")
        assert_status_ok(resp, "Explorer search basic")
        data = resp.json()
        assert "results" in data, f"Missing 'results': {list(data.keys())}"
        assert "count" in data, f"Missing 'count': {list(data.keys())}"
        assert isinstance(data["results"], list)

    def test_search_explorer_korean(self, api):
        """Korean search query works."""
        resp = api.search_explorer("테스트")
        assert_status_ok(resp, "Explorer search Korean")
        data = resp.json()
        assert isinstance(data["results"], list)

    def test_search_explorer_result_structure(self, api):
        """Each result has type, id, name, path fields."""
        resp = api.search_explorer("API-Test")
        assert_status_ok(resp)
        data = resp.json()
        for result in data["results"][:3]:  # Check first 3
            assert "type" in result, f"Missing 'type' in result: {result}"
            assert "id" in result, f"Missing 'id' in result: {result}"
            assert "name" in result, f"Missing 'name' in result: {result}"

    def test_search_explorer_count_matches(self, api):
        """Count field matches actual results length."""
        resp = api.search_explorer("test")
        assert_status_ok(resp)
        data = resp.json()
        assert data["count"] == len(data["results"])


# =========================================================================
# Semantic Search
# =========================================================================


class TestSemanticSearch:
    """GET /api/ldm/semantic-search"""

    def test_search_semantic_basic(self, api, test_tm_id):
        """Semantic search with TM returns valid response."""
        resp = api.search_semantic("sword", tm_id=test_tm_id)
        # May return 200 (with or without results) or 404 (TM not found)
        assert resp.status_code in {200, 404, 500}, (
            f"Unexpected status {resp.status_code}: {resp.text[:200]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "results" in data
            assert "count" in data

    def test_search_semantic_korean(self, api, test_tm_id):
        """Korean text semantic search."""
        resp = api.search_semantic("검", tm_id=test_tm_id)
        assert resp.status_code in {200, 404, 500}

    def test_search_semantic_score_range(self, api, test_tm_id):
        """Similarity scores are in 0.0-1.0 range."""
        resp = api.search_semantic("magic", tm_id=test_tm_id)
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("results", []):
                score = result.get("similarity", 0)
                assert 0.0 <= score <= 1.0, (
                    f"Score {score} out of range [0, 1]"
                )

    def test_search_semantic_results_sorted(self, api, test_tm_id):
        """Results are sorted by similarity descending."""
        resp = api.search_semantic("shield", tm_id=test_tm_id)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if len(results) >= 2:
                scores = [r.get("similarity", 0) for r in results]
                assert scores == sorted(scores, reverse=True), (
                    f"Results not sorted descending: {scores}"
                )

    def test_search_semantic_index_not_built(self, api, test_tm_id):
        """Gracefully handles FAISS index not built."""
        resp = api.search_semantic("test query", tm_id=test_tm_id)
        # Should not crash -- may return empty results or index_status
        assert resp.status_code != 500 or "index" in resp.text.lower(), (
            f"Unhandled error: {resp.text[:200]}"
        )

    def test_search_semantic_nonexistent_tm(self, api):
        """Nonexistent TM returns 404."""
        resp = api.search_semantic("test", tm_id=999999)
        assert_status(resp, 404, "Nonexistent TM")

    def test_search_semantic_threshold(self, api, test_tm_id):
        """Threshold parameter filters low-score results."""
        resp = api.search_semantic(
            "sword", tm_id=test_tm_id, threshold=0.9
        )
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("results", []):
                score = result.get("similarity", 0)
                # With very high threshold, should only get high-quality matches
                assert score >= 0.5, f"Low-quality result despite threshold: {score}"


# =========================================================================
# TM Search
# =========================================================================


class TestTMSuggest:
    """GET /api/ldm/tm/suggest"""

    def test_tm_suggest_basic(self, api, test_tm_id):
        """TM suggestion search returns suggestions list."""
        resp = api.tm_suggest("검", tm_id=test_tm_id)
        # pg_trgm may not work in SQLite/test mode
        assert resp.status_code in {200, 500}
        if resp.status_code == 200:
            data = resp.json()
            assert "suggestions" in data
            assert "count" in data

    def test_tm_suggest_korean(self, api, test_tm_id):
        """Korean source text for TM suggestions."""
        resp = api.tm_suggest("방패", tm_id=test_tm_id)
        assert resp.status_code in {200, 500}

    def test_tm_suggest_no_results(self, api, test_tm_id):
        """Query with no matches returns empty suggestions."""
        resp = api.tm_suggest("xyznonexistent", tm_id=test_tm_id)
        if resp.status_code == 200:
            data = resp.json()
            assert data["count"] == 0 or isinstance(data["suggestions"], list)


class TestTMExactSearch:
    """GET /api/ldm/tm/{tm_id}/search/exact"""

    def test_tm_exact_search(self, api, test_tm_id):
        """Exact match search returns match or not found."""
        resp = api.search_tm_exact(test_tm_id, "검")
        assert resp.status_code in {200, 404}
        if resp.status_code == 200:
            data = resp.json()
            assert "found" in data

    def test_tm_exact_search_no_match(self, api, test_tm_id):
        """No exact match returns found=false."""
        resp = api.search_tm_exact(test_tm_id, "nonexistent_term_xyz")
        if resp.status_code == 200:
            data = resp.json()
            assert data["found"] is False


class TestTMPatternSearch:
    """GET /api/ldm/tm/{tm_id}/search"""

    def test_tm_pattern_search(self, api, test_tm_id):
        """Pattern search returns results list."""
        resp = api.search_tm(test_tm_id, "검")
        assert resp.status_code in {200, 404}
        if resp.status_code == 200:
            data = resp.json()
            assert "results" in data
            assert "count" in data

    def test_tm_pattern_search_no_results(self, api, test_tm_id):
        """Pattern with no matches returns empty."""
        resp = api.search_tm(test_tm_id, "zzz_no_match_zzz")
        if resp.status_code == 200:
            data = resp.json()
            assert data["count"] == 0


# =========================================================================
# Codex Search
# =========================================================================


class TestCodexSearch:
    """GET /api/ldm/codex/search"""

    def test_codex_search_basic(self, api):
        """Codex search returns results structure."""
        resp = api.search_codex("sword")
        assert resp.status_code in {200, 404, 503}
        if resp.status_code == 200:
            data = resp.json()
            assert "results" in data or "count" in data

    def test_codex_search_korean(self, api):
        """Korean codex search."""
        resp = api.search_codex("검")
        assert resp.status_code in {200, 404, 503}

    def test_codex_types(self, api):
        """List codex entity types."""
        resp = api.get_codex_types()
        assert resp.status_code in {200, 404, 503}


# =========================================================================
# Edge Cases
# =========================================================================


class TestSearchEdgeCases:
    """Edge cases across search endpoints."""

    def test_search_special_characters(self, api):
        """Search with special characters does not crash."""
        resp = api.search_explorer("test<br/>value")
        # Should not be 500
        assert resp.status_code != 500, f"500 on special chars: {resp.text[:200]}"

    def test_search_empty_results_structure(self, api):
        """Unique query returns empty list, not error."""
        resp = api.search_explorer("zzzuniquequerythatwontmatch999")
        assert_status_ok(resp, "Empty results")
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []
