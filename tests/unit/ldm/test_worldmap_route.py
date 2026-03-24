"""Tests for WorldMap REST endpoints.

Phase 20: Interactive World Map (Plan 01, Task 2)
"""

from __future__ import annotations

from unittest.mock import patch

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


@pytest.fixture(autouse=True)
def reset_worldmap_singleton():
    """Reset the worldmap service singleton between tests."""
    import server.tools.ldm.routes.worldmap as worldmap_module
    worldmap_module._worldmap_service = None
    yield
    worldmap_module._worldmap_service = None


@pytest.fixture
def client(mock_auth):
    """FastAPI TestClient with mocked auth."""
    yield TestClient(wrapped_app)


# =============================================================================
# GET /api/ldm/worldmap/data tests
# =============================================================================


class TestGetMapData:
    """Tests for GET /api/ldm/worldmap/data."""

    def test_get_map_data_success(self, client):
        """GET /api/ldm/worldmap/data returns 200 with nodes and routes."""
        response = client.get("/api/ldm/worldmap/data")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "routes" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["routes"], list)

    def test_map_data_node_fields(self, client):
        """Response nodes have required fields: strkey, name, x, z, region_type."""
        response = client.get("/api/ldm/worldmap/data")
        assert response.status_code == 200
        data = response.json()

        assert len(data["nodes"]) == 14
        node = data["nodes"][0]
        assert "strkey" in node
        assert "name" in node
        assert "x" in node
        assert "z" in node
        assert "region_type" in node

    def test_map_data_route_fields(self, client):
        """Response routes have from_node, to_node, waypoints fields."""
        response = client.get("/api/ldm/worldmap/data")
        assert response.status_code == 200
        data = response.json()

        assert len(data["routes"]) >= 13  # fixture expanded from 13 to 17 routes
        route = data["routes"][0]
        assert "from_node" in route
        assert "to_node" in route
        assert "waypoints" in route
        assert isinstance(route["waypoints"], list)

    def test_map_data_bounds(self, client):
        """Response includes bounds dict with min/max X/Z."""
        response = client.get("/api/ldm/worldmap/data")
        assert response.status_code == 200
        data = response.json()

        bounds = data["bounds"]
        assert "min_x" in bounds
        assert "max_x" in bounds
        assert "min_z" in bounds
        assert "max_z" in bounds
        assert isinstance(bounds["min_x"], float)
