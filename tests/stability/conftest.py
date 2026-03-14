"""
Stability Test Infrastructure.

Provides fixtures for parametrized database parity testing across all 3 modes:
- ONLINE: PostgreSQL (ldm_* tables via SQLAlchemy ORM)
- SERVER_LOCAL: SQLite with ldm_* tables (server-local mode)
- OFFLINE: SQLite with offline_* tables (Electron app offline mode)

Usage:
    def test_something(db_mode, clean_db):
        # This test runs 3 times — once per mode
        ...
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# DbMode Enum
# =============================================================================

class DbMode(Enum):
    """Database mode for parametrized testing."""
    ONLINE = "online"
    SERVER_LOCAL = "server_local"
    OFFLINE = "offline"

    def __str__(self) -> str:
        return self.value


# =============================================================================
# Mode Parametrization Fixture
# =============================================================================

@pytest.fixture(params=[DbMode.ONLINE, DbMode.SERVER_LOCAL, DbMode.OFFLINE], ids=str)
def db_mode(request) -> DbMode:
    """Parametrize tests across all 3 database modes."""
    return request.param


# =============================================================================
# Clean Database Fixture
# =============================================================================

# =============================================================================
# Template DB Cache (session-scoped for performance)
# =============================================================================
# SQLAlchemy Base.metadata.create_all takes ~70s for ldm_* tables.
# We create the template DB once per session and copy it for each test.

_server_local_template: str | None = None


@pytest.fixture(scope="session")
def _server_local_template_db(tmp_path_factory):
    """Create server_local template DB once per session (expensive: ~70s first time)."""
    global _server_local_template
    template_dir = tmp_path_factory.mktemp("templates")
    template_path = template_dir / "server_local_template.db"

    from sqlalchemy import create_engine
    from server.database.models import Base
    engine = create_engine(f"sqlite:///{template_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    _server_local_template = str(template_path)
    return str(template_path)


@pytest.fixture
def clean_db(db_mode, tmp_path, _server_local_template_db):
    """
    Provide a clean database for each test.

    Returns:
        - ONLINE: skips (PostgreSQL not available)
        - SERVER_LOCAL: path to temp SQLite file with ldm_* tables (copied from template)
        - OFFLINE: path to temp SQLite file with offline_* tables
    """
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available in test environment")

    elif db_mode == DbMode.SERVER_LOCAL:
        db_path = tmp_path / "server_local_test.db"
        # Copy from pre-built template (fast: <1ms vs 70s)
        shutil.copy2(_server_local_template_db, str(db_path))
        # Enable WAL and foreign keys
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
        conn.close()
        yield str(db_path)

    elif db_mode == DbMode.OFFLINE:
        db_path = tmp_path / "offline_test.db"
        conn = sqlite3.connect(str(db_path))
        # Execute offline_schema.sql
        schema_path = Path(__file__).parent.parent.parent / "server" / "database" / "offline_schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        # Enable WAL and foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
        conn.close()
        yield str(db_path)


# =============================================================================
# assert_equivalent Helper
# =============================================================================

_IGNORE_FIELDS = {"id", "created_at", "updated_at", "downloaded_at", "sync_status"}


def assert_equivalent(
    result_a: dict | list,
    result_b: dict | list,
    ignore_fields: set[str] | None = None,
) -> None:
    """
    Compare two results (dict or list of dicts) ignoring volatile fields.

    Normalizes SQLite 0/1 to Python bool for comparison.

    Args:
        result_a: First result
        result_b: Second result
        ignore_fields: Additional fields to ignore beyond the defaults
    """
    skip = _IGNORE_FIELDS | (ignore_fields or set())

    def _normalize(value: Any) -> Any:
        """Normalize values for comparison (SQLite 0/1 -> bool)."""
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        return value

    def _clean(d: dict) -> dict:
        return {k: _normalize(v) for k, v in d.items() if k not in skip}

    if isinstance(result_a, dict) and isinstance(result_b, dict):
        cleaned_a = _clean(result_a)
        cleaned_b = _clean(result_b)
        assert cleaned_a == cleaned_b, (
            f"Dict mismatch:\n  A: {cleaned_a}\n  B: {cleaned_b}"
        )
    elif isinstance(result_a, list) and isinstance(result_b, list):
        assert len(result_a) == len(result_b), (
            f"List length mismatch: {len(result_a)} vs {len(result_b)}"
        )
        for i, (a, b) in enumerate(zip(result_a, result_b)):
            if isinstance(a, dict) and isinstance(b, dict):
                cleaned_a = _clean(a)
                cleaned_b = _clean(b)
                assert cleaned_a == cleaned_b, (
                    f"Dict mismatch at index {i}:\n  A: {cleaned_a}\n  B: {cleaned_b}"
                )
            else:
                assert _normalize(a) == _normalize(b), (
                    f"Value mismatch at index {i}: {a} vs {b}"
                )
    else:
        raise TypeError(
            f"Cannot compare {type(result_a).__name__} with {type(result_b).__name__}"
        )


# =============================================================================
# Repository Factory Fixtures
# =============================================================================
# Note: These fixtures create repository instances for the given db_mode.
# ONLINE mode is skipped (requires PostgreSQL). SERVER_LOCAL and OFFLINE
# create SQLite repositories with the appropriate schema mode.
# Full repo fixture implementation will be expanded as tests need them.
# =============================================================================

_TEST_USER = {"id": 1, "username": "test_admin", "role": "admin"}


def _make_test_db(db_mode: DbMode, db_path: str):
    """
    Create a database wrapper pointing at the test database path.

    This avoids using the singleton database instances (which point to real databases)
    and instead creates fresh instances pointing at the test temp database.
    """
    if db_mode == DbMode.SERVER_LOCAL:
        from server.database.server_sqlite import ServerSQLiteDatabase
        return ServerSQLiteDatabase(db_path=db_path)
    else:  # OFFLINE
        # For offline, we can't use OfflineDatabase directly because its __init__
        # runs _init_schema_sync which re-creates schema. We already have the schema
        # from clean_db. Create a minimal wrapper with the same _get_async_connection.
        from server.database.server_sqlite import ServerSQLiteDatabase
        # ServerSQLiteDatabase has the same _get_async_connection interface
        # and doesn't run schema init, so it works for offline too.
        return ServerSQLiteDatabase(db_path=db_path)


def _make_repo(db_mode, clean_db, repo_class, schema_mode):
    """Create a repo instance wired to the test database."""
    repo = repo_class(schema_mode=schema_mode)
    repo._db = _make_test_db(db_mode, clean_db)
    return repo


def _get_schema_mode(db_mode):
    """Get SchemaMode for the given DbMode."""
    from server.repositories.sqlite.base import SchemaMode
    return SchemaMode.SERVER if db_mode == DbMode.SERVER_LOCAL else SchemaMode.OFFLINE


@pytest.fixture
def platform_repo(db_mode, clean_db):
    """Platform repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
    return _make_repo(db_mode, clean_db, SQLitePlatformRepository, _get_schema_mode(db_mode))


@pytest.fixture
def project_repo(db_mode, clean_db):
    """Project repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.project_repo import SQLiteProjectRepository
    return _make_repo(db_mode, clean_db, SQLiteProjectRepository, _get_schema_mode(db_mode))


@pytest.fixture
def folder_repo(db_mode, clean_db):
    """Folder repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.folder_repo import SQLiteFolderRepository
    return _make_repo(db_mode, clean_db, SQLiteFolderRepository, _get_schema_mode(db_mode))


@pytest.fixture
def file_repo(db_mode, clean_db):
    """File repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.file_repo import SQLiteFileRepository
    return _make_repo(db_mode, clean_db, SQLiteFileRepository, _get_schema_mode(db_mode))


@pytest.fixture
def row_repo(db_mode, clean_db):
    """Row repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.row_repo import SQLiteRowRepository
    return _make_repo(db_mode, clean_db, SQLiteRowRepository, _get_schema_mode(db_mode))


@pytest.fixture
def tm_repo(db_mode, clean_db):
    """TM repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository
    return _make_repo(db_mode, clean_db, SQLiteTMRepository, _get_schema_mode(db_mode))


@pytest.fixture
def qa_repo(db_mode, clean_db):
    """QA repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository
    return _make_repo(db_mode, clean_db, SQLiteQAResultRepository, _get_schema_mode(db_mode))


@pytest.fixture
def trash_repo(db_mode, clean_db):
    """Trash repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.trash_repo import SQLiteTrashRepository
    return _make_repo(db_mode, clean_db, SQLiteTrashRepository, _get_schema_mode(db_mode))


@pytest.fixture
def capability_repo(db_mode, clean_db):
    """Capability repository for current db_mode."""
    if db_mode == DbMode.ONLINE:
        pytest.skip("PostgreSQL not available")
    from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository
    return SQLiteCapabilityRepository()


# =============================================================================
# Game Data Factory
# =============================================================================

@pytest.fixture
def game_data_factory():
    """
    Factory that returns a function to create a full game data hierarchy.

    Returns a dict builder that creates:
    - Platform "PC" (owner_id=1)
    - Project "Dark Souls IV"
    - Folder "UI"
    - File "menu_strings.xml"
    - 3 rows with Korean/English game strings

    Usage in tests:
        data = game_data_factory()
        # data contains template dicts for creating entities
    """
    def _build():
        return {
            "platform": {
                "name": "PC",
                "description": "PC Platform",
                "owner_id": 1,
                "is_restricted": 0,
            },
            "project": {
                "name": "Dark Souls IV",
                "description": "Action RPG",
                "owner_id": 1,
                "is_restricted": 0,
            },
            "folder": {
                "name": "UI",
            },
            "file": {
                "name": "menu_strings.xml",
                "original_filename": "menu_strings.xml",
                "format": "xml",
                "row_count": 3,
                "source_language": "ko",
                "target_language": "en",
            },
            "rows": [
                {"row_num": 0, "string_id": "MENU_NEW_GAME", "source": "새 게임", "target": "New Game", "status": "normal"},
                {"row_num": 1, "string_id": "MENU_CONTINUE", "source": "계속하기", "target": "Continue", "status": "normal"},
                {"row_num": 2, "string_id": "MENU_SETTINGS", "source": "설정", "target": "Settings", "status": "normal"},
            ],
        }
    return _build
