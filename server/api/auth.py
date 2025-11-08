"""
Authentication API Endpoints

User registration, login, and authentication management.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from server.api.schemas import UserLogin, UserRegister, Token, UserResponse
from server.database.models import User
from server.utils.dependencies import get_db, get_current_active_user, require_admin
from server.utils.auth import hash_password, verify_password, create_access_token


# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Public Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.

    Returns JWT access token on successful authentication.
    """
    # Find user by username
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user:
        logger.warning(f"Login attempt with non-existent username: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt by inactive user: {credentials.username}")
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

    logger.info(f"User logged in successfully: {user.username} (ID: {user.user_id})")

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)  # Only admins can register new users
):
    """
    User registration endpoint (admin only).

    Creates a new user account.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Create new user
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
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.username} (ID: {new_user.user_id}) by admin: {admin['username']}")

    return new_user


# ============================================================================
# Protected Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.

    Returns detailed info for the authenticated user.
    """
    user = db.query(User).filter(User.user_id == current_user["user_id"]).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only).

    Returns paginated list of all users.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"Admin {admin['username']} requested user list")
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    Get user by ID (admin only).
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    Activate a user account (admin only).
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    db.commit()

    logger.info(f"User {user.username} activated by admin {admin['username']}")

    return {"message": f"User {user.username} activated successfully"}


@router.put("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    Deactivate a user account (admin only).
    """
    user = db.query(User).filter(User.user_id == user_id).first()

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

    user.is_active = False
    db.commit()

    logger.info(f"User {user.username} deactivated by admin {admin['username']}")

    return {"message": f"User {user.username} deactivated successfully"}
