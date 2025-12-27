"""
Database Helper for Dev Testing

CRITICAL: Use server config for database connection, NOT hardcoded credentials.

Usage:
    from helpers.database import get_db_connection, execute_query

    with get_db_connection() as conn:
        result = execute_query(conn, "SELECT * FROM ldm_files")
"""

import sys
from contextlib import contextmanager
from typing import Any, List, Optional

# Add server path to import config
sys.path.insert(0, '/home/neil1988/LocalizationTools/server')

from sqlalchemy import create_engine, text
from config import DATABASE_URL

# Create engine using server config (CORRECT approach)
engine = create_engine(DATABASE_URL)


@contextmanager
def get_db_connection():
    """Get database connection using correct credentials from server config."""
    with engine.connect() as conn:
        yield conn


def execute_query(conn, query: str, params: dict = None) -> List[Any]:
    """Execute a query and return results."""
    result = conn.execute(text(query), params or {})
    return result.fetchall()


def execute_update(conn, query: str, params: dict = None) -> int:
    """Execute an update/delete and return rowcount."""
    result = conn.execute(text(query), params or {})
    conn.commit()
    return result.rowcount


# Common queries

def get_files_for_project(project_id: int) -> List[tuple]:
    """Get all files for a project."""
    with get_db_connection() as conn:
        return execute_query(conn,
            "SELECT id, name FROM ldm_files WHERE project_id = :pid",
            {"pid": project_id}
        )


def get_projects_for_user(user_id: int) -> List[tuple]:
    """Get all projects for a user."""
    with get_db_connection() as conn:
        return execute_query(conn,
            "SELECT id, name FROM ldm_projects WHERE owner_id = :uid",
            {"uid": user_id}
        )


def get_row_count_for_file(file_id: int) -> int:
    """Get row count for a file."""
    with get_db_connection() as conn:
        result = execute_query(conn,
            "SELECT COUNT(*) FROM ldm_rows WHERE file_id = :fid",
            {"fid": file_id}
        )
        return result[0][0] if result else 0


def delete_file(file_id: int) -> tuple:
    """Delete a file and its rows. Returns (rows_deleted, files_deleted)."""
    with get_db_connection() as conn:
        rows = execute_update(conn,
            "DELETE FROM ldm_rows WHERE file_id = :fid",
            {"fid": file_id}
        )
        files = execute_update(conn,
            "DELETE FROM ldm_files WHERE id = :fid",
            {"fid": file_id}
        )
        return (rows, files)


def search_files_by_name(pattern: str) -> List[tuple]:
    """Search files by name pattern."""
    with get_db_connection() as conn:
        return execute_query(conn,
            "SELECT id, name, project_id FROM ldm_files WHERE name ILIKE :pattern",
            {"pattern": f"%{pattern}%"}
        )


if __name__ == "__main__":
    # Test connection
    print(f"Connecting to: {DATABASE_URL[:50]}...")
    with get_db_connection() as conn:
        result = execute_query(conn, "SELECT 1")
        print(f"Connection test: {'OK' if result else 'FAILED'}")

    # List projects
    projects = get_projects_for_user(2)  # admin user
    print(f"\nProjects for user 2: {len(projects)}")
    for p in projects:
        print(f"  ID: {p[0]}, Name: {p[1]}")
