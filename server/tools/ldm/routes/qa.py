"""
QA (Quality Assurance) endpoints - Auto-LQA System

P2: Auto-LQA Implementation
Provides endpoints for:
- Single row QA check (LIVE mode)
- Full file QA check
- Get QA results (row/file level)
- Resolve QA issues
- QA summary

Uses centralized QA helpers from server/utils/qa_helpers.py
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMRow, LDMFile, LDMQAResult, User, LDMActiveTM, LDMTMEntry
from server.tools.ldm.schemas import (
    QACheckRequest,
    RowQACheckResponse, FileQACheckResponse,
    FileQAResultsResponse, RowQAResultsResponse,
    QAIssue, QAIssueWithRow, QASummary
)

# Import QA check functions from centralized utils
from server.utils.qa_helpers import check_pattern_match

router = APIRouter(tags=["LDM-QA"])


# =============================================================================
# QA Check Logic
# =============================================================================

async def _get_glossary_terms(
    db: AsyncSession,
    file_id: int,
    max_length: int = 20
) -> List[tuple]:
    """
    Get glossary terms from the project's linked TM.

    Uses short TM entries (source < max_length chars) as glossary.

    Args:
        db: Database session
        file_id: File ID to get project from
        max_length: Max source length for glossary terms

    Returns:
        List of (source, target) tuples
    """
    # Get file to find project_id
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return []

    # Get linked TMs for project
    result = await db.execute(
        select(LDMActiveTM.tm_id)
        .where(LDMActiveTM.project_id == file.project_id)
        .order_by(LDMActiveTM.priority)
    )
    tm_ids = [row[0] for row in result.all()]

    if not tm_ids:
        return []

    # Get short TM entries as glossary
    result = await db.execute(
        select(LDMTMEntry.source, LDMTMEntry.target)
        .where(
            LDMTMEntry.tm_id.in_(tm_ids),
            func.length(LDMTMEntry.source) <= max_length,
            LDMTMEntry.source.isnot(None),
            LDMTMEntry.target.isnot(None)
        )
        .limit(1000)  # Limit to prevent performance issues
    )

    return [(row[0], row[1]) for row in result.all()]


async def _run_qa_checks(
    db: AsyncSession,
    row: LDMRow,
    checks: List[str],
    file_rows: Optional[List[LDMRow]] = None,
    glossary_terms: Optional[List[tuple]] = None
) -> List[dict]:
    """
    Run QA checks on a single row.

    Args:
        db: Database session
        row: The row to check
        checks: List of check types to run
        file_rows: All rows in the file (needed for line check)
        glossary_terms: List of (source, target) tuples for term check

    Returns:
        List of issue dicts
    """
    issues = []

    if not row.source or not row.target:
        return issues  # Skip rows without both source and target

    # 1. Pattern Check - {code} patterns must match
    if "pattern" in checks:
        pattern_issue = check_pattern_match(row.source, row.target)
        if pattern_issue:
            # Generate message from details
            source_patterns = pattern_issue.get("source_patterns", [])
            target_patterns = pattern_issue.get("target_patterns", [])
            missing = set(source_patterns) - set(target_patterns)
            extra = set(target_patterns) - set(source_patterns)

            if missing and extra:
                message = f"Pattern mismatch: missing {missing}, extra {extra}"
            elif missing:
                message = f"Missing patterns: {', '.join(sorted(missing))}"
            else:
                message = f"Extra patterns: {', '.join(sorted(extra))}"

            issues.append({
                "check_type": "pattern",
                "severity": "error",
                "message": message,
                "details": pattern_issue
            })

    # 2. Line Check - Same source with different translations
    if "line" in checks and file_rows:
        source_normalized = row.source.strip().lower()
        for other_row in file_rows:
            if other_row.id == row.id:
                continue
            if not other_row.source or not other_row.target:
                continue
            if other_row.source.strip().lower() == source_normalized:
                # Same source, check if target differs
                if other_row.target.strip() != row.target.strip():
                    issues.append({
                        "check_type": "line",
                        "severity": "warning",
                        "message": f"Same source has different translation at row {other_row.row_num}",
                        "details": {
                            "other_row_id": other_row.id,
                            "other_row_num": other_row.row_num,
                            "other_target": other_row.target[:100] if other_row.target else None
                        }
                    })
                    break  # Only report first conflict

    # 3. Term Check - Glossary terms must be present in translation
    # Uses TM entries as glossary (short entries < 20 chars)
    if "term" in checks and glossary_terms:
        row_source_lower = row.source.lower()
        row_target_lower = row.target.lower()

        for term_source, term_target in glossary_terms:
            # Check if glossary source term appears in row source
            if term_source.lower() in row_source_lower:
                # Check if expected translation appears in row target
                if term_target.lower() not in row_target_lower:
                    issues.append({
                        "check_type": "term",
                        "severity": "warning",
                        "message": f"Missing term '{term_target}' for '{term_source}'",
                        "details": {
                            "glossary_source": term_source,
                            "glossary_target": term_target
                        }
                    })
                    # Only report first missing term per row to avoid spam
                    break

    return issues


async def _save_qa_results(
    db: AsyncSession,
    row: LDMRow,
    issues: List[dict]
) -> List[LDMQAResult]:
    """
    Save QA results to database.

    Clears old unresolved issues and saves new ones.
    Updates row's qa_flag_count and qa_checked_at.
    """
    # Delete old unresolved issues for this row
    await db.execute(
        LDMQAResult.__table__.delete().where(
            and_(
                LDMQAResult.row_id == row.id,
                LDMQAResult.resolved_at.is_(None)
            )
        )
    )

    # Create new QA results
    new_results = []
    for issue in issues:
        result = LDMQAResult(
            row_id=row.id,
            file_id=row.file_id,
            check_type=issue["check_type"],
            severity=issue["severity"],
            message=issue["message"],
            details=issue.get("details"),
            created_at=datetime.utcnow()
        )
        db.add(result)
        new_results.append(result)

    # Update row QA status
    row.qa_checked_at = datetime.utcnow()
    row.qa_flag_count = len(issues)

    await db.commit()
    return new_results


# =============================================================================
# Single Row QA Endpoints
# =============================================================================

@router.post("/rows/{row_id}/check-qa", response_model=RowQACheckResponse)
async def check_row_qa(
    row_id: int,
    request: QACheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Run QA checks on a single row (LIVE mode).

    Used when user confirms a cell with "Use QA" enabled.
    """
    # Get the row
    result = await db.execute(
        select(LDMRow).where(LDMRow.id == row_id)
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Get all rows in file for line check
    file_rows = None
    if "line" in request.checks:
        result = await db.execute(
            select(LDMRow).where(LDMRow.file_id == row.file_id)
        )
        file_rows = result.scalars().all()

    # Get glossary terms for term check
    glossary_terms = None
    if "term" in request.checks:
        glossary_terms = await _get_glossary_terms(db, row.file_id)

    # Run checks
    issues = await _run_qa_checks(db, row, request.checks, file_rows, glossary_terms)

    # Save results
    qa_results = await _save_qa_results(db, row, issues)

    checked_at = datetime.utcnow()

    logger.info(f"QA check row {row_id}: {len(issues)} issues found")

    return RowQACheckResponse(
        row_id=row_id,
        issues=[
            QAIssue(
                id=r.id,
                check_type=r.check_type,
                severity=r.severity,
                message=r.message,
                details=r.details,
                created_at=r.created_at,
                resolved_at=r.resolved_at
            ) for r in qa_results
        ],
        issue_count=len(issues),
        checked_at=checked_at
    )


@router.get("/rows/{row_id}/qa-results", response_model=RowQAResultsResponse)
async def get_row_qa_results(
    row_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA results for a single row (Edit Modal).
    """
    # Get unresolved QA results for this row
    result = await db.execute(
        select(LDMQAResult)
        .where(
            LDMQAResult.row_id == row_id,
            LDMQAResult.resolved_at.is_(None)
        )
        .order_by(LDMQAResult.created_at)
    )
    qa_results = result.scalars().all()

    return RowQAResultsResponse(
        row_id=row_id,
        issues=[
            QAIssue(
                id=r.id,
                check_type=r.check_type,
                severity=r.severity,
                message=r.message,
                details=r.details,
                created_at=r.created_at,
                resolved_at=r.resolved_at
            ) for r in qa_results
        ],
        total_count=len(qa_results)
    )


# =============================================================================
# File-Level QA Endpoints
# =============================================================================

@router.post("/files/{file_id}/check-qa", response_model=FileQACheckResponse)
async def check_file_qa(
    file_id: int,
    request: QACheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Run QA checks on entire file (Full File QA mode).

    Used when user right-clicks file → "Run Full QA".
    """
    # Get the file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get all rows
    result = await db.execute(
        select(LDMRow).where(LDMRow.file_id == file_id)
    )
    rows = result.scalars().all()

    # Get glossary terms for term check (once for all rows)
    glossary_terms = None
    if "term" in request.checks:
        glossary_terms = await _get_glossary_terms(db, file_id)

    # Summary counters
    summary = {
        check: {"issue_count": 0, "severity": "ok"}
        for check in request.checks
    }
    total_issues = 0
    rows_checked = 0

    # Check each row
    for row in rows:
        if not request.force and row.qa_checked_at:
            # Skip already checked rows unless force=True
            continue

        # Run checks
        issues = await _run_qa_checks(db, row, request.checks, rows, glossary_terms)

        # Save results
        await _save_qa_results(db, row, issues)

        rows_checked += 1
        total_issues += len(issues)

        # Update summary
        for issue in issues:
            check_type = issue["check_type"]
            if check_type in summary:
                summary[check_type]["issue_count"] += 1
                # Upgrade severity if needed
                if issue["severity"] == "error":
                    summary[check_type]["severity"] = "error"
                elif issue["severity"] == "warning" and summary[check_type]["severity"] == "ok":
                    summary[check_type]["severity"] = "warning"

    checked_at = datetime.utcnow()

    logger.info(f"QA check file {file_id}: {rows_checked} rows checked, {total_issues} issues found")

    return FileQACheckResponse(
        file_id=file_id,
        total_rows=len(rows),
        rows_checked=rows_checked,
        summary=summary,
        total_issues=total_issues,
        checked_at=checked_at
    )


@router.get("/files/{file_id}/qa-results", response_model=FileQAResultsResponse)
async def get_file_qa_results(
    file_id: int,
    check_type: Optional[str] = Query(None, description="Filter by check type"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA results for a file (QA Menu).

    Optionally filter by check_type.
    """
    # Build query
    query = (
        select(LDMQAResult, LDMRow)
        .join(LDMRow, LDMQAResult.row_id == LDMRow.id)
        .where(
            LDMQAResult.file_id == file_id,
            LDMQAResult.resolved_at.is_(None)
        )
    )

    if check_type:
        query = query.where(LDMQAResult.check_type == check_type)

    query = query.order_by(LDMRow.row_num, LDMQAResult.created_at)

    result = await db.execute(query)
    rows = result.all()

    issues = []
    for qa_result, row in rows:
        issues.append(QAIssueWithRow(
            id=qa_result.id,
            check_type=qa_result.check_type,
            severity=qa_result.severity,
            message=qa_result.message,
            details=qa_result.details,
            created_at=qa_result.created_at,
            resolved_at=qa_result.resolved_at,
            row_id=row.id,
            row_num=row.row_num,
            source=row.source[:200] if row.source else None,
            target=row.target[:200] if row.target else None
        ))

    return FileQAResultsResponse(
        file_id=file_id,
        check_type=check_type,
        issues=issues,
        total_count=len(issues)
    )


@router.get("/files/{file_id}/qa-summary", response_model=QASummary)
async def get_file_qa_summary(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA summary for a file.

    Returns count of issues per check type.
    """
    # Count issues by check type
    result = await db.execute(
        select(
            LDMQAResult.check_type,
            func.count(LDMQAResult.id).label("count")
        )
        .where(
            LDMQAResult.file_id == file_id,
            LDMQAResult.resolved_at.is_(None)
        )
        .group_by(LDMQAResult.check_type)
    )
    counts = {row.check_type: row.count for row in result.all()}

    # Get last checked time
    result = await db.execute(
        select(func.max(LDMRow.qa_checked_at))
        .where(LDMRow.file_id == file_id)
    )
    last_checked = result.scalar()

    total = sum(counts.values())

    return QASummary(
        file_id=file_id,
        line=counts.get("line", 0),
        term=counts.get("term", 0),
        pattern=counts.get("pattern", 0),
        character=counts.get("character", 0),
        grammar=counts.get("grammar", 0),
        total=total,
        last_checked=last_checked
    )


# =============================================================================
# QA Result Management
# =============================================================================

@router.post("/qa-results/{result_id}/resolve")
async def resolve_qa_issue(
    result_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Mark a QA issue as resolved.
    """
    # Get the QA result
    result = await db.execute(
        select(LDMQAResult).where(LDMQAResult.id == result_id)
    )
    qa_result = result.scalar_one_or_none()

    if not qa_result:
        raise HTTPException(status_code=404, detail="QA result not found")

    if qa_result.resolved_at:
        raise HTTPException(status_code=400, detail="QA issue already resolved")

    # Mark as resolved
    qa_result.resolved_at = datetime.utcnow()
    qa_result.resolved_by = current_user.user_id

    # Update row's qa_flag_count
    result = await db.execute(
        select(func.count(LDMQAResult.id))
        .where(
            LDMQAResult.row_id == qa_result.row_id,
            LDMQAResult.resolved_at.is_(None),
            LDMQAResult.id != result_id  # Exclude this one
        )
    )
    remaining_count = result.scalar() or 0

    await db.execute(
        update(LDMRow)
        .where(LDMRow.id == qa_result.row_id)
        .values(qa_flag_count=remaining_count)
    )

    await db.commit()

    logger.info(f"QA issue {result_id} resolved by user {current_user.user_id}")

    return {"status": "resolved", "result_id": result_id}
