"""
Logging API Endpoints

Log submission, error reporting, and analytics.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from server.api.schemas import (
    LogSubmission, LogResponse, ErrorReport, ErrorResponse
)
from server.database.models import LogEntry, ErrorLog, User
from server.utils.dependencies import get_db, get_current_active_user


# Create router
router = APIRouter(prefix="/logs", tags=["Logging"])


# ============================================================================
# Log Submission Endpoints
# ============================================================================

@router.post("/submit", response_model=LogResponse)
def submit_logs(
    submission: LogSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Submit usage logs from client.

    Accepts batch submissions of multiple log entries.
    """
    try:
        logs_created = 0

        for log_data in submission.logs:
            # Get user ID from username
            user = db.query(User).filter(User.username == log_data.username).first()
            if not user:
                logger.warning(f"Log submitted for non-existent user: {log_data.username}")
                # Create log entry with None user_id for unknown users
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

        db.commit()

        logger.info(f"Received {logs_created} log entries from user {current_user['username']}")

        return LogResponse(
            success=True,
            logs_received=logs_created,
            message=f"Successfully logged {logs_created} entries"
        )

    except Exception as e:
        db.rollback()
        logger.exception(f"Error submitting logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save logs: {str(e)}"
        )


@router.post("/error", response_model=ErrorResponse)
def submit_error_report(
    error: ErrorReport,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Submit error report from client.

    Records detailed error information for debugging.
    """
    try:
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
        db.commit()
        db.refresh(error_log)

        logger.error(
            f"Error reported by {current_user['username']}: "
            f"{error.error_type} in {error.tool_name}.{error.function_name}"
        )

        return ErrorResponse(
            success=True,
            error_id=error_log.error_id,
            message="Error report received"
        )

    except Exception as e:
        db.rollback()
        logger.exception(f"Error saving error report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save error report: {str(e)}"
        )


# ============================================================================
# Log Retrieval Endpoints (Admin)
# ============================================================================

@router.get("/recent")
def get_recent_logs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
    limit: int = 100,
    tool_name: str = None
):
    """
    Get recent log entries.

    Users can see their own logs. Admins can see all logs.
    """
    query = db.query(LogEntry)

    # Non-admins can only see their own logs
    if current_user["role"] not in ["admin", "superadmin"]:
        query = query.filter(LogEntry.user_id == current_user["user_id"])

    # Filter by tool if specified
    if tool_name:
        query = query.filter(LogEntry.tool_name == tool_name)

    # Order by timestamp descending and limit
    logs = query.order_by(LogEntry.timestamp.desc()).limit(limit).all()

    return logs


@router.get("/errors")
def get_recent_errors(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
    limit: int = 50
):
    """
    Get recent error logs (admin only).
    """
    if current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    errors = db.query(ErrorLog).order_by(ErrorLog.timestamp.desc()).limit(limit).all()

    return errors


@router.get("/user/{user_id}")
def get_user_logs(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
    limit: int = 100
):
    """
    Get logs for a specific user.

    Users can see their own logs. Admins can see any user's logs.
    """
    # Check permission
    if current_user["user_id"] != user_id and current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' logs"
        )

    logs = db.query(LogEntry).filter(
        LogEntry.user_id == user_id
    ).order_by(
        LogEntry.timestamp.desc()
    ).limit(limit).all()

    return logs


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/summary")
def get_log_stats_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get summary statistics of log entries.

    Admins see global stats. Users see their own stats.
    """
    from sqlalchemy import func

    if current_user["role"] in ["admin", "superadmin"]:
        # Global stats for admins
        query = db.query(LogEntry)
    else:
        # User's own stats
        query = db.query(LogEntry).filter(LogEntry.user_id == current_user["user_id"])

    total_logs = query.count()
    success_logs = query.filter(LogEntry.status == "success").count()
    error_logs = query.filter(LogEntry.status == "error").count()

    # Average duration
    avg_duration = query.with_entities(
        func.avg(LogEntry.duration_seconds)
    ).scalar() or 0.0

    # Most used tool
    most_used_tool = db.query(
        LogEntry.tool_name,
        func.count(LogEntry.log_id).label("count")
    ).group_by(
        LogEntry.tool_name
    ).order_by(
        func.count(LogEntry.log_id).desc()
    ).first()

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
def get_stats_by_tool(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get statistics grouped by tool.
    """
    from sqlalchemy import func

    if current_user["role"] in ["admin", "superadmin"]:
        query = db.query(LogEntry)
    else:
        query = db.query(LogEntry).filter(LogEntry.user_id == current_user["user_id"])

    tool_stats = query.with_entities(
        LogEntry.tool_name,
        func.count(LogEntry.log_id).label("total_uses"),
        func.avg(LogEntry.duration_seconds).label("avg_duration"),
        func.count(func.distinct(LogEntry.user_id)).label("unique_users")
    ).group_by(
        LogEntry.tool_name
    ).all()

    return [
        {
            "tool_name": stat.tool_name,
            "total_uses": stat.total_uses,
            "avg_duration_seconds": round(stat.avg_duration, 2),
            "unique_users": stat.unique_users
        }
        for stat in tool_stats
    ]
