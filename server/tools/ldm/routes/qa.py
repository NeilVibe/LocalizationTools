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
from server.utils.qa_helpers import (
    check_pattern_match,
    is_isolated,
)

# Try to import ahocorasick for efficient term matching
try:
    import ahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False
    logger.warning("ahocorasick not installed, using fallback for term check")

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
    # Simple: compare all entries, flag inconsistencies
    if "line" in checks and file_rows:
        source_text = row.source.strip()
        target_text = row.target.strip()

        for other_row in file_rows:
            if other_row.id == row.id:
                continue
            if not other_row.source or not other_row.target:
                continue

            other_source = other_row.source.strip()
            other_target = other_row.target.strip()

            if other_source == source_text:
                # Same source, check if target differs
                if other_target != target_text:
                    issues.append({
                        "check_type": "line",
                        "severity": "warning",
                        "message": f"Inconsistent: '{target_text[:50]}' vs '{other_target[:50]}' at row {other_row.row_num}",
                        "details": {
                            "other_row_id": other_row.id,
                            "other_row_num": other_row.row_num,
                            "other_target": other_target[:100]
                        }
                    })
                    break  # Only report first conflict

    # 3. Term Check - Glossary terms must be present in translation
    # Uses Aho-Corasick matching with word isolation
    if "term" in checks and glossary_terms:
        source_text = row.source.strip()
        target_text = row.target.strip()

        if HAS_AHOCORASICK:
            # Build automaton for efficient multi-pattern matching
            automaton = ahocorasick.Automaton()
            for idx, (term_source, term_target) in enumerate(glossary_terms):
                automaton.add_word(term_source, (idx, term_source, term_target))
            automaton.make_automaton()

            # Find all glossary terms in source
            for end_index, (idx, term_source, term_target) in automaton.iter(source_text):
                start_index = end_index - len(term_source) + 1

                # Check if match is isolated (whole word)
                if is_isolated(source_text, start_index, end_index + 1):
                    # Check if expected translation is in target
                    if term_target.lower() not in target_text.lower():
                        issues.append({
                            "check_type": "term",
                            "severity": "warning",
                            "message": f"Missing term '{term_target}' for '{term_source}'",
                            "details": {
                                "glossary_source": term_source,
                                "glossary_target": term_target
                            }
                        })
                        break  # Only report first missing term
        else:
            # Fallback: simple substring matching
            for term_source, term_target in glossary_terms:
                pos = source_text.find(term_source)
                if pos != -1:
                    # Check isolation
                    if is_isolated(source_text, pos, pos + len(term_source)):
                        if term_target.lower() not in target_text.lower():
                            issues.append({
                                "check_type": "term",
                                "severity": "warning",
                                "message": f"Missing term '{term_target}' for '{term_source}'",
                                "details": {
                                    "glossary_source": term_source,
                                    "glossary_target": term_target
                                }
                            })
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
    P9: Falls back to SQLite for local files.

    Used when user confirms a cell with "Use QA" enabled.
    """
    # Get the row
    result = await db.execute(
        select(LDMRow).where(LDMRow.id == row_id)
    )
    row = result.scalar_one_or_none()

    if not row:
        # P9: Fallback to SQLite for local files
        return await _check_local_row_qa(row_id, request)

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
    P9: Returns empty for local files (QA results are ephemeral).
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

    # P9: If no results found, check if it's a local file row (return empty)
    if not qa_results:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_row(row_id):
            return RowQAResultsResponse(row_id=row_id, issues=[], total_count=0)

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
    P9: Falls back to SQLite for local files.

    Used when user right-clicks file → "Run Full QA".
    """
    # Get the file
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        # P9: Fallback to SQLite for local files
        return await _check_local_file_qa(file_id, request)

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
    P9: Returns empty for local files (QA results are ephemeral).

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

    # P9: If no results, check if it's a local file (return empty)
    if not rows:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            return FileQAResultsResponse(file_id=file_id, check_type=check_type, issues=[], total_count=0)

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
    P9: Returns zeros for local files (QA results are ephemeral).

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

    # P9: If no counts and no last_checked, check if local file (return zeros)
    if not counts and not last_checked:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        if offline_db.get_local_file(file_id):
            return QASummary(
                file_id=file_id, line=0, term=0, pattern=0,
                character=0, grammar=0, total=0, last_checked=None
            )

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


# =============================================================================
# P9: SQLite Local File QA Helpers
# =============================================================================

async def _check_local_row_qa(row_id: int, request: QACheckRequest) -> RowQACheckResponse:
    """
    P9: Run QA checks on a local file row.
    Uses same QA logic but with SQLite data. Results are ephemeral (not saved).
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    row_data = offline_db.get_row(row_id)

    if not row_data:
        raise HTTPException(status_code=404, detail="Row not found")

    # Create row-like object for existing QA check functions
    class RowLike:
        def __init__(self, data):
            self.id = data.get("id")
            self.file_id = data.get("file_id")
            self.row_num = data.get("row_num", 0)
            self.string_id = data.get("string_id", "")
            self.source = data.get("source", "")
            self.target = data.get("target", "")
            self.status = data.get("status", "pending")

    row = RowLike(row_data)

    # Run pattern check (no database needed)
    issues = []
    if "pattern" in request.checks:
        pattern_issue = check_pattern_match(row.source, row.target)
        if pattern_issue:
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
                "id": 0,  # No persistence for local files
                "check_type": "pattern",
                "severity": "error",
                "message": message,
                "details": pattern_issue,
                "created_at": datetime.utcnow(),
                "resolved_at": None
            })

    checked_at = datetime.utcnow()
    logger.info(f"P9: Local QA check row {row_id}: {len(issues)} issues found")

    return RowQACheckResponse(
        row_id=row_id,
        issues=[QAIssue(**issue) for issue in issues],
        issue_count=len(issues),
        checked_at=checked_at
    )


async def _check_local_file_qa(file_id: int, request: QACheckRequest) -> FileQACheckResponse:
    """
    P9: Run QA checks on a local file.
    Uses same QA logic but with SQLite data. Results are ephemeral (not saved).
    """
    from server.database.offline import get_offline_db

    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    rows_data = offline_db.get_rows_for_file(file_id)

    # Create row-like objects
    class RowLike:
        def __init__(self, data):
            self.id = data.get("id")
            self.file_id = data.get("file_id")
            self.row_num = data.get("row_num", 0)
            self.string_id = data.get("string_id", "")
            self.source = data.get("source", "")
            self.target = data.get("target", "")
            self.status = data.get("status", "pending")
            self.qa_checked_at = None

    rows = [RowLike(r) for r in rows_data]

    # Summary counters
    summary = {check: {"issue_count": 0, "severity": "ok"} for check in request.checks}
    total_issues = 0
    rows_checked = 0

    # Check each row
    for row in rows:
        if not row.source or not row.target:
            continue

        row_issues = []

        # Pattern check
        if "pattern" in request.checks:
            pattern_issue = check_pattern_match(row.source, row.target)
            if pattern_issue:
                row_issues.append({"check_type": "pattern", "severity": "error"})

        rows_checked += 1
        total_issues += len(row_issues)

        # Update summary
        for issue in row_issues:
            check_type = issue["check_type"]
            if check_type in summary:
                summary[check_type]["issue_count"] += 1
                if issue["severity"] == "error":
                    summary[check_type]["severity"] = "error"

    checked_at = datetime.utcnow()
    logger.info(f"P9: Local QA check file {file_id}: {rows_checked} rows, {total_issues} issues")

    return FileQACheckResponse(
        file_id=file_id,
        total_rows=len(rows),
        rows_checked=rows_checked,
        summary=summary,
        total_issues=total_issues,
        checked_at=checked_at
    )
