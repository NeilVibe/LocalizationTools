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
from sqlalchemy import select, func, case, and_, desc, text
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
                100.0 * func.sum(
                    case((LogEntry.status == 'success', 1), else_=0)
                ) / func.count(LogEntry.log_id),
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
            # Handle SQLite returning string vs PostgreSQL returning date object
            date_str = row.date if isinstance(row.date, str) else (row.date.isoformat() if row.date else None)
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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

        # Query weekly statistics
        # For SQLite: group by year-week
        query = select(
            func.strftime('%Y-%W', LogEntry.timestamp).label('week_start'),
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.round(
                100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id),
                2
            ).label('success_rate'),
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.strftime('%Y-%W', LogEntry.timestamp)
        ).order_by(
            func.strftime('%Y-%W', LogEntry.timestamp).desc()
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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

        # Query monthly statistics
        query = select(
            func.strftime('%Y-%m', LogEntry.timestamp).label('month'),
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
            func.strftime('%Y-%m', LogEntry.timestamp)
        ).order_by(
            func.strftime('%Y-%m', LogEntry.timestamp).desc()
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
            func.round(func.avg(LogEntry.duration_seconds), 2).label('avg_duration'),
            func.round(
                100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id),
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
                100.0 * func.sum(case((LogEntry.status == 'error', 1), else_=0)) / func.count(LogEntry.log_id),
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
            # Handle SQLite returning string vs PostgreSQL returning date object
            date_str = row.date if isinstance(row.date, str) else (row.date.isoformat() if row.date else None)
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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # current_user: dict = Depends(require_admin_async)
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
