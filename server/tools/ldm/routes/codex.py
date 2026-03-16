"""Codex API endpoints -- entity registry, search, detail, listing.

Phase 19: Game World Codex -- provides REST endpoints for the interactive
Codex encyclopedia with semantic search across all entity types.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex import (
    CodexEntity,
    CodexListResponse,
    CodexSearchResponse,
)
from server.tools.ldm.services.codex_service import CodexService


router = APIRouter(prefix="/codex", tags=["Codex"])

# Module-level singleton (lazy-initialized on first request)
_codex_service: Optional[CodexService] = None

# Default base directory for StaticInfo
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root


def _get_codex_service() -> CodexService:
    """Get or create the CodexService singleton."""
    global _codex_service
    if _codex_service is None:
        # Check for mock_gamedata first (Phase 15)
        mock_dir = _DEFAULT_BASE_DIR / "tests" / "fixtures" / "mock_gamedata" / "StaticInfo"
        if mock_dir.is_dir():
            base_dir = mock_dir
        else:
            base_dir = _DEFAULT_BASE_DIR / "StaticInfo"

        logger.info(f"[Codex API] Initializing CodexService from {base_dir}")
        _codex_service = CodexService(base_dir=base_dir)

    return _codex_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/search", response_model=CodexSearchResponse)
async def search_codex(
    q: str = Query(..., description="Search query string"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Search the Codex encyclopedia via semantic search.

    Returns ranked results across all entity types (or filtered to one type).
    """
    if entity_type is not None:
        entity_type = entity_type.lower()

    svc = _get_codex_service()

    try:
        return svc.search(query=q, entity_type=entity_type, limit=limit)
    except Exception as e:
        logger.error(f"[Codex API] Search failed: {e}")
        return CodexSearchResponse(results=[], count=0, search_time_ms=0.0)


@router.get("/entity/{entity_type}/{strkey}", response_model=CodexEntity)
async def get_codex_entity(
    entity_type: str,
    strkey: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get a single Codex entity by type and StrKey.

    Returns 404 if entity not found.
    """
    entity_type = entity_type.lower()
    svc = _get_codex_service()

    try:
        entity = svc.get_entity(entity_type, strkey)
    except Exception as e:
        logger.error(f"[Codex API] get_entity failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_type}/{strkey}",
        )

    return entity


@router.get("/list/{entity_type}", response_model=CodexListResponse)
async def list_codex_entities(
    entity_type: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """List all entities of a given type.

    Returns empty list for unknown entity types (graceful).
    """
    entity_type = entity_type.lower()
    svc = _get_codex_service()

    try:
        return svc.list_entities(entity_type)
    except Exception as e:
        logger.error(f"[Codex API] list_entities failed: {e}")
        return CodexListResponse(entities=[], entity_type=entity_type, count=0)


@router.get("/types")
async def get_codex_types(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get available entity types with their counts.

    Returns dict of entity_type -> count.
    """
    svc = _get_codex_service()

    try:
        return svc.get_entity_types()
    except Exception as e:
        logger.error(f"[Codex API] get_entity_types failed: {e}")
        return {}
