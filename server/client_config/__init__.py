# Expose client_config module for imports
# This allows monkeypatch.setattr("server.client_config.client_config.ATTR", value)
from . import client_config  # noqa: F401
