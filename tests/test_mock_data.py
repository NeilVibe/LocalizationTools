"""
Tests for scripts/setup_mock_data.py — mock DB setup for v6.0 Showcase.

Covers: language detection, wipe_and_create, folder creation,
CLI flags (--confirm-wipe, --dry-run), and LOC PATH validation.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers — create the required tables in a temp DB
# ---------------------------------------------------------------------------

def _create_schema(conn: sqlite3.Connection) -> None:
    """Replicate the minimal schema needed by setup_mock_data."""
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            email TEXT,
            full_name TEXT,
            department TEXT,
            team TEXT,
            language TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by INTEGER,
            last_login TEXT,
            last_password_change TEXT,
            must_change_password INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ldm_platforms (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            description TEXT,
            created_at TEXT,
            updated_at TEXT,
            is_restricted INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS ldm_projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            platform_id INTEGER,
            description TEXT,
            is_restricted INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (owner_id) REFERENCES users(user_id),
            FOREIGN KEY (platform_id) REFERENCES ldm_platforms(id)
        );

        CREATE TABLE IF NOT EXISTS ldm_folders (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES ldm_projects(id),
            FOREIGN KEY (parent_id) REFERENCES ldm_folders(id)
        );

        CREATE TABLE IF NOT EXISTS ldm_files (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            folder_id INTEGER,
            filename TEXT,
            FOREIGN KEY (project_id) REFERENCES ldm_projects(id)
        );

        CREATE TABLE IF NOT EXISTS ldm_rows (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            FOREIGN KEY (file_id) REFERENCES ldm_files(id)
        );
    """)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite DB with the required schema."""
    db_path = tmp_path / "test_offline.db"
    conn = sqlite3.connect(str(db_path))
    _create_schema(conn)
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------

class TestLanguageDetection:
    def test_detect_fre(self):
        from scripts.setup_mock_data import detect_language_from_name
        code, name = detect_language_from_name("project_FRE")
        assert code == "FRE"
        assert name == "French"

    def test_detect_eng(self):
        from scripts.setup_mock_data import detect_language_from_name
        code, name = detect_language_from_name("project_ENG")
        assert code == "ENG"
        assert name == "English"

    def test_detect_multi(self):
        from scripts.setup_mock_data import detect_language_from_name
        code, name = detect_language_from_name("project_MULTI")
        assert code == "MULTI"
        assert name == "Multi-Language"

    def test_detect_unknown(self):
        from scripts.setup_mock_data import detect_language_from_name
        code, name = detect_language_from_name("some_random")
        assert code == "UNKNOWN"
        assert name == "Unknown"


# ---------------------------------------------------------------------------
# Wipe and create tests
# ---------------------------------------------------------------------------

class TestWipeAndCreate:
    def test_platform_created(self, temp_db: Path):
        from scripts.setup_mock_data import wipe_and_create
        wipe_and_create(temp_db)
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute("SELECT id, name FROM ldm_platforms").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == "v6.0 Showcase"

    def test_three_projects(self, temp_db: Path):
        from scripts.setup_mock_data import wipe_and_create
        wipe_and_create(temp_db)
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute("SELECT name FROM ldm_projects ORDER BY id").fetchall()
        conn.close()
        names = [r[0] for r in rows]
        assert names == ["project_FRE", "project_ENG", "project_MULTI"]

    def test_multi_project_folders(self, temp_db: Path):
        from scripts.setup_mock_data import wipe_and_create
        wipe_and_create(temp_db)
        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute(
            "SELECT name FROM ldm_folders WHERE project_id = 3 ORDER BY id"
        ).fetchall()
        conn.close()
        names = [r[0] for r in rows]
        assert names == ["corrections_FRE", "corrections_ENG"]


# ---------------------------------------------------------------------------
# CLI flag tests
# ---------------------------------------------------------------------------

class TestCLIFlags:
    def test_confirm_wipe_required(self):
        """Running without --confirm-wipe should exit with error."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/setup_mock_data.py"],
            capture_output=True, text=True,
            cwd="/home/neil1988/LocalizationTools",
        )
        assert result.returncode != 0

    def test_dry_run(self, temp_db: Path):
        """--dry-run should not persist any data."""
        from scripts.setup_mock_data import wipe_and_create
        wipe_and_create(temp_db, dry_run=True)
        conn = sqlite3.connect(str(temp_db))
        count = conn.execute("SELECT COUNT(*) FROM ldm_platforms").fetchone()[0]
        conn.close()
        assert count == 0


# ---------------------------------------------------------------------------
# LOC PATH validation tests
# ---------------------------------------------------------------------------

class TestValidateLocPath:
    def test_validate_txt_path(self, tmp_path: Path):
        """test123 has .txt languagedata files."""
        from scripts.setup_mock_data import validate_loc_path
        (tmp_path / "languagedata_fr PC 0904 1847.txt").touch()
        result = validate_loc_path(tmp_path)
        assert result["valid"] is True
        assert result["files_found"] >= 1

    def test_validate_xml_path(self, tmp_path: Path):
        from scripts.setup_mock_data import validate_loc_path
        (tmp_path / "languagedata_fre.xml").touch()
        result = validate_loc_path(tmp_path)
        assert result["valid"] is True
        assert result["files_found"] >= 1

    def test_validate_empty_path(self, tmp_path: Path):
        from scripts.setup_mock_data import validate_loc_path
        result = validate_loc_path(tmp_path)
        assert result["valid"] is False
