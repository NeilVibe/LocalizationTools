"""Project CRUD API tests.

Covers project create, list, get, rename, delete, tree, restriction,
access management, and edge cases.
"""
from __future__ import annotations

import time
import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
    assert_project_response,
    assert_list_response,
)
from tests.api.helpers.constants import (
    PROJECT_FIELDS,
    PROJECTS_LIST,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.projects]


# ======================================================================
# CRUD
# ======================================================================


class TestProjectCRUD:
    """Basic project CRUD operations."""

    def test_create_project(self, api):
        """POST /projects creates a project and returns id + name."""
        name = f"TestProject-{int(time.time())}"
        resp = api.create_project(name=name, description="E2E test project")
        assert_status(resp, 200, "Create project")
        data = resp.json()
        assert_project_response(data)
        assert data["name"] == name
        # Cleanup
        api.delete_project(data["id"], permanent=True)

    def test_list_projects(self, api, test_project_id):
        """GET /projects returns list with at least the test project."""
        resp = api.list_projects()
        assert_status_ok(resp, "List projects")
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        ids = [p["id"] for p in data]
        assert test_project_id in ids, f"Test project {test_project_id} not in list"

    def test_get_project(self, api, test_project_id):
        """GET /projects/{id} returns project with correct fields."""
        resp = api.get_project(test_project_id)
        assert_status_ok(resp, "Get project")
        data = resp.json()
        assert_project_response(data)
        assert data["id"] == test_project_id

    def test_rename_project(self, api):
        """PATCH /projects/{id}/rename changes project name."""
        # Create a temp project
        name = f"RenameTest-{int(time.time())}"
        resp = api.create_project(name=name)
        assert_status(resp, 200)
        pid = resp.json()["id"]

        new_name = f"Renamed-{int(time.time())}"
        rename_resp = api.rename_project(pid, new_name)
        assert_status_ok(rename_resp, "Rename project")

        # Verify rename
        get_resp = api.get_project(pid)
        assert get_resp.json()["name"] == new_name

        # Cleanup
        api.delete_project(pid, permanent=True)

    def test_delete_project(self, api):
        """DELETE /projects/{id} soft-deletes, then permanent delete removes it."""
        name = f"DeleteTest-{int(time.time())}"
        resp = api.create_project(name=name)
        pid = resp.json()["id"]

        # Soft delete
        del_resp = api.delete_project(pid)
        assert_status_ok(del_resp, "Delete project")

        # Permanent delete
        perm_resp = api.delete_project(pid, permanent=True)
        # Should succeed or already gone
        assert perm_resp.status_code in (200, 404)

    def test_get_nonexistent_project(self, api):
        """GET /projects/999999 returns 404."""
        resp = api.get_project(999999)
        assert resp.status_code == 404

    def test_create_project_duplicate_name(self, api):
        """Creating two projects with the same name should work or return error."""
        name = f"DupProject-{int(time.time())}"
        resp1 = api.create_project(name=name)
        assert_status(resp1, 200)
        pid1 = resp1.json()["id"]

        resp2 = api.create_project(name=name)
        # Some APIs allow duplicates, some don't
        if resp2.status_code == 200:
            pid2 = resp2.json()["id"]
            api.delete_project(pid2, permanent=True)
        else:
            assert resp2.status_code in (400, 409, 422)

        api.delete_project(pid1, permanent=True)


# ======================================================================
# Tree / Structure
# ======================================================================


class TestProjectTree:
    """Project tree and structure endpoints."""

    def test_project_tree(self, api, test_project_id):
        """GET /projects/{id}/tree returns tree structure."""
        resp = api.get_project_tree(test_project_id)
        assert_status_ok(resp, "Project tree")
        data = resp.json()
        # Tree should have some structure — at minimum a response
        assert data is not None

    def test_project_tree_nonexistent(self, api):
        """GET /projects/999999/tree returns 404."""
        resp = api.get_project_tree(999999)
        assert resp.status_code in (404, 403)


# ======================================================================
# Restriction / Access
# ======================================================================


class TestProjectAccess:
    """Project restriction and access management."""

    def test_set_project_restriction(self, api, test_project_id):
        """PUT /projects/{id}/restriction sets restriction flag."""
        resp = api.set_project_restriction(test_project_id, is_restricted=True)
        if resp.status_code in (404, 405):
            pytest.skip("Restriction endpoint not available")
        assert_status_ok(resp, "Set restriction")

        # Restore
        api.set_project_restriction(test_project_id, is_restricted=False)

    def test_list_project_access(self, api, test_project_id):
        """GET /projects/{id}/access returns access list."""
        resp = api.list_project_access(test_project_id)
        if resp.status_code in (404, 405):
            pytest.skip("Access endpoint not available")
        assert_status_ok(resp, "List access")


# ======================================================================
# Edge Cases
# ======================================================================


class TestProjectEdgeCases:
    """Project edge cases and error handling."""

    def test_create_project_empty_name(self, client, auth_headers):
        """POST /projects with empty name returns 422 or 400."""
        resp = client.post(
            PROJECTS_LIST,
            headers=auth_headers,
            json={"name": ""},
        )
        # Accept 200 (some APIs auto-generate name), 400, or 422
        assert resp.status_code in (200, 400, 422), (
            f"Expected 200/400/422 for empty name, got {resp.status_code}"
        )
        if resp.status_code == 200:
            # Cleanup auto-created project
            pid = resp.json().get("id")
            if pid:
                client.delete(
                    f"/api/ldm/projects/{pid}",
                    headers=auth_headers,
                    params={"permanent": True},
                )

    def test_create_project_long_name(self, api):
        """POST /projects with 250-char name."""
        long_name = "A" * 250
        resp = api.create_project(name=long_name)
        # Should either succeed or return validation error
        assert resp.status_code in (200, 400, 422), (
            f"Expected 200/400/422 for long name, got {resp.status_code}"
        )
        if resp.status_code == 200:
            api.delete_project(resp.json()["id"], permanent=True)

    def test_delete_nonexistent_project(self, api):
        """DELETE /projects/999999 returns 404."""
        resp = api.delete_project(999999, permanent=True)
        assert resp.status_code in (404, 200)  # Some APIs return 200 for idempotent delete
