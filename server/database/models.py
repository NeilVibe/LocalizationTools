"""
Database Models for LocalizationTools Server

SQLAlchemy ORM models matching the database schema.
Supports both SQLite (dev) and PostgreSQL (prod).
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

Base = declarative_base()


# ============================================================================
# Core Tables
# ============================================================================

class User(Base):
    """User accounts with authentication and profile info."""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(100), nullable=True)
    department = Column(String(50), nullable=True, index=True)
    role = Column(String(20), default="user")  # user, admin, superadmin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    log_entries = relationship("LogEntry", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', department='{self.department}')>"


class Session(Base):
    """Active user sessions tracking."""
    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    machine_id = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    app_version = Column(String(20), nullable=False)
    session_start = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id}, machine_id='{self.machine_id}')>"


class LogEntry(Base):
    """Main usage logs - every tool execution recorded."""
    __tablename__ = "log_entries"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=False, index=True)
    machine_id = Column(String(64), nullable=False, index=True)

    # Tool/Function info
    tool_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(100), nullable=False, index=True)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    duration_seconds = Column(Float, nullable=False)

    # Operation details
    status = Column(String(20), default="success")  # success, error, warning
    error_message = Column(Text, nullable=True)

    # File/Data metadata (JSONB for flexibility)
    file_info = Column(JSON, nullable=True)  # {size_mb, rows, columns, etc.}
    parameters = Column(JSON, nullable=True)  # Function parameters used

    # Relationships
    user = relationship("User", back_populates="log_entries")

    __table_args__ = (
        Index("idx_log_timestamp_tool", "timestamp", "tool_name"),
        Index("idx_log_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self):
        return f"<LogEntry(log_id={self.log_id}, user='{self.username}', tool='{self.tool_name}', function='{self.function_name}')>"


# ============================================================================
# Analytics Tables
# ============================================================================

class ToolUsageStats(Base):
    """Daily aggregated statistics per tool."""
    __tablename__ = "tool_usage_stats"

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    tool_name = Column(String(50), nullable=False, index=True)

    total_uses = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    total_duration_seconds = Column(Float, default=0.0)
    avg_duration_seconds = Column(Float, default=0.0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_tool_stats_date_tool", "date", "tool_name"),
    )

    def __repr__(self):
        return f"<ToolUsageStats(date='{self.date.date()}', tool='{self.tool_name}', uses={self.total_uses})>"


class FunctionUsageStats(Base):
    """Function-level usage statistics."""
    __tablename__ = "function_usage_stats"

    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    tool_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(100), nullable=False, index=True)

    total_uses = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    total_duration_seconds = Column(Float, default=0.0)
    avg_duration_seconds = Column(Float, default=0.0)
    min_duration_seconds = Column(Float, nullable=True)
    max_duration_seconds = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_func_stats_date_tool_func", "date", "tool_name", "function_name"),
    )

    def __repr__(self):
        return f"<FunctionUsageStats(date='{self.date.date()}', function='{self.function_name}', uses={self.total_uses})>"


class PerformanceMetrics(Base):
    """Detailed performance data (CPU, memory, processing times)."""
    __tablename__ = "performance_metrics"

    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tool_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(100), nullable=False)

    duration_seconds = Column(Float, nullable=False)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_mb = Column(Float, nullable=True)

    file_size_mb = Column(Float, nullable=True)
    rows_processed = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_perf_timestamp_tool", "timestamp", "tool_name"),
    )

    def __repr__(self):
        return f"<PerformanceMetrics(tool='{self.tool_name}', duration={self.duration_seconds:.2f}s)>"


class UserActivitySummary(Base):
    """Daily active user tracking."""
    __tablename__ = "user_activity_summary"

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(50), nullable=False)

    total_operations = Column(Integer, default=0)
    total_duration_seconds = Column(Float, default=0.0)
    tools_used = Column(JSON, nullable=True)  # List of tool names
    first_activity = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_activity_date_user", "date", "user_id"),
    )

    def __repr__(self):
        return f"<UserActivitySummary(date='{self.date.date()}', user='{self.username}', ops={self.total_operations})>"


# ============================================================================
# Management Tables
# ============================================================================

class AppVersion(Base):
    """Version management and update tracking."""
    __tablename__ = "app_versions"

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    version_number = Column(String(20), unique=True, nullable=False)
    release_date = Column(DateTime, default=datetime.utcnow)
    is_latest = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)  # Force update
    release_notes = Column(Text, nullable=True)
    download_url = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<AppVersion(version='{self.version_number}', latest={self.is_latest})>"


class UpdateHistory(Base):
    """Track when users update their app."""
    __tablename__ = "update_history"

    update_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    from_version = Column(String(20), nullable=False)
    to_version = Column(String(20), nullable=False)
    update_timestamp = Column(DateTime, default=datetime.utcnow)
    machine_id = Column(String(64), nullable=False)

    def __repr__(self):
        return f"<UpdateHistory(user_id={self.user_id}, {self.from_version} → {self.to_version})>"


class ErrorLog(Base):
    """Detailed error tracking with stack traces."""
    __tablename__ = "error_logs"

    error_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    machine_id = Column(String(64), nullable=False)

    tool_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(100), nullable=False)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)

    app_version = Column(String(20), nullable=False)
    context = Column(JSON, nullable=True)  # Additional context

    __table_args__ = (
        Index("idx_error_timestamp_tool", "timestamp", "tool_name"),
    )

    def __repr__(self):
        return f"<ErrorLog(error_id={self.error_id}, tool='{self.tool_name}', type='{self.error_type}')>"


class Announcement(Base):
    """Push notifications to users."""
    __tablename__ = "announcements"

    announcement_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default="info")  # info, warning, critical
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    target_users = Column(JSON, nullable=True)  # None = all users, or list of user_ids

    def __repr__(self):
        return f"<Announcement(id={self.announcement_id}, title='{self.title}', priority='{self.priority}')>"


class UserFeedback(Base):
    """Collect feedback and feature requests."""
    __tablename__ = "user_feedback"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    feedback_type = Column(String(20), nullable=False)  # bug, feature, comment
    tool_name = Column(String(50), nullable=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 stars

    status = Column(String(20), default="open")  # open, reviewed, implemented, closed
    admin_response = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="feedback")

    def __repr__(self):
        return f"<UserFeedback(id={self.feedback_id}, type='{self.feedback_type}', status='{self.status}')>"
