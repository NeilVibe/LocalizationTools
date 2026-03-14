"""
Schema Drift Guard Tests.

Catches schema drift between:
- Offline SQLite schema (offline_schema.sql) and TABLE_MAP
- OFFLINE_ONLY_COLUMNS allowlist vs actual schema differences
- PostgreSQL-specific SQL in repository code
- SQLite PRAGMA configuration

These tests run WITHOUT a live database — they parse SQL files and inspect code.
"""
from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
import sqlparse

from server.repositories.sqlite.base import TABLE_MAP, OFFLINE_ONLY_COLUMNS, SchemaMode
from tests.stability.conftest import DbMode


# =============================================================================
# Helpers
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
OFFLINE_SCHEMA_PATH = PROJECT_ROOT / "server" / "database" / "offline_schema.sql"
REPO_DIR = PROJECT_ROOT / "server" / "repositories"


def parse_create_tables(sql_content: str) -> dict[str, dict[str, str]]:
    """
    Parse CREATE TABLE statements from SQL content.

    Returns:
        {table_name: {column_name: column_type, ...}, ...}
    """
    tables = {}

    # Use regex to extract CREATE TABLE blocks — more reliable than sqlparse for DDL
    pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);',
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(sql_content):
        table_name = match.group(1)
        body = match.group(2)

        columns = {}
        for line in body.split('\n'):
            line = line.strip().rstrip(',')
            # Skip empty lines, comments, constraints, indexes
            if not line or line.startswith('--'):
                continue
            if any(line.upper().startswith(kw) for kw in
                   ('FOREIGN KEY', 'PRIMARY KEY', 'UNIQUE', 'INDEX', 'CHECK', 'CONSTRAINT')):
                continue

            # Parse column: name type [constraints...]
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip('"')
                # Skip if col_name looks like a keyword
                if col_name.upper() in ('FOREIGN', 'PRIMARY', 'UNIQUE', 'INDEX',
                                         'CHECK', 'CONSTRAINT', 'CREATE'):
                    continue
                col_type = parts[1].strip(',')
                columns[col_name] = col_type

        if columns:
            tables[table_name] = columns

    return tables


def get_sqlalchemy_table_columns(table_name: str) -> dict[str, str]:
    """Get column names and types from SQLAlchemy model by creating a temp DB."""
    from sqlalchemy import create_engine, inspect
    from server.database.models import Base

    # Create in-memory SQLite and introspect
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    columns = {}
    try:
        for col in inspector.get_columns(table_name):
            columns[col["name"]] = str(col["type"])
    except Exception:
        pass

    engine.dispose()
    return columns


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.stability
def test_offline_schema_covers_all_ldm_tables():
    """
    Every entry in TABLE_MAP must have its offline_name table defined
    in offline_schema.sql.
    """
    sql_content = OFFLINE_SCHEMA_PATH.read_text(encoding="utf-8")
    parsed_tables = parse_create_tables(sql_content)
    offline_table_names = set(parsed_tables.keys())

    missing = []
    for base_name, (offline_name, server_name) in TABLE_MAP.items():
        if offline_name not in offline_table_names:
            missing.append(f"{base_name}: expected table '{offline_name}' not found in offline_schema.sql")

    assert not missing, (
        f"TABLE_MAP entries missing from offline_schema.sql:\n" +
        "\n".join(f"  - {m}" for m in missing)
    )


@pytest.mark.stability
def test_offline_only_columns_complete():
    """
    OFFLINE_ONLY_COLUMNS must cover columns that are UNIVERSALLY offline-only
    (exist in offline tables but NEVER in any ldm_* table).

    Columns that exist in some ldm_* tables but not others (per-table differences)
    cannot be in the global OFFLINE_ONLY_COLUMNS set since _has_column() is global.

    Catches:
    - Missing allowlist entries (new universally-offline-only column not added)
    - Stale allowlist entries (column removed from offline schema)
    """
    sql_content = OFFLINE_SCHEMA_PATH.read_text(encoding="utf-8")
    offline_tables = parse_create_tables(sql_content)

    # Collect ALL columns that appear in ANY ldm_* table
    all_server_cols = set()
    # Collect columns that are in offline but not their specific ldm_* counterpart
    per_table_extras = {}

    for base_name, (offline_name, server_name) in TABLE_MAP.items():
        offline_cols = set(offline_tables.get(offline_name, {}).keys())
        server_cols = set(get_sqlalchemy_table_columns(server_name).keys())

        if not server_cols:
            continue

        all_server_cols.update(server_cols)
        extra = offline_cols - server_cols
        if extra:
            per_table_extras[base_name] = extra

    # Universally offline-only = in some offline table but NEVER in any ldm_* table
    all_extras = set()
    for extras in per_table_extras.values():
        all_extras.update(extras)

    universally_offline_only = all_extras - all_server_cols
    universally_offline_only -= {"id"}  # id is in both but may differ in type

    # Check: all universally offline-only columns are in the allowlist
    missing_from_allowlist = universally_offline_only - OFFLINE_ONLY_COLUMNS

    if missing_from_allowlist:
        # Report which tables have these extra columns
        details = []
        for col in sorted(missing_from_allowlist):
            tables_with = [bn for bn, extras in per_table_extras.items() if col in extras]
            details.append(f"  {col} (in: {', '.join(tables_with)})")
        pytest.fail(
            f"Columns universally offline-only but NOT in OFFLINE_ONLY_COLUMNS:\n" +
            "\n".join(details) +
            "\nAdd them to OFFLINE_ONLY_COLUMNS in server/repositories/sqlite/base.py"
        )

    # Stale check: entries in allowlist that aren't actually extra in any table
    stale_in_allowlist = OFFLINE_ONLY_COLUMNS - all_extras
    if stale_in_allowlist:
        import warnings
        warnings.warn(
            f"OFFLINE_ONLY_COLUMNS entries not found as extra in any offline table: "
            f"{stale_in_allowlist}. These may be stale.",
            stacklevel=1,
        )


@pytest.mark.stability
def test_no_postgresql_specific_sql_in_repos():
    """
    SQLite repository files must not contain PostgreSQL-specific SQL constructs.

    Only checks SQLite repos and shared code (interfaces, routing, base).
    PostgreSQL repos ARE expected to use PostgreSQL features — that's by design.

    Checks for:
    - RETURNING clause (in SQL strings)
    - ILIKE (PostgreSQL case-insensitive LIKE)
    - :: type casts in SQL strings (e.g., ::text, ::integer)
    - SQL NOW() in string literals (Python datetime.now() is fine)
    - ARRAY[ or array_agg (PostgreSQL arrays)
    """
    # Patterns to detect PostgreSQL-specific SQL
    # These look for constructs inside SQL string literals, not Python code
    sql_string_patterns = [
        (r'''['"].*\bRETURNING\b.*['"]''', 'RETURNING clause in SQL string'),
        (r'\.ilike\(', '.ilike() call (PostgreSQL-only)'),
        (r'''['"].*::\w+.*['"]''', ':: type cast in SQL string'),
        (r'''['"].*\bNOW\s*\(\).*['"]''', 'NOW() in SQL string'),
        (r'''['"].*\bARRAY\s*\[.*['"]''', 'ARRAY[] in SQL string'),
        (r'''['"].*\barray_agg\b.*['"]''', 'array_agg in SQL string'),
    ]

    # Only check non-PostgreSQL repos (SQLite repos, interfaces, routing, base)
    skip_dirs = {"postgresql", "__pycache__"}

    violations = []

    for py_file in REPO_DIR.rglob("*.py"):
        # Skip PostgreSQL-specific repos and cache
        if any(part in skip_dirs for part in py_file.parts):
            continue

        content = py_file.read_text(encoding="utf-8")

        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            for pattern, name in sql_string_patterns:
                if re.search(pattern, line):
                    violations.append(
                        f"  {py_file.relative_to(PROJECT_ROOT)}:{line_num} — {name}: {stripped[:120]}"
                    )

    assert not violations, (
        f"PostgreSQL-specific SQL found in non-PostgreSQL repository code:\n" +
        "\n".join(violations)
    )


@pytest.mark.stability
def test_sqlite_pragmas(db_mode, clean_db):
    """
    SQLite databases should have WAL journal mode (persistent across connections).

    Note: foreign_keys PRAGMA is per-connection in SQLite — it must be set on
    every new connection. We verify WAL mode here (which IS persistent) and
    document that foreign_keys must be enabled per-connection by repo code.
    """
    if db_mode == DbMode.ONLINE:
        pytest.skip("PRAGMA check only applies to SQLite modes")

    conn = sqlite3.connect(clean_db)
    try:
        # WAL mode persists across connections — verify it was set
        jm_result = conn.execute("PRAGMA journal_mode").fetchone()
        assert jm_result[0].lower() == "wal", (
            f"journal_mode should be 'wal', got '{jm_result[0]}'. "
            f"WAL mode should be set during database initialization."
        )

        # Verify foreign_keys CAN be enabled (not disabled by compile option)
        conn.execute("PRAGMA foreign_keys = ON")
        fk_result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk_result[0] == 1, (
            f"foreign_keys PRAGMA could not be enabled — SQLite may be compiled "
            f"without foreign key support"
        )
    finally:
        conn.close()


# Known pre-existing schema drift between offline and server-local schemas.
# These are documented mismatches that existed before the parity test infrastructure.
# Remove entries as they are fixed — the test will catch NEW drift.
KNOWN_SCHEMA_DRIFT = {
    # table_base_name: {"server_only": {cols}, "offline_only": {cols}}
    "files": {"server_only": {"created_by"}, "offline_only": set()},
    "rows": {"server_only": set(), "offline_only": {"created_at"}},
    "tms": {"server_only": {"line_pairs", "whole_pairs", "storage_path", "indexed_at"}, "offline_only": set()},
    "tm_entries": {"server_only": {"created_at"}, "offline_only": set()},
    "qa_results": {"server_only": {"check_type"}, "offline_only": set()},
}


@pytest.mark.stability
def test_server_local_schema_matches_offline_structure():
    """
    Verify that server-local (SQLAlchemy-created ldm_* tables) and offline
    (offline_schema.sql) have matching column names for equivalent tables,
    ignoring OFFLINE_ONLY_COLUMNS and KNOWN_SCHEMA_DRIFT.

    Catches: Two different init paths producing different schemas (Pitfall 5).
    New drift will fail the test. Known drift is tracked in KNOWN_SCHEMA_DRIFT.
    """
    sql_content = OFFLINE_SCHEMA_PATH.read_text(encoding="utf-8")
    offline_tables = parse_create_tables(sql_content)

    new_mismatches = []

    for base_name, (offline_name, server_name) in TABLE_MAP.items():
        offline_cols = set(offline_tables.get(offline_name, {}).keys())
        server_cols = set(get_sqlalchemy_table_columns(server_name).keys())

        if not offline_cols or not server_cols:
            continue

        known = KNOWN_SCHEMA_DRIFT.get(base_name, {"server_only": set(), "offline_only": set()})

        server_minus_offline = server_cols - offline_cols - OFFLINE_ONLY_COLUMNS - known["server_only"]
        offline_minus_server = offline_cols - server_cols - OFFLINE_ONLY_COLUMNS - known["offline_only"]

        if server_minus_offline:
            new_mismatches.append(
                f"  {base_name}: NEW columns in ldm_* ({server_name}) but NOT in offline ({offline_name}): {server_minus_offline}"
            )
        if offline_minus_server:
            new_mismatches.append(
                f"  {base_name}: NEW columns in offline ({offline_name}) but NOT in ldm_* ({server_name}): {offline_minus_server}"
            )

    if new_mismatches:
        pytest.fail(
            "NEW schema mismatch detected between server-local and offline tables:\n" +
            "\n".join(new_mismatches) +
            "\nIf intentional, add to KNOWN_SCHEMA_DRIFT in test_schema_drift.py"
        )


@pytest.mark.stability
def test_table_map_server_names_exist_in_models():
    """
    Every server_name in TABLE_MAP should correspond to an actual
    SQLAlchemy model table.
    """
    from sqlalchemy import create_engine, inspect
    from server.database.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    engine.dispose()

    missing = []
    for base_name, (offline_name, server_name) in TABLE_MAP.items():
        if server_name not in actual_tables:
            missing.append(f"  {base_name}: server table '{server_name}' not found in SQLAlchemy models")

    assert not missing, (
        "TABLE_MAP server names not found in SQLAlchemy models:\n" +
        "\n".join(missing)
    )
