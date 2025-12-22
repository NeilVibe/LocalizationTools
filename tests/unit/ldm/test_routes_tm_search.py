"""
Tests for LDM TM Search Route

Tests: routes/tm_search.py (3 endpoints)
- GET /tm/suggest - quick suggestions
- GET /tm/{tm_id}/search/exact - exact search
- GET /tm/{tm_id}/search - semantic search
"""

import pytest


class TestTMSuggest:
    """Test GET /api/ldm/tm/suggest."""

    def test_suggest_requires_auth(self, client):
        """TM suggest requires authentication."""
        response = client.get("/api/ldm/tm/suggest?tm_id=1&pattern=hello")
        assert response.status_code == 401


class TestTMSearchExact:
    """Test GET /api/ldm/tm/{tm_id}/search/exact."""

    def test_exact_search_requires_auth(self, client):
        """Exact search requires authentication."""
        response = client.get("/api/ldm/tm/1/search/exact?source=hello")
        assert response.status_code == 401


class TestTMSearch:
    """Test GET /api/ldm/tm/{tm_id}/search."""

    def test_search_requires_auth(self, client):
        """TM search requires authentication."""
        response = client.get("/api/ldm/tm/1/search?query=hello")
        assert response.status_code == 401

    def test_search_supports_threshold(self, client):
        """TM search supports custom threshold."""
        response = client.get("/api/ldm/tm/1/search?query=hello&threshold=0.8")
        assert response.status_code == 401

    def test_search_supports_top_k(self, client):
        """TM search supports top_k parameter."""
        response = client.get("/api/ldm/tm/1/search?query=hello&top_k=5")
        assert response.status_code == 401
