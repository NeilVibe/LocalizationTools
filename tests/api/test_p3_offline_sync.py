"""
Tests for P3: Offline/Online Sync Mode

Tests:
1. Offline Status - Check mode and stats
2. Subscribe - Subscribe platform/project/file for offline
3. Unsubscribe - Remove subscription
4. List Subscriptions - Get all active subscriptions
5. Download for Offline - Download file with rows to SQLite

Run: pytest tests/api/test_p3_offline_sync.py -v
Requires: Server running at localhost:8888 with test data
"""

import os
import pytest
import httpx
from typing import Optional

BASE_URL = "http://localhost:8888"


def _check_postgresql_available():
    """
    Check if PostgreSQL is available for tests that require online mode.
    Subscription tests require PostgreSQL (they return 400 in SQLite mode).
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    pg_user = os.getenv("POSTGRES_USER", "locanext")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "locanext_password")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "6433")
    pg_db = os.getenv("POSTGRES_DB", "locanext")

    db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

    try:
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, Exception):
        return False


# Check once at import time
_postgresql_available = _check_postgresql_available()

# Skip marker for tests that require PostgreSQL (online mode)
requires_postgresql = pytest.mark.skipif(
    not _postgresql_available,
    reason="Test requires PostgreSQL (subscription endpoints return 400 in SQLite mode)"
)


@pytest.fixture
def admin_headers():
    """Get auth headers for admin user."""
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_file_id(admin_headers):
    """Get or create a test file for sync tests."""
    # First, get projects
    response = httpx.get(f"{BASE_URL}/api/ldm/projects", headers=admin_headers)
    if response.status_code == 200:
        projects = response.json()
        if projects:
            project_id = projects[0]["id"]
            # Get files in project
            tree_resp = httpx.get(
                f"{BASE_URL}/api/ldm/projects/{project_id}/tree",
                headers=admin_headers
            )
            if tree_resp.status_code == 200:
                tree = tree_resp.json().get("tree", [])
                for item in tree:
                    if item["type"] == "file":
                        return item["id"]

    # If no file found, skip test
    pytest.skip("No test file available")


@pytest.fixture
def test_project_id(admin_headers):
    """Get a test project ID."""
    response = httpx.get(f"{BASE_URL}/api/ldm/projects", headers=admin_headers)
    if response.status_code == 200:
        projects = response.json()
        if projects:
            return projects[0]["id"]
    pytest.skip("No test project available")


class TestOfflineStatus:
    """Test offline status endpoint."""

    def test_get_offline_status(self, admin_headers):
        """Test getting offline status."""
        response = httpx.get(
            f"{BASE_URL}/api/ldm/offline/status",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "mode" in data
        assert data["mode"] in ["online", "offline"]
        assert "offline_available" in data
        assert "file_count" in data
        assert "pending_changes" in data
        assert isinstance(data["file_count"], int)
        assert isinstance(data["pending_changes"], int)


class TestSubscriptions:
    """Test subscription management."""

    def test_list_subscriptions_empty(self, admin_headers):
        """Test listing subscriptions (may be empty initially)."""
        response = httpx.get(
            f"{BASE_URL}/api/ldm/offline/subscriptions",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "subscriptions" in data
        assert "total_count" in data
        assert isinstance(data["subscriptions"], list)

    def test_subscribe_file(self, admin_headers, test_file_id):
        """Test subscribing a file for offline sync."""
        response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "file",
                "entity_id": test_file_id,
                "entity_name": "test_file.txt"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "subscription_id" in data
        assert data["subscription_id"] > 0

    def test_subscribe_with_auto_flag(self, admin_headers, test_file_id):
        """Test subscribing with auto_subscribed flag (simulating file open)."""
        response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "file",
                "entity_id": test_file_id,
                "entity_name": "auto_synced_file.txt",
                "auto_subscribed": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_unsubscribe_file(self, admin_headers, test_file_id):
        """Test unsubscribing a file from offline sync."""
        # First subscribe
        httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "file",
                "entity_id": test_file_id,
                "entity_name": "to_unsub.txt"
            }
        )

        # Then unsubscribe
        response = httpx.delete(
            f"{BASE_URL}/api/ldm/offline/subscribe/file/{test_file_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @requires_postgresql
    def test_subscribe_project(self, admin_headers, test_project_id):
        """Test subscribing a project for offline sync."""
        # Project sync downloads all files - needs longer timeout
        response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "project",
                "entity_id": test_project_id,
                "entity_name": "Test Project"
            },
            timeout=60.0  # Projects may have many files
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_subscription_appears_in_list(self, admin_headers, test_file_id):
        """Test that subscribed items appear in subscription list."""
        # Subscribe
        httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "file",
                "entity_id": test_file_id,
                "entity_name": "listed_file.txt"
            }
        )

        # Check list
        response = httpx.get(
            f"{BASE_URL}/api/ldm/offline/subscriptions",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Find our subscription
        found = any(
            s["entity_type"] == "file" and s["entity_id"] == test_file_id
            for s in data["subscriptions"]
        )
        assert found, "Subscribed file not found in subscription list"


class TestDownloadForOffline:
    """Test file download for offline use."""

    def test_download_file_for_offline(self, admin_headers, test_file_id):
        """Test downloading a file for offline use."""
        response = httpx.post(
            f"{BASE_URL}/api/ldm/files/{test_file_id}/download-for-offline",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["file_id"] == test_file_id
        assert "file_name" in data
        assert "row_count" in data
        assert isinstance(data["row_count"], int)


class TestOfflineFiles:
    """Test listing offline files."""

    def test_list_offline_files(self, admin_headers):
        """Test listing files available for offline use."""
        response = httpx.get(
            f"{BASE_URL}/api/ldm/offline/files",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "files" in data
        assert "total_count" in data
        assert isinstance(data["files"], list)


class TestContinuousSync:
    """Test continuous sync mechanism."""

    @requires_postgresql
    def test_sync_subscription_requires_subscription(self, admin_headers):
        """Test that sync-subscription fails without subscription."""
        response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/sync-subscription",
            headers=admin_headers,
            json={
                "entity_type": "file",
                "entity_id": 99999  # Non-existent
            },
            timeout=30.0
        )
        # Should return 404 (subscription not found) or 500 (file not found)
        assert response.status_code in [404, 500]

    @requires_postgresql
    def test_sync_subscription_with_project(self, admin_headers, test_project_id):
        """Test syncing a project subscription."""
        # First subscribe
        sub_response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/subscribe",
            headers=admin_headers,
            json={
                "entity_type": "project",
                "entity_id": test_project_id,
                "entity_name": "Test Project"
            },
            timeout=60.0
        )
        assert sub_response.status_code == 200

        # Now sync
        response = httpx.post(
            f"{BASE_URL}/api/ldm/offline/sync-subscription",
            headers=admin_headers,
            json={
                "entity_type": "project",
                "entity_id": test_project_id
            },
            timeout=60.0
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "updated_count" in data


class TestHealthChecks:
    """Quick health checks for P3 endpoints."""

    def test_all_p3_endpoints_exist(self, admin_headers):
        """Verify all P3 endpoints are accessible."""
        endpoints = [
            ("GET", "/api/ldm/offline/status"),
            ("GET", "/api/ldm/offline/subscriptions"),
            ("GET", "/api/ldm/offline/files"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = httpx.get(f"{BASE_URL}{endpoint}", headers=admin_headers)

            # Should not be 404 or 405
            assert response.status_code not in [404, 405], \
                f"{method} {endpoint} returned {response.status_code}"


# Quick standalone test runner
if __name__ == "__main__":
    """Run basic health checks without pytest."""
    import sys

    print("P3 Offline/Sync - Quick Health Check")
    print("=" * 50)

    # Login
    print("1. Logging in as admin...")
    resp = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if resp.status_code != 200:
        print(f"   FAIL: Login failed - {resp.text}")
        sys.exit(1)
    print("   OK: Logged in")

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test endpoints
    tests = [
        ("GET /api/ldm/offline/status", "GET", "/api/ldm/offline/status"),
        ("GET /api/ldm/offline/subscriptions", "GET", "/api/ldm/offline/subscriptions"),
        ("GET /api/ldm/offline/files", "GET", "/api/ldm/offline/files"),
    ]

    passed = 0
    failed = 0

    for name, method, endpoint in tests:
        print(f"2. Testing {name}...")
        if method == "GET":
            resp = httpx.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30.0)

        if resp.status_code == 200:
            print(f"   OK: {resp.status_code}")
            passed += 1
        else:
            print(f"   FAIL: {resp.status_code} - {resp.text[:100]}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
