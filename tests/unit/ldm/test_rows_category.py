"""
Tests for category field in list_rows response.

Phase 16 Plan 01: Category Clustering
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def mock_auth_and_repos():
    """Mock auth + repositories for rows endpoint testing."""
    mock_user = {"user_id": 1, "username": "testuser", "is_admin": False}

    mock_row_repo = AsyncMock()
    mock_file_repo = AsyncMock()

    with (
        patch(
            "server.utils.dependencies.get_current_active_user_async",
            return_value=lambda: mock_user,
        ) as _,
        patch(
            "server.tools.ldm.routes.rows.get_current_active_user_async",
        ) as mock_auth,
        patch(
            "server.tools.ldm.routes.rows.get_row_repository",
        ) as mock_row_dep,
        patch(
            "server.tools.ldm.routes.rows.get_file_repository",
        ) as mock_file_dep,
    ):
        mock_auth.return_value = mock_user
        mock_row_dep.return_value = mock_row_repo
        mock_file_dep.return_value = mock_file_repo
        yield mock_user, mock_row_repo, mock_file_repo


class TestRowsResponseIncludesCategory:
    """Test that GET /api/ldm/files/{id}/rows returns category field."""

    def test_rows_include_category_field(self, mock_auth_and_repos):
        mock_user, mock_row_repo, mock_file_repo = mock_auth_and_repos

        mock_file_repo.get = AsyncMock(return_value={"id": 1, "name": "test.xml"})
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(
                [
                    {
                        "id": 1,
                        "file_id": 1,
                        "row_num": 1,
                        "string_id": "SID_ITEM_001_NAME",
                        "source": "Sword of Dawn",
                        "target": "Sword of Dawn",
                        "status": "pending",
                        "updated_at": None,
                        "qa_checked_at": None,
                        "qa_flag_count": 0,
                        "translation_source": None,
                    }
                ],
                1,
            )
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) == 1
        assert data["rows"][0]["category"] == "Item"

    def test_category_populated_for_known_prefixes(self, mock_auth_and_repos):
        mock_user, mock_row_repo, mock_file_repo = mock_auth_and_repos

        mock_file_repo.get = AsyncMock(return_value={"id": 1, "name": "test.xml"})
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(
                [
                    {
                        "id": 1, "file_id": 1, "row_num": 1,
                        "string_id": "SID_ITEM_001_NAME",
                        "source": "A", "target": "B", "status": "pending",
                        "updated_at": None, "qa_checked_at": None,
                        "qa_flag_count": 0, "translation_source": None,
                    },
                    {
                        "id": 2, "file_id": 1, "row_num": 2,
                        "string_id": "SID_CHAR_005_DESC",
                        "source": "C", "target": "D", "status": "pending",
                        "updated_at": None, "qa_checked_at": None,
                        "qa_flag_count": 0, "translation_source": None,
                    },
                    {
                        "id": 3, "file_id": 1, "row_num": 3,
                        "string_id": "SID_QUEST_010_NAME",
                        "source": "E", "target": "F", "status": "pending",
                        "updated_at": None, "qa_checked_at": None,
                        "qa_flag_count": 0, "translation_source": None,
                    },
                ],
                3,
            )
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        rows = response.json()["rows"]
        assert rows[0]["category"] == "Item"
        assert rows[1]["category"] == "Character"
        assert rows[2]["category"] == "Quest"
