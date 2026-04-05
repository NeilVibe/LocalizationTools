"""
EMB-003: Test maintenance routes (integration).

Tests the API endpoints for TM maintenance.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def client():
    """Create test client."""
    # Import app lazily to avoid import issues
    from server.main import app
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "user_id": 1,
        "username": "testuser",
        "role": "admin"
    }


@pytest.fixture
def auth_headers():
    """Auth headers for authenticated requests."""
    # In tests, we need a valid token or mock auth
    return {"Authorization": "Bearer test_token_12345"}


class TestMaintenanceRoutes:
    """Test maintenance API routes."""

    @pytest.mark.asyncio
    async def test_check_stale_tms_endpoint_exists(self, client):
        """Test that check-stale endpoint exists (will fail auth but route exists)."""
        response = client.post("/api/ldm/maintenance/check-stale")
        # Should get 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_get_stale_tms_endpoint_exists(self, client):
        """Test that stale-tms endpoint exists."""
        response = client.get("/api/ldm/maintenance/stale-tms")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_sync_status_endpoint_exists(self, client):
        """Test that sync-status endpoint exists."""
        response = client.get("/api/ldm/maintenance/sync-status")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_queue_sync_endpoint_exists(self, client):
        """Test that queue sync endpoint exists."""
        response = client.post("/api/ldm/maintenance/sync/1")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_cancel_sync_endpoint_exists(self, client):
        """Test that cancel sync endpoint exists."""
        response = client.delete("/api/ldm/maintenance/sync/1")
        assert response.status_code in [401, 403]
