"""
Tests for POST /api/ldm/tm/context endpoint.

Tests:
- POST /tm/context with valid source + tm_id returns 200 with results and tier_counts
- POST /tm/context with empty source returns 200 with empty results
- POST /tm/context with invalid tm_id returns 404
- Auth required
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories import get_tm_repository

try:
    import ahocorasick
    AC_AVAILABLE = True
except ImportError:
    AC_AVAILABLE = False

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


def _mock_user():
    """Return a mock authenticated user for dependency override."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_admin": False
    }


@pytest.mark.skipif(not AC_AVAILABLE, reason="ahocorasick not installed")
class TestContextSearchEndpoint:
    """Test POST /api/ldm/tm/context."""

    def test_context_search_requires_auth(self, client):
        """Context search requires authentication."""
        response = client.post(
            "/api/ldm/tm/context",
            json={"source": "test", "tm_id": 1}
        )
        assert response.status_code == 401

    def test_context_search_returns_results(self):
        """POST /tm/context with valid source + tm_id returns 200 with results and tier_counts."""
        from server.tools.ldm.indexing.utils import normalize_for_hash

        # Build a minimal mock indexes dict with AC automaton
        whole_lookup = {
            normalize_for_hash("무기 강화"): {
                "entry_id": 1,
                "source_text": "무기 강화",
                "target_text": "Weapon Enhancement",
                "string_id": None,
            }
        }
        whole_automaton = ahocorasick.Automaton()
        for idx, key in enumerate(whole_lookup):
            whole_automaton.add_word(key, (idx, key))
        whole_automaton.make_automaton()

        mock_indexes = {
            "tm_id": 1,
            "metadata": {},
            "whole_lookup": whole_lookup,
            "line_lookup": {},
            "whole_automaton": whole_automaton,
            "line_automaton": None,
        }

        mock_tm = {"id": 1, "name": "Test TM", "status": "ready"}

        # Set up dependency overrides on actual FastAPI app
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_tm)

        fastapi_app.dependency_overrides[get_current_active_user_async] = _mock_user
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repo

        try:
            with patch("server.tools.ldm.routes.tm_search.TMIndexer") as MockIndexer:
                mock_indexer_instance = MagicMock()
                mock_indexer_instance.load_indexes.return_value = mock_indexes
                MockIndexer.return_value = mock_indexer_instance

                client = TestClient(fastapi_app)
                response = client.post(
                    "/api/ldm/tm/context",
                    json={"source": "지금 무기 강화를 시작합니다", "tm_id": 1}
                )

                assert response.status_code == 200
                data = response.json()
                assert "results" in data
                assert "tier_counts" in data
                assert "total" in data
                assert isinstance(data["results"], list)
                assert data["total"] > 0
                assert "whole" in data["tier_counts"]
                assert "line" in data["tier_counts"]
                assert "fuzzy" in data["tier_counts"]
        finally:
            fastapi_app.dependency_overrides.clear()

    def test_context_search_empty_source_returns_empty(self):
        """POST /tm/context with empty source returns 200 with empty results."""
        mock_tm = {"id": 1, "name": "Test TM", "status": "ready"}

        mock_indexes = {
            "tm_id": 1,
            "metadata": {},
            "whole_lookup": {},
            "line_lookup": {},
            "whole_automaton": None,
            "line_automaton": None,
        }

        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=mock_tm)

        fastapi_app.dependency_overrides[get_current_active_user_async] = _mock_user
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repo

        try:
            with patch("server.tools.ldm.routes.tm_search.TMIndexer") as MockIndexer:
                mock_indexer_instance = MagicMock()
                mock_indexer_instance.load_indexes.return_value = mock_indexes
                MockIndexer.return_value = mock_indexer_instance

                client = TestClient(fastapi_app)
                response = client.post(
                    "/api/ldm/tm/context",
                    json={"source": "", "tm_id": 1}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 0
                assert data["results"] == []
        finally:
            fastapi_app.dependency_overrides.clear()

    def test_context_search_invalid_tm_returns_404(self):
        """POST /tm/context with invalid tm_id returns 404."""
        mock_repo = AsyncMock()
        mock_repo.get = AsyncMock(return_value=None)

        fastapi_app.dependency_overrides[get_current_active_user_async] = _mock_user
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repo

        try:
            client = TestClient(fastapi_app)
            response = client.post(
                "/api/ldm/tm/context",
                json={"source": "test text", "tm_id": 9999}
            )

            assert response.status_code == 404
        finally:
            fastapi_app.dependency_overrides.clear()
