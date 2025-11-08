"""
API Schemas (Pydantic Models)

Request and response models for FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserLogin(BaseModel):
    """Login request."""
    username: str
    password: str


class UserRegister(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UserResponse(BaseModel):
    """User data response."""
    user_id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    department: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True  # For SQLAlchemy models


# ============================================================================
# Session Schemas
# ============================================================================

class SessionCreate(BaseModel):
    """Session creation request."""
    machine_id: str
    ip_address: Optional[str] = None
    app_version: str


class SessionResponse(BaseModel):
    """Session data response."""
    session_id: str
    user_id: int
    machine_id: str
    ip_address: Optional[str]
    app_version: str
    session_start: datetime
    last_activity: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Log Submission Schemas
# ============================================================================

class LogEntry(BaseModel):
    """Single log entry submission."""
    username: str
    machine_id: str
    tool_name: str
    function_name: str
    duration_seconds: float
    status: str = "success"  # success, error, warning
    error_message: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None  # {size_mb, rows, columns, etc.}
    parameters: Optional[Dict[str, Any]] = None  # Function parameters


class LogSubmission(BaseModel):
    """Batch log submission request."""
    session_id: Optional[str] = None
    logs: List[LogEntry]


class LogResponse(BaseModel):
    """Log submission response."""
    success: bool
    logs_received: int
    message: str


# ============================================================================
# Error Logging Schemas
# ============================================================================

class ErrorReport(BaseModel):
    """Error report submission."""
    machine_id: str
    tool_name: str
    function_name: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    app_version: str
    context: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error report response."""
    success: bool
    error_id: int
    message: str


# ============================================================================
# Stats & Analytics Schemas
# ============================================================================

class StatsRequest(BaseModel):
    """Stats query request."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tool_name: Optional[str] = None
    user_id: Optional[int] = None


class ToolStats(BaseModel):
    """Tool usage statistics."""
    tool_name: str
    total_uses: int
    unique_users: int
    avg_duration_seconds: float
    success_rate: float


class DashboardStats(BaseModel):
    """Dashboard overview statistics."""
    total_users: int
    active_users_today: int
    active_users_this_week: int
    active_users_this_month: int
    total_operations: int
    operations_today: int
    most_used_tools: List[ToolStats]
    avg_response_time: float


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    timestamp: datetime


# ============================================================================
# Announcement Schemas
# ============================================================================

class AnnouncementCreate(BaseModel):
    """Create announcement request."""
    title: str
    message: str
    priority: str = "info"  # info, warning, critical
    expires_at: Optional[datetime] = None
    target_users: Optional[List[int]] = None  # None = all users


class AnnouncementResponse(BaseModel):
    """Announcement data."""
    announcement_id: int
    title: str
    message: str
    priority: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Feedback Schemas
# ============================================================================

class FeedbackCreate(BaseModel):
    """User feedback submission."""
    feedback_type: str  # bug, feature, comment
    tool_name: Optional[str] = None
    subject: str
    description: str
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 stars


class FeedbackResponse(BaseModel):
    """Feedback data."""
    feedback_id: int
    user_id: int
    timestamp: datetime
    feedback_type: str
    tool_name: Optional[str]
    subject: str
    description: str
    rating: Optional[int]
    status: str
    admin_response: Optional[str]

    class Config:
        from_attributes = True
