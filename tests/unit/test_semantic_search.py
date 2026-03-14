"""
Tests for Semantic Search API Endpoint

Tests the GET /api/ldm/semantic-search endpoint that wires
TMSearcher 5-Tier Cascade into a REST API.

Run with: python3 -m pytest tests/unit/test_semantic_search.py -v
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.tools.ldm.routes.semantic_search import router
from server.utils.dependencies import get_current_active_user_async
from server.repositories import get_tm_repository


# ---------------------------------------------------------------------------
# Test App Setup
# ---------------------------------------------------------------------------

MOCK_USER = {"id": 1, "username": "testuser", "role": "admin"}

MOCK_SEARCH_RESULTS = {
    "tier": 2,
    "tier_name": "whole_embedding",
    "perfect_match": False,
    "results": [
        {
            "entry_id": 1,
            "source_text": "Save the file",
            "target_text": "\ud30c\uc77c\uc744 \uc800\uc7a5\ud558\uae30",
            "string_id": "STR_001",
            "score": 0.95,
            "match_type": "whole_embedding",
        },
        {
            "entry_id": 2,
            "source_text": "Save your progress",
            "target_text": "\uc9c4\ud589 \uc0c1\ud669\uc744 \uc800\uc7a5\ud558\uae30",
            "string_id": "STR_002",
            "score": 0.87,
            "match_type": "whole_embedding",
        },
        {
            "entry_id": 3,
            "source_text": "Save and exit",
            "target_text": "\uc800\uc7a5\ud558\uace0 \uc885\ub8cc\ud558\uae30",
            "string_id": "STR_003",
            "score": 0.72,
            "match_type": "whole_embedding",
        },
    ],
}


def _make_app_and_client(tm_repo_mock):
    """Create test app with dependency overrides."""
    app = FastAPI()
    app.include_router(router, prefix="/api/ldm")
    app.dependency_overrides[get_current_active_user_async] = lambda: MOCK_USER
    app.dependency_overrides[get_tm_repository] = lambda: tm_repo_mock
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Basic search returns results with similarity scores
# ---------------------------------------------------------------------------

class TestSemanticSearchBasic:
    """Test basic semantic search endpoint functionality."""

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_search_returns_results_with_scores(self, mock_indexer_cls, mock_searcher_cls):
        """GET /api/ldm/semantic-search with query + tm_id returns results with similarity scores."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        response = client.get("/api/ldm/semantic-search", params={"query": "save file", "tm_id": 1})

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3
        for result in data["results"]:
            assert "similarity" in result
            assert isinstance(result["similarity"], float)

    # ---------------------------------------------------------------------------
    # Test 2: Results ranked by similarity descending
    # ---------------------------------------------------------------------------

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_results_ranked_by_similarity_descending(self, mock_indexer_cls, mock_searcher_cls):
        """Results are ranked by similarity descending."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1})

        assert response.status_code == 200
        data = response.json()
        scores = [r["similarity"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True), "Results must be ranked by similarity descending"

    # ---------------------------------------------------------------------------
    # Test 3: Threshold filters low-similarity results
    # ---------------------------------------------------------------------------

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_threshold_parameter_passed_to_searcher(self, mock_indexer_cls, mock_searcher_cls):
        """Threshold parameter is passed through to TMSearcher."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1, "threshold": 0.9})

        assert response.status_code == 200
        mock_searcher_cls.return_value.search.assert_called_once()
        call_kwargs = mock_searcher_cls.return_value.search.call_args
        assert call_kwargs[1].get("threshold") == 0.9

    # ---------------------------------------------------------------------------
    # Test 4: max_results limits result count
    # ---------------------------------------------------------------------------

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_max_results_limits_count(self, mock_indexer_cls, mock_searcher_cls):
        """max_results parameter limits result count via top_k."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1, "max_results": 5})

        assert response.status_code == 200
        mock_searcher_cls.return_value.search.assert_called_once()
        call_kwargs = mock_searcher_cls.return_value.search.call_args
        assert call_kwargs[1].get("top_k") == 5


# ---------------------------------------------------------------------------
# Test 5: Missing tm_id returns 422
# ---------------------------------------------------------------------------

class TestSemanticSearchValidation:
    """Test validation and error cases."""

    def test_missing_tm_id_returns_422(self):
        """Missing tm_id returns 422 (validation error)."""
        mock_repo = AsyncMock()
        client = _make_app_and_client(mock_repo)
        response = client.get("/api/ldm/semantic-search", params={"query": "save"})
        assert response.status_code == 422

    def test_missing_query_returns_422(self):
        """Missing query returns 422 (validation error)."""
        mock_repo = AsyncMock()
        client = _make_app_and_client(mock_repo)
        response = client.get("/api/ldm/semantic-search", params={"tm_id": 1})
        assert response.status_code == 422

    # ---------------------------------------------------------------------------
    # Test 6: Invalid tm_id returns 404
    # ---------------------------------------------------------------------------

    def test_invalid_tm_id_returns_404(self):
        """Invalid tm_id returns 404."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = None  # TM not found
        client = _make_app_and_client(mock_repo)

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 99999})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 7: Performance - sub-second endpoint overhead
# ---------------------------------------------------------------------------

class TestSemanticSearchPerformance:
    """Test performance characteristics."""

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_search_completes_under_one_second(self, mock_indexer_cls, mock_searcher_cls):
        """Single search completes in under 1 second (mocked FAISS, endpoint overhead only)."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        start = time.time()
        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1})
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Search took {elapsed:.2f}s, must be under 1s"

        data = response.json()
        assert "search_time_ms" in data
        assert isinstance(data["search_time_ms"], float)


# ---------------------------------------------------------------------------
# Test 8: Response shape matches expected format
# ---------------------------------------------------------------------------

class TestSemanticSearchResponseShape:
    """Test response shape and structure."""

    @patch("server.tools.ldm.routes.semantic_search.TMSearcher")
    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_response_shape(self, mock_indexer_cls, mock_searcher_cls):
        """Response matches {results: [{source_text, target_text, similarity, match_type, tier}], count, search_time_ms}."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.return_value = {"whole_lookup": {}, "line_lookup": {}}
        mock_searcher_cls.return_value.search.return_value = MOCK_SEARCH_RESULTS

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1})

        assert response.status_code == 200
        data = response.json()

        # Top-level shape
        assert "results" in data
        assert "count" in data
        assert "search_time_ms" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["search_time_ms"], float)

        # Each result shape
        for result in data["results"]:
            assert "source_text" in result
            assert "target_text" in result
            assert "similarity" in result
            assert "match_type" in result
            assert "tier" in result


# ---------------------------------------------------------------------------
# Test: No FAISS index returns empty with status
# ---------------------------------------------------------------------------

class TestSemanticSearchEdgeCases:
    """Test edge cases like missing indexes."""

    @patch("server.tools.ldm.routes.semantic_search.TMIndexer")
    def test_no_index_returns_not_built_status(self, mock_indexer_cls):
        """Missing FAISS index returns {results: [], index_status: 'not_built'}."""
        mock_repo = AsyncMock()
        mock_repo.get.return_value = {"id": 1, "name": "Test TM", "entry_count": 100}
        client = _make_app_and_client(mock_repo)

        mock_indexer_cls.return_value.load_indexes.side_effect = FileNotFoundError("TM indexes not found")

        response = client.get("/api/ldm/semantic-search", params={"query": "save", "tm_id": 1})

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["index_status"] == "not_built"
