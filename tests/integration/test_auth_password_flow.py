"""Integration test: must_change_password in login flow."""
import pytest


def test_token_response_includes_must_change_password():
    """Login response JSON must include must_change_password field."""
    from server.api.schemas import Token

    # Simulate a user who must change password
    token = Token(
        access_token="eyJ...",
        token_type="bearer",
        user_id=3,
        username="seonchile",
        role="user",
        must_change_password=True,
    )
    data = token.model_dump()
    assert "must_change_password" in data
    assert data["must_change_password"] is True


def test_token_response_defaults_false():
    """must_change_password must default to False for backward compat."""
    from server.api.schemas import Token

    token = Token(
        access_token="eyJ...",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
    )
    data = token.model_dump()
    assert "must_change_password" in data
    assert data["must_change_password"] is False


def test_token_json_serialization():
    """Token must serialize must_change_password in JSON (what the frontend receives)."""
    from server.api.schemas import Token

    token = Token(
        access_token="test-token",
        token_type="bearer",
        user_id=2,
        username="testuser",
        role="user",
        must_change_password=True,
    )
    json_str = token.model_dump_json()
    assert '"must_change_password":true' in json_str or '"must_change_password": true' in json_str


def test_old_frontend_ignores_extra_field():
    """Simulate old frontend parsing: it reads only known fields, ignores must_change_password."""
    from server.api.schemas import Token

    token = Token(
        access_token="test-token",
        token_type="bearer",
        user_id=1,
        username="admin",
        role="admin",
        must_change_password=True,
    )
    data = token.model_dump()

    # Old frontend code only reads these:
    access_token = data["access_token"]
    user_id = data["user_id"]
    username = data["username"]
    role = data["role"]

    # These should all work fine
    assert access_token == "test-token"
    assert user_id == 1
    assert username == "admin"
    assert role == "admin"
    # Old frontend never reads must_change_password -- no crash


def test_new_frontend_handles_missing_field():
    """Simulate new frontend receiving response from OLD backend (no must_change_password)."""
    # Old backend returns this JSON (no must_change_password field)
    old_backend_response = {
        "access_token": "test-token",
        "token_type": "bearer",
        "user_id": 1,
        "username": "admin",
        "role": "admin",
    }

    # New frontend code: response.must_change_password || false
    must_change = old_backend_response.get("must_change_password") or False
    assert must_change is False  # Graceful fallback


def test_security_mode_from_config():
    """SECURITY_MODE reads from _USER_CONFIG with warn fallback."""
    from server import config
    # In test environment, no server-config.json, so should be "warn"
    assert config.SECURITY_MODE in ("warn", "strict")


def test_cors_origins_type():
    """_build_lan_cors_origins returns a list of strings."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.0.0.1")
    assert isinstance(origins, list)
    assert all(isinstance(o, str) for o in origins)
    assert len(origins) > 0
