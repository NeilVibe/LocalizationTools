"""
Unit Tests for UsageLogger

Tests all functionality of the usage logging system including:
- Session management
- Log operation tracking
- Offline queue handling
- Server communication
- Privacy settings

CLEAN, organized, comprehensive testing.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from client.utils.logger import UsageLogger, get_logger, log_function_call


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def mock_config(monkeypatch):
    """Mock client configuration for testing."""
    monkeypatch.setattr("client.config.OFFLINE_MODE", False)
    monkeypatch.setattr("client.config.MOCK_SERVER", False)
    monkeypatch.setattr("client.config.ENABLE_SERVER_LOGGING", True)
    monkeypatch.setattr("client.config.LOG_FILE_NAMES", False)
    monkeypatch.setattr("client.config.LOG_QUEUE_MAX_SIZE", 100)
    monkeypatch.setattr("client.config.API_SESSION_START", "http://localhost:8000/api/session/start")
    monkeypatch.setattr("client.config.API_SESSION_END", "http://localhost:8000/api/session/end")
    monkeypatch.setattr("client.config.API_LOGS", "http://localhost:8000/api/logs")
    monkeypatch.setattr("client.config.API_KEY", "test-api-key")
    monkeypatch.setattr("client.config.API_TIMEOUT", 5)
    monkeypatch.setattr("client.config.MACHINE_ID", "test-machine-123")
    monkeypatch.setattr("client.config.APP_VERSION", "1.0.0")
    monkeypatch.setattr("client.config.OS_INFO", "Linux")


@pytest.fixture
def offline_config(monkeypatch):
    """Mock offline configuration."""
    monkeypatch.setattr("client.config.OFFLINE_MODE", True)
    monkeypatch.setattr("client.config.MOCK_SERVER", False)
    monkeypatch.setattr("client.config.ENABLE_SERVER_LOGGING", True)
    monkeypatch.setattr("client.config.LOG_FILE_NAMES", True)
    monkeypatch.setattr("client.config.LOG_QUEUE_MAX_SIZE", 10)


@pytest.fixture
def mock_requests_success():
    """Mock successful requests."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"session_id": "test-session-123", "status": "success"}
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_requests_failure():
    """Mock failed requests."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_requests_timeout():
    """Mock request timeout."""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
        yield mock_post


# ============================================
# Session Management Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_logger_initialization_creates_session_id(mock_config, mock_requests_success):
    """
    Test that logger initialization creates a session ID.

    Given: A new UsageLogger instance
    When: __init__ is called
    Then: Session ID is generated and not None
    """
    logger = UsageLogger()

    assert logger.session_id is not None
    assert isinstance(logger.session_id, str)
    assert len(logger.session_id) > 0


@pytest.mark.unit
@pytest.mark.client
def test_logger_starts_session_with_server(mock_config, mock_requests_success):
    """
    Test that logger attempts to start session with server.

    Given: A new UsageLogger instance with server available
    When: __init__ is called
    Then: POST request is made to session start endpoint
    """
    logger = UsageLogger()

    # Verify session start was called
    mock_requests_success.assert_called()
    call_args = mock_requests_success.call_args
    assert "api/session/start" in call_args[0][0]


@pytest.mark.unit
@pytest.mark.client
def test_logger_offline_mode_skips_server_session(offline_config):
    """
    Test that offline mode skips server session creation.

    Given: OFFLINE_MODE is enabled
    When: UsageLogger is initialized
    Then: No server calls are made
    """
    with patch('requests.post') as mock_post:
        logger = UsageLogger()

        # No server calls should be made
        mock_post.assert_not_called()
        assert logger.server_available is False


@pytest.mark.unit
@pytest.mark.client
def test_logger_handles_server_unavailable_gracefully(mock_config, mock_requests_timeout):
    """
    Test that logger handles server unavailability gracefully.

    Given: Server is unavailable (timeout)
    When: UsageLogger is initialized
    Then: Logger continues to work without crashing
    """
    logger = UsageLogger()

    # Should not crash, just mark server as unavailable
    assert logger.server_available is False
    assert logger.session_id is not None


# ============================================
# Log Operation Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_log_operation_sends_correct_data_format(mock_config, mock_requests_success):
    """
    Test that log_operation sends correct data format to server.

    Given: A UsageLogger instance
    When: log_operation is called with all parameters
    Then: Correct JSON data is sent to server
    """
    logger = UsageLogger()

    logger.log_operation(
        user_id=1,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="create_dictionary",
        duration_seconds=45.234,
        status="success",
        file_size_mb=2.5,
        rows_processed=1000,
        sheets_processed=2,
        cpu_percent=65.5,
        memory_mb=512.3
    )

    # Get the last call to requests.post (the log call, not session start)
    calls = mock_requests_success.call_args_list
    log_call = calls[-1]  # Last call

    sent_data = log_call.kwargs['json']

    assert sent_data['user_id'] == 1
    assert sent_data['username'] == "test_user"
    assert sent_data['tool_name'] == "XLSTransfer"
    assert sent_data['function_name'] == "create_dictionary"
    assert sent_data['duration_seconds'] == 45.23  # Rounded
    assert sent_data['status'] == "success"
    assert sent_data['file_size_mb'] == 2.5
    assert sent_data['rows_processed'] == 1000
    assert sent_data['sheets_processed'] == 2
    assert sent_data['cpu_percent'] == 65.5
    assert sent_data['memory_mb'] == 512.3


@pytest.mark.unit
@pytest.mark.client
def test_log_operation_respects_privacy_settings(mock_config, mock_requests_success):
    """
    Test that log_operation respects privacy settings for file names.

    Given: LOG_FILE_NAMES is False
    When: log_operation is called with file_name
    Then: file_name is not sent to server
    """
    logger = UsageLogger()

    logger.log_operation(
        user_id=1,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="translate",
        duration_seconds=10.0,
        file_name="secret_document.xlsx"
    )

    calls = mock_requests_success.call_args_list
    log_call = calls[-1]
    sent_data = log_call.kwargs['json']

    # File name should be None due to privacy settings
    assert sent_data['file_name'] is None


@pytest.mark.unit
@pytest.mark.client
def test_log_operation_includes_file_name_when_allowed(monkeypatch, mock_requests_success):
    """
    Test that file names are logged when privacy setting allows.

    Given: LOG_FILE_NAMES is True
    When: log_operation is called with file_name
    Then: file_name is sent to server
    """
    monkeypatch.setattr("client.config.OFFLINE_MODE", False)
    monkeypatch.setattr("client.config.LOG_FILE_NAMES", True)
    monkeypatch.setattr("client.config.ENABLE_SERVER_LOGGING", True)
    monkeypatch.setattr("client.config.MOCK_SERVER", False)

    logger = UsageLogger()

    logger.log_operation(
        user_id=1,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="translate",
        duration_seconds=10.0,
        file_name="document.xlsx"
    )

    calls = mock_requests_success.call_args_list
    log_call = calls[-1]
    sent_data = log_call.kwargs['json']

    # File name should be included
    assert sent_data['file_name'] == "document.xlsx"


@pytest.mark.unit
@pytest.mark.client
def test_log_operation_rounds_numeric_values(mock_config, mock_requests_success):
    """
    Test that numeric values are properly rounded.

    Given: A UsageLogger instance
    When: log_operation is called with precise decimal values
    Then: Values are rounded to 2 decimal places
    """
    logger = UsageLogger()

    logger.log_operation(
        user_id=1,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="test",
        duration_seconds=45.23456789,
        file_size_mb=2.567891,
        cpu_percent=65.555,
        memory_mb=512.999
    )

    calls = mock_requests_success.call_args_list
    log_call = calls[-1]
    sent_data = log_call.kwargs['json']

    assert sent_data['duration_seconds'] == 45.23
    assert sent_data['file_size_mb'] == 2.57
    assert sent_data['cpu_percent'] == 65.56
    assert sent_data['memory_mb'] == 513.0


# ============================================
# Queue Handling Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_logger_queues_logs_when_server_unavailable(mock_config, mock_requests_timeout):
    """
    Test that logs are queued when server is unavailable.

    Given: Server is unavailable
    When: log_operation is called
    Then: Log is added to queue
    """
    logger = UsageLogger()

    logger.log_operation(
        user_id=1,
        username="test_user",
        tool_name="XLSTransfer",
        function_name="test",
        duration_seconds=10.0
    )

    assert len(logger.log_queue) == 1
    assert logger.log_queue[0]['username'] == "test_user"


@pytest.mark.unit
@pytest.mark.client
def test_logger_queue_max_size_limit(offline_config):
    """
    Test that queue respects max size limit.

    Given: Queue max size is 10
    When: 15 logs are added
    Then: Queue contains only 10 most recent logs
    """
    logger = UsageLogger()

    # Add 15 logs
    for i in range(15):
        logger.log_operation(
            user_id=1,
            username=f"user_{i}",
            tool_name="XLSTransfer",
            function_name="test",
            duration_seconds=1.0
        )

    # Queue should be limited to 10
    assert len(logger.log_queue) == 10
    # Should contain most recent logs (user_5 to user_14)
    assert logger.log_queue[0]['username'] == "user_5"
    assert logger.log_queue[-1]['username'] == "user_14"


@pytest.mark.unit
@pytest.mark.client
def test_logger_flushes_queue_when_server_available(mock_config):
    """
    Test that queued logs are flushed when server becomes available.

    Given: Logs in queue and server becomes available
    When: A new log is sent successfully
    Then: Queue is flushed to server
    """
    with patch('requests.post') as mock_post:
        # First call fails, subsequent calls succeed
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"status": "success"}

        mock_post.side_effect = [
            mock_response_success,  # Session start succeeds
            mock_response_fail,     # First log fails (gets queued)
            mock_response_success,  # Second log succeeds
            mock_response_success,  # Queued log 1 gets flushed
        ]

        logger = UsageLogger()

        # First log fails and gets queued
        logger.log_operation(
            user_id=1,
            username="user_1",
            tool_name="XLSTransfer",
            function_name="test",
            duration_seconds=1.0
        )

        assert len(logger.log_queue) == 1

        # Second log succeeds and triggers queue flush
        logger.log_operation(
            user_id=1,
            username="user_2",
            tool_name="XLSTransfer",
            function_name="test",
            duration_seconds=1.0
        )

        # Queue should be empty after flush
        assert len(logger.log_queue) == 0


# ============================================
# Decorator Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_log_function_call_decorator_tracks_duration(mock_config, mock_requests_success):
    """
    Test that decorator tracks function execution duration.

    Given: A function decorated with @log_function_call
    When: Function is called
    Then: Duration is logged to server
    """
    @log_function_call(username="test_user", tool_name="TestTool", function_name="test_func")
    def slow_function():
        time.sleep(0.1)
        return "done"

    result = slow_function()

    assert result == "done"

    # Get the log call
    calls = mock_requests_success.call_args_list
    log_call = calls[-1]
    sent_data = log_call.kwargs['json']

    assert sent_data['function_name'] == "test_func"
    assert sent_data['duration_seconds'] >= 0.1
    assert sent_data['status'] == "success"


@pytest.mark.unit
@pytest.mark.client
def test_log_function_call_decorator_captures_errors(mock_config, mock_requests_success):
    """
    Test that decorator captures and logs errors.

    Given: A function that raises an exception
    When: Function is called
    Then: Error is logged with correct status
    """
    @log_function_call(username="test_user", tool_name="TestTool", function_name="failing_func")
    def failing_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        failing_function()

    # Get the log call
    calls = mock_requests_success.call_args_list
    log_call = calls[-1]
    sent_data = log_call.kwargs['json']

    assert sent_data['status'] == "error"
    assert sent_data['error_message'] == "Test error"
    assert sent_data['error_type'] == "ValueError"


# ============================================
# Global Logger Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_get_logger_returns_singleton(mock_config, mock_requests_success):
    """
    Test that get_logger returns the same instance.

    Given: Multiple calls to get_logger()
    When: Instances are compared
    Then: Same instance is returned (singleton pattern)
    """
    # Reset global logger
    import client.utils.logger as logger_module
    logger_module._usage_logger = None

    logger1 = get_logger()
    logger2 = get_logger()

    assert logger1 is logger2


# ============================================
# Session End Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_end_session_sends_request(mock_config, mock_requests_success):
    """
    Test that end_session sends request to server.

    Given: A UsageLogger instance
    When: end_session is called
    Then: POST request is made to session end endpoint
    """
    logger = UsageLogger()
    session_id = logger.session_id

    logger.end_session()

    # Find the session end call
    calls = mock_requests_success.call_args_list
    session_end_call = [c for c in calls if "session/end" in c[0][0]]

    assert len(session_end_call) > 0
    sent_data = session_end_call[0].kwargs['json']
    assert sent_data['session_id'] == session_id


@pytest.mark.unit
@pytest.mark.client
def test_end_session_offline_mode_no_request(offline_config):
    """
    Test that end_session doesn't send request in offline mode.

    Given: OFFLINE_MODE is enabled
    When: end_session is called
    Then: No server request is made
    """
    with patch('requests.post') as mock_post:
        logger = UsageLogger()
        logger.end_session()

        # Only session start might be called, not session end
        # Actually in offline mode, neither should be called
        assert mock_post.call_count == 0


# ============================================
# Error Handling Tests
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_logger_handles_network_errors_gracefully(mock_config):
    """
    Test that logger handles various network errors gracefully.

    Given: Various network errors occur
    When: log_operation is called
    Then: No exceptions are raised, logs are queued
    """
    with patch('requests.post') as mock_post:
        # Simulate different network errors
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("No connection"),
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.RequestException("Generic error")
        ]

        logger = UsageLogger()

        # Should not raise exceptions
        logger.log_operation(
            user_id=1,
            username="test_user",
            tool_name="XLSTransfer",
            function_name="test",
            duration_seconds=1.0
        )

        logger.log_operation(
            user_id=1,
            username="test_user",
            tool_name="XLSTransfer",
            function_name="test2",
            duration_seconds=1.0
        )

        # Logs should be queued
        assert len(logger.log_queue) >= 2


# ============================================
# Integration Tests (within logger module)
# ============================================

@pytest.mark.unit
@pytest.mark.client
def test_logger_complete_workflow(mock_config, mock_requests_success):
    """
    Test complete logger workflow from start to end.

    Given: A new UsageLogger instance
    When: Multiple operations are logged and session ends
    Then: All operations complete successfully
    """
    logger = UsageLogger()

    # Log several operations
    for i in range(5):
        logger.log_operation(
            user_id=1,
            username="test_user",
            tool_name="XLSTransfer",
            function_name=f"function_{i}",
            duration_seconds=float(i),
            status="success"
        )

    # End session
    logger.end_session()

    # Verify all calls were made (1 session start + 5 logs + 1 session end = 7)
    assert mock_requests_success.call_count == 7
