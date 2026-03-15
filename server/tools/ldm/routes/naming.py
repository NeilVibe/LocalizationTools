"""Naming Coherence API endpoints -- similar names + AI naming suggestions.

Phase 21: AI Naming Coherence + Placeholders (Plan 01)

Provides REST endpoints for finding similar entity names via FAISS search
and generating AI-powered naming suggestions via Qwen3.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.naming import (
    NamingSimilarItem,
    NamingSimilarResponse,
    NamingSuggestionResponse,
)
from server.tools.ldm.services.naming_coherence_service import (
    NamingCoherenceService,
    get_naming_coherence_service,
)


router = APIRouter(prefix="/naming", tags=["LDM-Naming-Coherence"])

# Module-level singleton (lazy-initialized)
_naming_service: Optional[NamingCoherenceService] = None


def _get_naming_service() -> NamingCoherenceService:
    """Get or create the NamingCoherenceService singleton."""
    global _naming_service
    if _naming_service is None:
        _naming_service = get_naming_coherence_service()
    return _naming_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/similar/{entity_type}", response_model=NamingSimilarResponse)
async def get_similar_names(
    entity_type: str,
    name: str = Query(..., max_length=500, description="Entity name to search for"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Find similar entity names via CodexService FAISS search.

    Returns ranked list of existing entity names similar to the query.
    """
    svc = _get_naming_service()

    try:
        items = svc.find_similar_names(name=name, entity_type=entity_type, limit=limit)
        return NamingSimilarResponse(
            items=[NamingSimilarItem(**item) for item in items],
            count=len(items),
        )
    except Exception as e:
        logger.error(f"[Naming API] Similar names failed: {e}")
        return NamingSimilarResponse(items=[], count=0)


@router.get("/suggest/{entity_type}", response_model=NamingSuggestionResponse)
async def get_naming_suggestions(
    entity_type: str,
    name: str = Query(..., max_length=500, description="Entity name to get suggestions for"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get AI naming suggestions for an entity.

    Finds similar names first for context, then generates suggestions via Qwen3.
    Returns both suggestions and the similar names used as context.
    """
    svc = _get_naming_service()

    try:
        # Step 1: Find similar names for context
        similar_items = svc.find_similar_names(name=name, entity_type=entity_type, limit=10)

        # Step 2: Generate AI suggestions with similar names as context
        result = await svc.suggest_names(
            name=name,
            entity_type=entity_type,
            similar_names=similar_items,
        )

        return NamingSuggestionResponse(
            suggestions=[
                {"name": s["name"], "confidence": s["confidence"], "reasoning": s["reasoning"]}
                for s in result["suggestions"]
            ],
            status=result["status"],
            similar_names=[NamingSimilarItem(**item) for item in similar_items],
        )
    except Exception as e:
        logger.error(f"[Naming API] Suggestions failed: {e}")
        return NamingSuggestionResponse(suggestions=[], status="error", similar_names=[])


@router.get("/status")
async def get_naming_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get naming coherence service health (available, cache_size, model)."""
    svc = _get_naming_service()
    return svc.get_status()
