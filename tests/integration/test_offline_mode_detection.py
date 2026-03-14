"""
Mode Detection Logic Validation.

Phase 6, Plan 02: Tests for 3-mode detection logic in factory.py.
Proves OFFL-03 (transparent mode switching) at the factory level.

Modes:
- Offline: Authorization header starts with "Bearer OFFLINE_MODE_"
- Server-local: config.ACTIVE_DATABASE_TYPE == "sqlite"
- PostgreSQL: default when PostgreSQL is available
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from server.repositories.factory import _is_offline_mode, _is_server_local


# =============================================================================
# _is_offline_mode tests
# =============================================================================


class TestIsOfflineMode:
    """Tests for _is_offline_mode header detection."""

    def _make_request(self, auth_header: str | None = None) -> MagicMock:
        """Create a mock Request with optional Authorization header."""
        request = MagicMock()
        headers = {}
        if auth_header is not None:
            headers["Authorization"] = auth_header
        request.headers = headers
        return request

    def test_offline_mode_with_offline_token(self):
        """OFFLINE_MODE_ prefix -> True."""
        request = self._make_request("Bearer OFFLINE_MODE_abc123")
        assert _is_offline_mode(request) is True

    def test_offline_mode_with_regular_jwt(self):
        """Regular JWT token -> False."""
        request = self._make_request("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test")
        assert _is_offline_mode(request) is False

    def test_offline_mode_with_no_header(self):
        """No Authorization header -> False."""
        request = self._make_request()
        assert _is_offline_mode(request) is False

    def test_offline_mode_with_empty_header(self):
        """Empty Authorization header -> False."""
        request = self._make_request("")
        assert _is_offline_mode(request) is False

    def test_offline_mode_without_bearer_prefix(self):
        """OFFLINE_MODE_ without Bearer prefix -> False."""
        request = self._make_request("OFFLINE_MODE_abc123")
        assert _is_offline_mode(request) is False


# =============================================================================
# _is_server_local tests
# =============================================================================


class TestIsServerLocal:
    """Tests for _is_server_local config detection."""

    def test_server_local_when_sqlite(self):
        """ACTIVE_DATABASE_TYPE == 'sqlite' -> True."""
        with patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite"):
            assert _is_server_local() is True

    def test_server_local_when_postgresql(self):
        """ACTIVE_DATABASE_TYPE == 'postgresql' -> False."""
        with patch("server.config.ACTIVE_DATABASE_TYPE", "postgresql"):
            assert _is_server_local() is False


# =============================================================================
# Factory function routing tests
# =============================================================================


class TestFactoryRouting:
    """Tests that factory functions route to correct repository type."""

    def _make_request(self, auth_header: str | None = None) -> MagicMock:
        request = MagicMock()
        headers = {}
        if auth_header is not None:
            headers["Authorization"] = auth_header
        request.headers = headers
        return request

    def test_file_repo_server_local(self):
        """Server-local mode -> SQLiteFileRepository with SchemaMode.SERVER."""
        from server.repositories.factory import get_file_repository
        from server.repositories.sqlite.file_repo import SQLiteFileRepository
        from server.repositories.sqlite.base import SchemaMode

        request = self._make_request("Bearer eyJhbG...")
        with patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite"):
            repo = get_file_repository(request, db=MagicMock(), current_user={"user_id": 1})
            assert isinstance(repo, SQLiteFileRepository)
            assert repo.schema_mode == SchemaMode.SERVER

    def test_file_repo_offline(self):
        """Offline mode -> SQLiteFileRepository with SchemaMode.OFFLINE."""
        from server.repositories.factory import get_file_repository
        from server.repositories.sqlite.file_repo import SQLiteFileRepository
        from server.repositories.sqlite.base import SchemaMode

        request = self._make_request("Bearer OFFLINE_MODE_abc123")
        # Even if config is postgresql, offline header wins
        with patch("server.config.ACTIVE_DATABASE_TYPE", "postgresql"):
            repo = get_file_repository(request, db=MagicMock(), current_user={"user_id": 1})
            assert isinstance(repo, SQLiteFileRepository)
            assert repo.schema_mode == SchemaMode.OFFLINE

    @pytest.mark.parametrize("factory_name,sqlite_class_path", [
        ("get_platform_repository", "server.repositories.sqlite.platform_repo.SQLitePlatformRepository"),
        ("get_project_repository", "server.repositories.sqlite.project_repo.SQLiteProjectRepository"),
        ("get_folder_repository", "server.repositories.sqlite.folder_repo.SQLiteFolderRepository"),
        ("get_file_repository", "server.repositories.sqlite.file_repo.SQLiteFileRepository"),
        ("get_row_repository", "server.repositories.sqlite.row_repo.SQLiteRowRepository"),
        ("get_tm_repository", "server.repositories.sqlite.tm_repo.SQLiteTMRepository"),
        ("get_qa_repository", "server.repositories.sqlite.qa_repo.SQLiteQAResultRepository"),
        ("get_trash_repository", "server.repositories.sqlite.trash_repo.SQLiteTrashRepository"),
        ("get_capability_repository", "server.repositories.sqlite.capability_repo.SQLiteCapabilityRepository"),
    ])
    def test_all_factories_route_to_sqlite_in_server_local(self, factory_name, sqlite_class_path):
        """All 9 factory functions return SQLite repos when in server_local mode."""
        import importlib
        from server.repositories import factory as factory_module

        factory_fn = getattr(factory_module, factory_name)
        request = self._make_request("Bearer eyJhbG...")

        # Import the expected class
        module_path, class_name = sqlite_class_path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        expected_class = getattr(mod, class_name)

        with patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite"):
            repo = factory_fn(request, db=MagicMock(), current_user={"user_id": 1})
            # Row repo wraps in RoutingRowRepository, so check the inner primary
            if factory_name == "get_row_repository":
                from server.repositories.routing.row_repo import RoutingRowRepository
                assert isinstance(repo, RoutingRowRepository)
                assert isinstance(repo._primary, expected_class)
            elif factory_name == "get_capability_repository":
                # Capability repo doesn't take schema_mode param
                assert isinstance(repo, expected_class)
            else:
                assert isinstance(repo, expected_class)

    @pytest.mark.parametrize("factory_name", [
        "get_platform_repository",
        "get_project_repository",
        "get_folder_repository",
        "get_file_repository",
        "get_row_repository",
        "get_tm_repository",
        "get_qa_repository",
        "get_trash_repository",
        "get_capability_repository",
    ])
    def test_all_factories_route_to_sqlite_in_offline(self, factory_name):
        """All 9 factory functions return SQLite repos with OFFLINE mode for offline header."""
        from server.repositories import factory as factory_module
        from server.repositories.sqlite.base import SchemaMode

        factory_fn = getattr(factory_module, factory_name)
        request = self._make_request("Bearer OFFLINE_MODE_xyz")

        with patch("server.config.ACTIVE_DATABASE_TYPE", "postgresql"):
            repo = factory_fn(request, db=MagicMock(), current_user={"user_id": 1})
            # Row repo in offline is plain SQLiteRowRepository (no routing wrapper)
            if factory_name == "get_capability_repository":
                # Capability repo is always a stub in SQLite mode
                from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository
                assert isinstance(repo, SQLiteCapabilityRepository)
            elif factory_name == "get_row_repository":
                from server.repositories.sqlite.row_repo import SQLiteRowRepository
                assert isinstance(repo, SQLiteRowRepository)
                assert repo.schema_mode == SchemaMode.OFFLINE
            else:
                assert repo.schema_mode == SchemaMode.OFFLINE
