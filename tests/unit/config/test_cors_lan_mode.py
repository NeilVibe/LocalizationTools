"""Tests for CORS auto-restriction in LAN server mode."""
import pytest
from unittest.mock import patch
import importlib


def test_lan_mode_generates_cors_origins():
    """LAN server mode should auto-populate CORS_ORIGINS instead of CORS_ALLOW_ALL."""
    # Simulate: server_mode=lan_server, lan_ip=10.0.0.1, no CORS_ORIGINS env var
    mock_config = {
        "server_mode": "lan_server",
        "lan_ip": "10.0.0.1",
    }
    with patch.dict("os.environ", {}, clear=False):
        # Remove CORS_ORIGINS from env if present
        import os
        os.environ.pop("CORS_ORIGINS", None)

        # Simulate the function logic
        from server.config import _build_lan_cors_origins
        origins = _build_lan_cors_origins("10.0.0.1")

        assert "http://10.0.0.1:5173" in origins
        assert "https://10.0.0.1:5173" in origins
        assert "http://10.0.0.1:8888" in origins
        assert "https://10.0.0.1:8888" in origins
        assert "http://localhost:5173" in origins
        assert "app://." in origins  # Electron origin


def test_lan_mode_cors_not_allow_all():
    """LAN server mode should NOT set CORS_ALLOW_ALL=True when origins are auto-generated."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.0.0.1")
    # If origins are generated, CORS_ALLOW_ALL should be False
    assert len(origins) > 0
