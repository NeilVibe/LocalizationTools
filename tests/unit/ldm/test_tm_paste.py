"""
Tests for TM Paste End-to-End Flow (FIX-02)

Tests: TM paste via PATCH /api/ldm/tm/{tm_id}/assign
- Paste TM to platform scope
- Paste TM to project scope
- Paste TM to folder scope
- Paste TM to unassigned (move to root)
- Paste with invalid TM returns 404

The TM paste flow in the frontend (TMExplorerGrid.svelte) uses the assign
endpoint to move/copy TMs between locations in the TM tree. This test suite
verifies the backend API contract that the paste flow depends on.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import get_tm_repository

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


@pytest.fixture
def mock_tm_repo():
    """Mock TMRepository for paste tests."""
    repo = MagicMock()
    repo.get = AsyncMock(return_value={
        "id": 1,
        "name": "Test TM",
        "source_lang": "ko",
        "target_lang": "en",
        "entry_count": 100,
    })
    repo.assign = AsyncMock(return_value={"success": True})
    return repo


@pytest.fixture
def paste_client(mock_tm_repo):
    """TestClient with mocked TM repo and auth."""
    mock_user = {
        "user_id": 1,
        "username": "testuser",
        "role": "user",
        "is_active": True,
        "dev_mode": False,
    }

    async def override_get_user():
        return mock_user

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_tm_repo

    client = TestClient(wrapped_app)
    yield client, mock_tm_repo

    fastapi_app.dependency_overrides.clear()


class TestTMPasteFlow:
    """FIX-02: TM paste end-to-end via PATCH /api/ldm/tm/{tm_id}/assign."""

    def test_paste_tm_to_platform(self, paste_client):
        """Paste TM to platform scope via assign endpoint."""
        client, repo = paste_client

        response = client.patch("/api/ldm/tm/1/assign?platform_id=1")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["platform_id"] == 1
        assert data["project_id"] is None
        assert data["folder_id"] is None

        # Verify repo.assign was called with correct target
        repo.assign.assert_called_once()
        call_args = repo.assign.call_args
        assert call_args[0][0] == 1  # tm_id
        target = call_args[0][1]
        assert target.platform_id == 1
        assert target.project_id is None
        assert target.folder_id is None

    def test_paste_tm_to_project(self, paste_client):
        """Paste TM to project scope via assign endpoint."""
        client, repo = paste_client

        response = client.patch("/api/ldm/tm/1/assign?project_id=5")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == 5

        repo.assign.assert_called_once()
        target = repo.assign.call_args[0][1]
        assert target.project_id == 5

    def test_paste_tm_to_folder(self, paste_client):
        """Paste TM to folder scope via assign endpoint."""
        client, repo = paste_client

        response = client.patch("/api/ldm/tm/1/assign?folder_id=10")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["folder_id"] == 10

        repo.assign.assert_called_once()
        target = repo.assign.call_args[0][1]
        assert target.folder_id == 10

    def test_paste_tm_to_unassigned(self, paste_client):
        """Paste TM to unassigned (no scope params) via assign endpoint."""
        client, repo = paste_client

        response = client.patch("/api/ldm/tm/1/assign")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        # All scope IDs should be None (unassigned)
        assert data["platform_id"] is None
        assert data["project_id"] is None
        assert data["folder_id"] is None

    def test_paste_tm_not_found(self, paste_client):
        """Paste to non-existent TM returns 404."""
        client, repo = paste_client
        repo.get.return_value = None

        response = client.patch("/api/ldm/tm/99999/assign?platform_id=1")
        assert response.status_code == 404

    def test_paste_tm_multiple_scopes_rejected(self, paste_client):
        """Paste with multiple scopes is rejected (400)."""
        client, repo = paste_client

        response = client.patch("/api/ldm/tm/1/assign?platform_id=1&project_id=2")
        assert response.status_code == 400
        assert "Only one scope" in response.json()["detail"]

    def test_paste_tm_requires_auth(self):
        """Paste TM requires authentication (no auth override)."""
        fastapi_app.dependency_overrides.clear()
        client = TestClient(wrapped_app)
        response = client.patch("/api/ldm/tm/1/assign?platform_id=1")
        assert response.status_code == 401
