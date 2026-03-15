"""
Tests for Naming Coherence REST endpoints.

Phase 21: AI Naming Coherence + Placeholders (Plan 01)
Requirements: AINAME-01, AINAME-02, AINAME-03, AINAME-05
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async

# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app

MOCK_USER = {
    "user_id": 1,
    "username": "testuser",
    "role": "user",
    "is_active": True,
    "dev_mode": False,
}


@pytest.fixture
def mock_auth():
    """Mock auth for route tests."""
    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield
    fastapi_app.dependency_overrides.clear()


def _make_mock_naming_service(
    similar_items=None,
    suggestions=None,
    suggest_status="ok",
    available=True,
):
    """Build a mock NamingCoherenceService."""
    service = MagicMock()

    if similar_items is None:
        similar_items = [
            {"name": "Eldric the Wise", "strkey": "CHR_ELDRIC", "similarity": 0.95, "entity_type": "character"},
            {"name": "Eldara of the North", "strkey": "CHR_ELDARA", "similarity": 0.85, "entity_type": "character"},
        ]

    if suggestions is None:
        suggestions = [
            {"name": "Eldric Stormborn", "confidence": 0.9, "reasoning": "Follows weather pattern"},
            {"name": "Eldric Ironforge", "confidence": 0.8, "reasoning": "Follows craft pattern"},
            {"name": "Eldric Dawnwalker", "confidence": 0.7, "reasoning": "Follows nature pattern"},
        ]

    service.find_similar_names.return_value = similar_items
    service.suggest_names = AsyncMock(return_value={
        "suggestions": suggestions,
        "status": suggest_status,
    })
    service.get_status.return_value = {
        "available": available,
        "cache_size": 3,
        "model": "qwen3:4b",
    }
    return service


class TestGetSimilarNames:
    """Test GET /api/ldm/naming/similar/{entity_type}."""

    def test_success(self, mock_auth):
        """AINAME-01: Returns 200 with NamingSimilarResponse shape."""
        mock_svc = _make_mock_naming_service()

        with patch(
            "server.tools.ldm.routes.naming._get_naming_service",
            return_value=mock_svc,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/naming/similar/character",
                params={"name": "Eldric"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
        assert len(data["items"]) == 2
        assert data["count"] == 2

    def test_empty(self, mock_auth):
        """Returns 200 with empty items for non-matching name."""
        mock_svc = _make_mock_naming_service(similar_items=[])

        with patch(
            "server.tools.ldm.routes.naming._get_naming_service",
            return_value=mock_svc,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/naming/similar/character",
                params={"name": "Xyzzyplugh"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["count"] == 0


class TestGetNamingSuggestions:
    """Test GET /api/ldm/naming/suggest/{entity_type}."""

    def test_success(self, mock_auth):
        """AINAME-02: Returns 200 with suggestions + similar_names."""
        mock_svc = _make_mock_naming_service()

        with patch(
            "server.tools.ldm.routes.naming._get_naming_service",
            return_value=mock_svc,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/naming/suggest/character",
                params={"name": "Eldric"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "similar_names" in data
        assert "status" in data
        assert len(data["suggestions"]) == 3
        assert data["status"] == "ok"

    def test_ollama_down(self, mock_auth):
        """AINAME-05: Ollama unavailable still returns 200 with empty suggestions."""
        mock_svc = _make_mock_naming_service(
            suggestions=[],
            suggest_status="unavailable",
        )

        with patch(
            "server.tools.ldm.routes.naming._get_naming_service",
            return_value=mock_svc,
        ):
            client = TestClient(wrapped_app)
            response = client.get(
                "/api/ldm/naming/suggest/character",
                params={"name": "Eldric"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["suggestions"] == []


class TestGetNamingStatus:
    """Test GET /api/ldm/naming/status."""

    def test_status(self, mock_auth):
        """Returns service availability info."""
        mock_svc = _make_mock_naming_service()

        with patch(
            "server.tools.ldm.routes.naming._get_naming_service",
            return_value=mock_svc,
        ):
            client = TestClient(wrapped_app)
            response = client.get("/api/ldm/naming/status")

        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "cache_size" in data
        assert "model" in data
