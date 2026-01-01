"""
Endpoint Existence Verification Tests

This test module verifies that all critical API endpoints exist and respond correctly.
It's designed to catch issues like the TM endpoint problem (UI-084) where frontend
was calling non-existent backend routes.

Run with: pytest server/tests/api/test_endpoint_existence.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from server.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for protected endpoints."""
    # Use DEV_MODE credentials
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestCoreEndpoints:
    """Test core system endpoints."""

    def test_health_endpoint(self, client):
        """GET /health should return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_api_status_endpoint(self, client, auth_headers):
        """GET /api/status should return 200."""
        response = client.get("/api/status", headers=auth_headers)
        assert response.status_code == 200

    def test_root_endpoint(self, client):
        """GET / should return 200."""
        response = client.get("/")
        assert response.status_code == 200


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_simple(self, client):
        """GET /api/health/simple should return 200."""
        response = client.get("/api/health/simple")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_status(self, client, auth_headers):
        """GET /api/health/status should return 200 (requires auth)."""
        response = client.get("/api/health/status", headers=auth_headers)
        # Returns 200 with auth, or 401 without - but never 404
        assert response.status_code in [200, 401]

    def test_health_ping(self, client):
        """GET /api/health/ping should return 200."""
        response = client.get("/api/health/ping")
        assert response.status_code == 200


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_endpoint_exists(self, client):
        """POST /api/v2/auth/login should accept requests."""
        # Even with wrong credentials, endpoint should exist (return 401, not 404)
        response = client.post(
            "/api/v2/auth/login",
            data={"username": "test", "password": "test"}
        )
        assert response.status_code in [200, 401, 422]  # Not 404

    def test_me_endpoint_exists(self, client, auth_headers):
        """GET /api/v2/auth/me should exist."""
        response = client.get("/api/v2/auth/me", headers=auth_headers)
        assert response.status_code in [200, 401]  # Not 404


class TestLDMEndpoints:
    """Test LDM tool endpoints."""

    def test_ldm_health(self, client):
        """GET /api/ldm/health should return 200."""
        response = client.get("/api/ldm/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_ldm_projects(self, client, auth_headers):
        """GET /api/ldm/projects should return 200."""
        response = client.get("/api/ldm/projects", headers=auth_headers)
        assert response.status_code in [200, 401]

    def test_ldm_tm_list(self, client, auth_headers):
        """GET /api/ldm/tm should return 200."""
        response = client.get("/api/ldm/tm", headers=auth_headers)
        assert response.status_code in [200, 401]

    def test_ldm_tm_suggest_exists(self, client, auth_headers):
        """GET /api/ldm/tm/suggest should exist (the critical endpoint from UI-084)."""
        # This endpoint requires parameters, but should not return 404
        response = client.get(
            "/api/ldm/tm/suggest",
            params={"source": "test"},
            headers=auth_headers
        )
        # Should be 200, 401, or 422 (validation error), but NOT 404/405
        assert response.status_code not in [404, 405], \
            f"TM suggest endpoint returned {response.status_code}. This is the endpoint that was missing in UI-084!"

    def test_ldm_settings_embedding_engines(self, client, auth_headers):
        """GET /api/ldm/settings/embedding-engines should exist."""
        response = client.get("/api/ldm/settings/embedding-engines", headers=auth_headers)
        assert response.status_code in [200, 401]


class TestProgressEndpoints:
    """Test progress/operations endpoints."""

    def test_operations_list(self, client, auth_headers):
        """GET /api/progress/operations should return 200."""
        response = client.get("/api/progress/operations", headers=auth_headers)
        assert response.status_code in [200, 401]


class TestToolHealthEndpoints:
    """Test tool-specific health endpoints."""

    def test_xlstransfer_health(self, client):
        """GET /api/v2/xlstransfer/health should return 200."""
        response = client.get("/api/v2/xlstransfer/health")
        assert response.status_code == 200

    def test_quicksearch_health(self, client):
        """GET /api/v2/quicksearch/health should return 200."""
        response = client.get("/api/v2/quicksearch/health")
        assert response.status_code == 200

    def test_krsimilar_health(self, client):
        """GET /api/v2/kr-similar/health should return 200."""
        response = client.get("/api/v2/kr-similar/health")
        assert response.status_code == 200


class TestCriticalEndpointsExist:
    """
    Test that critical endpoints used by frontend actually exist.

    These are endpoints that, if missing, would cause silent failures
    like the UI-084 TM matches issue.
    """

    CRITICAL_GET_ENDPOINTS = [
        "/health",
        "/api/health/simple",
        "/api/ldm/health",
        "/api/v2/xlstransfer/health",
        "/api/v2/quicksearch/health",
        "/api/v2/kr-similar/health",
    ]

    CRITICAL_AUTH_GET_ENDPOINTS = [
        "/api/status",
        "/api/ldm/projects",
        "/api/ldm/tm",
        "/api/progress/operations",
    ]

    @pytest.mark.parametrize("endpoint", CRITICAL_GET_ENDPOINTS)
    def test_critical_public_endpoint_exists(self, client, endpoint):
        """Verify critical public endpoints exist and respond."""
        response = client.get(endpoint)
        assert response.status_code != 404, f"Critical endpoint {endpoint} returned 404!"
        assert response.status_code != 405, f"Critical endpoint {endpoint} returned 405 (wrong method)!"

    @pytest.mark.parametrize("endpoint", CRITICAL_AUTH_GET_ENDPOINTS)
    def test_critical_auth_endpoint_exists(self, client, auth_headers, endpoint):
        """Verify critical authenticated endpoints exist and respond."""
        response = client.get(endpoint, headers=auth_headers)
        assert response.status_code != 404, f"Critical endpoint {endpoint} returned 404!"
        assert response.status_code != 405, f"Critical endpoint {endpoint} returned 405 (wrong method)!"


class TestNoOrphanFrontendCalls:
    """
    Verify that endpoints called by frontend actually exist.

    This test class is specifically designed to catch the UI-084 type bug
    where frontend calls endpoints that don't exist on the backend.
    """

    # Endpoints that frontend components call (from ENDPOINT_AUDIT.md)
    FRONTEND_CALLED_ENDPOINTS = {
        # LDM.svelte
        "GET /api/ldm/health": None,
        "GET /api/status": None,
        "POST /api/go-online": {"json": {}},
        # VirtualGrid.svelte - THE CRITICAL ONE
        "GET /api/ldm/tm/suggest": {"params": {"source": "test"}},
        # FileExplorer.svelte
        "GET /api/ldm/projects": None,
        "GET /api/ldm/tm": None,
        # TMManager.svelte
        "GET /api/ldm/settings/embedding-engines": None,
        "GET /api/ldm/settings/embedding-engine": None,
        # Health checks
        "GET /api/health/simple": None,
    }

    def test_frontend_endpoints_exist(self, client, auth_headers):
        """Verify all endpoints that frontend calls actually exist."""
        for endpoint_spec, params in self.FRONTEND_CALLED_ENDPOINTS.items():
            method, path = endpoint_spec.split(" ", 1)

            if method == "GET":
                if params and "params" in params:
                    response = client.get(path, params=params["params"], headers=auth_headers)
                else:
                    response = client.get(path, headers=auth_headers)
            elif method == "POST":
                json_data = params.get("json", {}) if params else {}
                response = client.post(path, json=json_data, headers=auth_headers)
            else:
                continue

            assert response.status_code != 404, \
                f"Frontend calls {endpoint_spec} but it returns 404!"
            assert response.status_code != 405, \
                f"Frontend calls {endpoint_spec} but it returns 405 (wrong method)!"


# Run with verbose output when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
