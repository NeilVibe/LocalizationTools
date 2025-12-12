"""
Unified Progress Tracker with Context Manager Support

USAGE (Context Manager - Recommended):
    with TrackedOperation("TM Processing", user_id, tool_name="LDM") as op:
        op.update(25, "Generating embeddings...")
        # do work
        op.update(75, "Building index...")
        # do work
    # AUTO-completes on exit, AUTO-fails on exception

USAGE (Manual - Legacy):
    tracker = ProgressTracker(operation_id)
    tracker.update(25, "Step 1...")
    tracker.complete()

Features:
- Context manager: auto-create, auto-complete, auto-fail
- Direct DB writes (sync) - no HTTP deadlock
- WebSocket emission for real-time UI
- Graceful error handling - never breaks the operation
"""

import sys
from typing import Optional
from datetime import datetime
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Database setup (sync for tool compatibility)
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import server.config as config

    database_url = config.DATABASE_URL
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"Progress tracker DB not available: {e}")
    DB_AVAILABLE = False
    SessionLocal = None

# WebSocket setup (async, called via asyncio.run)
try:
    from server.utils.websocket import (
        emit_operation_start,
        emit_progress_update,
        emit_operation_complete,
        emit_operation_failed
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    emit_operation_start = None
    emit_progress_update = None
    emit_operation_complete = None
    emit_operation_failed = None


def _emit_async(coro):
    """Helper to call async WebSocket functions from sync code."""
    if not WEBSOCKET_AVAILABLE:
        return
    try:
        import asyncio
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in async context - create task
            loop.create_task(coro)
        except RuntimeError:
            # No running loop - use asyncio.run
            asyncio.run(coro)
    except Exception as e:
        logger.warning(f"WebSocket emit failed (non-blocking): {e}")


class ProgressTracker:
    """
    Tracks operation progress via direct database updates.

    Use TrackedOperation context manager for new code.
    This class is for manual tracking or legacy compatibility.
    """

    def __init__(self, operation_id: Optional[int] = None):
        self.operation_id = operation_id
        self.enabled = operation_id is not None and DB_AVAILABLE
        self._db = None

    def update(self, progress: float, message: str = None, completed_steps: Optional[int] = None, total_steps: Optional[int] = None, current_step: str = None):
        """Update progress in DB and emit WebSocket event.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message (positional)
            completed_steps: Number of completed steps
            total_steps: Total number of steps
            current_step: Alias for message (for compatibility)
        """
        # Support both 'message' (positional) and 'current_step' (keyword) for compatibility
        if current_step and not message:
            message = current_step
        if not message:
            message = f"Progress: {progress:.1f}%"
        if not self.enabled:
            logger.info(f"[PROGRESS] {progress:.1f}% - {message}")
            return

        try:
            db = SessionLocal()
            try:
                db.execute(text("""
                    UPDATE active_operations
                    SET progress_percentage = :progress,
                        current_step = :step,
                        completed_steps = :completed,
                        updated_at = :updated
                    WHERE operation_id = :op_id
                """), {
                    "progress": round(progress, 2),
                    "step": message,
                    "completed": completed_steps,
                    "updated": datetime.utcnow(),
                    "op_id": self.operation_id
                })
                db.commit()
            finally:
                db.close()

            # Emit WebSocket event
            if WEBSOCKET_AVAILABLE:
                _emit_async(emit_progress_update({
                    'operation_id': self.operation_id,
                    'progress_percentage': round(progress, 2),
                    'current_step': message,
                    'completed_steps': completed_steps,
                    'total_steps': total_steps,
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }))

        except Exception as e:
            logger.warning(f"Progress update failed (non-blocking): {e}")

    def complete(self, result: Optional[dict] = None):
        """Mark operation as completed."""
        if not self.enabled:
            return

        try:
            db = SessionLocal()
            try:
                db.execute(text("""
                    UPDATE active_operations
                    SET status = 'completed',
                        progress_percentage = 100,
                        current_step = 'Completed',
                        completed_at = :completed,
                        updated_at = :updated
                    WHERE operation_id = :op_id
                """), {
                    "completed": datetime.utcnow(),
                    "updated": datetime.utcnow(),
                    "op_id": self.operation_id
                })
                db.commit()
            finally:
                db.close()

            if WEBSOCKET_AVAILABLE:
                _emit_async(emit_operation_complete({
                    'operation_id': self.operation_id,
                    'status': 'completed',
                    'progress_percentage': 100,
                    'completed_at': datetime.utcnow().isoformat() + 'Z'
                }))

        except Exception as e:
            logger.warning(f"Complete update failed: {e}")

    def fail(self, error_message: str):
        """Mark operation as failed."""
        if not self.enabled:
            return

        try:
            db = SessionLocal()
            try:
                db.execute(text("""
                    UPDATE active_operations
                    SET status = 'failed',
                        error_message = :error,
                        completed_at = :completed,
                        updated_at = :updated
                    WHERE operation_id = :op_id
                """), {
                    "error": error_message,
                    "completed": datetime.utcnow(),
                    "updated": datetime.utcnow(),
                    "op_id": self.operation_id
                })
                db.commit()
            finally:
                db.close()

            if WEBSOCKET_AVAILABLE:
                _emit_async(emit_operation_failed({
                    'operation_id': self.operation_id,
                    'status': 'failed',
                    'error_message': error_message,
                    'completed_at': datetime.utcnow().isoformat() + 'Z'
                }))

        except Exception as e:
            logger.warning(f"Fail update failed: {e}")


class TrackedOperation:
    """
    Context manager for automatic operation tracking.

    AUTO-creates operation on enter.
    AUTO-completes on clean exit.
    AUTO-fails on exception.

    Usage:
        with TrackedOperation("Process TM", user_id, tool_name="LDM") as op:
            op.update(25, "Step 1...")
            op.update(75, "Step 2...")
        # Done - auto-completed
    """

    def __init__(
        self,
        operation_name: str,
        user_id: int,
        username: str = "system",
        tool_name: str = "Unknown",
        function_name: str = "process",
        total_steps: Optional[int] = None,
        file_info: Optional[dict] = None,
        parameters: Optional[dict] = None
    ):
        self.operation_name = operation_name
        self.user_id = user_id
        self.username = username
        self.tool_name = tool_name
        self.function_name = function_name
        self.total_steps = total_steps
        self.file_info = file_info
        self.parameters = parameters

        self.operation_id = None
        self._tracker = None
        self._entered = False

    def __enter__(self):
        """Create operation in DB and return tracker."""
        if not DB_AVAILABLE:
            logger.warning("TrackedOperation: DB not available, tracking disabled")
            self._tracker = ProgressTracker(None)
            return self._tracker

        try:
            db = SessionLocal()
            try:
                # Insert new operation
                result = db.execute(text("""
                    INSERT INTO active_operations
                    (user_id, username, tool_name, function_name, operation_name,
                     status, progress_percentage, total_steps, file_info, parameters,
                     started_at, updated_at)
                    VALUES
                    (:user_id, :username, :tool_name, :function_name, :operation_name,
                     'running', 0, :total_steps, :file_info, :parameters,
                     :started_at, :updated_at)
                    RETURNING operation_id
                """), {
                    "user_id": self.user_id,
                    "username": self.username,
                    "tool_name": self.tool_name,
                    "function_name": self.function_name,
                    "operation_name": self.operation_name,
                    "total_steps": self.total_steps,
                    "file_info": str(self.file_info) if self.file_info else None,
                    "parameters": str(self.parameters) if self.parameters else None,
                    "started_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                row = result.fetchone()
                self.operation_id = row[0]
                db.commit()

                logger.info(f"TrackedOperation created: {self.operation_id} - {self.operation_name}")

            finally:
                db.close()

            # Emit WebSocket start event
            if WEBSOCKET_AVAILABLE:
                _emit_async(emit_operation_start({
                    'operation_id': self.operation_id,
                    'user_id': self.user_id,
                    'username': self.username,
                    'tool_name': self.tool_name,
                    'operation_name': self.operation_name,
                    'status': 'running',
                    'progress_percentage': 0,
                    'started_at': datetime.utcnow().isoformat() + 'Z'
                }))

            self._tracker = ProgressTracker(self.operation_id)
            self._entered = True
            return self._tracker

        except Exception as e:
            logger.error(f"TrackedOperation creation failed: {e}")
            self._tracker = ProgressTracker(None)
            return self._tracker

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-complete or auto-fail based on exception."""
        if not self._tracker or not self._tracker.enabled:
            return False

        if exc_type is not None:
            # Exception occurred - mark as failed
            error_msg = f"{exc_type.__name__}: {exc_val}"
            self._tracker.fail(error_msg)
            logger.error(f"TrackedOperation failed: {self.operation_id} - {error_msg}")
        else:
            # Clean exit - mark as completed
            self._tracker.complete()
            logger.success(f"TrackedOperation completed: {self.operation_id} - {self.operation_name}")

        return False  # Don't suppress exceptions


# Convenience function for quick tracking
def track_operation(operation_name: str, user_id: int, **kwargs) -> TrackedOperation:
    """
    Convenience function to create a TrackedOperation.

    Usage:
        with track_operation("Process TM", user_id, tool_name="LDM") as op:
            op.update(50, "Working...")
    """
    return TrackedOperation(operation_name, user_id, **kwargs)
