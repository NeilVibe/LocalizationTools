"""
EXPLORER-009: User Capabilities Management (Admin only)

Endpoints for managing user capability grants.
Capabilities control access to privileged operations:
- delete_platform: Can permanently delete platforms
- delete_project: Can permanently delete projects
- cross_project_move: Can move resources between projects
- empty_trash: Can permanently empty entire trash

P10-REPO: Migrated to Repository Pattern (2026-01-13)
- All endpoints use CapabilityRepository
- Note: Admin-only, primarily online functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from server.utils.dependencies import require_admin_async
from server.repositories import CapabilityRepository, get_capability_repository
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
    repo: CapabilityRepository = Depends(get_capability_repository),
    current_user: dict = Depends(require_admin_async)
):
    """
    Grant a capability to a user.
    Admin only.

    P10-REPO: Uses CapabilityRepository for database operations.
    """
    # Validate capability name
    if grant.capability_name not in CAPABILITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability. Available: {list(CAPABILITIES.keys())}"
        )

    # Check if user exists
    user = await repo.get_user(grant.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already granted
    existing = await repo.get_user_capability(grant.user_id, grant.capability_name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User already has '{grant.capability_name}' capability"
        )

    # Calculate expiration
    expires_at = None
    if grant.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=grant.expires_in_days)

    # Create grant via repository
    capability = await repo.grant_capability(
        user_id=grant.user_id,
        capability_name=grant.capability_name,
        granted_by=current_user["user_id"],
        expires_at=expires_at
    )

    logger.success(f"[CAPS] Capability granted: {grant.capability_name} to user {grant.user_id} by admin {current_user['user_id']}")

    return {
        "success": True,
        "message": f"Granted '{grant.capability_name}' to user {user['username']}",
        "id": capability["id"],
        "expires_at": expires_at
    }


@router.delete("/{capability_id}")
async def revoke_capability(
    capability_id: int,
    repo: CapabilityRepository = Depends(get_capability_repository),
    current_user: dict = Depends(require_admin_async)
):
    """
    Revoke a capability grant by ID.
    Admin only.

    P10-REPO: Uses CapabilityRepository for database operations.
    """
    # Get capability info before deleting
    capability = await repo.get_capability(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability grant not found")

    user_id = capability["user_id"]
    capability_name = capability["capability_name"]

    # Revoke via repository
    await repo.revoke_capability(capability_id)

    logger.success(f"[CAPS] Capability revoked: {capability_name} from user {user_id} by admin {current_user['user_id']}")

    return {
        "success": True,
        "message": f"Revoked '{capability_name}' from user {user_id}"
    }


@router.get("")
async def list_all_capabilities(
    repo: CapabilityRepository = Depends(get_capability_repository),
    current_user: dict = Depends(require_admin_async)
):
    """
    List all capability grants.
    Admin only.

    P10-REPO: Uses CapabilityRepository for database operations.
    """
    caps = await repo.list_all_capabilities()

    now = datetime.utcnow()
    capabilities = []
    for cap in caps:
        expires_at = cap.get("expires_at")
        is_expired = expires_at is not None and expires_at < now
        capabilities.append({
            "id": cap["id"],
            "user_id": cap["user_id"],
            "username": cap["username"],
            "capability_name": cap["capability_name"],
            "capability_description": CAPABILITIES.get(cap["capability_name"], "Unknown"),
            "granted_by": cap["granted_by"],
            "granted_at": cap["granted_at"],
            "expires_at": expires_at,
            "is_expired": is_expired
        })

    return {
        "capabilities": capabilities,
        "count": len(capabilities)
    }


@router.get("/user/{user_id}")
async def list_user_capabilities(
    user_id: int,
    repo: CapabilityRepository = Depends(get_capability_repository),
    current_user: dict = Depends(require_admin_async)
):
    """
    List capabilities for a specific user.
    Admin only.

    P10-REPO: Uses CapabilityRepository for database operations.
    """
    # Check if user exists
    user = await repo.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    caps = await repo.list_user_capabilities(user_id)

    now = datetime.utcnow()
    capabilities = []
    for cap in caps:
        expires_at = cap.get("expires_at")
        is_expired = expires_at is not None and expires_at < now
        capabilities.append({
            "id": cap["id"],
            "capability_name": cap["capability_name"],
            "capability_description": CAPABILITIES.get(cap["capability_name"], "Unknown"),
            "granted_by": cap["granted_by"],
            "granted_at": cap["granted_at"],
            "expires_at": expires_at,
            "is_expired": is_expired
        })

    return {
        "user_id": user_id,
        "username": user["username"],
        "capabilities": capabilities,
        "count": len(capabilities)
    }
