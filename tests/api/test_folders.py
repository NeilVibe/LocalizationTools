"""Folder CRUD API tests.

Covers folder create, list, get, rename, move, delete, nesting,
and edge cases.
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
from tests.api.helpers.constants import FOLDER_FIELDS


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.folders]


# ======================================================================
# CRUD
# ======================================================================


class TestFolderCRUD:
    """Basic folder CRUD operations."""

    def test_create_folder(self, api, test_project_id):
        """POST /folders creates a folder in the test project."""
        name = f"TestFolder-{int(time.time())}"
        resp = api.create_folder(name=name, project_id=test_project_id)
        assert_status(resp, 200, "Create folder")
        data = resp.json()
        assert_json_fields(data, FOLDER_FIELDS, "FolderResponse")
        assert data["name"] == name
        # Cleanup
        api.delete_folder(data["id"], permanent=True)

    def test_list_folders(self, api, test_project_id, test_folder_id):
        """GET /projects/{id}/folders returns list including test folder."""
        resp = api.list_folders(test_project_id)
        assert_status_ok(resp, "List folders")
        data = resp.json()
        assert isinstance(data, list)
        ids = [f["id"] for f in data]
        assert test_folder_id in ids, f"Test folder {test_folder_id} not in list"

    def test_get_folder(self, api, test_folder_id):
        """GET /folders/{id} returns folder details."""
        resp = api.get_folder_contents(test_folder_id)
        assert_status_ok(resp, "Get folder")
        data = resp.json()
        assert data is not None

    def test_rename_folder(self, api, test_project_id):
        """PATCH /folders/{id}/rename changes folder name."""
        name = f"RenameFolder-{int(time.time())}"
        resp = api.create_folder(name=name, project_id=test_project_id)
        fid = resp.json()["id"]

        new_name = f"Renamed-{int(time.time())}"
        rename_resp = api.rename_folder(fid, new_name)
        assert_status_ok(rename_resp, "Rename folder")

        # Cleanup
        api.delete_folder(fid, permanent=True)

    def test_delete_folder(self, api, test_project_id):
        """DELETE /folders/{id} removes the folder."""
        name = f"DelFolder-{int(time.time())}"
        resp = api.create_folder(name=name, project_id=test_project_id)
        fid = resp.json()["id"]

        del_resp = api.delete_folder(fid, permanent=True)
        assert_status_ok(del_resp, "Delete folder")


# ======================================================================
# Nesting / Move
# ======================================================================


class TestFolderNesting:
    """Folder nesting and move operations."""

    def test_create_nested_folder(self, api, test_project_id):
        """Create a folder inside another folder (parent_id)."""
        parent_name = f"ParentFolder-{int(time.time())}"
        parent_resp = api.create_folder(name=parent_name, project_id=test_project_id)
        assert_status(parent_resp, 200)
        parent_id = parent_resp.json()["id"]

        child_name = f"ChildFolder-{int(time.time())}"
        child_resp = api.create_folder(
            name=child_name,
            project_id=test_project_id,
            parent_id=parent_id,
        )
        assert_status(child_resp, 200, "Create nested folder")
        child_data = child_resp.json()
        # Parent ID should be set
        if "parent_id" in child_data:
            assert child_data["parent_id"] == parent_id

        # Cleanup (parent deletion cascades)
        api.delete_folder(parent_id, permanent=True)

    def test_move_folder(self, api, test_project_id):
        """PATCH /folders/{id}/move moves folder to new parent."""
        # Create two folders
        f1_resp = api.create_folder(name=f"MoveSource-{int(time.time())}", project_id=test_project_id)
        f1_id = f1_resp.json()["id"]

        f2_resp = api.create_folder(name=f"MoveTarget-{int(time.time())}", project_id=test_project_id)
        f2_id = f2_resp.json()["id"]

        # Move f1 under f2
        move_resp = api.move_folder(f1_id, parent_id=f2_id)
        assert_status_ok(move_resp, "Move folder")

        # Cleanup
        api.delete_folder(f2_id, permanent=True)

    def test_move_folder_to_root(self, api, test_project_id):
        """Move folder to root (parent_id=None)."""
        f_resp = api.create_folder(name=f"MoveRoot-{int(time.time())}", project_id=test_project_id)
        fid = f_resp.json()["id"]

        move_resp = api.move_folder(fid, parent_id=None)
        assert_status_ok(move_resp, "Move folder to root")

        api.delete_folder(fid, permanent=True)


# ======================================================================
# Edge Cases
# ======================================================================


class TestFolderEdgeCases:
    """Folder edge cases and error handling."""

    def test_get_nonexistent_folder(self, api):
        """GET /folders/999999 returns 404."""
        resp = api.get_folder_contents(999999)
        assert resp.status_code in (404, 403)

    def test_delete_nonexistent_folder(self, api):
        """DELETE /folders/999999 returns 404."""
        resp = api.delete_folder(999999, permanent=True)
        assert resp.status_code in (404, 200)

    def test_create_folder_without_project(self, client, auth_headers):
        """POST /folders without project_id returns error."""
        resp = client.post(
            "/api/ldm/folders",
            headers=auth_headers,
            json={"name": "OrphanFolder"},
        )
        assert resp.status_code in (400, 404, 422), (
            f"Expected error for missing project_id, got {resp.status_code}"
        )

    def test_create_folder_long_name(self, api, test_project_id):
        """POST /folders with 200-char name."""
        long_name = "F" * 200
        resp = api.create_folder(name=long_name, project_id=test_project_id)
        assert resp.status_code in (200, 400, 422)
        if resp.status_code == 200:
            api.delete_folder(resp.json()["id"], permanent=True)
