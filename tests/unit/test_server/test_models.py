"""
Unit Tests for Database Models

Tests for SQLAlchemy ORM models in server/database/models.py
"""

import pytest
from datetime import datetime, timedelta
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.database.models import (
    Base,
    User,
    Session,
    LogEntry,
    ActiveOperation,
    ToolUsageStats,
    FunctionUsageStats,
    PerformanceMetrics,
    UserActivitySummary,
    AppVersion,
    UpdateHistory,
    ErrorLog,
    Announcement,
    UserFeedback,
)


# Create an in-memory SQLite database for testing
@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ============================================================================
# User Model Tests
# ============================================================================

class TestUserModel:
    """Tests for the User model."""

    def test_create_user_basic(self, test_db):
        """Test creating a basic user."""
        user = User(
            username="testuser",
            password_hash="hashed_password_123",
            email="test@example.com",
        )
        test_db.add(user)
        test_db.commit()

        assert user.user_id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"  # default
        assert user.is_active is True  # default

    def test_create_user_with_all_fields(self, test_db):
        """Test creating a user with all fields."""
        user = User(
            username="admin_user",
            password_hash="secure_hash",
            email="admin@example.com",
            full_name="Admin User",
            department="IT",
            role="admin",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        assert user.full_name == "Admin User"
        assert user.department == "IT"
        assert user.role == "admin"

    def test_user_created_at_default(self, test_db):
        """Test that created_at is set automatically."""
        user = User(
            username="timetest",
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_user_unique_username(self, test_db):
        """Test that username must be unique."""
        user1 = User(username="unique", password_hash="hash1")
        test_db.add(user1)
        test_db.commit()

        user2 = User(username="unique", password_hash="hash2")
        test_db.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()
        test_db.rollback()

    def test_user_unique_email(self, test_db):
        """Test that email must be unique when provided."""
        user1 = User(username="user1", password_hash="hash1", email="same@test.com")
        test_db.add(user1)
        test_db.commit()

        user2 = User(username="user2", password_hash="hash2", email="same@test.com")
        test_db.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()
        test_db.rollback()

    def test_user_repr(self, test_db):
        """Test User __repr__ method."""
        user = User(
            username="reprtest",
            password_hash="hash",
            department="QA",
        )
        test_db.add(user)
        test_db.commit()

        repr_str = repr(user)
        assert "reprtest" in repr_str
        assert "QA" in repr_str

    def test_user_nullable_email(self, test_db):
        """Test that email can be null."""
        user = User(
            username="nomail",
            password_hash="hash",
        )
        test_db.add(user)
        test_db.commit()

        assert user.email is None

    def test_user_last_login_update(self, test_db):
        """Test updating last_login field."""
        user = User(username="logintest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        assert user.last_login is None

        user.last_login = datetime.utcnow()
        test_db.commit()

        assert user.last_login is not None


# ============================================================================
# Session Model Tests
# ============================================================================

class TestSessionModel:
    """Tests for the Session model."""

    def test_create_session(self, test_db):
        """Test creating a session."""
        # First create a user
        user = User(username="sessionuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = Session(
            user_id=user.user_id,
            machine_id="machine_abc123",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        assert session.session_id is not None
        assert session.user_id == user.user_id
        assert session.is_active is True

    def test_session_uuid_format(self, test_db):
        """Test that session_id is a valid UUID."""
        user = User(username="uuidtest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = Session(
            user_id=user.user_id,
            machine_id="machine_001",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        # Verify it's a valid UUID format
        uuid.UUID(session.session_id)  # Should not raise

    def test_session_user_relationship(self, test_db):
        """Test session-user relationship."""
        user = User(username="reltest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = Session(
            user_id=user.user_id,
            machine_id="machine",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        # Access relationship
        assert session.user.username == "reltest"
        assert user.sessions[0].session_id == session.session_id

    def test_session_ip_address(self, test_db):
        """Test session IP address field."""
        user = User(username="iptest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = Session(
            user_id=user.user_id,
            machine_id="machine",
            ip_address="192.168.1.100",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()

        assert session.ip_address == "192.168.1.100"

    def test_session_cascade_delete(self, test_db):
        """Test that sessions are deleted when user is deleted."""
        user = User(username="cascadetest", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        session = Session(
            user_id=user.user_id,
            machine_id="machine",
            app_version="1.0.0",
        )
        test_db.add(session)
        test_db.commit()
        session_id = session.session_id

        # Delete user
        test_db.delete(user)
        test_db.commit()

        # Session should also be deleted
        found = test_db.query(Session).filter_by(session_id=session_id).first()
        assert found is None


# ============================================================================
# LogEntry Model Tests
# ============================================================================

class TestLogEntryModel:
    """Tests for the LogEntry model."""

    def test_create_log_entry(self, test_db):
        """Test creating a log entry."""
        user = User(username="loguser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        log = LogEntry(
            user_id=user.user_id,
            username="loguser",
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=5.5,
        )
        test_db.add(log)
        test_db.commit()

        assert log.log_id is not None
        assert log.status == "success"  # default

    def test_log_entry_with_error(self, test_db):
        """Test log entry with error status."""
        user = User(username="erroruser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        log = LogEntry(
            user_id=user.user_id,
            username="erroruser",
            machine_id="machine",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=0.1,
            status="error",
            error_message="File not found",
        )
        test_db.add(log)
        test_db.commit()

        assert log.status == "error"
        assert log.error_message == "File not found"

    def test_log_entry_json_fields(self, test_db):
        """Test JSON fields in log entry."""
        user = User(username="jsonuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        file_info = {"filename": "test.xlsx", "size_mb": 2.5, "rows": 1000}
        parameters = {"source_col": "A", "target_col": "B"}

        log = LogEntry(
            user_id=user.user_id,
            username="jsonuser",
            machine_id="machine",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=5.0,
            file_info=file_info,
            parameters=parameters,
        )
        test_db.add(log)
        test_db.commit()

        assert log.file_info["filename"] == "test.xlsx"
        assert log.parameters["source_col"] == "A"

    def test_log_entry_timestamp(self, test_db):
        """Test log entry timestamp."""
        user = User(username="tsuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        log = LogEntry(
            user_id=user.user_id,
            username="tsuser",
            machine_id="machine",
            tool_name="Test",
            function_name="test",
            duration_seconds=1.0,
        )
        test_db.add(log)
        test_db.commit()

        assert log.timestamp is not None


# ============================================================================
# ActiveOperation Model Tests
# ============================================================================

class TestActiveOperationModel:
    """Tests for the ActiveOperation model."""

    def test_create_active_operation(self, test_db):
        """Test creating an active operation."""
        user = User(username="opuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        operation = ActiveOperation(
            user_id=user.user_id,
            username="opuser",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            operation_name="Processing file.xlsx",
        )
        test_db.add(operation)
        test_db.commit()

        assert operation.operation_id is not None
        assert operation.status == "running"
        assert operation.progress_percentage == 0.0

    def test_operation_progress_update(self, test_db):
        """Test updating operation progress."""
        user = User(username="progressuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        operation = ActiveOperation(
            user_id=user.user_id,
            username="progressuser",
            tool_name="XLSTransfer",
            function_name="transfer",
            operation_name="Processing",
            total_steps=100,
        )
        test_db.add(operation)
        test_db.commit()

        # Update progress
        operation.progress_percentage = 50.0
        operation.completed_steps = 50
        operation.current_step = "Processing row 50/100"
        test_db.commit()

        assert operation.progress_percentage == 50.0
        assert operation.completed_steps == 50

    def test_operation_completion(self, test_db):
        """Test completing an operation."""
        user = User(username="completeuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        operation = ActiveOperation(
            user_id=user.user_id,
            username="completeuser",
            tool_name="Test",
            function_name="test",
            operation_name="Test Op",
        )
        test_db.add(operation)
        test_db.commit()

        # Complete operation
        operation.status = "completed"
        operation.progress_percentage = 100.0
        operation.completed_at = datetime.utcnow()
        operation.output_files = ["output.xlsx"]
        test_db.commit()

        assert operation.status == "completed"
        assert operation.completed_at is not None


# ============================================================================
# ToolUsageStats Model Tests
# ============================================================================

class TestToolUsageStatsModel:
    """Tests for the ToolUsageStats model."""

    def test_create_tool_stats(self, test_db):
        """Test creating tool usage stats."""
        stats = ToolUsageStats(
            date=datetime.utcnow(),
            tool_name="XLSTransfer",
            total_uses=100,
            unique_users=25,
            total_duration_seconds=500.0,
            avg_duration_seconds=5.0,
            success_count=95,
            error_count=5,
        )
        test_db.add(stats)
        test_db.commit()

        assert stats.stat_id is not None
        assert stats.total_uses == 100

    def test_tool_stats_defaults(self, test_db):
        """Test default values for tool stats."""
        stats = ToolUsageStats(
            date=datetime.utcnow(),
            tool_name="NewTool",
        )
        test_db.add(stats)
        test_db.commit()

        assert stats.total_uses == 0
        assert stats.unique_users == 0
        assert stats.success_count == 0


# ============================================================================
# FunctionUsageStats Model Tests
# ============================================================================

class TestFunctionUsageStatsModel:
    """Tests for the FunctionUsageStats model."""

    def test_create_function_stats(self, test_db):
        """Test creating function usage stats."""
        stats = FunctionUsageStats(
            date=datetime.utcnow(),
            tool_name="XLSTransfer",
            function_name="transfer_data",
            total_uses=50,
            unique_users=10,
            avg_duration_seconds=3.5,
            min_duration_seconds=1.0,
            max_duration_seconds=10.0,
        )
        test_db.add(stats)
        test_db.commit()

        assert stats.stat_id is not None
        assert stats.function_name == "transfer_data"


# ============================================================================
# PerformanceMetrics Model Tests
# ============================================================================

class TestPerformanceMetricsModel:
    """Tests for the PerformanceMetrics model."""

    def test_create_performance_metric(self, test_db):
        """Test creating a performance metric."""
        metric = PerformanceMetrics(
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=5.5,
            cpu_usage_percent=45.0,
            memory_mb=512.0,
            file_size_mb=2.5,
            rows_processed=1000,
        )
        test_db.add(metric)
        test_db.commit()

        assert metric.metric_id is not None
        assert metric.cpu_usage_percent == 45.0


# ============================================================================
# AppVersion Model Tests
# ============================================================================

class TestAppVersionModel:
    """Tests for the AppVersion model."""

    def test_create_app_version(self, test_db):
        """Test creating an app version."""
        version = AppVersion(
            version_number="2512010029",
            is_latest=True,
            release_notes="New features and bug fixes",
            download_url="https://example.com/download",
        )
        test_db.add(version)
        test_db.commit()

        assert version.version_id is not None
        assert version.is_latest is True

    def test_version_unique(self, test_db):
        """Test version number uniqueness."""
        v1 = AppVersion(version_number="1.0.0")
        test_db.add(v1)
        test_db.commit()

        v2 = AppVersion(version_number="1.0.0")
        test_db.add(v2)

        with pytest.raises(Exception):
            test_db.commit()
        test_db.rollback()


# ============================================================================
# ErrorLog Model Tests
# ============================================================================

class TestErrorLogModel:
    """Tests for the ErrorLog model."""

    def test_create_error_log(self, test_db):
        """Test creating an error log."""
        error = ErrorLog(
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            error_type="FileNotFoundError",
            error_message="The file does not exist",
            stack_trace="Traceback...",
            app_version="1.0.0",
            context={"file": "test.xlsx"},
        )
        test_db.add(error)
        test_db.commit()

        assert error.error_id is not None
        assert error.error_type == "FileNotFoundError"


# ============================================================================
# Announcement Model Tests
# ============================================================================

class TestAnnouncementModel:
    """Tests for the Announcement model."""

    def test_create_announcement(self, test_db):
        """Test creating an announcement."""
        announcement = Announcement(
            title="Maintenance Notice",
            message="System will be down for maintenance",
            priority="warning",
        )
        test_db.add(announcement)
        test_db.commit()

        assert announcement.announcement_id is not None
        assert announcement.is_active is True

    def test_announcement_with_targets(self, test_db):
        """Test announcement with target users."""
        announcement = Announcement(
            title="Team Update",
            message="For QA team only",
            target_users=[1, 2, 3],
        )
        test_db.add(announcement)
        test_db.commit()

        assert announcement.target_users == [1, 2, 3]


# ============================================================================
# UserFeedback Model Tests
# ============================================================================

class TestUserFeedbackModel:
    """Tests for the UserFeedback model."""

    def test_create_feedback(self, test_db):
        """Test creating user feedback."""
        user = User(username="feedbackuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        feedback = UserFeedback(
            user_id=user.user_id,
            feedback_type="feature",
            tool_name="XLSTransfer",
            subject="Add batch processing",
            description="It would be great to process multiple files at once",
            rating=4,
        )
        test_db.add(feedback)
        test_db.commit()

        assert feedback.feedback_id is not None
        assert feedback.status == "open"

    def test_feedback_user_relationship(self, test_db):
        """Test feedback-user relationship."""
        user = User(username="reluser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        feedback = UserFeedback(
            user_id=user.user_id,
            feedback_type="bug",
            subject="Bug report",
            description="Something is broken",
        )
        test_db.add(feedback)
        test_db.commit()

        assert feedback.user.username == "reluser"
        assert user.feedback[0].subject == "Bug report"


# ============================================================================
# UserActivitySummary Model Tests
# ============================================================================

class TestUserActivitySummaryModel:
    """Tests for the UserActivitySummary model."""

    def test_create_activity_summary(self, test_db):
        """Test creating an activity summary."""
        user = User(username="activityuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        summary = UserActivitySummary(
            date=datetime.utcnow(),
            user_id=user.user_id,
            username="activityuser",
            total_operations=25,
            total_duration_seconds=300.0,
            tools_used=["XLSTransfer", "QuickSearch"],
        )
        test_db.add(summary)
        test_db.commit()

        assert summary.summary_id is not None
        assert "XLSTransfer" in summary.tools_used


# ============================================================================
# UpdateHistory Model Tests
# ============================================================================

class TestUpdateHistoryModel:
    """Tests for the UpdateHistory model."""

    def test_create_update_history(self, test_db):
        """Test creating update history."""
        user = User(username="updateuser", password_hash="hash")
        test_db.add(user)
        test_db.commit()

        history = UpdateHistory(
            user_id=user.user_id,
            from_version="1.0.0",
            to_version="2.0.0",
            machine_id="machine_001",
        )
        test_db.add(history)
        test_db.commit()

        assert history.update_id is not None
        assert history.from_version == "1.0.0"
        assert history.to_version == "2.0.0"
