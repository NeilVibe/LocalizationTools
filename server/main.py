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
from fastapi import FastAPI, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from server import config
from sqlalchemy.orm import Session
from server.utils.dependencies import initialize_database, initialize_async_database, get_async_db, get_db
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
    logger.info(f"Database Mode: {config.DATABASE_MODE}")
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
# Fallback version if config.APP_VERSION is empty (Windows embedded Python issue)
_app_version = config.APP_VERSION or "0.0.0"
app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=_app_version,
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

# Include Admin Telemetry API (for central server monitoring)
from server.api import admin_telemetry
app.include_router(admin_telemetry.router)

# Include Admin DB Stats API (P21: Database Powerhouse monitoring)
from server.api import admin_db_stats
app.include_router(admin_db_stats.router)

# Include Health Status API (P24: Server Status Dashboard)
from server.api import health
app.include_router(health.router)

# Include LDM (LanguageData Manager) API - Real-time collaborative CAT tool
from server.tools.ldm import api as ldm_api
app.include_router(ldm_api.router)

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
        "database_mode": config.DATABASE_MODE,
        "database_type": config.ACTIVE_DATABASE_TYPE,
        "docs": f"{config.DOCS_URL}" if config.ENABLE_DOCS else "disabled",
    }


@app.get("/api/status")
async def get_status():
    """
    P33 Phase 4: Connection status endpoint for UI badges.

    Returns:
        - connection_mode: "online" | "offline"
        - database_type: "postgresql" | "sqlite"
        - database_mode: "auto" | "postgresql" | "sqlite"
        - can_sync: true if online (can sync TMs to server)
    """
    is_online = config.ACTIVE_DATABASE_TYPE == "postgresql"

    return {
        "connection_mode": "online" if is_online else "offline",
        "database_type": config.ACTIVE_DATABASE_TYPE,
        "database_mode": config.DATABASE_MODE,
        "can_sync": is_online,
        "server_version": config.APP_VERSION,
    }


@app.post("/api/go-online")
async def go_online():
    """
    P33 Phase 5: Attempt to reconnect to PostgreSQL (Go Online).

    This endpoint checks if PostgreSQL is reachable and attempts to switch
    from SQLite to PostgreSQL mode. Currently requires app restart to take effect.

    Returns:
        - success: bool
        - message: status message
        - postgresql_reachable: bool
        - action_required: "restart" | "none"
    """
    from server.database.db_setup import check_postgresql_reachable

    # Check if already online
    if config.ACTIVE_DATABASE_TYPE == "postgresql":
        return {
            "success": True,
            "message": "Already connected to PostgreSQL",
            "postgresql_reachable": True,
            "action_required": "none"
        }

    # Check PostgreSQL reachability
    pg_url = config.POSTGRES_URL
    is_reachable = check_postgresql_reachable(pg_url)

    if is_reachable:
        return {
            "success": True,
            "message": "PostgreSQL is reachable. Please restart the application to go online.",
            "postgresql_reachable": True,
            "action_required": "restart"
        }
    else:
        return {
            "success": False,
            "message": "PostgreSQL is not reachable. Check your network connection.",
            "postgresql_reachable": False,
            "action_required": "none"
        }


@app.get("/api/server-config")
async def get_server_config():
    """
    BUG-012 Fix: Get current server configuration.

    Returns the current PostgreSQL settings (without password for security).
    Allows frontend to display current configuration in Server Settings UI.
    """
    return {
        "postgres_host": config.POSTGRES_HOST,
        "postgres_port": config.POSTGRES_PORT,
        "postgres_user": config.POSTGRES_USER,
        "postgres_db": config.POSTGRES_DB,
        "postgres_password_set": config.POSTGRES_PASSWORD != "change_this_password",
        "config_file_path": str(config.USER_CONFIG_PATH),
        "config_file_exists": config.USER_CONFIG_PATH.exists(),
        "database_mode": config.DATABASE_MODE,
        "active_database_type": config.ACTIVE_DATABASE_TYPE
    }


@app.post("/api/server-config")
async def save_server_config(request: Request):
    """
    BUG-012 Fix: Save server configuration to user config file.

    Saves PostgreSQL connection settings to user config file.
    Requires app restart to take effect.

    Request body:
    {
        "postgres_host": "172.28.150.120",
        "postgres_port": 5432,
        "postgres_user": "locanext",
        "postgres_password": "password",
        "postgres_db": "locanext"
    }
    """
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ["postgres_host", "postgres_port", "postgres_user", "postgres_password", "postgres_db"]
        for field in required_fields:
            if field not in data:
                return {"success": False, "message": f"Missing required field: {field}"}

        # Build config object
        user_config = {
            "postgres_host": data["postgres_host"],
            "postgres_port": int(data["postgres_port"]),
            "postgres_user": data["postgres_user"],
            "postgres_password": data["postgres_password"],
            "postgres_db": data["postgres_db"]
        }

        # Save to file
        success = config.save_user_config(user_config)

        if success:
            logger.info(f"Server config saved to {config.USER_CONFIG_PATH}")
            return {
                "success": True,
                "message": "Configuration saved. Please restart the application to apply changes.",
                "config_file_path": str(config.USER_CONFIG_PATH),
                "action_required": "restart"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save configuration file.",
                "action_required": "none"
            }

    except json.JSONDecodeError:
        return {"success": False, "message": "Invalid JSON in request body"}
    except Exception as e:
        logger.error(f"Error saving server config: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/server-config/test")
async def test_server_connection(request: Request):
    """
    BUG-012 Fix: Test PostgreSQL connection with provided settings.

    Tests if the provided PostgreSQL settings can connect to the server.
    Does NOT save the configuration.

    Request body:
    {
        "postgres_host": "172.28.150.120",
        "postgres_port": 5432,
        "postgres_user": "locanext",
        "postgres_password": "password",
        "postgres_db": "locanext"
    }
    """
    try:
        data = await request.json()

        host = data.get("postgres_host", "localhost")
        port = int(data.get("postgres_port", 5432))
        user = data.get("postgres_user", "")
        password = data.get("postgres_password", "")
        db = data.get("postgres_db", "")

        # Test connection using socket first (fast check)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            result = sock.connect_ex((host, port))
            sock.close()
            if result != 0:
                return {
                    "success": False,
                    "message": f"Cannot reach {host}:{port}. Check host and port.",
                    "reachable": False
                }
        except socket.error as e:
            return {
                "success": False,
                "message": f"Network error: {str(e)}",
                "reachable": False
            }

        # Host is reachable, try actual PostgreSQL connection
        try:
            from sqlalchemy import create_engine, text
            test_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
            test_engine = create_engine(test_url, pool_pre_ping=True)

            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            test_engine.dispose()

            return {
                "success": True,
                "message": f"Successfully connected to PostgreSQL at {host}:{port}/{db}",
                "reachable": True,
                "authenticated": True
            }

        except Exception as e:
            error_msg = str(e)
            if "authentication failed" in error_msg.lower():
                return {
                    "success": False,
                    "message": "Authentication failed. Check username and password.",
                    "reachable": True,
                    "authenticated": False
                }
            elif "does not exist" in error_msg.lower():
                return {
                    "success": False,
                    "message": f"Database '{db}' does not exist on the server.",
                    "reachable": True,
                    "authenticated": True
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection error: {error_msg}",
                    "reachable": True,
                    "authenticated": False
                }

    except json.JSONDecodeError:
        return {"success": False, "message": "Invalid JSON in request body"}
    except Exception as e:
        logger.error(f"Error testing server connection: {e}")
        return {"success": False, "message": str(e)}


@app.get(config.HEALTH_CHECK_ENDPOINT)
async def health_check():
    """
    Health check endpoint.

    P33 Offline Mode: Returns auto_token for SQLite mode (local access).
    Frontend can use this token to auto-login without credentials.
    """
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

    # Base response
    response = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_type": config.ACTIVE_DATABASE_TYPE,
        "version": config.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

    # P33: Auto-token for SQLite offline mode
    # Local mode = no login required, full admin access
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        from server.utils.auth import create_access_token
        response["local_mode"] = True
        response["auto_token"] = create_access_token({
            "user_id": "LOCAL",
            "username": "LOCAL",
            "role": "admin"
        })
        logger.debug("Health check: SQLite mode - auto_token provided for local access")
    else:
        response["local_mode"] = False

    return response


# ============================================
# Additional API Routes
# ============================================


@app.get("/api/version/latest")
async def get_latest_version():
    """Get latest app version info."""
    from sqlalchemy import select
    from server.utils.dependencies import get_async_db
    from server.database.models import AppVersion

    async for db in get_async_db():
        result = await db.execute(
            select(AppVersion).where(AppVersion.is_latest == True).order_by(AppVersion.release_date.desc()).limit(1)
        )
        latest = result.scalars().first()

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


@app.get("/api/announcements")
def get_announcements(db: Session = Depends(get_db)):
    """Get active announcements for users.

    NOTE: Uses SYNC db session to avoid async event loop test isolation issues.
    See docs/cicd/TROUBLESHOOTING.md "Known Issue: Async Event Loop Test Isolation"
    """
    from sqlalchemy import or_
    from server.database.models import Announcement

    now = datetime.utcnow()
    announcements = db.query(Announcement).filter(
        Announcement.is_active == True,
        or_(Announcement.expires_at == None, Announcement.expires_at > now)
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

# Import LDM WebSocket handlers (registers event handlers on sio)
try:
    import server.tools.ldm.websocket  # noqa: F401 - registers @sio.event handlers
    logger.info("LDM WebSocket handlers registered")
except ImportError as e:
    logger.warning(f"LDM WebSocket handlers not available: {e}")

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
