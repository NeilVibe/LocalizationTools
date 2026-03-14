"""
API Endpoint Smoke Tests in SQLite Mode.

Phase 6, Plan 02: Proves critical API endpoints return valid responses
when running in SQLite server-local mode via FastAPI TestClient.

Uses dependency overrides to inject SQLite repositories so no real
PostgreSQL connection is needed. Validates OFFL-02 and OFFL-03.
"""

from __future__ import annotations

import sqlite3
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from server.main import app as _wrapped_app
from server.utils.dependencies import get_async_db, get_current_active_user_async

# server.main wraps FastAPI app in socketio.ASGIApp -- get the inner FastAPI instance
app = getattr(_wrapped_app, "other_asgi_app", _wrapped_app)
from server.repositories.factory import (
    get_platform_repository,
    get_project_repository,
    get_folder_repository,
    get_file_repository,
    get_row_repository,
    get_tm_repository,
    get_qa_repository,
    get_trash_repository,
    get_capability_repository,
)
from server.repositories.sqlite.base import SchemaMode
from server.repositories.sqlite.platform_repo import SQLitePlatformRepository
from server.repositories.sqlite.project_repo import SQLiteProjectRepository
from server.repositories.sqlite.folder_repo import SQLiteFolderRepository
from server.repositories.sqlite.file_repo import SQLiteFileRepository
from server.repositories.sqlite.row_repo import SQLiteRowRepository
from server.repositories.sqlite.tm_repo import SQLiteTMRepository
from server.repositories.sqlite.qa_repo import SQLiteQAResultRepository
from server.repositories.sqlite.trash_repo import SQLiteTrashRepository
from server.repositories.sqlite.capability_repo import SQLiteCapabilityRepository
from server.repositories.routing.row_repo import RoutingRowRepository
from server.database.server_sqlite import ServerSQLiteDatabase


# =============================================================================
# Test User
# =============================================================================

TEST_USER = {
    "user_id": 1,
    "id": 1,
    "username": "testadmin",
    "email": "test@example.com",
    "role": "admin",
    "is_admin": True,
}


# =============================================================================
# Session-scoped template DB (avoids expensive Base.metadata.create_all per test)
# =============================================================================

_template_path: str | None = None


@pytest.fixture(scope="session")
def _server_local_template():
    """Create server_local template DB once per session."""
    global _template_path
    tmpdir = tempfile.mkdtemp(prefix="api_smoke_")
    path = Path(tmpdir) / "template.db"

    from sqlalchemy import create_engine
    from server.database.models import Base
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    _template_path = str(path)
    yield str(path)

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# Per-test fresh DB + overrides
# =============================================================================

@pytest.fixture
def sqlite_db(tmp_path, _server_local_template):
    """Fresh SQLite database copied from template, with dependency overrides."""
    db_path = str(tmp_path / "test_api.db")
    shutil.copy2(_server_local_template, db_path)

    # Enable WAL + FK
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.commit()
    conn.close()

    test_db = ServerSQLiteDatabase(db_path=db_path)

    def _make_repo(cls):
        repo = cls(schema_mode=SchemaMode.SERVER)
        repo._db = test_db
        return repo

    # Override all factory dependencies to return SQLite repos pointing at temp DB
    app.dependency_overrides[get_async_db] = lambda: None
    app.dependency_overrides[get_current_active_user_async] = lambda: TEST_USER
    app.dependency_overrides[get_platform_repository] = lambda: _make_repo(SQLitePlatformRepository)
    app.dependency_overrides[get_project_repository] = lambda: _make_repo(SQLiteProjectRepository)
    app.dependency_overrides[get_folder_repository] = lambda: _make_repo(SQLiteFolderRepository)
    app.dependency_overrides[get_file_repository] = lambda: _make_repo(SQLiteFileRepository)
    app.dependency_overrides[get_row_repository] = lambda: RoutingRowRepository(_make_repo(SQLiteRowRepository))
    app.dependency_overrides[get_tm_repository] = lambda: _make_repo(SQLiteTMRepository)
    app.dependency_overrides[get_qa_repository] = lambda: _make_repo(SQLiteQAResultRepository)
    app.dependency_overrides[get_trash_repository] = lambda: _make_repo(SQLiteTrashRepository)
    app.dependency_overrides[get_capability_repository] = lambda: SQLiteCapabilityRepository()

    yield db_path

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client(sqlite_db):
    """FastAPI TestClient with all dependencies overridden for SQLite mode."""
    return TestClient(app)


# =============================================================================
# Health
# =============================================================================


class TestHealthEndpoint:
    def test_health(self, client):
        """GET /api/ldm/health -> 200."""
        resp = client.get("/api/ldm/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# =============================================================================
# Platform CRUD
# =============================================================================


class TestPlatformEndpoints:
    def test_create_platform(self, client):
        """POST /api/ldm/platforms -> 201."""
        resp = client.post("/api/ldm/platforms", json={"name": "PC", "description": "PC Platform"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "PC"
        assert "id" in data

    def test_list_platforms(self, client):
        """GET /api/ldm/platforms -> 200 with list."""
        # Create first
        client.post("/api/ldm/platforms", json={"name": "PC"})
        resp = client.get("/api/ldm/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert "platforms" in data
        assert data["total"] >= 1


# =============================================================================
# Project CRUD
# =============================================================================


class TestProjectEndpoints:
    def test_create_project(self, client):
        """POST /api/ldm/projects -> 200 (project create)."""
        resp = client.post("/api/ldm/projects", json={"name": "Test Project"})
        # ProjectCreate returns the project dict
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_list_projects(self, client):
        """GET /api/ldm/projects -> 200."""
        client.post("/api/ldm/projects", json={"name": "P1"})
        resp = client.get("/api/ldm/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# =============================================================================
# Folder CRUD
# =============================================================================


class TestFolderEndpoints:
    def _create_project(self, client) -> int:
        resp = client.post("/api/ldm/projects", json={"name": "FolderTestProj"})
        return resp.json()["id"]

    def test_create_folder(self, client):
        """POST /api/ldm/folders -> 200."""
        proj_id = self._create_project(client)
        resp = client.post("/api/ldm/folders", json={
            "project_id": proj_id,
            "name": "UI Strings",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "UI Strings"

    def test_list_folders(self, client):
        """GET /api/ldm/projects/{id}/folders -> 200."""
        proj_id = self._create_project(client)
        client.post("/api/ldm/folders", json={"project_id": proj_id, "name": "F1"})
        resp = client.get(f"/api/ldm/projects/{proj_id}/folders")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# =============================================================================
# Row operations (requires seeded file data)
# =============================================================================


class TestRowEndpoints:
    def _seed_hierarchy(self, sqlite_db) -> dict:
        """Seed platform -> project -> folder -> file -> rows directly in DB."""
        conn = sqlite3.connect(sqlite_db)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute(
            "INSERT INTO ldm_platforms (name, description, owner_id, is_restricted) VALUES (?, ?, ?, ?)",
            ("PC", "PC", 1, 0)
        )
        platform_id = c.lastrowid

        c.execute(
            "INSERT INTO ldm_projects (name, description, owner_id, platform_id, is_restricted) VALUES (?, ?, ?, ?, ?)",
            ("TestProj", "desc", 1, platform_id, 0)
        )
        project_id = c.lastrowid

        c.execute(
            "INSERT INTO ldm_folders (name, project_id) VALUES (?, ?)",
            ("UI", project_id)
        )
        folder_id = c.lastrowid

        c.execute(
            "INSERT INTO ldm_files (name, original_filename, format, row_count, folder_id, project_id, source_language, target_language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("menu.xml", "menu.xml", "xml", 2, folder_id, project_id, "ko", "en")
        )
        file_id = c.lastrowid

        for i, (sid, src, tgt) in enumerate([
            ("MENU_NEW", "새 게임", "New Game"),
            ("MENU_CONT", "계속하기", "Continue"),
        ]):
            c.execute(
                "INSERT INTO ldm_rows (file_id, row_num, string_id, source, target, status, qa_flag_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (file_id, i, sid, src, tgt, "normal", 0)
            )

        conn.commit()
        conn.close()

        return {"platform_id": platform_id, "project_id": project_id,
                "folder_id": folder_id, "file_id": file_id}

    def test_get_rows(self, client, sqlite_db):
        """GET /api/ldm/files/{id}/rows -> 200 with row data."""
        ids = self._seed_hierarchy(sqlite_db)
        resp = client.get(f"/api/ldm/files/{ids['file_id']}/rows")
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert len(data["rows"]) == 2

    def test_update_row(self, client, sqlite_db):
        """PUT /api/ldm/rows/{id} -> 200."""
        ids = self._seed_hierarchy(sqlite_db)
        # Get rows first to find row id
        rows_resp = client.get(f"/api/ldm/files/{ids['file_id']}/rows")
        row_id = rows_resp.json()["rows"][0]["id"]

        resp = client.put(f"/api/ldm/rows/{row_id}", json={
            "target": "New Game Updated",
            "status": "confirmed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["target"] == "New Game Updated"

    def test_search_rows(self, client, sqlite_db):
        """GET /api/ldm/files/{id}/rows?search=text -> 200."""
        ids = self._seed_hierarchy(sqlite_db)
        resp = client.get(f"/api/ldm/files/{ids['file_id']}/rows", params={"search": "New"})
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data


# =============================================================================
# TM endpoints
# =============================================================================


class TestTMEndpoints:
    def test_list_tms(self, client):
        """GET /api/ldm/tm -> 200 (empty list when no TMs)."""
        resp = client.get("/api/ldm/tm")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_tm_upload_requires_file(self, client):
        """POST /api/ldm/tm/upload without file -> 422 (validation error, not 500)."""
        resp = client.post("/api/ldm/tm/upload")
        # Should be 422 (missing required field), NOT 500
        assert resp.status_code == 422


# =============================================================================
# Project Tree
# =============================================================================


class TestProjectTree:
    def test_project_tree(self, client, sqlite_db):
        """GET /api/ldm/projects/{id}/tree -> 200."""
        # Seed data
        conn = sqlite3.connect(sqlite_db)
        conn.execute("INSERT INTO ldm_projects (name, owner_id, is_restricted) VALUES (?, ?, ?)", ("TreeProj", 1, 0))
        proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        resp = client.get(f"/api/ldm/projects/{proj_id}/tree")
        assert resp.status_code == 200


# =============================================================================
# Context/MapData graceful degradation
# =============================================================================


class TestContextStatus:
    def test_context_status(self, client):
        """GET /api/ldm/context/status -> 200 or 503 with graceful response."""
        resp = client.get("/api/ldm/context/status")
        # Context service returns status even when not configured
        assert resp.status_code in (200, 503)
        data = resp.json()
        # Should not be a 500 internal error -- must have a structured response
        assert isinstance(data, dict)


class TestMapDataStatus:
    def test_mapdata_status(self, client):
        """GET /api/ldm/mapdata/status -> 200 with not-loaded state."""
        resp = client.get("/api/ldm/mapdata/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "loaded" in data
        assert data["loaded"] is False


# =============================================================================
# No 500 errors meta-test
# =============================================================================


class TestNo500Errors:
    """Run a batch of GET endpoints and verify none return 500."""

    @pytest.mark.parametrize("path", [
        "/api/ldm/health",
        "/api/ldm/platforms",
        "/api/ldm/projects",
        "/api/ldm/tm",
        "/api/ldm/context/status",
        "/api/ldm/mapdata/status",
    ])
    def test_no_500_on_get(self, client, path):
        """GET {path} must never return 500."""
        resp = client.get(path)
        assert resp.status_code != 500, f"{path} returned 500: {resp.text}"
