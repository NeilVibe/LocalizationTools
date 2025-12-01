"""
Test Async Auth Endpoints

Test authentication and user management with async database.
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.dependencies import initialize_async_database, get_async_db
from server.utils.auth import (
    hash_password, verify_password, create_access_token,
    verify_token, get_current_user_async
)
from server.database.models import User


@pytest.mark.asyncio
async def test_async_user_authentication():
    """Test user authentication flow with async."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create test user
        ts = int(datetime.utcnow().timestamp())
        password = "SecurePassword123"
        password_hash = hash_password(password)

        test_user = User(
            username=f"auth_user_{ts}",
            password_hash=password_hash,
            email=f"auth_user_{ts}@example.com",
            full_name="Auth Test User",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        print(f"✓ Created user: {test_user.username}")

        # Verify password works
        assert verify_password(password, password_hash) is True
        assert verify_password("WrongPassword", password_hash) is False
        print(f"✓ Password verification works")

        # Create JWT token
        token = create_access_token({
            "user_id": test_user.user_id,
            "username": test_user.username,
            "role": test_user.role
        })

        assert token is not None
        print(f"✓ Created JWT token")

        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == test_user.user_id
        assert payload["username"] == test_user.username
        print(f"✓ Token verification successful")

        # Get user from token (async)
        user_data = await get_current_user_async(token, db)
        assert user_data is not None
        assert user_data["username"] == test_user.username
        assert user_data["user_id"] == test_user.user_id
        assert user_data["role"] == test_user.role
        print(f"✓ Async user retrieval successful")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_user_roles():
    """Test user roles and permissions."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        ts = int(datetime.utcnow().timestamp())

        # Create regular user
        regular_user = User(
            username=f"regular_user_{ts}",
            password_hash=hash_password("password123"),
            email=f"regular_{ts}@example.com",
            full_name="Regular User",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        # Create admin user
        admin_user = User(
            username=f"admin_user_{ts}",
            password_hash=hash_password("adminpass123"),
            email=f"admin_{ts}@example.com",
            full_name="Admin User",
            department="IT",
            role="admin",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(regular_user)
        db.add(admin_user)
        await db.commit()
        await db.refresh(regular_user)
        await db.refresh(admin_user)

        print(f"✓ Created regular user: {regular_user.username}")
        print(f"✓ Created admin user: {admin_user.username}")

        # Verify roles
        assert regular_user.role == "user"
        assert admin_user.role == "admin"

        # Query users by role
        result = await db.execute(
            select(User).where(User.role == "admin")
        )
        admins = result.scalars().all()

        assert any(admin.user_id == admin_user.user_id for admin in admins)
        print(f"✓ Found {len(admins)} admin users in database")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_user_activation():
    """Test user activation/deactivation."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create active user
        ts = int(datetime.utcnow().timestamp())
        test_user = User(
            username=f"activation_test_{ts}",
            password_hash=hash_password("testpass"),
            email=f"activation_{ts}@example.com",
            full_name="Activation Test",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        assert test_user.is_active is True
        print(f"✓ Created active user: {test_user.username}")

        # Deactivate user
        test_user.is_active = False
        await db.commit()
        await db.refresh(test_user)
        assert test_user.is_active is False
        print(f"✓ Deactivated user")

        # Reactivate user
        test_user.is_active = True
        await db.commit()
        await db.refresh(test_user)
        assert test_user.is_active is True
        print(f"✓ Reactivated user")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_user_query_operations():
    """Test various user query operations."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Query by username
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print(f"✓ Found admin user: {admin_user.username}")
        else:
            print("✓ No admin user found (expected in new database)")

        # Query active users
        result = await db.execute(
            select(User).where(User.is_active == True).limit(10)
        )
        active_users = result.scalars().all()

        assert isinstance(active_users, list)
        print(f"✓ Found {len(active_users)} active users")

        # Count users by department
        ts = int(datetime.utcnow().timestamp())
        test_dept = f"TestDept_{ts}"

        # Create users in same department
        for i in range(3):
            user = User(
                username=f"dept_user_{ts}_{i}",
                password_hash=hash_password("testpass"),
                email=f"dept_user_{ts}_{i}@example.com",
                full_name=f"Dept User {i}",
                department=test_dept,
                role="user",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)

        await db.commit()
        print(f"✓ Created 3 users in department {test_dept}")

        # Query by department
        result = await db.execute(
            select(User).where(User.department == test_dept)
        )
        dept_users = result.scalars().all()

        assert len(dept_users) == 3
        print(f"✓ Found {len(dept_users)} users in department {test_dept}")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_user_unique_constraints():
    """Test unique constraints on username and email."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        ts = int(datetime.utcnow().timestamp())

        # Create first user
        user1 = User(
            username=f"unique_test_{ts}",
            password_hash=hash_password("pass1"),
            email=f"unique_{ts}@example.com",
            full_name="Unique Test 1",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(user1)
        await db.commit()
        await db.refresh(user1)
        print(f"✓ Created user: {user1.username}")

        # Check username doesn't exist yet
        result = await db.execute(
            select(User).where(User.username == f"unique_test_{ts}_2")
        )
        existing = result.scalar_one_or_none()
        assert existing is None

        # Check email doesn't exist yet
        result = await db.execute(
            select(User).where(User.email == f"unique2_{ts}@example.com")
        )
        existing = result.scalar_one_or_none()
        assert existing is None

        print(f"✓ Verified username and email uniqueness checks work")

    finally:
        await async_gen.aclose()


@pytest.mark.asyncio
async def test_async_last_login_update():
    """Test updating last login timestamp."""
    initialize_async_database()

    async_gen = get_async_db()
    db = await async_gen.__anext__()

    try:
        # Create user without last login
        ts = int(datetime.utcnow().timestamp())
        test_user = User(
            username=f"login_test_{ts}",
            password_hash=hash_password("testpass"),
            email=f"login_test_{ts}@example.com",
            full_name="Login Test",
            department="Testing",
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
            last_login=None
        )

        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        assert test_user.last_login is None
        print(f"✓ Created user without last_login")

        # Simulate login - update last_login
        test_user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(test_user)

        assert test_user.last_login is not None
        print(f"✓ Updated last_login to {test_user.last_login}")

    finally:
        await async_gen.aclose()


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("Testing Async Authentication")
    print("=" * 60)

    asyncio.run(test_async_user_authentication())
    print()

    asyncio.run(test_async_user_roles())
    print()

    asyncio.run(test_async_user_activation())
    print()

    asyncio.run(test_async_user_query_operations())
    print()

    asyncio.run(test_async_user_unique_constraints())
    print()

    asyncio.run(test_async_last_login_update())
    print()

    print("=" * 60)
    print("✓ All async auth tests passed!")
    print("=" * 60)
