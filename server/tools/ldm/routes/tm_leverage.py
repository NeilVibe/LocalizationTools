"""
TM Leverage Statistics endpoint.

GET /api/ldm/files/{file_id}/leverage
Returns per-file leverage stats: exact, fuzzy, new counts and percentages.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.repositories import (
    FileRepository, get_file_repository,
    RowRepository, get_row_repository,
    TMRepository, get_tm_repository,
)

router = APIRouter(tags=["LDM"])


# =============================================================================
# Leverage Calculation Helpers (importable for testing)
# =============================================================================

def _compute_leverage(batch_results: List[Dict[str, Any]], total: int) -> Dict[str, Any]:
    """
    Compute leverage statistics from TMSearcher batch results.

    Categorization thresholds:
    - exact:  best score >= 1.0 (perfect match)
    - fuzzy:  best score >= 0.75 and < 1.0
    - new:    no results or best score < 0.75

    Args:
        batch_results: List of TMSearcher.search() result dicts.
        total: Total number of rows in the file.

    Returns:
        Dict with exact, fuzzy, new, total, exact_pct, fuzzy_pct, new_pct.
    """
    exact = 0
    fuzzy = 0
    new = 0

    for result in batch_results:
        results_list = result.get("results", [])
        if not results_list:
            new += 1
            continue

        best_score = max(r.get("score", 0) for r in results_list)
        if best_score >= 1.0:
            exact += 1
        elif best_score >= 0.75:
            fuzzy += 1
        else:
            new += 1

    return {
        "exact": exact,
        "fuzzy": fuzzy,
        "new": new,
        "total": total,
        "exact_pct": round(exact / total * 100, 1) if total > 0 else 0.0,
        "fuzzy_pct": round(fuzzy / total * 100, 1) if total > 0 else 0.0,
        "new_pct": round(new / total * 100, 1) if total > 0 else 0.0,
    }


def _compute_leverage_no_tm(total: int) -> Dict[str, Any]:
    """
    Compute leverage when no active TMs exist -- everything is 'new'.

    Args:
        total: Total number of rows in the file.

    Returns:
        Dict with all new.
    """
    return {
        "exact": 0,
        "fuzzy": 0,
        "new": total,
        "total": total,
        "exact_pct": 0.0,
        "fuzzy_pct": 0.0,
        "new_pct": round(100.0 if total > 0 else 0.0, 1),
    }


# =============================================================================
# Endpoint
# =============================================================================

@router.get("/files/{file_id}/leverage")
async def get_file_leverage(
    file_id: int,
    file_repo: FileRepository = Depends(get_file_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async),
):
    """
    Get TM leverage statistics for a file.

    Returns counts and percentages of exact, fuzzy, and new matches
    against the active Translation Memories for the file's scope.
    """
    # Verify file exists
    file_data = await file_repo.get(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    # Get all rows for the file
    rows = await row_repo.get_all_for_file(file_id)
    total = len(rows) if rows else 0

    if total == 0:
        return _compute_leverage_no_tm(total=0)

    # Get active TMs for this file's scope
    active_tms = await tm_repo.get_active_for_file(file_id)
    if not active_tms:
        return _compute_leverage_no_tm(total=total)

    # Extract source texts for batch search
    source_texts = [r.get("source", "") or "" for r in rows]

    # Use TMSearcher for batch scoring
    try:
        from server.tools.ldm.indexing.searcher import TMSearcher
        from server.tools.ldm.indexing.indexer import TMIndexer

        # Load indexes for the first active TM
        tm_id = active_tms[0]["id"]
        indexer = TMIndexer(tm_id=tm_id)
        indexes = indexer.load_indexes()

        if not indexes:
            logger.warning(f"[LEVERAGE] No indexes for TM {tm_id}, returning all new")
            return _compute_leverage_no_tm(total=total)

        searcher = TMSearcher(indexes)
        batch_results = searcher.search_batch(source_texts, top_k=1)

        return _compute_leverage(batch_results, total=total)

    except Exception as e:
        logger.error(f"[LEVERAGE] Search failed for file {file_id}: {e}")
        # Graceful degradation: return all new
        return _compute_leverage_no_tm(total=total)
