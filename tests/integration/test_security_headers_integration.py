"""Integration test: verify security headers appear on actual HTTP responses."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def app_no_ssl():
    """FastAPI app with security headers middleware (no SSL)."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    app.add_middleware(SecurityHeadersMiddleware, ssl_enabled=False)
    return app


@pytest.fixture
def app_with_ssl():
    """FastAPI app with security headers middleware (SSL enabled)."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    app.add_middleware(SecurityHeadersMiddleware, ssl_enabled=True)
    return app


def test_headers_present_on_response(app_no_ssl):
    """All security headers must appear on every response."""
    client = TestClient(app_no_ssl)
    response = client.get("/test")
    assert response.status_code == 200

    # CSP
    csp = response.headers.get("content-security-policy", "")
    assert "script-src 'self'" in csp
    assert "default-src 'self'" in csp
    assert "connect-src 'self' ws: wss:" in csp
    # Must NOT have http: or https: in connect-src (data exfiltration risk)
    connect_part = csp.split("connect-src")[1].split(";")[0]
    assert "http:" not in connect_part
    assert "https:" not in connect_part

    # Other headers
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("permissions-policy", "")
    assert response.headers.get("x-permitted-cross-domain-policies") == "none"

    # HSTS must NOT be present without SSL
    assert "strict-transport-security" not in response.headers


def test_hsts_present_with_ssl(app_with_ssl):
    """HSTS header must appear when SSL is enabled."""
    client = TestClient(app_with_ssl)
    response = client.get("/test")
    assert response.status_code == 200

    hsts = response.headers.get("strict-transport-security", "")
    assert "max-age=31536000" in hsts
    # Must NOT have includeSubDomains (LAN app uses IPs)
    assert "includeSubDomains" not in hsts


def test_headers_on_404(app_no_ssl):
    """Security headers must appear even on error responses."""
    client = TestClient(app_no_ssl)
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in response.headers


def test_headers_on_post(app_no_ssl):
    """Security headers must appear on POST responses too."""
    client = TestClient(app_no_ssl)
    response = client.post("/test")  # Will be 405 Method Not Allowed
    assert response.headers.get("x-frame-options") == "DENY"
