"""
Tests for category field in list_rows response.

Phase 16 Plan 01: Category Clustering
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import (
    get_row_repository,
    get_file_repository,
)

# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app

MOCK_USER = {
    "user_id": 1,
    "username": "testuser",
    "role": "user",
    "is_active": True,
    "dev_mode": False,
}


@pytest.fixture
def mock_repos():
    """Mock auth + repositories for rows endpoint testing."""
    mock_row_repo = AsyncMock()
    mock_file_repo = AsyncMock()

    async def override_get_user():
        return MOCK_USER

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_row_repo
    fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_file_repo

    yield mock_row_repo, mock_file_repo

    fastapi_app.dependency_overrides.clear()


class TestRowsResponseIncludesCategory:
    """Test that GET /api/ldm/files/{id}/rows returns category field."""

    def test_rows_include_category_field(self, mock_repos):
        mock_row_repo, mock_file_repo = mock_repos

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

        client = TestClient(wrapped_app)
        response = client.get("/api/ldm/files/1/rows")

        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) == 1
        assert data["rows"][0]["category"] == "Item"

    def test_category_populated_for_known_prefixes(self, mock_repos):
        mock_row_repo, mock_file_repo = mock_repos

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

        client = TestClient(wrapped_app)
        response = client.get("/api/ldm/files/1/rows")

        assert response.status_code == 200
        rows = response.json()["rows"]
        assert rows[0]["category"] == "Item"
        assert rows[1]["category"] == "Character"
        assert rows[2]["category"] == "Quest"
