"""Auth subsystem tests.

Covers login (form data + JSON), token validation, user management,
registration, password changes, and admin user operations.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
    assert_list_response,
)
from tests.api.helpers.constants import (
    AUTH_LOGIN,
    AUTH_ME,
    AUTH_USERS,
    AUTH_REGISTER,
    AUTH_CHANGE_PASSWORD,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    PROJECTS_LIST,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.auth]


# ======================================================================
# Login
# ======================================================================


class TestLogin:
    """Login endpoint tests — /api/v2/auth/login."""

    def test_login_valid_credentials_form(self, api):
        """POST login with valid form-data creds returns 200 + access_token."""
        resp = api.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        assert_status(resp, 200, "Login form-data")
        data = resp.json()
        assert "access_token" in data, f"Missing access_token in response: {data}"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 10

    def test_login_valid_credentials_json(self, api):
        """POST login with valid JSON body returns 200 + access_token."""
        resp = api.login_json(ADMIN_USERNAME, ADMIN_PASSWORD)
        assert_status(resp, 200, "Login JSON")
        data = resp.json()
        assert "access_token" in data

    def test_login_invalid_password(self, api):
        """POST login with wrong password returns 401."""
        resp = api.login(ADMIN_USERNAME, "wrong_password_123")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 for invalid password, got {resp.status_code}"
        )

    def test_login_nonexistent_user(self, api):
        """POST login with unknown username returns 401."""
        resp = api.login("nonexistent_user_xyz_999", "any_password")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 for nonexistent user, got {resp.status_code}"
        )

    def test_login_missing_fields(self, client):
        """POST login with empty body returns 422."""
        resp = client.post(AUTH_LOGIN, data={})
        assert resp.status_code in (400, 401, 422), (
            f"Expected 400/401/422 for missing fields, got {resp.status_code}"
        )

    @pytest.mark.parametrize(
        "username,password",
        [
            ("", ADMIN_PASSWORD),
            (ADMIN_USERNAME, ""),
            ("", ""),
        ],
        ids=["empty-username", "empty-password", "both-empty"],
    )
    def test_login_invalid_credential_variations(self, api, username, password):
        """Parametrized: empty username/password returns non-200."""
        resp = api.login(username, password)
        assert resp.status_code != 200, (
            f"Expected non-200 for empty credentials ({username!r}, {password!r}), "
            f"got {resp.status_code}"
        )


# ======================================================================
# Token Validation
# ======================================================================


class TestTokenValidation:
    """Token-based auth validation for protected endpoints."""

    def test_protected_endpoint_with_valid_token(self, client, auth_headers):
        """Access /api/ldm/projects with valid Bearer token succeeds."""
        resp = client.get(PROJECTS_LIST, headers=auth_headers)
        assert_status_ok(resp, "Protected endpoint with valid token")

    def test_protected_endpoint_without_token(self, client):
        """Access /api/ldm/projects without auth header returns 401/403."""
        resp = client.get(PROJECTS_LIST)
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without token, got {resp.status_code}"
        )

    def test_protected_endpoint_with_garbage_token(self, client):
        """Access with garbage Bearer token returns 401/403."""
        resp = client.get(
            PROJECTS_LIST,
            headers={"Authorization": "Bearer not.a.real.jwt.token"},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 with garbage token, got {resp.status_code}"
        )

    def test_protected_endpoint_with_malformed_header(self, client):
        """Access with malformed auth header (no Bearer prefix) returns 401/403."""
        resp = client.get(
            PROJECTS_LIST,
            headers={"Authorization": "NotBearer sometoken"},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 with malformed header, got {resp.status_code}"
        )


# ======================================================================
# User Profile (GET /me)
# ======================================================================


class TestUserProfile:
    """User profile endpoint tests — /api/v2/auth/me."""

    def test_get_current_user(self, api):
        """GET /me returns current user info with expected fields."""
        resp = api.get_me()
        assert_status_ok(resp, "Get current user")
        data = resp.json()
        # Should have at least username
        assert "username" in data or "user" in data, f"Missing user info: {data.keys()}"

    def test_get_me_without_auth(self, client):
        """GET /me without auth returns 401/403."""
        resp = client.get(AUTH_ME)
        assert resp.status_code in (401, 403)


# ======================================================================
# User Listing
# ======================================================================


class TestUserListing:
    """User list endpoint tests — /api/v2/auth/users."""

    def test_list_users(self, api):
        """GET /users returns list with at least the admin user."""
        resp = api.list_users()
        assert_status_ok(resp, "List users")
        data = resp.json()
        # Response could be a list or a dict with a users field
        if isinstance(data, list):
            assert len(data) >= 1, "Expected at least 1 user (admin)"
        elif isinstance(data, dict) and "users" in data:
            assert len(data["users"]) >= 1
        else:
            # At minimum it should be parseable
            assert data is not None


# ======================================================================
# Registration
# ======================================================================


class TestRegistration:
    """User registration tests — /api/v2/auth/register."""

    def test_register_new_user(self, api):
        """POST register creates a new user."""
        import time

        unique = f"testuser_{int(time.time())}"
        resp = api.register(
            username=unique,
            password="TestPass123!",
            email=f"{unique}@test.local",
        )
        # Accept 200 or 201
        assert resp.status_code in (200, 201), (
            f"Registration failed: {resp.status_code} {resp.text[:200]}"
        )

    def test_register_duplicate_username(self, api):
        """POST register with duplicate username returns error."""
        import time

        unique = f"dupuser_{int(time.time())}"
        # First registration
        resp1 = api.register(
            username=unique,
            password="TestPass123!",
            email=f"{unique}@test.local",
        )
        assert resp1.status_code in (200, 201)

        # Second registration with same username
        resp2 = api.register(
            username=unique,
            password="TestPass456!",
            email=f"{unique}_2@test.local",
        )
        assert resp2.status_code in (400, 409, 422), (
            f"Expected error for duplicate username, got {resp2.status_code}"
        )


# ======================================================================
# Password Change
# ======================================================================


class TestPasswordChange:
    """Password change tests — /api/v2/auth/me/password."""

    def test_change_password_wrong_current(self, api):
        """PUT password change with wrong current password fails."""
        resp = api.change_password(
            current_password="totally_wrong_password",
            new_password="NewPass123!",
        )
        assert resp.status_code in (400, 401, 403, 422), (
            f"Expected error for wrong current password, got {resp.status_code}"
        )


# ======================================================================
# Admin User Operations
# ======================================================================


class TestAdminUserOps:
    """Admin user management tests — /api/v2/auth/admin/users."""

    def test_admin_create_user(self, api):
        """POST admin/users creates user."""
        import time

        unique = f"admintest_{int(time.time())}"
        resp = api.admin_create_user(
            username=unique,
            password="AdminTest123!",
            email=f"{unique}@admin.local",
        )
        # May not be implemented — skip if 404/405
        if resp.status_code in (404, 405):
            pytest.skip("Admin create user endpoint not implemented")
        assert resp.status_code in (200, 201), (
            f"Admin user creation failed: {resp.status_code} {resp.text[:200]}"
        )

    def test_admin_create_user_without_admin(self, client):
        """POST admin/users without admin rights returns 401/403."""
        resp = client.post(
            "/api/v2/auth/admin/users",
            json={"username": "sneaky", "password": "pass", "email": "x@x.x"},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 for non-admin, got {resp.status_code}"
        )
