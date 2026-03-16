"""Codex API endpoints -- entity registry, search, detail, listing, AI image gen.

Phase 19: Game World Codex -- provides REST endpoints for the interactive
Codex encyclopedia with semantic search across all entity types.

Phase 31: AI Image Generation -- generate/serve/status endpoints for
Gemini-powered entity images. Plan 02 adds batch generation with
TrackedOperation progress and cancellation.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional

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
from server.utils.progress_tracker import TrackedOperation


router = APIRouter(prefix="/codex", tags=["Codex"])

# Module-level singleton (lazy-initialized on first request)
_codex_service: Optional[CodexService] = None

# Default base directory for StaticInfo
_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[4]  # project root

# Batch generation cancellation events keyed by operation_id
_cancel_events: Dict[int, asyncio.Event] = {}


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
        prompt = svc.build_prompt(entity)
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
        exc_str = str(exc).upper()
        if "SAFETY" in exc_str:
            raise HTTPException(status_code=422, detail="Content blocked by safety filter")
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
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
# Batch Generation Endpoints (Phase 31, Plan 02)
# =============================================================================


async def _run_batch_generation(
    entities: list,
    svc,
    operation_id: int,
    op,
    cancel_event: asyncio.Event,
):
    """Background task for sequential batch image generation."""
    total = len(entities)
    generated = 0
    failed = 0

    for i, entity in enumerate(entities):
        # Check cancellation before each generation
        if cancel_event.is_set():
            logger.info(f"[Codex API] Batch generation cancelled at {i}/{total}")
            op.update(
                (i / total) * 100,
                f"Cancelled after {generated} images",
                completed_steps=i,
                total_steps=total,
            )
            break

        try:
            prompt = svc.build_prompt(entity)
            png_bytes = await asyncio.to_thread(svc.generate_image, entity)
            svc.save_to_cache(entity.strkey, png_bytes, prompt)
            generated += 1
        except Exception as exc:
            logger.warning(
                f"[Codex API] Batch: failed to generate {entity.strkey}: {exc}"
            )
            failed += 1

        pct = ((i + 1) / total) * 100
        fail_suffix = f", {failed} failed" if failed > 0 else ""
        op.update(
            pct,
            f"Generated {generated}/{total}{fail_suffix}",
            completed_steps=i + 1,
            total_steps=total,
        )

        # Rate limit: 10 images per minute => 6 second delay between images
        if i < total - 1 and not cancel_event.is_set():
            await asyncio.sleep(6)

    logger.info(
        f"[Codex API] Batch generation done: {generated} generated, {failed} failed"
    )

    # Clean up cancel event
    _cancel_events.pop(operation_id, None)


@router.post("/batch-generate/{entity_type}")
async def batch_generate(
    entity_type: str,
    confirm: bool = Query(False, description="If false, returns preview. If true, starts batch."),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Batch generate AI images for all entities of a type missing cached images.

    Two-phase flow:
    - confirm=false: Returns count and estimated cost preview
    - confirm=true: Launches background batch generation with TrackedOperation
    """
    entity_type = entity_type.lower()
    svc = get_ai_image_service()
    codex = _get_codex_service()

    if not svc.available:
        raise HTTPException(
            status_code=503,
            detail="AI image generation unavailable (GEMINI_API_KEY not set)",
        )

    # Get all entities and filter to those without cached images
    list_response = codex.list_entities(entity_type)
    all_entities = list_response.entities
    to_generate = [e for e in all_entities if not svc.get_cached_image_path(e.strkey)]

    if not confirm:
        # Preview mode: return count and cost estimate
        return {
            "to_generate": len(to_generate),
            "estimated_cost": f"~${len(to_generate) * 0.05:.2f}",
            "entity_type": entity_type,
            "total_entities": len(all_entities),
        }

    if len(to_generate) == 0:
        return {"status": "complete", "to_generate": 0, "message": "All entities already have images"}

    # Start batch generation with TrackedOperation
    user_id = current_user.get("user_id", 0)
    tracked = TrackedOperation(
        f"AI Image Generation ({entity_type})",
        user_id,
        username=current_user.get("username", "system"),
        tool_name="Codex",
        function_name="batch_generate",
        total_steps=len(to_generate),
    )
    op = tracked.__enter__()
    if tracked.operation_id is None:
        tracked.__exit__(None, None, None)
        raise HTTPException(503, "Operation tracking unavailable")
    operation_id = tracked.operation_id

    # Create cancellation event
    cancel_event = asyncio.Event()
    _cancel_events[operation_id] = cancel_event

    # Launch background task
    async def _batch_wrapper():
        try:
            await _run_batch_generation(to_generate, svc, operation_id, op, cancel_event)
            tracked.__exit__(None, None, None)
        except Exception as exc:
            tracked.__exit__(type(exc), exc, exc.__traceback__)

    asyncio.create_task(_batch_wrapper())

    return {
        "status": "started",
        "operation_id": operation_id,
        "to_generate": len(to_generate),
    }


@router.post("/batch-generate/cancel/{operation_id:int}")
async def cancel_batch_generate(
    operation_id: int,
    current_user: dict = Depends(get_current_active_user_async),
):
    """Cancel a running batch generation operation."""
    cancel_event = _cancel_events.get(operation_id)
    if cancel_event is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active batch operation with id {operation_id}",
        )

    cancel_event.set()
    return {"status": "cancelling", "operation_id": operation_id}


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
        raise HTTPException(status_code=500, detail=str(e))


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
    offset: int = Query(0, ge=0, description="Skip N entities"),
    limit: int = Query(50, ge=1, le=200, description="Max entities per page"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """List entities of a given type with pagination.

    Returns paginated results with total count and has_more flag.
    Default: 50 entities per page starting from offset 0.
    """
    entity_type = entity_type.lower()
    svc = _get_codex_service()

    try:
        return svc.list_entities(entity_type, offset=offset, limit=limit)
    except Exception as e:
        logger.error(f"[Codex API] list_entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))
