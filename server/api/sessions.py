"""
Session Management API Endpoints

User session tracking and management.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from loguru import logger

from server.api.schemas import SessionCreate, SessionResponse
from server.database.models import Session
from server.utils.dependencies import get_db, get_current_active_user


# Create router
router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============================================================================
# Session Endpoints
# ============================================================================

@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    session_data: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Start a new user session.

    Creates a new session record when user opens the application.
    """
    try:
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
        db.commit()
        db.refresh(new_session)

        logger.info(
            f"New session started: {new_session.session_id} for user {current_user['username']} "
            f"on machine {session_data.machine_id}"
        )

        return new_session

    except Exception as e:
        db.rollback()
        logger.exception(f"Error starting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )


@router.put("/{session_id}/heartbeat")
def session_heartbeat(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update session last activity timestamp (heartbeat).

    Clients should call this periodically to keep session active.
    """
    session = db.query(Session).filter(Session.session_id == session_id).first()

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
    session.last_activity = datetime.utcnow()
    db.commit()

    return {"message": "Session updated", "last_activity": session.last_activity}


@router.put("/{session_id}/end")
def end_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    End a user session.

    Marks session as inactive when user closes the application.
    """
    session = db.query(Session).filter(Session.session_id == session_id).first()

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
    session.is_active = False
    session.last_activity = datetime.utcnow()
    db.commit()

    logger.info(f"Session ended: {session_id} for user {current_user['username']}")

    return {"message": "Session ended successfully"}


@router.get("/active", response_model=list[SessionResponse])
def get_active_sessions(
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get all active sessions.

    Users see their own sessions. Admins see all active sessions.
    """
    if current_user["role"] in ["admin", "superadmin"]:
        # Admins see all active sessions
        sessions = db.query(Session).filter(Session.is_active == True).all()
    else:
        # Users see only their own active sessions
        sessions = db.query(Session).filter(
            Session.user_id == current_user["user_id"],
            Session.is_active == True
        ).all()

    return sessions


@router.get("/user/{user_id}", response_model=list[SessionResponse])
def get_user_sessions(
    user_id: int,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
    include_inactive: bool = False
):
    """
    Get sessions for a specific user.

    Users can see their own sessions. Admins can see any user's sessions.
    """
    # Check permission
    if current_user["user_id"] != user_id and current_user["role"] not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' sessions"
        )

    query = db.query(Session).filter(Session.user_id == user_id)

    if not include_inactive:
        query = query.filter(Session.is_active == True)

    sessions = query.order_by(Session.session_start.desc()).all()

    return sessions
