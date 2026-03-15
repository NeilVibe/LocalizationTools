"""
Tests for LDM Folders Route

Tests: routes/folders.py (3 endpoints)
- GET /folders - list folders in project
- POST /folders - create folder
- DELETE /folders/{folder_id} - delete folder

FIX-03: Tests for folder fetch 200 immediately after creation (negative IDs)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import get_folder_repository, get_project_repository

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


class TestListFolders:
    """Test GET /api/ldm/folders."""

    def test_list_folders_requires_auth(self, client):
        """List folders requires authentication."""
        response = client.get("/api/ldm/projects/1/folders")
        assert response.status_code == 401


class TestCreateFolder:
    """Test POST /api/ldm/folders."""

    def test_create_folder_requires_auth(self, client):
        """Create folder requires authentication."""
        response = client.post("/api/ldm/folders", json={
            "name": "New Folder",
            "project_id": 1
        })
        assert response.status_code == 401

    def test_create_folder_requires_name(self, client):
        """Create folder requires name."""
        response = client.post("/api/ldm/folders", json={
            "project_id": 1
        })
        assert response.status_code in [401, 422]

    def test_create_folder_requires_project_id(self, client):
        """Create folder requires project_id."""
        response = client.post("/api/ldm/folders", json={
            "name": "New Folder"
        })
        assert response.status_code in [401, 422]

    def test_create_folder_accepts_parent_id(self, client):
        """Create folder accepts optional parent_id."""
        response = client.post("/api/ldm/folders", json={
            "name": "Subfolder",
            "project_id": 1,
            "parent_id": 1
        })
        assert response.status_code == 401


class TestDeleteFolder:
    """Test DELETE /api/ldm/folders/{folder_id}."""

    def test_delete_folder_requires_auth(self, client):
        """Delete folder requires authentication."""
        response = client.delete("/api/ldm/folders/1")
        assert response.status_code == 401


# =============================================================================
# FIX-03: Create-Then-Get with Negative IDs
# =============================================================================

class TestCreateThenGet:
    """FIX-03: Verify folder fetch returns 200 immediately after creation."""

    def test_create_then_get(self):
        """
        FIX-03: Creating a folder then immediately fetching its contents
        returns 200, even with negative IDs used by SQLite offline mode.
        """
        # Simulate a negative ID folder (SQLite offline pattern)
        negative_id = -123456789
        created_folder = {
            "id": negative_id,
            "name": "New Folder",
            "project_id": 1,
            "parent_id": None,
            "created_at": "2026-01-01T00:00:00",
        }
        folder_with_contents = {
            "id": negative_id,
            "name": "New Folder",
            "project_id": 1,
            "parent_id": None,
            "subfolders": [],
            "files": [],
        }

        mock_folder_repo = MagicMock()
        mock_folder_repo.create = AsyncMock(return_value=created_folder)
        mock_folder_repo.get_with_contents = AsyncMock(return_value=folder_with_contents)
        mock_folder_repo.get = AsyncMock(return_value=created_folder)

        mock_project_repo = MagicMock()
        mock_project_repo.get = AsyncMock(return_value={
            "id": 1,
            "name": "Test Project",
            "owner_id": 1,
        })

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
        fastapi_app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo
        fastapi_app.dependency_overrides[get_project_repository] = lambda: mock_project_repo

        try:
            client = TestClient(wrapped_app)

            # Step 1: Create folder
            response = client.post("/api/ldm/folders", json={
                "name": "New Folder",
                "project_id": 1,
            })
            assert response.status_code == 200
            data = response.json()
            folder_id = data["id"]
            assert folder_id == negative_id, "Folder should have negative ID"

            # Step 2: Immediately GET the folder contents
            response = client.get(f"/api/ldm/folders/{folder_id}")
            assert response.status_code == 200, f"FIX-03: GET after create returned {response.status_code}"
            contents = response.json()
            assert contents["id"] == negative_id
            assert contents["name"] == "New Folder"
            assert contents["subfolders"] == []
            assert contents["files"] == []
        finally:
            fastapi_app.dependency_overrides.clear()

    def test_get_nonexistent_folder_returns_404(self):
        """GET for non-existent folder returns 404."""
        mock_folder_repo = MagicMock()
        mock_folder_repo.get_with_contents = AsyncMock(return_value=None)

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
        fastapi_app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo

        try:
            client = TestClient(wrapped_app)
            response = client.get("/api/ldm/folders/99999")
            assert response.status_code == 404
        finally:
            fastapi_app.dependency_overrides.clear()
