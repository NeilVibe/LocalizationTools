"""
Health Status API

Thin route handlers delegating to HealthService.
Provides comprehensive health monitoring for the LocaNext platform.
- Simple status for client apps (green/orange/red)
- Detailed metrics for admin dashboard
- Ping endpoint (no DB, no service needed)
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.services.health_service import HealthService

router = APIRouter(prefix="/api/health", tags=["Health"])


# ============================================================================
# Response Models
# ============================================================================

class SimpleHealthResponse(BaseModel):
    """Simple health status for client apps."""
    status: str  # "healthy", "degraded", "unhealthy"
    api: str  # "connected", "slow", "error"
    database: str  # "connected", "slow", "error"
    websocket: str  # "connected", "disconnected"


class DetailedHealthResponse(BaseModel):
    """Detailed health metrics for admin dashboard."""
    api: Dict[str, Any]
    database: Dict[str, Any]
    websocket: Dict[str, Any]
    system: Dict[str, Any]
    users: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/simple", response_model=SimpleHealthResponse)
async def get_simple_health(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Simple health status for client apps.

    Returns green/orange/red status indicators.
    No authentication required.
    """
    service = HealthService(db)
    return await service.get_simple_health()


@router.get("/status", response_model=DetailedHealthResponse)
async def get_detailed_health(
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async)
):
    """
    Detailed health metrics for admin dashboard.

    Requires admin authentication.
    """
    service = HealthService(db)
    return await service.get_detailed_health()


@router.get("/server-health")
async def get_server_health(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Phase 110: Server & Database health info for StatusPage.

    No auth required (same as /health). Returns DB type, version, connection, table count.
    """
    from sqlalchemy import text
    from loguru import logger
    import server.config as config

    db_type = config.ACTIVE_DATABASE_TYPE
    info = {
        "database_type": db_type,
        "database_version": None,
        "connection_status": "unknown",
        "table_count": 0,
        "server_mode": config.get_user_config().get("server_mode", "standalone"),
        "app_version": config.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        if db_type == "postgresql":
            result = await db.execute(text("SELECT version()"))
            row = result.scalar_one_or_none()
            info["database_version"] = row or "unknown"

            result = await db.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            info["table_count"] = result.scalar_one_or_none() or 0

            result = await db.execute(text("SELECT pg_postmaster_start_time()"))
            start_time = result.scalar_one_or_none()
            if start_time:
                info["uptime_since"] = start_time.isoformat()

            result = await db.execute(text("SELECT pg_database_size(current_database())"))
            db_size = result.scalar_one_or_none() or 0
            info["database_size_mb"] = round(db_size / (1024 * 1024), 1)

        else:
            result = await db.execute(text("SELECT sqlite_version()"))
            info["database_version"] = f"SQLite {result.scalar_one_or_none()}"

            result = await db.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ))
            info["table_count"] = result.scalar_one_or_none() or 0

        info["connection_status"] = "connected"
        logger.info(f"[PHASE110:HEALTH] db={db_type} version={info['database_version']} tables={info['table_count']} connected=true")
    except Exception as exc:
        info["connection_status"] = "error"
        info["error"] = str(exc)
        logger.error(f"[PHASE110:HEALTH] db={db_type} connection error: {exc}")

    return info


@router.get("/ping")
async def ping():
    """
    Ultra-simple ping endpoint for connection testing.

    No database access, no auth - just returns pong.
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}
