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
    file_info = Column(JSON, nullable=True)  # Files being processed
    parameters = Column(JSON, nullable=True)  # Operation parameters

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Result storage
    output_dir = Column(String(500), nullable=True)  # Directory where output files are saved
    output_files = Column(JSON, nullable=True)  # List of output file paths/names

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
    extra_data = Column(JSON, nullable=True)

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
    data = Column(JSON, nullable=True)  # Additional structured data

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
    tools_used = Column(JSON, nullable=True)  # {"xlstransfer": 5, "quicksearch": 3}
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

class LDMProject(Base):
    """
    LDM Project - Top-level container for organizing localization files.
    Each user can have multiple projects.
    """
    __tablename__ = "ldm_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User")
    folders = relationship("LDMFolder", back_populates="project", cascade="all, delete-orphan")
    files = relationship("LDMFile", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ldm_project_owner", "owner_id"),
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
    )

    def __repr__(self):
        return f"<LDMFolder(id={self.id}, name='{self.name}', project_id={self.project_id})>"


class LDMFile(Base):
    """
    LDM File - Uploaded localization file stored in database.
    Original file parsed into LDMRow entries for editing.
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

    # Relationships
    project = relationship("LDMProject", back_populates="files")
    folder = relationship("LDMFolder", back_populates="files")
    rows = relationship("LDMRow", back_populates="file", cascade="all, delete-orphan")
    creator = relationship("User")

    __table_args__ = (
        Index("idx_ldm_file_project_folder", "project_id", "folder_id"),
    )

    def __repr__(self):
        return f"<LDMFile(id={self.id}, name='{self.name}', rows={self.row_count})>"


class LDMRow(Base):
    """
    LDM Row - Single localization string (source + target).
    Source (StrOrigin) is READ-ONLY, Target (Str) is EDITABLE.
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

    # Relationships
    file = relationship("LDMFile", back_populates="rows")
    editor = relationship("User")

    __table_args__ = (
        Index("idx_ldm_row_file_rownum", "file_id", "row_num"),
        Index("idx_ldm_row_file_stringid", "file_id", "string_id"),
        Index("idx_ldm_row_status", "status"),
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
