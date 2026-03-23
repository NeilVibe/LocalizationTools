"""
Health Service - System health monitoring and diagnostics.

Extracts business logic from health routes.
Uses AsyncSession for database operations.

Usage:
    from server.services.health_service import HealthService

    service = HealthService(db)
    simple = await service.get_simple_health()
    detailed = await service.get_detailed_health()
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server import config

# Module-level globals for uptime tracking
_server_start_time = datetime.utcnow()
_request_count = 0


def _format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _get_uptime() -> Dict[str, Any]:
    """Calculate server uptime."""
    uptime = datetime.utcnow() - _server_start_time
    total_seconds = int(uptime.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m"

    return {
        "seconds": total_seconds,
        "formatted": uptime_str,
        "started_at": _server_start_time.isoformat()
    }


def _get_system_stats() -> Dict[str, Any]:
    """Get system resource usage."""
    stats = {
        "cpu_percent": None,
        "memory_used_gb": None,
        "memory_total_gb": None,
        "memory_percent": None,
        "disk_percent": None
    }

    try:
        import psutil

        stats["cpu_percent"] = psutil.cpu_percent(interval=0.1)

        mem = psutil.virtual_memory()
        stats["memory_used_gb"] = round(mem.used / (1024**3), 1)
        stats["memory_total_gb"] = round(mem.total / (1024**3), 1)
        stats["memory_percent"] = mem.percent

        disk = psutil.disk_usage('/')
        stats["disk_percent"] = disk.percent

    except ImportError:
        logger.debug("psutil not installed - system stats unavailable")
    except Exception as e:
        logger.warning(f"Failed to get system stats: {e}")

    return stats


def _get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket connection stats."""
    try:
        from server.utils.websocket import sio, connected_clients

        active_rooms = 0
        active_connections = len(connected_clients) if connected_clients else 0

        if hasattr(sio, 'manager') and sio.manager:
            try:
                rooms = sio.manager.get_rooms(namespace='/')
                if rooms:
                    active_rooms = len(rooms)
            except Exception as room_err:
                logger.debug(f"Failed to get rooms: {room_err}")

        logger.debug(f"WebSocket stats: connections={active_connections}, rooms={active_rooms}")

        return {
            "status": "active",
            "connections": active_connections,
            "rooms": active_rooms
        }

    except Exception as e:
        logger.warning(f"WebSocket stats unavailable: {e}")
        return {
            "status": "unknown",
            "connections": 0,
            "rooms": 0
        }


async def _check_database_health(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity and gather stats."""
    start = time.time()
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        latency_ms = round((time.time() - start) * 1000, 1)

        pool_info = {}
        try:
            from server.utils.dependencies import _async_engine
            if _async_engine and hasattr(_async_engine.pool, 'status'):
                pool = _async_engine.pool
                pool_info = {
                    "pool_size": getattr(pool, 'size', lambda: 0)(),
                    "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
                    "overflow": getattr(pool, 'overflow', lambda: 0)(),
                }
        except Exception:
            pass

        try:
            size_result = await db.execute(
                text("SELECT pg_database_size(current_database())")
            )
            db_size = size_result.scalar()
        except Exception:
            db_size = None

        return {
            "status": "connected" if latency_ms < 100 else "slow",
            "latency_ms": latency_ms,
            "pool_size": pool_info.get("pool_size", 0),
            "pool_used": pool_info.get("checked_out", 0),
            "size_bytes": db_size,
            "size_formatted": _format_bytes(db_size) if db_size else None
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "latency_ms": None,
            "error": str(e)
        }


async def _get_active_users(db: AsyncSession) -> Dict[str, Any]:
    """Get active user count and recent sessions."""
    try:
        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)

        result = await db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM user_sessions
                WHERE last_activity > :cutoff
            """),
            {"cutoff": five_mins_ago}
        )
        active_count = result.scalar() or 0

        return {
            "online_count": active_count,
            "sessions": []
        }

    except Exception as e:
        logger.debug(f"User stats unavailable: {e}")
        return {
            "online_count": 0,
            "sessions": []
        }


class HealthService:
    """Service layer for system health monitoring."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_simple_health(self) -> Dict[str, Any]:
        """
        Simple health status for client apps.

        Returns green/orange/red status indicators.
        """
        db_health = await _check_database_health(self.db)
        db_status = db_health.get("status", "error")

        ws_stats = _get_websocket_stats()
        ws_status = ws_stats.get("status", "unknown")

        if db_status == "error":
            overall = "unhealthy"
        elif db_status == "slow":
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "api": "connected",
            "database": db_status,
            "websocket": "connected" if ws_status == "active" else "disconnected"
        }

    async def get_detailed_health(self) -> Dict[str, Any]:
        """
        Detailed health metrics for admin dashboard.

        Returns API stats, database health, WebSocket stats, system resources, and user activity.
        """
        uptime = _get_uptime()
        api_stats = {
            "status": "healthy",
            "version": config.APP_VERSION,
            "uptime_seconds": uptime["seconds"],
            "uptime_formatted": uptime["formatted"],
            "started_at": uptime["started_at"]
        }

        db_health = await _check_database_health(self.db)
        ws_stats = _get_websocket_stats()
        system_stats = _get_system_stats()
        user_stats = await _get_active_users(self.db)

        return {
            "api": api_stats,
            "database": db_health,
            "websocket": ws_stats,
            "system": system_stats,
            "users": user_stats
        }
