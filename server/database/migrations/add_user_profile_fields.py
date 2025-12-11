"""
Database Migration: Add User Profile Fields

Adds new columns to the users table:
- team: Team name (e.g., "Team ABC")
- language: Primary work language (e.g., "Japanese")
- created_by: Foreign key to admin who created the user
- last_password_change: Timestamp of last password change
- must_change_password: Force password change on first login

Run this migration with:
    python -m server.database.migrations.add_user_profile_fields
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import create_engine, text, inspect
from loguru import logger

from server import config


def get_existing_columns(engine, table_name: str) -> set:
    """Get existing column names for a table."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}


def run_migration():
    """Add new user profile fields to the users table."""
    logger.info("Starting migration: Add User Profile Fields")

    engine = create_engine(config.DATABASE_URL)

    # Get existing columns
    existing_columns = get_existing_columns(engine, 'users')
    logger.info(f"Existing columns in users table: {existing_columns}")

    # Define new columns to add
    new_columns = {
        'team': 'VARCHAR(100)',
        'language': 'VARCHAR(50)',
        'created_by': 'INTEGER REFERENCES users(user_id) ON DELETE SET NULL',
        'last_password_change': 'TIMESTAMP',
        'must_change_password': 'BOOLEAN DEFAULT FALSE',
    }

    with engine.connect() as conn:
        for column_name, column_type in new_columns.items():
            if column_name in existing_columns:
                logger.info(f"Column '{column_name}' already exists, skipping")
                continue

            try:
                # PostgreSQL syntax
                sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column_name} {column_type}"

                conn.execute(text(sql))
                conn.commit()
                logger.success(f"Added column '{column_name}' to users table")

            except Exception as e:
                # Column might already exist (race condition or partial migration)
                if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                    logger.info(f"Column '{column_name}' already exists (caught exception)")
                else:
                    logger.error(f"Failed to add column '{column_name}': {e}")
                    raise

    # Create indexes for new columns
    with engine.connect() as conn:
        indexes = [
            ('idx_users_team', 'users', 'team'),
            ('idx_users_language', 'users', 'language'),
        ]

        for index_name, table_name, column_name in indexes:
            try:
                sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"

                conn.execute(text(sql))
                conn.commit()
                logger.success(f"Created index '{index_name}'")

            except Exception as e:
                if 'already exists' in str(e).lower():
                    logger.info(f"Index '{index_name}' already exists")
                else:
                    logger.warning(f"Could not create index '{index_name}': {e}")

    logger.success("Migration completed: Add User Profile Fields")

    # Verify columns were added
    new_existing = get_existing_columns(engine, 'users')
    logger.info(f"Columns after migration: {new_existing}")

    return True


if __name__ == "__main__":
    run_migration()
