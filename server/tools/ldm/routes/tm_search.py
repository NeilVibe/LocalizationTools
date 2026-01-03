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
from server.tools.ldm.permissions import can_access_tm

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
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Get Translation Memory suggestions for a source text.

    If tm_id is provided, searches the Translation Memory entries.
    Otherwise, searches within project rows for similar texts.

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
    # ENHANCED DEBUG LOGGING
    logger.info(f"[TM-SUGGEST] START | source='{source[:50]}...' | tm_id={tm_id} | file_id={file_id} | threshold={threshold}")

    try:
        sql_params = {
            'search_text': source.strip(),
            'threshold': threshold,
            'max_results': max_results
        }
        logger.debug(f"[TM-SUGGEST] SQL params: {sql_params}")

        # If tm_id is provided, search the TM entries table
        if tm_id:
            logger.info(f"[TM-SUGGEST] MODE: TM entries search (tm_id={tm_id})")
            # DESIGN-001: Use permission helper for TM access check
            logger.debug(f"[TM-SUGGEST] Verifying TM access for user_id={current_user['user_id']}")
            if not await can_access_tm(db, tm_id, current_user):
                logger.warning(f"[TM-SUGGEST] TM {tm_id} not accessible by user {current_user['user_id']}")
                raise HTTPException(status_code=404, detail="Translation Memory not found")

            tm_result = await db.execute(
                select(LDMTranslationMemory).where(LDMTranslationMemory.id == tm_id)
            )
            tm = tm_result.scalar_one_or_none()
            if not tm:
                logger.warning(f"[TM-SUGGEST] TM {tm_id} not found")
                raise HTTPException(status_code=404, detail="Translation Memory not found")

            logger.debug(f"[TM-SUGGEST] TM verified: name='{tm.name}', entries={tm.entry_count}, status={tm.status}")
            sql_params['tm_id'] = tm_id

            # Search TM entries with pg_trgm similarity
            logger.debug(f"[TM-SUGGEST] Executing TM entry search with pg_trgm...")
            sql = text("""
                SELECT
                    e.id,
                    e.source_text as source,
                    e.target_text as target,
                    e.tm_id,
                    similarity(lower(e.source_text), lower(:search_text)) as sim
                FROM ldm_tm_entries e
                WHERE e.tm_id = :tm_id
                  AND e.target_text IS NOT NULL
                  AND e.target_text != ''
                  AND similarity(lower(e.source_text), lower(:search_text)) >= :threshold
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
                    'entry_id': row.id,
                    'tm_id': row.tm_id,
                    'file_name': 'TM'  # Mark as from TM
                }
                for row in rows
            ]

            logger.info(f"[TM-SUGGEST] SUCCESS | Found {len(suggestions)} matches from TM {tm_id}")
            for i, s in enumerate(suggestions[:3]):  # Log first 3
                logger.debug(f"[TM-SUGGEST] Match {i+1}: sim={s['similarity']:.2f} | src='{s['source'][:30]}...'")
            return {"suggestions": suggestions, "count": len(suggestions)}

        # Otherwise, search project rows (original behavior)
        logger.info(f"[TM-SUGGEST] MODE: Project rows search (no tm_id)")
        conditions = ["r.target IS NOT NULL", "r.target != ''"]
        if file_id:
            conditions.append("r.file_id = :file_id")
            sql_params['file_id'] = file_id
            logger.debug(f"[TM-SUGGEST] Filter: file_id={file_id}")
        elif project_id:
            conditions.append("f.project_id = :project_id")
            sql_params['project_id'] = project_id
            logger.debug(f"[TM-SUGGEST] Filter: project_id={project_id}")
        if exclude_row_id:
            conditions.append("r.id != :exclude_row_id")
            sql_params['exclude_row_id'] = exclude_row_id

        where_clause = " AND ".join(conditions)

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

        logger.info(f"[TM-SUGGEST] SUCCESS | Found {len(suggestions)} matches from project rows")
        for i, s in enumerate(suggestions[:3]):  # Log first 3
            logger.debug(f"[TM-SUGGEST] Match {i+1}: sim={s['similarity']:.2f} | file='{s['file_name']}' | src='{s['source'][:30]}...'")
        return {"suggestions": suggestions, "count": len(suggestions)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TM-SUGGEST] ERROR | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="TM search failed. Check server logs.")


@router.get("/tm/{tm_id}/search/exact")
async def search_tm_exact(
    tm_id: int,
    source: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    """
    Search for exact match in a Translation Memory (DESIGN-001: Public by default).

    Uses hash-based O(1) lookup for maximum speed.
    """
    logger.info(f"TM exact search: tm_id={tm_id}, source={source[:30]}...")

    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
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
    Search a Translation Memory using LIKE pattern (DESIGN-001: Public by default).

    For fuzzy/similar text searching (not exact match).
    """
    logger.info(f"TM search: tm_id={tm_id}, pattern={pattern[:30]}...")

    # DESIGN-001: Use permission helper for TM access check
    if not await can_access_tm(db, tm_id, current_user):
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
