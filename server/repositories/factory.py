"""
Repository Factory.

Provides dependency injection functions for FastAPI routes.
Automatically selects PostgreSQL or SQLite based on user's mode.

P9-ARCH: The repository pattern abstracts database access so that:
- Online mode uses PostgreSQL (multi-user, real-time sync)
- Offline mode uses SQLite (single-user, local storage)
"""

from typing import Optional
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import get_async_db
from server.repositories.interfaces.tm_repository import TMRepository


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Get current user from request state if available, otherwise None.

    This is used by the repository factory to detect offline mode.
    Unlike get_current_active_user_async, this doesn't raise on missing auth.
    """
    # Check if user was set by auth middleware
    if hasattr(request.state, "user"):
        return request.state.user

    # Try to get from Authorization header for mode detection
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Just return token info for mode detection
        return {"token": token}

    return None


def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> TMRepository:
    """
    Factory function - returns correct TM repository based on mode.

    Used as FastAPI dependency:
        @router.get("/tms")
        async def get_tms(repo: TMRepository = Depends(get_tm_repository)):
            return await repo.get_all()

    Logic:
    - If Authorization header token starts with "OFFLINE_MODE_" → SQLite
    - Otherwise → PostgreSQL
    """
    # Import here to avoid circular imports
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    # Check if offline mode from Authorization header
    auth_header = request.headers.get("Authorization", "")
    is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")

    if is_offline:
        return SQLiteTMRepository()
    else:
        return PostgreSQLTMRepository(db)


def is_offline_mode(current_user: Optional[dict]) -> bool:
    """Check if current user is in offline mode."""
    if not current_user:
        return False
    token = current_user.get("token", "")
    return isinstance(token, str) and token.startswith("OFFLINE_MODE_")
