#!/usr/bin/env python3
"""
Migration Script: JSON to JSONB

Converts all JSON columns to JSONB for better PostgreSQL performance.
Run this ONCE on existing databases after updating models.py.

Usage:
    python3 scripts/migrate_json_to_jsonb.py

Note: This is safe to run multiple times - JSONB columns won't be affected.
"""

import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text
from server.database.db_setup import engine

# Columns to migrate: (table_name, column_name)
MIGRATIONS = [
    # LogEntry
    ("log_entries", "file_info"),
    ("log_entries", "parameters"),
    # ActiveOperation
    ("active_operations", "file_info"),
    ("active_operations", "parameters"),
    ("active_operations", "output_files"),
    # UserActivitySummary
    ("user_activity_summary", "tools_used"),
    # ErrorLog
    ("error_logs", "context"),
    # Announcement
    ("announcements", "target_users"),
    # Installation
    ("installations", "extra_data"),
    # RemoteLog
    ("remote_logs", "data"),
    # TelemetrySummary
    ("telemetry_summary", "tools_used"),
    # LDMTrash (was Text, now JSONB)
    ("ldm_trash", "item_data"),
]


def migrate():
    """Run the JSON to JSONB migration."""
    logger.info("Starting JSON to JSONB migration...")

    with engine.connect() as conn:
        for table, column in MIGRATIONS:
            try:
                # Check if column exists and its type
                result = conn.execute(text(f"""
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_name = :table AND column_name = :column
                """), {"table": table, "column": column})

                row = result.fetchone()
                if not row:
                    logger.warning(f"Column {table}.{column} not found, skipping")
                    continue

                current_type = row[0]

                if current_type == 'jsonb':
                    logger.info(f"  {table}.{column}: Already JSONB, skipping")
                    continue

                if current_type in ('json', 'text'):
                    logger.info(f"  {table}.{column}: Converting {current_type} -> JSONB...")
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ALTER COLUMN {column}
                        TYPE JSONB USING {column}::JSONB
                    """))
                    conn.commit()
                    logger.info(f"  {table}.{column}: Done")
                else:
                    logger.warning(f"  {table}.{column}: Unexpected type {current_type}, skipping")

            except Exception as e:
                logger.error(f"  {table}.{column}: Failed - {e}")
                conn.rollback()

    logger.info("Migration complete!")


if __name__ == "__main__":
    migrate()
