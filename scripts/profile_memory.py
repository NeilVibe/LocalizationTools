#!/usr/bin/env python3
"""
Memory Profiling

Profile memory usage of server and client components.
"""

import sys
from pathlib import Path
import tracemalloc
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def profile_database_operations():
    """Profile memory usage of database operations."""
    logger.info("Profiling database operations...")

    tracemalloc.start()

    # Import after starting tracemalloc
    from server.database.db_setup import setup_database

    # Snapshot 1: Before database setup
    snapshot1 = tracemalloc.take_snapshot()

    # Setup database
    engine, session_maker = setup_database(use_postgres=False, drop_existing=False)

    # Snapshot 2: After database setup
    snapshot2 = tracemalloc.take_snapshot()

    # Create session and do some queries
    db = session_maker()
    from server.database.models import User, LogEntry

    # Query operations
    users = db.query(User).all()
    logs = db.query(LogEntry).limit(100).all()
    db.close()

    # Snapshot 3: After queries
    snapshot3 = tracemalloc.take_snapshot()

    # Compare snapshots
    top_stats1 = snapshot2.compare_to(snapshot1, 'lineno')
    top_stats2 = snapshot3.compare_to(snapshot2, 'lineno')

    logger.info("\nTop 5 memory increases (database setup):")
    for stat in top_stats1[:5]:
        logger.info(f"  {stat}")

    logger.info("\nTop 5 memory increases (queries):")
    for stat in top_stats2[:5]:
        logger.info(f"  {stat}")

    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"\nCurrent memory usage: {current / 1024 / 1024:.2f} MB")
    logger.info(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()


def profile_xls_transfer_modules():
    """Profile memory usage of XLSTransfer modules."""
    logger.info("\nProfiling XLSTransfer modules...")

    tracemalloc.start()

    # Snapshot before import
    snapshot1 = tracemalloc.take_snapshot()

    # Import modules
    from client.tools.xls_transfer import core, embeddings, translation, excel_utils

    # Snapshot after import
    snapshot2 = tracemalloc.take_snapshot()

    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    logger.info("\nTop 5 memory increases (module imports):")
    for stat in top_stats[:5]:
        logger.info(f"  {stat}")

    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"\nCurrent memory usage: {current / 1024 / 1024:.2f} MB")
    logger.info(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()


def profile_server_imports():
    """Profile memory usage of server imports."""
    logger.info("\nProfiling server imports...")

    tracemalloc.start()

    snapshot1 = tracemalloc.take_snapshot()

    # Import server modules
    from server.main import app
    from server.api import auth, logs, sessions

    snapshot2 = tracemalloc.take_snapshot()

    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    logger.info("\nTop 5 memory increases (server imports):")
    for stat in top_stats[:5]:
        logger.info(f"  {stat}")

    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"\nCurrent memory usage: {current / 1024 / 1024:.2f} MB")
    logger.info(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()


def main():
    """Run memory profiling."""
    logger.info("=" * 80)
    logger.info("MEMORY PROFILING")
    logger.info("=" * 80)

    # Profile different components
    profile_database_operations()
    profile_xls_transfer_modules()
    profile_server_imports()

    logger.info("\n" + "=" * 80)
    logger.success("✓ PROFILING COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
