"""Codex API endpoints -- entity registry, search, detail, listing, AI image gen.

Phase 19: Game World Codex -- provides REST endpoints for the interactive
Codex encyclopedia with semantic search across all entity types.

Phase 31: AI Image Generation -- generate/serve/status endpoints for
Gemini-powered entity images.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex import (
    CodexEntity,
    CodexListResponse,
    CodexSearchResponse,
)
from server.tools.ldm.services.codex_service import CodexService
from server.tools.ldm.services.ai_image_service import get_ai_image_service


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
# AI Image Generation Endpoints (Phase 31)
# =============================================================================


@router.get("/image-gen/status")
async def image_gen_status(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Check if AI image generation is available.

    Returns available=false when GEMINI_API_KEY is not set.
    """
    svc = get_ai_image_service()
    return {"available": svc.available}


@router.post("/generate-image/{entity_type}/{strkey}")
async def generate_image(
    entity_type: str,
    strkey: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Generate an AI image for a single Codex entity.

    Returns the URL to the generated image. Skips generation if already cached
    (unless force=true).
    """
    entity_type = entity_type.lower()
    svc = get_ai_image_service()
    codex = _get_codex_service()

    # Check availability
    if not svc.available:
        raise HTTPException(
            status_code=503,
            detail="AI image generation unavailable (GEMINI_API_KEY not set)",
        )

    # Get entity
    entity = codex.get_entity(entity_type, strkey)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_type}/{strkey}",
        )

    # Check cache (skip generation if cached and not forced)
    if not force:
        cached = svc.get_cached_image_path(strkey)
        if cached:
            return {
                "status": "cached",
                "image_url": f"/api/ldm/codex/image/{strkey}",
            }

    # Generate via Gemini (sync call wrapped in thread)
    try:
        prompt = svc._build_prompt(entity)
        png_bytes = await asyncio.to_thread(svc.generate_image, entity)
        svc.save_to_cache(strkey, png_bytes, prompt)

        return {
            "status": "generated",
            "image_url": f"/api/ldm/codex/image/{strkey}",
        }
    except ValueError as exc:
        logger.error(f"[Codex API] Image generation failed for {entity_type}/{strkey}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Codex API] Unexpected error generating image for {entity_type}/{strkey}: {exc}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}")


@router.get("/image/{strkey}")
async def get_codex_image(
    strkey: str,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Serve a cached AI-generated image for a Codex entity.

    Returns PNG bytes with 7-day browser cache headers.
    """
    svc = get_ai_image_service()
    cached = svc.get_cached_image_path(strkey)

    if not cached:
        raise HTTPException(
            status_code=404,
            detail=f"No generated image for entity: {strkey}",
        )

    png_bytes = cached.read_bytes()
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800"},
    )


# =============================================================================
# Existing Endpoints
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

    Returns 404 if entity not found. Enriches with ai_image_url if cached.
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

    # Enrich with AI image URL if cached
    img_svc = get_ai_image_service()
    if img_svc.get_cached_image_path(entity.strkey):
        entity.ai_image_url = f"/api/ldm/codex/image/{entity.strkey}"

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
