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

__all__ = [
    # Models
    "Base",
    "User",
    "Session",
    "LogEntry",
    "ToolUsageStats",
    "FunctionUsageStats",
    "PerformanceMetrics",
    "UserActivitySummary",
    "AppVersion",
    "UpdateHistory",
    "ErrorLog",
    "Announcement",
    "UserFeedback",
    # Setup functions
    "get_database_url",
    "create_database_engine",
    "initialize_database",
    "get_session_maker",
    "get_db_session",
    "test_connection",
    "get_table_counts",
    "setup_database",
]
