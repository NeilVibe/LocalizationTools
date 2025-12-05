"""
Remote Logging API - Central Collection Endpoint
Receives logs from user installations for centralized monitoring

Priority 12.5 - Central Server Communication (Telemetry)
"""

from fastapi import APIRouter, HTTPException, Header, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets
import hashlib
from loguru import logger

from server.utils.dependencies import get_async_db
from server.database.models import Installation, RemoteLog, RemoteSession, TelemetrySummary

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
    logger.info("New installation registration request", {
        "installation_name": registration.installation_name,
        "version": registration.version,
        "owner_email": registration.owner_email
    })

    # Generate unique API key (64 characters) and installation ID
    api_key = secrets.token_urlsafe(48)
    installation_id = secrets.token_urlsafe(16)

    # Create Installation record
    installation = Installation(
        installation_id=installation_id,
        api_key_hash=hash_api_key(api_key),
        installation_name=registration.installation_name,
        version=registration.version,
        owner_email=registration.owner_email,
        last_version=registration.version,
        extra_data=registration.metadata,
        is_active=True
    )

    db.add(installation)
    await db.commit()

    logger.success("Installation registered successfully", {
        "installation_id": installation_id,
        "installation_name": registration.installation_name
    })

    return {
        "success": True,
        "installation_id": installation_id,
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
    logger.info("Remote log batch received", {
        "installation_id": batch.installation_id,
        "log_count": len(batch.logs),
        "installation_name": batch.installation_name
    })

    if len(batch.logs) > 1000:
        logger.warning("Log batch too large", {
            "installation_id": batch.installation_id,
            "log_count": len(batch.logs)
        })
        raise HTTPException(
            status_code=413,
            detail="Batch too large. Maximum 1000 logs per request."
        )

    # Counters for telemetry summary
    level_counts = {
        "INFO": 0,
        "SUCCESS": 0,
        "WARNING": 0,
        "ERROR": 0,
        "CRITICAL": 0
    }

    # Process and store each log entry
    for log_entry in batch.logs:
        # Count by level
        if log_entry.level in level_counts:
            level_counts[log_entry.level] += 1

        # Parse timestamp
        try:
            log_timestamp = datetime.fromisoformat(log_entry.timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            log_timestamp = datetime.utcnow()

        # Create RemoteLog record
        remote_log = RemoteLog(
            installation_id=installation.installation_id,
            timestamp=log_timestamp,
            level=log_entry.level,
            message=log_entry.message,
            data=log_entry.data,
            source=log_entry.source,
            component=log_entry.component
        )
        db.add(remote_log)

        # Log errors and criticals to server logs for alerting
        if log_entry.level in ["ERROR", "CRITICAL"]:
            logger.error(f"Remote [{batch.installation_id}] {log_entry.message}", {
                "installation_id": batch.installation_id,
                "source": log_entry.source,
                "component": log_entry.component,
                "data": log_entry.data,
                "timestamp": log_entry.timestamp
            })

    await db.commit()

    # Update or create today's telemetry summary
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(TelemetrySummary).where(
            and_(
                TelemetrySummary.installation_id == installation.installation_id,
                TelemetrySummary.date == today
            )
        )
    )
    summary = result.scalar_one_or_none()

    if summary:
        summary.info_count += level_counts["INFO"]
        summary.success_count += level_counts["SUCCESS"]
        summary.warning_count += level_counts["WARNING"]
        summary.error_count += level_counts["ERROR"]
        summary.critical_count += level_counts["CRITICAL"]
    else:
        summary = TelemetrySummary(
            date=today,
            installation_id=installation.installation_id,
            info_count=level_counts["INFO"],
            success_count=level_counts["SUCCESS"],
            warning_count=level_counts["WARNING"],
            error_count=level_counts["ERROR"],
            critical_count=level_counts["CRITICAL"]
        )
        db.add(summary)

    await db.commit()

    # Log summary
    logger.success("Remote log batch processed", {
        "installation_id": batch.installation_id,
        "logs_processed": len(batch.logs),
        "errors": level_counts["ERROR"],
        "criticals": level_counts["CRITICAL"]
    })

    # Alert on criticals
    if level_counts["CRITICAL"] > 0:
        logger.critical(f"Critical errors detected from remote installation", {
            "installation_id": batch.installation_id,
            "installation_name": batch.installation_name,
            "critical_count": level_counts["CRITICAL"]
        })

    return {
        "success": True,
        "logs_received": len(batch.logs),
        "errors_detected": level_counts["ERROR"],
        "criticals_detected": level_counts["CRITICAL"],
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
    session = RemoteSession(
        installation_id=installation.installation_id,
        app_version=session_data.version,
        ip_address=session_data.ip_address,
        is_active=True
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Remote session started", {
        "session_id": session.session_id,
        "installation_id": installation.installation_id,
        "version": session_data.version
    })

    return {
        "success": True,
        "session_id": session.session_id,
        "started_at": session.started_at.isoformat()
    }


@router.post("/sessions/heartbeat")
async def session_heartbeat(
    heartbeat: SessionHeartbeat,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """Update session heartbeat."""
    result = await db.execute(
        select(RemoteSession).where(
            and_(
                RemoteSession.session_id == heartbeat.session_id,
                RemoteSession.installation_id == installation.installation_id,
                RemoteSession.is_active == True
            )
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.last_heartbeat = datetime.utcnow()
    await db.commit()

    return {"success": True, "last_heartbeat": session.last_heartbeat.isoformat()}


@router.post("/sessions/end")
async def end_session(
    end_data: SessionEnd,
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """End a session."""
    result = await db.execute(
        select(RemoteSession).where(
            and_(
                RemoteSession.session_id == end_data.session_id,
                RemoteSession.installation_id == installation.installation_id
            )
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.utcnow()
    session.is_active = False
    session.end_reason = end_data.end_reason
    session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

    await db.commit()

    # Update today's telemetry summary
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(TelemetrySummary).where(
            and_(
                TelemetrySummary.installation_id == installation.installation_id,
                TelemetrySummary.date == today
            )
        )
    )
    summary = result.scalar_one_or_none()

    if summary:
        summary.total_sessions += 1
        summary.total_duration_seconds += session.duration_seconds
        summary.avg_session_seconds = summary.total_duration_seconds / summary.total_sessions
    else:
        summary = TelemetrySummary(
            date=today,
            installation_id=installation.installation_id,
            total_sessions=1,
            total_duration_seconds=session.duration_seconds,
            avg_session_seconds=float(session.duration_seconds)
        )
        db.add(summary)

    await db.commit()

    logger.info("Remote session ended", {
        "session_id": session.session_id,
        "duration_seconds": session.duration_seconds,
        "end_reason": end_data.end_reason
    })

    return {
        "success": True,
        "session_id": session.session_id,
        "duration_seconds": session.duration_seconds
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
    logger.info("Installation status requested", {"installation_id": installation_id})

    # Get installation
    result = await db.execute(
        select(Installation).where(Installation.installation_id == installation_id)
    )
    target_installation = result.scalar_one_or_none()

    if not target_installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    # Get log counts for last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

    log_counts = await db.execute(
        select(
            func.count().label('total'),
            func.sum(func.cast(RemoteLog.level == 'ERROR', Integer)).label('errors'),
            func.sum(func.cast(RemoteLog.level == 'CRITICAL', Integer)).label('criticals')
        ).where(
            and_(
                RemoteLog.installation_id == installation_id,
                RemoteLog.received_at >= twenty_four_hours_ago
            )
        )
    )
    counts = log_counts.first()

    return {
        "installation_id": installation_id,
        "installation_name": target_installation.installation_name,
        "status": "active" if target_installation.is_active else "inactive",
        "last_seen": target_installation.last_seen.isoformat() if target_installation.last_seen else None,
        "version": target_installation.last_version or target_installation.version,
        "logs_24h": counts.total or 0,
        "errors_24h": counts.errors or 0,
        "criticals_24h": counts.criticals or 0
    }


@router.get("/installations")
async def list_installations(
    installation: Installation = Depends(get_verified_installation),
    db: AsyncSession = Depends(get_async_db)
):
    """List all registered installations (admin only)."""
    result = await db.execute(
        select(Installation).order_by(Installation.last_seen.desc())
    )
    installations = result.scalars().all()

    return {
        "count": len(installations),
        "installations": [
            {
                "installation_id": inst.installation_id,
                "installation_name": inst.installation_name,
                "version": inst.last_version or inst.version,
                "is_active": inst.is_active,
                "last_seen": inst.last_seen.isoformat() if inst.last_seen else None,
                "created_at": inst.created_at.isoformat() if inst.created_at else None
            }
            for inst in installations
        ]
    }


@router.get("/health")
async def remote_logging_health(db: AsyncSession = Depends(get_async_db)):
    """Health check for remote logging service."""
    # Count active installations
    result = await db.execute(
        select(func.count()).select_from(Installation).where(Installation.is_active == True)
    )
    active_count = result.scalar() or 0

    return {
        "status": "healthy",
        "service": "remote-logging",
        "accepting_submissions": True,
        "registered_installations": active_count
    }


# ============================================================================
# Frontend Logging (Local - for browser console visibility)
# ============================================================================

@router.post("/frontend")
async def log_frontend(request: Request):
    """
    Receive logs from frontend browser and write to backend log file.
    This gives us visibility into browser console.
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
