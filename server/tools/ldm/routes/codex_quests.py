"""Quest Codex API endpoints -- bulk list, type filtering, detail.

Phase 102: Codex Overhaul -- Quest Codex (QACompiler graft).

Endpoints:
  GET /codex/quests           - Bulk quest list with type/search filtering
  GET /codex/quests/types     - Quest type breakdown with counts
  GET /codex/quests/{strkey}  - Full quest detail
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_quests import (
    QuestCardResponse,
    QuestDetailResponse,
    QuestListResponse,
    QuestTypeItem,
    QuestTypeResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index

router = APIRouter(prefix="/codex/quests", tags=["Codex Quests"])


def _build_quest_card(strkey: str, mega, lang: str) -> Optional[QuestCardResponse]:
    entry = mega.get_quest(strkey)
    if entry is None:
        return None
    # Translation lookup
    name_translated = ""
    stringids = mega.entity_strkey_to_stringids.get(strkey, set())
    for sid in stringids:
        trans = mega.stringid_to_translations.get(sid, {})
        if lang in trans:
            name_translated = trans[lang]
            break
    # Image lookup (greedy scan)
    image_urls = [str(p) for p in mega.get_image_paths(strkey)]
    return QuestCardResponse(
        strkey=entry.strkey,
        name_kr=entry.name,
        name_translated=name_translated,
        desc_kr=entry.desc,
        quest_type=entry.quest_type,
        quest_subtype=entry.quest_subtype,
        faction_key=entry.faction_key,
        image_urls=image_urls,
        source_file=entry.source_file,
    )


@router.get("/types", response_model=QuestTypeResponse)
async def get_quest_types(user=Depends(get_current_active_user_async)):
    """Get quest type breakdown with counts."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")
    type_counts = {}
    for entry in mega.quest_by_strkey.values():
        qt = entry.quest_type or "unknown"
        type_counts[qt] = type_counts.get(qt, 0) + 1
    types = [QuestTypeItem(quest_type=k, count=v) for k, v in sorted(type_counts.items())]
    return QuestTypeResponse(types=types, total_quests=len(mega.quest_by_strkey))


@router.get("/{strkey}", response_model=QuestDetailResponse)
async def get_quest_detail(strkey: str, lang: str = Query("eng"), user=Depends(get_current_active_user_async)):
    """Get full quest detail by StrKey."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")
    entry = mega.get_quest(strkey.lower())
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Quest not found: {strkey}")
    card = _build_quest_card(strkey.lower(), mega, lang)
    return QuestDetailResponse(
        **(card.model_dump() if card else {}),
        knowledge_pass_0=[],
        knowledge_pass_1=[],
        knowledge_pass_2=[],
        related_entities=[],
    )


@router.get("", response_model=QuestListResponse)
async def list_quests(
    quest_type: Optional[str] = Query(None, description="Filter by quest type"),
    quest_subtype: Optional[str] = Query(None, description="Filter by quest subtype"),
    q: Optional[str] = Query(None, description="Search query"),
    lang: str = Query("eng"),
    user=Depends(get_current_active_user_async),
):
    """Bulk load all quests with optional type/search filtering."""
    mega = get_mega_index()
    if mega is None:
        raise HTTPException(status_code=503, detail="MegaIndex not built")

    # Build all cards
    cards = []
    for strkey in mega.quest_by_strkey:
        entry = mega.quest_by_strkey[strkey]
        # Type filter
        if quest_type and entry.quest_type != quest_type.lower():
            continue
        # Subtype filter
        if quest_subtype and entry.quest_subtype != quest_subtype.lower():
            continue
        card = _build_quest_card(strkey, mega, lang)
        if card:
            # Search filter
            if q:
                q_lower = q.lower()
                searchable = f"{card.name_kr} {card.name_translated} {card.strkey} {card.desc_kr}".lower()
                if q_lower not in searchable:
                    continue
            cards.append(card)

    # Sort by Korean name
    cards.sort(key=lambda c: c.name_kr)
    return QuestListResponse(
        items=cards,
        total=len(cards),
        type_filter=quest_type,
        subtype_filter=quest_subtype,
    )
