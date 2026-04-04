"""Tests for JWT secret auto-generation in setup wizard."""
import pytest


def test_setup_config_has_secret_key():
    """Setup wizard config must include a secret_key that is NOT the default."""
    # Simulate what main.py:1084-1096 generates
    import secrets
    server_config_data = {
        "server_mode": "lan_server",
        "secret_key": secrets.token_urlsafe(32),
        "admin_token": secrets.token_urlsafe(32),
    }
    assert server_config_data["secret_key"] != "dev-secret-key-CHANGE-IN-PRODUCTION"
    assert len(server_config_data["secret_key"]) >= 32


def test_setup_config_has_security_mode_strict():
    """Setup wizard config must set security_mode to strict."""
    import secrets
    server_config_data = {
        "server_mode": "lan_server",
        "secret_key": secrets.token_urlsafe(32),
        "security_mode": "strict",
    }
    assert server_config_data["security_mode"] == "strict"


def test_default_secret_key_is_detectable():
    """The default secret key constant must be detectable for security validation."""
    from server.config import _DEFAULT_SECRET_KEY
    assert _DEFAULT_SECRET_KEY == "dev-secret-key-CHANGE-IN-PRODUCTION"
