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


@router.get("/ping")
async def ping():
    """
    Ultra-simple ping endpoint for connection testing.

    No database access, no auth - just returns pong.
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}
