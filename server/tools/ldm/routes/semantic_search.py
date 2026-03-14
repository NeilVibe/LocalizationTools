"""
Semantic Search endpoint - Model2Vec powered "find similar" search.

Uses TMSearcher 5-Tier Cascade for semantic matching:
- Tier 1: Perfect hash match
- Tier 2: Whole embedding match (FAISS + Model2Vec)
- Tier 3: Perfect line match (hash)
- Tier 4: Line embedding match (FAISS + Model2Vec)
- Tier 5: N-gram fallback

Phase 4: Search and AI Differentiators
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.repositories import TMRepository, get_tm_repository
from server.tools.ldm.indexing.indexer import TMIndexer
from server.tools.ldm.indexing.searcher import TMSearcher

router = APIRouter(tags=["LDM"])


@router.get("/semantic-search")
async def semantic_search(
    query: str = Query(..., min_length=1, description="Search query text"),
    tm_id: int = Query(..., description="Translation Memory ID to search"),
    threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    tm_repo: TMRepository = Depends(get_tm_repository),
    current_user: dict = Depends(get_current_active_user_async),
):
    """
    Semantic search across a Translation Memory using Model2Vec embeddings.

    Finds translations by meaning, not just exact text matching.
    Uses the 5-Tier Cascade search (hash -> FAISS -> n-gram fallback).

    Returns results ranked by similarity descending with timing info.
    """
    logger.info(f"[SEMANTIC-SEARCH] START | query='{query[:50]}' | tm_id={tm_id} | threshold={threshold} | max_results={max_results}")

    start_time = time.time()

    # Validate TM exists
    tm = await tm_repo.get(tm_id)
    if not tm:
        logger.warning(f"[SEMANTIC-SEARCH] TM {tm_id} not found")
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Load TM indexes
    try:
        indexer = TMIndexer(db=None)
        indexes = indexer.load_indexes(tm_id)
    except FileNotFoundError:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.warning(f"[SEMANTIC-SEARCH] No indexes built for TM {tm_id}")
        return {
            "results": [],
            "count": 0,
            "search_time_ms": round(elapsed_ms, 2),
            "index_status": "not_built",
        }
    except RuntimeError as e:
        logger.error(f"[SEMANTIC-SEARCH] Index load error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load TM indexes. Try rebuilding indexes for TM {tm_id}.",
        )

    # Create searcher with Model2Vec ONLY (per locked decision)
    # TMSearcher auto-loads model2vec via get_current_engine_name() when needed
    searcher = TMSearcher(indexes, threshold=threshold)

    # Execute search
    try:
        search_result = searcher.search(query, top_k=max_results, threshold=threshold)
    except RuntimeError as e:
        logger.error(f"[SEMANTIC-SEARCH] Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Semantic search failed. Check if indexes need rebuilding.",
        )

    elapsed_ms = (time.time() - start_time) * 1000

    # Transform results to response format
    tier = search_result.get("tier", 0)
    tier_name = search_result.get("tier_name", "no_match")
    raw_results = search_result.get("results", [])

    results = []
    for r in raw_results:
        results.append({
            "source_text": r.get("source_text") or r.get("source_line", ""),
            "target_text": r.get("target_text") or r.get("target_line", ""),
            "similarity": float(r.get("score", 0.0)),
            "match_type": r.get("match_type", "unknown"),
            "tier": tier,
            "string_id": r.get("string_id"),
            "entry_id": r.get("entry_id"),
        })

    # Ensure results are sorted by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)

    logger.info(
        f"[SEMANTIC-SEARCH] DONE | tm_id={tm_id} | tier={tier} ({tier_name}) | "
        f"results={len(results)} | time={elapsed_ms:.1f}ms"
    )

    return {
        "results": results,
        "count": len(results),
        "search_time_ms": round(elapsed_ms, 2),
    }
