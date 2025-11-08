"""
LocalizationTools Server

Central logging and analytics server for LocalizationTools.
"""

import sys
from pathlib import Path

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

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url=config.DOCS_URL if config.ENABLE_DOCS else None,
    redoc_url=config.REDOC_URL if config.ENABLE_DOCS else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers (sync - for backward compatibility)
app.include_router(auth.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")

# Include async API routers (v2)
app.include_router(auth_async.router, prefix="/api/v2")
app.include_router(logs_async.router, prefix="/api/v2")
app.include_router(sessions_async.router, prefix="/api/v2")

# Mount Socket.IO for WebSocket support
app.mount("/ws", socket_app)


# ============================================
# Startup and Shutdown Events
# ============================================


@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
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

    logger.info("WebSocket server mounted at /ws")
    logger.success("Server startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown."""
    logger.info("Server shutting down...")

    # TODO: Close database connections
    # TODO: Stop background tasks
    # TODO: Cleanup

    logger.success("Server shutdown complete")


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
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")

    uvicorn.run(
        "server.main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower(),
    )
