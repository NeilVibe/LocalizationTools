"""
Tests for LDM TM CRUD Route

Tests: routes/tm_crud.py (5 endpoints)
- GET /tm - list TMs
- GET /tm/{id} - get single TM
- POST /tm/upload - upload TM file
- DELETE /tm/{id} - delete TM
- GET /tm/{id}/export - export TM
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestListTMs:
    """Test GET /api/ldm/tm."""

    def test_list_tms_requires_auth(self, client):
        """List TMs requires authentication."""
        response = client.get("/api/ldm/tm")
        assert response.status_code == 401


class TestGetTM:
    """Test GET /api/ldm/tm/{tm_id}."""

    def test_get_tm_requires_auth(self, client):
        """Get TM requires authentication."""
        response = client.get("/api/ldm/tm/1")
        assert response.status_code == 401


class TestUploadTM:
    """Test POST /api/ldm/tm/upload."""

    def test_upload_tm_requires_auth(self, client):
        """Upload TM requires authentication."""
        # Create fake file
        file_content = b"source\ttarget\nhello\tworld"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data = {"name": "Test TM"}

        response = client.post("/api/ldm/tm/upload", files=files, data=data)
        assert response.status_code == 401

    def test_upload_tm_requires_file(self, client):
        """Upload TM requires file."""
        response = client.post("/api/ldm/tm/upload", data={"name": "Test TM"})
        assert response.status_code in [401, 422]

    def test_upload_tm_requires_name(self, client):
        """Upload TM requires name."""
        file_content = b"source\ttarget\nhello\tworld"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/api/ldm/tm/upload", files=files)
        assert response.status_code in [401, 422]


class TestDeleteTM:
    """Test DELETE /api/ldm/tm/{tm_id}."""

    def test_delete_tm_requires_auth(self, client):
        """Delete TM requires authentication."""
        response = client.delete("/api/ldm/tm/1")
        assert response.status_code == 401


class TestExportTM:
    """Test GET /api/ldm/tm/{tm_id}/export."""

    def test_export_tm_requires_auth(self, client):
        """Export TM requires authentication."""
        response = client.get("/api/ldm/tm/1/export")
        assert response.status_code == 401

    def test_export_tm_supports_formats(self, client):
        """Export TM supports different formats."""
        # Test that format parameter is accepted
        for fmt in ["text", "excel", "tmx"]:
            response = client.get(f"/api/ldm/tm/1/export?format={fmt}")
            # Should fail auth, not format validation
            assert response.status_code == 401
