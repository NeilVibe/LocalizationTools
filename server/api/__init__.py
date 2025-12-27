"""
API Package

FastAPI routers and schemas for the LocalizationTools server.
All endpoints use async versions.
"""

from server.api import auth_async, logs_async, sessions_async, schemas

# Aliases for backwards compatibility
auth = auth_async
logs = logs_async
sessions = sessions_async

__all__ = ["auth", "logs", "sessions", "auth_async", "logs_async", "sessions_async", "schemas"]
