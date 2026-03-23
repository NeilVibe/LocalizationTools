"""
Statistics API Endpoints for Admin Dashboard

Thin route handlers that delegate to StatsService.
Business logic lives in server/services/stats_service.py.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.utils.dependencies import get_async_db, require_admin_async
from server.services.stats_service import StatsService

# Create router
router = APIRouter(prefix="/api/v2/admin/stats", tags=["Admin Statistics"])


# ============================================================================
# Overview / Real-time Metrics
# ============================================================================

@router.get("/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get real-time overview metrics for dashboard home page."""
    try:
        service = StatsService(db)
        return await service.get_overview()
    except Exception as e:
        logger.error(f"Error fetching overview stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch overview stats: {str(e)}")


# ============================================================================
# Daily Statistics
# ============================================================================

@router.get("/daily")
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get daily usage statistics for the specified number of days."""
    try:
        service = StatsService(db)
        return await service.get_daily_stats(days)
    except Exception as e:
        logger.error(f"Error fetching daily stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch daily stats: {str(e)}")


# ============================================================================
# Weekly Statistics
# ============================================================================

@router.get("/weekly")
async def get_weekly_stats(
    weeks: int = Query(12, ge=1, le=52, description="Number of weeks to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get weekly aggregated statistics."""
    try:
        service = StatsService(db)
        return await service.get_weekly_stats(weeks)
    except Exception as e:
        logger.error(f"Error fetching weekly stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch weekly stats: {str(e)}")


# ============================================================================
# Monthly Statistics
# ============================================================================

@router.get("/monthly")
async def get_monthly_stats(
    months: int = Query(12, ge=1, le=24, description="Number of months to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get monthly aggregated statistics."""
    try:
        service = StatsService(db)
        return await service.get_monthly_stats(months)
    except Exception as e:
        logger.error(f"Error fetching monthly stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch monthly stats: {str(e)}")


# ============================================================================
# Tool Popularity Statistics
# ============================================================================

@router.get("/tools/popularity")
async def get_tool_popularity(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get tool popularity statistics."""
    try:
        service = StatsService(db)
        return await service.get_tool_popularity(days)
    except Exception as e:
        logger.error(f"Error fetching tool popularity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tool popularity: {str(e)}")


# ============================================================================
# Function-Level Statistics
# ============================================================================

@router.get("/tools/{tool_name}/functions")
async def get_function_stats(
    tool_name: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get function-level statistics for a specific tool."""
    try:
        service = StatsService(db)
        return await service.get_function_stats(tool_name, days)
    except Exception as e:
        logger.error(f"Error fetching function stats for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch function stats: {str(e)}")


# ============================================================================
# Performance Metrics
# ============================================================================

@router.get("/performance/fastest")
async def get_fastest_functions(
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    min_usage: int = Query(10, ge=1, description="Minimum usage count for inclusion"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get fastest functions by average duration."""
    try:
        service = StatsService(db)
        return await service.get_fastest_functions(limit, days, min_usage)
    except Exception as e:
        logger.error(f"Error fetching fastest functions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch fastest functions: {str(e)}")


@router.get("/performance/slowest")
async def get_slowest_functions(
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    min_usage: int = Query(10, ge=1, description="Minimum usage count for inclusion"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get slowest functions by average duration."""
    try:
        service = StatsService(db)
        return await service.get_slowest_functions(limit, days, min_usage)
    except Exception as e:
        logger.error(f"Error fetching slowest functions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch slowest functions: {str(e)}")


# ============================================================================
# Error Tracking
# ============================================================================

@router.get("/errors/rate")
async def get_error_rate(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get error rate over time."""
    try:
        service = StatsService(db)
        return await service.get_error_rate(days)
    except Exception as e:
        logger.error(f"Error fetching error rate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch error rate: {str(e)}")


@router.get("/errors/top")
async def get_top_errors(
    limit: int = Query(10, ge=1, le=50, description="Number of errors to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get most common errors."""
    try:
        service = StatsService(db)
        return await service.get_top_errors(limit, days)
    except Exception as e:
        logger.error(f"Error fetching top errors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top errors: {str(e)}")


# ============================================================================
# Team & Language Analytics
# ============================================================================

@router.get("/analytics/by-team")
async def get_stats_by_team(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get usage statistics grouped by team."""
    try:
        service = StatsService(db)
        return await service.get_stats_by_team(days)
    except Exception as e:
        logger.error(f"Error fetching team analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch team analytics: {str(e)}")


@router.get("/analytics/by-language")
async def get_stats_by_language(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get usage statistics grouped by user's primary language."""
    try:
        service = StatsService(db)
        return await service.get_stats_by_language(days)
    except Exception as e:
        logger.error(f"Error fetching language analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch language analytics: {str(e)}")


@router.get("/analytics/user-rankings")
async def get_user_rankings(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get top users by activity with profile info."""
    try:
        service = StatsService(db)
        return await service.get_user_rankings(days, limit)
    except Exception as e:
        logger.error(f"Error fetching user rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user rankings: {str(e)}")


# ============================================================================
# Server Logs Endpoint
# ============================================================================

@router.get("/server-logs")
async def get_server_logs(
    lines: int = Query(default=100, description="Number of log lines to return"),
    current_user: dict = Depends(require_admin_async)
):
    """Get server log file contents (last N lines)."""
    try:
        service = StatsService(None)  # No DB needed for log reading
        return await service.get_server_logs(lines)
    except Exception as e:
        logger.error(f"Error reading server logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read server logs: {str(e)}")


# ============================================================================
# Database Monitoring Endpoint
# ============================================================================

@router.get("/database")
async def get_database_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get comprehensive database statistics."""
    try:
        service = StatsService(db)
        return await service.get_database_stats()
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")


# ============================================================================
# Server Monitoring Endpoint
# ============================================================================

@router.get("/server")
async def get_server_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """Get comprehensive server statistics."""
    try:
        service = StatsService(db)
        return await service.get_server_stats()
    except Exception as e:
        logger.error(f"Error getting server stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get server stats: {str(e)}")
