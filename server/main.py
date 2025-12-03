"""
LocalizationTools Server

Central logging and analytics server for LocalizationTools.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from server import config
from server.utils.dependencies import initialize_database, initialize_async_database
from server.api import auth, logs, sessions
from server.api import auth_async, logs_async, sessions_async
from server.utils.websocket import socket_app
from server.middleware import RequestLoggingMiddleware, PerformanceLoggingMiddleware
from server.middleware.ip_filter import IPFilterMiddleware, parse_ip_ranges
from server.utils.cache import cache


def setup_logging():
    """Configure logging for the server."""
    logger.remove()  # Remove default handler

    # Add file logging
    logger.add(
        config.LOG_FILE,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
    )

    # Add error file logging
    logger.add(
        config.ERROR_LOG_FILE,
        format=config.LOG_FORMAT,
        level="ERROR",
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
    )

    # Add console logging
    logger.add(sys.stdout, format=config.LOG_FORMAT, level=config.LOG_LEVEL)

    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Database: {config.DATABASE_TYPE}")
    logger.info(f"Database URL: {config.DATABASE_URL}")


# Setup logging
setup_logging()

# Validate security configuration on startup
if not config.validate_security_on_startup(logger):
    logger.error("Server startup aborted due to security configuration errors!")
    logger.error("Fix the security issues above or set SECURITY_MODE=warn to continue (not recommended for production)")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # === STARTUP ===
    logger.info("Server starting up...")

    # Initialize database connections (both sync and async)
    try:
        initialize_database()
        logger.success("Sync database initialized successfully")

        initialize_async_database()
        logger.success("Async database initialized successfully")
    except Exception as e:
        logger.exception(f"Failed to initialize database: {e}")
        raise

    logger.info("WebSocket server will be wrapped at startup")

    # Initialize Redis cache (optional)
    try:
        await cache.connect()
    except Exception as e:
        logger.warning(f"Redis cache initialization skipped: {e}")

    logger.success("Server startup complete")

    yield  # Server runs here

    # === SHUTDOWN ===
    logger.info("Server shutting down...")

    # Disconnect Redis cache
    try:
        await cache.disconnect()
    except Exception as e:
        logger.warning(f"Redis disconnect error: {e}")

    logger.success("Server shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url=config.DOCS_URL if config.ENABLE_DOCS else None,
    redoc_url=config.REDOC_URL if config.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# Add CORS middleware
# In development (CORS_ALLOW_ALL=True): accepts all origins for convenience
# In production (CORS_ORIGINS env set): only whitelisted origins allowed
if config.CORS_ALLOW_ALL:
    logger.warning("CORS: Allowing ALL origins (development mode)")
    logger.warning("Set CORS_ORIGINS env var for production!")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    logger.info(f"CORS: Restricting to {len(config.CORS_ORIGINS)} whitelisted origins")
    for origin in config.CORS_ORIGINS:
        logger.info(f"  - {origin}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=config.CORS_ALLOW_METHODS,
        allow_headers=config.CORS_ALLOW_HEADERS,
    )

# Add IP Range Filter middleware (Internal Enterprise Security)
# This blocks requests from IPs outside the allowed ranges
if config.ALLOWED_IP_RANGE:
    allowed_ranges = parse_ip_ranges(config.ALLOWED_IP_RANGE)
    logger.info(f"IP Filter: ENABLED - Restricting to {len(allowed_ranges)} range(s)")
    for range_str in allowed_ranges:
        logger.info(f"  - {range_str}")
    app.add_middleware(
        IPFilterMiddleware,
        allowed_ranges=allowed_ranges,
        allow_localhost=config.IP_FILTER_ALLOW_LOCALHOST,
        log_blocked=config.IP_FILTER_LOG_BLOCKED,
    )
else:
    logger.warning("IP Filter: DISABLED (no ALLOWED_IP_RANGE set)")
    logger.warning("Set ALLOWED_IP_RANGE env var for production!")

# Add comprehensive logging middleware
# Order matters: These run in REVERSE order (last added = first to run)
app.add_middleware(PerformanceLoggingMiddleware, sample_rate=1.0)
app.add_middleware(RequestLoggingMiddleware)

# Include API routers (sync - for backward compatibility)
app.include_router(auth.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")

# Include async API routers (v2)
app.include_router(auth_async.router, prefix="/api/v2")
app.include_router(logs_async.router, prefix="/api/v2")
app.include_router(sessions_async.router, prefix="/api/v2")

# Include updates API (for self-hosted app distribution)
from server.api import updates
app.include_router(updates.router)

# Include XLSTransfer API (App #1)
from server.api import xlstransfer_async
app.include_router(xlstransfer_async.router)

# Include QuickSearch API (App #2)
from server.api import quicksearch_async
app.include_router(quicksearch_async.router)

# Include KR Similar API (App #3)
from server.api import kr_similar_async
app.include_router(kr_similar_async.router)

# Include Progress Operations API (for real-time progress tracking)
from server.api import progress_operations
app.include_router(progress_operations.router)

# Include Remote Logging API (for centralized monitoring of user installations)
from server.api import remote_logging
app.include_router(remote_logging.router)

# Include File Download API
from server.api import download
app.include_router(download.router)

# Include Admin Statistics API (for dashboard analytics)
from server.api import stats, rankings
app.include_router(stats.router)
app.include_router(rankings.router)

# Socket.IO will be mounted at the end after all setup is complete

# Note: Startup and shutdown events are now handled via the lifespan context manager
# defined above (see @asynccontextmanager def lifespan). This replaces the deprecated
# @app.on_event("startup") and @app.on_event("shutdown") decorators.


# ============================================
# Root Endpoints
# ============================================


@app.get("/")
async def root():
    """Root endpoint - server info."""
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
        "database": config.DATABASE_TYPE,
        "docs": f"{config.DOCS_URL}" if config.ENABLE_DOCS else "disabled",
    }


@app.get(config.HEALTH_CHECK_ENDPOINT)
async def health_check():
    """Health check endpoint."""
    from server.utils.dependencies import _engine

    db_status = "unknown"
    if _engine:
        try:
            with _engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.error(f"Health check database error: {e}")
            db_status = "error"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": config.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Additional API Routes
# ============================================


@app.get("/api/version/latest")
async def get_latest_version():
    """Get latest app version info."""
    from server.utils.dependencies import get_db
    from server.database.models import AppVersion

    db = next(get_db())
    try:
        latest = db.query(AppVersion).filter(
            AppVersion.is_latest == True
        ).first()

        if latest:
            return {
                "latest_version": latest.version_number,
                "download_url": latest.download_url,
                "release_notes": latest.release_notes,
                "is_mandatory": latest.is_required,
                "release_date": latest.release_date.isoformat(),
            }
        else:
            return {
                "latest_version": config.APP_VERSION,
                "download_url": f"{config.UPDATE_DOWNLOAD_URL_BASE}/LocalizationTools-{config.APP_VERSION}.exe",
                "release_notes": "Current version",
                "is_mandatory": False,
                "release_date": datetime.utcnow().isoformat(),
            }
    finally:
        db.close()


@app.get("/api/announcements")
async def get_announcements():
    """Get active announcements for users."""
    from server.utils.dependencies import get_db
    from server.database.models import Announcement

    db = next(get_db())
    try:
        now = datetime.utcnow()
        announcements = db.query(Announcement).filter(
            Announcement.is_active == True,
            (Announcement.expires_at == None) | (Announcement.expires_at > now)
        ).all()

        return {
            "announcements": [
                {
                    "id": a.announcement_id,
                    "title": a.title,
                    "message": a.message,
                    "priority": a.priority,
                    "created_at": a.created_at.isoformat()
                }
                for a in announcements
            ]
        }
    finally:
        db.close()


# ============================================
# Error Handlers
# ============================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if config.DEBUG else "An error occurred",
        },
    )


# ============================================
# Socket.IO Integration (wrap entire app AFTER all setup)
# ============================================

# Import Socket.IO server object (not the ASGI wrapper)
from server.utils.websocket import sio
import socketio

# Wrap the complete FastAPI app with Socket.IO
# This must be done AFTER all routes, middleware, and events are set up
app = socketio.ASGIApp(sio, app, socketio_path='/ws/socket.io')

logger.info("Socket.IO integrated with FastAPI app at /ws/socket.io")


# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")

    uvicorn.run(
        app,  # Run the wrapped app directly
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=False,  # Disable reload when using wrapped app
        log_level=config.LOG_LEVEL.lower(),
    )
