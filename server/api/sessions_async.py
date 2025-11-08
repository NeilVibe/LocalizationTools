"""
Session Management API Endpoints (ASYNC)

User session tracking and management with async/await.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from server.api.schemas import SessionCreate, SessionResponse
from server.database.models import Session
from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.utils.websocket import emit_session_update


# Create router
router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============================================================================
# Session Endpoints
# ============================================================================

@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Start a new user session (ASYNC).

    Creates a new session record when user opens the application.
    """
    try:
        async with db.begin():
            # Create new session
            new_session = Session(
                user_id=current_user["user_id"],
                machine_id=session_data.machine_id,
                ip_address=session_data.ip_address,
                app_version=session_data.app_version,
                session_start=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                is_active=True
            )

            db.add(new_session)
            await db.flush()  # Flush to get the session_id
            await db.refresh(new_session)

        # Emit WebSocket event for session start
        await emit_session_update({
            'session_id': new_session.session_id,
            'user_id': current_user["user_id"],
            'username': current_user["username"],
            'machine_id': session_data.machine_id,
            'app_version': session_data.app_version,
            'session_start': new_session.session_start.isoformat()
        }, 'start')

        logger.info(
            f"New session started: {new_session.session_id} for user {current_user['username']} "
            f"on machine {session_data.machine_id}"
        )

        return new_session

    except Exception as e:
        logger.exception(f"Error starting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )


@router.put("/{session_id}/heartbeat")
async def session_heartbeat(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Update session last activity timestamp (heartbeat) (ASYNC).

    Clients should call this periodically to keep session active.
    """
    # Query session
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify session belongs to current user
    if session.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this session"
        )

    # Update last activity
    async with db.begin():
        session.last_activity = datetime.utcnow()

    return {"message": "Session updated", "last_activity": session.last_activity}


@router.put("/{session_id}/end")
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    End a user session (ASYNC).

    Marks session as inactive when user closes the application.
    """
    # Query session
    result = await db.execute(
        select(Session).where(Session.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify session belongs to current user
    if session.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this session"
        )

    # Mark session as inactive
    async with db.begin():
        session.is_active = False
        session.last_activity = datetime.utcnow()

    # Emit WebSocket event for session end
    await emit_session_update({
        'session_id': session_id,
        'user_id': current_user["user_id"],
        'username': current_user["username"],
        'is_active': False,
        'last_activity': session.last_activity.isoformat()
    }, 'end')

    logger.info(f"Session ended: {session_id} for user {current_user['username']}")

    return {"message": "Session ended successfully"}


@router.get("/active", response_model=list[SessionResponse])
async def get_active_sessions(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get all active sessions (ASYNC).

    Users see their own sessions. Admins see all active sessions.
    """
    if current_user["role"] in ["admin", "superadmin"]:
        # Admins see all active sessions
        query = select(Session).where(Session.is_active == True)
    else:
        # Users see only their own active sessions
        query = select(Session).where(
            Session.user_id == current_user["user_id"],
            Session.is_active == True
        )

    result = await db.execute(query)
    sessions = result.scalars().all()

    return sessions


@router.get("/user/{user_id}", response_model=list[SessionResponse])
async def get_user_sessions(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async),
    include_inactive: bool = False
):
    """
    Get sessions for a specific user (ASYNC).

    Users can see their own sessions. Admins can see any user's sessions.
    """
    # Check permission
    if current_user["user_id"] != user_id and current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' sessions"
        )

    query = select(Session).where(Session.user_id == user_id)

    if not include_inactive:
        query = query.where(Session.is_active == True)

    query = query.order_by(Session.session_start.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

    return sessions
