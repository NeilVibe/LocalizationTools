"""
FastAPI Dependencies

Dependency injection functions for FastAPI endpoints.
"""

from typing import Generator, AsyncGenerator

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasicCredentials
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger

from server.database.db_setup import get_session_maker, create_database_engine, initialize_database as init_db_tables, setup_database
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
_async_engine_loop = None  # Track which event loop the async engine was created in


def initialize_database():
    """
    Initialize database engine, session maker, and create tables (call once at startup).

    P33 Offline Mode:
    - Uses setup_database() which handles DATABASE_MODE auto-detection
    - If DATABASE_MODE=auto and PostgreSQL unreachable → uses SQLite
    - If DATABASE_MODE=postgresql → fails if PostgreSQL unreachable
    - If DATABASE_MODE=sqlite → uses SQLite directly
    """
    global _engine, _session_maker

    if _engine is None:
        # Use setup_database() for proper mode handling (P33 Offline Mode)
        _engine, _session_maker = setup_database(echo=config.DB_ECHO)
        logger.info(f"Database initialized: {config.ACTIVE_DATABASE_TYPE.upper()}")


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


def get_sync_engine():
    """
    Get the shared synchronous database engine.

    Use this instead of create_engine() to share connection pool.
    Useful for background tasks that need sync database access.

    Returns:
        SQLAlchemy Engine instance.

    Example:
        >>> from server.utils.dependencies import get_sync_engine
        >>> engine = get_sync_engine()
        >>> with Session(engine) as session:
        >>>     result = session.query(User).all()
    """
    global _engine
    if _engine is None:
        initialize_database()
    return _engine


def initialize_async_database():
    """
    Initialize async database engine and session maker (call once at startup).

    P33 Offline Mode:
    - SQLite: Skip async initialization (pysqlite is not async)
    - PostgreSQL: Initialize async engine with asyncpg

    ROBUST: Gracefully degrades to sync-only mode if asyncpg is not installed.
    """
    import asyncio
    global _async_engine, _async_session_maker, _async_engine_loop

    # Skip async database for SQLite (pysqlite is not async)
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        logger.info("Async database skipped: SQLite mode (using sync database only)")
        return

    # Check if asyncpg is available (required for async PostgreSQL)
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        logger.warning("Async database skipped: asyncpg not installed (using sync database only)")
        logger.warning("To enable async database, install asyncpg: pip install asyncpg")
        return

    # Get current event loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    # Recreate engine if we're in a different event loop (fixes test isolation)
    if _async_engine is not None and _async_engine_loop is not None and current_loop is not None:
        if _async_engine_loop != current_loop:
            logger.debug("Event loop changed, recreating async engine")
            _async_engine = None
            _async_session_maker = None

    if _async_engine is None:
        # PostgreSQL async URL (postgresql+asyncpg://)
        database_url = config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

        # PostgreSQL with connection pooling (uses config values)
        _async_engine = create_async_engine(
            database_url,
            echo=config.DB_ECHO,
            pool_size=config.DB_POOL_SIZE,       # Connection pool size
            max_overflow=config.DB_MAX_OVERFLOW, # Max extra connections
            pool_timeout=config.DB_POOL_TIMEOUT, # Timeout for getting connection
            pool_recycle=config.DB_POOL_RECYCLE, # Recycle connections after N seconds
            pool_pre_ping=True                   # Verify connections before using
        )

        _async_session_maker = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False     # Don't expire objects after commit
        )

        # Track which event loop this engine was created in
        _async_engine_loop = current_loop

        logger.info("Async database initialized: PostgreSQL")


def _check_async_engine_loop():
    """
    Check if the async engine was created in a different event loop.
    If so, reset it so it gets recreated in the current loop.

    This fixes test isolation issues where pytest creates new event loops
    after running 100+ tests.
    """
    import asyncio
    global _async_engine, _async_session_maker, _async_engine_loop

    # Skip for SQLite mode
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        return

    # If no engine exists, nothing to check
    if _async_engine is None:
        return

    # Get current event loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - can't check
        return

    # If engine was created in a different loop, reset it
    if _async_engine_loop is not None and _async_engine_loop != current_loop:
        logger.debug("Event loop changed - resetting async engine for test isolation")
        _async_engine = None
        _async_session_maker = None
        _async_engine_loop = None


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get async database session.

    NOTE: Auto-commits on success, auto-rollbacks on exception.
    For explicit transaction control, use session.begin() in endpoint.

    P33 Offline Mode:
    - SQLite: Falls back to sync session (wrapped for async compatibility)
    - PostgreSQL: Uses async session

    Yields:
        Async database session.

    Example:
        >>> @app.get("/users")
        >>> async def get_users(db: AsyncSession = Depends(get_async_db)):
        >>>     result = await db.execute(select(User))
        >>>     return result.scalars().all()  # Auto-commits after return
    """
    # Check if event loop changed (fixes test isolation after 100+ tests)
    _check_async_engine_loop()

    if _async_session_maker is None:
        initialize_async_database()

    # SQLite mode: async_session_maker is None, use sync session
    if _async_session_maker is None:
        # Fallback to sync session for SQLite mode
        # Note: This works because sync sessions can be used in async context
        # but won't benefit from async I/O
        if _session_maker is None:
            initialize_database()
        session = _session_maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return

    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on exception
            raise
        finally:
            await session.close()


# ============================================================================
# Authentication Dependencies (Sync and Async)
# ============================================================================

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)  # auto_error=False for DEV_MODE support


# ============================================================================
# DEV_MODE: Localhost-only Auto-Authentication
# ============================================================================

def _is_localhost(request: Request) -> bool:
    """Check if request comes from localhost."""
    if not request.client:
        return False
    host = request.client.host
    return host in ("127.0.0.1", "::1", "localhost")


def _get_dev_user() -> dict:
    """Return auto-authenticated dev user for DEV_MODE."""
    return {
        "user_id": 1,
        "username": "dev_admin",
        "role": "admin",
        "is_active": True,
        "dev_mode": True  # Flag to identify DEV_MODE sessions
    }


# Log DEV_MODE status on module load
if config.DEV_MODE:
    logger.warning("⚠️  DEV_MODE enabled - localhost auto-authentication active")


def get_current_active_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI dependency to get current authenticated user (SYNC).

    Supports DEV_MODE: Auto-authenticates as admin on localhost when enabled.

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer token from Authorization header (optional in DEV_MODE).
        db: Database session.

    Returns:
        User data dictionary.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    # DEV_MODE: Auto-authenticate on localhost
    if config.DEV_MODE and _is_localhost(request):
        if not credentials:
            logger.debug("DEV_MODE: Auto-authenticating as dev_admin")
            return _get_dev_user()

    # Normal authentication flow
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """
    FastAPI dependency to get current authenticated user (ASYNC).

    Supports DEV_MODE: Auto-authenticates as admin on localhost when enabled.

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer token from Authorization header (optional in DEV_MODE).
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
    # DEV_MODE: Auto-authenticate on localhost
    if config.DEV_MODE and _is_localhost(request):
        if not credentials:
            logger.debug("DEV_MODE: Auto-authenticating as dev_admin (async)")
            return _get_dev_user()

    # Normal authentication flow
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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


async def require_admin_async(
    current_user: dict = Depends(get_current_active_user_async)
) -> dict:
    """
    FastAPI dependency to require admin role (ASYNC).

    Args:
        current_user: Current authenticated user.

    Returns:
        User data dictionary if admin.

    Raises:
        HTTPException: If user is not an admin.

    Example:
        >>> @app.delete("/users/{user_id}")
        >>> async def delete_user(user_id: int, admin: dict = Depends(require_admin_async)):
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
