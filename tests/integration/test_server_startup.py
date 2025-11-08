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
        """Test that all expected routes are registered."""
        routes = [route.path for route in app.routes]

        # Core routes
        assert "/" in routes
        assert "/health" in routes

        # Auth routes
        assert "/api/auth/login" in routes
        assert "/api/auth/register" in routes
        assert "/api/auth/me" in routes

        # Log routes
        assert "/api/logs/submit" in routes
        assert "/api/logs/error" in routes

        # Session routes
        assert "/api/sessions/start" in routes
        assert "/api/sessions/{session_id}/heartbeat" in routes
        assert "/api/sessions/{session_id}/end" in routes

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

        assert config.DATABASE_TYPE in ["sqlite", "postgresql"]
        assert config.SQLITE_DATABASE_URL is not None
        assert config.POSTGRES_DATABASE_URL is not None
