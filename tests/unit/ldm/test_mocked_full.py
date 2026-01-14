"""
Full Mocked Tests for LDM Routes

P10: Uses Repository Pattern mocking - mocks at the repository level, not DB level.

Pattern:
    OLD: Mock db.execute() → complex, brittle, tied to SQLAlchemy internals
    NEW: Mock repo.get() → clean, matches interface, abstraction-aware

This file tests routes by mocking repository factory functions.
Repositories are mocked to return predefined data without DB access.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async

# Repository factory imports - we override these
from server.repositories.factory import (
    get_project_repository,
    get_file_repository,
    get_folder_repository,
    get_row_repository,
    get_tm_repository,
    get_platform_repository,
    get_qa_repository,
    get_trash_repository,
    get_capability_repository,
)

# The app from main.py is wrapped with Socket.IO (ASGIApp)
# Get the original FastAPI app for dependency_overrides
fastapi_app = wrapped_app.other_asgi_app


# =============================================================================
# FIXTURES - Fake Data (now as dicts, matching repository return format)
# =============================================================================

@pytest.fixture
def mock_user():
    """Fake authenticated user."""
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
def sample_project():
    """Fake project dict (matching repository return format)."""
    return {
        "id": 1,
        "name": "Test Project",
        "description": "Test description",
        "owner_id": 1,
        "platform_id": None,
        "is_restricted": False,
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
        "updated_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def sample_tm():
    """Fake TM dict (matching repository return format)."""
    return {
        "id": 1,
        "name": "Test TM",
        "description": "Test TM description",
        "source_lang": "ko",
        "target_lang": "en",
        "entry_count": 100,
        "status": "ready",
        "owner_id": 1,
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
        "updated_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def sample_tm_entry():
    """Fake TM entry dict."""
    return {
        "id": 1,
        "tm_id": 1,
        "source_text": "안녕하세요",
        "target_text": "Hello",
        "string_id": "STR_001",
        "is_confirmed": False,
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
        "updated_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def sample_folder():
    """Fake folder dict."""
    return {
        "id": 1,
        "name": "Test Folder",
        "project_id": 1,
        "parent_id": None,
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def sample_file():
    """Fake file dict."""
    return {
        "id": 1,
        "name": "test.txt",
        "original_filename": "test.txt",
        "format": "txt",
        "project_id": 1,
        "folder_id": 1,
        "row_count": 10,
        "source_language": "ko",
        "target_language": "en",
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
        "updated_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


@pytest.fixture
def sample_row():
    """Fake row dict."""
    return {
        "id": 1,
        "file_id": 1,
        "row_num": 1,
        "source": "소스 텍스트",
        "target": "Target text",
        "string_id": "STR_001",
        "status": "pending",
        "is_locked": False,
        "locked_by": None,
        "updated_by": None,
        "created_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
        "updated_at": datetime(2025, 1, 1, 0, 0, 0).isoformat(),
    }


# =============================================================================
# MOCK REPOSITORY FIXTURES
# =============================================================================

@pytest.fixture
def mock_project_repo():
    """Mock ProjectRepository with all methods as AsyncMock."""
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.get_accessible = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=None)
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=False)
    repo.rename = AsyncMock(return_value=None)
    repo.check_name_exists = AsyncMock(return_value=False)
    repo.generate_unique_name = AsyncMock(side_effect=lambda name, *args: name)
    repo.get_with_stats = AsyncMock(return_value=None)
    repo.count = AsyncMock(return_value=0)
    repo.search = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_file_repo():
    """Mock FileRepository with all methods as AsyncMock (matching interface)."""
    repo = MagicMock()
    # Core CRUD
    repo.get = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_project = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=None)
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=False)
    repo.get_rows = AsyncMock(return_value={"rows": [], "total": 0})
    repo.rename = AsyncMock(return_value=None)
    repo.check_name_exists = AsyncMock(return_value=False)
    # Handle both positional and keyword args for generate_unique_name
    repo.generate_unique_name = AsyncMock(
        side_effect=lambda *args, **kwargs: kwargs.get('base_name') or (args[0] if args else "test.txt")
    )
    # Additional methods from interface
    repo.move = AsyncMock(return_value=None)
    repo.copy = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=[])
    repo.get_for_folder = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_folder_repo():
    """Mock FolderRepository with all methods as AsyncMock."""
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_project = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=None)
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=False)
    repo.rename = AsyncMock(return_value=None)
    repo.check_name_exists = AsyncMock(return_value=False)
    repo.generate_unique_name = AsyncMock(side_effect=lambda name, *args, **kwargs: name)
    # Additional methods from interface
    repo.get_with_contents = AsyncMock(return_value={"subfolders": [], "files": []})
    repo.move = AsyncMock(return_value=None)
    repo.move_cross_project = AsyncMock(return_value=None)
    repo.copy = AsyncMock(return_value=None)
    repo.get_children = AsyncMock(return_value=[])
    repo.is_descendant = AsyncMock(return_value=False)
    repo.search = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_row_repo():
    """Mock RowRepository with all methods as AsyncMock (matching interface)."""
    repo = MagicMock()
    # Core CRUD
    repo.get = AsyncMock(return_value=None)
    repo.get_with_file = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value={"id": 1})
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=False)
    # Bulk operations
    repo.bulk_create = AsyncMock(return_value=0)
    repo.bulk_update = AsyncMock(return_value=0)
    # Query operations - get_for_file returns Tuple[List, int]
    repo.get_for_file = AsyncMock(return_value=([], 0))
    repo.get_all_for_file = AsyncMock(return_value=[])
    repo.count_for_file = AsyncMock(return_value=0)
    # History
    repo.add_edit_history = AsyncMock(return_value=None)
    repo.get_edit_history = AsyncMock(return_value=[])
    # Similarity search
    repo.suggest_similar = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_tm_repo():
    """Mock TMRepository with all methods as AsyncMock (matching interface)."""
    repo = MagicMock()
    # Core CRUD
    repo.get = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.get_accessible = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=None)
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=False)
    # TM Entries
    repo.get_entries = AsyncMock(return_value=[])  # Returns List, not dict
    repo.search_entries = AsyncMock(return_value=[])  # For search queries
    repo.add_entry = AsyncMock(return_value=None)
    repo.add_entries_bulk = AsyncMock(return_value=0)
    repo.update_entry = AsyncMock(return_value=None)
    repo.delete_entry = AsyncMock(return_value=False)
    repo.confirm_entry = AsyncMock(return_value=None)
    repo.bulk_confirm_entries = AsyncMock(return_value=0)
    repo.get_glossary_terms = AsyncMock(return_value=[])
    # Search
    repo.search_exact = AsyncMock(return_value=None)
    repo.search_similar = AsyncMock(return_value=[])
    # Tree/Assignment
    repo.get_tree = AsyncMock(return_value=[])
    repo.assign = AsyncMock(return_value=None)
    repo.unassign = AsyncMock(return_value=None)
    repo.activate = AsyncMock(return_value=None)
    repo.deactivate = AsyncMock(return_value=None)
    repo.get_assignment = AsyncMock(return_value=None)
    repo.get_for_scope = AsyncMock(return_value=[])
    repo.get_active_for_file = AsyncMock(return_value=[])
    # TM Linking
    repo.link_to_project = AsyncMock(return_value=None)
    repo.unlink_from_project = AsyncMock(return_value=False)
    repo.get_linked_for_project = AsyncMock(return_value=None)
    repo.get_all_linked_for_project = AsyncMock(return_value=[])
    # Index operations
    repo.get_indexes = AsyncMock(return_value=[])
    repo.count_entries = AsyncMock(return_value=0)
    repo.get_sync_status = AsyncMock(return_value={"is_stale": False, "db_entry_count": 0})
    return repo


@pytest.fixture
def mock_capability_repo():
    """Mock CapabilityRepository with all methods as AsyncMock."""
    repo = MagicMock()
    repo.get_user_capability = AsyncMock(return_value=True)  # Allow by default in tests
    repo.grant_capability = AsyncMock(return_value=None)
    repo.revoke_capability = AsyncMock(return_value=None)
    repo.get_user_capabilities = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_trash_repo():
    """Mock TrashRepository with all methods as AsyncMock (matching interface)."""
    repo = MagicMock()
    # Query operations
    repo.get = AsyncMock(return_value=None)
    repo.get_for_user = AsyncMock(return_value=[])
    repo.get_expired = AsyncMock(return_value=[])
    # Write operations
    repo.create = AsyncMock(return_value={"id": 1, "item_type": "project", "item_id": 1})
    repo.restore = AsyncMock(return_value=None)
    repo.permanent_delete = AsyncMock(return_value=True)
    repo.empty_for_user = AsyncMock(return_value=0)
    repo.cleanup_expired = AsyncMock(return_value=0)
    # Utility
    repo.count_for_user = AsyncMock(return_value=0)
    return repo


# =============================================================================
# CLIENT FIXTURE - Sets up dependency overrides
# =============================================================================

@pytest.fixture
def client_with_repos(
    mock_user,
    mock_project_repo,
    mock_file_repo,
    mock_folder_repo,
    mock_row_repo,
    mock_tm_repo,
    mock_capability_repo,
    mock_trash_repo
):
    """
    TestClient with mocked repositories.

    P10: Overrides factory functions to return mock repositories.
    This is the correct abstraction level for testing routes.
    """
    async def override_get_user():
        return mock_user

    # Override auth
    fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user

    # Override repository factories - return our mocks
    fastapi_app.dependency_overrides[get_project_repository] = lambda: mock_project_repo
    fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_file_repo
    fastapi_app.dependency_overrides[get_folder_repository] = lambda: mock_folder_repo
    fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_row_repo
    fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_tm_repo
    fastapi_app.dependency_overrides[get_capability_repository] = lambda: mock_capability_repo
    fastapi_app.dependency_overrides[get_trash_repository] = lambda: mock_trash_repo

    client = TestClient(wrapped_app)
    yield client, {
        "project_repo": mock_project_repo,
        "file_repo": mock_file_repo,
        "folder_repo": mock_folder_repo,
        "row_repo": mock_row_repo,
        "tm_repo": mock_tm_repo,
        "capability_repo": mock_capability_repo,
        "trash_repo": mock_trash_repo,
    }

    fastapi_app.dependency_overrides.clear()


# =============================================================================
# PROJECT TESTS - Using Repository Mocks
# =============================================================================

class TestProjectsMocked:
    """Mocked tests for projects endpoints using Repository Pattern."""

    def test_list_projects_empty(self, client_with_repos):
        """List projects returns empty list when no projects."""
        client, repos = client_with_repos
        repos["project_repo"].get_accessible.return_value = []

        response = client.get("/api/ldm/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client_with_repos, sample_project):
        """List projects returns project list."""
        client, repos = client_with_repos
        repos["project_repo"].get_accessible.return_value = [sample_project]

        response = client.get("/api/ldm/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Project"

    def test_create_project_valid(self, client_with_repos, sample_project):
        """Create project with valid data."""
        client, repos = client_with_repos
        repos["project_repo"].create.return_value = sample_project

        response = client.post("/api/ldm/projects", json={
            "name": "New Project",
            "description": "New project description",
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Test Project"  # Returns what repo.create returns
        assert data["id"] == 1

    def test_create_project_missing_name(self, client_with_repos):
        """Create project fails without name."""
        client, repos = client_with_repos

        response = client.post("/api/ldm/projects", json={})
        assert response.status_code == 422

    def test_get_project_exists(self, client_with_repos, sample_project):
        """Get existing project returns project."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project

        response = client.get("/api/ldm/projects/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Project"

    def test_get_project_not_found(self, client_with_repos):
        """Get non-existent project returns 404."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = None

        response = client.get("/api/ldm/projects/99999")
        assert response.status_code == 404

    def test_delete_project_exists(self, client_with_repos, sample_project):
        """Delete existing project succeeds."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["project_repo"].delete.return_value = True

        response = client.delete("/api/ldm/projects/1")
        assert response.status_code == 200


# =============================================================================
# TM CRUD TESTS - Using Repository Mocks
# =============================================================================

class TestTMCrudMocked:
    """Mocked tests for TM CRUD endpoints using Repository Pattern."""

    def test_list_tms_empty(self, client_with_repos):
        """List TMs returns empty list."""
        client, repos = client_with_repos
        repos["tm_repo"].get_all.return_value = []

        response = client.get("/api/ldm/tm")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tms_with_data(self, client_with_repos, sample_tm):
        """List TMs returns TM list."""
        client, repos = client_with_repos
        repos["tm_repo"].get_all.return_value = [sample_tm]

        response = client.get("/api/ldm/tm")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test TM"

    def test_get_tm_exists(self, client_with_repos, sample_tm):
        """Get existing TM returns TM."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm

        response = client.get("/api/ldm/tm/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test TM"

    def test_get_tm_not_found(self, client_with_repos):
        """Get non-existent TM returns 404."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = None

        response = client.get("/api/ldm/tm/99999")
        assert response.status_code == 404

    def test_delete_tm_exists(self, client_with_repos, sample_tm):
        """Delete existing TM succeeds."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].delete.return_value = True

        response = client.delete("/api/ldm/tm/1")
        assert response.status_code == 200


# =============================================================================
# TM ENTRIES TESTS - Using Repository Mocks
# =============================================================================

class TestTMEntriesMocked:
    """Mocked tests for TM entries endpoints using Repository Pattern."""

    def test_list_entries_paginated(self, client_with_repos, sample_tm, sample_tm_entry):
        """List entries returns paginated results."""
        client, repos = client_with_repos
        # Set TM with entry_count for pagination
        sample_tm_with_count = {**sample_tm, "entry_count": 1}
        repos["tm_repo"].get.return_value = sample_tm_with_count
        # get_entries returns a List, not a dict
        repos["tm_repo"].get_entries.return_value = [sample_tm_entry]

        response = client.get("/api/ldm/tm/1/entries?page=1&limit=50")
        assert response.status_code == 200

    def test_list_entries_with_search(self, client_with_repos, sample_tm, sample_tm_entry):
        """List entries with search filter."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        # search uses search_entries, not get_entries
        repos["tm_repo"].search_entries.return_value = [sample_tm_entry]

        response = client.get("/api/ldm/tm/1/entries?search=hello")
        assert response.status_code == 200

    def test_add_entry_valid(self, client_with_repos, sample_tm, sample_tm_entry):
        """Add entry with valid data."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].add_entry.return_value = sample_tm_entry

        response = client.post("/api/ldm/tm/1/entries", data={
            "source_text": "새로운 텍스트",
            "target_text": "New text"
        })
        assert response.status_code in [200, 201]

    def test_update_entry_valid(self, client_with_repos, sample_tm, sample_tm_entry):
        """Update entry with valid data."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].update_entry.return_value = sample_tm_entry

        response = client.put("/api/ldm/tm/1/entries/1", json={
            "target_text": "Updated translation"
        })
        assert response.status_code == 200

    def test_delete_entry_exists(self, client_with_repos, sample_tm):
        """Delete existing entry succeeds."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].delete_entry.return_value = True

        response = client.delete("/api/ldm/tm/1/entries/1")
        assert response.status_code == 200

    def test_confirm_entry(self, client_with_repos, sample_tm, sample_tm_entry):
        """Confirm entry succeeds."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        confirmed_entry = {**sample_tm_entry, "is_confirmed": True}
        repos["tm_repo"].confirm_entry.return_value = confirmed_entry

        response = client.post("/api/ldm/tm/1/entries/1/confirm")
        assert response.status_code == 200


# =============================================================================
# TM SEARCH TESTS - Using Repository Mocks
# =============================================================================

class TestTMSearchMocked:
    """Mocked tests for TM search endpoints using Repository Pattern."""

    def test_search_exact_found(self, client_with_repos, sample_tm, sample_tm_entry):
        """Exact search finds match."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].search_exact.return_value = sample_tm_entry

        response = client.get("/api/ldm/tm/1/search/exact?source=hello")
        assert response.status_code == 200

    def test_search_exact_not_found(self, client_with_repos, sample_tm):
        """Exact search returns empty when no match."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].search_exact.return_value = None

        response = client.get("/api/ldm/tm/1/search/exact?source=nonexistent")
        # Returns 200 with null/empty result
        assert response.status_code == 200


# =============================================================================
# FILES TESTS - Using Repository Mocks
# =============================================================================

class TestFilesMocked:
    """Mocked tests for files endpoints using Repository Pattern."""

    def test_list_files_empty(self, client_with_repos, sample_project):
        """List files returns empty list."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["file_repo"].get_by_project.return_value = []

        response = client.get("/api/ldm/projects/1/files")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_file_exists(self, client_with_repos, sample_file):
        """Get existing file returns file info."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file

        response = client.get("/api/ldm/files/1")
        assert response.status_code == 200
        assert response.json()["name"] == "test.txt"

    def test_get_file_not_found(self, client_with_repos):
        """Get file returns 404 when file not found."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = None

        response = client.get("/api/ldm/files/99999")
        assert response.status_code == 404

    def test_get_file_rows_paginated(self, client_with_repos, sample_file, sample_row):
        """Get file rows returns paginated results."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file
        # get_for_file returns Tuple[List, int]
        repos["row_repo"].get_for_file.return_value = ([sample_row], 1)

        response = client.get("/api/ldm/files/1/rows?page=1&limit=50")
        assert response.status_code == 200


# =============================================================================
# FOLDERS TESTS - Using Repository Mocks
# =============================================================================

class TestFoldersMocked:
    """Mocked tests for folders endpoints using Repository Pattern."""

    def test_list_folders_empty(self, client_with_repos, sample_project):
        """List folders returns empty list."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["folder_repo"].get_by_project.return_value = []

        response = client.get("/api/ldm/projects/1/folders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_folder_valid(self, client_with_repos, sample_project, sample_folder):
        """Create folder with valid data."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["folder_repo"].create.return_value = sample_folder

        response = client.post("/api/ldm/folders", json={
            "name": "New Folder",
            "project_id": 1
        })
        assert response.status_code in [200, 201]

    def test_create_folder_missing_name(self, client_with_repos):
        """Create folder fails without name."""
        client, repos = client_with_repos

        response = client.post("/api/ldm/folders", json={
            "project_id": 1
        })
        assert response.status_code == 422

    def test_delete_folder_exists(self, client_with_repos, sample_folder):
        """Delete existing folder succeeds."""
        client, repos = client_with_repos
        repos["folder_repo"].get.return_value = sample_folder
        repos["folder_repo"].delete.return_value = True

        response = client.delete("/api/ldm/folders/1")
        assert response.status_code == 200


# =============================================================================
# ROWS TESTS - Using Repository Mocks
# =============================================================================

class TestRowsMocked:
    """Mocked tests for rows endpoints using Repository Pattern."""

    def test_list_rows_empty(self, client_with_repos, sample_file):
        """List rows returns empty paginated result."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file
        # get_for_file returns Tuple[List, int]
        repos["row_repo"].get_for_file.return_value = ([], 0)

        response = client.get("/api/ldm/files/1/rows")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["rows"] == []

    def test_list_rows_with_data(self, client_with_repos, sample_file, sample_row):
        """List rows returns rows with pagination."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file
        # get_for_file returns Tuple[List, int]
        repos["row_repo"].get_for_file.return_value = ([sample_row], 1)

        response = client.get("/api/ldm/files/1/rows?page=1&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1

    def test_list_rows_with_search(self, client_with_repos, sample_file, sample_row):
        """List rows with search filter."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file
        # get_for_file returns Tuple[List, int]
        repos["row_repo"].get_for_file.return_value = ([sample_row], 1)

        response = client.get("/api/ldm/files/1/rows?search=텍스트")
        assert response.status_code == 200

    def test_list_rows_with_status_filter(self, client_with_repos, sample_file, sample_row):
        """List rows with status filter."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = sample_file
        # get_for_file returns Tuple[List, int]
        repos["row_repo"].get_for_file.return_value = ([sample_row], 1)

        response = client.get("/api/ldm/files/1/rows?status=pending")
        assert response.status_code == 200

    def test_list_rows_file_not_found(self, client_with_repos):
        """List rows returns 404 when file not found."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = None

        response = client.get("/api/ldm/files/99999/rows")
        assert response.status_code == 404

    def test_update_row_target(self, client_with_repos, sample_row):
        """Update row target text succeeds."""
        client, repos = client_with_repos
        # get_with_file returns row with file info for permission check
        repos["row_repo"].get_with_file.return_value = sample_row
        updated_row = {**sample_row, "target": "Updated translation"}
        repos["row_repo"].update.return_value = updated_row

        response = client.put("/api/ldm/rows/1", json={
            "target": "Updated translation"
        })
        assert response.status_code == 200

    def test_update_row_status(self, client_with_repos, sample_row):
        """Update row status succeeds."""
        client, repos = client_with_repos
        # get_with_file returns row with file info for permission check
        repos["row_repo"].get_with_file.return_value = sample_row
        updated_row = {**sample_row, "status": "translated"}
        repos["row_repo"].update.return_value = updated_row

        response = client.put("/api/ldm/rows/1", json={
            "status": "translated"
        })
        assert response.status_code == 200

    def test_update_row_not_found(self, client_with_repos):
        """Update non-existent row returns 404."""
        client, repos = client_with_repos
        # get_with_file returns None when row not found
        repos["row_repo"].get_with_file.return_value = None

        response = client.put("/api/ldm/rows/99999", json={
            "target": "New text"
        })
        assert response.status_code == 404

    def test_get_project_tree(self, client_with_repos, sample_project, sample_folder, sample_file):
        """Get project tree returns folder/file structure."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["row_repo"].get_project_tree.return_value = {
            "project": sample_project,
            "tree": [
                {"type": "folder", **sample_folder, "children": []}
            ]
        }

        response = client.get("/api/ldm/projects/1/tree")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert "tree" in data
        assert data["project"]["name"] == "Test Project"

    def test_get_project_tree_not_found(self, client_with_repos):
        """Get project tree returns 404 when project not found."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = None

        response = client.get("/api/ldm/projects/99999/tree")
        assert response.status_code == 404

    def test_get_project_tree_empty(self, client_with_repos, sample_project):
        """Get project tree with no folders/files returns empty tree."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["row_repo"].get_project_tree.return_value = {
            "project": sample_project,
            "tree": []
        }

        response = client.get("/api/ldm/projects/1/tree")
        assert response.status_code == 200
        data = response.json()
        assert data["tree"] == []


# =============================================================================
# FILES EXTENDED TESTS - Using Repository Mocks
# =============================================================================

class TestFilesExtendedMocked:
    """Extended mocked tests for files endpoints using Repository Pattern."""

    def test_list_files_with_folder_filter(self, client_with_repos, sample_project, sample_file):
        """List files with folder filter."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project
        repos["file_repo"].get_by_project.return_value = [sample_file]

        response = client.get("/api/ldm/projects/1/files?folder_id=1")
        assert response.status_code == 200

    def test_list_files_project_not_found(self, client_with_repos):
        """List files returns 404 when project not found."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = None

        response = client.get("/api/ldm/projects/99999/files")
        assert response.status_code == 404

    def test_upload_unsupported_format(self, client_with_repos, sample_project):
        """Upload file with unsupported format returns 400."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = sample_project

        from io import BytesIO
        fake_file = BytesIO(b"some content")

        response = client.post(
            "/api/ldm/files/upload",
            data={"project_id": "1"},
            files={"file": ("test.pdf", fake_file, "application/pdf")}
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    def test_upload_project_not_found(self, client_with_repos):
        """Upload file returns 404 when project not found."""
        client, repos = client_with_repos
        repos["project_repo"].get.return_value = None

        from io import BytesIO
        fake_file = BytesIO(b"source\ttarget\n")

        response = client.post(
            "/api/ldm/files/upload",
            data={"project_id": "99999"},
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        assert response.status_code == 404

    def test_excel_preview_unsupported_format(self, client_with_repos):
        """Excel preview rejects non-Excel files."""
        client, repos = client_with_repos

        from io import BytesIO
        fake_file = BytesIO(b"some content")

        response = client.post(
            "/api/ldm/files/excel-preview",
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        assert response.status_code == 400
        assert "Excel" in response.json()["detail"]

    def test_download_file_not_found(self, client_with_repos):
        """Download file returns 404 when file not found."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = None

        response = client.get("/api/ldm/files/99999/download")
        assert response.status_code == 404

    def test_register_as_tm_file_not_found(self, client_with_repos):
        """Register as TM returns 404 when file not found."""
        client, repos = client_with_repos
        repos["file_repo"].get.return_value = None

        response = client.post("/api/ldm/files/99999/register-as-tm", json={
            "name": "New TM",
            "language": "en"
        })
        assert response.status_code == 404


# =============================================================================
# TM INDEXES TESTS - Using Repository Mocks
# =============================================================================

class TestTMIndexesMocked:
    """Mocked tests for TM indexes endpoints using Repository Pattern."""

    def test_build_indexes_tm_not_found(self, client_with_repos):
        """Build indexes returns 404 when TM not found."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = None

        response = client.post("/api/ldm/tm/99999/build-indexes")
        assert response.status_code == 404

    def test_get_index_status_tm_not_found(self, client_with_repos):
        """Get index status returns 404 when TM not found."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = None

        response = client.get("/api/ldm/tm/99999/indexes")
        assert response.status_code == 404

    def test_get_index_status_success(self, client_with_repos, sample_tm):
        """Get index status returns index list."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].get_indexes.return_value = [
            {"index_type": "whole", "status": "ready", "file_size": 1024}
        ]

        response = client.get("/api/ldm/tm/1/indexes")
        assert response.status_code == 200
        data = response.json()
        assert data["tm_id"] == 1
        assert "indexes" in data

    def test_get_sync_status_tm_not_found(self, client_with_repos):
        """Get sync status returns 404 when TM not found."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = None

        response = client.get("/api/ldm/tm/99999/sync-status")
        assert response.status_code == 404

    def test_get_sync_status_success(self, client_with_repos, sample_tm):
        """Get sync status returns sync info."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = sample_tm
        repos["tm_repo"].get_sync_status.return_value = {
            "is_stale": False,
            "db_entry_count": 100,
            "indexed_entry_count": 100
        }

        response = client.get("/api/ldm/tm/1/sync-status")
        assert response.status_code == 200
        data = response.json()
        assert data["tm_id"] == 1
        assert "is_stale" in data
        assert "db_entry_count" in data

    def test_sync_indexes_tm_not_found(self, client_with_repos):
        """Sync indexes returns 404 when TM not found."""
        client, repos = client_with_repos
        repos["tm_repo"].get.return_value = None

        response = client.post("/api/ldm/tm/99999/sync")
        assert response.status_code == 404
