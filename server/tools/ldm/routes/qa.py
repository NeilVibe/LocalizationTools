"""
QA (Quality Assurance) endpoints - Auto-LQA System

P2: Auto-LQA Implementation
P10: DB Abstraction Layer - Uses QAResultRepository for FULL PARITY

Provides endpoints for:
- Single row QA check (LIVE mode)
- Full file QA check
- Get QA results (row/file level)
- Resolve QA issues
- QA summary

Uses centralized QA helpers from server/utils/qa_helpers.py
Uses QAResultRepository for database operations (PostgreSQL/SQLite)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.models import LDMFile, User, LDMActiveTM, LDMTMEntry
from server.repositories import (
    QAResultRepository, get_qa_repository,
    RowRepository, get_row_repository,
    FileRepository, get_file_repository
)
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
    logger.warning("[QA] ahocorasick not installed, using fallback for term check")

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
    row: Dict[str, Any],
    checks: List[str],
    file_rows: Optional[List[Dict[str, Any]]] = None,
    glossary_terms: Optional[List[tuple]] = None
) -> List[dict]:
    """
    Run QA checks on a single row.

    P10: Works with dicts from Repository Pattern (not LDMRow objects).

    Args:
        row: Row dict with id, file_id, row_num, source, target
        checks: List of check types to run
        file_rows: All rows in the file as dicts (needed for line check)
        glossary_terms: List of (source, target) tuples for term check

    Returns:
        List of issue dicts
    """
    issues = []

    source = row.get("source", "")
    target = row.get("target", "")
    row_id = row.get("id")

    if not source or not target:
        return issues  # Skip rows without both source and target

    # 1. Pattern Check - {code} patterns must match
    if "pattern" in checks:
        pattern_issue = check_pattern_match(source, target)
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
        source_text = source.strip()
        target_text = target.strip()

        for other_row in file_rows:
            other_id = other_row.get("id")
            other_source = other_row.get("source", "")
            other_target = other_row.get("target", "")

            if other_id == row_id:
                continue
            if not other_source or not other_target:
                continue

            other_source_stripped = other_source.strip()
            other_target_stripped = other_target.strip()

            if other_source_stripped == source_text:
                # Same source, check if target differs
                if other_target_stripped != target_text:
                    issues.append({
                        "check_type": "line",
                        "severity": "warning",
                        "message": f"Inconsistent: '{target_text[:50]}' vs '{other_target_stripped[:50]}' at row {other_row.get('row_num', 0)}",
                        "details": {
                            "other_row_id": other_id,
                            "other_row_num": other_row.get("row_num", 0),
                            "other_target": other_target_stripped[:100]
                        }
                    })
                    break  # Only report first conflict

    # 3. Term Check - Glossary terms must be present in translation
    # Uses Aho-Corasick matching with word isolation
    if "term" in checks and glossary_terms:
        source_text = source.strip()
        target_text = target.strip()

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
    qa_repo: QAResultRepository,
    row_id: int,
    file_id: int,
    issues: List[dict]
) -> List[dict]:
    """
    Save QA results to database using QAResultRepository.

    P10: Uses repository pattern - works with both PostgreSQL and SQLite.

    Clears old unresolved issues and saves new ones.
    """
    logger.debug(f"[QA] _save_qa_results: row_id={row_id}, file_id={file_id}, issues={len(issues)}")

    # Delete old unresolved issues for this row
    await qa_repo.delete_unresolved_for_row(row_id)

    # Bulk create new QA results
    if issues:
        results_to_create = [
            {
                "row_id": row_id,
                "file_id": file_id,
                "check_type": issue["check_type"],
                "severity": issue["severity"],
                "message": issue["message"],
                "details": issue.get("details")
            }
            for issue in issues
        ]
        await qa_repo.bulk_create(results_to_create)

    # Get saved results to return
    saved_results = await qa_repo.get_for_row(row_id)
    logger.debug(f"[QA] _save_qa_results complete: row_id={row_id}, saved={len(saved_results)}")
    return saved_results


# =============================================================================
# Single Row QA Endpoints
# =============================================================================

@router.post("/rows/{row_id}/check-qa", response_model=RowQACheckResponse)
async def check_row_qa(
    row_id: int,
    request: QACheckRequest,
    db: AsyncSession = Depends(get_async_db),
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Run QA checks on a single row (LIVE mode).
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.

    Used when user confirms a cell with "Use QA" enabled.
    """
    logger.debug(f"[QA] check_row_qa: row_id={row_id}, checks={request.checks}")

    # Get the row using repository (handles PostgreSQL/SQLite automatically)
    row = await row_repo.get(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    file_id = row.get("file_id")

    # Get all rows in file for line check
    file_rows = None
    if "line" in request.checks:
        file_rows = await row_repo.get_all_for_file(file_id)

    # Get glossary terms for term check
    # NOTE: Glossary terms still use PostgreSQL - TM linking not yet in repository
    glossary_terms = None
    if "term" in request.checks:
        glossary_terms = await _get_glossary_terms(db, file_id)

    # Run checks
    issues = await _run_qa_checks(row, request.checks, file_rows, glossary_terms)

    # Save results using repository (works for both PostgreSQL and SQLite)
    qa_results = await _save_qa_results(qa_repo, row.get("id"), file_id, issues)

    checked_at = datetime.utcnow()

    logger.info(f"[QA] check_row_qa complete: row_id={row_id}, issues={len(issues)}")

    return RowQACheckResponse(
        row_id=row_id,
        issues=[
            QAIssue(
                id=r["id"],
                check_type=r["check_type"],
                severity=r["severity"],
                message=r["message"],
                details=r.get("details"),
                created_at=r["created_at"],
                resolved_at=r.get("resolved_at")
            ) for r in qa_results
        ],
        issue_count=len(issues),
        checked_at=checked_at
    )


@router.get("/rows/{row_id}/qa-results", response_model=RowQAResultsResponse)
async def get_row_qa_results(
    row_id: int,
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA results for a single row (Edit Modal).
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    """
    logger.debug(f"[QA] get_row_qa_results: row_id={row_id}")

    # Get unresolved QA results for this row using repository
    qa_results = await qa_repo.get_for_row(row_id, include_resolved=False)

    logger.debug(f"[QA] get_row_qa_results complete: row_id={row_id}, count={len(qa_results)}")

    return RowQAResultsResponse(
        row_id=row_id,
        issues=[
            QAIssue(
                id=r["id"],
                check_type=r["check_type"],
                severity=r["severity"],
                message=r["message"],
                details=r.get("details"),
                created_at=r["created_at"],
                resolved_at=r.get("resolved_at")
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
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Run QA checks on entire file (Full File QA mode).
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.

    Used when user right-clicks file → "Run Full QA".
    """
    logger.debug(f"[QA] check_file_qa: file_id={file_id}, checks={request.checks}")

    # Get file using repository (handles PostgreSQL/SQLite automatically)
    file = await file_repo.get(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Get all rows using repository
    rows = await row_repo.get_all_for_file(file_id)

    # Get glossary terms for term check (once for all rows)
    # NOTE: Glossary terms still use PostgreSQL - TM linking not yet in repository
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
        # Skip already checked rows unless force=True
        if not request.force and row.get("qa_checked_at"):
            continue

        source = row.get("source", "")
        target = row.get("target", "")

        if not source or not target:
            continue

        # Run checks
        issues = await _run_qa_checks(row, request.checks, rows, glossary_terms)

        # Save results using repository
        await _save_qa_results(qa_repo, row.get("id"), file_id, issues)

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

    logger.info(f"[QA] check_file_qa complete: file_id={file_id}, rows_checked={rows_checked}, issues={total_issues}")

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
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA results for a file (QA Menu).
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.

    Optionally filter by check_type.
    """
    logger.debug(f"[QA] get_file_qa_results: file_id={file_id}, check_type={check_type}")

    # Get QA results using repository (includes row info)
    qa_results = await qa_repo.get_for_file(file_id, check_type=check_type, include_resolved=False)

    issues = []
    for r in qa_results:
        issues.append(QAIssueWithRow(
            id=r["id"],
            check_type=r["check_type"],
            severity=r["severity"],
            message=r["message"],
            details=r.get("details"),
            created_at=r["created_at"],
            resolved_at=r.get("resolved_at"),
            row_id=r["row_id"],
            row_num=r.get("row_num", 0),
            source=r.get("source"),
            target=r.get("target")
        ))

    logger.debug(f"[QA] get_file_qa_results complete: file_id={file_id}, count={len(issues)}")

    return FileQAResultsResponse(
        file_id=file_id,
        check_type=check_type,
        issues=issues,
        total_count=len(issues)
    )


@router.get("/files/{file_id}/qa-summary", response_model=QASummary)
async def get_file_qa_summary(
    file_id: int,
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Get QA summary for a file.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.

    Returns count of issues per check type.
    """
    logger.debug(f"[QA] get_file_qa_summary: file_id={file_id}")

    # Get summary using repository
    summary = await qa_repo.get_summary(file_id)

    logger.debug(f"[QA] get_file_qa_summary complete: file_id={file_id}, total={summary.get('total', 0)}")

    return QASummary(
        file_id=file_id,
        line=summary.get("line", 0),
        term=summary.get("term", 0),
        pattern=summary.get("pattern", 0),
        character=summary.get("character", 0),
        grammar=summary.get("grammar", 0),
        total=summary.get("total", 0),
        last_checked=summary.get("last_checked")
    )


# =============================================================================
# QA Result Management
# =============================================================================

@router.post("/qa-results/{result_id}/resolve")
async def resolve_qa_issue(
    result_id: int,
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    current_user: User = Depends(get_current_active_user_async)
):
    """
    Mark a QA issue as resolved.
    P10: Uses repository pattern - works with both PostgreSQL and SQLite.
    """
    logger.debug(f"[QA] resolve_qa_issue: result_id={result_id}")

    # Get the QA result first to check if it exists
    qa_result = await qa_repo.get(result_id)

    if not qa_result:
        raise HTTPException(status_code=404, detail="QA result not found")

    if qa_result.get("resolved_at"):
        raise HTTPException(status_code=400, detail="QA issue already resolved")

    # Resolve using repository
    resolved = await qa_repo.resolve(result_id, current_user.user_id)

    logger.info(f"[QA] resolve_qa_issue complete: result_id={result_id}, resolved_by={current_user.user_id}")

    return {"status": "resolved", "result_id": result_id}

