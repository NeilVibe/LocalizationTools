"""
PG LISTEN/NOTIFY -- Real-time event bus for cross-backend sync.

Phase 111: When multiple backends connect to the same PostgreSQL,
PG LISTEN/NOTIFY propagates events to ALL of them. Each backend
then broadcasts to its own local WebSocket client.

Channels:
- locanext_row_update: Row edits (target, status changes)
- locanext_file_change: File/folder/project changes
- locanext_activity: Activity log entries (for dashboard)

Usage:
    # Send notification (from any route):
    await pg_notify("locanext_row_update", {"file_id": 1, "row_id": 42, ...})

    # Listener starts automatically in lifespan when PG is active.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional, Callable, Awaitable

import asyncpg
from loguru import logger

from server import config

# Global listener connection
_listener_conn: Optional[asyncpg.Connection] = None
_listener_task: Optional[asyncio.Task] = None

# Callbacks registered by WebSocket layer
_callbacks: dict[str, list[Callable]] = {}


def on_notify(channel: str, callback: Callable[[dict], Awaitable[None]]):
    """Register a callback for a PG NOTIFY channel."""
    if channel not in _callbacks:
        _callbacks[channel] = []
    _callbacks[channel].append(callback)


async def pg_notify(channel: str, payload: dict):
    """Send a PG NOTIFY with JSON payload. Safe to call from any async context.

    Uses a short-lived connection to avoid blocking the listener connection.
    Falls back silently if PG is not available (SQLite mode).
    """
    if config.ACTIVE_DATABASE_TYPE != "postgresql":
        return  # SQLite mode -- no PG NOTIFY, local WebSocket handles it

    try:
        dsn = _get_asyncpg_dsn()
        conn = await asyncpg.connect(dsn, timeout=5)
        try:
            payload_str = json.dumps(payload, default=str)
            await conn.execute(f"SELECT pg_notify($1, $2)", channel, payload_str)
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"[PG_NOTIFY] Failed to send on {channel}: {e}")


async def start_listener():
    """Start the PG LISTEN listener. Call from FastAPI lifespan."""
    global _listener_conn, _listener_task

    if config.ACTIVE_DATABASE_TYPE != "postgresql":
        logger.info("[PG_NOTIFY] SQLite mode -- PG LISTEN not started (local WebSocket only)")
        return

    try:
        dsn = _get_asyncpg_dsn()
        _listener_conn = await asyncpg.connect(dsn, timeout=10)

        # Subscribe to channels
        channels = ["locanext_row_update", "locanext_file_change", "locanext_activity"]
        for ch in channels:
            await _listener_conn.add_listener(ch, _handle_notification)

        logger.success(f"[PG_NOTIFY] Listening on {len(channels)} channels: {', '.join(channels)}")

        # Keep connection alive with periodic pings
        _listener_task = asyncio.create_task(_keepalive_loop())
    except Exception as e:
        logger.warning(f"[PG_NOTIFY] Failed to start listener: {e}. Real-time cross-user sync disabled.")


async def stop_listener():
    """Stop the PG LISTEN listener. Call from FastAPI lifespan shutdown."""
    global _listener_conn, _listener_task

    if _listener_task:
        _listener_task.cancel()
        _listener_task = None

    if _listener_conn:
        try:
            await _listener_conn.close()
        except Exception:
            pass
        _listener_conn = None

    logger.info("[PG_NOTIFY] Listener stopped")


def _handle_notification(conn, pid, channel, payload):
    """Handle incoming PG NOTIFY. Runs registered callbacks."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        data = {"raw": payload}

    callbacks = _callbacks.get(channel, [])
    for cb in callbacks:
        try:
            # Schedule callback in the event loop (notification handler is sync)
            asyncio.get_running_loop().create_task(cb(data))
        except Exception as e:
            logger.error(f"[PG_NOTIFY] Callback error on {channel}: {e}")


async def _keepalive_loop():
    """Periodic ping to keep the LISTEN connection alive."""
    while True:
        try:
            await asyncio.sleep(30)
            if _listener_conn and not _listener_conn.is_closed():
                await _listener_conn.execute("SELECT 1")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"[PG_NOTIFY] Keepalive failed: {e}")
            # Try to reconnect
            try:
                await stop_listener()
                await asyncio.sleep(5)
                await start_listener()
            except Exception as reconnect_err:
                logger.error(f"[PG_NOTIFY] Reconnect failed: {reconnect_err}. Listener stopped permanently.")
                break


def _get_asyncpg_dsn() -> str:
    """Convert config to asyncpg DSN format."""
    return (
        f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@"
        f"{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
    )
