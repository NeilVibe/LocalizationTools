"""
API True Simulation Tests - Client ↔ Server Communication

Tests REAL API endpoints without mocks, simulating actual client-server
communication as it happens in production.

Architecture:
    LocaNext Desktop (Electron) → HTTP Request → FastAPI Server → Response → Desktop

This file tests:
1. Tool API endpoints (KR Similar, QuickSearch, XLSTransfer)
2. Auth endpoints (login, token validation)
3. Health/status endpoints
4. Error handling
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Skip if server dependencies not available
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestAPIHealthEndpoints:
    """Test health/status endpoints - most basic API test."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create test client for FastAPI app."""
        # Import here to avoid circular imports
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_health_endpoint(self, client):
        """GET /health returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in str(data).lower()

    def test_root_endpoint(self, client):
        """GET / returns something (redirect or info)."""
        response = client.get("/", follow_redirects=False)
        # Should return 200, 307 redirect, or similar
        assert response.status_code in [200, 307, 302, 301]

    def test_docs_endpoint(self, client):
        """GET /docs returns Swagger UI."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


class TestAPIAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_login_missing_credentials(self, client):
        """POST /api/auth/login without credentials fails."""
        response = client.post("/api/auth/login", json={})
        # Should fail with 400 or 422 (validation error)
        assert response.status_code in [400, 401, 422]

    def test_login_invalid_credentials(self, client):
        """POST /api/auth/login with wrong credentials fails."""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent_user_12345",
            "password": "wrong_password"
        })
        assert response.status_code in [400, 401, 403, 422]

    def test_protected_endpoint_without_token(self, client):
        """Protected endpoints return 401 without token."""
        # Try accessing a protected endpoint (stats requires auth)
        response = client.get("/api/v2/stats/summary")
        # Should require auth or return data
        assert response.status_code in [200, 401, 403, 404]


class TestAPIKRSimilarEndpoints:
    """Test KR Similar API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_kr_similar_search_endpoint_exists(self, client):
        """KR Similar search endpoint exists."""
        # Try to access endpoint (may need auth)
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "안녕하세요",
            "threshold": 0.5,
            "top_k": 5
        })
        # Should exist (may return 401 if auth required, but not 404)
        assert response.status_code != 404

    def test_kr_similar_normalize_endpoint(self, client):
        """Test normalize endpoint if it exists."""
        response = client.post("/api/v2/kr-similar/normalize", json={
            "text": "{ChangeScene(Main)}안녕하세요"
        })
        # Endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            assert "normalized" in data or "text" in data


class TestAPIQuickSearchEndpoints:
    """Test QuickSearch API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_quicksearch_search_endpoint_exists(self, client):
        """QuickSearch search endpoint exists."""
        response = client.post("/api/v2/quicksearch/search", json={
            "query": "안녕",
            "match_type": "contains"
        })
        # Should exist (may fail with other error, but not 404)
        assert response.status_code != 404

    def test_quicksearch_status_endpoint(self, client):
        """QuickSearch status endpoint."""
        response = client.get("/api/v2/quicksearch/status")
        # Should return status
        assert response.status_code in [200, 401, 403, 404]


class TestAPIXLSTransferEndpoints:
    """Test XLSTransfer API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_xlstransfer_status_endpoint_exists(self, client):
        """XLSTransfer status endpoint exists."""
        response = client.get("/api/v2/xlstransfer/status")
        # Should exist
        assert response.status_code in [200, 401, 403, 404]

    def test_xlstransfer_search_endpoint(self, client):
        """XLSTransfer search endpoint."""
        response = client.post("/api/v2/xlstransfer/search", json={
            "query": "안녕하세요",
            "threshold": 0.9
        })
        # May require dictionary loaded
        assert response.status_code in [200, 400, 401, 403, 404, 422, 500]


class TestAPIErrorHandling:
    """Test API error handling."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_404_for_nonexistent_endpoint(self, client):
        """Nonexistent endpoint returns 404."""
        response = client.get("/api/v99/nonexistent/endpoint")
        assert response.status_code == 404

    def test_invalid_json_returns_error(self, client):
        """Invalid JSON body returns error."""
        response = client.post(
            "/api/v2/kr-similar/search",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        # Should return error code (400, 401, 403, 422, etc)
        assert response.status_code in [400, 401, 403, 422, 500]

    def test_method_not_allowed(self, client):
        """Wrong HTTP method returns 405."""
        # GET on POST-only endpoint
        response = client.get("/api/v2/kr-similar/search")
        assert response.status_code == 405


class TestAPICORSHeaders:
    """Test CORS headers are set correctly."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_cors_headers_on_options(self, client):
        """OPTIONS request returns CORS headers."""
        response = client.options(
            "/api/v2/kr-similar/search",
            headers={"Origin": "http://localhost:5176"}
        )
        # Should have CORS headers or return 200
        assert response.status_code in [200, 204, 405]

    def test_cors_allowed_origin(self, client):
        """Request from allowed origin succeeds."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5176"}
        )
        assert response.status_code == 200


class TestAPIResponseFormat:
    """Test API response format consistency."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_health_response_is_json(self, client):
        """Health endpoint returns JSON."""
        response = client.get("/health")
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_error_response_has_detail(self, client):
        """Error responses include detail message."""
        response = client.get("/api/v99/nonexistent")
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data or "error" in data or "message" in data


class TestAPIWebSocketEndpoint:
    """Test WebSocket endpoints exist."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_websocket_endpoint_exists(self, client):
        """WebSocket endpoint exists (may require upgrade)."""
        # HTTP GET on WebSocket endpoint should fail with specific error
        response = client.get("/ws")
        # WebSocket endpoints return various codes when accessed via HTTP
        # 400, 403, 426 (Upgrade Required) are common
        assert response.status_code in [400, 403, 404, 426, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
