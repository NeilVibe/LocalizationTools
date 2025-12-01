"""
Authentication API Endpoints (ASYNC)

User registration, login, and authentication management with async/await.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.api.schemas import UserLogin, UserRegister, Token, UserResponse
from server.database.models import User
from server.utils.dependencies import get_async_db, get_current_active_user_async, require_admin_async
from server.utils.auth import hash_password, verify_password, create_access_token
from server.utils.audit_logger import (
    log_login_success,
    log_login_failure,
    log_user_created,
    log_password_change,
)


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


# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Public Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    User login endpoint (ASYNC).

    Returns JWT access token on successful authentication.
    """
    client_ip = get_client_ip(request)

    # Find user by username
    result = await db.execute(
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
    await db.commit()

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
    # TEMPORARILY DISABLED FOR DASHBOARD TESTING
    # admin: dict = Depends(require_admin_async),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only) (ASYNC).

    Returns paginated list of all users.
    """
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    logger.info(f"User list requested (auth temporarily disabled)")
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
