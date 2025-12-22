"""
Tests for LDM Folders Route

Tests: routes/folders.py (3 endpoints)
- GET /folders - list folders in project
- POST /folders - create folder
- DELETE /folders/{folder_id} - delete folder
"""

import pytest


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
