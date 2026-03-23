"""
Stats Service - Business logic for admin dashboard statistics.

Extracted from server/api/stats.py to follow the service layer pattern
established by SyncService. Route handlers become thin wrappers.

Usage:
    from server.services.stats_service import StatsService

    service = StatsService(db)
    overview = await service.get_overview()
"""

from __future__ import annotations

import os
import platform
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, desc, text, cast
from sqlalchemy.types import Numeric
from loguru import logger

from server.database.models import User as UserModel, Session, LogEntry, ErrorLog


class StatsService:
    """Service layer for admin dashboard statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Overview / Real-time Metrics
    # =========================================================================

    async def get_overview(self) -> Dict[str, Any]:
        """Get real-time overview metrics for dashboard home page."""
        logger.info("Requesting overview stats")

        # Active users (last 30 minutes)
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        active_users_query = select(func.count(func.distinct(Session.user_id))).where(
            and_(
                Session.is_active == True,
                Session.last_activity >= thirty_min_ago
            )
        )
        active_users_result = await self.db.execute(active_users_query)
        active_users = active_users_result.scalar() or 0

        # Today's operations
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_ops_query = select(func.count(LogEntry.log_id)).where(
            LogEntry.timestamp >= today_start
        )
        today_ops_result = await self.db.execute(today_ops_query)
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
        success_rate_result = await self.db.execute(success_rate_query)
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
        avg_duration_result = await self.db.execute(avg_duration_query)
        avg_duration = avg_duration_result.scalar() or 0.0

        return {
            "active_users": active_users,
            "today_operations": today_operations,
            "success_rate": float(success_rate),
            "avg_duration_seconds": round(float(avg_duration), 2)
        }

    # =========================================================================
    # Daily Statistics
    # =========================================================================

    async def get_daily_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get daily usage statistics for the specified number of days."""
        logger.info(f"Requesting daily stats for {days} days")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        query = select(
            func.date(LogEntry.timestamp).label('date'),
            func.count(LogEntry.log_id).label('operations'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(
                case((LogEntry.status == 'success', 1), else_=0)
            ).label('successful_ops'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            func.date(LogEntry.timestamp)
        ).order_by(
            func.date(LogEntry.timestamp)
        )

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Weekly Statistics
    # =========================================================================

    async def get_weekly_stats(self, weeks: int = 12) -> Dict[str, Any]:
        """Get weekly aggregated statistics."""
        logger.info(f"Requesting weekly stats for {weeks} weeks")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks)

        week_col = func.to_char(LogEntry.timestamp, 'IYYY-IW')
        query = select(
            week_col.label('week_start'),
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
            week_col
        ).order_by(
            week_col.desc()
        )

        result = await self.db.execute(query)
        rows = result.all()

        weekly_stats = []
        for row in rows:
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

    # =========================================================================
    # Monthly Statistics
    # =========================================================================

    async def get_monthly_stats(self, months: int = 12) -> Dict[str, Any]:
        """Get monthly aggregated statistics."""
        logger.info(f"Requesting monthly stats for {months} months")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)

        month_col = func.to_char(LogEntry.timestamp, 'YYYY-MM')
        query = select(
            month_col.label('month'),
            func.count(LogEntry.log_id).label('total_ops'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(
                case((LogEntry.status == 'success', 1), else_=0)
            ).label('successful_ops'),
            func.sum(
                case((LogEntry.status == 'error', 1), else_=0)
            ).label('failed_ops'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            month_col
        ).order_by(
            month_col.desc()
        )

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Tool Popularity
    # =========================================================================

    async def get_tool_popularity(self, days: int = 30) -> Dict[str, Any]:
        """Get tool popularity statistics."""
        logger.info(f"Requesting tool popularity for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Total operations count for percentage calculation
        total_ops_query = select(func.count(LogEntry.log_id)).where(
            LogEntry.timestamp >= start_date
        )
        total_ops_result = await self.db.execute(total_ops_query)
        total_ops = total_ops_result.scalar() or 1

        query = select(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration')
        ).where(
            LogEntry.timestamp >= start_date
        ).group_by(
            LogEntry.tool_name
        ).order_by(
            func.count(LogEntry.log_id).desc()
        )

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Function-Level Statistics
    # =========================================================================

    async def get_function_stats(self, tool_name: str, days: int = 30) -> Dict[str, Any]:
        """Get function-level statistics for a specific tool."""
        logger.info(f"Requesting function stats for {tool_name}")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Total operations for this tool
        total_tool_ops_query = select(func.count(LogEntry.log_id)).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.tool_name == tool_name
            )
        )
        total_tool_ops_result = await self.db.execute(total_tool_ops_query)
        total_tool_ops = total_tool_ops_result.scalar() or 1

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

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Performance Metrics
    # =========================================================================

    async def get_fastest_functions(self, limit: int = 10, days: int = 30, min_usage: int = 10) -> Dict[str, Any]:
        """Get fastest functions by average duration."""
        logger.info(f"Requesting top {limit} fastest functions")

        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(cast(func.min(LogEntry.duration_seconds), Numeric), 2).label('min_duration'),
            func.round(cast(func.max(LogEntry.duration_seconds), Numeric), 2).label('max_duration')
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

        result = await self.db.execute(query)
        rows = result.all()

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

    async def get_slowest_functions(self, limit: int = 10, days: int = 30, min_usage: int = 10) -> Dict[str, Any]:
        """Get slowest functions by average duration."""
        logger.info(f"Requesting top {limit} slowest functions")

        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(cast(func.min(LogEntry.duration_seconds), Numeric), 2).label('min_duration'),
            func.round(cast(func.max(LogEntry.duration_seconds), Numeric), 2).label('max_duration')
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

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Error Tracking
    # =========================================================================

    async def get_error_rate(self, days: int = 30) -> Dict[str, Any]:
        """Get error rate over time."""
        logger.info(f"Requesting error rate for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

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

        result = await self.db.execute(query)
        rows = result.all()

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

    async def get_top_errors(self, limit: int = 10, days: int = 30) -> Dict[str, Any]:
        """Get most common errors."""
        logger.info(f"Requesting top {limit} errors")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Total error count for percentage calculation
        total_errors_query = select(func.count(LogEntry.log_id)).where(
            and_(
                LogEntry.timestamp >= start_date,
                LogEntry.status == 'error'
            )
        )
        total_errors_result = await self.db.execute(total_errors_query)
        total_errors = total_errors_result.scalar() or 1

        query = select(
            LogEntry.error_message,
            func.count(LogEntry.log_id).label('error_count'),
            func.count(func.distinct(LogEntry.user_id)).label('affected_users'),
            LogEntry.tool_name
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

        result = await self.db.execute(query)
        rows = result.all()

        top_errors = []
        for row in rows:
            error_count = int(row.error_count)
            pct_of_errors = round(100.0 * error_count / total_errors, 2)
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

    # =========================================================================
    # Team & Language Analytics
    # =========================================================================

    async def get_stats_by_team(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics grouped by team."""
        logger.info(f"Requesting team analytics for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

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

        result = await self.db.execute(query)
        rows = result.all()

        # Get most used tool per team
        team_tools: Dict[str, Optional[str]] = {}
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
                tool_result = await self.db.execute(tool_query)
                tool_row = tool_result.first()
                team_tools[row.team] = tool_row.tool_name if tool_row else None

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

    async def get_stats_by_language(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics grouped by user's primary language."""
        logger.info(f"Requesting language analytics for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

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

        result = await self.db.execute(query)
        rows = result.all()

        # Get most used tool per language
        lang_tools: Dict[str, Optional[str]] = {}
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
                tool_result = await self.db.execute(tool_query)
                tool_row = tool_result.first()
                lang_tools[row.language] = tool_row.tool_name if tool_row else None

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

    # =========================================================================
    # User Rankings (analytics endpoint)
    # =========================================================================

    async def get_user_rankings(self, days: int = 30, limit: int = 20) -> Dict[str, Any]:
        """Get top users by activity with profile info."""
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

        result = await self.db.execute(query)
        rows = result.all()

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

    # =========================================================================
    # Server Logs
    # =========================================================================

    async def get_server_logs(self, lines: int = 100) -> Dict[str, Any]:
        """Get server log file contents (last N lines). No DB needed."""
        logger.info(f"Requesting last {lines} server log lines")

        log_file = Path(__file__).parent.parent / "data" / "logs" / "server.log"

        if not log_file.exists():
            logger.warning(f"Server log file not found: {log_file}")
            return {
                "logs": [],
                "total_lines": 0,
                "message": "Server log file not found"
            }

        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        logs = []
        for line in last_lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split('|', 2)
            if len(parts) >= 3:
                timestamp = parts[0].strip()
                level = parts[1].strip()
                message = parts[2].strip()

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

    # =========================================================================
    # Database Monitoring
    # =========================================================================

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics (PostgreSQL)."""
        logger.info("Requesting database statistics")

        # Get PostgreSQL version
        version_result = await self.db.execute(text("SELECT version()"))
        pg_version = version_result.scalar()

        # Get database size
        size_result = await self.db.execute(text(
            "SELECT pg_database_size(current_database())"
        ))
        size_bytes = size_result.scalar() or 0

        # Get all tables in public schema
        tables_result = await self.db.execute(text("""
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
            columns_result = await self.db.execute(text("""
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
            indexes_result = await self.db.execute(text("""
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
        idx_count_result = await self.db.execute(text("""
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

    # =========================================================================
    # Server Monitoring
    # =========================================================================

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics (CPU, memory, disk, network)."""
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
            cpu_info = {"cores": os.cpu_count() or 1, "percent": 0, "load_avg": [0, 0, 0]}
            memory_info = {"total": 0, "available": 0, "used": 0, "percent": 0}
            disk_info = {"total": 0, "used": 0, "free": 0, "percent": 0}
            network_info = {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0, "connections": 0}
            uptime_seconds = 0

        # Get active sessions count from database
        try:
            active_sessions_result = await self.db.execute(
                select(func.count(Session.session_id)).where(Session.is_active == True)
            )
            active_sessions = active_sessions_result.scalar() or 0
        except Exception:
            active_sessions = 0

        api_info = {
            "port": 8888,
            "active_sessions": active_sessions,
            "websocket_clients": 0,
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
