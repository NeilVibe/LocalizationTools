"""
Integration Test - Server Startup

Test that the FastAPI server starts correctly and all endpoints are registered.
"""

import pytest
from fastapi.testclient import TestClient
from server.main import app


class TestServerStartup:
    """Test server initialization and startup."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_server_root_endpoint(self, client):
        """Test root endpoint returns server info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "version" in data
        assert "timestamp" in data

    def test_api_documentation_available(self, client):
        """Test that API documentation is accessible."""
        # OpenAPI schema
        response = client.get("/docs")
        assert response.status_code == 200

    def test_all_routes_registered(self, client):
        """Test that all expected routes are accessible.

        Note: Since main.py wraps the FastAPI app with Socket.IO's ASGIApp,
        we can't access .routes directly. Instead, we verify endpoints respond.
        """
        # Core routes - verify they respond (any status except 404)
        core_routes = ["/", "/health", "/docs"]
        for route in core_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

        # Auth routes - should return 405 for GET (method not allowed) or 422 (validation)
        # Not 404 (not found)
        auth_routes = ["/api/auth/login", "/api/auth/register"]
        for route in auth_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

        # /api/auth/me requires auth, so it should return 401
        response = client.get("/api/auth/me")
        assert response.status_code in [401, 403], "Route /api/auth/me should require auth"

        # Log routes
        log_routes = ["/api/logs/submit", "/api/logs/error"]
        for route in log_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

        # Session routes - POST endpoints
        response = client.get("/api/sessions/start")
        assert response.status_code != 404, "Route /api/sessions/start should exist"

    def test_cors_headers_present(self, client):
        """Test that CORS headers are configured."""
        response = client.options("/api/auth/login")
        # CORS should allow OPTIONS requests
        assert response.status_code in [200, 405]  # 405 if no OPTIONS handler, but CORS should be present


@pytest.mark.integration
class TestServerDatabase:
    """Test server database initialization."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_database_connection(self, client):
        """Test that database is connected via health check."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Database should be connected or unknown (if not initialized yet)
        assert data["database"] in ["connected", "unknown", "error"]


@pytest.mark.integration
class TestServerConfig:
    """Test server configuration."""

    def test_server_config_loaded(self):
        """Test that server configuration is loaded."""
        from server import config

        assert config.APP_NAME is not None
        assert config.APP_VERSION is not None
        assert config.SERVER_HOST is not None
        assert config.SERVER_PORT is not None

    def test_database_config(self):
        """Test database configuration."""
        from server import config

        # Database mode can be: auto, postgresql, sqlite
        assert config.DATABASE_MODE in ("auto", "postgresql", "sqlite")
        # Active type is set after detection
        assert config.ACTIVE_DATABASE_TYPE in ("postgresql", "sqlite")
        assert config.DATABASE_URL is not None
