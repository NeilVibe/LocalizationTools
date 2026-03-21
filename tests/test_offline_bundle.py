"""
Offline Bundle Factory/Repository Audit + Smoke Tests.

OFFLINE-04: Verifies all 9 factory functions produce correct SQLite repos
            in both OFFLINE and SERVER-LOCAL modes.
OFFLINE-05: Smoke tests verifying no service hard-depends on PostgreSQL,
            embedding engine handles light mode, media converter doesn't crash.

All tests run WITHOUT PostgreSQL, Electron, or network access.
"""
from __future__ import annotations

import os
import glob
import ast
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from loguru import logger

# ============================================================================
# Imports under test
# ============================================================================
from server.repositories.factory import (
    _is_offline_mode,
    _is_server_local,
    get_tm_repository,
    get_file_repository,
    get_row_repository,
    get_project_repository,
    get_folder_repository,
    get_platform_repository,
    get_qa_repository,
    get_trash_repository,
    get_capability_repository,
)
from server.repositories.sqlite.base import SchemaMode

# SQLite repo classes for isinstance checks
from server.repositories.sqlite.tm_repo import SQLiteTMRepository
from server.repositories.sqlite.file_repo import SQLiteFileRepository
from server.repositories.sqlite.row_repo import SQLiteRowRepository
from server.repositories.sqlite.project_repo import SQLiteProjectRepository
from server.repositories.sqlite.folder_repo import SQLiteFolderRepository
from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository
from server.repositories.sqlite.trash_repo import SQLiteTrashRepository
from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository

# Routing wrapper for row repo
from server.repositories.routing.row_repo import RoutingRowRepository


# ============================================================================
# Helpers
# ============================================================================

def _make_offline_request() -> MagicMock:
    """Create a mock Request with OFFLINE_MODE_ auth header."""
    req = MagicMock()
    req.headers = {"Authorization": "Bearer OFFLINE_MODE_test_token"}
    return req


def _make_normal_request() -> MagicMock:
    """Create a mock Request with a normal JWT auth header."""
    req = MagicMock()
    req.headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"}
    return req


def _make_no_auth_request() -> MagicMock:
    """Create a mock Request with no Authorization header."""
    req = MagicMock()
    req.headers = {}
    return req


def _mock_db() -> MagicMock:
    """Dummy AsyncSession."""
    return MagicMock()


def _mock_user() -> dict:
    """Dummy current_user."""
    return {"id": 1, "username": "test_user", "is_admin": False}


# ============================================================================
# A) MODE DETECTION TESTS
# ============================================================================

class TestModeDetection:
    """Tests for _is_offline_mode and _is_server_local."""

    def test_is_offline_mode_with_offline_header(self):
        req = _make_offline_request()
        assert _is_offline_mode(req) is True

    def test_is_offline_mode_with_normal_header(self):
        req = _make_normal_request()
        assert _is_offline_mode(req) is False

    def test_is_offline_mode_with_no_header(self):
        req = _make_no_auth_request()
        assert _is_offline_mode(req) is False

    def test_is_offline_mode_with_partial_match(self):
        """Bearer OFFLINE_ (no MODE) should NOT match."""
        req = MagicMock()
        req.headers = {"Authorization": "Bearer OFFLINE_abc"}
        assert _is_offline_mode(req) is False

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_is_server_local_sqlite(self):
        assert _is_server_local() is True

    @patch("server.config.ACTIVE_DATABASE_TYPE", "postgresql")
    def test_is_server_local_postgresql(self):
        assert _is_server_local() is False


# ============================================================================
# B) FACTORY AUDIT -- OFFLINE MODE (all 9 repos)
# ============================================================================

class TestFactoryOfflineMode:
    """All 9 factory functions must return SQLite repos with SchemaMode.OFFLINE."""

    def setup_method(self):
        self.request = _make_offline_request()
        self.db = _mock_db()
        self.user = _mock_user()

    def test_tm_repository_offline(self):
        repo = get_tm_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteTMRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_file_repository_offline(self):
        repo = get_file_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteFileRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_row_repository_offline(self):
        repo = get_row_repository(self.request, self.db, self.user)
        # In offline mode, it's a direct SQLiteRowRepository (no routing wrapper)
        assert isinstance(repo, SQLiteRowRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_project_repository_offline(self):
        repo = get_project_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteProjectRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_folder_repository_offline(self):
        repo = get_folder_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteFolderRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_platform_repository_offline(self):
        repo = get_platform_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLitePlatformRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_qa_repository_offline(self):
        repo = get_qa_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteQAResultRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_trash_repository_offline(self):
        repo = get_trash_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteTrashRepository)
        assert repo.schema_mode == SchemaMode.OFFLINE

    def test_capability_repository_offline(self):
        repo = get_capability_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteCapabilityRepository)
        # Capability repo is a stub -- no schema_mode attribute
        assert not hasattr(repo, "schema_mode")


# ============================================================================
# C) FACTORY AUDIT -- SERVER-LOCAL SQLite MODE (all 9 repos)
# ============================================================================

class TestFactoryServerLocalMode:
    """All 9 factory functions in server-local SQLite mode (config == 'sqlite')."""

    def setup_method(self):
        self.request = _make_normal_request()
        self.db = _mock_db()
        self.user = _mock_user()

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_tm_repository_server_local(self):
        repo = get_tm_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteTMRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_file_repository_server_local(self):
        repo = get_file_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteFileRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_row_repository_server_local(self):
        repo = get_row_repository(self.request, self.db, self.user)
        # In server-local mode, row repo is wrapped in RoutingRowRepository
        assert isinstance(repo, RoutingRowRepository)
        # The inner primary repo should be SQLiteRowRepository with SERVER mode
        assert isinstance(repo._primary, SQLiteRowRepository)
        assert repo._primary.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_project_repository_server_local(self):
        repo = get_project_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteProjectRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_folder_repository_server_local(self):
        repo = get_folder_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteFolderRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_platform_repository_server_local(self):
        repo = get_platform_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLitePlatformRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_qa_repository_server_local(self):
        repo = get_qa_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteQAResultRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_trash_repository_server_local(self):
        repo = get_trash_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteTrashRepository)
        assert repo.schema_mode == SchemaMode.SERVER

    @patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")
    def test_capability_repository_server_local(self):
        repo = get_capability_repository(self.request, self.db, self.user)
        assert isinstance(repo, SQLiteCapabilityRepository)
        # Capability repo is always a stub in SQLite modes -- no schema_mode
        assert not hasattr(repo, "schema_mode")


# ============================================================================
# D) SMOKE TESTS -- App works without PostgreSQL
# ============================================================================

class TestOfflineSmoke:
    """Verify no service hard-depends on PostgreSQL drivers."""

    def test_no_pg_imports_in_ldm_services(self):
        """Scan all .py files in server/tools/ldm/services/ for direct psycopg2/asyncpg imports.

        Services MUST go through repositories -- never import PostgreSQL drivers directly.
        """
        services_dir = os.path.join(
            os.path.dirname(__file__), "..", "server", "tools", "ldm", "services"
        )
        services_dir = os.path.normpath(services_dir)

        py_files = glob.glob(os.path.join(services_dir, "**", "*.py"), recursive=True)
        assert len(py_files) > 0, f"No .py files found in {services_dir}"

        violations = []
        pg_modules = {"psycopg2", "asyncpg", "psycopg"}

        for filepath in py_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=filepath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_module = alias.name.split(".")[0]
                        if root_module in pg_modules:
                            violations.append(
                                f"{os.path.relpath(filepath)}: import {alias.name} (line {node.lineno})"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        root_module = node.module.split(".")[0]
                        if root_module in pg_modules:
                            violations.append(
                                f"{os.path.relpath(filepath)}: from {node.module} import ... (line {node.lineno})"
                            )

        assert violations == [], (
            f"Services must not directly import PostgreSQL drivers:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_embedding_engine_light_mode(self):
        """is_light_mode() must return a bool without crashing."""
        from server.tools.shared.embedding_engine import is_light_mode

        # Reset cache so it re-evaluates
        import server.tools.shared.embedding_engine as ee
        original = ee._light_mode
        try:
            ee._light_mode = None
            result = is_light_mode()
            assert isinstance(result, bool)
            logger.info(f"is_light_mode() returned {result}")
        finally:
            ee._light_mode = original

    def test_media_converter_vgmstream_search(self):
        """MediaConverter._find_vgmstream() must not crash (returns Path or None)."""
        from server.tools.ldm.services.media_converter import MediaConverter

        converter = MediaConverter()
        result = converter._find_vgmstream()
        assert result is None or hasattr(result, "exists"), (
            f"Expected Path or None, got {type(result)}"
        )
        logger.info(f"_find_vgmstream() returned {result}")

    def test_schema_mode_enum_values(self):
        """SchemaMode enum must have exactly OFFLINE and SERVER values."""
        modes = {m.value for m in SchemaMode}
        assert modes == {"offline", "server"}

    def test_sqlite_base_table_mapping(self):
        """TABLE_MAP must cover all 10 base table names."""
        from server.repositories.sqlite.base import TABLE_MAP

        expected_tables = {
            "platforms", "projects", "folders", "files", "rows",
            "tms", "tm_entries", "tm_assignments", "qa_results", "trash",
        }
        assert set(TABLE_MAP.keys()) == expected_tables

    def test_sqlite_base_offline_table_prefix(self):
        """OFFLINE mode tables must start with 'offline_'."""
        from server.repositories.sqlite.base import TABLE_MAP

        for base_name, (offline_name, _) in TABLE_MAP.items():
            assert offline_name.startswith("offline_"), (
                f"Table '{base_name}' offline name '{offline_name}' doesn't start with 'offline_'"
            )

    def test_sqlite_base_server_table_prefix(self):
        """SERVER mode tables must start with 'ldm_'."""
        from server.repositories.sqlite.base import TABLE_MAP

        for base_name, (_, server_name) in TABLE_MAP.items():
            assert server_name.startswith("ldm_"), (
                f"Table '{base_name}' server name '{server_name}' doesn't start with 'ldm_'"
            )
