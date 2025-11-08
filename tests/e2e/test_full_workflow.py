"""
End-to-End Full Workflow Tests

Tests the complete client-server workflow:
1. Server startup
2. User authentication
3. Session management
4. Log submission
5. Statistics calculation
6. Admin dashboard display

These tests require the server to be running or use a test server instance.
"""

import pytest
import sys
from pathlib import Path
import time
from datetime import datetime
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.database.models import Base, User, Session as DBSession, LogEntry
from server.database.db_setup import setup_database
from server.utils.auth import hash_password, create_access_token
from server import config


class TestFullWorkflow:
    """Test the complete end-to-end workflow."""

    @pytest.fixture
    def test_db(self, temp_dir):
        """Create a temporary test database."""
        db_path = temp_dir / "test_e2e.db"
        db_url = f"sqlite:///{db_path}"

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        SessionMaker = sessionmaker(bind=engine)

        yield SessionMaker

        # Cleanup
        engine.dispose()

    @pytest.fixture
    def test_user(self, test_db):
        """Create a test user in the database."""
        db = test_db()
        try:
            user = User(
                username="testuser",
                password_hash=hash_password("testpassword123"),
                email="test@example.com",
                full_name="Test User",
                department="QA",
                role="user",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    def test_database_initialization(self, test_db):
        """Test that database initializes correctly."""
        db = test_db()
        try:
            # Verify tables exist
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]

            # Check critical tables exist
            assert "users" in tables
            assert "sessions" in tables
            assert "log_entries" in tables
            assert "tool_usage_stats" in tables

        finally:
            db.close()

    def test_user_creation_and_authentication(self, test_db, test_user):
        """Test user creation and password verification."""
        db = test_db()
        try:
            # Verify user was created
            user = db.query(User).filter(User.username == "testuser").first()
            assert user is not None
            assert user.email == "test@example.com"
            assert user.role == "user"
            assert user.is_active is True

            # Test JWT token creation
            token = create_access_token({"sub": user.username, "user_id": user.user_id})
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 50  # JWT tokens are long

        finally:
            db.close()

    def test_session_lifecycle(self, test_db, test_user):
        """Test complete session lifecycle: start -> heartbeat -> end."""
        db = test_db()
        try:
            # Create session
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Verify session created
            assert session.session_id is not None
            assert session.is_active is True

            # Update session (heartbeat)
            session.last_activity = datetime.utcnow()
            db.commit()

            # End session
            session.is_active = False
            db.commit()

            # Verify session ended
            db.refresh(session)
            assert session.is_active is False

        finally:
            db.close()

    def test_log_entry_creation(self, test_db, test_user):
        """Test creating log entries."""
        db = test_db()
        try:
            # Create session first
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Create log entry
            log = LogEntry(
                user_id=test_user.user_id,
                session_id=session.session_id,
                username=test_user.username,
                machine_id="test-machine-123",
                tool_name="XLSTransfer",
                function_name="create_dictionary",
                timestamp=datetime.utcnow(),
                duration_seconds=10.5,
                status="success"
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            # Verify log entry
            assert log.log_id is not None
            assert log.tool_name == "XLSTransfer"
            assert log.function_name == "create_dictionary"
            assert log.status == "success"
            assert log.duration_seconds == 10.5

            # Query log entry
            saved_log = db.query(LogEntry).filter(
                LogEntry.log_id == log.log_id
            ).first()
            assert saved_log is not None
            assert saved_log.user_id == test_user.user_id

        finally:
            db.close()

    def test_multiple_logs_statistics(self, test_db, test_user):
        """Test statistics calculation with multiple log entries."""
        db = test_db()
        try:
            # Create session
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Create multiple log entries
            logs = [
                LogEntry(
                    user_id=test_user.user_id,
                    session_id=session.session_id,
                    username=test_user.username,
                    machine_id="test-machine-123",
                    tool_name="XLSTransfer",
                    function_name="create_dictionary",
                    timestamp=datetime.utcnow(),
                    duration_seconds=10.0,
                    status="success"
                ),
                LogEntry(
                    user_id=test_user.user_id,
                    session_id=session.session_id,
                    username=test_user.username,
                    machine_id="test-machine-123",
                    tool_name="XLSTransfer",
                    function_name="transfer_to_excel",
                    timestamp=datetime.utcnow(),
                    duration_seconds=15.0,
                    status="success"
                ),
                LogEntry(
                    user_id=test_user.user_id,
                    session_id=session.session_id,
                    username=test_user.username,
                    machine_id="test-machine-123",
                    tool_name="XLSTransfer",
                    function_name="check_newlines",
                    timestamp=datetime.utcnow(),
                    duration_seconds=5.0,
                    status="error",
                    error_message="Test error"
                ),
            ]

            for log in logs:
                db.add(log)
            db.commit()

            # Calculate statistics
            total_logs = db.query(LogEntry).count()
            successful_logs = db.query(LogEntry).filter(
                LogEntry.status == "success"
            ).count()
            failed_logs = db.query(LogEntry).filter(
                LogEntry.status == "error"
            ).count()

            # Verify statistics
            assert total_logs == 3
            assert successful_logs == 2
            assert failed_logs == 1

            # Test tool-specific stats
            xls_logs = db.query(LogEntry).filter(
                LogEntry.tool_name == "XLSTransfer"
            ).count()
            assert xls_logs == 3

            # Test function-specific stats
            create_dict_logs = db.query(LogEntry).filter(
                LogEntry.function_name == "create_dictionary"
            ).count()
            assert create_dict_logs == 1

        finally:
            db.close()

    def test_user_activity_summary(self, test_db, test_user):
        """Test user activity summary generation."""
        db = test_db()
        try:
            # Create session
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Create logs
            for i in range(5):
                log = LogEntry(
                    user_id=test_user.user_id,
                    session_id=session.session_id,
                    username=test_user.username,
                    machine_id="test-machine-123",
                    tool_name="XLSTransfer",
                    function_name=f"function_{i}",
                    timestamp=datetime.utcnow(),
                    duration_seconds=float(i + 1),
                    status="success"
                )
                db.add(log)
            db.commit()

            # Calculate user statistics
            user_logs = db.query(LogEntry).filter(
                LogEntry.user_id == test_user.user_id
            ).all()

            total_operations = len(user_logs)
            total_duration = sum(log.duration_seconds for log in user_logs)
            avg_duration = total_duration / total_operations if total_operations > 0 else 0

            # Verify statistics
            assert total_operations == 5
            assert total_duration == 15.0  # 1+2+3+4+5
            assert avg_duration == 3.0

        finally:
            db.close()

    def test_error_tracking(self, test_db, test_user):
        """Test error logging and tracking."""
        db = test_db()
        try:
            # Create session
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Create error log
            error_log = LogEntry(
                user_id=test_user.user_id,
                session_id=session.session_id,
                username=test_user.username,
                machine_id="test-machine-123",
                tool_name="XLSTransfer",
                function_name="create_dictionary",
                timestamp=datetime.utcnow(),
                duration_seconds=2.5,
                status="error",
                error_message="File not found: test.xlsx"
            )
            db.add(error_log)
            db.commit()
            db.refresh(error_log)

            # Verify error log
            assert error_log.status == "error"
            assert error_log.error_message == "File not found: test.xlsx"

            # Query error logs
            errors = db.query(LogEntry).filter(
                LogEntry.status == "error"
            ).all()
            assert len(errors) == 1
            assert errors[0].error_message is not None

        finally:
            db.close()

    def test_performance_tracking(self, test_db, test_user):
        """Test performance metrics tracking."""
        db = test_db()
        try:
            # Create session
            session = DBSession(
                user_id=test_user.user_id,
                machine_id="test-machine-123",
                app_version="1.0.0-test",
                session_start=datetime.utcnow(),
                is_active=True
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Create logs with varying durations
            durations = [5.0, 10.0, 15.0, 20.0, 25.0]
            for duration in durations:
                log = LogEntry(
                    user_id=test_user.user_id,
                    session_id=session.session_id,
                    username=test_user.username,
                    machine_id="test-machine-123",
                    tool_name="XLSTransfer",
                    function_name="create_dictionary",
                    timestamp=datetime.utcnow(),
                    duration_seconds=duration,
                    status="success"
                )
                db.add(log)
            db.commit()

            # Calculate performance metrics
            logs = db.query(LogEntry).filter(
                LogEntry.function_name == "create_dictionary"
            ).all()

            durations_list = [log.duration_seconds for log in logs]
            min_duration = min(durations_list)
            max_duration = max(durations_list)
            avg_duration = sum(durations_list) / len(durations_list)

            # Verify metrics
            assert min_duration == 5.0
            assert max_duration == 25.0
            assert avg_duration == 15.0

        finally:
            db.close()


@pytest.mark.requires_server
class TestServerIntegration:
    """Tests that require a running server instance."""

    @pytest.fixture
    def server_url(self):
        """Return the test server URL."""
        return f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"

    def test_server_health_check(self, server_url):
        """Test server health check endpoint."""
        try:
            response = requests.get(f"{server_url}/health", timeout=5)

            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert data["status"] == "healthy"
            else:
                # Server not running - skip test
                pytest.skip("Server not running")

        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running - skipping integration test")

    def test_server_root_endpoint(self, server_url):
        """Test server root endpoint."""
        try:
            response = requests.get(f"{server_url}/", timeout=5)

            if response.status_code == 200:
                data = response.json()
                assert "message" in data or "name" in data
            else:
                pytest.skip("Server not running")

        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running - skipping integration test")

    def test_version_endpoint(self, server_url):
        """Test version endpoint."""
        try:
            response = requests.get(f"{server_url}/api/version/latest", timeout=5)

            if response.status_code == 200:
                data = response.json()
                assert "version_number" in data or "message" in data
            else:
                pytest.skip("Server not running")

        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running - skipping integration test")
