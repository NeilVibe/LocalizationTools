"""
Rankings API Endpoints for Admin Dashboard

Thin route handlers that delegate to RankingsService.
Business logic lives in server/services/rankings_service.py.
"""

from __future__ import annotations

from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.utils.dependencies import get_async_db, require_admin_async
from server.services.rankings_service import RankingsService

# Create router
router = APIRouter(prefix="/api/v2/admin/rankings", tags=["Admin Rankings"])


# ============================================================================
# User Rankings
# ============================================================================

@router.get("/users")
async def get_user_rankings(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get user rankings by operations count."""
    try:
        service = RankingsService(db)
        return await service.get_user_rankings(period, limit)
    except Exception as e:
        logger.error(f"Error fetching user rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user rankings: {str(e)}")


@router.get("/users/by-time")
async def get_user_rankings_by_time(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get user rankings by total processing time spent."""
    try:
        service = RankingsService(db)
        return await service.get_user_rankings_by_time(period, limit)
    except Exception as e:
        logger.error(f"Error fetching user rankings by time: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user rankings by time: {str(e)}")


# ============================================================================
# App Rankings
# ============================================================================

@router.get("/apps")
async def get_app_rankings(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get app/tool rankings by usage."""
    try:
        service = RankingsService(db)
        return await service.get_app_rankings(period)
    except Exception as e:
        logger.error(f"Error fetching app rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch app rankings: {str(e)}")


# ============================================================================
# Function Rankings
# ============================================================================

@router.get("/functions")
async def get_function_rankings(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of functions to return"),
    tool_name: Optional[str] = Query(None, description="Filter by specific tool"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get function rankings by usage."""
    try:
        service = RankingsService(db)
        return await service.get_function_rankings(period, limit, tool_name)
    except Exception as e:
        logger.error(f"Error fetching function rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch function rankings: {str(e)}")


@router.get("/functions/by-time")
async def get_function_rankings_by_time(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of functions to return"),
    tool_name: Optional[str] = Query(None, description="Filter by specific tool"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get function rankings by total processing time."""
    try:
        service = RankingsService(db)
        return await service.get_function_rankings_by_time(period, limit, tool_name)
    except Exception as e:
        logger.error(f"Error fetching function rankings by time: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch function rankings by time: {str(e)}")


# ============================================================================
# Combined Top Rankings (One-Stop Overview)
# ============================================================================

@router.get("/top")
async def get_top_rankings(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    db: AsyncSession = Depends(get_async_db),
    _admin: dict = Depends(require_admin_async),
):
    """Get combined top rankings in one call."""
    try:
        service = RankingsService(db)
        return await service.get_top_rankings(period)
    except Exception as e:
        logger.error(f"Error fetching combined top rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch combined top rankings: {str(e)}")
