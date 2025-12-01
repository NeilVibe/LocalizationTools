"""
Integration Test - API Endpoints

Test all FastAPI endpoints with actual requests.
"""

import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.database.db_setup import setup_database, get_session_maker
from server.database.models import User
from server.utils.auth import hash_password


@pytest.fixture(scope="module")
def test_db():
    """Setup test database using a separate test database file.

    IMPORTANT: Uses drop_existing=False to avoid destroying the main database.
    This test uses a TestClient which shares the app's database.
    """
    # Do NOT drop the existing database - just get a session maker
    # The main database should already be set up with admin user
    engine, session_maker = setup_database(use_postgres=False, drop_existing=False)
    yield session_maker
    # No cleanup needed - we're using the main database


@pytest.fixture(scope="module")
def test_user(test_db):
    """Get or create a test user.

    IMPORTANT: Since we use drop_existing=False to preserve the main database,
    we must check if the user exists before creating to avoid UNIQUE constraint errors.
    """
    from sqlalchemy import select

    db = test_db()
    try:
        # Check if testuser already exists
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if existing_user:
            # Update password to ensure tests work (password may have been different)
            existing_user.password_hash = hash_password("testpassword123")
            db.commit()
            return existing_user

        # Create new test user if doesn't exist
        user = User(
            username="testuser",
            password_hash=hash_password("testpassword123"),
            email="test@example.com",
            full_name="Test User",
            department="Testing",
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "user_id" in data
        assert "username" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "testuser"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "password"}
        )
        assert response.status_code == 401

    def test_get_current_user_without_auth(self, client):
        """Test getting current user without authentication."""
        response = client.get("/api/auth/me")
        assert response.status_code == 403  # No auth header

    def test_get_current_user_with_auth(self, client, test_user):
        """Test getting current user with valid token."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"


@pytest.mark.integration
class TestLogEndpoints:
    """Test logging endpoints."""

    def test_submit_logs_without_auth(self, client):
        """Test log submission without authentication."""
        response = client.post(
            "/api/logs/submit",
            json={"session_id": "test-session", "logs": []}
        )
        assert response.status_code == 403  # No auth

    def test_submit_logs_with_auth(self, client, test_user):
        """Test log submission with authentication."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        token = login_response.json()["access_token"]

        # Submit logs (session_id is None since we don't have an active session)
        response = client.post(
            "/api/logs/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": None,
                "logs": [
                    {
                        "username": "testuser",
                        "machine_id": "test-machine-001",
                        "tool_name": "XLSTransfer",
                        "function_name": "create_dictionary",
                        "duration_seconds": 5.5,
                        "status": "success"
                    }
                ]
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["logs_received"] == 1

    def test_get_log_stats(self, client, test_user):
        """Test getting log statistics."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        token = login_response.json()["access_token"]

        # Get stats
        response = client.get(
            "/api/logs/stats/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_operations" in data
        assert "success_rate" in data


@pytest.mark.integration
class TestSessionEndpoints:
    """Test session management endpoints."""

    def test_start_session(self, client, test_user):
        """Test starting a session."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        token = login_response.json()["access_token"]

        # Start session
        response = client.post(
            "/api/sessions/start",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "machine_id": "test-machine-001",
                "ip_address": "127.0.0.1",
                "app_version": "1.0.0"
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert "session_id" in data
        assert data["machine_id"] == "test-machine-001"
        assert data["is_active"] is True

    def test_get_active_sessions(self, client, test_user):
        """Test getting active sessions."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpassword123"}
        )
        token = login_response.json()["access_token"]

        # Get active sessions
        response = client.get(
            "/api/sessions/active",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestVersionEndpoint:
    """Test version and announcement endpoints."""

    def test_get_latest_version(self, client):
        """Test getting latest version."""
        response = client.get("/api/version/latest")
        assert response.status_code == 200

        data = response.json()
        assert "latest_version" in data
        assert "download_url" in data

    def test_get_announcements(self, client):
        """Test getting announcements."""
        response = client.get("/api/announcements")
        assert response.status_code == 200

        data = response.json()
        assert "announcements" in data
        assert isinstance(data["announcements"], list)
