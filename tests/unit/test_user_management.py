"""
Unit Tests for User Management System

Tests for:
- User profile fields (team, language, created_by, etc.)
- Change password functionality
- Admin user management (create, update, reset password, delete)

TRUE SIMULATION: These tests run against a real server with real database.
"""

import pytest
import requests
from datetime import datetime
import time

# Unique suffix for test users to avoid conflicts
TEST_SUFFIX = str(int(time.time()))[-6:]

# Test configuration
BASE_URL = "http://localhost:8888"
API_URL = f"{BASE_URL}/api/v2"

# Skip if server not running (check safely without crashing at import)
def _server_running():
    try:
        return requests.get(f"{BASE_URL}/health", timeout=2).ok
    except Exception:
        return False

pytestmark = pytest.mark.skipif(
    not _server_running(),
    reason="Server not running"
)


def get_admin_token():
    """Get admin authentication token."""
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def create_test_user(token, username, password="testpass123", **kwargs):
    """Helper to create a test user."""
    data = {
        "username": username,
        "password": password,
        "must_change_password": False,
        **kwargs
    }
    response = requests.post(
        f"{API_URL}/auth/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    return response


def cleanup_test_user(token, user_id):
    """Helper to clean up test user."""
    requests.delete(
        f"{API_URL}/auth/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )


class TestUserProfileFields:
    """Test user profile fields are stored and retrieved correctly."""

    def test_user_response_includes_new_fields(self):
        """Verify UserResponse includes team, language, created_by, etc."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        response = requests.get(
            f"{API_URL}/auth/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0

        # Check admin user has all required fields
        admin = users[0]
        assert "team" in admin
        assert "language" in admin
        assert "created_by" in admin
        assert "last_password_change" in admin
        assert "must_change_password" in admin

    def test_create_user_with_profile_fields(self):
        """Test creating user with team and language."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Create user with full profile (unique username)
        response = create_test_user(
            token,
            username=f"test_profile_{TEST_SUFFIX}",
            full_name="Test User",
            team="Team Alpha",
            language="Japanese"
        )

        assert response.status_code == 201
        user = response.json()

        assert user["full_name"] == "Test User"
        assert user["team"] == "Team Alpha"
        assert user["language"] == "Japanese"
        assert user["created_by"] == 1  # Created by admin (user_id=1)

        # Cleanup
        cleanup_test_user(token, user["user_id"])

    def test_created_by_tracks_admin(self):
        """Verify created_by field tracks who created the user."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        response = create_test_user(token, username=f"test_created_{TEST_SUFFIX}")

        assert response.status_code == 201
        user = response.json()

        # Admin user_id is 1
        assert user["created_by"] == 1

        cleanup_test_user(token, user["user_id"])


class TestChangePassword:
    """Test user password change functionality."""

    def test_change_password_success(self):
        """User can change their own password."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        # Create test user
        response = create_test_user(
            admin_token,
            username="test_pw_change",
            password="oldpass123"
        )

        if response.status_code == 400 and "already exists" in response.text:
            # Reset password to known value
            users_resp = requests.get(
                f"{API_URL}/auth/users",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            user = next((u for u in users_resp.json() if u["username"] == "test_pw_change"), None)
            if user:
                requests.put(
                    f"{API_URL}/auth/admin/users/{user['user_id']}/reset-password",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"new_password": "oldpass123", "must_change_password": False}
                )
        else:
            assert response.status_code == 201

        # Login as test user
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_pw_change", "password": "oldpass123"}
        )
        assert login_resp.status_code == 200
        user_token = login_resp.json()["access_token"]

        # Change password
        change_resp = requests.put(
            f"{API_URL}/auth/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": "oldpass123",
                "new_password": "newpass456",
                "confirm_password": "newpass456"
            }
        )
        assert change_resp.status_code == 200
        assert "Password changed successfully" in change_resp.json()["message"]

        # Verify new password works
        new_login = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_pw_change", "password": "newpass456"}
        )
        assert new_login.status_code == 200

    def test_change_password_wrong_current(self):
        """Changing password with wrong current password should fail."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        # Try to change password with wrong current password
        response = requests.put(
            f"{API_URL}/auth/me/password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "newpass456",
                "confirm_password": "newpass456"
            }
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_mismatch(self):
        """Changing password with mismatched confirm should fail."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        response = requests.put(
            f"{API_URL}/auth/me/password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "current_password": "admin123",
                "new_password": "newpass456",
                "confirm_password": "differentpass"
            }
        )
        assert response.status_code == 400
        assert "match" in response.json()["detail"].lower()

    def test_change_password_clears_must_change_flag(self):
        """Changing password should clear must_change_password flag."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        # Create user with must_change_password=True
        response = create_test_user(
            admin_token,
            username="test_must_change",
            password="temppass123",
            must_change_password=True
        )

        if response.status_code == 400 and "already exists" in response.text:
            # Reset password with must_change_password=True
            users_resp = requests.get(
                f"{API_URL}/auth/users",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            user = next((u for u in users_resp.json() if u["username"] == "test_must_change"), None)
            if user:
                requests.put(
                    f"{API_URL}/auth/admin/users/{user['user_id']}/reset-password",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"new_password": "temppass123", "must_change_password": True}
                )
                user_id = user["user_id"]
        else:
            assert response.status_code == 201
            user_id = response.json()["user_id"]

        # Login as user
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_must_change", "password": "temppass123"}
        )
        assert login_resp.status_code == 200
        user_token = login_resp.json()["access_token"]

        # Change password
        requests.put(
            f"{API_URL}/auth/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": "temppass123",
                "new_password": "permanentpass",
                "confirm_password": "permanentpass"
            }
        )

        # Check flag is cleared
        me_resp = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Token might be invalid after password change, re-login
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_must_change", "password": "permanentpass"}
        )
        new_token = login_resp.json()["access_token"]

        me_resp = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["must_change_password"] == False


class TestAdminUserManagement:
    """Test admin user management endpoints."""

    def test_admin_create_user_full_profile(self):
        """Admin can create user with full profile."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        response = create_test_user(
            token,
            username=f"test_fullprof_{TEST_SUFFIX}",
            email=f"test_{TEST_SUFFIX}@example.com",
            full_name="Test Full Profile",
            team="Quality Team",
            language="Korean",
            department="Localization"
        )

        assert response.status_code == 201
        user = response.json()

        assert user["username"] == f"test_fullprof_{TEST_SUFFIX}"
        assert user["email"] == f"test_{TEST_SUFFIX}@example.com"
        assert user["full_name"] == "Test Full Profile"
        assert user["team"] == "Quality Team"
        assert user["language"] == "Korean"
        assert user["department"] == "Localization"

        cleanup_test_user(token, user["user_id"])

    def test_admin_update_user_profile(self):
        """Admin can update user profile fields."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Create user
        create_resp = create_test_user(
            token,
            username="test_update_profile",
            team="Team A",
            language="Japanese"
        )

        if create_resp.status_code == 400 and "already exists" in create_resp.text:
            users_resp = requests.get(
                f"{API_URL}/auth/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            user = next((u for u in users_resp.json() if u["username"] == "test_update_profile"), None)
            user_id = user["user_id"] if user else None
        else:
            assert create_resp.status_code == 201
            user_id = create_resp.json()["user_id"]

        if not user_id:
            pytest.skip("Could not get user ID")

        # Update profile
        update_resp = requests.put(
            f"{API_URL}/auth/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "team": "Team B",
                "language": "Korean",
                "full_name": "Updated Name"
            }
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()

        assert updated["team"] == "Team B"
        assert updated["language"] == "Korean"
        assert updated["full_name"] == "Updated Name"

    def test_admin_reset_user_password(self):
        """Admin can reset any user's password."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Create user
        create_resp = create_test_user(
            token,
            username="test_reset_pw",
            password="original123"
        )

        if create_resp.status_code == 400 and "already exists" in create_resp.text:
            users_resp = requests.get(
                f"{API_URL}/auth/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            user = next((u for u in users_resp.json() if u["username"] == "test_reset_pw"), None)
            user_id = user["user_id"] if user else None
        else:
            assert create_resp.status_code == 201
            user_id = create_resp.json()["user_id"]

        if not user_id:
            pytest.skip("Could not get user ID")

        # Reset password
        reset_resp = requests.put(
            f"{API_URL}/auth/admin/users/{user_id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_password": "adminreset456", "must_change_password": True}
        )
        assert reset_resp.status_code == 200

        # Verify new password works
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_reset_pw", "password": "adminreset456"}
        )
        assert login_resp.status_code == 200

    def test_admin_deactivate_user(self):
        """Admin can deactivate (soft delete) a user."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Create user
        create_resp = create_test_user(
            token,
            username="test_deactivate"
        )

        if create_resp.status_code == 400 and "already exists" in create_resp.text:
            users_resp = requests.get(
                f"{API_URL}/auth/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            user = next((u for u in users_resp.json() if u["username"] == "test_deactivate"), None)
            user_id = user["user_id"] if user else None
            # Reactivate if needed
            if user and not user["is_active"]:
                requests.put(
                    f"{API_URL}/auth/users/{user_id}/activate",
                    headers={"Authorization": f"Bearer {token}"}
                )
        else:
            assert create_resp.status_code == 201
            user_id = create_resp.json()["user_id"]

        if not user_id:
            pytest.skip("Could not get user ID")

        # Deactivate (soft delete)
        delete_resp = requests.delete(
            f"{API_URL}/auth/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_resp.status_code == 200

        # Verify user cannot login
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "test_deactivate", "password": "testpass123"}
        )
        assert login_resp.status_code == 403  # Inactive user

    def test_admin_cannot_deactivate_self(self):
        """Admin cannot deactivate their own account."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Try to deactivate self (admin is user_id=1)
        response = requests.delete(
            f"{API_URL}/auth/admin/users/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "own account" in response.json()["detail"].lower()

    def test_admin_cannot_demote_self(self):
        """Admin cannot demote their own role."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Try to change own role to user
        response = requests.put(
            f"{API_URL}/auth/admin/users/1",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "user"}
        )
        assert response.status_code == 400
        assert "demote" in response.json()["detail"].lower()

    def test_duplicate_username_rejected(self):
        """Creating user with duplicate username should fail."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        # Create first user
        create_test_user(token, username="test_duplicate")

        # Try to create again
        response = create_test_user(token, username="test_duplicate")
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_invalid_role_rejected(self):
        """Creating user with invalid role should fail."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        response = requests.post(
            f"{API_URL}/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "test_invalid_role",
                "password": "testpass123",
                "role": "superadmin"  # Invalid role
            }
        )
        assert response.status_code == 400
        assert "invalid role" in response.json()["detail"].lower()


class TestPasswordValidation:
    """Test password validation rules."""

    def test_password_minimum_length(self):
        """Password must be at least 6 characters."""
        token = get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")

        response = requests.post(
            f"{API_URL}/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "test_short_pw",
                "password": "12345"  # Too short
            }
        )
        assert response.status_code == 422  # Validation error


class TestNonAdminRestrictions:
    """Test that non-admin users cannot access admin endpoints."""

    def test_regular_user_cannot_create_users(self):
        """Regular users cannot create other users."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        # Create a regular user
        create_test_user(admin_token, username="regular_user", password="userpass123")

        # Login as regular user
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "regular_user", "password": "userpass123"}
        )

        if login_resp.status_code != 200:
            pytest.skip("Could not login as regular user")

        user_token = login_resp.json()["access_token"]

        # Try to create a user
        response = requests.post(
            f"{API_URL}/auth/admin/users",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "username": "unauthorized_create",
                "password": "testpass123"
            }
        )
        assert response.status_code in [401, 403]  # Unauthorized or Forbidden

    def test_regular_user_cannot_reset_passwords(self):
        """Regular users cannot reset other users' passwords."""
        admin_token = get_admin_token()
        if not admin_token:
            pytest.skip("Could not get admin token")

        # Get regular user token (created in previous test)
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": "regular_user", "password": "userpass123"}
        )

        if login_resp.status_code != 200:
            pytest.skip("Could not login as regular user")

        user_token = login_resp.json()["access_token"]

        # Try to reset admin password
        response = requests.put(
            f"{API_URL}/auth/admin/users/1/reset-password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"new_password": "hackedpass"}
        )
        assert response.status_code in [401, 403]
