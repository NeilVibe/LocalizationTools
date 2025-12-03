"""
Unit Tests for Auth Module

Tests password hashing, JWT tokens, and authentication utilities.
TRUE SIMULATION - no mocks, real bcrypt and JWT operations.
"""

import pytest
import sys
from pathlib import Path
from datetime import timedelta
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password_returns_string(self):
        """hash_password returns a string."""
        from server.utils.auth import hash_password
        result = hash_password("testpassword123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_different_each_time(self):
        """Same password produces different hashes (due to salt)."""
        from server.utils.auth import hash_password
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2  # Different salts

    def test_hash_password_bcrypt_format(self):
        """Hash is in bcrypt format (starts with $2b$)."""
        from server.utils.auth import hash_password
        result = hash_password("testpassword")
        assert result.startswith("$2b$") or result.startswith("$2a$")

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        from server.utils.auth import hash_password, verify_password
        password = "mySecurePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password returns False for wrong password."""
        from server.utils.auth import hash_password, verify_password
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_password(self):
        """verify_password handles empty password."""
        from server.utils.auth import hash_password, verify_password
        hashed = hash_password("actualpassword")
        assert verify_password("", hashed) is False

    def test_verify_password_unicode(self):
        """verify_password works with unicode passwords."""
        from server.utils.auth import hash_password, verify_password
        password = "p@ssw0rd_"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_invalid_hash_returns_false(self):
        """verify_password returns False for invalid hash format."""
        from server.utils.auth import verify_password
        result = verify_password("password", "not_a_valid_hash")
        assert result is False

    def test_hash_password_long_password(self):
        """hash_password handles passwords up to 72 bytes."""
        from server.utils.auth import hash_password, verify_password
        # bcrypt has 72-byte limit
        password = "a" * 72
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_special_characters(self):
        """hash_password handles special characters."""
        from server.utils.auth import hash_password, verify_password
        password = "P@$$w0rd!#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token_returns_string(self):
        """create_access_token returns a JWT string."""
        from server.utils.auth import create_access_token
        token = create_access_token({"user_id": 1, "username": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_jwt_format(self):
        """Token is in JWT format (3 parts separated by dots)."""
        from server.utils.auth import create_access_token
        token = create_access_token({"user_id": 1})
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_verify_token_valid(self):
        """verify_token decodes valid token."""
        from server.utils.auth import create_access_token, verify_token
        data = {"user_id": 42, "username": "john", "role": "admin"}
        token = create_access_token(data)
        decoded = verify_token(token)
        assert decoded is not None
        assert decoded["user_id"] == 42
        assert decoded["username"] == "john"
        assert decoded["role"] == "admin"

    def test_verify_token_contains_exp(self):
        """Token contains expiration claim."""
        from server.utils.auth import create_access_token, verify_token
        token = create_access_token({"user_id": 1})
        decoded = verify_token(token)
        assert "exp" in decoded

    def test_verify_token_invalid_returns_none(self):
        """verify_token returns None for invalid token."""
        from server.utils.auth import verify_token
        result = verify_token("invalid.token.here")
        assert result is None

    def test_verify_token_empty_returns_none(self):
        """verify_token returns None for empty token."""
        from server.utils.auth import verify_token
        result = verify_token("")
        assert result is None

    def test_verify_token_tampered_returns_none(self):
        """verify_token returns None for tampered token."""
        from server.utils.auth import create_access_token, verify_token
        token = create_access_token({"user_id": 1})
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        result = verify_token(tampered)
        assert result is None

    def test_create_token_with_custom_expiry(self):
        """create_access_token accepts custom expiry."""
        from server.utils.auth import create_access_token, verify_token
        from datetime import timedelta

        # Create token with 1 hour expiry
        token = create_access_token(
            {"user_id": 1},
            expires_delta=timedelta(hours=1)
        )
        decoded = verify_token(token)
        assert decoded is not None
        assert decoded["user_id"] == 1

    def test_create_token_preserves_all_data(self):
        """All data in token is preserved after decoding."""
        from server.utils.auth import create_access_token, verify_token

        data = {
            "user_id": 123,
            "username": "testuser",
            "email": "test@example.com",
            "role": "admin",
            "department": "Engineering"
        }
        token = create_access_token(data)
        decoded = verify_token(token)

        for key, value in data.items():
            assert decoded[key] == value


class TestAPIKeyGeneration:
    """Test API key generation."""

    def test_generate_api_key_returns_string(self):
        """generate_api_key returns a string."""
        from server.utils.auth import generate_api_key
        key = generate_api_key()
        assert isinstance(key, str)

    def test_generate_api_key_sufficient_length(self):
        """API key has sufficient length for security."""
        from server.utils.auth import generate_api_key
        key = generate_api_key()
        assert len(key) >= 32  # At least 32 characters

    def test_generate_api_key_unique(self):
        """Each generated key is unique."""
        from server.utils.auth import generate_api_key
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All unique

    def test_generate_api_key_url_safe(self):
        """API key is URL-safe (no special chars that need encoding)."""
        from server.utils.auth import generate_api_key
        key = generate_api_key()
        # URL-safe base64 only uses: A-Z, a-z, 0-9, -, _
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', key)


class TestIsAdmin:
    """Test admin role checking."""

    def test_is_admin_with_admin_role(self):
        """is_admin returns True for admin role."""
        from server.utils.auth import is_admin
        user = {"user_id": 1, "username": "admin", "role": "admin"}
        assert is_admin(user) is True

    def test_is_admin_with_superadmin_role(self):
        """is_admin returns True for superadmin role."""
        from server.utils.auth import is_admin
        user = {"user_id": 1, "username": "superadmin", "role": "superadmin"}
        assert is_admin(user) is True

    def test_is_admin_with_user_role(self):
        """is_admin returns False for regular user role."""
        from server.utils.auth import is_admin
        user = {"user_id": 1, "username": "user", "role": "user"}
        assert is_admin(user) is False

    def test_is_admin_with_no_role(self):
        """is_admin returns False if no role specified."""
        from server.utils.auth import is_admin
        user = {"user_id": 1, "username": "user"}
        assert is_admin(user) is False

    def test_is_admin_with_empty_dict(self):
        """is_admin returns False for empty dict."""
        from server.utils.auth import is_admin
        assert is_admin({}) is False

    def test_is_admin_case_sensitive(self):
        """Role check is case-sensitive."""
        from server.utils.auth import is_admin
        user = {"role": "ADMIN"}  # uppercase
        assert is_admin(user) is False


class TestTokenExpiration:
    """Test token expiration behavior."""

    def test_expired_token_returns_none(self):
        """Expired token returns None on verification."""
        from server.utils.auth import create_access_token, verify_token
        from datetime import timedelta

        # Create token that expires immediately
        token = create_access_token(
            {"user_id": 1},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        result = verify_token(token)
        assert result is None

    def test_token_valid_before_expiry(self):
        """Token is valid before expiry time."""
        from server.utils.auth import create_access_token, verify_token
        from datetime import timedelta

        # Create token with 1 hour expiry
        token = create_access_token(
            {"user_id": 1},
            expires_delta=timedelta(hours=1)
        )

        result = verify_token(token)
        assert result is not None
        assert result["user_id"] == 1


class TestAuthModuleExports:
    """Test module exports."""

    def test_all_functions_importable(self):
        """All expected functions are importable."""
        from server.utils.auth import (
            hash_password,
            verify_password,
            create_access_token,
            verify_token,
            get_current_user,
            get_current_user_async,
            generate_api_key,
            is_admin
        )
        assert callable(hash_password)
        assert callable(verify_password)
        assert callable(create_access_token)
        assert callable(verify_token)
        assert callable(get_current_user)
        assert callable(get_current_user_async)
        assert callable(generate_api_key)
        assert callable(is_admin)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
