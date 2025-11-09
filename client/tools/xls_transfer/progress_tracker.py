"""
Progress Tracker for XLSTransfer Operations

Updates progress directly in database to avoid HTTP deadlock.
Includes comprehensive logging for monitoring and troubleshooting.
"""

import os
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path

# Add server path for database access
server_path = Path(__file__).parent.parent.parent.parent / "server"
sys.path.insert(0, str(server_path))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import server.config as config
    from server.utils.websocket import emit_progress_update

    database_url = config.DATABASE_URL
    engine = create_engine(database_url, connect_args={"check_same_thread": False} if "sqlite" in database_url else {})
    SessionLocal = sessionmaker(bind=engine)
    DB_AVAILABLE = True
    WEBSOCKET_AVAILABLE = True
    print(f"[PROGRESS] ✓ Database connection established: {database_url.split('/')[-1]}", file=sys.stderr)
except ImportError as e:
    if "emit_progress_update" in str(e):
        # Database works but WebSocket doesn't - that's okay
        WEBSOCKET_AVAILABLE = False
        DB_AVAILABLE = True if 'engine' in locals() else False
        print(f"[PROGRESS] ⚠ WebSocket not available: {e}", file=sys.stderr)
    else:
        print(f"[PROGRESS] ⚠ Database not available: {e}", file=sys.stderr)
        DB_AVAILABLE = False
        WEBSOCKET_AVAILABLE = False
except Exception as e:
    print(f"[PROGRESS] ⚠ Database not available: {e}", file=sys.stderr)
    DB_AVAILABLE = False
    WEBSOCKET_AVAILABLE = False


class ProgressTracker:
    """
    Tracks and reports operation progress via direct database updates.

    Features:
    - Direct database writes (no HTTP deadlock)
    - Detailed current_step descriptions
    - Graceful error handling (never breaks the operation)
    - Comprehensive logging for monitoring
    """

    def __init__(self, operation_id: Optional[int] = None):
        """
        Initialize progress tracker.

        Args:
            operation_id: ActiveOperation ID from database
        """
        self.operation_id = operation_id
        self.enabled = operation_id is not None and DB_AVAILABLE

        if self.enabled:
            print(f"[PROGRESS] Progress tracking enabled for operation_id={operation_id}", file=sys.stderr)
        elif operation_id and not DB_AVAILABLE:
            print(f"[PROGRESS] ⚠ Database unavailable - progress tracking disabled", file=sys.stderr)
        else:
            print("[PROGRESS] Progress tracking disabled (no operation_id provided)", file=sys.stderr)

    def update(
        self,
        progress_percentage: float,
        current_step: str,
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None
    ):
        """
        Send progress update directly to database.

        Args:
            progress_percentage: Progress from 0.0 to 100.0
            current_step: Human-readable description of current step
            completed_steps: Number of completed steps (optional)
            total_steps: Total number of steps (optional)

        Example:
            tracker.update(45.5, "Processing row 234/500", 234, 500)
        """
        if not self.enabled:
            # Still log progress for monitoring, even if not sending to DB
            print(f"[PROGRESS] {progress_percentage:.1f}% - {current_step}", file=sys.stderr)
            return

        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"[PROGRESS] [{timestamp}] Updating operation {self.operation_id}: "
                f"{progress_percentage:.1f}% - {current_step}",
                file=sys.stderr
            )

            # Update database directly
            db = SessionLocal()
            try:
                update_query = text("""
                    UPDATE active_operations
                    SET progress_percentage = :progress,
                        current_step = :step,
                        completed_steps = :completed,
                        updated_at = :updated
                    WHERE operation_id = :op_id
                """)

                db.execute(update_query, {
                    "progress": round(progress_percentage, 2),
                    "step": current_step,
                    "completed": completed_steps,
                    "updated": datetime.utcnow(),
                    "op_id": self.operation_id
                })
                db.commit()

                print(f"[PROGRESS] ✓ Database update successful", file=sys.stderr)

            finally:
                db.close()

        except Exception as e:
            # Any error - log but don't break the operation
            print(f"[PROGRESS] ⚠ Database update failed: {type(e).__name__}: {e}", file=sys.stderr)

    def log_milestone(self, message: str):
        """
        Log an important milestone without updating progress.

        Args:
            message: Milestone description

        Example:
            tracker.log_milestone("Dictionary loaded successfully (18,332 pairs)")
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[MILESTONE] [{timestamp}] {message}", file=sys.stderr)

    def log_error(self, error_message: str, error_type: str = "Error"):
        """
        Log an error that occurred during operation.

        Args:
            error_message: Error description
            error_type: Type of error (e.g., "ValueError", "FileNotFoundError")
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[ERROR] [{timestamp}] {error_type}: {error_message}", file=sys.stderr)
