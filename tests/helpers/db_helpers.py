"""
Database Test Helpers

Functions for creating, managing, and cleaning up test data in the database.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession


def create_test_user(
    db: Session,
    username: str = None,
    email: str = None,
    password_hash: str = "test_hash_123",
    role: str = "user",
    department: str = "test_dept",
    is_active: bool = True,
) -> "User":
    """
    Create a test user in the database.

    Args:
        db: Database session
        username: Username (auto-generated if None)
        email: Email (auto-generated if None)
        password_hash: Password hash
        role: User role (user, admin, superadmin)
        department: Department name
        is_active: Whether user is active

    Returns:
        Created User object
    """
    from server.database.models import User

    if username is None:
        username = f"test_user_{uuid.uuid4().hex[:8]}"
    if email is None:
        email = f"{username}@test.com"

    user = User(
        username=username,
        password_hash=password_hash,
        email=email,
        full_name=f"Test User {username}",
        department=department,
        role=role,
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_session(
    db: Session,
    user_id: int,
    machine_id: str = None,
    ip_address: str = "127.0.0.1",
    app_version: str = "1.0.0",
    is_active: bool = True,
) -> "Session":
    """
    Create a test session for a user.

    Args:
        db: Database session
        user_id: ID of the user
        machine_id: Machine identifier (auto-generated if None)
        ip_address: IP address
        app_version: App version string
        is_active: Whether session is active

    Returns:
        Created Session object
    """
    from server.database.models import Session as DBSession

    if machine_id is None:
        machine_id = f"test_machine_{uuid.uuid4().hex[:8]}"

    session = DBSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        machine_id=machine_id,
        ip_address=ip_address,
        app_version=app_version,
        session_start=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        is_active=is_active,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def create_test_log_entry(
    db: Session,
    user_id: int,
    username: str,
    tool_name: str = "test_tool",
    function_name: str = "test_function",
    machine_id: str = None,
    session_id: str = None,
    duration_seconds: float = 1.0,
    status: str = "success",
    error_message: str = None,
    file_info: Dict[str, Any] = None,
    parameters: Dict[str, Any] = None,
) -> "LogEntry":
    """
    Create a test log entry.

    Args:
        db: Database session
        user_id: ID of the user
        username: Username
        tool_name: Name of the tool
        function_name: Name of the function
        machine_id: Machine identifier
        session_id: Session ID
        duration_seconds: Operation duration
        status: Operation status
        error_message: Error message if any
        file_info: File metadata
        parameters: Operation parameters

    Returns:
        Created LogEntry object
    """
    from server.database.models import LogEntry

    if machine_id is None:
        machine_id = f"test_machine_{uuid.uuid4().hex[:8]}"

    log_entry = LogEntry(
        user_id=user_id,
        session_id=session_id,
        username=username,
        machine_id=machine_id,
        tool_name=tool_name,
        function_name=function_name,
        timestamp=datetime.utcnow(),
        duration_seconds=duration_seconds,
        status=status,
        error_message=error_message,
        file_info=file_info,
        parameters=parameters,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def cleanup_test_data(db: Session, prefix: str = "test_") -> int:
    """
    Clean up test data from the database.

    Args:
        db: Database session
        prefix: Username prefix to identify test users

    Returns:
        Number of records deleted
    """
    from server.database.models import User, Session as DBSession, LogEntry

    count = 0

    # Delete log entries for test users
    test_users = db.query(User).filter(User.username.like(f"{prefix}%")).all()
    for user in test_users:
        entries = db.query(LogEntry).filter(LogEntry.user_id == user.user_id).delete()
        count += entries
        sessions = db.query(DBSession).filter(DBSession.user_id == user.user_id).delete()
        count += sessions

    # Delete test users
    users_deleted = db.query(User).filter(User.username.like(f"{prefix}%")).delete()
    count += users_deleted

    db.commit()
    return count


async def async_create_test_user(
    db: AsyncSession,
    username: str = None,
    email: str = None,
    password_hash: str = "test_hash_123",
    role: str = "user",
) -> "User":
    """
    Async version of create_test_user.
    """
    from server.database.models import User

    if username is None:
        username = f"test_user_{uuid.uuid4().hex[:8]}"
    if email is None:
        email = f"{username}@test.com"

    user = User(
        username=username,
        password_hash=password_hash,
        email=email,
        full_name=f"Test User {username}",
        department="test_dept",
        role=role,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
