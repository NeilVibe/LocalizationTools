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

try:
    import ahocorasick
    AC_AVAILABLE = True
except ImportError:
    AC_AVAILABLE = False


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

    def test_context_search_returns_results(self, client, mock_user):
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

        with patch("server.tools.ldm.routes.tm_search.get_current_active_user_async", return_value=mock_user), \
             patch("server.tools.ldm.routes.tm_search.get_tm_repository") as mock_get_repo, \
             patch("server.tools.ldm.routes.tm_search.TMIndexer") as MockIndexer:

            # Mock TMRepository
            mock_repo = AsyncMock()
            mock_repo.get = AsyncMock(return_value=mock_tm)
            mock_get_repo.return_value = mock_repo

            # Mock TMIndexer.load_indexes
            mock_indexer_instance = MagicMock()
            mock_indexer_instance.load_indexes.return_value = mock_indexes
            MockIndexer.return_value = mock_indexer_instance

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
            # Check tier_counts has expected keys
            assert "whole" in data["tier_counts"]
            assert "line" in data["tier_counts"]
            assert "fuzzy" in data["tier_counts"]

    def test_context_search_empty_source_returns_empty(self, client, mock_user):
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

        with patch("server.tools.ldm.routes.tm_search.get_current_active_user_async", return_value=mock_user), \
             patch("server.tools.ldm.routes.tm_search.get_tm_repository") as mock_get_repo, \
             patch("server.tools.ldm.routes.tm_search.TMIndexer") as MockIndexer:

            mock_repo = AsyncMock()
            mock_repo.get = AsyncMock(return_value=mock_tm)
            mock_get_repo.return_value = mock_repo

            mock_indexer_instance = MagicMock()
            mock_indexer_instance.load_indexes.return_value = mock_indexes
            MockIndexer.return_value = mock_indexer_instance

            response = client.post(
                "/api/ldm/tm/context",
                json={"source": "", "tm_id": 1}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["results"] == []

    def test_context_search_invalid_tm_returns_404(self, client, mock_user):
        """POST /tm/context with invalid tm_id returns 404."""
        with patch("server.tools.ldm.routes.tm_search.get_current_active_user_async", return_value=mock_user), \
             patch("server.tools.ldm.routes.tm_search.get_tm_repository") as mock_get_repo:

            mock_repo = AsyncMock()
            mock_repo.get = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            response = client.post(
                "/api/ldm/tm/context",
                json={"source": "test text", "tm_id": 9999}
            )

            assert response.status_code == 404
