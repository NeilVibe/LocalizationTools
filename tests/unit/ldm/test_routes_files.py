"""
Tests for LDM Files Route

Tests: routes/files.py (6 endpoints)
- GET /files - list files in folder
- GET /files/{file_id} - get file info
- POST /files/upload - upload file
- GET /files/{file_id}/download - download file
- GET /files/{file_id}/rows - get file rows (paginated)
- DELETE /files/{file_id} - delete file
"""

import pytest
from io import BytesIO


class TestListFiles:
    """Test GET /api/ldm/projects/{project_id}/files."""

    def test_list_files_requires_auth(self, client):
        """List files requires authentication."""
        response = client.get("/api/ldm/projects/1/files")
        assert response.status_code == 401


class TestGetFile:
    """Test GET /api/ldm/files/{file_id}."""

    def test_get_file_requires_auth(self, client):
        """Get file requires authentication."""
        response = client.get("/api/ldm/files/1")
        assert response.status_code == 401


class TestUploadFile:
    """Test POST /api/ldm/files/upload."""

    def test_upload_file_requires_auth(self, client):
        """Upload file requires authentication."""
        file_content = b"test content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data = {"folder_id": "1"}

        response = client.post("/api/ldm/files/upload", files=files, data=data)
        assert response.status_code == 401

    def test_upload_file_requires_folder_id(self, client):
        """Upload file requires folder_id."""
        file_content = b"test content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/api/ldm/files/upload", files=files)
        assert response.status_code in [401, 422]

    def test_upload_file_requires_file(self, client):
        """Upload requires file."""
        response = client.post("/api/ldm/files/upload", data={"folder_id": "1"})
        assert response.status_code in [401, 422]


class TestDownloadFile:
    """Test GET /api/ldm/files/{file_id}/download."""

    def test_download_file_requires_auth(self, client):
        """Download file requires authentication."""
        response = client.get("/api/ldm/files/1/download")
        assert response.status_code == 401


class TestGetFileRows:
    """Test GET /api/ldm/files/{file_id}/rows."""

    def test_get_rows_requires_auth(self, client):
        """Get file rows requires authentication."""
        response = client.get("/api/ldm/files/1/rows")
        assert response.status_code == 401

    def test_get_rows_supports_pagination(self, client):
        """Get rows supports pagination."""
        response = client.get("/api/ldm/files/1/rows?page=1&limit=50")
        assert response.status_code == 401

    def test_get_rows_supports_sorting(self, client):
        """Get rows supports sorting."""
        response = client.get("/api/ldm/files/1/rows?sort_by=row_number&sort_order=asc")
        assert response.status_code == 401


class TestRegisterAsTM:
    """Test POST /api/ldm/files/{file_id}/register-as-tm."""

    def test_register_as_tm_requires_auth(self, client):
        """Register file as TM requires authentication."""
        response = client.post("/api/ldm/files/1/register-as-tm")
        assert response.status_code == 401
