"""
Rankings Service - Business logic for admin dashboard rankings/leaderboards.

Extracted from server/api/rankings.py to follow the service layer pattern
established by SyncService. Route handlers become thin wrappers.

Usage:
    from server.services.rankings_service import RankingsService

    service = RankingsService(db)
    rankings = await service.get_user_rankings("monthly", 20)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, desc, text, cast
from sqlalchemy.types import Numeric
from loguru import logger

from server.database.models import User as UserModel, LogEntry


class RankingsService:
    """Service layer for admin dashboard rankings and leaderboards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _get_start_date(period: str) -> datetime:
        """Calculate start date from period string."""
        end_date = datetime.utcnow()
        if period == "daily":
            return end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            return end_date - timedelta(days=7)
        elif period == "monthly":
            return end_date - timedelta(days=30)
        else:  # all_time
            return datetime(2000, 1, 1)

    @staticmethod
    def _format_time(total_seconds: float) -> str:
        """Format seconds into 'Xh Ym' string."""
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    # =========================================================================
    # User Rankings
    # =========================================================================

    async def get_user_rankings(self, period: str = "monthly", limit: int = 20) -> Dict[str, Any]:
        """Get user rankings by operations count."""
        logger.info(f"Requesting user rankings for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

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

        result = await self.db.execute(query)
        rows = result.all()

        user_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)

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

            top_tool_result = await self.db.execute(top_tool_query)
            top_tool_row = top_tool_result.first()
            top_tool = top_tool_row.tool_name if top_tool_row else "N/A"

            user_rankings.append({
                "rank": idx,
                "username": row.username,
                "display_name": row.full_name or row.username,
                "total_operations": int(row.total_operations),
                "time_spent": self._format_time(total_seconds),
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

    async def get_user_rankings_by_time(self, period: str = "monthly", limit: int = 20) -> Dict[str, Any]:
        """Get user rankings by total processing time spent."""
        logger.info(f"Requesting user rankings by time for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

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

        result = await self.db.execute(query)
        rows = result.all()

        user_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)

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

            top_tool_result = await self.db.execute(top_tool_query)
            top_tool_row = top_tool_result.first()
            top_tool = top_tool_row.tool_name if top_tool_row else "N/A"

            user_rankings.append({
                "rank": idx,
                "username": row.username,
                "display_name": row.full_name or row.username,
                "total_operations": int(row.total_operations),
                "time_spent": self._format_time(total_seconds),
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

    # =========================================================================
    # App Rankings
    # =========================================================================

    async def get_app_rankings(self, period: str = "monthly") -> Dict[str, Any]:
        """Get app/tool rankings by usage."""
        logger.info(f"Requesting app rankings for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

        query = select(
            LogEntry.tool_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.count(func.distinct(LogEntry.user_id)).label('unique_users'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
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

        app_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)

            app_rankings.append({
                "rank": idx,
                "app_name": row.tool_name,
                "usage_count": int(row.usage_count),
                "unique_users": int(row.unique_users),
                "total_time": self._format_time(total_seconds),
                "total_time_seconds": int(total_seconds),
                "avg_duration": float(row.avg_duration or 0)
            })

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "rankings": app_rankings
        }

    # =========================================================================
    # Function Rankings
    # =========================================================================

    async def get_function_rankings(
        self, period: str = "monthly", limit: int = 20, tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get function rankings by usage."""
        logger.info(f"Requesting function rankings for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

        conditions = [LogEntry.timestamp >= start_date]
        if tool_name:
            conditions.append(LogEntry.tool_name == tool_name)

        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
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

        result = await self.db.execute(query)
        rows = result.all()

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

    async def get_function_rankings_by_time(
        self, period: str = "monthly", limit: int = 20, tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get function rankings by total processing time."""
        logger.info(f"Requesting function rankings by time for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

        conditions = [LogEntry.timestamp >= start_date]
        if tool_name:
            conditions.append(LogEntry.tool_name == tool_name)

        query = select(
            LogEntry.tool_name,
            LogEntry.function_name,
            func.count(LogEntry.log_id).label('usage_count'),
            func.sum(LogEntry.duration_seconds).label('total_time_seconds'),
            func.round(cast(func.avg(LogEntry.duration_seconds), Numeric), 2).label('avg_duration'),
            func.round(
                cast(100.0 * func.sum(case((LogEntry.status == 'success', 1), else_=0)) / func.count(LogEntry.log_id), Numeric),
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

        result = await self.db.execute(query)
        rows = result.all()

        function_rankings = []
        for idx, row in enumerate(rows, 1):
            total_seconds = float(row.total_time_seconds or 0)

            function_rankings.append({
                "rank": idx,
                "tool_name": row.tool_name,
                "function_name": row.function_name,
                "usage_count": int(row.usage_count),
                "total_time": self._format_time(total_seconds),
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

    # =========================================================================
    # Combined Top Rankings
    # =========================================================================

    async def get_top_rankings(self, period: str = "monthly") -> Dict[str, Any]:
        """Get combined top rankings in one call (top users, apps, functions)."""
        logger.info(f"Requesting combined top rankings for period: {period}")

        start_date = self._get_start_date(period)
        end_date = datetime.utcnow()

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

        users_result = await self.db.execute(users_query)
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

        apps_result = await self.db.execute(apps_query)
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

        functions_result = await self.db.execute(functions_query)
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
