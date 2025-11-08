"""
FastAPI Dependencies

Dependency injection functions for FastAPI endpoints.
"""

from typing import Generator, AsyncGenerator

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger

from server.database.db_setup import get_session_maker, create_database_engine
from server.utils.auth import get_current_user, is_admin
from server import config


# ============================================================================
# Database Dependency (Sync and Async)
# ============================================================================

# Create global engines and session makers
_engine = None
_session_maker = None
_async_engine = None
_async_session_maker = None


def initialize_database():
    """Initialize database engine and session maker (call once at startup)."""
    global _engine, _session_maker

    if _engine is None:
        use_postgres = config.DATABASE_TYPE == "postgresql"
        _engine = create_database_engine(use_postgres=use_postgres, echo=config.DB_ECHO)
        _session_maker = get_session_maker(_engine)
        logger.info(f"Database initialized: {config.DATABASE_TYPE}")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session (SYNC - for backward compatibility).

    Yields:
        Database session.

    Example:
        >>> @app.get("/users")
        >>> def get_users(db: Session = Depends(get_db)):
        >>>     return db.query(User).all()
    """
    if _session_maker is None:
        initialize_database()

    db = _session_maker()
    try:
        yield db
    finally:
        db.close()


def initialize_async_database():
    """Initialize async database engine and session maker (call once at startup)."""
    global _async_engine, _async_session_maker

    if _async_engine is None:
        # Create async engine based on database type
        if config.DATABASE_TYPE == "postgresql":
            # PostgreSQL async URL (postgresql+asyncpg://)
            database_url = config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        else:
            # SQLite async URL (sqlite+aiosqlite://)
            database_url = config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

        _async_engine = create_async_engine(
            database_url,
            echo=config.DB_ECHO,
            pool_size=20,              # Connection pool size
            max_overflow=10,           # Max extra connections
            pool_timeout=30,           # Timeout for getting connection
            pool_recycle=3600,         # Recycle connections after 1 hour
            pool_pre_ping=True         # Verify connections before using
        )

        _async_session_maker = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False     # Don't expire objects after commit
        )

        logger.info(f"Async database initialized: {config.DATABASE_TYPE}")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get async database session.

    Yields:
        Async database session.

    Example:
        >>> @app.get("/users")
        >>> async def get_users(db: AsyncSession = Depends(get_async_db)):
        >>>     result = await db.execute(select(User))
        >>>     return result.scalars().all()
    """
    if _async_session_maker is None:
        initialize_async_database()

    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# Authentication Dependencies (Sync and Async)
# ============================================================================

# HTTP Bearer token security
security = HTTPBearer()


def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI dependency to get current authenticated user (SYNC).

    Args:
        credentials: HTTP Bearer token from Authorization header.
        db: Database session.

    Returns:
        User data dictionary.

    Raises:
        HTTPException: If token is invalid or user not found.

    Example:
        >>> @app.get("/protected")
        >>> def protected_route(user: dict = Depends(get_current_active_user)):
        >>>     return {"message": f"Hello {user['username']}"}
    """
    token = credentials.credentials
    user = get_current_user(token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user_async(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """
    FastAPI dependency to get current authenticated user (ASYNC).

    Args:
        credentials: HTTP Bearer token from Authorization header.
        db: Async database session.

    Returns:
        User data dictionary.

    Raises:
        HTTPException: If token is invalid or user not found.

    Example:
        >>> @app.get("/protected")
        >>> async def protected_route(user: dict = Depends(get_current_active_user_async)):
        >>>     return {"message": f"Hello {user['username']}"}
    """
    from server.utils.auth import get_current_user_async

    token = credentials.credentials
    user = await get_current_user_async(token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    FastAPI dependency to require admin role.

    Args:
        current_user: Current authenticated user.

    Returns:
        User data dictionary if admin.

    Raises:
        HTTPException: If user is not an admin.

    Example:
        >>> @app.delete("/users/{user_id}")
        >>> def delete_user(user_id: int, admin: dict = Depends(require_admin)):
        >>>     # Only admins can access this endpoint
        >>>     return {"message": "User deleted"}
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


def get_api_key(x_api_key: str = Header(...)) -> str:
    """
    FastAPI dependency to verify API key.

    Args:
        x_api_key: API key from X-API-Key header.

    Returns:
        API key if valid.

    Raises:
        HTTPException: If API key is invalid.

    Example:
        >>> @app.post("/logs")
        >>> def submit_log(api_key: str = Depends(get_api_key)):
        >>>     return {"message": "Log received"}
    """
    if x_api_key != config.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


# ============================================================================
# Optional Authentication (for public endpoints)
# ============================================================================

def get_optional_user(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
) -> dict:
    """
    FastAPI dependency to get current user (optional).

    Returns None if no auth token provided, or user dict if valid token.
    Useful for endpoints that can work with or without authentication.

    Args:
        db: Database session.
        authorization: Authorization header (optional).

    Returns:
        User data dictionary if authenticated, None otherwise.

    Example:
        >>> @app.get("/stats")
        >>> def get_stats(user: dict = Depends(get_optional_user)):
        >>>     if user:
        >>>         # Show detailed stats for authenticated user
        >>>         return detailed_stats
        >>>     else:
        >>>         # Show public stats
        >>>         return public_stats
    """
    if not authorization:
        return None

    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)

    return user
