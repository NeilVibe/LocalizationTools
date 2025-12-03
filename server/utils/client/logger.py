"""
Logging Utility

Sends usage logs to the central server for analytics.
Tracks tool usage, function calls, performance metrics, and errors.

CLEAN logging with proper error handling and offline queue.
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json
import requests
from loguru import logger

from server.client_config import client_config as config


class UsageLogger:
    """
    Central usage logger that sends detailed logs to server.

    Tracks:
    - User ID and session
    - Tool and function usage
    - Performance metrics (duration, CPU, memory)
    - File metadata (size, rows processed)
    - Errors and status

    Handles offline mode gracefully by queueing logs locally.
    """

    def __init__(self):
        """Initialize the logger."""
        self.session_id = str(uuid.uuid4())
        self.log_queue = []
        self.max_queue_size = config.LOG_QUEUE_MAX_SIZE
        self.server_available = not config.OFFLINE_MODE

        # Initialize session
        self._start_session()

    def _start_session(self):
        """Start a new session with the server."""
        if config.OFFLINE_MODE or config.MOCK_SERVER:
            logger.info("Offline mode - session tracking disabled")
            return

        try:
            response = requests.post(
                config.API_SESSION_START,
                json={
                    "machine_id": config.MACHINE_ID,
                    "app_version": config.APP_VERSION,
                    "os_info": config.OS_INFO,
                },
                headers={"X-API-Key": config.API_KEY},
                timeout=config.API_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id", self.session_id)
                logger.info(f"Session started: {self.session_id}")
                self.server_available = True
            else:
                logger.warning(f"Failed to start session: {response.status_code}")
                self.server_available = False

        except requests.exceptions.RequestException as e:
            logger.warning(f"Server unavailable: {e}")
            self.server_available = False

    def log_operation(
        self,
        user_id: Optional[int],
        username: str,
        tool_name: str,
        function_name: str,
        duration_seconds: float,
        status: str = "success",
        file_name: Optional[str] = None,
        file_size_mb: Optional[float] = None,
        rows_processed: Optional[int] = None,
        sheets_processed: Optional[int] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        cpu_percent: Optional[float] = None,
        memory_mb: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a tool operation to the server.

        Args:
            user_id: User database ID (if authenticated)
            username: Username for tracking
            tool_name: Name of the tool (e.g., "XLSTransfer")
            function_name: Name of the function (e.g., "create_dictionary")
            duration_seconds: How long the operation took
            status: "success", "error", or "cancelled"
            file_name: Name of the file processed (optional, privacy-aware)
            file_size_mb: Size of the file in MB
            rows_processed: Number of rows processed
            sheets_processed: Number of sheets processed
            error_message: Error message if status is "error"
            error_type: Type of error (e.g., "ValueError")
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
            metadata: Additional metadata as JSON
        """

        # Respect privacy settings
        if not config.LOG_FILE_NAMES:
            file_name = None

        log_entry = {
            "user_id": user_id,
            "username": username,
            "session_id": self.session_id,
            "tool_name": tool_name,
            "function_name": function_name,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": round(duration_seconds, 2),
            "status": status,
            "file_name": file_name,
            "file_size_mb": round(file_size_mb, 2) if file_size_mb else None,
            "rows_processed": rows_processed,
            "sheets_processed": sheets_processed,
            "error_message": error_message,
            "error_type": error_type,
            "cpu_percent": round(cpu_percent, 2) if cpu_percent else None,
            "memory_mb": round(memory_mb, 2) if memory_mb else None,
            "metadata": metadata or {},
        }

        logger.info(
            f"Logging: {username} → {tool_name}.{function_name} "
            f"({duration_seconds:.2f}s, {status})"
        )

        # Send to server or queue
        if config.ENABLE_SERVER_LOGGING:
            self._send_log(log_entry)
        else:
            logger.debug("Server logging disabled")

    def _send_log(self, log_entry: Dict[str, Any]):
        """Send log entry to server."""

        if config.OFFLINE_MODE or config.MOCK_SERVER:
            logger.debug("Offline mode - log queued locally")
            self._queue_log(log_entry)
            return

        try:
            response = requests.post(
                config.API_LOGS,
                json=log_entry,
                headers={"X-API-Key": config.API_KEY},
                timeout=config.API_TIMEOUT
            )

            if response.status_code == 200:
                logger.debug("Log sent successfully")
                self.server_available = True
                # Process queued logs
                self._flush_queue()
            else:
                logger.warning(f"Failed to send log: {response.status_code}")
                self._queue_log(log_entry)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Server unavailable: {e}")
            self.server_available = False
            self._queue_log(log_entry)

    def _queue_log(self, log_entry: Dict[str, Any]):
        """Queue log locally when server is unavailable."""
        if len(self.log_queue) >= self.max_queue_size:
            # Remove oldest log
            self.log_queue.pop(0)
            logger.warning("Log queue full, removing oldest entry")

        self.log_queue.append(log_entry)
        logger.debug(f"Log queued ({len(self.log_queue)}/{self.max_queue_size})")

    def _flush_queue(self):
        """Send queued logs to server."""
        if not self.log_queue:
            return

        logger.info(f"Flushing {len(self.log_queue)} queued logs...")

        while self.log_queue:
            log_entry = self.log_queue[0]
            try:
                response = requests.post(
                    config.API_LOGS,
                    json=log_entry,
                    headers={"X-API-Key": config.API_KEY},
                    timeout=config.API_TIMEOUT
                )

                if response.status_code == 200:
                    self.log_queue.pop(0)
                    logger.debug("Queued log sent successfully")
                else:
                    logger.warning("Failed to flush queue, will retry later")
                    break

            except requests.exceptions.RequestException:
                logger.warning("Server unavailable, keeping queue")
                break

    def end_session(self):
        """End the current session."""
        if config.OFFLINE_MODE or config.MOCK_SERVER:
            return

        try:
            requests.post(
                config.API_SESSION_END,
                json={"session_id": self.session_id},
                headers={"X-API-Key": config.API_KEY},
                timeout=config.API_TIMEOUT
            )
            logger.info(f"Session ended: {self.session_id}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to end session: {e}")


# Global logger instance
_usage_logger: Optional[UsageLogger] = None


def get_logger() -> UsageLogger:
    """Get the global usage logger instance."""
    global _usage_logger
    if _usage_logger is None:
        _usage_logger = UsageLogger()
    return _usage_logger


def log_function_call(
    username: str,
    tool_name: str,
    function_name: str
):
    """
    Decorator to automatically log function calls.

    Usage:
        @log_function_call(username="john_doe", tool_name="XLSTransfer", function_name="create_dictionary")
        def create_dictionary(file_path):
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            error_message = None
            error_type = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_message = str(e)
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                get_logger().log_operation(
                    user_id=None,  # TODO: Get from session
                    username=username,
                    tool_name=tool_name,
                    function_name=function_name,
                    duration_seconds=duration,
                    status=status,
                    error_message=error_message,
                    error_type=error_type
                )

        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Example 1: Manual logging
    logger_instance = get_logger()

    logger_instance.log_operation(
        user_id=None,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="create_dictionary",
        duration_seconds=45.2,
        status="success",
        file_size_mb=2.5,
        rows_processed=5000
    )

    # Example 2: Using decorator
    @log_function_call(
        username="test_user",
        tool_name="XLSTransfer",
        function_name="test_function"
    )
    def test_function():
        time.sleep(1)
        return "Done!"

    test_function()

    # End session
    logger_instance.end_session()
