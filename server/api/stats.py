"""
Statistics API Endpoints for Admin Dashboard

Provides comprehensive analytics including:
- Daily/weekly/monthly usage statistics
- Tool popularity and function-level breakdowns
- Performance metrics and trends
- User activity and engagement
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, desc, text, cast
from sqlalchemy.types import Numeric
from loguru import logger

from server.database.models import User as UserModel, Session, LogEntry, ErrorLog
from server.utils.dependencies import get_async_db, require_admin_async

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
    """
    Get real-time overview metrics for dashboard home page.

    Returns:
    - Active users (last 30 minutes)
    - Today's operations
    - Success rate
    - Average duration
    """
    try:
        logger.info("Requesting overview stats")

        # Active users (last 30 minutes)
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        active_users_query = select(func.count(func.distinct(Session.user_id))).where(
            and_(
                Session.is_active == True,
                Session.last_activity >= thirty_min_ago
            )
        )
        active_users_result = await db.execute(active_users_query)
        active_users = active_users_result.scalar() or 0

        # Today's operations
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_ops_query = select(func.count(LogEntry.log_id)).where(
            LogEntry.timestamp >= today_start
        )
        today_ops_result = await db.execute(today_ops_query)
        today_operations = today_ops_result.scalar() or 0

        # Success rate (today)
        success_rate_query = select(
            func.round(
                cast(
                    100.0 * func.sum(
                        case((LogEntry.status == 'success', 1), else_=0)
                    ) / func.count(LogEntry.log_id),
                    Numeric
                ),
                2
            )
        ).where(LogEntry.timestamp >= today_start)
        success_rate_result = await db.execute(success_rate_query)
        success_rate = success_rate_result.scalar() or 0.0

        # Average duration (today, successful operations only)
        avg_duration_query = select(
            func.avg(LogEntry.duration_seconds)
        ).where(
            and_(
                LogEntry.timestamp >= today_start,
                LogEntry.status == 'success'
            )
        )
        avg_duration_result = await db.execute(avg_duration_query)
        avg_duration = avg_duration_result.scalar() or 0.0

        return {
            "active_users": active_users,
            "today_operations": today_operations,
            "success_rate": float(success_rate),
            "avg_duration_seconds": round(float(avg_duration), 2)
        }

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
    """
    Get daily usage statistics for the specified number of days.

    Returns operations per day with:
    - Total operations
    - Unique users
    - Successful operations
    """
    try:
        logger.info(f"Requesting daily stats for {days} days")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Query daily statistics
        query = select(
            func.date(LogEntry.timestamp).label('date'),
            func.count(LogEntry.log_id).label('operations'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(
                case((LogEntry.status == 'success', 1), else_=0)
            ).label('successful_ops'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.date(LogEntry.timestamp)
        ).order_by(
            func.date(LogEntry.timestamp)
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results
        daily_stats = []
        for row in rows:
            date_str = row.date.isoformat() if row.date else None
            daily_stats.append({
                "date": date_str,
                "operations": int(row.operations),
                "unique_users": int(row.unique_users),
                "successful_ops": int(row.successful_ops or 0),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": f"last_{days}_days",
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "data": daily_stats
        }

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
    """
    Get weekly aggregated statistics.

    Returns week-by-week breakdown with:
    - Total operations
    - Unique users
    - Success rate
    - Average duration
    """
    try:
        logger.info(f"Requesting weekly stats for {weeks} weeks")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks)

        # Query weekly statistics (PostgreSQL)
        query = select(
            func.to_char(LogEntry.timestamp, 'IYYY-IW').label('week_start'),
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('success_rate'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.to_char(LogEntry.timestamp, 'IYYY-IW')
        ).order_by(
            func.to_char(LogEntry.timestamp, 'IYYY-IW').desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results
        weekly_stats = []
        for row in rows:
            # week_start is already a string in format 'YYYY-WW'
            weekly_stats.append({
                "week_start": row.week_start,
                "total_ops": int(row.total_ops),
                "unique_users": int(row.unique_users),
                "success_rate": float(row.success_rate or 0),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": f"last_{weeks}_weeks",
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "data": weekly_stats
        }

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
    """
    Get monthly aggregated statistics.

    Returns month-by-month breakdown with:
    - Total operations
    - Unique users
    - Successful operations
    - Failed operations
    - Average duration
    """
    try:
        logger.info(f"Requesting monthly stats for {months} months")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)  # Approximate

        # Query monthly statistics (PostgreSQL)
        query = select(
            func.to_char(LogEntry.timestamp, 'YYYY-MM').label('month'),
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(
                case((LogEntry.status == 'success', 1), else_=0)
            ).label('successful_ops'),
            func.sum(
                case((LogEntry.status == 'error', 1), else_=0)
            ).label('failed_ops'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.to_char(LogEntry.timestamp, 'YYYY-MM')
        ).order_by(
            func.to_char(LogEntry.timestamp, 'YYYY-MM').desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results
        monthly_stats = []
        for row in rows:
            monthly_stats.append({
                "month": row.month,
                "total_ops": int(row.total_ops),
                "unique_users": int(row.unique_users),
                "successful_ops": int(row.successful_ops or 0),
                "failed_ops": int(row.failed_ops or 0),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": f"last_{months}_months",
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "data": monthly_stats
        }

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
    """
    Get tool popularity statistics.

    Returns most used tools with:
    - Usage count
    - Unique users
    - Percentage of total usage
    - Average duration
    """
    try:
        logger.info(f"Requesting tool popularity for {days} days")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total operations count for percentage calculation
        total_ops_query = select(func.count(LogEntry.log_id)).where(
            LogEntry.timestamp >= start_date
        )
        total_ops_result = await db.execute(total_ops_query)
        total_ops = total_ops_result.scalar() or 1  # Avoid division by zero

        # Query tool popularity
        query = select(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
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

        # Format results with percentage
        tool_stats = []
        for row in rows:
            usage_count = int(row.usage_count)
            percentage = round(100.0 * usage_count / total_ops, 2)
            tool_stats.append({
                "tool_name": row.tool_name,
                "usage_count": usage_count,
                "unique_users": int(row.unique_users),
                "percentage": float(percentage),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": f"last_{days}_days",
            "total_operations": int(total_ops),
            "tools": tool_stats
        }

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
    """
    Get function-level statistics for a specific tool.

    Returns function breakdown with:
    - Usage count
    - Percentage of tool usage
    - Average duration
    - Success rate
    """
    try:
        logger.info(f"Requesting function stats for {tool_name}")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total operations for this tool (for percentage calculation)
        total_tool_ops_query = select(func.count(LogEntry.log_id)).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.tool_name == tool_name
            )
        )
        total_tool_ops_result = await db.execute(total_tool_ops_query)
        total_tool_ops = total_tool_ops_result.scalar() or 1  # Avoid division by zero

        # Query function statistics
        query = select(
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('success_rate')
        ).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.tool_name == tool_name
            )
        ).group_by(
            LogEntry.function_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results with percentage
        function_stats = []
        for row in rows:
            usage_count = int(row.usage_count)
            pct_of_tool = round(100.0 * usage_count / total_tool_ops, 2)
            function_stats.append({
                "function_name": row.function_name,
                "usage_count": usage_count,
                "pct_of_tool": float(pct_of_tool),
                "avg_duration": float(row.avg_duration or 0),
                "success_rate": float(row.success_rate or 0)
            })

        return {
            "tool_name": tool_name,
            "period": f"last_{days}_days",
            "total_operations": int(total_tool_ops),
            "functions": function_stats
        }

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
    """
    Get fastest functions by average duration.

    Returns top N fastest functions with:
    - Tool name
    - Function name
    - Average duration
    - Usage count
    - Min/max duration
    """
    try:
        logger.info(f"Requesting top {limit} fastest functions")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query fastest functions
        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration'),
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(func.min(LogEntry.duration_seconds), 2).label('min_duration'),
            func.round(func.max(LogEntry.duration_seconds), 2).label('max_duration')
        ).where(
            and_(
                LogEntry.status == 'success',
                LogEntry.timestamp >= start_date
            )
        ).group_by(
            LogEntry.tool_name,
            LogEntry.function_name
        ).having(
            func.count(LogEntry.log_id) >= min_usage
        ).order_by(
            func.avg(LogEntry.duration_seconds).asc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        fastest_functions = []
        for idx, row in enumerate(rows, 1):
            fastest_functions.append({
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "avg_duration": float(row.avg_duration or 0),
                "usage_count": int(row.usage_count),
                "min_duration": float(row.min_duration or 0),
                "max_duration": float(row.max_duration or 0)
            })

        return {
            "period": f"last_{days}_days",
            "min_usage_threshold": min_usage,
            "fastest_functions": fastest_functions
        }

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
    """
    Get slowest functions by average duration.

    Returns top N slowest functions (same structure as fastest).
    """
    try:
        logger.info(f"Requesting top {limit} slowest functions")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query slowest functions (same as fastest but DESC order)
        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration'),
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(func.min(LogEntry.duration_seconds), 2).label('min_duration'),
            func.round(func.max(LogEntry.duration_seconds), 2).label('max_duration')
        ).where(
            and_(
                LogEntry.status == 'success',
                LogEntry.timestamp >= start_date
            )
        ).group_by(
            LogEntry.tool_name,
            LogEntry.function_name
        ).having(
            func.count(LogEntry.log_id) >= min_usage
        ).order_by(
            func.avg(LogEntry.duration_seconds).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        slowest_functions = []
        for idx, row in enumerate(rows, 1):
            slowest_functions.append({
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "avg_duration": float(row.avg_duration or 0),
                "usage_count": int(row.usage_count),
                "min_duration": float(row.min_duration or 0),
                "max_duration": float(row.max_duration or 0)
            })

        return {
            "period": f"last_{days}_days",
            "min_usage_threshold": min_usage,
            "slowest_functions": slowest_functions
        }

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
    """
    Get error rate over time.

    Returns daily error rates with:
    - Total operations
    - Error count
    - Error percentage
    """
    try:
        logger.info(f"Requesting error rate for {days} days")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query daily error rates
        query = select(
            func.date(LogEntry.timestamp).label('date'),
            func.count(LogEntry.log_id).label('total_operations'),
            func.sum(
                case((LogEntry.status == 'error', 1), else_=0)
            ).label('errors'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'error', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('error_rate')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.date(LogEntry.timestamp)
        ).order_by(
            func.date(LogEntry.timestamp)
        )

        result = await db.execute(query)
        rows = result.all()

        # Format results
        error_rates = []
        for row in rows:
            date_str = row.date.isoformat() if row.date else None
            error_rates.append({
                "date": date_str,
                "total_operations": int(row.total_operations),
                "errors": int(row.errors or 0),
                "error_rate": float(row.error_rate or 0)
            })

        return {
            "period": f"last_{days}_days",
            "data": error_rates
        }

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
    """
    Get most common errors.

    Returns top N errors with:
    - Error type/message
    - Count
    - Percentage of total errors
    - Affected users
    - Most common tool
    """
    try:
        logger.info(f"Requesting top {limit} errors")

        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total error count for percentage calculation
        total_errors_query = select(func.count(LogEntry.log_id)).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.status == 'error'
            )
        )
        total_errors_result = await db.execute(total_errors_query)
        total_errors = total_errors_result.scalar() or 1  # Avoid division by zero

        # Query top errors
        # Group by error_message to identify error types
        query = select(
            LogEntry.error_message,
            func.count(LogEntry.log_id).label('error_count'),
            func.count(func.distinct(LogEntry.user_id)).label('affected_users'),
            LogEntry.tool_name  # Most common tool will be handled in subquery
        ).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.status == 'error',
                LogEntry.error_message.isnot(None)
            )
        ).group_by(
            LogEntry.error_message,
            LogEntry.tool_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        top_errors = []
        for row in rows:
            error_count = int(row.error_count)
            pct_of_errors = round(100.0 * error_count / total_errors, 2)

            # Extract error type from message (first 100 chars)
            error_type = row.error_message[:100] if row.error_message else "Unknown error"

            top_errors.append({
                "error_type": error_type,
                "error_count": error_count,
                "pct_of_errors": float(pct_of_errors),
                "affected_users": int(row.affected_users),
                "most_common_tool": row.tool_name
            })

        return {
            "period": f"last_{days}_days",
            "total_errors": int(total_errors),
            "top_errors": top_errors
        }

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
    """
    Get usage statistics grouped by team.

    Returns operations per team with:
    - Team name
    - Total operations
    - Unique users
    - Average duration
    - Most used tool
    """
    try:
        logger.info(f"Requesting team analytics for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Join LogEntry with User to get team info
        query = select(
            UserModel.team,
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('success_rate')
        ).join(
            UserModel, LogEntry.user_id == UserModel.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.team
        ).order_by(
            func.count(LogEntry.log_id).desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Get most used tool per team (separate query)
        team_tools = {}
        for row in rows:
            if row.team:
                tool_query = select(
                    LogEntry.tool_name,
                    func.count(LogEntry.log_id).label('count')
                ).join(
                    UserModel, LogEntry.user_id == UserModel.user_id
                ).where(
                    and_(
                        LogEntry.timestamp >= start_date,
                        UserModel.team == row.team
                    )
                ).group_by(
                    LogEntry.tool_name
                ).order_by(
                    func.count(LogEntry.log_id).desc()
                ).limit(1)
                tool_result = await db.execute(tool_query)
                tool_row = tool_result.first()
                team_tools[row.team] = tool_row.tool_name if tool_row else None

        # Format results
        team_stats = []
        for row in rows:
            team_name = row.team or "Unassigned"
            team_stats.append({
                "team": team_name,
                "total_ops": int(row.total_ops),
                "unique_users": int(row.unique_users),
                "avg_duration": float(row.avg_duration or 0),
                "success_rate": float(row.success_rate or 0),
                "most_used_tool": team_tools.get(row.team, None)
            })

        return {
            "period": f"last_{days}_days",
            "teams": team_stats
        }

    except Exception as e:
        logger.error(f"Error fetching team analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch team analytics: {str(e)}")


@router.get("/analytics/by-language")
async def get_stats_by_language(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get usage statistics grouped by user's primary language.

    Returns operations per language with:
    - Language name
    - Total operations
    - Unique users
    - Average duration
    - Most used tool
    """
    try:
        logger.info(f"Requesting language analytics for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Join LogEntry with User to get language info
        query = select(
            UserModel.language,
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('success_rate')
        ).join(
            UserModel, LogEntry.user_id == UserModel.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.language
        ).order_by(
            func.count(LogEntry.log_id).desc()
        )

        result = await db.execute(query)
        rows = result.all()

        # Get most used tool per language
        lang_tools = {}
        for row in rows:
            if row.language:
                tool_query = select(
                    LogEntry.tool_name,
                    func.count(LogEntry.log_id).label('count')
                ).join(
                    UserModel, LogEntry.user_id == UserModel.user_id
                ).where(
                    and_(
                        LogEntry.timestamp >= start_date,
                        UserModel.language == row.language
                    )
                ).group_by(
                    LogEntry.tool_name
                ).order_by(
                    func.count(LogEntry.log_id).desc()
                ).limit(1)
                tool_result = await db.execute(tool_query)
                tool_row = tool_result.first()
                lang_tools[row.language] = tool_row.tool_name if tool_row else None

        # Format results
        language_stats = []
        for row in rows:
            lang_name = row.language or "Unassigned"
            language_stats.append({
                "language": lang_name,
                "total_ops": int(row.total_ops),
                "unique_users": int(row.unique_users),
                "avg_duration": float(row.avg_duration or 0),
                "success_rate": float(row.success_rate or 0),
                "most_used_tool": lang_tools.get(row.language, None)
            })

        return {
            "period": f"last_{days}_days",
            "languages": language_stats
        }

    except Exception as e:
        logger.error(f"Error fetching language analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch language analytics: {str(e)}")


@router.get("/analytics/user-rankings")
async def get_user_rankings(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(20, ge=1, le=100, description="Number of users to return"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get top users by activity with profile info.

    Returns user rankings with:
    - Full name (or username)
    - Team
    - Language
    - Total operations
    - Success rate
    """
    try:
        logger.info(f"Requesting user rankings for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            UserModel.user_id,
            UserModel.username,
            UserModel.full_name,
            UserModel.team,
            UserModel.language,
            func.count(LogEntry.log_id).label('total_ops'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
                2
            ).label('success_rate'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration')
        ).join(
            UserModel, LogEntry.user_id == UserModel.user_id
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            UserModel.user_id,
            UserModel.username,
            UserModel.full_name,
            UserModel.team,
            UserModel.language
        ).order_by(
            func.count(LogEntry.log_id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Format results
        rankings = []
        for idx, row in enumerate(rows, 1):
            display_name = row.full_name or row.username
            rankings.append({
                "rank": idx,
                "user_id": row.user_id,
                "display_name": display_name,
                "username": row.username,
                "team": row.team or "Unassigned",
                "language": row.language or "Unassigned",
                "total_ops": int(row.total_ops),
                "success_rate": float(row.success_rate or 0),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": f"last_{days}_days",
            "rankings": rankings
        }

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
    """
    Get server log file contents (last N lines).

    Returns real-time server logs from server.log file.
    """
    import os
    from pathlib import Path

    try:
        logger.info(f"Requesting last {lines} server log lines")

        # Path to server log file
        log_file = Path(__file__).parent.parent / "data" / "logs" / "server.log"

        if not log_file.exists():
            logger.warning(f"Server log file not found: {log_file}")
            return {
                "logs": [],
                "total_lines": 0,
                "message": "Server log file not found"
            }

        # Read last N lines from file
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Parse log lines into structured format
        logs = []
        for line in last_lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse log line format: "TIMESTAMP | LEVEL | MESSAGE"
            parts = line.split('|', 2)
            if len(parts) >= 3:
                timestamp = parts[0].strip()
                level = parts[1].strip()
                message = parts[2].strip()

                # Determine status based on level
                status_map = {
                    'INFO': 'info',
                    'SUCCESS': 'success',
                    'WARNING': 'warning',
                    'ERROR': 'error',
                    'CRITICAL': 'error'
                }
                status = status_map.get(level.upper(), 'info')

                logs.append({
                    "timestamp": timestamp,
                    "status": status,
                    "tool_name": "SERVER",
                    "function_name": "system",
                    "username": "system",
                    "message": message,
                    "level": level
                })
            else:
                # If line doesn't match format, add as raw message
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "info",
                    "tool_name": "SERVER",
                    "function_name": "system",
                    "username": "system",
                    "message": line,
                    "level": "INFO"
                })

        return {
            "logs": logs,
            "total_lines": len(all_lines),
            "returned_lines": len(logs),
            "log_file": str(log_file)
        }

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
    """
    Get comprehensive database statistics including:
    - Database size
    - Table information with row counts
    - Column details per table
    - Index information

    PostgreSQL only.
    """
    from sqlalchemy import text

    try:
        logger.info("Requesting database statistics")

        # Get PostgreSQL version
        version_result = await db.execute(text("SELECT version()"))
        pg_version = version_result.scalar()

        # Get database size
        size_result = await db.execute(text(
            "SELECT pg_database_size(current_database())"
        ))
        size_bytes = size_result.scalar() or 0

        # Get all tables in public schema
        tables_result = await db.execute(text("""
            SELECT
                t.table_name,
                (SELECT reltuples::bigint FROM pg_class WHERE relname = t.table_name) as row_count
            FROM information_schema.tables t
            WHERE t.table_schema = 'public'
            AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
        """))
        table_rows = tables_result.fetchall()

        tables = []
        total_rows = 0

        for table_row in table_rows:
            table_name = table_row.table_name
            row_count = int(table_row.row_count or 0)
            total_rows += row_count

            # Get column info for this table
            columns_result = await db.execute(text("""
                SELECT
                    ordinal_position as cid,
                    column_name as name,
                    data_type as type,
                    is_nullable = 'NO' as notnull,
                    column_default as default_value,
                    (SELECT COUNT(*) > 0 FROM information_schema.table_constraints tc
                     JOIN information_schema.constraint_column_usage ccu
                     ON tc.constraint_name = ccu.constraint_name
                     WHERE tc.table_name = c.table_name
                     AND ccu.column_name = c.column_name
                     AND tc.constraint_type = 'PRIMARY KEY') as pk
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                AND c.table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})

            columns = []
            for col in columns_result.fetchall():
                columns.append({
                    "cid": col.cid,
                    "name": col.name,
                    "type": col.type.upper(),
                    "notnull": col.notnull,
                    "default": col.default_value,
                    "pk": col.pk
                })

            # Get indexes for this table
            indexes_result = await db.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = :table_name
            """), {"table_name": table_name})
            indexes = [row.indexname for row in indexes_result.fetchall()]

            tables.append({
                "name": table_name,
                "row_count": row_count,
                "columns": columns,
                "indexes": indexes
            })

        # Get total index count
        idx_count_result = await db.execute(text("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = 'public'
        """))
        indexes_count = idx_count_result.scalar() or 0

        return {
            "size_bytes": size_bytes,
            "tables": tables,
            "total_rows": total_rows,
            "indexes_count": indexes_count,
            "database_type": "postgresql",
            "pg_version": pg_version,
            "last_modified": datetime.utcnow().isoformat()
        }

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
    """
    Get comprehensive server statistics including:
    - CPU usage and load
    - Memory usage
    - Disk usage
    - Network statistics
    - System information
    """
    import os
    import platform
    import socket

    try:
        logger.info("Requesting server statistics")

        # Try to import psutil for system stats
        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False
            logger.warning("psutil not available, returning limited server stats")

        # Basic system info (always available)
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "python_version": platform.python_version(),
            "pid": os.getpid()
        }

        if has_psutil:
            # CPU info
            cpu_info = {
                "cores": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.1),
                "load_avg": list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0]
            }

            # Memory info
            mem = psutil.virtual_memory()
            memory_info = {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent
            }

            # Disk info
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }

            # Network info
            net_io = psutil.net_io_counters()
            connections = len(psutil.net_connections())
            network_info = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "connections": connections
            }

            # Process info
            process = psutil.Process(os.getpid())
            uptime = datetime.now() - datetime.fromtimestamp(process.create_time())
            uptime_seconds = int(uptime.total_seconds())

        else:
            # Fallback values when psutil not available
            cpu_info = {"cores": os.cpu_count() or 1, "percent": 0, "load_avg": [0, 0, 0]}
            memory_info = {"total": 0, "available": 0, "used": 0, "percent": 0}
            disk_info = {"total": 0, "used": 0, "free": 0, "percent": 0}
            network_info = {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0, "connections": 0}
            uptime_seconds = 0

        # Get active sessions count from database
        try:
            active_sessions_result = await db.execute(
                select(func.count(Session.session_id)).where(Session.is_active == True)
            )
            active_sessions = active_sessions_result.scalar() or 0
        except:
            active_sessions = 0

        # API info
        api_info = {
            "port": 8888,
            "active_sessions": active_sessions,
            "websocket_clients": 0,  # Would need WebSocket manager to track this
            "last_request": datetime.utcnow().isoformat()
        }

        return {
            "status": "running",
            "uptime": uptime_seconds,
            "system": system_info,
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "network": network_info,
            "api": api_info
        }

    except Exception as e:
        logger.error(f"Error getting server stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get server stats: {str(e)}")
