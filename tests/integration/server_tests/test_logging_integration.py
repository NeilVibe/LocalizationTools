"""
Logging Integration Tests

Tests for the complete logging flow including:
- Log entry creation
- Statistics aggregation
- Performance metrics
- Error tracking
"""

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.database.models import (
    Base,
    User,
    LogEntry,
    ToolUsageStats,
    FunctionUsageStats,
    PerformanceMetrics,
    ErrorLog,
    ActiveOperation,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def test_db():
    """Create a test database using PostgreSQL."""
    import os

    # Use PostgreSQL from environment (CI) or default local config
    pg_user = os.getenv("POSTGRES_USER", "locanext")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "locanext_password")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "6433")
    pg_db = os.getenv("POSTGRES_DB", "locanext")

    db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    engine = create_engine(db_url, echo=False)

    # Don't create/drop all - use existing tables
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def test_user(test_db):
    """Get or create a test user, cleaning up old test data."""
    # Check if user exists first (PostgreSQL persists data)
    existing = test_db.query(User).filter_by(username="logtest_user").first()
    if existing:
        # Clean up old test data for this user
        test_db.query(LogEntry).filter_by(user_id=existing.user_id).delete()
        test_db.query(ErrorLog).filter(ErrorLog.tool_name.in_(['XLSTransfer', 'Test', 'QuickSearch', 'KRSimilar'])).delete(synchronize_session='fetch')
        test_db.query(ActiveOperation).filter_by(user_id=existing.user_id).delete()
        test_db.query(PerformanceMetrics).delete()
        test_db.query(FunctionUsageStats).delete()
        test_db.query(ToolUsageStats).delete()
        test_db.commit()
        return existing

    user = User(
        username="logtest_user",
        password_hash="hash",
        department="QA",
    )
    test_db.add(user)
    test_db.commit()
    return user


class TestLogEntryCreation:
    """Tests for creating log entries."""

    def test_log_successful_operation(self, test_db, test_user):
        """Test logging a successful operation."""
        log = LogEntry(
            user_id=test_user.user_id,
            username=test_user.username,
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=5.5,
            status="success",
            file_info={"filename": "test.xlsx", "rows": 1000},
        )
        test_db.add(log)
        test_db.commit()

        assert log.log_id is not None
        assert log.status == "success"

    def test_log_failed_operation(self, test_db, test_user):
        """Test logging a failed operation."""
        log = LogEntry(
            user_id=test_user.user_id,
            username=test_user.username,
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=0.1,
            status="error",
            error_message="File format not supported",
        )
        test_db.add(log)
        test_db.commit()

        assert log.status == "error"
        assert "not supported" in log.error_message

    def test_log_with_parameters(self, test_db, test_user):
        """Test logging with operation parameters."""
        params = {
            "source_column": "A",
            "target_column": "B",
            "sheet_name": "Sheet1",
        }

        log = LogEntry(
            user_id=test_user.user_id,
            username=test_user.username,
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="copy_column",
            duration_seconds=2.0,
            parameters=params,
        )
        test_db.add(log)
        test_db.commit()

        assert log.parameters["source_column"] == "A"

    def test_query_logs_by_tool(self, test_db, test_user):
        """Test querying logs by tool name."""
        # Create logs for different tools
        tools = ["XLSTransfer", "QuickSearch", "KRSimilar"]
        for tool in tools:
            for i in range(3):
                log = LogEntry(
                    user_id=test_user.user_id,
                    username=test_user.username,
                    machine_id="machine",
                    tool_name=tool,
                    function_name="test",
                    duration_seconds=1.0,
                )
                test_db.add(log)

        test_db.commit()

        # Query for specific tool (filter by function_name to avoid pollution from other tests)
        xls_logs = test_db.query(LogEntry).filter_by(tool_name="XLSTransfer", function_name="test").all()
        assert len(xls_logs) == 3

    def test_query_logs_by_date_range(self, test_db, test_user):
        """Test querying logs by date range."""
        now = datetime.utcnow()

        # Create logs with different timestamps
        for i in range(5):
            log = LogEntry(
                user_id=test_user.user_id,
                username=test_user.username,
                machine_id="machine",
                tool_name="Test",
                function_name="test",
                duration_seconds=1.0,
                timestamp=now - timedelta(days=i),
            )
            test_db.add(log)

        test_db.commit()

        # Query last 3 days (for this user only)
        three_days_ago = now - timedelta(days=3)
        recent_logs = test_db.query(LogEntry).filter(
            LogEntry.timestamp >= three_days_ago,
            LogEntry.user_id == test_user.user_id
        ).all()

        assert len(recent_logs) == 4  # today + 3 days back


class TestStatisticsAggregation:
    """Tests for statistics aggregation."""

    def test_create_daily_tool_stats(self, test_db):
        """Test creating daily tool usage stats."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        stats = ToolUsageStats(
            date=today,
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

    def test_aggregate_function_stats(self, test_db):
        """Test function-level statistics."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        functions = ["transfer_data", "copy_column", "merge_files"]
        for func in functions:
            stats = FunctionUsageStats(
                date=today,
                tool_name="XLSTransfer",
                function_name=func,
                total_uses=10,
                unique_users=5,
                avg_duration_seconds=2.0,
            )
            test_db.add(stats)

        test_db.commit()

        # Query all function stats for today
        func_stats = test_db.query(FunctionUsageStats).filter_by(
            date=today,
            tool_name="XLSTransfer"
        ).all()

        assert len(func_stats) == 3

    def test_calculate_success_rate(self, test_db):
        """Test calculating success rate from stats."""
        stats = ToolUsageStats(
            date=datetime.utcnow(),
            tool_name="XLSTransfer",
            total_uses=100,
            success_count=95,
            error_count=5,
        )
        test_db.add(stats)
        test_db.commit()

        # Calculate success rate
        success_rate = stats.success_count / stats.total_uses * 100
        assert success_rate == 95.0


class TestPerformanceTracking:
    """Tests for performance metrics tracking."""

    def test_record_performance_metric(self, test_db):
        """Test recording a performance metric."""
        metric = PerformanceMetrics(
            tool_name="XLSTransfer",
            function_name="transfer_data",
            duration_seconds=5.5,
            cpu_usage_percent=45.0,
            memory_mb=512.0,
            file_size_mb=10.0,
            rows_processed=5000,
        )
        test_db.add(metric)
        test_db.commit()

        assert metric.metric_id is not None

    def test_query_slow_operations(self, test_db):
        """Test finding slow operations."""
        # Create metrics with varying durations
        for i in range(10):
            metric = PerformanceMetrics(
                tool_name="XLSTransfer",
                function_name="transfer",
                duration_seconds=float(i * 2),  # 0, 2, 4, 6, 8, 10, 12, 14, 16, 18
            )
            test_db.add(metric)

        test_db.commit()

        # Find operations slower than 10 seconds
        slow_ops = test_db.query(PerformanceMetrics).filter(
            PerformanceMetrics.duration_seconds > 10
        ).all()

        assert len(slow_ops) == 4  # 12, 14, 16, 18

    def test_average_performance(self, test_db, test_user):
        """Test calculating average performance."""
        from sqlalchemy import func

        # Add performance data
        for i in range(5):
            metric = PerformanceMetrics(
                tool_name="XLSTransfer",
                function_name="transfer",
                duration_seconds=float(i + 1),  # 1, 2, 3, 4, 5
            )
            test_db.add(metric)

        test_db.commit()

        # Calculate average
        avg = test_db.query(func.avg(PerformanceMetrics.duration_seconds)).scalar()
        assert avg == 3.0


class TestErrorTracking:
    """Tests for error logging and tracking."""

    def test_log_error_with_stack_trace(self, test_db, test_user):
        """Test logging an error with stack trace."""
        error = ErrorLog(
            user_id=test_user.user_id,
            machine_id="machine_001",
            tool_name="XLSTransfer",
            function_name="transfer_data",
            error_type="ValueError",
            error_message="Invalid column reference",
            stack_trace="Traceback (most recent call last):\n  File...",
            app_version="1.0.0",
            context={"column": "ZZ", "row": 100},
        )
        test_db.add(error)
        test_db.commit()

        assert error.error_id is not None
        assert error.error_type == "ValueError"

    def test_query_errors_by_type(self, test_db, test_user):
        """Test querying errors by type."""
        error_types = ["ValueError", "FileNotFoundError", "ValueError", "TypeError"]

        for err_type in error_types:
            error = ErrorLog(
                machine_id="machine",
                tool_name="Test",
                function_name="test",
                error_type=err_type,
                error_message="Test error",
                app_version="1.0.0",
            )
            test_db.add(error)

        test_db.commit()

        value_errors = test_db.query(ErrorLog).filter_by(error_type="ValueError").all()
        assert len(value_errors) == 2

    def test_error_count_by_tool(self, test_db):
        """Test counting errors by tool."""
        from sqlalchemy import func

        tools = ["XLSTransfer", "XLSTransfer", "QuickSearch"]
        for tool in tools:
            error = ErrorLog(
                machine_id="machine",
                tool_name=tool,
                function_name="test",
                error_type="Error",
                error_message="Test",
                app_version="1.0.0",
            )
            test_db.add(error)

        test_db.commit()

        # Count by tool
        counts = test_db.query(
            ErrorLog.tool_name,
            func.count(ErrorLog.error_id)
        ).group_by(ErrorLog.tool_name).all()

        counts_dict = dict(counts)
        assert counts_dict["XLSTransfer"] == 2
        assert counts_dict["QuickSearch"] == 1


class TestActiveOperations:
    """Tests for active operation tracking."""

    def test_track_running_operation(self, test_db, test_user):
        """Test tracking a running operation."""
        op = ActiveOperation(
            user_id=test_user.user_id,
            username=test_user.username,
            tool_name="XLSTransfer",
            function_name="transfer_data",
            operation_name="Processing large_file.xlsx",
            total_steps=1000,
        )
        test_db.add(op)
        test_db.commit()

        assert op.status == "running"
        assert op.progress_percentage == 0.0

    def test_update_operation_progress(self, test_db, test_user):
        """Test updating operation progress."""
        op = ActiveOperation(
            user_id=test_user.user_id,
            username=test_user.username,
            tool_name="XLSTransfer",
            function_name="transfer",
            operation_name="Processing",
            total_steps=100,
        )
        test_db.add(op)
        test_db.commit()

        # Simulate progress updates
        for i in range(1, 11):
            op.completed_steps = i * 10
            op.progress_percentage = float(i * 10)
            op.current_step = f"Processing row {i * 10}/100"
            test_db.commit()

        assert op.progress_percentage == 100.0
        assert op.completed_steps == 100

    def test_complete_operation(self, test_db, test_user):
        """Test completing an operation."""
        op = ActiveOperation(
            user_id=test_user.user_id,
            username=test_user.username,
            tool_name="XLSTransfer",
            function_name="transfer",
            operation_name="Processing",
        )
        test_db.add(op)
        test_db.commit()

        # Complete operation
        op.status = "completed"
        op.progress_percentage = 100.0
        op.completed_at = datetime.utcnow()
        op.output_files = ["output.xlsx"]
        test_db.commit()

        assert op.status == "completed"
        assert op.output_files == ["output.xlsx"]

    def test_fail_operation(self, test_db, test_user):
        """Test failing an operation."""
        op = ActiveOperation(
            user_id=test_user.user_id,
            username=test_user.username,
            tool_name="XLSTransfer",
            function_name="transfer",
            operation_name="Processing",
        )
        test_db.add(op)
        test_db.commit()

        # Fail operation
        op.status = "failed"
        op.error_message = "Out of memory"
        op.completed_at = datetime.utcnow()
        test_db.commit()

        assert op.status == "failed"
        assert "memory" in op.error_message

    def test_find_running_operations(self, test_db, test_user):
        """Test finding all running operations."""
        # Create mix of running and completed
        statuses = ["running", "completed", "running", "failed", "running"]
        for i, status in enumerate(statuses):
            op = ActiveOperation(
                user_id=test_user.user_id,
                username=test_user.username,
                tool_name="Test",
                function_name="test",
                operation_name=f"Op {i}",
                status=status,
            )
            test_db.add(op)

        test_db.commit()

        # Filter by user to avoid counting operations from other tests/background tasks
        running = test_db.query(ActiveOperation).filter_by(
            status="running",
            user_id=test_user.user_id
        ).all()
        assert len(running) == 3
