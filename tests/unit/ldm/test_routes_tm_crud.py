"""
Tests for LDM TM CRUD Route

Tests: routes/tm_crud.py (5 endpoints)
- GET /tm - list TMs
- GET /tm/{id} - get single TM
- POST /tm/upload - upload TM file
- DELETE /tm/{id} - delete TM
- GET /tm/{id}/export - export TM

FIX-01: Tests for offline TM visibility in online TM tree
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO
from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import get_tm_repository


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


# =============================================================================
# FIX-01: Offline TM Visibility in Online TM Tree
# =============================================================================

# Get the FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


class TestOfflineTMInTree:
    """FIX-01: Verify offline TMs appear alongside online TMs in the tree."""

    def test_offline_tm_in_tree(self):
        """
        FIX-01: TM tree endpoint merges offline TMs from SQLite
        into the online PostgreSQL tree, so users see both.
        """
        # Mock the primary (online) TM repo
        mock_online_repo = MagicMock()
        mock_online_repo.get_tree = AsyncMock(return_value={
            "unassigned": [
                {"tm_id": 1, "tm_name": "Online TM", "entry_count": 50}
            ],
            "platforms": [
                {
                    "id": 1,
                    "name": "Main Platform",
                    "tms": [],
                    "projects": [
                        {
                            "id": 1,
                            "name": "Project A",
                            "tms": [{"tm_id": 2, "tm_name": "Project TM", "entry_count": 100}],
                            "folders": []
                        }
                    ]
                }
            ]
        })

        # Mock the offline SQLite TM repo
        mock_offline_tree = {
            "unassigned": [
                {"tm_id": -1, "tm_name": "Offline TM", "entry_count": 25}
            ],
            "platforms": [
                {
                    "id": -1,
                    "name": "Offline Storage",
                    "tms": [],
                    "projects": [
                        {
                            "id": -1,
                            "name": "Offline Storage",
                            "tms": [{"tm_id": -2, "tm_name": "Offline Project TM", "entry_count": 30}],
                            "folders": []
                        }
                    ]
                }
            ]
        }

        mock_user = {
            "user_id": 1,
            "username": "testuser",
            "role": "user",
            "is_active": True,
            "dev_mode": False,
        }

        async def override_get_user():
            return mock_user

        fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_online_repo

        try:
            with patch(
                "server.repositories.factory._is_offline_mode", return_value=False
            ), patch(
                "server.repositories.factory._is_server_local", return_value=False
            ), patch(
                "server.repositories.sqlite.tm_repo.SQLiteTMRepository"
            ) as mock_sqlite_cls:
                mock_offline_repo = MagicMock()
                mock_offline_repo.get_tree = AsyncMock(return_value=mock_offline_tree)
                mock_sqlite_cls.return_value = mock_offline_repo

                client = TestClient(wrapped_app)
                response = client.get("/api/ldm/tm-tree")

                assert response.status_code == 200
                data = response.json()

                # Verify merged tree has both online and offline unassigned TMs
                unassigned_names = [tm["tm_name"] for tm in data["unassigned"]]
                assert "Online TM" in unassigned_names, "Online TM missing from tree"
                assert "Offline TM" in unassigned_names, "Offline TM missing from tree (FIX-01)"

                # Verify platforms include offline storage
                platform_names = [p["name"] for p in data["platforms"]]
                assert "Main Platform" in platform_names
                assert "Offline Storage" in platform_names, "Offline Storage platform missing (FIX-01)"

                # Verify offline TMs in projects
                offline_platform = next(p for p in data["platforms"] if p["name"] == "Offline Storage")
                offline_project = offline_platform["projects"][0]
                offline_tm_names = [tm["tm_name"] for tm in offline_project["tms"]]
                assert "Offline Project TM" in offline_tm_names, "Offline project TM missing (FIX-01)"
        finally:
            fastapi_app.dependency_overrides.clear()

    def test_tree_merge_helper_combines_platforms(self):
        """Test _merge_tm_trees merges platforms by name correctly."""
        from server.tools.ldm.routes.tm_assignment import _merge_tm_trees

        primary = {
            "unassigned": [{"tm_id": 1, "tm_name": "A"}],
            "platforms": [
                {
                    "name": "Shared Platform",
                    "tms": [{"tm_id": 2, "tm_name": "B"}],
                    "projects": [
                        {"name": "Project X", "tms": [], "folders": []}
                    ]
                }
            ]
        }
        offline = {
            "unassigned": [{"tm_id": -1, "tm_name": "C"}],
            "platforms": [
                {
                    "name": "Shared Platform",
                    "tms": [{"tm_id": -2, "tm_name": "D"}],
                    "projects": [
                        {"name": "Offline Project", "tms": [{"tm_id": -3, "tm_name": "E"}], "folders": []}
                    ]
                }
            ]
        }

        merged = _merge_tm_trees(primary, offline)

        # Unassigned merged
        assert len(merged["unassigned"]) == 2
        names = {tm["tm_name"] for tm in merged["unassigned"]}
        assert names == {"A", "C"}

        # Shared platform merged (not duplicated)
        assert len(merged["platforms"]) == 1
        platform = merged["platforms"][0]
        assert platform["name"] == "Shared Platform"

        # Platform TMs merged
        platform_tm_names = {tm["tm_name"] for tm in platform["tms"]}
        assert platform_tm_names == {"B", "D"}

        # Projects include both
        project_names = {p["name"] for p in platform["projects"]}
        assert "Project X" in project_names
        assert "Offline Project" in project_names
