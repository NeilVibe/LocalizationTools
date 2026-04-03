"""
Admin Telemetry API - Dashboard Endpoints for Central Server Monitoring

Priority 12.5.8 - Admin Dashboard Telemetry Tab
Provides endpoints for viewing telemetry data from desktop installations.
Uses JWT authentication (admin role required).

Thin route handlers -- business logic in server/services/telemetry_service.py.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.utils.dependencies import get_async_db, require_admin_async
from server.services.telemetry_service import TelemetryService

# Create router
router = APIRouter(prefix="/api/v2/admin/telemetry", tags=["Admin Telemetry"])


# ============================================================================
# Overview / Summary
# ============================================================================

@router.get("/overview")
async def get_telemetry_overview(
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get telemetry overview for dashboard home.

    Returns:
    - Total active installations
    - Active sessions (now)
    - Today's log count
    - Error/Critical count (24h)
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_overview()
    except Exception as e:
        logger.error(f"Error fetching telemetry overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview: {str(e)}")


# ============================================================================
# Installations
# ============================================================================

@router.get("/installations")
async def get_installations(
    include_inactive: bool = Query(False, description="Include inactive installations"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get all registered installations.

    Returns list of installations with status and last activity.
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_installations(include_inactive=include_inactive)
    except Exception as e:
        logger.error(f"Error fetching installations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch installations: {str(e)}")


@router.get("/installations/{installation_id}")
async def get_installation_detail(
    installation_id: str,
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get detailed information for a specific installation.
    """
    try:
        svc = TelemetryService(db)
        result = await svc.get_installation_detail(installation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Installation not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching installation detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch installation: {str(e)}")


# ============================================================================
# Sessions
# ============================================================================

@router.get("/sessions")
async def get_sessions(
    active_only: bool = Query(True, description="Only show active sessions"),
    days: int = Query(7, ge=1, le=30, description="Number of days of history"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get remote sessions with optional filtering.
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_sessions(active_only=active_only, days=days, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


# ============================================================================
# Logs
# ============================================================================

@router.get("/logs")
async def get_remote_logs(
    installation_id: Optional[str] = Query(None, description="Filter by installation"),
    level: Optional[str] = Query(None, description="Filter by level (INFO, ERROR, etc.)"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get remote logs with filtering options.
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_remote_logs(
            installation_id=installation_id, level=level, hours=hours, limit=limit
        )
    except Exception as e:
        logger.error(f"Error fetching remote logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


@router.get("/logs/errors")
async def get_error_logs(
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get error and critical logs only.
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_error_logs(hours=hours, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch error logs: {str(e)}")


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats/daily")
async def get_daily_telemetry_stats(
    days: int = Query(30, ge=1, le=90, description="Number of days"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get daily telemetry statistics.

    Returns per-day breakdown of:
    - Log counts by level
    - Session counts
    - Active installations
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_daily_stats(days=days)
    except Exception as e:
        logger.error(f"Error fetching daily telemetry stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/stats/by-installation")
async def get_stats_by_installation(
    days: int = Query(30, ge=1, le=90, description="Number of days"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """
    Get aggregated statistics per installation.
    """
    try:
        svc = TelemetryService(db)
        return await svc.get_stats_by_installation(days=days)
    except Exception as e:
        logger.error(f"Error fetching stats by installation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
