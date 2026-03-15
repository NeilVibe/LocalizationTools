"""
Tests for category filtering on rows endpoint.

Phase 16 Plan 01: Category Clustering
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from server.main import app


def _make_row(id: int, row_num: int, string_id: str, source: str = "src",
              target: str = "tgt", status: str = "pending"):
    return {
        "id": id, "file_id": 1, "row_num": row_num,
        "string_id": string_id, "source": source, "target": target,
        "status": status, "updated_at": None, "qa_checked_at": None,
        "qa_flag_count": 0, "translation_source": None,
    }


# Sample rows for filtering tests
MIXED_ROWS = [
    _make_row(1, 1, "SID_ITEM_001_NAME", source="Sword"),
    _make_row(2, 2, "SID_ITEM_002_NAME", source="Shield"),
    _make_row(3, 3, "SID_CHAR_001_DESC", source="Hero"),
    _make_row(4, 4, "SID_QUEST_001_NAME", source="Find the key"),
    _make_row(5, 5, "SID_SKILL_001_NAME", source="Fireball"),
    _make_row(6, 6, "SID_ITEM_003_NAME", source="Potion", status="approved"),
    _make_row(7, 7, "SID_CHAR_002_NAME", source="Villain", status="approved"),
]


@pytest.fixture
def mock_auth_and_repos():
    """Mock auth + repositories for rows endpoint testing."""
    mock_user = {"user_id": 1, "username": "testuser", "is_admin": False}
    mock_row_repo = AsyncMock()
    mock_file_repo = AsyncMock()

    with (
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
        mock_file_repo.get = AsyncMock(return_value={"id": 1, "name": "test.xml"})
        yield mock_user, mock_row_repo, mock_file_repo


class TestSingleCategoryFilter:
    """Test ?category=Item returns only Item rows."""

    def test_filter_single_category(self, mock_auth_and_repos):
        _, mock_row_repo, _ = mock_auth_and_repos
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(list(MIXED_ROWS), len(MIXED_ROWS))
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows?category=Item",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return Item rows (3 items)
        assert data["total"] == 3
        for row in data["rows"]:
            assert row["category"] == "Item"


class TestMultiCategoryFilter:
    """Test ?category=Item,Character returns both."""

    def test_filter_multi_category(self, mock_auth_and_repos):
        _, mock_row_repo, _ = mock_auth_and_repos
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(list(MIXED_ROWS), len(MIXED_ROWS))
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows?category=Item,Character",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        # 3 Item + 2 Character = 5
        assert data["total"] == 5
        categories = {row["category"] for row in data["rows"]}
        assert categories == {"Item", "Character"}


class TestCategoryFilterCombinedWithSearch:
    """Test category filter combined with search."""

    def test_category_with_search(self, mock_auth_and_repos):
        _, mock_row_repo, _ = mock_auth_and_repos
        # Simulate search already filtered on backend
        search_results = [
            _make_row(1, 1, "SID_ITEM_001_NAME", source="Sword"),
            _make_row(3, 3, "SID_CHAR_001_DESC", source="Sword Master"),
        ]
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(search_results, len(search_results))
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows?search=sword&category=Item",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        # Only Item rows from search results
        assert data["total"] == 1
        assert data["rows"][0]["category"] == "Item"


class TestCategoryFilterCombinedWithStatus:
    """Test category filter combined with status filter."""

    def test_category_with_status(self, mock_auth_and_repos):
        _, mock_row_repo, _ = mock_auth_and_repos
        # Simulate status filter already applied on backend
        confirmed_rows = [
            _make_row(6, 6, "SID_ITEM_003_NAME", source="Potion", status="approved"),
            _make_row(7, 7, "SID_CHAR_002_NAME", source="Villain", status="approved"),
        ]
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(confirmed_rows, len(confirmed_rows))
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows?category=Item&filter=confirmed",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["rows"][0]["category"] == "Item"


class TestCategoryFilterNoMatches:
    """Test category filter with no matches returns empty."""

    def test_no_matches(self, mock_auth_and_repos):
        _, mock_row_repo, _ = mock_auth_and_repos
        mock_row_repo.get_for_file = AsyncMock(
            return_value=(list(MIXED_ROWS), len(MIXED_ROWS))
        )

        client = TestClient(app)
        response = client.get(
            "/api/ldm/files/1/rows?category=Region",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["rows"] == []
