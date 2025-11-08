"""
Request/Response Logging Middleware

Comprehensive logging of all API requests and responses for debugging and audit trails.
"""

import time
import json
from typing import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs:
    - Request: Method, URL, headers, body, client IP
    - Response: Status code, headers, body (if not too large)
    - Performance: Request duration
    - Errors: Full stack trace on exceptions
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and response, logging everything.
        """
        # Generate unique request ID
        request_id = f"{int(time.time() * 1000)}-{id(request)}"

        # Log request start
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url)

        # Get request body if present (for debugging)
        body_data = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # Read and store body
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        body_data = json.loads(body_bytes.decode())
                        # Mask sensitive fields
                        if isinstance(body_data, dict):
                            for sensitive_field in ['password', 'token', 'secret', 'api_key']:
                                if sensitive_field in body_data:
                                    body_data[sensitive_field] = "***REDACTED***"
                    except:
                        body_data = body_bytes.decode()[:200]  # First 200 chars

                # Create new request with body available
                async def receive():
                    return {"type": "http.request", "body": body_bytes}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Could not read request body: {e}")

        # Log request
        logger.info(
            f"[{request_id}] → {method} {url} | "
            f"Client: {client_ip} | "
            f"User-Agent: {request.headers.get('user-agent', 'unknown')[:100]}"
        )

        if body_data:
            logger.debug(f"[{request_id}] Request Body: {json.dumps(body_data, indent=2)[:500]}")

        # Start timer
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            status_code = response.status_code
            log_level = "INFO"
            if status_code >= 500:
                log_level = "ERROR"
            elif status_code >= 400:
                log_level = "WARNING"

            log_message = (
                f"[{request_id}] ← {status_code} {method} {url} | "
                f"Duration: {duration_ms:.2f}ms"
            )

            if log_level == "ERROR":
                logger.error(log_message)
            elif log_level == "WARNING":
                logger.warning(log_message)
            else:
                logger.info(log_message)

            # Log slow requests
            if duration_ms > 1000:  # > 1 second
                logger.warning(
                    f"[{request_id}] SLOW REQUEST: {method} {url} took {duration_ms:.2f}ms"
                )

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.time() - start_time) * 1000

            # Log exception with full details
            logger.exception(
                f"[{request_id}] ✗ EXCEPTION during {method} {url} | "
                f"Duration: {duration_ms:.2f}ms | "
                f"Error: {str(e)}"
            )

            # Re-raise to let FastAPI handle it
            raise


class DatabaseQueryLoggingMiddleware:
    """
    Middleware to log database queries for debugging.

    Note: SQLAlchemy's echo=True in config.py already logs queries,
    but this provides additional context.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Could add database-specific logging here
            # For now, rely on SQLAlchemy's echo parameter
            pass

        await self.app(scope, receive, send)


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and log performance metrics.
    """

    def __init__(self, app, sample_rate: float = 1.0):
        super().__init__(app)
        self.sample_rate = sample_rate
        self.request_count = 0
        self.total_duration = 0.0
        self.endpoint_stats = {}

    async def dispatch(self, request: Request, call_next: Callable):
        """Track performance metrics."""
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Update stats
            self.request_count += 1
            self.total_duration += duration

            endpoint = f"{request.method} {request.url.path}"
            if endpoint not in self.endpoint_stats:
                self.endpoint_stats[endpoint] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'min_duration': float('inf'),
                    'max_duration': 0.0
                }

            stats = self.endpoint_stats[endpoint]
            stats['count'] += 1
            stats['total_duration'] += duration
            stats['min_duration'] = min(stats['min_duration'], duration)
            stats['max_duration'] = max(stats['max_duration'], duration)

            # Log stats every 100 requests
            if self.request_count % 100 == 0:
                avg_duration = self.total_duration / self.request_count
                logger.info(
                    f"Performance Stats: {self.request_count} requests | "
                    f"Avg: {avg_duration*1000:.2f}ms | "
                    f"Total time: {self.total_duration:.2f}s"
                )

            return response

        except Exception as e:
            logger.exception(f"Performance tracking error: {e}")
            raise


def get_performance_stats() -> dict:
    """Get current performance statistics."""
    # This would return stats from the middleware instance
    # Implementation depends on how middleware is instantiated
    return {
        "message": "Performance stats available via middleware instance"
    }
