"""
API-level tests for Game Dev merge endpoint.

POST /api/ldm/files/{file_id}/gamedev-merge

Tests:
- Correct change counts for a known diff
- 404 when file has no rows
- 404 when file not found
- 422 when original_content not available
- Valid base64-encoded XML output
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import get_file_repository, get_row_repository
from server.tools.ldm.file_handlers.xml_handler import parse_gamedev_nodes

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "xml"
SAMPLE_XML = FIXTURES_DIR / "gamedev_sample.xml"


def _load_xml_bytes() -> bytes:
    """Load sample XML as bytes."""
    return SAMPLE_XML.read_bytes()


def _load_rows(max_depth: int = 3) -> list[dict]:
    """Parse sample XML into Game Dev rows."""
    root = etree.parse(str(SAMPLE_XML)).getroot()
    rows = parse_gamedev_nodes(root, max_depth=max_depth)
    # Add IDs to simulate DB rows
    for i, row in enumerate(rows):
        row["id"] = i + 1
    return rows


class TestGameDevMergeAPI:
    """Tests for POST /files/{file_id}/gamedev-merge."""

    @pytest.fixture
    def mock_repos(self):
        """Create mock file and row repositories."""
        file_repo = AsyncMock()
        row_repo = AsyncMock()
        return {"file_repo": file_repo, "row_repo": row_repo}

    @pytest.fixture
    def client_with_repos(self, mock_repos):
        """TestClient with mocked repositories."""
        mock_user = {
            "user_id": 1,
            "username": "testuser",
            "role": "admin",
            "is_active": True,
        }

        async def override_get_user():
            return mock_user

        fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
        fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_repos["file_repo"]
        fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_repos["row_repo"]

        client = TestClient(wrapped_app)
        yield client, mock_repos

        fastapi_app.dependency_overrides.clear()

    def test_merge_returns_correct_change_counts(self, client_with_repos):
        """Merge with one modified attribute returns correct counts."""
        client, repos = client_with_repos

        xml_bytes = _load_xml_bytes()
        rows = _load_rows()

        # Modify Iron Sword Value from 150 to 200
        import copy
        modified_rows = copy.deepcopy(rows)
        modified_rows[0]["extra_data"]["attributes"]["Value"] = "200"

        # Setup mocks
        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": {
                "file_type": "gamedev",
                "original_content": base64.b64encode(xml_bytes).decode("ascii"),
            },
        }
        repos["row_repo"].get_all_for_file.return_value = modified_rows
        repos["row_repo"].bulk_update.return_value = 1

        response = client.post("/api/ldm/files/1/gamedev-merge", json={"max_depth": 3})

        assert response.status_code == 200
        data = response.json()
        assert data["changed_nodes"] >= 1
        assert data["modified_attributes"] >= 1
        assert data["total_nodes"] > 0
        assert data["rows_updated"] >= 0
        assert "output_xml" in data

    def test_merge_output_is_valid_base64_xml(self, client_with_repos):
        """Output XML is valid base64-encoded XML."""
        client, repos = client_with_repos

        xml_bytes = _load_xml_bytes()
        rows = _load_rows()

        # Modify one attribute
        import copy
        modified_rows = copy.deepcopy(rows)
        modified_rows[0]["extra_data"]["attributes"]["Value"] = "999"

        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": {
                "file_type": "gamedev",
                "original_content": base64.b64encode(xml_bytes).decode("ascii"),
            },
        }
        repos["row_repo"].get_all_for_file.return_value = modified_rows
        repos["row_repo"].bulk_update.return_value = 1

        response = client.post("/api/ldm/files/1/gamedev-merge", json={"max_depth": 3})

        assert response.status_code == 200
        data = response.json()

        # Decode base64 and parse as XML
        decoded_xml = base64.b64decode(data["output_xml"])
        root = etree.fromstring(decoded_xml)
        assert root is not None
        # Verify the modification was applied
        first_item = root[0]
        assert first_item.get("Value") == "999"

    def test_merge_404_when_no_rows(self, client_with_repos):
        """Returns 404 when file has no rows."""
        client, repos = client_with_repos

        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": {"file_type": "gamedev"},
        }
        repos["row_repo"].get_all_for_file.return_value = []

        response = client.post("/api/ldm/files/1/gamedev-merge", json={})

        assert response.status_code == 404
        assert "No rows" in response.json()["detail"]

    def test_merge_404_when_file_not_found(self, client_with_repos):
        """Returns 404 when file does not exist."""
        client, repos = client_with_repos

        repos["file_repo"].get.return_value = None

        response = client.post("/api/ldm/files/999/gamedev-merge", json={})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_merge_422_when_no_original_content(self, client_with_repos):
        """Returns 422 when original_content is not stored."""
        client, repos = client_with_repos

        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": {"file_type": "gamedev"},
        }
        repos["row_repo"].get_all_for_file.return_value = _load_rows()

        response = client.post("/api/ldm/files/1/gamedev-merge", json={})

        assert response.status_code == 422
        assert "Original XML content not available" in response.json()["detail"]

    def test_merge_unchanged_returns_zero_changes(self, client_with_repos):
        """Merge with unchanged rows returns zero changed_nodes."""
        client, repos = client_with_repos

        xml_bytes = _load_xml_bytes()
        rows = _load_rows()

        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": {
                "file_type": "gamedev",
                "original_content": base64.b64encode(xml_bytes).decode("ascii"),
            },
        }
        repos["row_repo"].get_all_for_file.return_value = rows
        repos["row_repo"].bulk_update.return_value = 0

        response = client.post("/api/ldm/files/1/gamedev-merge", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["changed_nodes"] == 0
        assert data["added_nodes"] == 0
        assert data["removed_nodes"] == 0

    def test_merge_with_string_extra_data(self, client_with_repos):
        """File extra_data stored as JSON string is parsed correctly."""
        client, repos = client_with_repos

        xml_bytes = _load_xml_bytes()
        rows = _load_rows()

        repos["file_repo"].get.return_value = {
            "id": 1,
            "name": "test.xml",
            "extra_data": json.dumps({
                "file_type": "gamedev",
                "original_content": base64.b64encode(xml_bytes).decode("ascii"),
            }),
        }
        repos["row_repo"].get_all_for_file.return_value = rows
        repos["row_repo"].bulk_update.return_value = 0

        response = client.post("/api/ldm/files/1/gamedev-merge", json={})

        assert response.status_code == 200
