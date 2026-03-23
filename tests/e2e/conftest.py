"""
Shared fixtures for E2E tests.

Mirrors the API test fixtures (client, auth, project, APIClient) so that
E2E tests can use the same typed wrapper without duplicating setup logic.
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from server.main import app


# ---------------------------------------------------------------------------
# Core client / auth
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Create a TestClient for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, str]:
    """Authenticate as admin and return bearer-token headers."""
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    raise RuntimeError(
        f"Admin login failed. Last response: {response.status_code} "
        f"{response.text[:300]}"
    )


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_project_id(client: TestClient, auth_headers: dict[str, str]):
    """Create a dedicated test project; delete it on teardown."""
    resp = client.post(
        "/api/ldm/projects",
        headers=auth_headers,
        json={"name": "E2E-LangData-Test", "description": "Language data E2E tests"},
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.text}"
    project_id: int = resp.json()["id"]

    yield project_id

    client.delete(
        f"/api/ldm/projects/{project_id}",
        headers=auth_headers,
        params={"permanent": True},
    )


# ---------------------------------------------------------------------------
# Typed API client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api(client: TestClient, auth_headers: dict[str, str]):
    """Return an APIClient instance pre-configured with auth."""
    from tests.api.helpers.api_client import APIClient

    return APIClient(client=client, auth_headers=auth_headers)
