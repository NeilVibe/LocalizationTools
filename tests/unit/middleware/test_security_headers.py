# tests/unit/middleware/test_security_headers.py
"""Tests for security headers middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_scope(path="/", method="GET"):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }


class FakeResponse:
    """Simulates a Starlette Response with mutable headers."""

    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = MutableHeaders(raw=headers or [])


@pytest.fixture
def make_app():
    """Create a minimal ASGI app that returns 200 with empty headers."""
    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({
            "type": "http.response.body",
            "body": b"OK",
        })
    return app


def test_csp_header_present(make_app):
    """CSP header must include script-src 'self' and style-src 'unsafe-inline'."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    middleware = SecurityHeadersMiddleware(make_app)
    # We test via the response headers dict
    headers = middleware.get_security_headers(ssl_enabled=False)
    csp = headers.get("Content-Security-Policy", "")

    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" in csp  # Required for Svelte/Carbon styles
    assert "default-src 'self'" in csp
    # connect-src must NOT allow http:/https: (data exfiltration risk)
    assert "connect-src 'self' ws: wss:" in csp
    assert "http:" not in csp.split("connect-src")[1].split(";")[0]


def test_x_frame_options(make_app):
    """X-Frame-Options must be DENY."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Frame-Options"] == "DENY"


def test_x_content_type_options(make_app):
    """X-Content-Type-Options must be nosniff."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_hsts_only_when_ssl(make_app):
    """Strict-Transport-Security must only be set when SSL is enabled."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    mw = SecurityHeadersMiddleware(make_app)
    headers_no_ssl = mw.get_security_headers(ssl_enabled=False)
    headers_ssl = mw.get_security_headers(ssl_enabled=True)

    assert "Strict-Transport-Security" not in headers_no_ssl
    assert "max-age=" in headers_ssl["Strict-Transport-Security"]


def test_referrer_policy(make_app):
    """Referrer-Policy must be strict-origin-when-cross-origin."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy(make_app):
    """Permissions-Policy must restrict camera, microphone, geolocation."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    pp = headers["Permissions-Policy"]
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


def test_cross_domain_policies(make_app):
    """X-Permitted-Cross-Domain-Policies must be none."""
    from server.middleware.security_headers import SecurityHeadersMiddleware

    headers = SecurityHeadersMiddleware(make_app).get_security_headers(ssl_enabled=False)
    assert headers["X-Permitted-Cross-Domain-Policies"] == "none"
