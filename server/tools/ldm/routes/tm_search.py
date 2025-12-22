"""
TM Search endpoints - Suggest, exact search, pattern search.

Migrated from api.py lines 1093-1189, 1723-1818
"""

import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from loguru import logger

from server.utils.dependencies import get_async_db, get_current_active_user_async
from server.database.db_utils import normalize_text_for_hash
from server.database.models import LDMTranslationMemory, LDMTMEntry
from server.tools.ldm.schemas import TMSuggestResponse

router = APIRouter(tags=["LDM"])


@router.get("/tm/suggest", response_model=TMSuggestResponse)
async def get_tm_suggestions(
    source: str,
    file_id: Optional[int] = None,
    project_id: Optional[int] = None,
    exclude_row_id: Optional[int] = None,
    threshold: float = Query(0.70, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)"),
    max_results: int = Query(5, ge=1, le=50, description="Maximum suggestions to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get Translation Memory suggestions for a source text.

    Finds similar source texts in the database and returns their translations.

    Args:
        source: Korean source text to find matches for
        file_id: Optional - limit search to same file
        project_id: Optional - limit search to same project
        exclude_row_id: Optional - exclude this row from results
        threshold: Minimum similarity (0.0-1.0, default 0.70)
        max_results: Maximum suggestions (default 5)

    Returns:
        List of TM suggestions with source, target, similarity, etc.
    """
    logger.info(f"TM suggest: source={source[:30]}..., file={file_id}, project={project_id}")

    try:
        # Use PostgreSQL pg_trgm similarity() for efficient fuzzy matching
        # This is O(log n) with GIN index vs O(n) Python loop
        sql_params = {
            'search_text': source.strip(),
            'threshold': threshold,
            'max_results': max_results
        }

        # Base conditions - use parameterized queries (NO f-strings for SQL!)
        conditions = ["r.target IS NOT NULL", "r.target != ''"]
        if file_id:
            conditions.append("r.file_id = :file_id")
            sql_params['file_id'] = file_id
        elif project_id:
            conditions.append("f.project_id = :project_id")
            sql_params['project_id'] = project_id
        if exclude_row_id:
            conditions.append("r.id != :exclude_row_id")
            sql_params['exclude_row_id'] = exclude_row_id

        where_clause = " AND ".join(conditions)

        # Use pg_trgm similarity() for fuzzy matching
        # Falls back to exact match if pg_trgm not available
        sql = text(f"""
            SELECT
                r.id,
                r.source,
                r.target,
                r.file_id,
                f.name as file_name,
                similarity(lower(r.source), lower(:search_text)) as sim
            FROM ldm_rows r
            JOIN ldm_files f ON r.file_id = f.id
            WHERE {where_clause}
              AND similarity(lower(r.source), lower(:search_text)) >= :threshold
            ORDER BY sim DESC
            LIMIT :max_results
        """)

        result = await db.execute(sql, sql_params)
        rows = result.fetchall()

        suggestions = [
            {
                'source': row.source,
                'target': row.target,
                'similarity': round(float(row.sim), 3),
                'row_id': row.id,
                'file_name': row.file_name
            }
            for row in rows
        ]

        logger.info(f"TM found {len(suggestions)} suggestions (pg_trgm)")
        return {"suggestions": suggestions, "count": len(suggestions)}

    except Exception as e:
        logger.error(f"TM suggest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM search failed. Check server logs.")


@router.get("/tm/{tm_id}/search/exact")
async def search_tm_exact(
    tm_id: int,
    source: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search for exact match in a Translation Memory.

    Uses hash-based O(1) lookup for maximum speed.
    """
    logger.info(f"TM exact search: tm_id={tm_id}, source={source[:30]}...")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not tm_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Generate hash for O(1) lookup (async query)
    normalized = normalize_text_for_hash(source)
    source_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    entry_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_hash == source_hash
        )
    )
    entry = entry_result.scalar_one_or_none()

    if entry:
        return {
            "match": {
                "source_text": entry.source_text,
                "target_text": entry.target_text,
                "similarity": 1.0,
                "tier": 1,
                "strategy": "perfect_whole_match"
            },
            "found": True
        }
    return {"match": None, "found": False}


@router.get("/tm/{tm_id}/search")
async def search_tm(
    tm_id: int,
    pattern: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search a Translation Memory using LIKE pattern.

    For fuzzy/similar text searching (not exact match).
    """
    logger.info(f"TM search: tm_id={tm_id}, pattern={pattern[:30]}...")

    # Verify TM ownership (async)
    tm_result = await db.execute(
        select(LDMTranslationMemory).where(
            LDMTranslationMemory.id == tm_id,
            LDMTranslationMemory.owner_id == current_user["user_id"]
        )
    )
    if not tm_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Translation Memory not found")

    # Async LIKE search
    entries_result = await db.execute(
        select(LDMTMEntry).where(
            LDMTMEntry.tm_id == tm_id,
            LDMTMEntry.source_text.ilike(f"%{pattern}%")
        ).limit(limit)
    )
    entries = entries_result.scalars().all()

    results = [
        {
            "source_text": e.source_text,
            "target_text": e.target_text,
            "similarity": 0.0,  # LIKE doesn't provide similarity
            "tier": 0,
            "strategy": "like_search"
        }
        for e in entries
    ]
    return {"results": results, "count": len(results)}
