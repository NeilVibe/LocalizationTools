#!/usr/bin/env python3
"""
Setup Mock Data for v6.0 Showcase Offline Transfer.

Creates a fresh SQLite database with:
- 1 platform: "v6.0 Showcase"
- 3 projects: project_FRE, project_ENG, project_MULTI
- 2 folders under project_MULTI: corrections_FRE, corrections_ENG

Usage:
    python scripts/setup_mock_data.py --confirm-wipe
    python scripts/setup_mock_data.py --confirm-wipe --dry-run
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANGUAGE_SUFFIX_MAP: dict[str, str] = {
    "FRE": "French",
    "ENG": "English",
    "GER": "German",
    "ITA": "Italian",
    "JPN": "Japanese",
    "KOR": "Korean",
    "POL": "Polish",
    "POR-BR": "Portuguese (BR)",
    "RUS": "Russian",
    "SPA-ES": "Spanish (ES)",
    "SPA-MX": "Spanish (MX)",
    "TUR": "Turkish",
    "ZHO-CN": "Chinese (Simplified)",
    "ZHO-TW": "Chinese (Traditional)",
    "MULTI": "Multi-Language",
}

DB_PATH = Path(__file__).parent.parent / "server" / "data" / "offline.db"

# Admin password hash (bcrypt of "admin123")
_ADMIN_HASH = "$2b$12$LJ3m4ys3Lk0TSwHjbMkJYOQZmSGfXMBkVfPvBNqYaKj2lHgGzVPi6"


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language_from_name(project_name: str) -> tuple[str, str]:
    """Detect language from project name suffix.

    Splits on '_' from the right and checks against LANGUAGE_SUFFIX_MAP.

    Returns:
        (suffix_code, display_name) or ("UNKNOWN", "Unknown").
    """
    parts = project_name.rsplit("_", 1)
    if len(parts) == 2:
        suffix = parts[1]
        if suffix in LANGUAGE_SUFFIX_MAP:
            return suffix, LANGUAGE_SUFFIX_MAP[suffix]
    return "UNKNOWN", "Unknown"


# ---------------------------------------------------------------------------
# LOC PATH validation
# ---------------------------------------------------------------------------

def validate_loc_path(path: Path) -> dict:
    """Validate a LOC PATH directory for languagedata files.

    Accepts .xml, .txt, .xlsx — any extension matching languagedata_*.*.

    Returns:
        {"valid": bool, "files_found": int, "file_types": [filename list]}
    """
    if not path.exists() or not path.is_dir():
        return {"valid": False, "files_found": 0, "file_types": []}

    files = list(path.glob("languagedata_*.*"))
    return {
        "valid": len(files) > 0,
        "files_found": len(files),
        "file_types": [f.name for f in files],
    }


# ---------------------------------------------------------------------------
# Table creation (ensure tables exist)
# ---------------------------------------------------------------------------

def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create required tables if they don't exist."""
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
# Wipe and create
# ---------------------------------------------------------------------------

def wipe_and_create(db_path: Path, dry_run: bool = False) -> None:
    """Wipe existing mock data and create fresh platform/projects/folders.

    Args:
        db_path: Path to the SQLite database file.
        dry_run: If True, rollback instead of committing.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Ensure tables exist (idempotent)
        ensure_tables(conn)

        # Delete in FK-safe order
        for table in ("ldm_rows", "ldm_files", "ldm_folders", "ldm_projects", "ldm_platforms"):
            conn.execute(f"DELETE FROM {table}")
            logger.debug(f"Cleared {table}")

        # Ensure admin user exists
        conn.execute(
            "INSERT OR IGNORE INTO users "
            "(user_id, username, password_hash, role, is_active, created_at) "
            "VALUES (1, 'admin', ?, 'admin', 1, ?)",
            (_ADMIN_HASH, now),
        )

        # Insert platform
        conn.execute(
            "INSERT INTO ldm_platforms (id, name, owner_id, description, created_at, updated_at) "
            "VALUES (1, 'v6.0 Showcase', 1, 'Mock platform for offline transfer demo', ?, ?)",
            (now, now),
        )

        # Insert 3 projects
        projects = [
            (1, "project_FRE", "French localization project"),
            (2, "project_ENG", "English localization project"),
            (3, "project_MULTI", "Multi-language merge testing"),
        ]
        for pid, name, desc in projects:
            lang_code, lang_name = detect_language_from_name(name)
            conn.execute(
                "INSERT INTO ldm_projects "
                "(id, name, owner_id, platform_id, description, is_restricted, created_at, updated_at) "
                "VALUES (?, ?, 1, 1, ?, 0, ?, ?)",
                (pid, name, f"{desc} [{lang_name}]", now, now),
            )
            logger.debug(f"Created project: {name} (language: {lang_code} = {lang_name})")

        # Insert 2 folders under project_MULTI (id=3)
        folders = [
            (1, 3, "corrections_FRE"),
            (2, 3, "corrections_ENG"),
        ]
        for fid, proj_id, name in folders:
            conn.execute(
                "INSERT INTO ldm_folders (id, project_id, parent_id, name, created_at) "
                "VALUES (?, ?, NULL, ?, ?)",
                (fid, proj_id, name, now),
            )
            logger.debug(f"Created folder: {name} (project_id={proj_id})")

        if dry_run:
            conn.rollback()
            logger.info("[DRY RUN] Changes rolled back — no data written")
        else:
            conn.commit()
            logger.success(
                "Mock data created: 1 platform, 3 projects, 2 folders"
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Setup mock data for v6.0 Showcase Offline Transfer"
    )
    parser.add_argument(
        "--confirm-wipe",
        action="store_true",
        help="Required flag to confirm you want to wipe and recreate mock data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without modifying the database",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})",
    )

    args = parser.parse_args()

    if not args.confirm_wipe:
        logger.error("Must pass --confirm-wipe to proceed")
        sys.exit(1)

    logger.info(f"Database: {args.db_path}")
    if args.dry_run:
        logger.info("Mode: DRY RUN (no changes will be persisted)")

    wipe_and_create(args.db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
