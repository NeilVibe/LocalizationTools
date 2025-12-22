"""
Full Mocked Tests for LDM Routes

Uses FastAPI dependency_overrides to properly mock auth and database.
Target: 85% coverage on LDM routes.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from server.main import app as wrapped_app
from server.utils.dependencies import get_async_db, get_current_active_user_async

# The app from main.py is wrapped with Socket.IO (ASGIApp)
# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app


# =============================================================================
# FIXTURES - Fake Data
# =============================================================================

@pytest.fixture
def mock_user():
    """Fake authenticated user - matches server/utils/dependencies._get_dev_user()."""
    return {
        "user_id": 1,
        "username": "testuser",
        "role": "user",
        "is_active": True,
        "dev_mode": False
    }


@pytest.fixture
def mock_admin():
    """Fake admin user."""
    return {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": True,
        "dev_mode": False
    }


@pytest.fixture
def mock_project():
    """Fake project object with all required fields."""
    p = MagicMock()
    p.id = 1
    p.name = "Test Project"
    p.description = "Test description"
    p.source_lang = "ko"
    p.target_lang = "en"
    p.owner_id = 1
    p.created_at = datetime(2025, 1, 1, 0, 0, 0)
    p.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    return p


@pytest.fixture
def mock_tm():
    """Fake TM object with all required fields."""
    tm = MagicMock()
    tm.id = 1
    tm.name = "Test TM"
    tm.description = "Test TM description"
    tm.source_lang = "ko"
    tm.target_lang = "en"
    tm.entry_count = 100
    tm.status = "ready"
    tm.owner_id = 1
    tm.created_at = datetime(2025, 1, 1, 0, 0, 0)
    tm.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    return tm


@pytest.fixture
def mock_tm_entry():
    """Fake TM entry object with all required fields."""
    e = MagicMock()
    e.id = 1
    e.tm_id = 1
    e.source_text = "안녕하세요"
    e.target_text = "Hello"
    e.string_id = "STR_001"
    e.is_confirmed = False
    e.created_at = datetime(2025, 1, 1, 0, 0, 0)
    e.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    e.confirmed_at = None
    e.confirmed_by = None
    # TM relationship for ownership check
    e.tm = MagicMock()
    e.tm.owner_id = 1
    return e


@pytest.fixture
def mock_folder():
    """Fake folder object with all required fields."""
    f = MagicMock()
    f.id = 1
    f.name = "Test Folder"
    f.project_id = 1
    f.created_at = datetime(2025, 1, 1, 0, 0, 0)
    # Project relationship for ownership check
    f.project = MagicMock()
    f.project.owner_id = 1
    return f


@pytest.fixture
def mock_file():
    """Fake file object with all required fields."""
    f = MagicMock()
    f.id = 1
    f.name = "test.txt"
    f.original_filename = "test.txt"
    f.format = "txt"
    f.folder_id = 1
    f.row_count = 10
    f.source_language = "ko"
    f.target_language = "en"
    f.created_at = datetime(2025, 1, 1, 0, 0, 0)
    f.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    # Project relationship for ownership check
    f.project = MagicMock()
    f.project.id = 1
    f.project.owner_id = 1
    return f


@pytest.fixture
def mock_db():
    """Fake async database session with smart refresh."""
    db = AsyncMock()

    # Make refresh populate required fields on the object
    async def smart_refresh(obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = 1
        if not hasattr(obj, 'created_at') or obj.created_at is None:
            obj.created_at = datetime(2025, 1, 1, 0, 0, 0)
        if not hasattr(obj, 'updated_at') or obj.updated_at is None:
            obj.updated_at = datetime(2025, 1, 1, 0, 0, 0)
        # For TM entry fields
        if hasattr(obj, 'tm_id') and (not hasattr(obj, 'string_id') or obj.string_id is None):
            obj.string_id = None
        if hasattr(obj, 'is_confirmed') and obj.is_confirmed is None:
            obj.is_confirmed = False

    db.refresh = AsyncMock(side_effect=smart_refresh)
    return db


@pytest.fixture
def client_with_auth(mock_user, mock_db):
    """TestClient with mocked auth and database."""
    async def override_get_user():
        return mock_user

    async def override_get_db():
        return mock_db

    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
    fastapi_app.dependency_overrides[get_async_db] = override_get_db

    client = TestClient(wrapped_app)
    yield client

    fastapi_app.dependency_overrides.clear()


# =============================================================================
# PROJECT TESTS - Mocked
# =============================================================================

class TestProjectsMocked:
    """Mocked tests for projects endpoints."""

    def test_list_projects_empty(self, client_with_auth, mock_db):
        """List projects returns empty list when no projects."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client_with_auth, mock_db, mock_project):
        """List projects returns project list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_project]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Project"

    def test_create_project_valid(self, client_with_auth, mock_db):
        """Create project with valid data."""
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.post("/api/ldm/projects", json={
            "name": "New Project",
            "description": "New project description",
            "source_lang": "ko",
            "target_lang": "en"
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New Project"
        assert data["id"] == 1

    def test_create_project_missing_name(self, client_with_auth):
        """Create project fails without name."""
        response = client_with_auth.post("/api/ldm/projects", json={
            "source_lang": "ko",
            "target_lang": "en"
        })
        assert response.status_code == 422

    def test_get_project_exists(self, client_with_auth, mock_db, mock_project):
        """Get existing project returns project."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/projects/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Project"

    def test_get_project_not_found(self, client_with_auth, mock_db):
        """Get non-existent project returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/projects/99999")
        assert response.status_code == 404

    def test_delete_project_exists(self, client_with_auth, mock_db, mock_project):
        """Delete existing project succeeds."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.delete("/api/ldm/projects/1")
        assert response.status_code == 200


# =============================================================================
# TM CRUD TESTS - Mocked
# =============================================================================

class TestTMCrudMocked:
    """Mocked tests for TM CRUD endpoints."""

    def test_list_tms_empty(self, client_with_auth, mock_db):
        """List TMs returns empty list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/tm")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tms_with_data(self, client_with_auth, mock_db, mock_tm):
        """List TMs returns TM list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tm]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/tm")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test TM"

    def test_get_tm_exists(self, client_with_auth, mock_db, mock_tm):
        """Get existing TM returns TM."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tm
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/tm/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test TM"

    def test_get_tm_not_found(self, client_with_auth, mock_db):
        """Get non-existent TM returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/tm/99999")
        assert response.status_code == 404

    def test_delete_tm_exists(self, client_with_auth, mock_db, mock_tm):
        """Delete existing TM succeeds."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tm
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.delete("/api/ldm/tm/1")
        assert response.status_code == 200


# =============================================================================
# TM ENTRIES TESTS - Mocked
# =============================================================================

class TestTMEntriesMocked:
    """Mocked tests for TM entries endpoints."""

    def test_list_entries_paginated(self, client_with_auth, mock_db, mock_tm, mock_tm_entry):
        """List entries returns paginated results."""
        # First call: get TM for ownership check
        # Second call: count entries
        # Third call: get entries
        mock_tm_result = MagicMock()
        mock_tm_result.scalar_one_or_none.return_value = mock_tm

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = [mock_tm_entry]

        mock_db.execute = AsyncMock(side_effect=[
            mock_tm_result, mock_count_result, mock_entries_result
        ])

        response = client_with_auth.get("/api/ldm/tm/1/entries?page=1&limit=50")
        assert response.status_code == 200

    def test_list_entries_with_search(self, client_with_auth, mock_db, mock_tm, mock_tm_entry):
        """List entries with search filter."""
        mock_tm_result = MagicMock()
        mock_tm_result.scalar_one_or_none.return_value = mock_tm

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_entries_result = MagicMock()
        mock_entries_result.scalars.return_value.all.return_value = [mock_tm_entry]

        mock_db.execute = AsyncMock(side_effect=[
            mock_tm_result, mock_count_result, mock_entries_result
        ])

        response = client_with_auth.get("/api/ldm/tm/1/entries?search=hello")
        assert response.status_code == 200

    def test_add_entry_valid(self, client_with_auth, mock_db, mock_tm):
        """Add entry with valid data - uses Form data not JSON."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tm
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # This endpoint uses Form data, not JSON
        response = client_with_auth.post("/api/ldm/tm/1/entries", data={
            "source_text": "새로운 텍스트",
            "target_text": "New text"
        })
        assert response.status_code in [200, 201]

    def test_update_entry_valid(self, client_with_auth, mock_db, mock_tm_entry):
        """Update entry with valid data."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tm_entry
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        response = client_with_auth.put("/api/ldm/tm/1/entries/1", json={
            "target_text": "Updated translation"
        })
        assert response.status_code == 200

    def test_delete_entry_exists(self, client_with_auth, mock_db, mock_tm, mock_tm_entry):
        """Delete existing entry succeeds."""
        # First query: get TM for ownership check
        mock_tm_result = MagicMock()
        mock_tm_result.scalar_one_or_none.return_value = mock_tm

        # Second query: get entry
        mock_entry_result = MagicMock()
        mock_entry_result.scalar_one_or_none.return_value = mock_tm_entry

        mock_db.execute = AsyncMock(side_effect=[mock_tm_result, mock_entry_result])
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.delete("/api/ldm/tm/1/entries/1")
        assert response.status_code == 200

    def test_confirm_entry(self, client_with_auth, mock_db, mock_tm_entry):
        """Confirm entry succeeds."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tm_entry
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        response = client_with_auth.post("/api/ldm/tm/1/entries/1/confirm")
        assert response.status_code == 200


# =============================================================================
# TM SEARCH TESTS - Mocked
# =============================================================================

class TestTMSearchMocked:
    """Mocked tests for TM search endpoints."""

    def test_search_exact_found(self, client_with_auth, mock_db, mock_tm, mock_tm_entry):
        """Exact search finds match."""
        mock_tm_result = MagicMock()
        mock_tm_result.scalar_one_or_none.return_value = mock_tm

        mock_entry_result = MagicMock()
        mock_entry_result.scalar_one_or_none.return_value = mock_tm_entry

        mock_db.execute = AsyncMock(side_effect=[mock_tm_result, mock_entry_result])

        response = client_with_auth.get("/api/ldm/tm/1/search/exact?source=hello")
        assert response.status_code == 200

    def test_search_exact_not_found(self, client_with_auth, mock_db, mock_tm):
        """Exact search returns empty when no match."""
        mock_tm_result = MagicMock()
        mock_tm_result.scalar_one_or_none.return_value = mock_tm

        mock_entry_result = MagicMock()
        mock_entry_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_tm_result, mock_entry_result])

        response = client_with_auth.get("/api/ldm/tm/1/search/exact?source=nonexistent")
        # Could be 200 with null or 404 depending on implementation
        assert response.status_code in [200, 404]


# =============================================================================
# FILES TESTS - Mocked
# =============================================================================

class TestFilesMocked:
    """Mocked tests for files endpoints."""

    def test_list_files_empty(self, client_with_auth, mock_db, mock_project):
        """List files returns empty list."""
        # First: project check, Second: files list
        mock_proj_result = MagicMock()
        mock_proj_result.scalar_one_or_none.return_value = mock_project

        mock_files_result = MagicMock()
        mock_files_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_proj_result, mock_files_result])

        response = client_with_auth.get("/api/ldm/projects/1/files")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_file_exists(self, client_with_auth, mock_db, mock_file):
        """Get existing file returns file info."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_file
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client_with_auth.get("/api/ldm/files/1")
        assert response.status_code == 200

    def test_get_file_rows_paginated(self, client_with_auth, mock_db, mock_file):
        """Get file rows returns paginated results."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.row_number = 1
        mock_row.source = "Source text"
        mock_row.target = "Target text"
        mock_row.string_id = "STR_001"
        mock_row.status = "pending"
        mock_row.is_locked = False
        mock_row.locked_by = None
        mock_row.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        # First: file check, Second: count, Third: rows
        mock_file_result = MagicMock()
        mock_file_result.scalar_one_or_none.return_value = mock_file

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_rows_result = MagicMock()
        mock_rows_result.scalars.return_value.all.return_value = [mock_row]

        mock_db.execute = AsyncMock(side_effect=[
            mock_file_result, mock_count_result, mock_rows_result
        ])

        response = client_with_auth.get("/api/ldm/files/1/rows?page=1&limit=50")
        assert response.status_code == 200


# =============================================================================
# FOLDERS TESTS - Mocked
# =============================================================================

class TestFoldersMocked:
    """Mocked tests for folders endpoints."""

    def test_list_folders_empty(self, client_with_auth, mock_db, mock_project):
        """List folders returns empty list."""
        mock_proj_result = MagicMock()
        mock_proj_result.scalar_one_or_none.return_value = mock_project

        mock_folders_result = MagicMock()
        mock_folders_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_proj_result, mock_folders_result])

        response = client_with_auth.get("/api/ldm/projects/1/folders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_folder_valid(self, client_with_auth, mock_db, mock_project):
        """Create folder with valid data."""
        mock_proj_result = MagicMock()
        mock_proj_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute = AsyncMock(return_value=mock_proj_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.post("/api/ldm/folders", json={
            "name": "New Folder",
            "project_id": 1
        })
        assert response.status_code in [200, 201]

    def test_create_folder_missing_name(self, client_with_auth):
        """Create folder fails without name."""
        response = client_with_auth.post("/api/ldm/folders", json={
            "project_id": 1
        })
        assert response.status_code == 422

    def test_delete_folder_exists(self, client_with_auth, mock_db, mock_folder):
        """Delete existing folder succeeds."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_folder
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        response = client_with_auth.delete("/api/ldm/folders/1")
        assert response.status_code == 200
