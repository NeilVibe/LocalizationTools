"""Tests for Codex REST endpoints.

Phase 19: Game World Codex (Plan 01, Task 2)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
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


def _mock_embedding_engine():
    """Create a mock embedding engine for tests."""
    engine = MagicMock()
    engine.dimension = 256
    engine.is_loaded = True

    def _encode(texts, normalize=True, show_progress=False):
        if isinstance(texts, str):
            texts = [texts]
        vecs = np.random.RandomState(42).randn(len(texts), 256).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vecs / norms

    engine.encode = _encode
    engine.load = MagicMock()
    return engine


@pytest.fixture
def mock_auth():
    """Mock auth for route tests."""
    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield
    fastapi_app.dependency_overrides.clear()


# Reset the codex service singleton between tests
@pytest.fixture(autouse=True)
def reset_codex_singleton():
    """Reset the codex service singleton between tests."""
    import server.tools.ldm.routes.codex as codex_module
    codex_module._codex_service = None
    yield
    codex_module._codex_service = None


@pytest.fixture
def client(mock_auth):
    """FastAPI TestClient with mocked auth and embedding engine."""
    mock_engine = _mock_embedding_engine()

    with patch("server.tools.ldm.services.codex_service.get_embedding_engine",
               return_value=mock_engine):
        yield TestClient(wrapped_app)


# =============================================================================
# Search endpoint tests
# =============================================================================


class TestSearchEndpoint:
    """Tests for GET /api/ldm/codex/search."""

    def test_search_returns_200(self, client):
        """GET /api/ldm/codex/search?q=sword returns 200 with CodexSearchResponse."""
        response = client.get("/api/ldm/codex/search", params={"q": "sword"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert "search_time_ms" in data

    def test_search_with_type_filter(self, client):
        """GET /api/ldm/codex/search?q=sword&entity_type=item filters to items."""
        response = client.get(
            "/api/ldm/codex/search",
            params={"q": "sword", "entity_type": "item"},
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert result["entity"]["entity_type"] == "item"


# =============================================================================
# Entity detail endpoint tests
# =============================================================================


class TestEntityEndpoint:
    """Tests for GET /api/ldm/codex/entity/{entity_type}/{strkey}."""

    def test_get_entity_found(self, client):
        """GET /api/ldm/codex/entity/character/STR_CHAR_0023 returns 200 (or 404 if MegaIndex not loaded)."""
        response = client.get("/api/ldm/codex/entity/character/STR_CHAR_0023")
        # In CI without gamedata, MegaIndex has no entities loaded → 404 is acceptable
        if response.status_code == 404:
            pytest.skip("MegaIndex not loaded in CI — entity not available")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "character"
        assert data["strkey"] == "STR_CHAR_0023"

    def test_get_entity_not_found(self, client):
        """GET /api/ldm/codex/entity/item/NONEXISTENT returns 404."""
        response = client.get("/api/ldm/codex/entity/item/NONEXISTENT")
        assert response.status_code == 404


# =============================================================================
# List endpoint tests
# =============================================================================


class TestListEndpoint:
    """Tests for GET /api/ldm/codex/list/{entity_type}."""

    def test_list_characters(self, client):
        """GET /api/ldm/codex/list/character returns 200 with entities."""
        response = client.get("/api/ldm/codex/list/character")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "character"
        assert data["count"] > 0
        assert len(data["entities"]) == data["count"]

    def test_list_unknown_type(self, client):
        """GET /api/ldm/codex/list/invalid_type returns 200 with empty list."""
        response = client.get("/api/ldm/codex/list/invalid_type")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["entities"] == []


# =============================================================================
# Types endpoint tests
# =============================================================================


class TestTypesEndpoint:
    """Tests for GET /api/ldm/codex/types."""

    def test_types_returns_counts(self, client):
        """GET /api/ldm/codex/types returns entity type counts."""
        response = client.get("/api/ldm/codex/types")
        assert response.status_code == 200
        data = response.json()
        assert "character" in data
        assert "item" in data
        assert isinstance(data["character"], int)
        assert data["character"] > 0
