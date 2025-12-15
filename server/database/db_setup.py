"""
Database Setup and Initialization

Handles database creation, connection management, and initialization.
Supports PostgreSQL (online) and SQLite (offline mode - P33).

Auto-fallback: If DATABASE_MODE=auto and PostgreSQL is unreachable,
automatically falls back to SQLite for offline operation.
"""

import os
import socket
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from server.database.models import Base
from server import config


# ============================================================================
# PostgreSQL Connectivity Check
# ============================================================================

def check_postgresql_reachable(timeout: int = 3) -> bool:
    """
    Quick check if PostgreSQL server is reachable.

    Uses socket connection to check if the port is open.
    Faster than trying a full database connection.

    Args:
        timeout: Connection timeout in seconds

    Returns:
        True if PostgreSQL server is reachable
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((config.POSTGRES_HOST, config.POSTGRES_PORT))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"PostgreSQL reachability check failed: {e}")
        return False


def test_postgresql_connection(timeout: int = 3) -> bool:
    """
    Test actual PostgreSQL database connection.

    Args:
        timeout: Connection timeout in seconds

    Returns:
        True if connection successful
    """
    try:
        # Create engine with short timeout
        engine = create_engine(
            config.POSTGRES_DATABASE_URL,
            connect_args={"connect_timeout": timeout},
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception as e:
        logger.debug(f"PostgreSQL connection test failed: {e}")
        return False


# ============================================================================
# Database Engine Creation
# ============================================================================

def get_database_url() -> str:
    """
    Get the active database connection URL.

    Returns:
        Database connection URL string.
    """
    return config.DATABASE_URL


def create_database_engine(echo: bool = False, db_url: str = None):
    """
    Create SQLAlchemy database engine.

    Automatically detects database type from URL and configures appropriately.

    Args:
        echo: If True, log all SQL statements (verbose).
        db_url: Optional database URL (uses config.DATABASE_URL if not provided)

    Returns:
        SQLAlchemy Engine instance.
    """
    if db_url is None:
        db_url = config.DATABASE_URL

    is_sqlite = db_url.startswith("sqlite")

    if is_sqlite:
        # SQLite configuration
        engine = create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False}  # Allow multi-thread access
        )

        # Enable foreign keys for SQLite (disabled by default)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info(f"SQLite engine created: {db_url}")
    else:
        # PostgreSQL configuration
        engine = create_engine(
            db_url,
            echo=echo,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_timeout=config.DB_POOL_TIMEOUT,
            pool_recycle=config.DB_POOL_RECYCLE,
            pool_pre_ping=True
        )
        logger.info(f"PostgreSQL engine created: {engine.url.database}")

    return engine


def create_sqlite_engine(echo: bool = False):
    """
    Create SQLite engine for offline mode.

    Args:
        echo: If True, log all SQL statements.

    Returns:
        SQLAlchemy Engine instance for SQLite.
    """
    return create_database_engine(echo=echo, db_url=config.SQLITE_DATABASE_URL)


def create_postgresql_engine(echo: bool = False):
    """
    Create PostgreSQL engine for online mode.

    Args:
        echo: If True, log all SQL statements.

    Returns:
        SQLAlchemy Engine instance for PostgreSQL.
    """
    return create_database_engine(echo=echo, db_url=config.POSTGRES_DATABASE_URL)


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


def is_postgresql(session_or_engine) -> bool:
    """
    Check if the database is PostgreSQL.

    Args:
        session_or_engine: SQLAlchemy session or engine

    Returns:
        True if PostgreSQL, False if SQLite or other
    """
    return config.ACTIVE_DATABASE_TYPE == "postgresql"


def is_sqlite(session_or_engine) -> bool:
    """
    Check if the database is SQLite.

    Args:
        session_or_engine: SQLAlchemy session or engine

    Returns:
        True if SQLite, False otherwise
    """
    return config.ACTIVE_DATABASE_TYPE == "sqlite"


# ============================================================================
# Main Setup Function
# ============================================================================

def setup_database(
    drop_existing: bool = False,
    echo: bool = False,
    force_mode: str = None
) -> Tuple[Engine, sessionmaker]:
    """
    Complete database setup process with auto-fallback.

    P33 Offline Mode:
    - If DATABASE_MODE=auto and PostgreSQL unreachable → use SQLite
    - If DATABASE_MODE=postgresql → fail if unreachable
    - If DATABASE_MODE=sqlite → use SQLite directly

    Args:
        drop_existing: If True, drop all existing tables first.
        echo: If True, log all SQL statements.
        force_mode: Override DATABASE_MODE ("postgresql" or "sqlite")

    Returns:
        Tuple of (engine, session_maker).

    Raises:
        ConnectionError: If PostgreSQL required but unreachable.

    Example:
        >>> engine, session_maker = setup_database()
        >>> with get_db_session(session_maker) as db:
        >>>     # Perform database operations
        >>>     pass
    """
    logger.info("=" * 70)
    logger.info("DATABASE SETUP START")
    logger.info("=" * 70)

    mode = force_mode or config.DATABASE_MODE
    logger.info(f"Database mode: {mode}")

    # Determine which database to use
    use_sqlite = False
    db_url = None

    if mode == "sqlite":
        # Force SQLite mode
        use_sqlite = True
        db_url = config.SQLITE_DATABASE_URL
        logger.info("Using SQLite (forced by DATABASE_MODE=sqlite)")

    elif mode == "postgresql":
        # Force PostgreSQL - fail if unreachable
        logger.info("Checking PostgreSQL connection...")
        if not test_postgresql_connection(config.POSTGRES_CONNECT_TIMEOUT):
            raise ConnectionError(
                f"Failed to connect to PostgreSQL at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}. "
                f"DATABASE_MODE=postgresql requires PostgreSQL to be available."
            )
        db_url = config.POSTGRES_DATABASE_URL
        logger.success("PostgreSQL connection verified")

    else:  # mode == "auto"
        # Auto mode: try PostgreSQL, fallback to SQLite
        logger.info("Auto mode: Checking PostgreSQL availability...")

        if check_postgresql_reachable(config.POSTGRES_CONNECT_TIMEOUT):
            # PostgreSQL server is reachable, try full connection
            if test_postgresql_connection(config.POSTGRES_CONNECT_TIMEOUT):
                db_url = config.POSTGRES_DATABASE_URL
                logger.success("PostgreSQL available - using online mode")
            else:
                logger.warning("PostgreSQL reachable but connection failed - falling back to SQLite")
                use_sqlite = True
        else:
            logger.warning(f"PostgreSQL not reachable at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}")
            use_sqlite = True

        if use_sqlite:
            db_url = config.SQLITE_DATABASE_URL
            logger.info("Using SQLite for offline mode")

    # Update global config with active database
    db_type = "sqlite" if use_sqlite else "postgresql"
    config.set_active_database(db_type, db_url)

    # Create engine
    engine = create_database_engine(echo=echo, db_url=db_url)

    # Test connection
    if not test_connection(engine):
        raise ConnectionError(f"Failed to connect to {db_type} database")

    # Initialize tables
    initialize_database(engine, drop_existing=drop_existing)

    # Create session maker
    session_maker = get_session_maker(engine)

    # Verify tables
    SessionLocal = session_maker()
    try:
        counts = get_table_counts(SessionLocal)
        logger.info("Table row counts:")
        for table, count in list(counts.items())[:5]:  # Show first 5 tables
            logger.info(f"  {table}: {count}")
        if len(counts) > 5:
            logger.info(f"  ... and {len(counts) - 5} more tables")
    finally:
        SessionLocal.close()

    logger.info("=" * 70)
    logger.success(f"DATABASE SETUP COMPLETE ({db_type.upper()})")
    logger.info("=" * 70)

    return engine, session_maker


# ============================================================================
# CLI for Direct Execution
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database setup utility")
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
    parser.add_argument(
        "--mode",
        choices=["auto", "postgresql", "sqlite"],
        help="Force database mode (overrides DATABASE_MODE env var)"
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
            echo=args.echo,
            force_mode=args.mode
        )
        logger.success(f"Database is ready for use ({config.ACTIVE_DATABASE_TYPE})")
    except Exception as e:
        logger.exception(f"Database setup failed: {e}")
        exit(1)
