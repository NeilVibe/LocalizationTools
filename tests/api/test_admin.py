"""Admin, platform, settings, and capabilities API tests.

Covers admin health/stats, platform CRUD, project-platform assignment,
platform access management, capabilities management, settings endpoints,
and authorization enforcement.
"""
from __future__ import annotations

import time

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
    assert_list_response,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.admin]


# ======================================================================
# Health / Overview
# ======================================================================


class TestAdminHealth:
    """Admin health and overview endpoints."""

    def test_admin_health(self, api):
        """GET /health returns top-level app health."""
        resp = api.admin_health()
        assert_status_ok(resp, "App health")
        data = resp.json()
        assert isinstance(data, dict)

    def test_ldm_health(self, api):
        """GET /api/ldm/health returns LDM subsystem health."""
        resp = api.health()
        assert_status_ok(resp, "LDM health")
        data = resp.json()
        assert isinstance(data, dict)

    def test_health_response_fields(self, api):
        """Health response contains expected fields."""
        resp = api.health()
        assert_status_ok(resp)
        data = resp.json()
        # Should have at least status indicator
        assert len(data) > 0, "Health response is empty"

    def test_admin_health_no_500(self, api):
        """App health endpoint never returns 500."""
        resp = api.admin_health()
        assert resp.status_code != 500, (
            f"Health endpoint returned 500: {resp.text[:300]}"
        )

    def test_ldm_health_no_500(self, api):
        """LDM health endpoint never returns 500."""
        resp = api.health()
        assert resp.status_code != 500, (
            f"LDM health returned 500: {resp.text[:300]}"
        )

    def test_health_response_time(self, api):
        """Health endpoint responds within reasonable time."""
        import time as _t
        start = _t.monotonic()
        resp = api.health()
        elapsed = _t.monotonic() - start
        assert elapsed < 10.0, f"Health endpoint took {elapsed:.1f}s (too slow)"
        assert_status_ok(resp)


# ======================================================================
# Platforms
# ======================================================================


class TestPlatforms:
    """Platform CRUD and management."""

    def test_list_platforms(self, api):
        """GET /api/ldm/platforms returns platform list."""
        resp = api.list_platforms()
        assert_status_ok(resp, "List platforms")
        data = resp.json()
        assert "platforms" in data or isinstance(data, list)

    def test_create_platform(self, api):
        """POST /api/ldm/platforms creates a new platform."""
        name = f"TestPlatform-{int(time.time())}"
        resp = api.create_platform(name, description="E2E test platform")
        assert resp.status_code in (200, 201), (
            f"Create platform failed: {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert "id" in data
        platform_id = data["id"]

        # Cleanup
        api.delete_platform(platform_id, permanent=True)

    def test_get_platform(self, api):
        """GET /api/ldm/platforms/{id} returns platform details."""
        name = f"GetPlatform-{int(time.time())}"
        create_resp = api.create_platform(name)
        if create_resp.status_code not in (200, 201):
            pytest.skip("Platform creation failed")
        pid = create_resp.json()["id"]

        resp = api.get_platform(pid)
        assert_status_ok(resp, "Get platform")
        data = resp.json()
        assert data["id"] == pid
        assert data["name"] == name

        api.delete_platform(pid, permanent=True)

    def test_update_platform(self, api):
        """PATCH /api/ldm/platforms/{id} updates platform."""
        name = f"UpdatePlatform-{int(time.time())}"
        create_resp = api.create_platform(name)
        if create_resp.status_code not in (200, 201):
            pytest.skip("Platform creation failed")
        pid = create_resp.json()["id"]

        new_name = f"Updated-{int(time.time())}"
        resp = api.update_platform(pid, name=new_name)
        assert_status_ok(resp, "Update platform")
        assert resp.json()["name"] == new_name

        api.delete_platform(pid, permanent=True)

    def test_delete_platform(self, api):
        """DELETE /api/ldm/platforms/{id} removes platform."""
        name = f"DeletePlatform-{int(time.time())}"
        create_resp = api.create_platform(name)
        if create_resp.status_code not in (200, 201):
            pytest.skip("Platform creation failed")
        pid = create_resp.json()["id"]

        resp = api.delete_platform(pid, permanent=True)
        assert_status_ok(resp, "Delete platform")

        # Verify gone
        get_resp = api.get_platform(pid)
        assert get_resp.status_code == 404

    def test_assign_project_to_platform(self, api, test_project_id):
        """PATCH /api/ldm/projects/{id}/platform assigns project."""
        name = f"AssignPlatform-{int(time.time())}"
        create_resp = api.create_platform(name)
        if create_resp.status_code not in (200, 201):
            pytest.skip("Platform creation failed")
        pid = create_resp.json()["id"]

        resp = api.assign_project_to_platform(test_project_id, pid)
        assert_status_ok(resp, "Assign project to platform")

        # Unassign
        api.assign_project_to_platform(test_project_id, None)
        api.delete_platform(pid, permanent=True)

    def test_get_nonexistent_platform(self, api):
        """GET /api/ldm/platforms/999999 returns 404."""
        resp = api.get_platform(999999)
        assert resp.status_code == 404


# ======================================================================
# Capabilities (Admin)
# ======================================================================


class TestCapabilities:
    """Admin capabilities management."""

    def test_list_available_capabilities(self, api):
        """GET /api/ldm/admin/capabilities/available returns capability types."""
        resp = api.list_available_capabilities()
        assert_status_ok(resp, "List available capabilities")
        data = resp.json()
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
        assert len(data["capabilities"]) > 0, "No capabilities available"

    def test_list_all_capabilities(self, api):
        """GET /api/ldm/admin/capabilities returns all grants."""
        resp = api.list_all_capabilities()
        assert_status_ok(resp, "List all capabilities")
        data = resp.json()
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)

    def test_list_user_capabilities(self, api):
        """GET /api/ldm/admin/capabilities/user/{id} returns user caps."""
        # Get admin user ID first
        me_resp = api.get_me()
        if me_resp.status_code != 200:
            pytest.skip("Cannot get current user")
        user_id = me_resp.json().get("user_id", me_resp.json().get("id", 1))

        resp = api.list_user_capabilities(user_id)
        assert_status_ok(resp, "List user capabilities")
        data = resp.json()
        assert "capabilities" in data

    def test_capabilities_response_schema(self, api):
        """Capabilities list has expected structure."""
        resp = api.list_available_capabilities()
        if resp.status_code != 200:
            pytest.skip("Capabilities endpoint not available")
        data = resp.json()
        for cap in data["capabilities"]:
            assert "name" in cap, f"Capability missing 'name': {cap}"
            assert "description" in cap, f"Capability missing 'description': {cap}"


# ======================================================================
# Settings
# ======================================================================


class TestSettings:
    """Settings / embedding engine endpoints."""

    def test_get_embedding_engines(self, api):
        """GET /api/ldm/settings/embedding-engines lists engines."""
        resp = api.list_embedding_engines()
        assert_status_ok(resp, "List embedding engines")
        data = resp.json()
        assert isinstance(data, list)

    def test_get_current_embedding_engine(self, api):
        """GET /api/ldm/settings/embedding-engine returns current engine."""
        resp = api.get_current_embedding_engine()
        assert_status_ok(resp, "Get current engine")
        data = resp.json()
        assert "current_engine" in data

    def test_settings_response_schema(self, api):
        """Settings endpoint returns well-structured response."""
        resp = api.get_current_embedding_engine()
        if resp.status_code != 200:
            pytest.skip("Engine endpoint not available")
        data = resp.json()
        assert_json_fields(data, ["current_engine", "engine_name"], "EmbeddingEngine")


# ======================================================================
# Authorization Enforcement
# ======================================================================


class TestAdminAuthorization:
    """Verify admin endpoints require authentication."""

    def test_admin_requires_auth(self, client):
        """Admin capabilities endpoint without auth returns 401/403."""
        resp = client.get("/api/ldm/admin/capabilities/available")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {resp.status_code}"
        )

    def test_admin_capabilities_requires_auth(self, client):
        """Admin capabilities list without auth returns 401/403."""
        resp = client.get("/api/ldm/admin/capabilities")
        assert resp.status_code in (401, 403)

    def test_admin_endpoints_no_500(self, api):
        """Batch check: no admin-related endpoint returns 500."""
        endpoints = [
            ("/api/ldm/admin/capabilities/available", "GET"),
            ("/api/ldm/admin/capabilities", "GET"),
            ("/api/ldm/platforms", "GET"),
            ("/api/ldm/settings/embedding-engines", "GET"),
            ("/api/ldm/settings/embedding-engine", "GET"),
            ("/api/ldm/maintenance/sync-status", "GET"),
            ("/health", "GET"),
            ("/api/ldm/health", "GET"),
        ]
        failures = []
        for url, method in endpoints:
            if method == "GET":
                resp = api._get(url)
            else:
                resp = api._post(url)
            if resp.status_code == 500:
                failures.append(f"{method} {url} -> 500: {resp.text[:200]}")

        assert not failures, f"Endpoints returning 500:\n" + "\n".join(failures)
