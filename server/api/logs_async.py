"""
Logging API Endpoints (ASYNC)

Log submission, error reporting, and analytics with async/await.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from server.api.schemas import (
    LogSubmission, LogResponse, ErrorReport, ErrorResponse
)
from server.database.models import LogEntry, ErrorLog, User
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.utils.websocket import emit_log_entry, emit_error_report


# Create router
router = APIRouter(prefix="/logs", tags=["Logging"])


# ============================================================================
# Log Submission Endpoints
# ============================================================================

@router.post("/submit", response_model=LogResponse)
async def submit_logs(
    submission: LogSubmission,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Submit usage logs from client (ASYNC).

    Accepts batch submissions of multiple log entries.
    """
    try:
        logs_created = 0

        async with db.begin():
            for log_data in submission.logs:
                # Get user ID from username (async)
                result = await db.execute(
                    select(User).where(User.username == log_data.username)
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"Log submitted for non-existent user: {log_data.username}")
                    user_id = None
                else:
                    user_id = user.user_id

                # Create log entry
                log_entry = LogEntry(
                    user_id=user_id,
                    session_id=submission.session_id,
                    username=log_data.username,
                    machine_id=log_data.machine_id,
                    tool_name=log_data.tool_name,
                    function_name=log_data.function_name,
                    timestamp=datetime.utcnow(),
                    duration_seconds=log_data.duration_seconds,
                    status=log_data.status,
                    error_message=log_data.error_message,
                    file_info=log_data.file_info,
                    parameters=log_data.parameters
                )

                db.add(log_entry)
                logs_created += 1

                # Emit WebSocket event for real-time updates
                await emit_log_entry({
                    'user_id': user_id,
                    'username': log_data.username,
                    'tool_name': log_data.tool_name,
                    'function_name': log_data.function_name,
                    'status': log_data.status,
                    'duration_seconds': log_data.duration_seconds,
                    'timestamp': datetime.utcnow().isoformat()
                })

        logger.info(f"Received {logs_created} log entries from user {current_user['username']}")

        return LogResponse(
            success=True,
            logs_received=logs_created,
            message=f"Successfully logged {logs_created} entries"
        )

    except Exception as e:
        logger.exception(f"Error submitting logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save logs: {str(e)}"
        )


@router.post("/error", response_model=ErrorResponse)
async def submit_error_report(
    error: ErrorReport,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Submit error report from client (ASYNC).

    Records detailed error information for debugging.
    """
    try:
        async with db.begin():
            error_log = ErrorLog(
                timestamp=datetime.utcnow(),
                user_id=current_user["user_id"],
                machine_id=error.machine_id,
                tool_name=error.tool_name,
                function_name=error.function_name,
                error_type=error.error_type,
                error_message=error.error_message,
                stack_trace=error.stack_trace,
                app_version=error.app_version,
                context=error.context
            )

            db.add(error_log)
            await db.flush()  # Flush to get the ID
            error_id = error_log.error_id

        # Emit WebSocket event for real-time error notifications
        await emit_error_report({
            'error_id': error_id,
            'user_id': current_user["user_id"],
            'username': current_user["username"],
            'tool_name': error.tool_name,
            'function_name': error.function_name,
            'error_type': error.error_type,
            'error_message': error.error_message,
            'timestamp': datetime.utcnow().isoformat()
        })

        logger.error(
            f"Error reported by {current_user['username']}: "
            f"{error.error_type} in {error.tool_name}.{error.function_name}"
        )

        return ErrorResponse(
            success=True,
            error_id=error_id,
            message="Error report received"
        )

    except Exception as e:
        logger.exception(f"Error saving error report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save error report: {str(e)}"
        )


# ============================================================================
# Log Retrieval Endpoints (Admin)
# ============================================================================

@router.get("/recent")
async def get_recent_logs(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    limit: int = 100,
    tool_name: str = None
):
    """
    Get recent log entries (ASYNC).

    Users can see their own logs. Admins can see all logs.
    """
    query = select(LogEntry)

    # Non-admins can only see their own logs
    if current_user["role"] not in ["admin", "superadmin"]:
        query = query.where(LogEntry.user_id == current_user["user_id"])

    # Filter by tool if specified
    if tool_name:
        query = query.where(LogEntry.tool_name == tool_name)

    # Order by timestamp descending and limit
    query = query.order_by(LogEntry.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.get("/errors")
async def get_recent_errors(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    limit: int = 50
):
    """
    Get recent error logs (admin only) (ASYNC).
    """
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    query = select(ErrorLog).order_by(ErrorLog.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    errors = result.scalars().all()

    return errors


@router.get("/user/{user_id}")
async def get_user_logs(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    limit: int = 100
):
    """
    Get logs for a specific user (ASYNC).

    Users can see their own logs. Admins can see any user's logs.
    """
    # Check permission
    if current_user["user_id"] != user_id and current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' logs"
        )

    query = select(LogEntry).where(
        LogEntry.user_id == user_id
    ).order_by(
        LogEntry.timestamp.desc()
    ).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/summary")
async def get_log_stats_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get summary statistics of log entries (ASYNC).

    Admins see global stats. Users see their own stats.
    """
    if current_user["role"] in ["admin", "superadmin"]:
        # Global stats for admins
        query = select(LogEntry)
    else:
        # User's own stats
        query = select(LogEntry).where(LogEntry.user_id == current_user["user_id"])

    # Total logs
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_logs = total_result.scalar()

    # Success logs
    success_query = query.where(LogEntry.status == "success")
    success_result = await db.execute(select(func.count()).select_from(success_query.subquery()))
    success_logs = success_result.scalar()

    # Error logs
    error_query = query.where(LogEntry.status == "error")
    error_result = await db.execute(select(func.count()).select_from(error_query.subquery()))
    error_logs = error_result.scalar()

    # Average duration
    avg_query = select(func.avg(LogEntry.duration_seconds)).select_from(query.subquery())
    avg_result = await db.execute(avg_query)
    avg_duration = avg_result.scalar() or 0.0

    # Most used tool
    most_used_query = select(
        LogEntry.tool_name,
        func.count(LogEntry.log_id).label("count")
    ).select_from(query.subquery()).group_by(
        LogEntry.tool_name
    ).order_by(
        func.count(LogEntry.log_id).desc()
    ).limit(1)

    most_used_result = await db.execute(most_used_query)
    most_used_tool = most_used_result.first()

    return {
        "total_operations": total_logs,
        "successful_operations": success_logs,
        "failed_operations": error_logs,
        "success_rate": (success_logs / total_logs * 100) if total_logs > 0 else 0.0,
        "avg_duration_seconds": round(avg_duration, 2),
        "most_used_tool": most_used_tool[0] if most_used_tool else None,
        "most_used_tool_count": most_used_tool[1] if most_used_tool else 0
    }


@router.get("/stats/by-tool")
async def get_stats_by_tool(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get statistics grouped by tool (ASYNC).
    """
    if current_user["role"] in ["admin", "superadmin"]:
        query = select(LogEntry)
    else:
        query = select(LogEntry).where(LogEntry.user_id == current_user["user_id"])

    tool_stats_query = select(
        LogEntry.tool_name,
        func.count(LogEntry.log_id).label("total_uses"),
        func.avg(LogEntry.duration_seconds).label("avg_duration"),
        func.count(func.distinct(LogEntry.user_id)).label("unique_users")
    ).select_from(query.subquery()).group_by(
        LogEntry.tool_name
    )

    result = await db.execute(tool_stats_query)
    tool_stats = result.all()

    return [
        {
            "tool_name": stat.tool_name,
            "total_uses": stat.total_uses,
            "avg_duration_seconds": round(stat.avg_duration, 2),
            "unique_users": stat.unique_users
        }
        for stat in tool_stats
    ]
