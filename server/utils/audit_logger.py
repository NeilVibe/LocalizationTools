"""
Security Audit Logger

Logs security-relevant events for IT security compliance:
- Login attempts (success/failure)
- Blocked IP attempts
- Admin operations
- Password changes
- Security configuration changes

All events are logged to both file and database for easy querying.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

# Audit log file path
AUDIT_LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "security_audit.log"


class AuditEventType(str, Enum):
    """Types of security audit events."""
    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"

    # Access control events
    IP_BLOCKED = "IP_BLOCKED"
    IP_ALLOWED = "IP_ALLOWED"
    CORS_BLOCKED = "CORS_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"

    # Admin events
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"
    USER_MODIFIED = "USER_MODIFIED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"

    # Security config events
    SECURITY_CONFIG_CHANGED = "SECURITY_CONFIG_CHANGED"
    SERVER_STARTED = "SERVER_STARTED"
    SERVER_STOPPED = "SERVER_STOPPED"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# Configure audit logger
audit_logger = logging.getLogger("security_audit")
audit_logger.setLevel(logging.INFO)

# File handler for audit log
if not audit_logger.handlers:
    file_handler = logging.FileHandler(AUDIT_LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    audit_logger.addHandler(file_handler)


def log_audit_event(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.INFO,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> Dict[str, Any]:
    """
    Log a security audit event.

    Args:
        event_type: Type of security event
        severity: Event severity level
        user_id: User ID (if applicable)
        username: Username (if applicable)
        ip_address: Client IP address
        details: Additional event details
        success: Whether the action was successful

    Returns:
        Dict containing the logged event data
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type.value,
        "severity": severity.value,
        "success": success,
        "user_id": user_id,
        "username": username,
        "ip_address": ip_address,
        "details": details or {},
    }

    # Format log message
    msg_parts = [
        f"[{event_type.value}]",
        f"success={success}",
    ]

    if username:
        msg_parts.append(f"user={username}")
    if ip_address:
        msg_parts.append(f"ip={ip_address}")
    if details:
        msg_parts.append(f"details={json.dumps(details)}")

    log_message = " | ".join(msg_parts)

    # Log to file
    if severity == AuditSeverity.CRITICAL:
        audit_logger.critical(log_message)
    elif severity == AuditSeverity.WARNING:
        audit_logger.warning(log_message)
    else:
        audit_logger.info(log_message)

    # Also log to main logger for visibility
    if severity == AuditSeverity.CRITICAL:
        logger.critical(f"AUDIT: {log_message}")
    elif severity == AuditSeverity.WARNING:
        logger.warning(f"AUDIT: {log_message}")
    else:
        logger.info(f"AUDIT: {log_message}")

    return event


# Convenience functions for common events

def log_login_success(username: str, ip_address: str, user_id: Optional[int] = None) -> Dict:
    """Log successful login attempt."""
    return log_audit_event(
        event_type=AuditEventType.LOGIN_SUCCESS,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        success=True,
    )


def log_login_failure(
    username: str,
    ip_address: str,
    reason: str = "Invalid credentials"
) -> Dict:
    """Log failed login attempt."""
    return log_audit_event(
        event_type=AuditEventType.LOGIN_FAILURE,
        severity=AuditSeverity.WARNING,
        username=username,
        ip_address=ip_address,
        details={"reason": reason},
        success=False,
    )


def log_logout(username: str, ip_address: str, user_id: Optional[int] = None) -> Dict:
    """Log user logout."""
    return log_audit_event(
        event_type=AuditEventType.LOGOUT,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        success=True,
    )


def log_ip_blocked(ip_address: str, reason: str = "IP not in allowed range") -> Dict:
    """Log blocked IP attempt."""
    return log_audit_event(
        event_type=AuditEventType.IP_BLOCKED,
        severity=AuditSeverity.WARNING,
        ip_address=ip_address,
        details={"reason": reason},
        success=False,
    )


def log_password_change(
    username: str,
    ip_address: str,
    user_id: Optional[int] = None,
    changed_by: Optional[str] = None
) -> Dict:
    """Log password change."""
    details = {}
    if changed_by and changed_by != username:
        details["changed_by"] = changed_by

    return log_audit_event(
        event_type=AuditEventType.PASSWORD_CHANGE,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        details=details if details else None,
        success=True,
    )


def log_user_created(
    new_username: str,
    created_by: str,
    ip_address: str,
    user_id: Optional[int] = None
) -> Dict:
    """Log new user creation."""
    return log_audit_event(
        event_type=AuditEventType.USER_CREATED,
        severity=AuditSeverity.INFO,
        user_id=user_id,
        username=new_username,
        ip_address=ip_address,
        details={"created_by": created_by},
        success=True,
    )


def log_user_deleted(
    deleted_username: str,
    deleted_by: str,
    ip_address: str
) -> Dict:
    """Log user deletion."""
    return log_audit_event(
        event_type=AuditEventType.USER_DELETED,
        severity=AuditSeverity.WARNING,
        username=deleted_username,
        ip_address=ip_address,
        details={"deleted_by": deleted_by},
        success=True,
    )


def log_server_started(config_summary: Dict[str, Any]) -> Dict:
    """Log server startup."""
    return log_audit_event(
        event_type=AuditEventType.SERVER_STARTED,
        severity=AuditSeverity.INFO,
        details=config_summary,
        success=True,
    )


def log_rate_limited(ip_address: str, endpoint: str) -> Dict:
    """Log rate limiting event."""
    return log_audit_event(
        event_type=AuditEventType.RATE_LIMITED,
        severity=AuditSeverity.WARNING,
        ip_address=ip_address,
        details={"endpoint": endpoint},
        success=False,
    )


def get_audit_log_path() -> Path:
    """Get the path to the audit log file."""
    return AUDIT_LOG_FILE


def get_recent_audit_events(limit: int = 100) -> list:
    """
    Read recent audit events from log file.

    Args:
        limit: Maximum number of events to return

    Returns:
        List of recent audit events (newest first)
    """
    events = []

    if not AUDIT_LOG_FILE.exists():
        return events

    try:
        with open(AUDIT_LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Get last N lines (newest)
        recent_lines = lines[-limit:] if len(lines) > limit else lines

        for line in reversed(recent_lines):
            line = line.strip()
            if line:
                events.append(line)

        return events
    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []


def get_failed_login_count(ip_address: str, minutes: int = 15) -> int:
    """
    Count failed login attempts from an IP in the last N minutes.

    Useful for implementing account lockout.

    Args:
        ip_address: IP to check
        minutes: Time window in minutes

    Returns:
        Count of failed login attempts
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    count = 0

    if not AUDIT_LOG_FILE.exists():
        return 0

    try:
        with open(AUDIT_LOG_FILE, 'r') as f:
            for line in f:
                if AuditEventType.LOGIN_FAILURE.value in line and ip_address in line:
                    # Parse timestamp from line
                    try:
                        timestamp_str = line.split(' | ')[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        if timestamp > cutoff:
                            count += 1
                    except (ValueError, IndexError):
                        continue

        return count
    except Exception as e:
        logger.error(f"Error counting failed logins: {e}")
        return 0
