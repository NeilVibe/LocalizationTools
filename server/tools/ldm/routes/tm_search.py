"""
TM Search endpoints - Suggest, exact search, pattern search.

P10: FULL ABSTRACT + REPO Pattern
- All endpoints use Repository Pattern with permissions baked in
- No direct DB access in routes

Migrated from api.py lines 1093-1189, 1723-1818
Note: Similarity search (pg_trgm) is PostgreSQL-specific, returns empty in offline
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.repositories import TMRepository, RowRepository, get_tm_repository, get_row_repository
from server.tools.ldm.schemas import TMSuggestResponse

router = APIRouter(tags=["LDM"])


@router.get("/tm/suggest", response_model=TMSuggestResponse)
async def get_tm_suggestions(
    source: str,
    tm_id: Optional[int] = None,
    file_id: Optional[int] = None,
    project_id: Optional[int] = None,
    exclude_row_id: Optional[int] = None,
    threshold: float = Query(0.50, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)"),
    max_results: int = Query(5, ge=1, le=50, description="Maximum suggestions to return"),
    tm_repo: TMRepository = Depends(get_tm_repository),
    row_repo: RowRepository = Depends(get_row_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get Translation Memory suggestions for a source text.

    If tm_id is provided, searches the Translation Memory entries.
    Otherwise, searches within project rows for similar texts.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.

    Args:
        source: Korean source text to find matches for
        tm_id: Optional - search in specific Translation Memory
        file_id: Optional - limit search to same file (if no tm_id)
        project_id: Optional - limit search to same project (if no tm_id)
        exclude_row_id: Optional - exclude this row from results
        threshold: Minimum similarity (0.0-1.0, default 0.50)
        max_results: Maximum suggestions (default 5)

    Returns:
        List of TM suggestions with source, target, similarity, etc.
    """
    logger.info(f"[TM-SEARCH] [TM-SUGGEST] START | source='{source[:50]}...' | tm_id={tm_id} | file_id={file_id} | threshold={threshold}")

    try:
        # If tm_id is provided, search the TM entries table
        if tm_id:
            logger.info(f"[TM-SEARCH] [TM-SUGGEST] MODE: TM entries search (tm_id={tm_id})")

            # P10: Get TM via repository (permissions checked inside - returns None if no access)
            tm = await tm_repo.get(tm_id)
            if not tm:
                logger.warning(f"[TM-SEARCH] [TM-SUGGEST] TM {tm_id} not found or not accessible")
                raise HTTPException(status_code=404, detail="Translation Memory not found")

            logger.debug(f"[TM-SEARCH] [TM-SUGGEST] TM verified: name='{tm.get('name')}', entries={tm.get('entry_count')}")

            # Search TM entries with pg_trgm similarity via repository
            suggestions = await tm_repo.search_similar(
                tm_id=tm_id,
                source=source,
                threshold=threshold,
                max_results=max_results
            )

            # P11-B: Add tm_name to each suggestion for UI display
            tm_name = tm.get('name', 'Unknown TM')
            for s in suggestions:
                s['tm_name'] = tm_name

            logger.info(f"[TM-SEARCH] [TM-SUGGEST] SUCCESS | Found {len(suggestions)} matches from TM '{tm_name}'")
            for i, s in enumerate(suggestions[:3]):
                logger.debug(f"[TM-SEARCH] [TM-SUGGEST] Match {i+1}: sim={s['similarity']:.2f} | src='{s['source'][:30]}...'")
            return {"suggestions": suggestions, "count": len(suggestions)}

        # Otherwise, search project rows via repository
        logger.info(f"[TM-SEARCH] [TM-SUGGEST] MODE: Project rows search (no tm_id)")

        suggestions = await row_repo.suggest_similar(
            source=source,
            file_id=file_id,
            project_id=project_id,
            exclude_row_id=exclude_row_id,
            threshold=threshold,
            max_results=max_results
        )

        logger.info(f"[TM-SEARCH] [TM-SUGGEST] SUCCESS | Found {len(suggestions)} matches from project rows")
        for i, s in enumerate(suggestions[:3]):
            logger.debug(f"[TM-SEARCH] [TM-SUGGEST] Match {i+1}: sim={s['similarity']:.2f} | file='{s['file_name']}' | src='{s['source'][:30]}...'")
        return {"suggestions": suggestions, "count": len(suggestions)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TM-SEARCH] [TM-SUGGEST] ERROR | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM search failed. Check server logs.")


@router.get("/tm/{tm_id}/search/exact")
async def search_tm_exact(
    tm_id: int,
    source: str,
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search for exact match in a Translation Memory (DESIGN-001: Public by default).

    Uses hash-based O(1) lookup for maximum speed.

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    logger.info(f"[TM-SEARCH] TM exact search: tm_id={tm_id}, source={source[:30]}...")

    # P10: Get TM via repository (permissions checked inside - returns None if no access)
    tm = await tm_repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Search via repository (handles hash generation internally)
    match = await tm_repo.search_exact(tm_id, source)

    if match:
        return {"match": match, "found": True}
    return {"match": None, "found": False}


@router.get("/tm/{tm_id}/search")
async def search_tm(
    tm_id: int,
    pattern: str,
    limit: int = Query(10, ge=1, le=100),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search a Translation Memory using LIKE pattern (DESIGN-001: Public by default).

    For fuzzy/similar text searching (not exact match).

    P10: FULL ABSTRACT - Permission check is INSIDE repository.
    """
    logger.info(f"[TM-SEARCH] TM search: tm_id={tm_id}, pattern={pattern[:30]}...")

    # P10: Get TM via repository (permissions checked inside - returns None if no access)
    tm = await tm_repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Search via repository (uses existing search_entries method)
    entries = await tm_repo.search_entries(tm_id, pattern, limit)

    results = [
        {
            "source_text": e.get("source_text"),
            "target_text": e.get("target_text"),
            "similarity": 0.0,  # LIKE doesn't provide similarity
            "tier": 0,
            "strategy": "like_search"
        }
        for e in entries
    ]
    return {"results": results, "count": len(results)}
