"""
Authentication API Endpoints (ASYNC)

User registration, login, and authentication management with async/await.
"""

import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from loguru import logger

from server.api.schemas import (
    UserLogin, UserRegister, Token, UserResponse,
    PasswordChange, AdminUserCreate, AdminUserUpdate, AdminPasswordReset
)
from server.database.models import User
from server.utils.dependencies import get_db, get_async_db, get_current_active_user_async, require_admin_async
from server.utils.auth import hash_password, verify_password, create_access_token
from server.utils.audit_logger import (
    log_login_success,
    log_login_failure,
    log_user_created,
    log_password_change,
    get_failed_login_count,
)

# Rate limiting constants
MAX_FAILED_LOGINS = 5  # Max attempts per IP
LOCKOUT_MINUTES = 15   # Time window for rate limiting


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


# Valid user roles
VALID_ROLES = ["user", "admin"]

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Public Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User login endpoint (SYNC - works with both PostgreSQL and SQLite).

    Returns JWT access token on successful authentication.
    Rate limited: max 5 failed attempts per IP per 15 minutes.
    """
    client_ip = get_client_ip(request)

    # Rate limiting check (skip in DEV_MODE or test environments)
    # See docs/cicd/TROUBLESHOOTING.md "Test Isolation Pattern"
    # Use os.environ directly to avoid import issues
    dev_mode = os.environ.get("DEV_MODE", "").lower() == "true"
    skip_rate_limit = (
        dev_mode or  # DEV_MODE=true disables rate limiting for CI tests
        os.environ.get("PYTEST_CURRENT_TEST") or  # pytest sets this when running tests
        os.environ.get("CI") == "true" or  # CI environment
        client_ip == "testclient"  # FastAPI TestClient uses this IP
    )
    if not skip_rate_limit:
        failed_count = get_failed_login_count(client_ip, LOCKOUT_MINUTES)
        if failed_count >= MAX_FAILED_LOGINS:
            logger.warning(f"Rate limit exceeded for IP: {client_ip} ({failed_count} failed attempts)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Please try again in {LOCKOUT_MINUTES} minutes."
            )

    # Find user by username
    result = db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login attempt with non-existent username: {credentials.username}")
        # Audit log: failed login (user not found)
        log_login_failure(credentials.username, client_ip, "User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {credentials.username}")
        # Audit log: failed login (wrong password)
        log_login_failure(credentials.username, client_ip, "Invalid password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt by inactive user: {credentials.username}")
        # Audit log: failed login (inactive user)
        log_login_failure(credentials.username, client_ip, "User account inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    token_data = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role
    }
    access_token = create_access_token(token_data)

    # Audit log: successful login
    log_login_success(user.username, client_ip, user.user_id)
    logger.info(f"User logged in successfully: {user.username} (ID: {user.user_id})")

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)  # Only admins can register new users
):
    """
    User registration endpoint (admin only) (ASYNC).

    Creates a new user account.
    """
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists (if provided)
    if user_data.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_email = result.scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create new user
    async with db.begin():
        new_user = User(
            username=user_data.username,
            password_hash=password_hash,
            email=user_data.email,
            full_name=user_data.full_name,
            department=user_data.department,
            role="user",  # Default role
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(new_user)
        await db.flush()  # Flush to get the user_id
        await db.refresh(new_user)

    logger.info(f"New user registered: {new_user.username} (ID: {new_user.user_id}) by admin: {admin['username']}")

    return new_user


# ============================================================================
# Protected Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get current user information (ASYNC).

    Returns detailed info for the authenticated user.
    """
    result = await db.execute(
        select(User).where(User.user_id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only) (ASYNC).

    Returns paginated list of all users.
    """
    query = select(User).order_by(User.user_id).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    logger.info(f"Admin {admin['username']} requested user list")
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Get user by ID (admin only) (ASYNC).
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Activate a user account (admin only) (ASYNC).
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    async with db.begin():
        user.is_active = True

    logger.info(f"User {user.username} activated by admin {admin['username']}")

    return {"message": f"User {user.username} activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Deactivate a user account (admin only) (ASYNC).
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent deactivating yourself
    if user.user_id == admin["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    async with db.begin():
        user.is_active = False

    logger.info(f"User {user.username} deactivated by admin {admin['username']}")

    return {"message": f"User {user.username} deactivated successfully"}


# ============================================================================
# User Self-Service Endpoints
# ============================================================================

@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: dict = Depends(get_current_active_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Change own password (ASYNC).

    User must provide current password and new password.
    """
    client_ip = get_client_ip(request)

    # Verify passwords match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.user_id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(password_data.current_password, user.password_hash):
        logger.warning(f"Failed password change attempt for user: {user.username} - wrong current password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Update password
    user.password_hash = hash_password(password_data.new_password)
    user.last_password_change = datetime.utcnow()
    user.must_change_password = False  # Clear the flag after password change
    await db.commit()

    # Audit log
    log_password_change(user.username, client_ip, user.user_id)
    logger.info(f"Password changed successfully for user: {user.username}")

    return {"message": "Password changed successfully"}


# ============================================================================
# Admin User Management Endpoints
# ============================================================================

@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: AdminUserCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Create a new user (admin only) (ASYNC).

    Admin can set all user profile fields including team, language, etc.
    """
    client_ip = get_client_ip(request)

    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists (if provided)
    if user_data.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_email = result.scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Validate role
    if user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {VALID_ROLES}"
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create new user with all profile fields
    new_user = User(
        username=user_data.username,
        password_hash=password_hash,
        email=user_data.email,
        full_name=user_data.full_name,
        team=user_data.team,
        language=user_data.language,
        department=user_data.department,
        role=user_data.role,
        is_active=True,
        created_at=datetime.utcnow(),
        created_by=admin["user_id"],
        must_change_password=user_data.must_change_password
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Audit log
    log_user_created(new_user.username, admin["username"], client_ip)
    logger.info(f"New user created: {new_user.username} (ID: {new_user.user_id}) by admin: {admin['username']}")

    return new_user


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Update user profile (admin only) (ASYNC).

    Admin can update email, full_name, team, language, department, role, is_active.
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness if being updated
    if user_data.email and user_data.email != user.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Validate role if being updated
    if user_data.role:
        valid_roles = ["user", "admin"]
        if user_data.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {VALID_ROLES}"
            )

    # Prevent admin from demoting themselves
    if user.user_id == admin["user_id"] and user_data.role == "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote your own account"
        )

    # Update only provided fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user.username} updated by admin {admin['username']}: {update_data}")

    return user


@router.put("/admin/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    password_data: AdminPasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Reset user password (admin only) (ASYNC).

    Admin can reset any user's password. By default, forces password change on next login.
    """
    client_ip = get_client_ip(request)

    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.password_hash = hash_password(password_data.new_password)
    user.last_password_change = datetime.utcnow()
    user.must_change_password = password_data.must_change_password

    await db.commit()

    # Audit log
    log_password_change(user.username, client_ip, user.user_id, changed_by=admin["username"])
    logger.info(f"Password reset for user {user.username} by admin {admin['username']}")

    return {"message": f"Password reset successfully for user {user.username}"}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: dict = Depends(require_admin_async)
):
    """
    Deactivate user (soft delete) (admin only) (ASYNC).

    This is a soft delete - sets is_active=False instead of deleting the record.
    Use PUT /users/{user_id}/activate to reactivate.
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent deleting yourself
    if user.user_id == admin["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Soft delete
    user.is_active = False
    await db.commit()

    logger.info(f"User {user.username} deactivated (soft delete) by admin {admin['username']}")

    return {"message": f"User {user.username} deactivated successfully"}
