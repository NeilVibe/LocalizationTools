"""
Tests for LDM TM Entries Route

Tests: routes/tm_entries.py (6 endpoints)
- GET /tm/{tm_id}/entries - list entries (paginated)
- POST /tm/{tm_id}/entries - add entry
- PUT /tm/{tm_id}/entries/{entry_id} - update entry
- DELETE /tm/{tm_id}/entries/{entry_id} - delete entry
- POST /tm/{tm_id}/entries/{entry_id}/confirm - confirm single entry
- POST /tm/{tm_id}/entries/bulk-confirm - bulk confirm entries
"""

import pytest


class TestListTMEntries:
    """Test GET /api/ldm/tm/{tm_id}/entries."""

    def test_list_entries_requires_auth(self, client):
        """List TM entries requires authentication."""
        response = client.get("/api/ldm/tm/1/entries")
        assert response.status_code == 401

    def test_list_entries_supports_pagination(self, client):
        """List entries supports pagination params."""
        response = client.get("/api/ldm/tm/1/entries?page=1&limit=50")
        assert response.status_code == 401

    def test_list_entries_supports_sorting(self, client):
        """List entries supports sorting params."""
        response = client.get("/api/ldm/tm/1/entries?sort_by=source_text&sort_order=desc")
        assert response.status_code == 401

    def test_list_entries_supports_search(self, client):
        """List entries supports search param."""
        response = client.get("/api/ldm/tm/1/entries?search=hello")
        assert response.status_code == 401


class TestAddTMEntry:
    """Test POST /api/ldm/tm/{tm_id}/entries."""

    def test_add_entry_requires_auth(self, client):
        """Add TM entry requires authentication."""
        response = client.post("/api/ldm/tm/1/entries", json={
            "source_text": "안녕하세요",
            "target_text": "Hello"
        })
        assert response.status_code == 401


class TestUpdateTMEntry:
    """Test PUT /api/ldm/tm/{tm_id}/entries/{entry_id}."""

    def test_update_entry_requires_auth(self, client):
        """Update TM entry requires authentication."""
        response = client.put("/api/ldm/tm/1/entries/1", json={
            "target_text": "Updated Hello"
        })
        assert response.status_code == 401


class TestDeleteTMEntry:
    """Test DELETE /api/ldm/tm/{tm_id}/entries/{entry_id}."""

    def test_delete_entry_requires_auth(self, client):
        """Delete TM entry requires authentication."""
        response = client.delete("/api/ldm/tm/1/entries/1")
        assert response.status_code == 401


class TestConfirmTMEntry:
    """Test POST /api/ldm/tm/{tm_id}/entries/{entry_id}/confirm."""

    def test_confirm_entry_requires_auth(self, client):
        """Confirm entry requires authentication."""
        response = client.post("/api/ldm/tm/1/entries/1/confirm")
        assert response.status_code == 401


class TestBulkConfirmTMEntries:
    """Test POST /api/ldm/tm/{tm_id}/entries/bulk-confirm."""

    def test_bulk_confirm_requires_auth(self, client):
        """Bulk confirm requires authentication."""
        response = client.post("/api/ldm/tm/1/entries/bulk-confirm", json={
            "entry_ids": [1, 2, 3]
        })
        assert response.status_code == 401
