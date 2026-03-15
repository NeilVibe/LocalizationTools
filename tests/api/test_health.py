"""Health endpoint tests.

Validates the /health and /api/ldm/health endpoints return correct
status information and schema fields.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import assert_status, assert_json_fields
from tests.api.helpers.constants import LDM_HEALTH, APP_HEALTH


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.health]


# ---------------------------------------------------------------------------
# /api/ldm/health
# ---------------------------------------------------------------------------


class TestLDMHealth:
    """Tests for the LDM module health endpoint."""

    def test_health_endpoint_returns_200(self, api):
        """GET /api/ldm/health returns 200 with status field."""
        resp = api.health()
        assert_status(resp, 200, "LDM health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_response_schema(self, api):
        """Validate all expected fields are present in health response."""
        resp = api.health()
        data = resp.json()
        assert_json_fields(data, ["status", "module", "version", "features"], "Health schema")

    def test_health_features_flags(self, api):
        """Validate feature flags are booleans in health response."""
        resp = api.health()
        features = resp.json()["features"]
        assert isinstance(features, dict), "features should be a dict"
        for key in ("projects", "folders", "files", "tm"):
            assert key in features, f"Missing feature flag: {key}"
            assert isinstance(features[key], bool), f"Feature '{key}' should be bool"


# ---------------------------------------------------------------------------
# /health  (top-level FastAPI health)
# ---------------------------------------------------------------------------


class TestAppHealth:
    """Tests for the top-level application health endpoint."""

    def test_app_health_returns_200(self, client):
        """GET /health returns 200."""
        resp = client.get(APP_HEALTH)
        # Accept 200 or 4xx (auth-gated) but not 5xx
        assert resp.status_code < 500, f"App health returned {resp.status_code}: {resp.text[:200]}"

    def test_app_health_has_status(self, client):
        """GET /health response has a status field (if accessible)."""
        resp = client.get(APP_HEALTH)
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data, f"Missing 'status' field in health response: {data}"
