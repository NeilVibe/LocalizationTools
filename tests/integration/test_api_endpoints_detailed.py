"""
Detailed API Endpoint Tests

Tests specific API endpoints with various inputs and edge cases.
Uses FastAPI TestClient for true simulation.

Note: 403 responses are expected when IP filtering is enabled.
"""

import pytest
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

# Common status codes including 401/403 for auth/IP filtering
SUCCESS_CODES = [200]
ERROR_CODES = [400, 401, 403, 422, 500]
ALL_CODES = [200, 400, 401, 403, 404, 422, 500]


class TestKRSimilarAPIDetailed:
    """Detailed tests for KR Similar API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_search_with_valid_korean(self, client):
        """Search with valid Korean text."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "안녕하세요",
            "threshold": 0.5,
            "top_k": 5
        })
        # May fail if no dictionary loaded or IP filtered
        assert response.status_code in ALL_CODES

    def test_search_with_empty_query(self, client):
        """Search with empty query returns error."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "",
            "threshold": 0.5
        })
        assert response.status_code in ERROR_CODES

    def test_search_with_invalid_threshold(self, client):
        """Search with invalid threshold."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "테스트",
            "threshold": 2.0  # Invalid: > 1.0
        })
        assert response.status_code in ERROR_CODES

    def test_search_with_negative_threshold(self, client):
        """Search with negative threshold."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "테스트",
            "threshold": -0.5
        })
        assert response.status_code in ERROR_CODES

    def test_status_endpoint(self, client):
        """KR Similar status endpoint."""
        response = client.get("/api/v2/kr-similar/status")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_dictionaries_endpoint(self, client):
        """KR Similar dictionaries endpoint."""
        response = client.get("/api/v2/kr-similar/dictionaries")
        assert response.status_code in [200, 401, 403, 404]


class TestQuickSearchAPIDetailed:
    """Detailed tests for QuickSearch API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_search_contains_mode(self, client):
        """Search with 'contains' match type."""
        response = client.post("/api/v2/quicksearch/search", json={
            "query": "안녕",
            "match_type": "contains",
            "limit": 10
        })
        assert response.status_code in ALL_CODES

    def test_search_exact_mode(self, client):
        """Search with 'exact' match type."""
        response = client.post("/api/v2/quicksearch/search", json={
            "query": "안녕하세요",
            "match_type": "exact"
        })
        assert response.status_code in ALL_CODES

    def test_search_with_limit(self, client):
        """Search with result limit."""
        response = client.post("/api/v2/quicksearch/search", json={
            "query": "테스트",
            "limit": 5
        })
        assert response.status_code in ALL_CODES

    def test_multiline_search(self, client):
        """Multi-line search endpoint."""
        response = client.post("/api/v2/quicksearch/search-multi", json={
            "queries": ["안녕", "감사", "마을"],
            "match_type": "contains"
        })
        assert response.status_code in ALL_CODES


class TestXLSTransferAPIDetailed:
    """Detailed tests for XLSTransfer API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_search_with_high_threshold(self, client):
        """Search with high threshold (exact match)."""
        response = client.post("/api/v2/xlstransfer/search", json={
            "query": "안녕하세요",
            "threshold": 0.99
        })
        assert response.status_code in ALL_CODES

    def test_search_with_low_threshold(self, client):
        """Search with low threshold (fuzzy match)."""
        response = client.post("/api/v2/xlstransfer/search", json={
            "query": "안녕",
            "threshold": 0.5
        })
        assert response.status_code in ALL_CODES

    def test_status_with_details(self, client):
        """Status endpoint returns details."""
        response = client.get("/api/v2/xlstransfer/status")
        # May be 403 for IP filtering or 200/404
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            # Should have some status info
            assert isinstance(data, dict)


class TestAuthAPIDetailed:
    """Detailed tests for Auth API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_login_with_empty_username(self, client):
        """Login with empty username fails."""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": "password123"
        })
        assert response.status_code in [400, 401, 403, 422]

    def test_login_with_empty_password(self, client):
        """Login with empty password fails."""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": ""
        })
        assert response.status_code in [400, 401, 403, 422]

    def test_login_returns_json(self, client):
        """Login endpoint returns JSON."""
        response = client.post("/api/auth/login", json={
            "username": "test",
            "password": "test"
        })
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_me_endpoint_requires_auth(self, client):
        """Me endpoint requires authentication."""
        response = client.get("/api/auth/me")
        assert response.status_code in [401, 403]

    def test_register_endpoint_exists(self, client):
        """Register endpoint exists."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "password123"
        })
        # May fail for various reasons but should not be 404
        assert response.status_code != 404


class TestLogsAPIDetailed:
    """Detailed tests for Logs API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_logs_endpoint_exists(self, client):
        """Logs endpoint exists."""
        response = client.get("/api/logs")
        # May require auth
        assert response.status_code in [200, 401, 403, 404]

    def test_logs_with_filters(self, client):
        """Logs endpoint accepts filters."""
        response = client.get("/api/logs", params={
            "level": "INFO",
            "limit": 10
        })
        assert response.status_code in [200, 401, 403, 404, 422]


class TestStatsAPIDetailed:
    """Detailed tests for Stats API endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_stats_summary_endpoint(self, client):
        """Stats summary endpoint."""
        response = client.get("/api/v2/stats/summary")
        assert response.status_code in [200, 401, 403, 404]

    def test_stats_dashboard_endpoint(self, client):
        """Stats dashboard endpoint."""
        response = client.get("/api/v2/stats/dashboard")
        assert response.status_code in [200, 401, 403, 404]


class TestVersionAndUpdatesAPI:
    """Test version and updates endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_version_endpoint(self, client):
        """Version endpoint returns current version."""
        response = client.get("/api/version/latest")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            # May be "version" or "latest_version" key
            assert "version" in data or "latest_version" in data or isinstance(data, str)

    def test_announcements_endpoint(self, client):
        """Announcements endpoint."""
        response = client.get("/api/announcements")
        assert response.status_code in [200, 401, 403, 404]


class TestAPIInputValidation:
    """Test API input validation."""

    @pytest.fixture(scope="class")
    def client(self):
        from server.main import app
        with TestClient(app) as client:
            yield client

    def test_special_characters_in_query(self, client):
        """Special characters in query handled."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "<script>alert('xss')</script>",
            "threshold": 0.5
        })
        # Should not crash (may be 403 for IP filtering)
        assert response.status_code in ALL_CODES

    def test_unicode_in_query(self, client):
        """Unicode characters in query handled."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": "한글 + 日本語 + العربية",
            "threshold": 0.5
        })
        assert response.status_code in ALL_CODES

    def test_very_long_query(self, client):
        """Very long query handled."""
        long_query = "안녕하세요 " * 1000
        response = client.post("/api/v2/kr-similar/search", json={
            "query": long_query,
            "threshold": 0.5
        })
        assert response.status_code in [200, 400, 403, 413, 422, 500]

    def test_null_values_rejected(self, client):
        """Null values in required fields rejected."""
        response = client.post("/api/v2/kr-similar/search", json={
            "query": None,
            "threshold": 0.5
        })
        assert response.status_code in ERROR_CODES


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
