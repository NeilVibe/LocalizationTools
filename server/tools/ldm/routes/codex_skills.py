"""Skill Codex API endpoints -- bulk list, detail.

Phase 102: Codex Overhaul -- Skill Codex.

Endpoints:
  GET /codex/skills           - Bulk skill list with search filtering
  GET /codex/skills/{strkey}  - Full skill detail
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_skills import (
    SkillCardResponse,
    SkillDetailResponse,
    SkillListResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index

router = APIRouter(prefix="/codex/skills", tags=["Codex Skills"])


def _build_skill_card(strkey: str, mega, lang: str) -> Optional[SkillCardResponse]:
    entry = mega.get_skill(strkey)
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
    return SkillCardResponse(
        strkey=entry.strkey,
        name_kr=entry.name,
        name_translated=name_translated,
        desc_kr=entry.desc,
        image_urls=image_urls,
        source_file=entry.source_file,
    )


@router.get("/{strkey}", response_model=SkillDetailResponse)
async def get_skill_detail(strkey: str, lang: str = Query("eng"), user=Depends(get_current_active_user_async)):
    """Get full skill detail by StrKey."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")
    entry = mega.get_skill(strkey.lower())
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {strkey}")
    card = _build_skill_card(strkey.lower(), mega, lang)
    return SkillDetailResponse(
        **(card.model_dump() if card else {}),
        learn_knowledge_key=entry.learn_knowledge_key,
        knowledge_pass_0=[],
        knowledge_pass_1=[],
        knowledge_pass_2=[],
        related_entities=[],
    )


@router.get("", response_model=SkillListResponse)
async def list_skills(
    q: Optional[str] = Query(None, description="Search query"),
    lang: str = Query("eng"),
    user=Depends(get_current_active_user_async),
):
    """Bulk load all skills with optional search filtering."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")

    cards = []
    for strkey, entry in mega.skill_by_strkey.items():
        card = _build_skill_card(strkey, mega, lang)
        if card:
            if q:
                q_lower = q.lower()
                searchable = f"{card.name_kr} {card.name_translated} {card.strkey} {card.desc_kr}".lower()
                if q_lower not in searchable:
                    continue
            cards.append(card)

    cards.sort(key=lambda c: c.name_kr)
    return SkillListResponse(items=cards, total=len(cards))
