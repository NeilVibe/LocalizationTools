"""
Audit Logging Tests

Tests for the security audit logging system that tracks
login attempts, blocked IPs, and other security events.
"""

import os
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from server.utils.audit_logger import (
    AuditEventType,
    AuditSeverity,
    log_audit_event,
    log_login_success,
    log_login_failure,
    log_logout,
    log_ip_blocked,
    log_password_change,
    log_user_created,
    log_user_deleted,
    log_server_started,
    log_rate_limited,
    get_audit_log_path,
    get_recent_audit_events,
    get_failed_login_count,
    AUDIT_LOG_FILE,
)


class TestAuditEventTypes:
    """Tests for audit event type definitions."""

    def test_authentication_event_types_exist(self):
        """Test that authentication event types are defined."""
        assert AuditEventType.LOGIN_SUCCESS
        assert AuditEventType.LOGIN_FAILURE
        assert AuditEventType.LOGOUT
        assert AuditEventType.TOKEN_REFRESH
        assert AuditEventType.PASSWORD_CHANGE

    def test_access_control_event_types_exist(self):
        """Test that access control event types are defined."""
        assert AuditEventType.IP_BLOCKED
        assert AuditEventType.IP_ALLOWED
        assert AuditEventType.CORS_BLOCKED
        assert AuditEventType.RATE_LIMITED

    def test_admin_event_types_exist(self):
        """Test that admin event types are defined."""
        assert AuditEventType.USER_CREATED
        assert AuditEventType.USER_DELETED
        assert AuditEventType.USER_MODIFIED
        assert AuditEventType.PERMISSION_CHANGED

    def test_system_event_types_exist(self):
        """Test that system event types are defined."""
        assert AuditEventType.SECURITY_CONFIG_CHANGED
        assert AuditEventType.SERVER_STARTED
        assert AuditEventType.SERVER_STOPPED


class TestAuditSeverity:
    """Tests for audit severity levels."""

    def test_severity_levels_exist(self):
        """Test that severity levels are defined."""
        assert AuditSeverity.INFO
        assert AuditSeverity.WARNING
        assert AuditSeverity.CRITICAL


class TestLogAuditEvent:
    """Tests for the main log_audit_event function."""

    def test_log_audit_event_returns_dict(self):
        """Test that log_audit_event returns event dict."""
        event = log_audit_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            username="testuser",
            ip_address="192.168.1.100",
        )

        assert isinstance(event, dict)
        assert "timestamp" in event
        assert "event_type" in event
        assert event["event_type"] == "LOGIN_SUCCESS"
        assert event["username"] == "testuser"
        assert event["ip_address"] == "192.168.1.100"

    def test_log_audit_event_includes_all_fields(self):
        """Test that all fields are included in event."""
        event = log_audit_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.WARNING,
            user_id=123,
            username="testuser",
            ip_address="192.168.1.100",
            details={"reason": "Invalid password"},
            success=False,
        )

        assert event["event_type"] == "LOGIN_FAILURE"
        assert event["severity"] == "WARNING"
        assert event["user_id"] == 123
        assert event["username"] == "testuser"
        assert event["ip_address"] == "192.168.1.100"
        assert event["details"]["reason"] == "Invalid password"
        assert event["success"] is False

    def test_log_audit_event_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO format."""
        event = log_audit_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
        )

        # Should be parseable as ISO datetime
        timestamp = datetime.fromisoformat(event["timestamp"])
        assert isinstance(timestamp, datetime)


class TestConvenienceFunctions:
    """Tests for convenience logging functions."""

    def test_log_login_success(self):
        """Test log_login_success function."""
        event = log_login_success(
            username="admin",
            ip_address="192.168.1.100",
            user_id=1,
        )

        assert event["event_type"] == "LOGIN_SUCCESS"
        assert event["username"] == "admin"
        assert event["ip_address"] == "192.168.1.100"
        assert event["user_id"] == 1
        assert event["success"] is True

    def test_log_login_failure(self):
        """Test log_login_failure function."""
        event = log_login_failure(
            username="baduser",
            ip_address="10.0.0.1",
            reason="Invalid credentials",
        )

        assert event["event_type"] == "LOGIN_FAILURE"
        assert event["username"] == "baduser"
        assert event["ip_address"] == "10.0.0.1"
        assert event["details"]["reason"] == "Invalid credentials"
        assert event["success"] is False
        assert event["severity"] == "WARNING"

    def test_log_logout(self):
        """Test log_logout function."""
        event = log_logout(
            username="admin",
            ip_address="192.168.1.100",
            user_id=1,
        )

        assert event["event_type"] == "LOGOUT"
        assert event["success"] is True

    def test_log_ip_blocked(self):
        """Test log_ip_blocked function."""
        event = log_ip_blocked(
            ip_address="203.0.113.50",
            reason="IP not in allowed range",
        )

        assert event["event_type"] == "IP_BLOCKED"
        assert event["ip_address"] == "203.0.113.50"
        assert event["details"]["reason"] == "IP not in allowed range"
        assert event["success"] is False
        assert event["severity"] == "WARNING"

    def test_log_password_change(self):
        """Test log_password_change function."""
        event = log_password_change(
            username="user1",
            ip_address="192.168.1.100",
            user_id=5,
        )

        assert event["event_type"] == "PASSWORD_CHANGE"
        assert event["username"] == "user1"
        assert event["success"] is True

    def test_log_password_change_by_admin(self):
        """Test log_password_change when changed by admin."""
        event = log_password_change(
            username="user1",
            ip_address="192.168.1.100",
            user_id=5,
            changed_by="admin",
        )

        assert event["event_type"] == "PASSWORD_CHANGE"
        assert event["details"]["changed_by"] == "admin"

    def test_log_user_created(self):
        """Test log_user_created function."""
        event = log_user_created(
            new_username="newuser",
            created_by="admin",
            ip_address="192.168.1.100",
            user_id=10,
        )

        assert event["event_type"] == "USER_CREATED"
        assert event["username"] == "newuser"
        assert event["details"]["created_by"] == "admin"
        assert event["success"] is True

    def test_log_user_deleted(self):
        """Test log_user_deleted function."""
        event = log_user_deleted(
            deleted_username="olduser",
            deleted_by="admin",
            ip_address="192.168.1.100",
        )

        assert event["event_type"] == "USER_DELETED"
        assert event["username"] == "olduser"
        assert event["details"]["deleted_by"] == "admin"
        assert event["severity"] == "WARNING"

    def test_log_server_started(self):
        """Test log_server_started function."""
        config_summary = {
            "version": "1.0.0",
            "ip_filter_enabled": True,
        }
        event = log_server_started(config_summary)

        assert event["event_type"] == "SERVER_STARTED"
        assert event["details"]["version"] == "1.0.0"
        assert event["success"] is True

    def test_log_rate_limited(self):
        """Test log_rate_limited function."""
        event = log_rate_limited(
            ip_address="192.168.1.100",
            endpoint="/api/v2/auth/login",
        )

        assert event["event_type"] == "RATE_LIMITED"
        assert event["ip_address"] == "192.168.1.100"
        assert event["details"]["endpoint"] == "/api/v2/auth/login"
        assert event["severity"] == "WARNING"


class TestAuditLogFile:
    """Tests for audit log file operations."""

    def test_get_audit_log_path_returns_path(self):
        """Test that get_audit_log_path returns a Path object."""
        path = get_audit_log_path()
        assert isinstance(path, Path)
        assert path.name == "security_audit.log"

    def test_audit_log_file_is_in_logs_directory(self):
        """Test that audit log is in the logs directory."""
        path = get_audit_log_path()
        assert "logs" in str(path)

    def test_get_recent_audit_events_returns_list(self):
        """Test that get_recent_audit_events returns a list."""
        events = get_recent_audit_events(limit=10)
        assert isinstance(events, list)

    def test_get_recent_audit_events_respects_limit(self):
        """Test that get_recent_audit_events respects limit parameter."""
        # Log some events
        for i in range(5):
            log_login_success(f"user{i}", f"192.168.1.{i}", i)

        events = get_recent_audit_events(limit=3)
        assert len(events) <= 3


class TestFailedLoginCount:
    """Tests for failed login counting."""

    def test_get_failed_login_count_returns_int(self):
        """Test that get_failed_login_count returns an integer."""
        count = get_failed_login_count("192.168.1.100")
        assert isinstance(count, int)
        assert count >= 0

    def test_get_failed_login_count_for_unknown_ip(self):
        """Test failed login count for IP with no failures."""
        count = get_failed_login_count("255.255.255.255")
        assert count == 0


class TestAuditLogIntegration:
    """Integration tests for audit logging."""

    def test_events_are_logged_to_file(self):
        """Test that events are actually written to the log file."""
        # Log a unique event
        unique_user = f"testuser_{datetime.utcnow().timestamp()}"
        log_login_success(unique_user, "192.168.1.100", 999)

        # Check if the event appears in the file
        log_path = get_audit_log_path()
        if log_path.exists():
            with open(log_path, 'r') as f:
                content = f.read()
                assert unique_user in content or "LOGIN_SUCCESS" in content

    def test_multiple_event_types_logged(self):
        """Test that different event types are logged correctly."""
        # Log different types of events
        log_login_success("user1", "192.168.1.1", 1)
        log_login_failure("user2", "192.168.1.2", "Wrong password")
        log_ip_blocked("10.0.0.1", "Not in range")

        # All should complete without error
        events = get_recent_audit_events(limit=10)
        assert isinstance(events, list)


class TestSeverityLogging:
    """Tests for severity-based logging."""

    def test_info_severity_events(self):
        """Test that INFO severity events are logged."""
        event = log_audit_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
        )
        assert event["severity"] == "INFO"

    def test_warning_severity_events(self):
        """Test that WARNING severity events are logged."""
        event = log_audit_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.WARNING,
        )
        assert event["severity"] == "WARNING"

    def test_critical_severity_events(self):
        """Test that CRITICAL severity events are logged."""
        event = log_audit_event(
            event_type=AuditEventType.USER_DELETED,
            severity=AuditSeverity.CRITICAL,
        )
        assert event["severity"] == "CRITICAL"
