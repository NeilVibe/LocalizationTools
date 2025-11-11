"""
Rankings API Endpoints for Admin Dashboard

Provides leaderboard and ranking data:
- Top users (by operations, by time spent)
- Top apps (most used)
- Top functions (most used, most time consuming)
- Daily/weekly/monthly/all-time rankings
"""

from datetime import datetime, timedelta
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, desc, text
from loguru import logger

from server.database.models import User as UserModel, LogEntry
from server.utils.dependencies import get_async_db, require_admin_async

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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get user rankings by operations count.

    Returns top N users with:
    - Rank
    - Username
    - Display name
    - Total operations
    - Time spent (total duration)
    - Active days
    - Top tool
    """
    try:
        logger.info(f"Requesting user rankings for period: {period}")

        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)  # Far past date

        # Query user rankings with their statistics
        # Using subquery for top tool per user
        query = select(
            UserModel.username,
            UserModel.full_name,
            func.count(LogEntry.log_id).label('total_operations'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
            func.count(func.distinct(func.date(LogEntry.timestamp))).label('active_days')
        ).join(
            LogEntry, UserModel.user_id == LogEntry.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.user_id,
            UserModel.username,
            UserModel.full_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results with rank and time formatting
        user_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            # Get user's top tool (most used)
            top_tool_query = select(
                LogEntry.tool_name,
                func.count(LogEntry.log_id).label('count')
            ).where(
                and_(
                    LogEntry.username == row.username,
                    LogEntry.timestamp >= start_date
                )
            ).group_by(
                LogEntry.tool_name
            ).order_by(
                func.count(LogEntry.log_id).desc()
            ).limit(1)

            top_tool_result = await db.execute(top_tool_query)
            top_tool_row = top_tool_result.first()
            top_tool = top_tool_row.tool_name if top_tool_row else "N/A"

            user_rankings.append({
                "rank": idx,
                "username": row.username,
                "display_name": row.full_name or row.username,
                "total_operations": int(row.total_operations),
                "time_spent": f"{hours}h {minutes}m",
                "time_spent_seconds": int(total_seconds),
                "active_days": int(row.active_days),
                "top_tool": top_tool
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "rankings": user_rankings
        }

    except Exception as e:
        logger.error(f"Error fetching user rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user rankings: {str(e)}")


@router.get("/users/by-time")
async def get_user_rankings_by_time(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    db: AsyncSession = Depends(get_async_db),
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get user rankings by total processing time spent.

    Same structure as operations ranking but sorted by time.
    """
    try:
        logger.info(f"Requesting user rankings by time for period: {period}")

        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Query user rankings sorted by time spent
        query = select(
            UserModel.username,
            UserModel.full_name,
            func.count(LogEntry.log_id).label('total_operations'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
            func.count(func.distinct(func.date(LogEntry.timestamp))).label('active_days')
        ).join(
            LogEntry, UserModel.user_id == LogEntry.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.user_id,
            UserModel.username,
            UserModel.full_name
        ).order_by(
            func.sum(LogEntry.duration_seconds).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        user_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            # Get user's top tool
            top_tool_query = select(
                LogEntry.tool_name,
                func.count(LogEntry.log_id).label('count')
            ).where(
                and_(
                    LogEntry.username == row.username,
                    LogEntry.timestamp >= start_date
                )
            ).group_by(
                LogEntry.tool_name
            ).order_by(
                func.count(LogEntry.log_id).desc()
            ).limit(1)

            top_tool_result = await db.execute(top_tool_query)
            top_tool_row = top_tool_result.first()
            top_tool = top_tool_row.tool_name if top_tool_row else "N/A"

            user_rankings.append({
                "rank": idx,
                "username": row.username,
                "display_name": row.full_name or row.username,
                "total_operations": int(row.total_operations),
                "time_spent": f"{hours}h {minutes}m",
                "time_spent_seconds": int(total_seconds),
                "active_days": int(row.active_days),
                "top_tool": top_tool
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "sort_by": "time_spent",
            "rankings": user_rankings
        }

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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get app/tool rankings by usage.

    Returns all apps ranked by:
    - Total usage count
    - Unique users
    - Total processing time
    - Average duration per operation
    """
    try:
        logger.info(f"Requesting app rankings for period: {period}")

        # Calculate date range
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Query app rankings
        query = select(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            LogEntry.tool_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results
        app_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            app_rankings.append({
                "rank": idx,
                "app_name": row.tool_name,
                "usage_count": int(row.usage_count),
                "unique_users": int(row.unique_users),
                "total_time": f"{hours}h {minutes}m",
                "total_time_seconds": int(total_seconds),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "rankings": app_rankings
        }

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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get function rankings by usage.

    Returns top N functions with:
    - Tool name
    - Function name
    - Usage count
    - Average duration
    - Success rate
    """
    try:
        logger.info(f"Requesting function rankings for period: {period}")

        # Calculate date range
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Build query with optional tool filter
        conditions = [LogEntry.timestamp >= start_date]
        if tool_name:
            conditions.append(LogEntry.tool_name == tool_name)

        # Query function rankings
        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration'),
            func.round(
                100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id),
                2
            ).label('success_rate')
        ).where(
            and_(*conditions)
        ).group_by(
            LogEntry.tool_name,
            LogEntry.function_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        function_rankings = []
        for idx, row in enumerate(rows, 1):
            function_rankings.append({
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "usage_count": int(row.usage_count),
                "avg_duration": float(row.avg_duration or 0),
                "success_rate": float(row.success_rate or 0)
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "tool_filter": tool_name,
            "rankings": function_rankings
        }

    except Exception as e:
        logger.error(f"Error fetching function rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch function rankings: {str(e)}")


@router.get("/functions/by-time")
async def get_function_rankings_by_time(
    period: Literal["daily", "weekly", "monthly", "all_time"] = Query("monthly", description="Ranking period"),
    limit: int = Query(20, ge=1, le=100, description="Number of functions to return"),
    tool_name: Optional[str] = Query(None, description="Filter by specific tool"),
    db: AsyncSession = Depends(get_async_db),
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get function rankings by total processing time.

    Returns top N functions sorted by cumulative time spent.
    """
    try:
        logger.info(f"Requesting function rankings by time for period: {period}")

        # Calculate date range
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Build query with optional tool filter
        conditions = [LogEntry.timestamp >= start_date]
        if tool_name:
            conditions.append(LogEntry.tool_name == tool_name)

        # Query function rankings by total time
        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration'),
            func.round(
                100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id),
                2
            ).label('success_rate')
        ).where(
            and_(*conditions)
        ).group_by(
            LogEntry.tool_name,
            LogEntry.function_name
        ).order_by(
            func.sum(LogEntry.duration_seconds).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        function_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            function_rankings.append({
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "usage_count": int(row.usage_count),
                "total_time": f"{hours}h {minutes}m",
                "total_time_seconds": int(total_seconds),
                "avg_duration": float(row.avg_duration or 0),
                "success_rate": float(row.success_rate or 0)
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "tool_filter": tool_name,
            "sort_by": "total_time",
            "rankings": function_rankings
        }

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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
):
    """
    Get combined top rankings in one call.

    Returns:
    - Top 10 users
    - Top 5 apps
    - Top 10 functions

    Perfect for dashboard overview page.
    """
    try:
        logger.info(f"Requesting combined top rankings for period: {period}")

        # Calculate date range
        end_date = datetime.utcnow()
        if period == "daily":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Top 10 Users
        users_query = select(
            UserModel.username,
            UserModel.full_name,
            func.count(LogEntry.log_id).label('operations')
        ).join(
            LogEntry, UserModel.user_id == LogEntry.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.user_id,
            UserModel.username,
            UserModel.full_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(10)

        users_result = await db.execute(users_query)
        top_users = [
            {
                "rank": idx,
                "username": row.username,
                "display_name": row.full_name or row.username,
                "operations": int(row.operations)
            }
            for idx, row in enumerate(users_result.all(), 1)
        ]

        # Top 5 Apps
        apps_query = select(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label('usage_count')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            LogEntry.tool_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(5)

        apps_result = await db.execute(apps_query)
        top_apps = [
            {
                "rank": idx,
                "app_name": row.tool_name,
                "usage_count": int(row.usage_count)
            }
            for idx, row in enumerate(apps_result.all(), 1)
        ]

        # Top 10 Functions
        functions_query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            LogEntry.tool_name,
            LogEntry.function_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(10)

        functions_result = await db.execute(functions_query)
        top_functions = [
            {
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "usage_count": int(row.usage_count)
            }
            for idx, row in enumerate(functions_result.all(), 1)
        ]

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "top_users": top_users,
            "top_apps": top_apps,
            "top_functions": top_functions
        }

    except Exception as e:
        logger.error(f"Error fetching combined top rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch combined top rankings: {str(e)}")
