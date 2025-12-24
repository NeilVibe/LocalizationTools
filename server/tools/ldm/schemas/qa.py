"""QA (Quality Assurance) related schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# =============================================================================
# Request Schemas
# =============================================================================

class QACheckRequest(BaseModel):
    """Request to run QA checks on a row or file."""
    checks: List[str] = ["line", "term", "pattern", "character"]  # Check types to run
    force: bool = False  # True = re-check all, False = skip already checked


class QAResolveRequest(BaseModel):
    """Request to resolve a QA issue."""
    pass  # No body needed, just POST to resolve


# =============================================================================
# Response Schemas
# =============================================================================

class QAIssue(BaseModel):
    """Single QA issue."""
    id: int
    check_type: str  # 'line', 'term', 'pattern', 'character', 'grammar'
    severity: str  # 'error', 'warning', 'info'
    message: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QAIssueWithRow(QAIssue):
    """QA issue with row context (for file-level reports)."""
    row_id: int
    row_num: int
    source: Optional[str] = None
    target: Optional[str] = None


class RowQACheckResponse(BaseModel):
    """Response from checking a single row."""
    row_id: int
    issues: List[QAIssue]
    issue_count: int
    checked_at: datetime


class FileQACheckResponse(BaseModel):
    """Response from checking an entire file."""
    file_id: int
    total_rows: int
    rows_checked: int
    summary: Dict[str, Dict[str, Any]]  # {check_type: {issue_count: X, severity: "warning"}}
    total_issues: int
    checked_at: datetime


class FileQAResultsResponse(BaseModel):
    """QA results for a file, optionally filtered by check type."""
    file_id: int
    check_type: Optional[str] = None  # If filtered
    issues: List[QAIssueWithRow]
    total_count: int


class RowQAResultsResponse(BaseModel):
    """QA results for a single row."""
    row_id: int
    issues: List[QAIssue]
    total_count: int


class QASummary(BaseModel):
    """Summary of QA status for a file."""
    file_id: int
    line: int = 0
    term: int = 0
    pattern: int = 0
    character: int = 0
    grammar: int = 0
    total: int = 0
    last_checked: Optional[datetime] = None
