"""Gimmick Codex API endpoints -- bulk list, detail.

Phase 102: Codex Overhaul -- Gimmick Codex.

Endpoints:
  GET /codex/gimmicks           - Bulk gimmick list with search filtering
  GET /codex/gimmicks/{strkey}  - Full gimmick detail
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_gimmicks import (
    GimmickCardResponse,
    GimmickDetailResponse,
    GimmickListResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index

router = APIRouter(prefix="/codex/gimmicks", tags=["Codex Gimmicks"])


def _build_gimmick_card(strkey: str, mega, lang: str) -> Optional[GimmickCardResponse]:
    entry = mega.get_gimmick(strkey)
    if entry is None:
        return None
    name_translated = ""
    stringids = mega.entity_strkey_to_stringids.get(strkey, set())
    for sid in stringids:
        trans = mega.stringid_to_translations.get(sid, {})
        if lang in trans:
            name_translated = trans[lang]
            break
    image_urls = [str(p) for p in mega.get_image_paths(strkey)]
    return GimmickCardResponse(
        strkey=entry.strkey,
        name_kr=entry.name,
        name_translated=name_translated,
        desc_kr=entry.desc,
        seal_desc=entry.seal_desc,
        image_urls=image_urls,
        source_file=entry.source_file,
    )


@router.get("/{strkey}", response_model=GimmickDetailResponse)
async def get_gimmick_detail(strkey: str, lang: str = Query("eng"), user=Depends(get_current_active_user_async)):
    """Get full gimmick detail by StrKey."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")
    entry = mega.get_gimmick(strkey.lower())
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Gimmick not found: {strkey}")
    card = _build_gimmick_card(strkey.lower(), mega, lang)
    return GimmickDetailResponse(
        **(card.model_dump() if card else {}),
        knowledge_pass_0=[],
        knowledge_pass_1=[],
        knowledge_pass_2=[],
        related_entities=[],
    )


@router.get("", response_model=GimmickListResponse)
async def list_gimmicks(
    q: Optional[str] = Query(None, description="Search query"),
    lang: str = Query("eng"),
    user=Depends(get_current_active_user_async),
):
    """Bulk load all gimmicks with optional search filtering."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")

    cards = []
    for strkey, entry in mega.gimmick_by_strkey.items():
        card = _build_gimmick_card(strkey, mega, lang)
        if card:
            if q:
                q_lower = q.lower()
                searchable = f"{card.name_kr} {card.name_translated} {card.strkey} {card.desc_kr} {card.seal_desc}".lower()
                if q_lower not in searchable:
                    continue
            cards.append(card)

    cards.sort(key=lambda c: c.name_kr)
    return GimmickListResponse(items=cards, total=len(cards))
