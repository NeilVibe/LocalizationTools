"""Integration test: CORS auto-lock and cross-IP connectivity in LAN mode."""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


def test_cors_origins_cover_admin_ip():
    """Generated CORS origins must include admin's own IP on all ports."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.35.34.61")

    # Admin FastAPI
    assert "http://10.35.34.61:8888" in origins
    assert "https://10.35.34.61:8888" in origins
    # Admin dashboard
    assert "http://10.35.34.61:8885" in origins
    assert "https://10.35.34.61:8885" in origins
    # Vite dev
    assert "http://10.35.34.61:5173" in origins
    assert "https://10.35.34.61:5173" in origins


def test_cors_origins_cover_electron():
    """Electron app:// origin must always be in the CORS list."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.35.34.61")
    assert "app://." in origins


def test_cors_origins_cover_localhost():
    """Localhost origins must be included (Admin accesses own PC)."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("192.168.1.100")

    assert "http://localhost:5173" in origins
    assert "https://localhost:5173" in origins
    assert "http://localhost:8888" in origins
    assert "https://localhost:8888" in origins
    assert "http://localhost:8885" in origins
    assert "https://localhost:8885" in origins


def test_cors_origins_various_lan_ips():
    """Function should work with any valid LAN IP."""
    from server.config import _build_lan_cors_origins

    for ip in ["10.0.0.1", "192.168.1.100", "172.16.0.50", "10.35.34.61"]:
        origins = _build_lan_cors_origins(ip)
        assert f"http://{ip}:8888" in origins
        assert f"https://{ip}:8888" in origins
        assert "app://." in origins
        assert len(origins) == 13  # 1 electron + 6 localhost + 6 lan_ip


def test_cross_subnet_user_electron_origin():
    """User at 10.35.46.81 sends Origin: app://. — must be allowed by Admin's CORS."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.35.34.61")

    # User's Electron app sends this origin regardless of their IP
    assert "app://." in origins


def test_user_browser_origin_matches_admin_url():
    """Browser accessing http://10.35.34.61:8888 sends Origin: http://10.35.34.61:8888."""
    from server.config import _build_lan_cors_origins
    origins = _build_lan_cors_origins("10.35.34.61")

    # Browser Origin = the URL the user typed = admin's address
    assert "http://10.35.34.61:8888" in origins
    assert "https://10.35.34.61:8888" in origins


def test_fastapi_cors_with_electron_origin():
    """Real FastAPI + CORSMiddleware: request with Origin: app://. must get CORS headers."""
    from server.config import _build_lan_cors_origins

    origins = _build_lan_cors_origins("10.35.34.61")

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)

    # Preflight OPTIONS request with Electron origin
    response = client.options(
        "/health",
        headers={
            "Origin": "app://.",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "app://."

    # Actual GET with Electron origin
    response = client.get("/health", headers={"Origin": "app://."})
    assert response.headers.get("access-control-allow-origin") == "app://."


def test_fastapi_cors_blocks_unknown_origin():
    """Real FastAPI + CORSMiddleware: request from unknown origin must NOT get CORS headers."""
    from server.config import _build_lan_cors_origins

    origins = _build_lan_cors_origins("10.35.34.61")

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)

    # Request from an attacker's origin
    response = client.get("/health", headers={"Origin": "http://evil.com"})
    # CORS should NOT reflect the attacker's origin
    cors_origin = response.headers.get("access-control-allow-origin", "")
    assert cors_origin != "http://evil.com"


def test_fastapi_cors_allows_admin_browser_origin():
    """Real FastAPI: browser accessing admin URL gets proper CORS headers."""
    from server.config import _build_lan_cors_origins

    origins = _build_lan_cors_origins("10.35.34.61")

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "http://10.35.34.61:8888"})
    assert response.headers.get("access-control-allow-origin") == "http://10.35.34.61:8888"
