"""
Remote Logging Service - Business logic for remote log collection.

Extracted from server/api/remote_logging.py (Phase 69-72 service extraction).
Follows SyncService pattern: class-based with __init__(db) accepting AsyncSession.

Usage:
    from server.services.remote_logging_service import RemoteLoggingService

    svc = RemoteLoggingService(db)
    result = await svc.register_installation("MyApp", "1.0.0")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer
from loguru import logger

from server.database.models import Installation, RemoteLog, RemoteSession, TelemetrySummary


class RemoteLoggingService:
    """Service layer for remote log collection and session tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Registration
    # =========================================================================

    async def register_installation(
        self,
        name: str,
        version: str,
        api_key_hash: str,
        owner_email: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Register new installation and return its details.

        The caller is responsible for generating the API key and passing the hash.

        Returns dict with installation_id (the generated ID).
        """
        logger.info("New installation registration request", {
            "installation_name": name,
            "version": version,
            "owner_email": owner_email
        })

        installation_id = secrets.token_urlsafe(16)

        installation = Installation(
            installation_id=installation_id,
            api_key_hash=api_key_hash,
            installation_name=name,
            version=version,
            owner_email=owner_email,
            last_version=version,
            extra_data=metadata,
            is_active=True
        )

        self.db.add(installation)
        await self.db.commit()

        logger.success("Installation registered successfully", {
            "installation_id": installation_id,
            "installation_name": name
        })

        return {
            "installation_id": installation_id,
        }

    # =========================================================================
    # Log Submission
    # =========================================================================

    async def submit_logs(
        self,
        installation: Installation,
        batch_logs: list,
        batch_installation_id: str,
        batch_installation_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a batch of log entries and update telemetry summary.

        Args:
            installation: Verified Installation model instance.
            batch_logs: List of log entry dicts with keys:
                timestamp, level, message, data, source, component.
            batch_installation_id: Installation ID from the batch payload.
            batch_installation_name: Optional name from the batch payload.

        Returns dict with logs_received, errors_detected, criticals_detected.
        """
        logger.info("Remote log batch received", {
            "installation_id": batch_installation_id,
            "log_count": len(batch_logs),
            "installation_name": batch_installation_name
        })

        # Counters for telemetry summary
        level_counts = {
            "INFO": 0,
            "SUCCESS": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0
        }

        for log_entry in batch_logs:
            level = log_entry.get("level", "INFO")
            if level in level_counts:
                level_counts[level] += 1

            # Parse timestamp
            try:
                log_timestamp = datetime.fromisoformat(
                    log_entry.get("timestamp", "").replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                log_timestamp = datetime.utcnow()

            remote_log = RemoteLog(
                installation_id=installation.installation_id,
                timestamp=log_timestamp,
                level=level,
                message=log_entry.get("message", ""),
                data=log_entry.get("data"),
                source=log_entry.get("source"),
                component=log_entry.get("component")
            )
            self.db.add(remote_log)

            # Log errors and criticals to server logs for alerting
            if level in ["ERROR", "CRITICAL"]:
                logger.error(f"Remote [{batch_installation_id}] {log_entry.get('message', '')}", {
                    "installation_id": batch_installation_id,
                    "source": log_entry.get("source"),
                    "component": log_entry.get("component"),
                    "data": log_entry.get("data"),
                    "timestamp": log_entry.get("timestamp")
                })

        await self.db.commit()

        # Update or create today's telemetry summary
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(TelemetrySummary).where(
                and_(
                    TelemetrySummary.installation_id == installation.installation_id,
                    TelemetrySummary.date == today
                )
            )
        )
        summary = result.scalar_one_or_none()

        if summary:
            summary.info_count += level_counts["INFO"]
            summary.success_count += level_counts["SUCCESS"]
            summary.warning_count += level_counts["WARNING"]
            summary.error_count += level_counts["ERROR"]
            summary.critical_count += level_counts["CRITICAL"]
        else:
            summary = TelemetrySummary(
                date=today,
                installation_id=installation.installation_id,
                info_count=level_counts["INFO"],
                success_count=level_counts["SUCCESS"],
                warning_count=level_counts["WARNING"],
                error_count=level_counts["ERROR"],
                critical_count=level_counts["CRITICAL"]
            )
            self.db.add(summary)

        await self.db.commit()

        logger.success("Remote log batch processed", {
            "installation_id": batch_installation_id,
            "logs_processed": len(batch_logs),
            "errors": level_counts["ERROR"],
            "criticals": level_counts["CRITICAL"]
        })

        # Alert on criticals
        if level_counts["CRITICAL"] > 0:
            logger.critical("Critical errors detected from remote installation", {
                "installation_id": batch_installation_id,
                "installation_name": batch_installation_name,
                "critical_count": level_counts["CRITICAL"]
            })

        return {
            "logs_received": len(batch_logs),
            "errors_detected": level_counts["ERROR"],
            "criticals_detected": level_counts["CRITICAL"],
        }

    # =========================================================================
    # Session Tracking
    # =========================================================================

    async def start_session(
        self,
        installation: Installation,
        version: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new remote session.

        Returns dict with session_id and started_at.
        """
        session = RemoteSession(
            installation_id=installation.installation_id,
            app_version=version,
            ip_address=ip_address,
            is_active=True
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info("Remote session started", {
            "session_id": session.session_id,
            "installation_id": installation.installation_id,
            "version": version
        })

        return {
            "session_id": session.session_id,
            "started_at": session.started_at.isoformat()
        }

    async def heartbeat(
        self,
        session_id: str,
        installation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Update session heartbeat.

        Returns dict with last_heartbeat, or None if session not found.
        """
        result = await self.db.execute(
            select(RemoteSession).where(
                and_(
                    RemoteSession.session_id == session_id,
                    RemoteSession.installation_id == installation_id,
                    RemoteSession.is_active == True
                )
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        session.last_heartbeat = datetime.utcnow()
        await self.db.commit()

        return {"last_heartbeat": session.last_heartbeat.isoformat()}

    async def end_session(
        self,
        session_id: str,
        installation_id: str,
        end_reason: str = "user_closed",
    ) -> Optional[Dict[str, Any]]:
        """
        End a session and update telemetry summary.

        Returns dict with session_id and duration_seconds, or None if not found.
        """
        result = await self.db.execute(
            select(RemoteSession).where(
                and_(
                    RemoteSession.session_id == session_id,
                    RemoteSession.installation_id == installation_id
                )
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        session.ended_at = datetime.utcnow()
        session.is_active = False
        session.end_reason = end_reason
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

        await self.db.commit()

        # Update today's telemetry summary
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(TelemetrySummary).where(
                and_(
                    TelemetrySummary.installation_id == installation_id,
                    TelemetrySummary.date == today
                )
            )
        )
        summary = result.scalar_one_or_none()

        if summary:
            summary.total_sessions += 1
            summary.total_duration_seconds += session.duration_seconds
            summary.avg_session_seconds = summary.total_duration_seconds / summary.total_sessions
        else:
            summary = TelemetrySummary(
                date=today,
                installation_id=installation_id,
                total_sessions=1,
                total_duration_seconds=session.duration_seconds,
                avg_session_seconds=float(session.duration_seconds)
            )
            self.db.add(summary)

        await self.db.commit()

        logger.info("Remote session ended", {
            "session_id": session.session_id,
            "duration_seconds": session.duration_seconds,
            "end_reason": end_reason
        })

        return {
            "session_id": session.session_id,
            "duration_seconds": session.duration_seconds
        }

    # =========================================================================
    # Status & Query
    # =========================================================================

    async def get_installation_status(
        self,
        installation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get status and recent activity for an installation.

        Returns dict with status info, or None if not found.
        """
        logger.info("Installation status requested", {"installation_id": installation_id})

        result = await self.db.execute(
            select(Installation).where(Installation.installation_id == installation_id)
        )
        target_installation = result.scalar_one_or_none()

        if not target_installation:
            return None

        # Get log counts for last 24 hours
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

        log_counts = await self.db.execute(
            select(
                func.count().label('total'),
                func.sum(func.cast(RemoteLog.level == 'ERROR', Integer)).label('errors'),
                func.sum(func.cast(RemoteLog.level == 'CRITICAL', Integer)).label('criticals')
            ).where(
                and_(
                    RemoteLog.installation_id == installation_id,
                    RemoteLog.received_at >= twenty_four_hours_ago
                )
            )
        )
        counts = log_counts.first()

        return {
            "installation_id": installation_id,
            "installation_name": target_installation.installation_name,
            "status": "active" if target_installation.is_active else "inactive",
            "last_seen": target_installation.last_seen.isoformat() if target_installation.last_seen else None,
            "version": target_installation.last_version or target_installation.version,
            "logs_24h": counts.total or 0,
            "errors_24h": counts.errors or 0,
            "criticals_24h": counts.criticals or 0
        }

    async def get_health(self) -> Dict[str, Any]:
        """
        Health check for remote logging service.

        Returns dict with status, service name, and active installation count.
        """
        result = await self.db.execute(
            select(func.count()).select_from(Installation).where(Installation.is_active == True)
        )
        active_count = result.scalar() or 0

        return {
            "status": "healthy",
            "service": "remote-logging",
            "accepting_submissions": True,
            "registered_installations": active_count
        }
