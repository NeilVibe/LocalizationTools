"""
Telemetry Service - Admin dashboard telemetry data access.

Extracted from server/api/admin_telemetry.py (Phase 69-72 service extraction).
Follows SyncService pattern: class-based with __init__(db) accepting AsyncSession.

Usage:
    from server.services.telemetry_service import TelemetryService

    svc = TelemetryService(db)
    overview = await svc.get_overview()
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, Integer
from loguru import logger

from server.database.models import Installation, RemoteLog, RemoteSession, TelemetrySummary


class TelemetryService:
    """Service layer for admin telemetry dashboard."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Overview / Summary
    # =========================================================================

    async def get_overview(self) -> Dict[str, Any]:
        """
        Get telemetry overview for dashboard home.

        Returns dict with:
        - active_installations, active_sessions, online_now
        - today_logs, errors_24h
        """
        logger.info("Requesting telemetry overview")

        # Active installations count
        active_installs_result = await self.db.execute(
            select(func.count()).select_from(Installation).where(
                Installation.is_active == True
            )
        )
        active_installations = active_installs_result.scalar() or 0

        # Active sessions (is_active = True)
        active_sessions_result = await self.db.execute(
            select(func.count()).select_from(RemoteSession).where(
                RemoteSession.is_active == True
            )
        )
        active_sessions = active_sessions_result.scalar() or 0

        # Today's logs
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_logs_result = await self.db.execute(
            select(func.count()).select_from(RemoteLog).where(
                RemoteLog.received_at >= today_start
            )
        )
        today_logs = today_logs_result.scalar() or 0

        # Errors/Criticals (24h)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        errors_result = await self.db.execute(
            select(func.count()).select_from(RemoteLog).where(
                and_(
                    RemoteLog.received_at >= twenty_four_hours_ago,
                    RemoteLog.level.in_(['ERROR', 'CRITICAL'])
                )
            )
        )
        errors_24h = errors_result.scalar() or 0

        # Online in last 5 minutes (using last_seen)
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        online_now_result = await self.db.execute(
            select(func.count()).select_from(Installation).where(
                and_(
                    Installation.is_active == True,
                    Installation.last_seen >= five_min_ago
                )
            )
        )
        online_now = online_now_result.scalar() or 0

        return {
            "active_installations": active_installations,
            "active_sessions": active_sessions,
            "online_now": online_now,
            "today_logs": today_logs,
            "errors_24h": errors_24h
        }

    # =========================================================================
    # Installations
    # =========================================================================

    async def get_installations(self, include_inactive: bool = False) -> Dict[str, Any]:
        """
        Get all registered installations with status and activity.

        Returns dict with count and installations list.
        """
        logger.info("Requesting installation list")

        query = select(Installation).order_by(desc(Installation.last_seen))

        if not include_inactive:
            query = query.where(Installation.is_active == True)

        result = await self.db.execute(query)
        installations = result.scalars().all()

        now = datetime.utcnow()
        five_min_ago = now - timedelta(minutes=5)

        installation_list = []
        for inst in installations:
            is_online = inst.last_seen and inst.last_seen >= five_min_ago

            # Get today's session count
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            sessions_result = await self.db.execute(
                select(func.count()).select_from(RemoteSession).where(
                    and_(
                        RemoteSession.installation_id == inst.installation_id,
                        RemoteSession.started_at >= today_start
                    )
                )
            )
            today_sessions = sessions_result.scalar() or 0

            # Get error count (24h)
            twenty_four_hours_ago = now - timedelta(hours=24)
            errors_result = await self.db.execute(
                select(func.count()).select_from(RemoteLog).where(
                    and_(
                        RemoteLog.installation_id == inst.installation_id,
                        RemoteLog.received_at >= twenty_four_hours_ago,
                        RemoteLog.level.in_(['ERROR', 'CRITICAL'])
                    )
                )
            )
            errors_24h = errors_result.scalar() or 0

            installation_list.append({
                "installation_id": inst.installation_id,
                "installation_name": inst.installation_name,
                "version": inst.last_version or inst.version,
                "owner_email": inst.owner_email,
                "is_active": inst.is_active,
                "is_online": is_online,
                "last_seen": inst.last_seen.isoformat() if inst.last_seen else None,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
                "today_sessions": today_sessions,
                "errors_24h": errors_24h
            })

        return {
            "count": len(installation_list),
            "installations": installation_list
        }

    async def get_installation_detail(self, installation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific installation.

        Returns dict with installation detail, or None if not found.
        """
        logger.info(f"Requesting installation detail: {installation_id}")

        result = await self.db.execute(
            select(Installation).where(Installation.installation_id == installation_id)
        )
        inst = result.scalar_one_or_none()

        if not inst:
            return None

        now = datetime.utcnow()
        five_min_ago = now - timedelta(minutes=5)
        is_online = inst.last_seen and inst.last_seen >= five_min_ago

        # Get recent sessions
        sessions_result = await self.db.execute(
            select(RemoteSession).where(
                RemoteSession.installation_id == installation_id
            ).order_by(desc(RemoteSession.started_at)).limit(10)
        )
        recent_sessions = sessions_result.scalars().all()

        # Get log counts by level (last 7 days)
        seven_days_ago = now - timedelta(days=7)
        log_counts_result = await self.db.execute(
            select(
                RemoteLog.level,
                func.count().label('count')
            ).where(
                and_(
                    RemoteLog.installation_id == installation_id,
                    RemoteLog.received_at >= seven_days_ago
                )
            ).group_by(RemoteLog.level)
        )
        log_counts = {row.level: row.count for row in log_counts_result.all()}

        return {
            "installation_id": inst.installation_id,
            "installation_name": inst.installation_name,
            "version": inst.last_version or inst.version,
            "owner_email": inst.owner_email,
            "is_active": inst.is_active,
            "is_online": is_online,
            "last_seen": inst.last_seen.isoformat() if inst.last_seen else None,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
            "extra_data": inst.extra_data,
            "log_counts_7d": log_counts,
            "recent_sessions": [
                {
                    "session_id": s.session_id,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "is_active": s.is_active,
                    "duration_seconds": s.duration_seconds,
                    "app_version": s.app_version,
                    "end_reason": s.end_reason
                }
                for s in recent_sessions
            ]
        }

    # =========================================================================
    # Sessions
    # =========================================================================

    async def get_sessions(
        self,
        active_only: bool = True,
        days: int = 7,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get remote sessions with optional filtering.

        Returns dict with count and sessions list.
        """
        logger.info(f"Requesting sessions (active_only={active_only}, days={days})")

        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(RemoteSession).where(
            RemoteSession.started_at >= start_date
        )

        if active_only:
            query = query.where(RemoteSession.is_active == True)

        query = query.order_by(desc(RemoteSession.started_at)).limit(limit)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        # Enrich with installation names
        session_list = []
        for session in sessions:
            inst_result = await self.db.execute(
                select(Installation.installation_name).where(
                    Installation.installation_id == session.installation_id
                )
            )
            inst_name = inst_result.scalar() or "Unknown"

            session_list.append({
                "session_id": session.session_id,
                "installation_id": session.installation_id,
                "installation_name": inst_name,
                "app_version": session.app_version,
                "ip_address": session.ip_address,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "last_heartbeat": session.last_heartbeat.isoformat() if session.last_heartbeat else None,
                "is_active": session.is_active,
                "duration_seconds": session.duration_seconds,
                "end_reason": session.end_reason
            })

        return {
            "count": len(session_list),
            "sessions": session_list
        }

    # =========================================================================
    # Logs
    # =========================================================================

    async def get_remote_logs(
        self,
        installation_id: Optional[str] = None,
        level: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get remote logs with filtering options.

        Returns dict with count and logs list.
        """
        logger.info(f"Requesting remote logs (installation={installation_id}, level={level})")

        start_date = datetime.utcnow() - timedelta(hours=hours)

        query = select(RemoteLog).where(
            RemoteLog.received_at >= start_date
        )

        if installation_id:
            query = query.where(RemoteLog.installation_id == installation_id)

        if level:
            query = query.where(RemoteLog.level == level.upper())

        query = query.order_by(desc(RemoteLog.received_at)).limit(limit)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        log_list = []
        for log in logs:
            inst_result = await self.db.execute(
                select(Installation.installation_name).where(
                    Installation.installation_id == log.installation_id
                )
            )
            inst_name = inst_result.scalar() or "Unknown"

            log_list.append({
                "log_id": log.log_id,
                "installation_id": log.installation_id,
                "installation_name": inst_name,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "received_at": log.received_at.isoformat() if log.received_at else None,
                "level": log.level,
                "message": log.message,
                "component": log.component,
                "source": log.source,
                "data": log.data
            })

        return {
            "count": len(log_list),
            "logs": log_list
        }

    async def get_error_logs(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get error and critical logs only.

        Returns dict with count and logs list.
        """
        logger.info(f"Requesting error logs (hours={hours})")

        start_date = datetime.utcnow() - timedelta(hours=hours)

        query = select(RemoteLog).where(
            and_(
                RemoteLog.received_at >= start_date,
                RemoteLog.level.in_(['ERROR', 'CRITICAL'])
            )
        ).order_by(desc(RemoteLog.received_at)).limit(limit)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        log_list = []
        for log in logs:
            inst_result = await self.db.execute(
                select(Installation.installation_name).where(
                    Installation.installation_id == log.installation_id
                )
            )
            inst_name = inst_result.scalar() or "Unknown"

            log_list.append({
                "log_id": log.log_id,
                "installation_id": log.installation_id,
                "installation_name": inst_name,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "received_at": log.received_at.isoformat() if log.received_at else None,
                "level": log.level,
                "message": log.message,
                "component": log.component,
                "source": log.source,
                "data": log.data
            })

        return {
            "count": len(log_list),
            "logs": log_list
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_daily_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get daily telemetry statistics.

        Returns per-day breakdown of log counts, session counts, active installations.
        """
        logger.info(f"Requesting daily telemetry stats for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(TelemetrySummary).where(
                TelemetrySummary.date >= start_date
            ).order_by(TelemetrySummary.date)
        )
        summaries = result.scalars().all()

        # Aggregate by date
        daily_data: Dict[str, Dict[str, Any]] = {}
        for summary in summaries:
            date_str = summary.date.strftime('%Y-%m-%d')
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "info_count": 0,
                    "success_count": 0,
                    "warning_count": 0,
                    "error_count": 0,
                    "critical_count": 0,
                    "total_sessions": 0,
                    "installations": set()
                }

            daily_data[date_str]["info_count"] += summary.info_count or 0
            daily_data[date_str]["success_count"] += summary.success_count or 0
            daily_data[date_str]["warning_count"] += summary.warning_count or 0
            daily_data[date_str]["error_count"] += summary.error_count or 0
            daily_data[date_str]["critical_count"] += summary.critical_count or 0
            daily_data[date_str]["total_sessions"] += summary.total_sessions or 0
            daily_data[date_str]["installations"].add(summary.installation_id)

        # Convert to list and count installations
        stats_list = []
        for date_str, data in sorted(daily_data.items()):
            stats_list.append({
                "date": data["date"],
                "info_count": data["info_count"],
                "success_count": data["success_count"],
                "warning_count": data["warning_count"],
                "error_count": data["error_count"],
                "critical_count": data["critical_count"],
                "total_sessions": data["total_sessions"],
                "active_installations": len(data["installations"])
            })

        return {
            "period": f"last_{days}_days",
            "data": stats_list
        }

    async def get_stats_by_installation(self, days: int = 30) -> Dict[str, Any]:
        """
        Get aggregated statistics per installation.

        Returns per-installation breakdown of logs, errors, sessions, duration.
        """
        logger.info(f"Requesting stats by installation for {days} days")

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all active installations
        installs_result = await self.db.execute(
            select(Installation).where(Installation.is_active == True)
        )
        installations = installs_result.scalars().all()

        stats_list = []
        for inst in installations:
            # Get log counts
            log_result = await self.db.execute(
                select(
                    func.count().label('total_logs'),
                    func.sum(func.cast(RemoteLog.level == 'ERROR', Integer)).label('errors'),
                    func.sum(func.cast(RemoteLog.level == 'CRITICAL', Integer)).label('criticals')
                ).where(
                    and_(
                        RemoteLog.installation_id == inst.installation_id,
                        RemoteLog.received_at >= start_date
                    )
                )
            )
            log_counts = log_result.first()

            # Get session counts
            session_result = await self.db.execute(
                select(
                    func.count().label('total_sessions'),
                    func.sum(RemoteSession.duration_seconds).label('total_duration')
                ).where(
                    and_(
                        RemoteSession.installation_id == inst.installation_id,
                        RemoteSession.started_at >= start_date
                    )
                )
            )
            session_counts = session_result.first()

            stats_list.append({
                "installation_id": inst.installation_id,
                "installation_name": inst.installation_name,
                "version": inst.last_version or inst.version,
                "total_logs": log_counts.total_logs or 0,
                "errors": log_counts.errors or 0,
                "criticals": log_counts.criticals or 0,
                "total_sessions": session_counts.total_sessions or 0,
                "total_duration_hours": round((session_counts.total_duration or 0) / 3600, 2)
            })

        # Sort by total logs descending
        stats_list.sort(key=lambda x: x["total_logs"], reverse=True)

        return {
            "period": f"last_{days}_days",
            "installations": stats_list
        }
