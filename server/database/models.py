"""
Database Models for LocalizationTools Server

SQLAlchemy ORM models matching the database schema.
Supports PostgreSQL (online) and SQLite (offline mode).
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Float, Boolean, DateTime,
    ForeignKey, Index, Enum as SQLEnum, JSON, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

# Dialect-agnostic JSON type
# Uses JSONB on PostgreSQL (faster, indexable) and JSON on SQLite
class FlexibleJSON(TypeDecorator):
    """
    Dialect-agnostic JSON column type.

    - PostgreSQL: Uses JSONB (faster, indexable)
    - SQLite: Uses JSON (TEXT storage with JSON functions)

    This allows the same models to work with both databases.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

# Alias for backwards compatibility and clarity
JSONB = FlexibleJSON

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
    full_name = Column(String(100), nullable=True)  # Display name (e.g., "Sujin Park")
    department = Column(String(50), nullable=True, index=True)  # Legacy field
    team = Column(String(100), nullable=True, index=True)  # Team name (e.g., "Team ABC")
    language = Column(String(50), nullable=True, index=True)  # Primary work language (e.g., "Japanese")
    role = Column(String(20), default="user")  # user, admin, superadmin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)  # Admin who created this user
    last_login = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)  # Track password updates
    must_change_password = Column(Boolean, default=False)  # Force password change on first login

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    log_entries = relationship("LogEntry", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    created_users = relationship("User", backref="creator", remote_side=[user_id])  # Users created by this admin

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', team='{self.team}', language='{self.language}')>"


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
    file_info = Column(JSONB, nullable=True)  # {size_mb, rows, columns, etc.}
    parameters = Column(JSONB, nullable=True)  # Function parameters used

    # Relationships
    user = relationship("User", back_populates="log_entries")

    __table_args__ = (
        Index("idx_log_timestamp_tool", "timestamp", "tool_name"),
        Index("idx_log_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self):
        return f"<LogEntry(log_id={self.log_id}, user='{self.username}', tool='{self.tool_name}', function='{self.function_name}')>"


class ActiveOperation(Base):
    """Track currently running operations with real-time progress."""
    __tablename__ = "active_operations"

    operation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=False, index=True)

    # Operation info
    tool_name = Column(String(50), nullable=False, index=True)
    function_name = Column(String(100), nullable=False, index=True)
    operation_name = Column(String(200), nullable=False)  # Human-readable name

    # Progress tracking
    status = Column(String(20), default="running", index=True)  # running, completed, failed, cancelled
    progress_percentage = Column(Float, default=0.0)  # 0.0 to 100.0
    current_step = Column(String(200), nullable=True)  # "Processing row 150/500"
    total_steps = Column(Integer, nullable=True)  # Total number of steps if known
    completed_steps = Column(Integer, default=0)  # Steps completed so far

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)  # ETA based on progress

    # File/Data metadata
    file_info = Column(JSONB, nullable=True)  # Files being processed
    parameters = Column(JSONB, nullable=True)  # Operation parameters

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Result storage
    output_dir = Column(String(500), nullable=True)  # Directory where output files are saved
    output_files = Column(JSONB, nullable=True)  # List of output file paths/names

    __table_args__ = (
        Index("idx_active_status", "status"),
        Index("idx_active_user_started", "user_id", "started_at"),
    )

    def __repr__(self):
        return f"<ActiveOperation(operation_id={self.operation_id}, user='{self.username}', operation='{self.operation_name}', progress={self.progress_percentage}%)>"


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
    tools_used = Column(JSONB, nullable=True)  # List of tool names
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
    context = Column(JSONB, nullable=True)  # Additional context

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
    target_users = Column(JSONB, nullable=True)  # None = all users, or list of user_ids

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


# ============================================================================
# Telemetry Tables (Central Server - receives from Desktop Apps)
# ============================================================================

class Installation(Base):
    """
    Registered installations that send telemetry to Central Server.
    Each Desktop App registers once and gets an API key for communication.
    """
    __tablename__ = "installations"

    installation_id = Column(String(32), primary_key=True)  # Unique installation ID
    api_key_hash = Column(String(255), nullable=False)  # Hashed API key for security
    installation_name = Column(String(100), nullable=False, index=True)  # Human-readable name
    version = Column(String(20), nullable=False)  # App version at registration
    owner_email = Column(String(100), nullable=True, index=True)

    # Status tracking
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_version = Column(String(20), nullable=True)  # Most recent version reported

    # Extra data (OS, machine info, etc.)
    extra_data = Column(JSONB, nullable=True)

    # Relationships
    remote_sessions = relationship("RemoteSession", back_populates="installation", cascade="all, delete-orphan")
    remote_logs = relationship("RemoteLog", back_populates="installation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_installation_active", "is_active"),
        Index("idx_installation_last_seen", "last_seen"),
    )

    def __repr__(self):
        return f"<Installation(id='{self.installation_id}', name='{self.installation_name}', active={self.is_active})>"


class RemoteSession(Base):
    """
    Track user sessions from remote installations.
    A session starts when user opens the app and ends when they close it.
    """
    __tablename__ = "remote_sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    installation_id = Column(String(32), ForeignKey("installations.installation_id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, nullable=True)  # Calculated on end

    # Connection info
    ip_address = Column(String(45), nullable=True)
    app_version = Column(String(20), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    end_reason = Column(String(50), nullable=True)  # "user_closed", "timeout", "error"

    # Relationships
    installation = relationship("Installation", back_populates="remote_sessions")

    __table_args__ = (
        Index("idx_remote_session_active", "is_active"),
        Index("idx_remote_session_installation_started", "installation_id", "started_at"),
    )

    def __repr__(self):
        return f"<RemoteSession(id='{self.session_id}', installation='{self.installation_id}', active={self.is_active})>"


class RemoteLog(Base):
    """
    Store log entries received from remote installations.
    Central Server receives batches of logs from Desktop Apps.
    """
    __tablename__ = "remote_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    installation_id = Column(String(32), ForeignKey("installations.installation_id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Log data
    timestamp = Column(DateTime, nullable=False, index=True)  # Original timestamp from client
    level = Column(String(20), nullable=False, index=True)  # INFO, SUCCESS, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)  # Additional structured data

    # Source info
    source = Column(String(50), nullable=False, index=True)  # "locanext-app", "admin-dashboard"
    component = Column(String(100), nullable=True)  # Specific component/module

    # Server tracking
    received_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    installation = relationship("Installation", back_populates="remote_logs")

    __table_args__ = (
        Index("idx_remote_log_timestamp_level", "timestamp", "level"),
        Index("idx_remote_log_installation_timestamp", "installation_id", "timestamp"),
    )

    def __repr__(self):
        return f"<RemoteLog(id={self.log_id}, level='{self.level}', installation='{self.installation_id}')>"


class TelemetrySummary(Base):
    """
    Daily aggregated telemetry statistics per installation.
    Updated periodically by background job or on log submission.
    """
    __tablename__ = "telemetry_summary"

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)  # Date of summary (UTC midnight)
    installation_id = Column(String(32), ForeignKey("installations.installation_id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # Session stats
    total_sessions = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    avg_session_seconds = Column(Float, default=0.0)

    # Tool usage
    tools_used = Column(JSONB, nullable=True)  # {"xlstransfer": 5, "quicksearch": 3}
    total_operations = Column(Integer, default=0)

    # Error tracking
    info_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)

    # Update tracking
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_telemetry_date_installation", "date", "installation_id", unique=True),
    )

    def __repr__(self):
        return f"<TelemetrySummary(date='{self.date.date()}', installation='{self.installation_id}', sessions={self.total_sessions})>"


# ============================================================================
# LDM (LanguageData Manager) Tables
# ============================================================================

class LDMPlatform(Base):
    """
    LDM Platform - Top-level organization above Projects.

    Used to group projects by platform (PC, Mobile, Console, etc.)
    TM Explorer mirrors this structure for hierarchical TM assignment.

    Special platform_id=1 is reserved for "Unassigned" (TM safety net).
    """
    __tablename__ = "ldm_platforms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # DESIGN-001: Public by default permission model
    # False = public (all users can access), True = restricted (only assigned users)
    is_restricted = Column(Boolean, default=False, nullable=False)

    # Relationships
    owner = relationship("User")
    projects = relationship("LDMProject", back_populates="platform", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_platform_owner", "owner_id"),
        # DESIGN-001: Globally unique names (was per-owner)
        UniqueConstraint("name", name="uq_ldm_platform_name"),
    )

    def __repr__(self):
        return f"<LDMPlatform(id={self.id}, name='{self.name}')>"


class LDMProject(Base):
    """
    LDM Project - Container for organizing localization files.
    Now belongs to a Platform for hierarchical organization.
    """
    __tablename__ = "ldm_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    platform_id = Column(Integer, ForeignKey("ldm_platforms.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # DESIGN-001: Public by default permission model
    # False = public (all users can access), True = restricted (only assigned users)
    is_restricted = Column(Boolean, default=False, nullable=False)

    # Relationships
    owner = relationship("User")
    platform = relationship("LDMPlatform", back_populates="projects")
    folders = relationship("LDMFolder", back_populates="project", cascade="all, delete-orphan")
    files = relationship("LDMFile", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_project_owner", "owner_id"),
        Index("idx_ldm_project_platform", "platform_id"),
        # DB-002: Per-parent unique names (same name allowed in different platforms)
        UniqueConstraint("platform_id", "name", name="uq_ldm_project_platform_name"),
    )

    def __repr__(self):
        return f"<LDMProject(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


class LDMFolder(Base):
    """
    LDM Folder - Organize files within a project (tree structure).
    Supports nested folders via parent_id.
    """
    __tablename__ = "ldm_folders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("ldm_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("ldm_folders.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("LDMProject", back_populates="folders")
    parent = relationship("LDMFolder", remote_side=[id], backref="children")
    files = relationship("LDMFile", back_populates="folder", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_folder_project_parent", "project_id", "parent_id"),
        # DB-002: Per-parent unique names (same name allowed in different folders)
        UniqueConstraint("project_id", "parent_id", "name", name="uq_ldm_folder_parent_name"),
    )

    def __repr__(self):
        return f"<LDMFolder(id={self.id}, name='{self.name}', project_id={self.project_id})>"


class LDMFile(Base):
    """
    LDM File - Uploaded localization file stored in database.
    Original file parsed into LDMRow entries for editing.

    extra_data stores file-level metadata for FULL reconstruction:
    - TXT: {"encoding": "utf-8", "total_columns": 10, "column_headers": [...]}
    - XML: {"root_element": "LangData", "declaration": "<?xml...?>", "namespaces": {...}}
    - Excel: {"sheet_name": "...", "headers": [...], "total_columns": 5}
    """
    __tablename__ = "ldm_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("ldm_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_id = Column(Integer, ForeignKey("ldm_folders.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)  # Original uploaded filename
    format = Column(String(20), nullable=False)  # "txt", "xml", "xlsx"
    row_count = Column(Integer, default=0)
    source_language = Column(String(10), default="ko")  # Korean original
    target_language = Column(String(10), nullable=True)  # Translation target language
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    # File-level metadata for FULL reconstruction (preserves original structure)
    extra_data = Column(FlexibleJSON, nullable=True)

    # Relationships
    project = relationship("LDMProject", back_populates="files")
    folder = relationship("LDMFolder", back_populates="files")
    rows = relationship("LDMRow", back_populates="file", cascade="all, delete-orphan")
    creator = relationship("User")

    __table_args__ = (
        Index("idx_ldm_file_project_folder", "project_id", "folder_id"),
        # DB-002: Per-parent unique names (same name allowed in different folders)
        UniqueConstraint("project_id", "folder_id", "name", name="uq_ldm_file_folder_name"),
    )

    def __repr__(self):
        return f"<LDMFile(id={self.id}, name='{self.name}', rows={self.row_count})>"


class LDMRow(Base):
    """
    LDM Row - Single localization string (source + target).
    Source (StrOrigin) is READ-ONLY, Target (Str) is EDITABLE.

    extra_data stores additional columns/attributes for FULL file reconstruction:
    - TXT: columns beyond 0-6 → {"col7": "...", "col8": "..."}
    - XML: attributes beyond stringid/strorigin/str → {"attr1": "...", "attr2": "..."}
    - Excel: columns beyond A-B → {"C": "...", "D": "..."}
    """
    __tablename__ = "ldm_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("ldm_files.id", ondelete="CASCADE"), nullable=False, index=True)
    row_num = Column(Integer, nullable=False)  # Original row number in file
    string_id = Column(String(255), nullable=True, index=True)  # StringId attribute (may be null for TXT)

    # Source = Korean original (READ-ONLY)
    source = Column(Text, nullable=True)  # StrOrigin attribute or TXT index 5

    # Target = Translation (EDITABLE)
    target = Column(Text, nullable=True)  # Str attribute or TXT index 6

    # Status tracking
    status = Column(String(20), default="pending")  # pending, translated, reviewed, approved
    updated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # QA tracking (P2: Auto-LQA)
    qa_checked_at = Column(DateTime, nullable=True)  # Last QA check timestamp
    qa_flag_count = Column(Integer, default=0)  # Number of unresolved QA issues

    # Extra data for FULL file reconstruction (preserves ALL original data)
    extra_data = Column(FlexibleJSON, nullable=True)

    # Relationships
    file = relationship("LDMFile", back_populates="rows")
    editor = relationship("User")
    qa_results = relationship("LDMQAResult", back_populates="row", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_row_file_rownum", "file_id", "row_num"),
        Index("idx_ldm_row_file_stringid", "file_id", "string_id"),
        Index("idx_ldm_row_status", "status"),
        Index("idx_ldm_row_qa_flagged", "file_id", "qa_flag_count"),  # P2: QA filter
    )

    def __repr__(self):
        return f"<LDMRow(id={self.id}, file_id={self.file_id}, string_id='{self.string_id}', status='{self.status}')>"


class LDMEditHistory(Base):
    """
    LDM Edit History - Track all changes to rows for version control.
    Enables rollback and audit trail.
    """
    __tablename__ = "ldm_edit_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    row_id = Column(Integer, ForeignKey("ldm_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    old_target = Column(Text, nullable=True)
    new_target = Column(Text, nullable=True)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)

    edited_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    row = relationship("LDMRow")
    user = relationship("User")

    __table_args__ = (
        Index("idx_ldm_history_row_time", "row_id", "edited_at"),
    )

    def __repr__(self):
        return f"<LDMEditHistory(id={self.id}, row_id={self.row_id}, edited_at='{self.edited_at}')>"


class LDMQAResult(Base):
    """
    LDM QA Result - Individual QA issue on a row.

    P2: Auto-LQA System
    Stores QA check results (line, term, pattern, character, grammar).
    Each row can have multiple QA results from different check types.
    """
    __tablename__ = "ldm_qa_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    row_id = Column(Integer, ForeignKey("ldm_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("ldm_files.id", ondelete="CASCADE"), nullable=False, index=True)

    # Check info
    check_type = Column(String(50), nullable=False)  # 'line', 'term', 'pattern', 'character', 'grammar'
    severity = Column(String(20), default="warning")  # 'error', 'warning', 'info'
    message = Column(Text, nullable=False)  # Human-readable issue description
    details = Column(FlexibleJSON, nullable=True)  # Check-specific data (e.g., expected term, pattern details)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)  # NULL = unresolved

    # Resolution info
    resolved_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    # Relationships
    row = relationship("LDMRow", back_populates="qa_results")
    file = relationship("LDMFile")
    resolver = relationship("User")

    __table_args__ = (
        Index("idx_qa_result_row", "row_id"),
        Index("idx_qa_result_file", "file_id"),
        Index("idx_qa_result_file_type", "file_id", "check_type"),
        Index("idx_qa_result_unresolved", "file_id", "resolved_at"),  # Filter unresolved
        # Prevent duplicate identical issues on same row
        Index("idx_qa_result_unique", "row_id", "check_type", "message", unique=True),
    )

    def __repr__(self):
        return f"<LDMQAResult(id={self.id}, row_id={self.row_id}, type='{self.check_type}', severity='{self.severity}')>"


class LDMActiveSession(Base):
    """
    LDM Active Session - Track who's viewing/editing which file.
    Used for presence indicators and row locking.
    """
    __tablename__ = "ldm_active_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("ldm_files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Current position
    cursor_row = Column(Integer, nullable=True)  # Row user is viewing
    editing_row = Column(Integer, nullable=True)  # Row user has locked for editing (modal open)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    file = relationship("LDMFile")
    user = relationship("User")

    __table_args__ = (
        Index("idx_ldm_session_file", "file_id"),
        Index("idx_ldm_session_user", "user_id"),
    )

    def __repr__(self):
        return f"<LDMActiveSession(file_id={self.file_id}, user_id={self.user_id}, editing_row={self.editing_row})>"


# =============================================================================
# LDM Translation Memory Tables (Phase 7)
# =============================================================================

class LDMTranslationMemory(Base):
    """
    LDM Translation Memory - Container for TM entries.
    Each TM can have millions of source/target pairs with FAISS indexes.
    """
    __tablename__ = "ldm_translation_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Source/Target language codes
    source_lang = Column(String(10), default="ko")  # Korean
    target_lang = Column(String(10), default="en")  # English

    # Stats (updated after indexing)
    entry_count = Column(Integer, default=0)
    whole_pairs = Column(Integer, default=0)  # Entries in whole_text index
    line_pairs = Column(Integer, default=0)   # Entries in line index

    # Status: pending → indexing → ready → error
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)

    # TM Mode: "standard" (duplicates merged) or "stringid" (all variations kept)
    mode = Column(String(20), default="standard")

    # Index storage paths (relative to TM storage root)
    storage_path = Column(String(500), nullable=True)  # Base path for this TM's files
    # Index files stored at: {storage_path}/whole.index, {storage_path}/line.index, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)  # When indexing completed

    # Relationships
    owner = relationship("User")
    entries = relationship("LDMTMEntry", back_populates="tm", cascade="all, delete-orphan")
    active_links = relationship("LDMActiveTM", back_populates="tm", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_tm_owner", "owner_id"),
        Index("idx_ldm_tm_status", "status"),
        # DESIGN-001: Globally unique TM names (no duplicates anywhere)
        UniqueConstraint("name", name="uq_ldm_tm_name"),
    )

    def __repr__(self):
        return f"<LDMTranslationMemory(id={self.id}, name='{self.name}', entries={self.entry_count}, status='{self.status}')>"


class LDMTMEntry(Base):
    """
    LDM TM Entry - Single source/target translation pair.
    Hash indexes for O(1) exact match lookup.
    """
    __tablename__ = "ldm_tm_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id", ondelete="CASCADE"), nullable=False, index=True)

    # Translation pair
    source_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=True)

    # Hash for exact lookup (SHA256 of normalized source)
    source_hash = Column(String(64), nullable=False, index=True)

    # StringID for context-aware matching (same source, different targets based on context)
    # Used in "stringid" mode TMs - allows same source to have multiple translations
    string_id = Column(String(255), nullable=True, index=True)

    # Optional metadata from TMX
    created_by = Column(String(255), nullable=True)  # creationid from TMX
    change_date = Column(DateTime, nullable=True)    # changedate from TMX

    # Import timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # BUG-020: memoQ-style metadata for confirmation workflow
    # Modification tracking (when entry edited in TM Viewer)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)

    # Confirmation tracking (when user approves translation - memoQ workflow)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(255), nullable=True)
    is_confirmed = Column(Boolean, default=False, nullable=False)

    # Relationships
    tm = relationship("LDMTranslationMemory", back_populates="entries")

    __table_args__ = (
        Index("idx_ldm_tm_entry_tm", "tm_id"),
        Index("idx_ldm_tm_entry_hash", "source_hash"),
        Index("idx_ldm_tm_entry_tm_hash", "tm_id", "source_hash"),  # Composite for TM-specific lookup
        Index("idx_ldm_tm_entry_stringid", "string_id"),  # For StringID mode lookups
        Index("idx_ldm_tm_entry_tm_hash_stringid", "tm_id", "source_hash", "string_id"),  # Full composite
        Index("idx_ldm_tm_entry_confirmed", "tm_id", "is_confirmed"),  # BUG-020: Filter by confirmation status
    )

    def __repr__(self):
        src_preview = self.source_text[:30] + "..." if len(self.source_text or "") > 30 else self.source_text
        return f"<LDMTMEntry(id={self.id}, tm_id={self.tm_id}, source='{src_preview}')>"


class LDMActiveTM(Base):
    """
    LDM Active TM - Links active TMs to projects/files.
    A project can have multiple TMs active with priority ordering.
    """
    __tablename__ = "ldm_active_tms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id", ondelete="CASCADE"), nullable=False, index=True)

    # Can be linked to project OR specific file (one must be set)
    project_id = Column(Integer, ForeignKey("ldm_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    file_id = Column(Integer, ForeignKey("ldm_files.id", ondelete="CASCADE"), nullable=True, index=True)

    # Priority order (lower = higher priority, searched first)
    priority = Column(Integer, default=0)

    # Who activated this TM
    activated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    activated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tm = relationship("LDMTranslationMemory", back_populates="active_links")
    project = relationship("LDMProject")
    file = relationship("LDMFile")

    __table_args__ = (
        Index("idx_ldm_active_tm_project", "project_id"),
        Index("idx_ldm_active_tm_file", "file_id"),
        # Ensure a TM is only linked once per project/file
        Index("idx_ldm_active_tm_unique", "tm_id", "project_id", "file_id", unique=True),
    )

    def __repr__(self):
        target = f"project={self.project_id}" if self.project_id else f"file={self.file_id}"
        return f"<LDMActiveTM(tm_id={self.tm_id}, {target}, priority={self.priority})>"


class LDMTMAssignment(Base):
    """
    LDM TM Assignment - Hierarchical TM assignment to Platform/Project/Folder.

    TM Hierarchy System:
    - TMs can be assigned to Platform, Project, or Folder level
    - Only ONE scope should be set (others NULL) - or ALL NULL for "Unassigned"
    - Activation cascades down: TM active at Project applies to all folders/files
    - TM Explorer mirrors File Explorer structure (read-only)

    Scope Resolution (for file):
    1. Check folder-level TMs (walk up to root)
    2. Check project-level TMs
    3. Check platform-level TMs
    All active TMs in chain contribute matches.
    """
    __tablename__ = "ldm_tm_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scope: Only ONE should be set (NULL = unassigned)
    platform_id = Column(Integer, ForeignKey("ldm_platforms.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("ldm_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(Integer, ForeignKey("ldm_folders.id", ondelete="SET NULL"), nullable=True, index=True)

    # Activation status
    is_active = Column(Boolean, default=False, nullable=False)

    # Priority (lower = higher priority when multiple TMs at same scope)
    priority = Column(Integer, default=0)

    # Metadata
    assigned_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)

    # Relationships
    tm = relationship("LDMTranslationMemory")
    platform = relationship("LDMPlatform")
    project = relationship("LDMProject")
    folder = relationship("LDMFolder")

    __table_args__ = (
        Index("idx_tm_assignment_tm", "tm_id"),
        Index("idx_tm_assignment_platform", "platform_id"),
        Index("idx_tm_assignment_project", "project_id"),
        Index("idx_tm_assignment_folder", "folder_id"),
        Index("idx_tm_assignment_active", "is_active"),
        # Each TM can only be assigned to one scope at a time
        UniqueConstraint("tm_id", name="uq_tm_assignment_tm"),
    )

    def __repr__(self):
        if self.folder_id:
            scope = f"folder={self.folder_id}"
        elif self.project_id:
            scope = f"project={self.project_id}"
        elif self.platform_id:
            scope = f"platform={self.platform_id}"
        else:
            scope = "unassigned"
        active = "ACTIVE" if self.is_active else "inactive"
        return f"<LDMTMAssignment(tm_id={self.tm_id}, {scope}, {active})>"


# =============================================================================
# Database Backup & Safety Tables
# =============================================================================

class LDMBackup(Base):
    """
    LDM Backup - Track database backups for disaster recovery.
    Automated backups before major operations + scheduled backups.
    """
    __tablename__ = "ldm_backups"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # What was backed up
    backup_type = Column(String(50), nullable=False)  # "full", "project", "file", "tm"
    project_id = Column(Integer, nullable=True)  # If project-specific backup
    file_id = Column(Integer, nullable=True)     # If file-specific backup
    tm_id = Column(Integer, nullable=True)       # If TM-specific backup

    # Backup file location
    backup_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=True)  # Bytes

    # Status
    status = Column(String(50), default="completed")  # completed, failed, restoring
    error_message = Column(Text, nullable=True)

    # Trigger info
    trigger = Column(String(100), nullable=True)  # "scheduled", "pre_delete", "manual", "pre_import"
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Retention
    expires_at = Column(DateTime, nullable=True)  # Auto-delete after this date

    __table_args__ = (
        Index("idx_ldm_backup_type", "backup_type"),
        Index("idx_ldm_backup_created", "created_at"),
    )

    def __repr__(self):
        return f"<LDMBackup(id={self.id}, type='{self.backup_type}', status='{self.status}')>"


class LDMTrash(Base):
    """
    LDM Trash Bin - Soft delete for projects, folders, files, and TMs.

    User-friendly recycle bin:
    - Items stay in trash for 30 days (configurable)
    - Easy 1-click restore from UI
    - Permanent delete after expiration
    - Preserves full data for restore
    """
    __tablename__ = "ldm_trash"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # What was deleted
    item_type = Column(String(50), nullable=False)  # "project", "folder", "file", "tm"
    item_id = Column(Integer, nullable=False)       # Original ID
    item_name = Column(String(255), nullable=False) # Name for display

    # Parent info (for restoring to correct location)
    parent_project_id = Column(Integer, nullable=True)  # Project it belonged to
    parent_folder_id = Column(Integer, nullable=True)   # Folder it was in

    # Full data snapshot (JSON) for restore
    item_data = Column(JSONB, nullable=False)  # JSON of the deleted item + children

    # Who deleted it
    deleted_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Auto-expire (permanent delete after this date)
    expires_at = Column(DateTime, nullable=False)  # Default: 30 days from deletion

    # Status
    status = Column(String(50), default="trashed")  # trashed, restored, expired

    __table_args__ = (
        Index("idx_ldm_trash_type", "item_type"),
        Index("idx_ldm_trash_deleted_by", "deleted_by"),
        Index("idx_ldm_trash_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<LDMTrash(id={self.id}, type='{self.item_type}', name='{self.item_name}')>"


# =============================================================================
# LDM Index Tracking (for TM FAISS indexes)
# =============================================================================

class LDMTMIndex(Base):
    """
    LDM TM Index - Track FAISS index files for TMs.

    Each TM can have multiple indexes:
    - whole.index (whole text embeddings)
    - line.index (line-by-line embeddings)
    - whole_text_lookup.pkl (hash lookup)
    - line_lookup.pkl (line hash lookup)
    """
    __tablename__ = "ldm_tm_indexes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tm_id = Column(Integer, ForeignKey("ldm_translation_memories.id", ondelete="CASCADE"), nullable=False, index=True)

    # Index type
    index_type = Column(String(50), nullable=False)  # "whole_faiss", "line_faiss", "whole_hash", "line_hash"
    index_path = Column(String(500), nullable=False)  # Path to index file

    # Stats
    entry_count = Column(Integer, default=0)  # Entries in this index
    file_size = Column(BigInteger, nullable=True)  # Bytes

    # Status
    status = Column(String(50), default="building")  # building, ready, error
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    built_at = Column(DateTime, nullable=True)  # When build completed

    __table_args__ = (
        Index("idx_ldm_tm_index_tm", "tm_id"),
        Index("idx_ldm_tm_index_type", "tm_id", "index_type", unique=True),
    )

    def __repr__(self):
        return f"<LDMTMIndex(tm_id={self.tm_id}, type='{self.index_type}', status='{self.status}')>"


# =============================================================================
# LDM Resource Access Control (DESIGN-001)
# =============================================================================

class LDMResourceAccess(Base):
    """
    LDM Resource Access - Explicit access grants for restricted platforms/projects.

    DESIGN-001: Public by Default Permission Model
    - Only needed for restricted resources (is_restricted=True)
    - Public resources (is_restricted=False) are accessible to all users
    - Admins bypass restrictions entirely
    - Owner of a resource always has access

    Only ONE of platform_id or project_id should be set (not both).
    """
    __tablename__ = "ldm_resource_access"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Resource being accessed (only ONE should be set)
    platform_id = Column(Integer, ForeignKey("ldm_platforms.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("ldm_projects.id", ondelete="CASCADE"), nullable=True, index=True)

    # User granted access
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Access level (for future expansion: read, write, admin)
    access_level = Column(String(20), default="full")

    # Audit fields
    granted_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    platform = relationship("LDMPlatform", foreign_keys=[platform_id])
    project = relationship("LDMProject", foreign_keys=[project_id])
    user = relationship("User", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        Index("idx_resource_access_platform", "platform_id", "user_id"),
        Index("idx_resource_access_project", "project_id", "user_id"),
        # Prevent duplicate grants
        UniqueConstraint("platform_id", "user_id", name="uq_resource_access_platform_user"),
        UniqueConstraint("project_id", "user_id", name="uq_resource_access_project_user"),
    )

    def __repr__(self):
        resource = f"platform_id={self.platform_id}" if self.platform_id else f"project_id={self.project_id}"
        return f"<LDMResourceAccess({resource}, user_id={self.user_id})>"
