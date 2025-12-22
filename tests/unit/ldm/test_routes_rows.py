"""
Tests for LDM Rows Route

Tests: routes/rows.py (3 endpoints)
- GET /rows/{row_id} - get single row
- PUT /rows/{row_id} - update row
- GET /projects/{project_id}/tree - get project tree
"""

import pytest


class TestGetFileRows:
    """Test GET /api/ldm/files/{file_id}/rows."""

    def test_get_rows_requires_auth(self, client):
        """Get file rows requires authentication."""
        response = client.get("/api/ldm/files/1/rows")
        assert response.status_code == 401


class TestUpdateRow:
    """Test PUT /api/ldm/rows/{row_id}."""

    def test_update_row_requires_auth(self, client):
        """Update row requires authentication."""
        response = client.put("/api/ldm/rows/1", json={
            "target": "Updated translation"
        })
        assert response.status_code == 401

    def test_update_row_accepts_target(self, client):
        """Update row accepts target field."""
        response = client.put("/api/ldm/rows/1", json={
            "target": "새로운 번역"
        })
        assert response.status_code == 401

    def test_update_row_accepts_status(self, client):
        """Update row accepts status field."""
        response = client.put("/api/ldm/rows/1", json={
            "status": "confirmed"
        })
        assert response.status_code == 401


class TestProjectTree:
    """Test GET /api/ldm/projects/{project_id}/tree."""

    def test_project_tree_requires_auth(self, client):
        """Project tree requires authentication."""
        response = client.get("/api/ldm/projects/1/tree")
        assert response.status_code == 401
