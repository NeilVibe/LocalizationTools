# server/middleware/security_headers.py
"""
Security headers middleware — OWASP best practices.

Adds CSP, X-Frame-Options, X-Content-Type-Options, HSTS (when SSL),
Referrer-Policy, and Permissions-Policy to every HTTP response.

Backward compatible: headers are purely additive. No existing behavior changes.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response."""

    def __init__(self, app, ssl_enabled: bool = False):
        super().__init__(app)
        self.ssl_enabled = ssl_enabled
        self._headers = self.get_security_headers(ssl_enabled)
        logger.info(f"[SECURITY] Headers middleware active (SSL={ssl_enabled}, {len(self._headers)} headers)")

    def get_security_headers(self, ssl_enabled: bool) -> dict[str, str]:
        """Build the security headers dict. Separated for testing."""
        headers = {
            # CSP: block XSS script injection. unsafe-inline for styles only (Svelte/Carbon requirement).
            # connect-src 'self' ws: wss: — same-origin API + Socket.IO. LAN cross-PC connections
            # work because the User's browser loads from the Admin's origin (same-origin).
            # Do NOT use http: https: — that would allow XSS data exfiltration to any server.
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss:; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME-type sniffing
            "X-Content-Type-Options": "nosniff",
            # Control referrer info leakage
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Restrict browser features
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        }

        # Prevent Adobe Flash/Acrobat cross-domain data loading
        headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # HSTS only when SSL is active (sending over HTTP would break non-SSL setups)
        # No includeSubDomains — LAN app uses IP addresses, not domain names
        if ssl_enabled:
            headers["Strict-Transport-Security"] = "max-age=31536000"

        return headers

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in self._headers.items():
            response.headers[key] = value
        return response
