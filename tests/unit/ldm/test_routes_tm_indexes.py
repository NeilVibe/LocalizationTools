"""
Tests for LDM TM Indexes Route

Tests: routes/tm_indexes.py (4 endpoints)
- POST /tm/{tm_id}/build-indexes - build FAISS indexes
- GET /tm/{tm_id}/indexes - get index info
- GET /tm/{tm_id}/sync-status - get sync status
- POST /tm/{tm_id}/sync - sync DB to indexes
"""

import pytest


class TestBuildIndexes:
    """Test POST /api/ldm/tm/{tm_id}/build-indexes."""

    def test_build_indexes_requires_auth(self, client):
        """Build indexes requires authentication."""
        response = client.post("/api/ldm/tm/1/build-indexes")
        assert response.status_code == 401


class TestGetIndexes:
    """Test GET /api/ldm/tm/{tm_id}/indexes."""

    def test_get_indexes_requires_auth(self, client):
        """Get indexes requires authentication."""
        response = client.get("/api/ldm/tm/1/indexes")
        assert response.status_code == 401


class TestSyncStatus:
    """Test GET /api/ldm/tm/{tm_id}/sync-status."""

    def test_sync_status_requires_auth(self, client):
        """Sync status requires authentication."""
        response = client.get("/api/ldm/tm/1/sync-status")
        assert response.status_code == 401


class TestSync:
    """Test POST /api/ldm/tm/{tm_id}/sync."""

    def test_sync_requires_auth(self, client):
        """Sync requires authentication."""
        response = client.post("/api/ldm/tm/1/sync")
        assert response.status_code == 401
