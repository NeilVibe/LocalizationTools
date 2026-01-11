"""
EXPLORER-009: User Capabilities Management (Admin only)

Endpoints for managing user capability grants.
Capabilities control access to privileged operations:
- delete_platform: Can permanently delete platforms
- delete_project: Can permanently delete projects
- cross_project_move: Can move resources between projects
- empty_trash: Can permanently empty entire trash
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from server.utils.dependencies import get_async_db, require_admin_async
from server.database.models import UserCapability, User
from ..permissions import CAPABILITIES

from loguru import logger

router = APIRouter(prefix="/admin/capabilities", tags=["admin-capabilities"])


# ============== Schemas ==============

class CapabilityGrant(BaseModel):
    """Request body for granting a capability."""
    user_id: int
    capability_name: str
    expires_in_days: Optional[int] = None  # None = permanent


class CapabilityInfo(BaseModel):
    """Response model for a capability grant."""
    id: int
    user_id: int
    username: str
    capability_name: str
    capability_description: str
    granted_by: Optional[int]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_expired: bool


class CapabilityListResponse(BaseModel):
    """Response model for listing capabilities."""
    capabilities: List[CapabilityInfo]
    count: int


class AvailableCapability(BaseModel):
    """Response model for available capability types."""
    name: str
    description: str


# ============== Endpoints ==============

@router.get("/available")
async def list_available_capabilities(
    current_user: dict = Depends(require_admin_async)
):
    """
    List all available capability types.
    Admin only.
    """
    return {
        "capabilities": [
            {"name": name, "description": desc}
            for name, desc in CAPABILITIES.items()
        ]
    }


@router.post("")
async def grant_capability(
    grant: CapabilityGrant,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """
    Grant a capability to a user.
    Admin only.
    """
    # Validate capability name
    if grant.capability_name not in CAPABILITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability. Available: {list(CAPABILITIES.keys())}"
        )

    # Check if user exists
    result = await db.execute(
        select(User).where(User.user_id == grant.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already granted
    result = await db.execute(
        select(UserCapability).where(
            UserCapability.user_id == grant.user_id,
            UserCapability.capability_name == grant.capability_name
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User already has '{grant.capability_name}' capability"
        )

    # Calculate expiration
    expires_at = None
    if grant.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=grant.expires_in_days)

    # Create grant
    capability = UserCapability(
        user_id=grant.user_id,
        capability_name=grant.capability_name,
        granted_by=current_user["user_id"],
        expires_at=expires_at
    )
    db.add(capability)
    await db.commit()
    await db.refresh(capability)

    logger.success(f"[CAPS] Capability granted: {grant.capability_name} to user {grant.user_id} by admin {current_user['user_id']}")

    return {
        "success": True,
        "message": f"Granted '{grant.capability_name}' to user {user.username}",
        "id": capability.id,
        "expires_at": expires_at
    }


@router.delete("/{capability_id}")
async def revoke_capability(
    capability_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """
    Revoke a capability grant by ID.
    Admin only.
    """
    result = await db.execute(
        select(UserCapability).where(UserCapability.id == capability_id)
    )
    capability = result.scalar_one_or_none()

    if not capability:
        raise HTTPException(status_code=404, detail="Capability grant not found")

    user_id = capability.user_id
    capability_name = capability.capability_name

    await db.delete(capability)
    await db.commit()

    logger.success(f"[CAPS] Capability revoked: {capability_name} from user {user_id} by admin {current_user['user_id']}")

    return {
        "success": True,
        "message": f"Revoked '{capability_name}' from user {user_id}"
    }


@router.get("")
async def list_all_capabilities(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """
    List all capability grants.
    Admin only.
    """
    result = await db.execute(
        select(UserCapability, User.username)
        .join(User, UserCapability.user_id == User.user_id)
        .order_by(UserCapability.user_id, UserCapability.capability_name)
    )
    rows = result.all()

    now = datetime.utcnow()
    capabilities = []
    for cap, username in rows:
        is_expired = cap.expires_at is not None and cap.expires_at < now
        capabilities.append({
            "id": cap.id,
            "user_id": cap.user_id,
            "username": username,
            "capability_name": cap.capability_name,
            "capability_description": CAPABILITIES.get(cap.capability_name, "Unknown"),
            "granted_by": cap.granted_by,
            "granted_at": cap.granted_at,
            "expires_at": cap.expires_at,
            "is_expired": is_expired
        })

    return {
        "capabilities": capabilities,
        "count": len(capabilities)
    }


@router.get("/user/{user_id}")
async def list_user_capabilities(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(require_admin_async)
):
    """
    List capabilities for a specific user.
    Admin only.
    """
    # Check if user exists
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserCapability).where(UserCapability.user_id == user_id)
    )
    caps = result.scalars().all()

    now = datetime.utcnow()
    capabilities = []
    for cap in caps:
        is_expired = cap.expires_at is not None and cap.expires_at < now
        capabilities.append({
            "id": cap.id,
            "capability_name": cap.capability_name,
            "capability_description": CAPABILITIES.get(cap.capability_name, "Unknown"),
            "granted_by": cap.granted_by,
            "granted_at": cap.granted_at,
            "expires_at": cap.expires_at,
            "is_expired": is_expired
        })

    return {
        "user_id": user_id,
        "username": user.username,
        "capabilities": capabilities,
        "count": len(capabilities)
    }
