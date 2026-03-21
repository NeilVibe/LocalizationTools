"""
Phase 45: MegaIndex API - Status, build trigger, entity lookup, and counts.

Exposes MegaIndex state to the frontend and provides endpoints for
triggering builds and looking up individual entities.

Endpoints:
- GET  /mega/status              -> dict sizes, build_time, built status
- POST /mega/build               -> trigger build, return stats
- GET  /mega/entity/{type}/{key} -> single entity lookup (404 if missing)
- GET  /mega/counts              -> entity type counts
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from loguru import logger

from ..services.mega_index import get_mega_index

router = APIRouter(prefix="/mega", tags=["mega_index"])


class BuildRequest(BaseModel):
    """Optional body for build endpoint."""

    preload_langs: Optional[List[str]] = None


@router.get("/status")
async def mega_status():
    """
    Get MegaIndex status without triggering a build.

    Returns dict sizes, build_time, and built status.
    """
    mi = get_mega_index()
    return mi.stats()


@router.post("/build")
async def mega_build(body: Optional[BuildRequest] = None):
    """
    Trigger MegaIndex build and return stats after completion.

    Optionally specify preload_langs (defaults to ["eng", "kor"]).
    """
    mi = get_mega_index()
    preload_langs = body.preload_langs if body and body.preload_langs else None
    logger.info(f"[MEGAINDEX] Build triggered via API, langs={preload_langs}")
    mi.build(preload_langs=preload_langs)
    return mi.stats()


@router.get("/entity/{entity_type}/{strkey}")
async def mega_entity(entity_type: str, strkey: str):
    """
    Look up a single entity by type and StrKey.

    Returns entity data as JSON dict. Returns 404 if not found.
    """
    mi = get_mega_index()
    entity = mi.get_entity(entity_type, strkey)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_type}/{strkey}",
        )
    return dataclasses.asdict(entity)


@router.get("/counts")
async def mega_counts():
    """
    Get entity type counts.

    Does not trigger a build -- returns current state.
    """
    mi = get_mega_index()
    return mi.entity_counts()
