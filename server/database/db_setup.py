"""
Database Setup and Initialization

Handles database creation, connection management, and initialization.
Supports both SQLite (development) and PostgreSQL (production).
"""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from server.database.models import Base
from server import config


# ============================================================================
# SQLite Configuration
# ============================================================================

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key support for SQLite."""
    if "sqlite" in str(dbapi_conn):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ============================================================================
# Database Engine Creation
# ============================================================================

def get_database_url(use_postgres: bool = False) -> str:
    """
    Get database connection URL.

    Args:
        use_postgres: If True, use PostgreSQL. Otherwise use SQLite.

    Returns:
        Database connection URL string.
    """
    if use_postgres:
        # PostgreSQL URL (production)
        return config.POSTGRES_DATABASE_URL
    else:
        # SQLite URL (development)
        return config.SQLITE_DATABASE_URL


def create_database_engine(use_postgres: bool = False, echo: bool = False):
    """
    Create SQLAlchemy database engine.

    Args:
        use_postgres: If True, connect to PostgreSQL. Otherwise use SQLite.
        echo: If True, log all SQL statements (verbose).

    Returns:
        SQLAlchemy Engine instance.
    """
    db_url = get_database_url(use_postgres=use_postgres)

    # Create engine with appropriate settings
    if use_postgres:
        engine = create_engine(
            db_url,
            echo=echo,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True  # Verify connections before using
        )
    else:
        engine = create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False}  # SQLite threading
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
    Get row counts for all tables.

    Args:
        session: Database session.

    Returns:
        Dictionary mapping table names to row counts.
    """
    from server.database.models import (
        User, Session as DBSession, LogEntry, ToolUsageStats,
        FunctionUsageStats, PerformanceMetrics, UserActivitySummary,
        AppVersion, UpdateHistory, ErrorLog, Announcement, UserFeedback
    )

    counts = {
        "users": session.query(User).count(),
        "sessions": session.query(DBSession).count(),
        "log_entries": session.query(LogEntry).count(),
        "tool_usage_stats": session.query(ToolUsageStats).count(),
        "function_usage_stats": session.query(FunctionUsageStats).count(),
        "performance_metrics": session.query(PerformanceMetrics).count(),
        "user_activity_summary": session.query(UserActivitySummary).count(),
        "app_versions": session.query(AppVersion).count(),
        "update_history": session.query(UpdateHistory).count(),
        "error_logs": session.query(ErrorLog).count(),
        "announcements": session.query(Announcement).count(),
        "user_feedback": session.query(UserFeedback).count(),
    }

    return counts


# ============================================================================
# Main Setup Function
# ============================================================================

def setup_database(use_postgres: bool = False, drop_existing: bool = False, echo: bool = False):
    """
    Complete database setup process.

    Args:
        use_postgres: If True, use PostgreSQL. Otherwise use SQLite.
        drop_existing: If True, drop all existing tables first.
        echo: If True, log all SQL statements.

    Returns:
        Tuple of (engine, session_maker).

    Example:
        >>> engine, session_maker = setup_database(use_postgres=False)
        >>> with get_db_session(session_maker) as db:
        >>>     # Perform database operations
        >>>     pass
    """
    logger.info("=" * 70)
    logger.info("DATABASE SETUP START")
    logger.info("=" * 70)

    # Create engine
    engine = create_database_engine(use_postgres=use_postgres, echo=echo)

    # Test connection
    if not test_connection(engine):
        raise ConnectionError("Failed to connect to database")

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

    parser = argparse.ArgumentParser(description="Database setup utility")
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Use PostgreSQL instead of SQLite"
    )
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
        logger.warning("⚠️  DROP EXISTING TABLES REQUESTED!")
        response = input("Are you sure? This will DELETE ALL DATA! (yes/no): ")
        if response.lower() != "yes":
            logger.info("Database setup cancelled")
            exit(0)

    # Run setup
    try:
        engine, session_maker = setup_database(
            use_postgres=args.postgres,
            drop_existing=args.drop,
            echo=args.echo
        )
        logger.success("✓ Database is ready for use")
    except Exception as e:
        logger.exception(f"Database setup failed: {e}")
        exit(1)
