"""
Remote Logging API - Central Collection Endpoint
Receives logs from user installations for centralized monitoring

Priority 12.5 - Central Server Communication (Telemetry)

Thin route handlers — business logic in server/services/remote_logging_service.py.
"""

from fastapi import APIRouter, HTTPException, Header, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import hashlib
from loguru import logger

from server.utils.dependencies import get_async_db
from server.database.models import Installation
from server.services.remote_logging_service import RemoteLoggingService

router = APIRouter(prefix="/api/v1/remote-logs", tags=["Remote Logging"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RemoteLogEntry(BaseModel):
    """Single log entry from remote installation"""
    timestamp: str
    level: str  # INFO, SUCCESS, WARNING, ERROR, CRITICAL
    message: str
    data: Optional[dict] = None
    source: str  # "locanext-app", "admin-dashboard", etc.
    component: Optional[str] = None
    user_agent: Optional[str] = None
    installation_id: str
    version: Optional[str] = None


class RemoteLogBatch(BaseModel):
    """Batch of log entries from remote installation"""
    installation_id: str
    installation_name: Optional[str] = None
    logs: List[RemoteLogEntry]
    metadata: Optional[dict] = None


class InstallationRegistration(BaseModel):
    """Register new installation for remote logging"""
    installation_name: str
    version: str
    owner_email: Optional[str] = None
    metadata: Optional[dict] = None


class SessionStart(BaseModel):
    """Start a new session"""
    installation_id: str
    version: str
    ip_address: Optional[str] = None


class SessionEnd(BaseModel):
    """End a session"""
    session_id: str
    end_reason: str = "user_closed"  # user_closed, timeout, error


class SessionHeartbeat(BaseModel):
    """Session heartbeat"""
    session_id: str


# ============================================================================
# Helper Functions
# ============================================================================

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key_db(api_key: str, db: AsyncSession) -> Optional[Installation]:
    """
    Verify API key against database.
    Returns Installation if valid, None otherwise.
    """
    key_hash = hash_api_key(api_key)
    result = await db.execute(
        select(Installation).where(
            and_(
                Installation.api_key_hash == key_hash,
                Installation.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


async def get_verified_installation(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_async_db)
) -> Installation:
    """
    Dependency that verifies API key and returns Installation.
    Raises 401 if invalid.
    """
    if not x_api_key or len(x_api_key) < 32:
        logger.warning("Invalid API key attempt", {"key_length": len(x_api_key) if x_api_key else 0})
        raise HTTPException(status_code=401, detail="Invalid API key")

    installation = await verify_api_key_db(x_api_key, db)
    if not installation:
        logger.warning("API key not found in database")
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Update last_seen
    installation.last_seen = datetime.utcnow()
    await db.commit()

    return installation


# ============================================================================
# Registration Endpoint
# ============================================================================

@router.post("/register")
async def register_installation(
    registration: InstallationRegistration,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register new installation and generate API key.
    Returns API key for subsequent log submissions.
    """
    import secrets

    # Generate API key (64 characters)
    api_key = secrets.token_urlsafe(48)

    svc = RemoteLoggingService(db)
    result = await svc.register_installation(
        name=registration.installation_name,
        version=registration.version,
        api_key_hash=hash_api_key(api_key),
        owner_email=registration.owner_email,
        metadata=registration.metadata,
    )

    return {
        "success": True,
        "installation_id": result["installation_id"],
        "api_key": api_key,
        "message": "Installation registered successfully. Store this API key securely."
    }


# ============================================================================
# Log Submission Endpoint
# ============================================================================

@router.post("/submit")
async def submit_logs(
    batch: RemoteLogBatch,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Submit batch of logs from remote installation.
    Accepts up to 1000 log entries per request.
    """
    if len(batch.logs) > 1000:
        logger.warning("Log batch too large", {
            "installation_id": batch.installation_id,
            "log_count": len(batch.logs)
        })
        raise HTTPException(
            status_code=413,
            detail="Batch too large. Maximum 1000 logs per request."
        )

    svc = RemoteLoggingService(db)
    # Convert Pydantic models to dicts for the service
    log_dicts = [entry.model_dump() for entry in batch.logs]
    result = await svc.submit_logs(
        installation=installation,
        batch_logs=log_dicts,
        batch_installation_id=batch.installation_id,
        batch_installation_name=batch.installation_name,
    )

    return {
        "success": True,
        "logs_received": result["logs_received"],
        "errors_detected": result["errors_detected"],
        "criticals_detected": result["criticals_detected"],
        "message": "Logs received successfully"
    }


# ============================================================================
# Session Tracking Endpoints
# ============================================================================

@router.post("/sessions/start")
async def start_session(
    session_data: SessionStart,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """Start a new session for an installation."""
    svc = RemoteLoggingService(db)
    result = await svc.start_session(
        installation=installation,
        version=session_data.version,
        ip_address=session_data.ip_address,
    )

    return {
        "success": True,
        "session_id": result["session_id"],
        "started_at": result["started_at"]
    }


@router.post("/sessions/heartbeat")
async def session_heartbeat(
    heartbeat: SessionHeartbeat,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """Update session heartbeat."""
    svc = RemoteLoggingService(db)
    result = await svc.heartbeat(
        session_id=heartbeat.session_id,
        installation_id=installation.installation_id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"success": True, "last_heartbeat": result["last_heartbeat"]}


@router.post("/sessions/end")
async def end_session(
    end_data: SessionEnd,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """End a session."""
    svc = RemoteLoggingService(db)
    result = await svc.end_session(
        session_id=end_data.session_id,
        installation_id=installation.installation_id,
        end_reason=end_data.end_reason,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "session_id": result["session_id"],
        "duration_seconds": result["duration_seconds"]
    }


# ============================================================================
# Status & Query Endpoints
# ============================================================================

@router.get("/status/{installation_id}")
async def get_installation_status(
    installation_id: str,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """Get status and recent activity for installation."""
    # IDOR fix: installation can only query its own status
    if installation.installation_id != installation_id:
        raise HTTPException(status_code=403, detail="Cannot access other installation's status")

    svc = RemoteLoggingService(db)
    result = await svc.get_installation_status(installation_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Installation not found")

    return result


@router.get("/installations")
async def list_installations(
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """List installations visible to the requesting installation (own data only)."""
    # Only return the requesting installation's own data (not all installations)
    return {
        "count": 1,
        "installations": [
            {
                "installation_id": installation.installation_id,
                "installation_name": installation.installation_name,
                "version": installation.last_version or installation.version,
                "is_active": installation.is_active,
                "last_seen": installation.last_seen.isoformat() if installation.last_seen else None,
                "created_at": installation.created_at.isoformat() if installation.created_at else None
            }
        ]
    }


@router.get("/health")
async def remote_logging_health(db: AsyncSession = Depends(get_async_db)):
    """Health check for remote logging service."""
    svc = RemoteLoggingService(db)
    return await svc.get_health()


# ============================================================================
# Frontend Logging (Local - for browser console visibility)
# ============================================================================

@router.post("/frontend")
async def log_frontend(
    request: Request,
):
    """
    Receive logs from frontend browser and write to backend log file.
    No authentication required — this is a local-only endpoint for dev visibility.
    """
    try:
        body = await request.json()
        level = body.get('level', 'INFO')
        message = body.get('message', '')
        data = body.get('data', {})
        source = body.get('source', 'frontend')

        log_message = f"[FRONTEND] {message}"

        # Log with full data visibility
        if level == 'ERROR':
            logger.error(f"{log_message} | DATA: {data}")
        elif level == 'WARNING':
            logger.warning(f"{log_message} | DATA: {data}")
        elif level == 'SUCCESS':
            logger.success(f"{log_message} | DATA: {data}")
        else:
            logger.info(f"{log_message} | DATA: {data}")

        return {"status": "logged"}
    except Exception as e:
        logger.error(f"Failed to log frontend message: {str(e)}")
        return {"status": "error", "detail": str(e)}
