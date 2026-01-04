"""
Authentication Utilities

Password hashing, JWT token generation, and user verification.
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server import config


# ============================================================================
# Password Hashing
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        Hashed password string.

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
    """
    salt = bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to check against.

    Returns:
        True if password matches, False otherwise.

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================================================
# JWT Token Management
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode in the token (e.g., {"user_id": 1, "username": "john"}).
        expires_delta: Optional custom expiration time. Defaults to config.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT token string.

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "john"})
        >>> decoded = verify_token(token)
        >>> decoded["username"]
        'john'
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        config.SECRET_KEY,
        algorithm=config.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify.

    Returns:
        Decoded token data dict if valid, None if invalid or expired.
        For OFFLINE_MODE tokens, returns virtual admin user data.

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> data = verify_token(token)
        >>> data["user_id"]
        1
    """
    # P9: Handle OFFLINE_MODE tokens from launcher's "Start Offline" button
    # These tokens allow working without server credentials
    if token and token.startswith("OFFLINE_MODE_"):
        logger.debug("OFFLINE_MODE token detected - returning virtual admin user")
        return {
            "user_id": "OFFLINE",
            "username": "Offline User",
            "role": "admin",
            "offline_mode": True
        }

    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_current_user(token: str, db) -> Optional[dict]:
    """
    Get current user from JWT token.

    Args:
        token: JWT token string.
        db: Database session.

    Returns:
        User data dict if valid, None otherwise.

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "john"})
        >>> user = get_current_user(token, db)
        >>> user["username"]
        'john'
    """
    from server.database.models import User

    # Verify token
    payload = verify_token(token)
    if not payload:
        return None

    # Get user ID from token
    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("No user_id in token")
        return None

    # P9: Handle OFFLINE mode - look up real OFFLINE user from database
    # This ensures we use the real integer user_id that works with foreign keys
    if payload.get("offline_mode") or user_id == "OFFLINE":
        offline_user = db.query(User).filter(User.username == "OFFLINE").first()
        if offline_user:
            return {
                "user_id": offline_user.user_id,
                "username": offline_user.username,
                "email": offline_user.email,
                "full_name": offline_user.full_name,
                "department": offline_user.department,
                "role": offline_user.role,
                "is_active": offline_user.is_active,
                "offline_mode": True
            }
        else:
            logger.warning("OFFLINE user not found in database - run db_setup to create it")
            return None

    # Fetch user from database
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return None

    if not user.is_active:
        logger.warning(f"User {user_id} is not active")
        return None

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department,
        "role": user.role,
        "is_active": user.is_active,
    }


async def get_current_user_async(token: str, db: AsyncSession) -> Optional[dict]:
    """
    Get current user from JWT token (ASYNC version).

    Args:
        token: JWT token string.
        db: Async database session.

    Returns:
        User data dict if valid, None otherwise.

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "john"})
        >>> user = await get_current_user_async(token, db)
        >>> user["username"]
        'john'
    """
    from server.database.models import User

    # Verify token
    payload = verify_token(token)
    if not payload:
        return None

    # Get user ID from token
    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("No user_id in token")
        return None

    # P9: Handle OFFLINE mode - look up real OFFLINE user from database
    # This ensures we use the real integer user_id that works with foreign keys
    if payload.get("offline_mode") or user_id == "OFFLINE":
        result = await db.execute(select(User).where(User.username == "OFFLINE"))
        offline_user = result.scalar_one_or_none()
        if offline_user:
            return {
                "user_id": offline_user.user_id,
                "username": offline_user.username,
                "email": offline_user.email,
                "full_name": offline_user.full_name,
                "department": offline_user.department,
                "role": offline_user.role,
                "is_active": offline_user.is_active,
                "offline_mode": True
            }
        else:
            logger.warning("OFFLINE user not found in database - run db_setup to create it")
            return None

    # Fetch user from database (async)
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in database")
        return None

    if not user.is_active:
        logger.warning(f"User {user_id} is not active")
        return None

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department,
        "role": user.role,
        "is_active": user.is_active,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def generate_api_key() -> str:
    """
    Generate a random API key for server-client communication.

    Returns:
        Random API key string.
    """
    import secrets
    return secrets.token_urlsafe(32)


def is_admin(user: dict) -> bool:
    """
    Check if user has admin role.

    Args:
        user: User data dictionary.

    Returns:
        True if user is admin or superadmin.
    """
    return user.get("role") in ["admin", "superadmin"]
