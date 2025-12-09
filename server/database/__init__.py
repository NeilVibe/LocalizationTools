"""
Database Package

Clean exports for database models, setup, and utilities.
"""

from server.database.models import (
    Base,
    # Core tables
    User,
    Session,
    LogEntry,
    ActiveOperation,
    # Analytics tables
    ToolUsageStats,
    FunctionUsageStats,
    PerformanceMetrics,
    UserActivitySummary,
    # Management tables
    AppVersion,
    UpdateHistory,
    ErrorLog,
    Announcement,
    UserFeedback,
    # Telemetry tables (Central Server)
    Installation,
    RemoteSession,
    RemoteLog,
    TelemetrySummary,
)

from server.database.db_setup import (
    get_database_url,
    create_database_engine,
    initialize_database,
    get_session_maker,
    get_db_session,
    test_connection,
    get_table_counts,
    setup_database,
)

from server.database.db_utils import (
    # Batch operations
    bulk_insert,
    bulk_insert_tm_entries,
    bulk_insert_rows,
    # Text utilities
    normalize_text_for_hash,
    # FTS
    search_rows_fts,
    add_fts_indexes,
    add_trigram_index,
    is_postgresql,
    # Query helpers
    chunked_query,
    upsert_batch,
)

__all__ = [
    # Models
    "Base",
    "User",
    "Session",
    "LogEntry",
    "ActiveOperation",
    "ToolUsageStats",
    "FunctionUsageStats",
    "PerformanceMetrics",
    "UserActivitySummary",
    "AppVersion",
    "UpdateHistory",
    "ErrorLog",
    "Announcement",
    "UserFeedback",
    # Telemetry tables
    "Installation",
    "RemoteSession",
    "RemoteLog",
    "TelemetrySummary",
    # Setup functions
    "get_database_url",
    "create_database_engine",
    "initialize_database",
    "get_session_maker",
    "get_db_session",
    "test_connection",
    "get_table_counts",
    "setup_database",
    # DB Utilities (batch operations, FTS)
    "bulk_insert",
    "bulk_insert_tm_entries",
    "bulk_insert_rows",
    "normalize_text_for_hash",
    "search_rows_fts",
    "add_fts_indexes",
    "add_trigram_index",
    "is_postgresql",
    "chunked_query",
    "upsert_batch",
]
