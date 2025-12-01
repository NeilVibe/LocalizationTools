"""
IP Range Filter Middleware

Restricts API access to specific IP ranges for internal enterprise deployment.
Supports CIDR notation and multiple ranges.

Usage in .env:
    ALLOWED_IP_RANGE=192.168.11.0/24
    ALLOWED_IP_RANGE=192.168.11.0/24,192.168.12.0/24,10.0.0.0/8

Examples:
    192.168.11.0/24  -> 192.168.11.1 - 192.168.11.254
    10.0.0.0/8       -> 10.0.0.1 - 10.255.255.254
    192.168.11.50/32 -> Single IP only
"""

import ipaddress
import logging
from typing import List, Optional, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Import audit logger (with fallback if not available)
try:
    from server.utils.audit_logger import log_ip_blocked
    AUDIT_ENABLED = True
except ImportError:
    AUDIT_ENABLED = False
    log_ip_blocked = None


class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to filter requests by IP address.

    Blocks requests from IPs outside the allowed ranges.
    Always allows localhost for development.
    """

    def __init__(
        self,
        app,
        allowed_ranges: Optional[List[str]] = None,
        allow_localhost: bool = True,
        log_blocked: bool = True,
    ):
        """
        Initialize IP filter middleware.

        Args:
            app: FastAPI application
            allowed_ranges: List of CIDR ranges (e.g., ["192.168.11.0/24"])
                           If None or empty, all IPs are allowed (dev mode)
            allow_localhost: Always allow localhost/127.0.0.1 (default: True)
            log_blocked: Log blocked IP attempts (default: True)
        """
        super().__init__(app)
        self.allow_localhost = allow_localhost
        self.log_blocked = log_blocked
        self.enabled = False
        self.networks: List[ipaddress.IPv4Network] = []

        # Parse allowed ranges
        if allowed_ranges:
            self._parse_ranges(allowed_ranges)

    def _parse_ranges(self, ranges: List[str]) -> None:
        """Parse CIDR ranges into network objects."""
        for range_str in ranges:
            range_str = range_str.strip()
            if not range_str:
                continue

            try:
                # Support both single IPs and CIDR notation
                if "/" not in range_str:
                    # Single IP - treat as /32
                    range_str = f"{range_str}/32"

                network = ipaddress.IPv4Network(range_str, strict=False)
                self.networks.append(network)
                logger.info(f"IP Filter: Added allowed range {network}")
            except ValueError as e:
                logger.error(f"IP Filter: Invalid range '{range_str}': {e}")

        if self.networks:
            self.enabled = True
            logger.info(f"IP Filter: ENABLED with {len(self.networks)} range(s)")
        else:
            logger.warning("IP Filter: No valid ranges configured, filter DISABLED")

    def _is_localhost(self, ip: str) -> bool:
        """Check if IP is localhost."""
        localhost_ips = {"127.0.0.1", "::1", "localhost"}
        return ip in localhost_ips

    def _is_allowed(self, ip: str) -> bool:
        """
        Check if IP is allowed.

        Returns True if:
        - Filter is disabled (no ranges configured)
        - IP is localhost and allow_localhost is True
        - IP is within any of the allowed ranges
        """
        # If filter not enabled, allow all
        if not self.enabled:
            return True

        # Always allow localhost in development
        if self.allow_localhost and self._is_localhost(ip):
            return True

        try:
            ip_addr = ipaddress.IPv4Address(ip)

            # Check against all allowed networks
            for network in self.networks:
                if ip_addr in network:
                    return True

            return False
        except ValueError:
            # Invalid IP format - block it
            logger.warning(f"IP Filter: Invalid IP format: {ip}")
            return False

    def _get_client_ip(self, request: Request) -> str:
        """
        Get the real client IP address.

        Checks X-Forwarded-For header for reverse proxy setups,
        falls back to direct client IP.
        """
        # Check for reverse proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()

        # Direct connection
        if request.client:
            return request.client.host

        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and check IP."""
        client_ip = self._get_client_ip(request)

        if not self._is_allowed(client_ip):
            # Log blocked attempt
            if self.log_blocked:
                logger.warning(
                    f"IP Filter: BLOCKED request from {client_ip} "
                    f"to {request.method} {request.url.path}"
                )
                # Audit log the blocked attempt
                if AUDIT_ENABLED and log_ip_blocked:
                    log_ip_blocked(
                        client_ip,
                        f"Blocked access to {request.method} {request.url.path}"
                    )

            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied: IP not in allowed range",
                    "error": "ip_not_allowed",
                }
            )

        # IP allowed - continue to next middleware/route
        response = await call_next(request)
        return response


def parse_ip_ranges(env_value: str) -> List[str]:
    """
    Parse IP ranges from environment variable.

    Supports comma-separated values:
        "192.168.11.0/24,192.168.12.0/24,10.0.0.0/8"

    Returns list of range strings.
    """
    if not env_value:
        return []

    ranges = []
    for part in env_value.split(","):
        part = part.strip()
        if part:
            ranges.append(part)

    return ranges


def get_ip_filter_status(middleware: IPFilterMiddleware) -> dict:
    """Get current IP filter configuration status."""
    return {
        "enabled": middleware.enabled,
        "allow_localhost": middleware.allow_localhost,
        "log_blocked": middleware.log_blocked,
        "allowed_ranges": [str(n) for n in middleware.networks],
        "range_count": len(middleware.networks),
    }
