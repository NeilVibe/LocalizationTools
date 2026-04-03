"""
Activity Feed API — Provides recent activity for the Admin Dashboard.

Phase 111: Exposes ldm_edit_history + log_entries as a unified activity feed
so the dashboard can show ALL user activity (row edits, tool operations, etc.)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import get_async_db, require_admin_async

router = APIRouter(prefix="/api/v2/activity", tags=["activity"])


@router.get("/recent")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=500),
    hours: int = Query(24, ge=1, le=168),
    _admin: dict = Depends(require_admin_async),
    db: AsyncSession = Depends(get_async_db),
):
    """Get recent activity across all users — row edits + tool operations.

    Combines ldm_edit_history (row edits) and log_entries (tool operations)
    into a single chronological feed for the admin dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    activities = []

    # 1. Row edits from ldm_edit_history
    try:
        result = await db.execute(text("""
            SELECT h.id, h.row_id, h.user_id, h.old_status, h.new_status,
                   h.edited_at, u.username,
                   r.string_id, r.source, f.name as file_name
            FROM ldm_edit_history h
            LEFT JOIN users u ON h.user_id = u.user_id
            LEFT JOIN ldm_rows r ON h.row_id = r.id
            LEFT JOIN ldm_files f ON r.file_id = f.id
            WHERE h.edited_at >= :since
            ORDER BY h.edited_at DESC
            LIMIT :limit
        """), {"since": since, "limit": limit})
        rows = result.mappings().all()

        for row in rows:
            action = "confirmed" if row["new_status"] == "reviewed" else "edited"
            activities.append({
                "type": "row_edit",
                "action": action,
                "timestamp": row["edited_at"].isoformat() if row["edited_at"] else None,
                "user": row["username"] or "Unknown",
                "user_id": row["user_id"],
                "details": {
                    "row_id": row["row_id"],
                    "string_id": row["string_id"],
                    "file_name": row["file_name"],
                    "old_status": row["old_status"],
                    "new_status": row["new_status"],
                },
            })
    except Exception as e:
        logger.warning(f"[Activity] Failed to fetch edit history: {e}")

    # 2. Tool operations from log_entries
    try:
        result = await db.execute(text("""
            SELECT l.id, l.user_id, l.tool_name, l.function_name,
                   l.timestamp_start, l.status, l.file_name, l.rows_processed,
                   u.username
            FROM log_entries l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE l.timestamp_start >= :since
            ORDER BY l.timestamp_start DESC
            LIMIT :limit
        """), {"since": since, "limit": limit})
        rows = result.mappings().all()

        for row in rows:
            activities.append({
                "type": "tool_operation",
                "action": row["function_name"],
                "timestamp": row["timestamp_start"].isoformat() if row["timestamp_start"] else None,
                "user": row["username"] or "Unknown",
                "user_id": row["user_id"],
                "details": {
                    "tool": row["tool_name"],
                    "function": row["function_name"],
                    "status": row["status"],
                    "file_name": row["file_name"],
                    "rows_processed": row["rows_processed"],
                },
            })
    except Exception as e:
        logger.warning(f"[Activity] Failed to fetch log entries: {e}")

    # Sort combined list by timestamp (newest first)
    activities.sort(key=lambda a: a["timestamp"] or "", reverse=True)

    return {
        "activities": activities[:limit],
        "total": len(activities),
        "since": since.isoformat(),
    }


@router.get("/stats")
async def get_activity_stats(
    hours: int = Query(24, ge=1, le=168),
    _admin: dict = Depends(require_admin_async),
    db: AsyncSession = Depends(get_async_db),
):
    """Get activity statistics for the dashboard overview cards."""
    since = datetime.utcnow() - timedelta(hours=hours)

    stats = {
        "rows_edited": 0,
        "rows_confirmed": 0,
        "active_users": 0,
        "tool_operations": 0,
    }

    try:
        # Row edit counts
        result = await db.execute(text("""
            SELECT
                COUNT(*) as total_edits,
                COUNT(*) FILTER (WHERE new_status = 'reviewed') as confirmed
            FROM ldm_edit_history
            WHERE edited_at >= :since
        """), {"since": since})
        row = result.mappings().first()
        if row:
            stats["rows_edited"] = row["total_edits"]
            stats["rows_confirmed"] = row["confirmed"]

        # Active users (distinct users who edited)
        result = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id) as active_users
            FROM ldm_edit_history
            WHERE edited_at >= :since AND user_id IS NOT NULL
        """), {"since": since})
        row = result.mappings().first()
        if row:
            stats["active_users"] = row["active_users"]

        # Tool operations
        result = await db.execute(text("""
            SELECT COUNT(*) as ops
            FROM log_entries
            WHERE timestamp_start >= :since
        """), {"since": since})
        row = result.mappings().first()
        if row:
            stats["tool_operations"] = row["ops"]

    except Exception as e:
        logger.warning(f"[Activity] Failed to fetch stats: {e}")

    return stats
