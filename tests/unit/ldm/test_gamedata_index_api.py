"""Tests for GameData Index API endpoints.

Phase 29: Multi-Tier Indexing (Plan 02, Task 1)

Tests: POST /index/build, POST /index/search, POST /index/detect, GET /index/status
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def mock_auth():
    """Mock auth for route tests."""
    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """TestClient with app."""
    return TestClient(wrapped_app)


@pytest.fixture(autouse=True)
def reset_indexer_singleton():
    """Reset the indexer singleton between tests."""
    import server.tools.ldm.indexing.gamedata_indexer as mod
    mod._indexer_instance = None
    yield
    mod._indexer_instance = None


# Mock folder data returned by parse_folder
MOCK_FOLDER_DATA = MagicMock()
MOCK_FOLDER_DATA.total_nodes = 10

# Mock build result
MOCK_BUILD_RESULT = {
    "entity_count": 10,
    "whole_lookup_count": 25,
    "line_lookup_count": 5,
    "whole_embeddings_count": 10,
    "line_embeddings_count": 3,
    "ac_terms_count": 10,
    "build_time_ms": 150,
}

# Mock search result
MOCK_SEARCH_RESULT = {
    "tier": 1,
    "tier_name": "perfect_whole",
    "perfect_match": True,
    "results": [
        {
            "entity_name": "Blade of Dawn",
            "entity_desc": "A legendary sword",
            "node_id": "r0",
            "tag": "ItemInfo",
            "file_path": "/mock/items.xml",
            "score": 1.0,
            "match_type": "perfect_whole",
        }
    ],
}

# Mock detect result
MOCK_DETECT_RESULT = [
    {
        "term": "Blade of Dawn",
        "start": 4,
        "end": 17,
        "node_id": "r0",
        "tag": "ItemInfo",
        "entity_name": "Blade of Dawn",
    }
]


class TestIndexBuild:
    """Test POST /api/ldm/gamedata/index/build."""

    def test_index_build_requires_auth(self, client):
        """Build requires authentication."""
        response = client.post(
            "/api/ldm/gamedata/index/build",
            json={"path": "/some/path"},
        )
        assert response.status_code == 401

    @patch("server.tools.ldm.routes.gamedata.GameDataTreeService")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_build_success(
        self, mock_get_indexer, mock_tree_cls, client, mock_auth
    ):
        """Build with valid folder returns entity stats."""
        mock_svc = MagicMock()
        mock_svc.parse_folder.return_value = MOCK_FOLDER_DATA
        mock_tree_cls.return_value = mock_svc

        mock_indexer = MagicMock()
        mock_indexer.build_from_folder_tree.return_value = MOCK_BUILD_RESULT
        mock_get_indexer.return_value = mock_indexer

        response = client.post(
            "/api/ldm/gamedata/index/build",
            json={"path": "/valid/folder"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity_count"] == 10
        assert data["whole_lookup_count"] == 25
        assert data["status"] == "ready"

    @patch("server.tools.ldm.routes.gamedata.GameDataTreeService")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_build_not_found(
        self, mock_get_indexer, mock_tree_cls, client, mock_auth
    ):
        """Build with nonexistent folder returns 404."""
        mock_svc = MagicMock()
        mock_svc.parse_folder.side_effect = FileNotFoundError("Not found")
        mock_tree_cls.return_value = mock_svc

        response = client.post(
            "/api/ldm/gamedata/index/build",
            json={"path": "/nonexistent"},
        )
        assert response.status_code == 404

    @patch("server.tools.ldm.routes.gamedata.GameDataTreeService")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_build_empty_folder(
        self, mock_get_indexer, mock_tree_cls, client, mock_auth
    ):
        """Build with empty folder (no entities) returns 400."""
        mock_svc = MagicMock()
        empty_data = MagicMock()
        empty_data.total_nodes = 0
        mock_svc.parse_folder.return_value = empty_data
        mock_tree_cls.return_value = mock_svc

        response = client.post(
            "/api/ldm/gamedata/index/build",
            json={"path": "/empty/folder"},
        )
        assert response.status_code == 400


class TestIndexSearch:
    """Test POST /api/ldm/gamedata/index/search."""

    def test_index_search_requires_auth(self, client):
        """Search requires authentication."""
        response = client.post(
            "/api/ldm/gamedata/index/search",
            json={"query": "test"},
        )
        assert response.status_code == 401

    @patch("server.tools.ldm.routes.gamedata.GameDataSearcher")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_search_success(
        self, mock_get_indexer, mock_searcher_cls, client, mock_auth
    ):
        """Search after build returns tier and results."""
        mock_indexer = MagicMock()
        mock_indexer.is_ready = True
        mock_indexer.indexes = {"whole_lookup": {}}
        mock_get_indexer.return_value = mock_indexer

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = MOCK_SEARCH_RESULT
        mock_searcher_cls.return_value = mock_searcher

        response = client.post(
            "/api/ldm/gamedata/index/search",
            json={"query": "Blade of Dawn"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] >= 1
        assert len(data["results"]) > 0
        assert data["results"][0]["entity_name"] == "Blade of Dawn"

    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_search_not_ready(self, mock_get_indexer, client, mock_auth):
        """Search before build returns 400."""
        mock_indexer = MagicMock()
        mock_indexer.is_ready = False
        mock_get_indexer.return_value = mock_indexer

        response = client.post(
            "/api/ldm/gamedata/index/search",
            json={"query": "test"},
        )
        assert response.status_code == 400

    @patch("server.tools.ldm.routes.gamedata.GameDataSearcher")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_search_empty_query(
        self, mock_get_indexer, mock_searcher_cls, client, mock_auth
    ):
        """Search with empty query returns tier=0."""
        mock_indexer = MagicMock()
        mock_indexer.is_ready = True
        mock_indexer.indexes = {}
        mock_get_indexer.return_value = mock_indexer

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = {
            "tier": 0,
            "tier_name": "empty",
            "results": [],
            "perfect_match": False,
        }
        mock_searcher_cls.return_value = mock_searcher

        response = client.post(
            "/api/ldm/gamedata/index/search",
            json={"query": ""},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == 0


class TestIndexDetect:
    """Test POST /api/ldm/gamedata/index/detect."""

    def test_index_detect_requires_auth(self, client):
        """Detect requires authentication."""
        response = client.post(
            "/api/ldm/gamedata/index/detect",
            json={"text": "test"},
        )
        assert response.status_code == 401

    @patch("server.tools.ldm.routes.gamedata.GameDataSearcher")
    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_detect_success(
        self, mock_get_indexer, mock_searcher_cls, client, mock_auth
    ):
        """Detect after build returns entities with positions."""
        mock_indexer = MagicMock()
        mock_indexer.is_ready = True
        mock_indexer.indexes = {}
        mock_get_indexer.return_value = mock_indexer

        mock_searcher = MagicMock()
        mock_searcher.detect_entities.return_value = MOCK_DETECT_RESULT
        mock_searcher_cls.return_value = mock_searcher

        response = client.post(
            "/api/ldm/gamedata/index/detect",
            json={"text": "The Blade of Dawn"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert len(data["entities"]) > 0
        assert data["entities"][0]["entity_name"] == "Blade of Dawn"

    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_detect_not_ready(self, mock_get_indexer, client, mock_auth):
        """Detect before build returns 400."""
        mock_indexer = MagicMock()
        mock_indexer.is_ready = False
        mock_get_indexer.return_value = mock_indexer

        response = client.post(
            "/api/ldm/gamedata/index/detect",
            json={"text": "test"},
        )
        assert response.status_code == 400


class TestIndexStatus:
    """Test GET /api/ldm/gamedata/index/status."""

    def test_index_status_requires_auth(self, client):
        """Status requires authentication."""
        response = client.get("/api/ldm/gamedata/index/status")
        assert response.status_code == 401

    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_status_not_built(self, mock_get_indexer, client, mock_auth):
        """Status before build returns ready=false."""
        mock_indexer = MagicMock()
        mock_indexer.get_status.return_value = {
            "ready": False,
            "entity_count": 0,
            "build_time_ms": 0,
            "ac_terms_count": 0,
            "whole_lookup_count": 0,
            "line_lookup_count": 0,
        }
        mock_get_indexer.return_value = mock_indexer

        response = client.get("/api/ldm/gamedata/index/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["entity_count"] == 0

    @patch("server.tools.ldm.routes.gamedata.get_gamedata_indexer")
    def test_index_status_after_build(self, mock_get_indexer, client, mock_auth):
        """Status after build returns ready=true with entity_count > 0."""
        mock_indexer = MagicMock()
        mock_indexer.get_status.return_value = {
            "ready": True,
            "entity_count": 100,
            "build_time_ms": 250,
            "ac_terms_count": 80,
            "whole_lookup_count": 200,
            "line_lookup_count": 50,
        }
        mock_get_indexer.return_value = mock_indexer

        response = client.get("/api/ldm/gamedata/index/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["entity_count"] > 0
