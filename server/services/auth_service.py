"""
AuthService - Business logic for authentication and user management.

Extracted from server/api/auth_async.py. Handles all async user operations.
The sync login endpoint remains in the route file (it uses sync Session).

Usage:
    from server.services.auth_service import AuthService

    service = AuthService(async_db_session)
    user = await service.get_user_by_id(1)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from server.database.models import User
from server.utils.auth import hash_password, verify_password


# Valid user roles -- Phase 110: added superadmin tier
VALID_ROLES = ["user", "admin", "superadmin"]

# Role hierarchy for permission checks
ROLE_HIERARCHY = {"user": 0, "admin": 1, "superadmin": 2}


class AuthService:
    """Service layer for authentication and user management (async only)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # User Lookup
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Fetch a single user by ID."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Return a paginated list of all users ordered by ID."""
        query = select(User).order_by(User.user_id).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Registration
    # =========================================================================

    async def register_user(
        self,
        username: str,
        password: str,
        email: str | None = None,
        full_name: str | None = None,
        department: str | None = None,
    ) -> User:
        """
        Register a new user with default role='user'.

        Raises:
            ValueError: If username or email already exists.
        """
        # Check username uniqueness
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Check email uniqueness
        if email:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            if result.scalar_one_or_none():
                raise ValueError("Email already registered")

        new_user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            full_name=full_name,
            department=department,
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
        )

        self.db.add(new_user)
        await self.db.flush()
        await self.db.refresh(new_user)

        logger.info(f"New user registered: {new_user.username} (ID: {new_user.user_id})")
        return new_user

    # =========================================================================
    # Activate / Deactivate
    # =========================================================================

    async def activate_user(self, user_id: int) -> User:
        """
        Set a user's is_active to True.

        Raises:
            LookupError: If user not found.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        user.is_active = True
        await self.db.commit()

        logger.info(f"User {user.username} activated")
        return user

    async def deactivate_user(self, user_id: int, admin_user_id: int) -> User:
        """
        Set a user's is_active to False.

        Raises:
            LookupError: If user not found.
            ValueError: If admin tries to deactivate themselves.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        if user.user_id == admin_user_id:
            raise ValueError("Cannot deactivate your own account")

        user.is_active = False
        await self.db.commit()

        logger.info(f"User {user.username} deactivated")
        return user

    # =========================================================================
    # Password Management
    # =========================================================================

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Self-service password change. Verifies current password first.

        Raises:
            LookupError: If user not found.
            ValueError: If current password is incorrect.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        user.last_password_change = datetime.utcnow()
        user.must_change_password = False
        await self.db.commit()

        logger.info(f"Password changed for user: {user.username}")
        return user

    async def admin_reset_password(
        self,
        user_id: int,
        new_password: str,
        must_change_password: bool = True,
    ) -> User:
        """
        Admin resets a user's password.

        Raises:
            LookupError: If user not found.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        user.password_hash = hash_password(new_password)
        user.last_password_change = datetime.utcnow()
        user.must_change_password = must_change_password
        await self.db.commit()

        logger.info(f"Password reset for user: {user.username}")
        return user

    # =========================================================================
    # Admin User CRUD
    # =========================================================================

    async def admin_create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        email: str | None = None,
        full_name: str | None = None,
        team: str | None = None,
        language: str | None = None,
        department: str | None = None,
        must_change_password: bool = False,
        created_by: int | None = None,
        creator_role: str | None = None,
    ) -> User:
        """
        Admin creates a user with full profile fields.

        Raises:
            ValueError: If username/email already exists or role is invalid.
        """
        # Check username uniqueness
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Check email uniqueness
        if email:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            if result.scalar_one_or_none():
                raise ValueError("Email already registered")

        # Validate role
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {VALID_ROLES}")

        # Phase 110: Only superadmin can assign superadmin role
        if role == "superadmin" and creator_role != "superadmin":
            logger.warning(f"[PHASE110:ROLE] Non-superadmin (role={creator_role}) tried to create superadmin user '{username}'")
            raise ValueError("Only superadmin can assign superadmin role")

        new_user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            full_name=full_name,
            team=team,
            language=language,
            department=department,
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
            created_by=created_by,
            must_change_password=must_change_password,
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        logger.info(f"New user created: {new_user.username} (ID: {new_user.user_id})")
        return new_user

    async def admin_update_user(
        self,
        user_id: int,
        update_data: dict[str, Any],
        admin_user_id: int,
    ) -> User:
        """
        Admin updates user profile fields.

        Args:
            user_id: Target user ID.
            update_data: Dict of fields to update (from model_dump(exclude_unset=True)).
            admin_user_id: ID of the admin performing the update.

        Raises:
            LookupError: If user not found.
            ValueError: If email conflict, invalid role, or self-demotion.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        # Check email uniqueness if being updated
        new_email = update_data.get("email")
        if new_email and new_email != user.email:
            result = await self.db.execute(
                select(User).where(User.email == new_email)
            )
            if result.scalar_one_or_none():
                raise ValueError("Email already registered")

        # Validate role if being updated
        new_role = update_data.get("role")
        if new_role and new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {VALID_ROLES}")

        # Phase 110: Only superadmin can assign/change to superadmin role
        if new_role == "superadmin":
            admin = await self.get_user_by_id(admin_user_id)
            if not admin or admin.role != "superadmin":
                logger.warning(f"[PHASE110:ROLE] Non-superadmin (user_id={admin_user_id}) tried to set superadmin on user_id={user_id}")
                raise ValueError("Only superadmin can assign superadmin role")

        # Prevent admin from demoting themselves
        if user.user_id == admin_user_id and new_role and ROLE_HIERARCHY.get(new_role, 0) < ROLE_HIERARCHY.get(user.role, 0):
            raise ValueError("Cannot demote your own account")

        # Apply updates
        for field, value in update_data.items():
            if value is not None:
                setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User {user.username} updated: {update_data}")
        return user

    async def admin_delete_user(self, user_id: int, admin_user_id: int) -> User:
        """
        Soft-delete a user (set is_active=False).

        Raises:
            LookupError: If user not found.
            ValueError: If admin tries to delete themselves or user_id=1.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise LookupError("User not found")

        if user.user_id == admin_user_id:
            raise ValueError("Cannot delete your own account")

        # Phase 110: user_id=1 is the machine owner, cannot be deleted
        if user.user_id == 1:
            logger.warning(f"[PHASE110:ROLE] Attempt to delete protected user_id=1 (machine owner) by admin_user_id={admin_user_id}")
            raise ValueError("Cannot delete the machine owner account (user_id=1)")

        user.is_active = False
        await self.db.commit()

        logger.info(f"User {user.username} deactivated (soft delete)")
        return user
