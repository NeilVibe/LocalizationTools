"""
Tests for LDM Health Route

Tests: routes/health.py (1 endpoint)
Coverage target: 71% -> 100%
"""

import pytest


class TestLDMHealth:
    """Test LDM health endpoint."""

    def test_health_check_returns_ok(self, client):
        """GET /api/ldm/health returns status ok."""
        response = client.get("/api/ldm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "LDM (LanguageData Manager)"
        assert "version" in data

    def test_health_check_includes_features(self, client):
        """Health check includes feature flags."""
        response = client.get("/api/ldm/health")

        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        features = data["features"]
        assert features["projects"] is True
        assert features["folders"] is True
        assert features["files"] is True
        assert features["tm"] is True

    def test_health_check_no_auth_required(self, client):
        """Health check does not require authentication."""
        # No auth headers
        response = client.get("/api/ldm/health")
        assert response.status_code == 200
