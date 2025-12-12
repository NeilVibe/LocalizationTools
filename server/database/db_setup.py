"""
Database Setup and Initialization

Handles database creation, connection management, and initialization.
PostgreSQL only - no SQLite support.
"""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from server.database.models import Base
from server import config


# ============================================================================
# Database Engine Creation
# ============================================================================

def get_database_url() -> str:
    """
    Get PostgreSQL database connection URL.

    Returns:
        Database connection URL string.
    """
    return config.DATABASE_URL


def create_database_engine(echo: bool = False):
    """
    Create SQLAlchemy database engine for PostgreSQL.

    Args:
        echo: If True, log all SQL statements (verbose).

    Returns:
        SQLAlchemy Engine instance.
    """
    db_url = get_database_url()

    engine = create_engine(
        db_url,
        echo=echo,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
        pool_timeout=config.DB_POOL_TIMEOUT,
        pool_recycle=config.DB_POOL_RECYCLE,
        pool_pre_ping=True  # Verify connections before using
    )

    logger.info(f"Database engine created: {engine.url.database}")
    return engine


# ============================================================================
# Database Initialization
# ============================================================================

def initialize_database(engine, drop_existing: bool = False):
    """
    Initialize database tables.

    Args:
        engine: SQLAlchemy engine instance.
        drop_existing: If True, drop all existing tables first (DANGEROUS!).
    """
    if drop_existing:
        logger.warning("Dropping all existing tables...")
        Base.metadata.drop_all(engine)
        logger.info("All tables dropped")

    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.success("Database tables created successfully")

    # Log created tables
    table_names = Base.metadata.tables.keys()
    logger.info(f"Tables created: {', '.join(table_names)}")


# ============================================================================
# Session Management
# ============================================================================

def get_session_maker(engine):
    """
    Create a session maker for database operations.

    Args:
        engine: SQLAlchemy engine instance.

    Returns:
        SQLAlchemy sessionmaker instance.
    """
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    return SessionLocal


def get_db_session(session_maker) -> Session:
    """
    Get a database session (use with context manager).

    Args:
        session_maker: SQLAlchemy sessionmaker instance.

    Yields:
        Database session.

    Example:
        >>> with get_db_session(session_maker) as db:
        >>>     user = db.query(User).filter(User.username == "john").first()
    """
    db = session_maker()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================

def test_connection(engine) -> bool:
    """
    Test database connection.

    Args:
        engine: SQLAlchemy engine instance.

    Returns:
        True if connection successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.success("Database connection test: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Database connection test: FAILED - {e}")
        return False


def get_table_counts(session: Session) -> dict:
    """
    Get row counts for all tables dynamically.

    Args:
        session: Database session.

    Returns:
        Dictionary mapping table names to row counts.
    """
    from sqlalchemy import text

    counts = {}

    # Get all table names from metadata
    for table_name in Base.metadata.tables.keys():
        try:
            result = session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            counts[table_name] = result.scalar()
        except Exception:
            counts[table_name] = -1  # Table might not exist yet

    return counts


# ============================================================================
# Main Setup Function
# ============================================================================

def setup_database(drop_existing: bool = False, echo: bool = False):
    """
    Complete database setup process (PostgreSQL).

    Args:
        drop_existing: If True, drop all existing tables first.
        echo: If True, log all SQL statements.

    Returns:
        Tuple of (engine, session_maker).

    Example:
        >>> engine, session_maker = setup_database()
        >>> with get_db_session(session_maker) as db:
        >>>     # Perform database operations
        >>>     pass
    """
    logger.info("=" * 70)
    logger.info("DATABASE SETUP START (PostgreSQL)")
    logger.info("=" * 70)

    # Create engine
    engine = create_database_engine(echo=echo)

    # Test connection
    if not test_connection(engine):
        raise ConnectionError("Failed to connect to PostgreSQL database")

    # Initialize tables
    initialize_database(engine, drop_existing=drop_existing)

    # Create session maker
    session_maker = get_session_maker(engine)

    # Verify tables
    SessionLocal = session_maker()
    try:
        counts = get_table_counts(SessionLocal)
        logger.info("Table row counts:")
        for table, count in counts.items():
            logger.info(f"  {table}: {count}")
    finally:
        SessionLocal.close()

    logger.info("=" * 70)
    logger.success("DATABASE SETUP COMPLETE")
    logger.info("=" * 70)

    return engine, session_maker


# ============================================================================
# CLI for Direct Execution
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database setup utility (PostgreSQL)")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables (DANGEROUS!)"
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Echo SQL statements (verbose)"
    )

    args = parser.parse_args()

    if args.drop:
        logger.warning("DROP EXISTING TABLES REQUESTED!")
        response = input("Are you sure? This will DELETE ALL DATA! (yes/no): ")
        if response.lower() != "yes":
            logger.info("Database setup cancelled")
            exit(0)

    # Run setup
    try:
        engine, session_maker = setup_database(
            drop_existing=args.drop,
            echo=args.echo
        )
        logger.success("Database is ready for use")
    except Exception as e:
        logger.exception(f"Database setup failed: {e}")
        exit(1)
