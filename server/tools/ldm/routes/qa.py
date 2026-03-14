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
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.database.models import User
from server.repositories import (
    QAResultRepository, get_qa_repository,
    RowRepository, get_row_repository,
    FileRepository, get_file_repository,
    TMRepository, get_tm_repository
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

# P051-02: Noise filter threshold -- terms triggering more issues than this
# across a file are likely false positives and get excluded
MAX_ISSUES_PER_TERM = 6


# =============================================================================
# QA Check Logic
# =============================================================================

async def _get_glossary_terms(
    file_id: int,
    tm_repo: TMRepository,
    max_length: int = 20
) -> List[tuple]:
    """
    Get glossary terms from the file's linked TMs.

    P10: Uses Repository Pattern - works with both PostgreSQL and SQLite.

    Uses short TM entries (source < max_length chars) as glossary.

    Args:
        file_id: File ID to get active TMs for
        tm_repo: TM Repository (handles PostgreSQL/SQLite automatically)
        max_length: Max source length for glossary terms

    Returns:
        List of (source, target) tuples
    """
    # P051-02: Try GlossaryService first (if available from Plan 01)
    try:
        from server.tools.ldm.services.glossary_service import get_glossary_service
        glossary_svc = get_glossary_service()
        if glossary_svc and glossary_svc.is_loaded():
            terms = glossary_svc.get_terms_for_file(file_id)
            if terms:
                logger.debug(f"[QA] Using GlossaryService for file_id={file_id}, {len(terms)} terms")
                return terms
    except (ImportError, AttributeError):
        pass  # GlossaryService not available, fall back to TM-based

    # Get active TMs for this file (inherits from folder/project/platform)
    active_tms = await tm_repo.get_active_for_file(file_id)

    if not active_tms:
        return []

    # Extract TM IDs
    tm_ids = [tm.get("id") for tm in active_tms if tm.get("id")]

    if not tm_ids:
        return []

    # Get glossary terms using repository
    return await tm_repo.get_glossary_terms(tm_ids, max_length=max_length)


def _build_line_check_index(
    file_rows: List[Dict[str, Any]]
) -> Dict[str, List[tuple]]:
    """
    Build a source-to-targets grouping dict for O(1) Line Check lookups.

    Args:
        file_rows: All rows in the file as dicts

    Returns:
        Dict mapping source_text -> list of (row_id, row_num, target_text)
    """
    from collections import defaultdict
    index: Dict[str, List[tuple]] = defaultdict(list)
    for row in file_rows:
        source = (row.get("source") or "").strip()
        target = (row.get("target") or "").strip()
        if source and target:
            index[source].append((
                row.get("id"),
                row.get("row_num", 0),
                target
            ))
    return dict(index)


def _build_term_automaton(glossary_terms: List[tuple]):
    """
    Build an Aho-Corasick automaton from glossary terms (once, reused for all rows).

    P051-02: Extracted from _run_qa_checks to enable service-level reuse.

    Args:
        glossary_terms: List of (source, target) tuples

    Returns:
        Tuple of (automaton, term_map) where term_map maps index -> (source, target)
    """
    if not HAS_AHOCORASICK or not glossary_terms:
        return None, {}

    automaton = ahocorasick.Automaton()
    term_map = {}
    for idx, (term_source, term_target) in enumerate(glossary_terms):
        automaton.add_word(term_source, (idx, term_source, term_target))
        term_map[idx] = (term_source, term_target)
    automaton.make_automaton()
    return automaton, term_map


def _apply_noise_filter(issues: List[dict]) -> List[dict]:
    """
    Remove term check issues for terms that trigger too many times (false positives).

    P051-02: If a glossary term triggers more than MAX_ISSUES_PER_TERM issues
    across a file, it's likely a false positive (too generic) and is excluded.

    Args:
        issues: List of issue dicts (term check only)

    Returns:
        Filtered list with noisy terms removed
    """
    from collections import Counter

    # Count occurrences per glossary_source
    term_counts: Counter = Counter()
    for issue in issues:
        if issue.get("check_type") == "term":
            glossary_source = issue.get("details", {}).get("glossary_source", "")
            if glossary_source:
                term_counts[glossary_source] += 1

    # Filter out noisy terms
    noisy_terms = {term for term, count in term_counts.items() if count > MAX_ISSUES_PER_TERM}

    if not noisy_terms:
        return issues

    logger.debug(f"[QA] Noise filter removing {len(noisy_terms)} noisy terms: {noisy_terms}")

    return [
        issue for issue in issues
        if issue.get("check_type") != "term"
        or issue.get("details", {}).get("glossary_source", "") not in noisy_terms
    ]


async def _run_qa_checks(
    row: Dict[str, Any],
    checks: List[str],
    file_rows: Optional[List[Dict[str, Any]]] = None,
    glossary_terms: Optional[List[tuple]] = None,
    line_check_index: Optional[Dict[str, List[tuple]]] = None,
    term_automaton=None,
    term_map: Optional[Dict[int, tuple]] = None,
) -> List[dict]:
    """
    Run QA checks on a single row.

    P10: Works with dicts from Repository Pattern (not LDMRow objects).
    P051-02: Enhanced with pre-built line_check_index for O(1) lookups,
             pre-built term_automaton for efficient multi-pattern matching.

    Args:
        row: Row dict with id, file_id, row_num, source, target
        checks: List of check types to run
        file_rows: All rows in the file as dicts (needed for line check if no index)
        glossary_terms: List of (source, target) tuples for term check
        line_check_index: Pre-built index from _build_line_check_index
        term_automaton: Pre-built AC automaton from _build_term_automaton
        term_map: Term map from _build_term_automaton

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
    # P051-02: Group-based O(n) approach instead of O(n^2) per-row comparison
    if "line" in checks and (file_rows or line_check_index):
        source_text = source.strip()
        target_text = target.strip()

        # Build index on-the-fly if not provided (single-row QA mode)
        if line_check_index is None and file_rows:
            line_check_index = _build_line_check_index(file_rows)

        if line_check_index and source_text in line_check_index:
            for other_id, other_row_num, other_target in line_check_index[source_text]:
                if other_id == row_id:
                    continue
                if other_target != target_text:
                    issues.append({
                        "check_type": "line",
                        "severity": "warning",
                        "message": f"Inconsistent: '{target_text[:50]}' vs '{other_target[:50]}' at row {other_row_num}",
                        "details": {
                            "other_row_id": other_id,
                            "other_row_num": other_row_num,
                            "other_target": other_target[:100]
                        }
                    })

    # 3. Term Check - Glossary terms must be present in translation
    # P051-02: Uses pre-built AC automaton (service-level), reports ALL missing terms
    if "term" in checks and glossary_terms:
        source_text = source.strip()
        target_text = target.strip()

        # Build automaton on-the-fly if not provided (single-row QA mode)
        ac = term_automaton
        if ac is None and HAS_AHOCORASICK:
            ac, term_map = _build_term_automaton(glossary_terms)

        if ac is not None:
            # Find all glossary terms in source using AC automaton
            for end_index, (idx, term_source, term_target) in ac.iter(source_text):
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
        else:
            # Fallback: simple substring matching (no ahocorasick)
            for term_source, term_target in glossary_terms:
                pos = source_text.find(term_source)
                if pos != -1:
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
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
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

    # Get glossary terms for term check (P10: Now uses Repository Pattern)
    glossary_terms = None
    if "term" in request.checks:
        glossary_terms = await _get_glossary_terms(file_id, tm_repo)

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
    qa_repo: QAResultRepository = Depends(get_qa_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
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

    # Get glossary terms for term check (P10: Now uses Repository Pattern)
    glossary_terms = None
    if "term" in request.checks:
        glossary_terms = await _get_glossary_terms(file_id, tm_repo)

    # P051-02: Build pre-computed structures ONCE for all rows
    line_check_index = None
    if "line" in request.checks:
        line_check_index = _build_line_check_index(rows)

    term_automaton = None
    term_map = None
    if "term" in request.checks and glossary_terms:
        term_automaton, term_map = _build_term_automaton(glossary_terms)

    # Summary counters
    summary = {
        check: {"issue_count": 0, "severity": "ok"}
        for check in request.checks
    }
    total_issues = 0
    rows_checked = 0

    # P051-02: Collect all term issues for noise filtering
    all_term_issues: List[tuple] = []  # (row_id, file_id, issue)

    # Check each row
    for row in rows:
        # Skip already checked rows unless force=True
        if not request.force and row.get("qa_checked_at"):
            continue

        source = row.get("source", "")
        target = row.get("target", "")

        if not source or not target:
            continue

        # Run checks with pre-built structures
        issues = await _run_qa_checks(
            row, request.checks, rows, glossary_terms,
            line_check_index=line_check_index,
            term_automaton=term_automaton,
            term_map=term_map,
        )

        # Separate term issues for noise filter, save non-term issues immediately
        non_term_issues = [i for i in issues if i["check_type"] != "term"]
        term_issues = [i for i in issues if i["check_type"] == "term"]

        if term_issues:
            for ti in term_issues:
                all_term_issues.append((row.get("id"), file_id, ti))

        # Save non-term results immediately
        await _save_qa_results(qa_repo, row.get("id"), file_id, non_term_issues)

        rows_checked += 1
        total_issues += len(non_term_issues)

        # Update summary for non-term issues
        for issue in non_term_issues:
            check_type = issue["check_type"]
            if check_type in summary:
                summary[check_type]["issue_count"] += 1
                if issue["severity"] == "error":
                    summary[check_type]["severity"] = "error"
                elif issue["severity"] == "warning" and summary[check_type]["severity"] == "ok":
                    summary[check_type]["severity"] = "warning"

    # P051-02: Apply noise filter to collected term issues, then save
    if all_term_issues:
        all_term_issue_dicts = [ti for _, _, ti in all_term_issues]
        filtered_term_issues = _apply_noise_filter(all_term_issue_dicts)

        # Build a set of filtered issues for fast lookup
        filtered_set = set()
        for fi in filtered_term_issues:
            key = (fi["details"]["glossary_source"], fi["details"]["glossary_target"])
            filtered_set.add(key)

        # Save filtered term issues grouped by row
        from collections import defaultdict
        row_term_issues: Dict[int, List[dict]] = defaultdict(list)
        for row_id_val, file_id_val, ti in all_term_issues:
            key = (ti["details"]["glossary_source"], ti["details"]["glossary_target"])
            if key in filtered_set:
                row_term_issues[row_id_val].append(ti)

        for rid, term_issues_for_row in row_term_issues.items():
            # Append term issues to existing saved results for this row
            await _save_qa_results(qa_repo, rid, file_id, term_issues_for_row)
            total_issues += len(term_issues_for_row)

        # Update term summary
        if "term" in summary:
            term_count = sum(len(v) for v in row_term_issues.values())
            summary["term"]["issue_count"] = term_count
            if term_count > 0:
                summary["term"]["severity"] = "warning"

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

