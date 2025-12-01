"""
Test Async Infrastructure

Test async database connections, dependencies, and endpoints.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import initialize_async_database, get_async_db
from server.utils.auth import get_current_user_async, create_access_token, hash_password
from server.database.models import User, LogEntry


@pytest.mark.asyncio
async def test_async_database_initialization():
    """Test that async database initializes correctly."""
    initialize_async_database()

    # Get a session
    async_gen = get_async_db()
    db = await async_gen.__anext__()

    assert db is not None
    assert isinstance(db, AsyncSession)

    # Cleanup
    await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_database_query():
    """Test that async queries work."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Try to query users table
        result = await db.execute(select(User).limit(5))
        users = result.scalars().all()

        # Should work even if empty
        assert isinstance(users, list)

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_user_creation():
    """Test creating a user with async session."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create test user with unique timestamp
        ts = int(datetime.utcnow().timestamp())
        test_user = User(
            username=f"test_async_{ts}",
            password_hash=hash_password("testpass123"),
            email=f"test_async_{ts}@example.com",
            full_name="Async Test User",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        assert test_user.user_id is not None
        print(f"✓ Created user with ID: {test_user.user_id}")

        # Verify we can query it back
        result = await db.execute(
            select(User).where(User.user_id == test_user.user_id)
        )
        fetched_user = result.scalar_one_or_none()

        assert fetched_user is not None
        assert fetched_user.username == test_user.username
        print(f"✓ Verified user: {fetched_user.username}")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_auth_get_current_user():
    """Test async JWT authentication."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create a test user first
        ts = int(datetime.utcnow().timestamp())
        test_user = User(
            username=f"auth_test_{ts}",
            password_hash=hash_password("password123"),
            email=f"auth_test_{ts}@example.com",
            full_name="Auth Test",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        # Create JWT token
        token = create_access_token({
            "user_id": test_user.user_id,
            "username": test_user.username
        })

        assert token is not None
        print(f"✓ Created JWT token")

        # Test async auth
        user_data = await get_current_user_async(token, db)

        assert user_data is not None
        assert user_data["username"] == test_user.username
        assert user_data["user_id"] == test_user.user_id
        print(f"✓ Async auth successful: {user_data['username']}")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_log_creation():
    """Test creating log entries with async session."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create a user first (log requires user_id)
        ts = int(datetime.utcnow().timestamp())
        test_user = User(
            username=f"log_test_{ts}",
            password_hash=hash_password("testpass"),
            email=f"log_test_{ts}@example.com",
            full_name="Log Test User",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        # Create test log with valid user_id
        test_log = LogEntry(
            user_id=test_user.user_id,  # Valid user_id required
            session_id=None,
            username=test_user.username,
            machine_id="test-machine",
            tool_name="TestTool",
            function_name="test_function",
            timestamp=datetime.utcnow(),
            duration_seconds=10.5,
            status="success"
        )

        db.add(test_log)
        await db.commit()
        await db.refresh(test_log)

        assert test_log.log_id is not None
        print(f"✓ Created log entry with ID: {test_log.log_id}")

        # Query it back
        result = await db.execute(
            select(LogEntry).where(LogEntry.log_id == test_log.log_id)
        )
        fetched_log = result.scalar_one_or_none()

        assert fetched_log is not None
        assert fetched_log.tool_name == "TestTool"
        assert fetched_log.duration_seconds == 10.5
        print(f"✓ Verified log: {fetched_log.tool_name} - {fetched_log.duration_seconds}s")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_transaction_rollback():
    """Test that async transactions rollback on error."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Start a transaction
        async with db.begin():
            test_log = LogEntry(
                username="rollback_test",
                machine_id="test-machine",
                tool_name="RollbackTest",
                function_name="test_rollback",
                timestamp=datetime.utcnow(),
                duration_seconds=1.0,
                status="success"
            )
            db.add(test_log)

            # Force an error by raising exception
            raise ValueError("Intentional error for rollback test")

    except ValueError:
        # Transaction should have rolled back
        pass

    # Verify the log was NOT saved
    result = await db.execute(
        select(LogEntry).where(LogEntry.tool_name == "RollbackTest")
    )
    logs = result.scalars().all()

    assert len(logs) == 0
    print(f"✓ Transaction rollback successful (no logs found)")

    await async_gen.aclose()


def test_sync_to_async_compatibility():
    """Test that sync and async can coexist."""
    from server.utils.dependencies import initialize_database, get_db

    # Initialize sync database
    initialize_database()

    # Get sync session
    sync_gen = get_db()
    sync_db = next(sync_gen)

    assert sync_db is not None
    print("✓ Sync database still works")

    sync_db.close()

    # Initialize async database
    initialize_async_database()
    print("✓ Both sync and async can coexist")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Async Infrastructure")
    print("=" * 60)

    # Run async tests
    asyncio.run(test_async_database_initialization())
    print()

    asyncio.run(test_async_database_query())
    print()

    asyncio.run(test_async_user_creation())
    print()

    asyncio.run(test_async_auth_get_current_user())
    print()

    asyncio.run(test_async_log_creation())
    print()

    asyncio.run(test_async_transaction_rollback())
    print()

    test_sync_to_async_compatibility()
    print()

    print("=" * 60)
    print("✓ All async infrastructure tests passed!")
    print("=" * 60)
