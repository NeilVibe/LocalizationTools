"""Character Codex API endpoints -- paginated list, category filtering, detail, search.

Phase 47: Character Codex UI -- thin wrappers around MegaIndex O(1) lookups.
All data comes from MegaIndex (built in Phase 45).

Endpoints:
  GET /codex/characters/categories  - Filename-based character categories with counts
  GET /codex/characters/{strkey}    - Full character detail with knowledge resolution passes
  GET /codex/characters             - Paginated character list with category/search filtering
"""

from __future__ import annotations

from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_items import KnowledgePassEntry
from server.tools.ldm.schemas.codex_characters import (
    CharacterCardResponse,
    CharacterCategoryItem,
    CharacterCategoryResponse,
    CharacterDetailResponse,
    CharacterListResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index


router = APIRouter(prefix="/codex/characters", tags=["Codex Characters"])


# =============================================================================
# Helpers
# =============================================================================


# Known race tokens extracted from use_macro patterns
_RACE_TOKENS = {
    "human", "elf", "dwarf", "giant", "shai", "orc", "goblin",
    "troll", "demon", "dragon", "beast", "undead", "golem",
    "fairy", "spirit", "vampire", "werewolf", "naga", "centaur",
}

# Known gender tokens
_GENDER_TOKENS = {"male", "female"}


def _parse_use_macro(use_macro: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract race and gender from use_macro string.

    Pattern: "Macro_NPC_Human_Male" -> race="Human", gender="Male"
    Splits by "_" and searches for known tokens.
    """
    if not use_macro:
        return None, None

    parts = use_macro.split("_")
    race = None
    gender = None

    for part in parts:
        lower = part.lower()
        if lower in _RACE_TOKENS and race is None:
            race = part  # Preserve original casing
        elif lower in _GENDER_TOKENS and gender is None:
            gender = part

    return race, gender


def _extract_category(source_file: str) -> str:
    """Extract category from source filename.

    "characterinfo_npc.staticinfo.xml" -> "NPC"
    "characterinfo_monster.staticinfo.xml" -> "MONSTER"
    """
    if not source_file:
        return "UNKNOWN"

    name = source_file.lower()
    # Strip characterinfo_ prefix
    if name.startswith("characterinfo_"):
        name = name[len("characterinfo_"):]
    # Strip .staticinfo.xml suffix
    if name.endswith(".staticinfo.xml"):
        name = name[: -len(".staticinfo.xml")]
    elif name.endswith(".xml"):
        name = name[: -len(".xml")]

    return name.upper() if name else "UNKNOWN"


def _build_character_card(
    strkey: str,
    mega,
    lang: str,
) -> Optional[CharacterCardResponse]:
    """Build a CharacterCardResponse from MegaIndex data."""
    entry = mega.get_character(strkey)
    if entry is None:
        return None

    # Translated name: find first _NAME StringId
    name_translated = None
    sids = mega.entity_stringids("character", strkey)
    for sid in sorted(sids):
        if sid.upper().endswith("_NAME"):
            name_translated = mega.get_translation(sid, lang)
            if name_translated:
                break

    # Image URL from knowledge UITextureName
    image_url = None
    if entry.knowledge_key:
        knowledge = mega.get_knowledge(entry.knowledge_key)
        if knowledge and knowledge.ui_texture_name:
            image_url = f"/api/ldm/mapdata/thumbnail/{knowledge.ui_texture_name}"

    # Fallback: ui_icon_path
    if not image_url and entry.ui_icon_path:
        image_url = f"/api/ldm/mapdata/thumbnail/{entry.ui_icon_path}"

    # Parse race/gender from use_macro
    race, gender = _parse_use_macro(entry.use_macro)

    # Parse category from source_file
    category = _extract_category(entry.source_file)

    return CharacterCardResponse(
        strkey=entry.strkey,
        name_kr=entry.name,
        name_translated=name_translated,
        desc_kr=entry.desc or None,
        category=category,
        race=race,
        gender=gender,
        image_url=image_url,
        source_file=entry.source_file,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/categories", response_model=CharacterCategoryResponse)
async def get_character_categories(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get filename-based character categories with counts.

    Groups characters by source file prefix (e.g. NPC, MONSTER).
    """
    try:
        mega = get_mega_index()
        all_chars = mega.all_entities("character")

        # Group by category
        cat_counts: dict[str, int] = {}
        for entry in all_chars.values():
            cat = _extract_category(entry.source_file)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Sort by category name
        categories = sorted(
            [CharacterCategoryItem(category=c, count=n) for c, n in cat_counts.items()],
            key=lambda x: x.category,
        )

        return CharacterCategoryResponse(
            categories=categories,
            total_characters=len(all_chars),
        )
    except Exception as exc:
        logger.error(f"[Character Codex] get_character_categories failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strkey}", response_model=CharacterDetailResponse)
async def get_character_detail(
    strkey: str,
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get full character detail including knowledge resolution passes.

    Knowledge resolution:
    - Pass 0: Entities that reference the same KnowledgeKey (siblings)
    - Pass 1: Direct KnowledgeKey resolution
    - Pass 2: Entities with identical Korean name (excluding pass 0/1 hits)
    """
    try:
        mega = get_mega_index()
        entry = mega.get_character(strkey)

        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Character not found: {strkey}",
            )

        # Build base card fields
        card = _build_character_card(strkey, mega, lang)

        # Knowledge Pass 0: entities referencing the same knowledge key (filtered to knowledge type)
        pass_0 = []
        seen_strkeys = set()
        if entry.knowledge_key:
            refs = mega.find_by_knowledge_key(entry.knowledge_key)
            for etype, ref_strkey in refs:
                if etype == "knowledge" and ref_strkey != strkey:
                    k_entry = mega.get_knowledge(ref_strkey)
                    if k_entry:
                        pass_0.append(KnowledgePassEntry(
                            name=k_entry.name,
                            desc=k_entry.desc,
                            source=k_entry.source_file,
                        ))
                        seen_strkeys.add(ref_strkey)

        # Knowledge Pass 1: Direct KnowledgeKey resolution
        pass_1 = []
        if entry.knowledge_key:
            direct_k = mega.get_knowledge(entry.knowledge_key)
            if direct_k and direct_k.strkey not in seen_strkeys:
                pass_1.append(KnowledgePassEntry(
                    name=direct_k.name,
                    desc=direct_k.desc,
                    source=direct_k.source_file,
                ))
                seen_strkeys.add(direct_k.strkey)

        # Knowledge Pass 2: Identical Korean name matches (knowledge type, excluding seen)
        pass_2 = []
        if entry.name:
            name_matches = mega.find_by_korean_name(entry.name)
            for etype, ref_strkey in name_matches:
                if etype == "knowledge" and ref_strkey not in seen_strkeys:
                    k_entry = mega.get_knowledge(ref_strkey)
                    if k_entry:
                        pass_2.append(KnowledgePassEntry(
                            name=k_entry.name,
                            desc=k_entry.desc,
                            source=k_entry.source_file,
                        ))
                        seen_strkeys.add(ref_strkey)

        # Related entities (all types referencing same knowledge key, excluding self)
        related = []
        if entry.knowledge_key:
            refs = mega.find_by_knowledge_key(entry.knowledge_key)
            for etype, ref_strkey in refs:
                if ref_strkey != strkey:
                    related.append(ref_strkey)

        # Parse race/gender
        race, gender = _parse_use_macro(entry.use_macro)

        return CharacterDetailResponse(
            strkey=entry.strkey,
            name_kr=entry.name,
            name_translated=card.name_translated if card else None,
            desc_kr=entry.desc or None,
            category=_extract_category(entry.source_file),
            race=race,
            gender=gender,
            image_url=card.image_url if card else None,
            source_file=entry.source_file,
            age=entry.age or None,
            job=entry.job or None,
            use_macro=entry.use_macro,
            knowledge_key=entry.knowledge_key,
            knowledge_pass_0=pass_0,
            knowledge_pass_1=pass_1,
            knowledge_pass_2=pass_2,
            related_entities=related,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Character Codex] get_character_detail failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=CharacterListResponse)
async def list_characters(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None, description="Filter by filename-based category"),
    q: Optional[str] = Query(None, description="Search across name, StrKey, use_macro, age, job"),
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get paginated character list with optional category filtering and text search.

    - category: filters characters by filename-based category (e.g. NPC, MONSTER)
    - q: searches across Korean name, translated name, StrKey, use_macro, age, job
    """
    try:
        mega = get_mega_index()
        all_chars = mega.all_entities("character")

        # Collect strkeys to process
        strkeys = list(all_chars.keys())

        # Category filtering (case-insensitive)
        if category:
            cat_upper = category.upper()
            strkeys = [
                sk for sk in strkeys
                if _extract_category(all_chars[sk].source_file) == cat_upper
            ]

        # Text search filtering
        if q:
            q_lower = q.lower()
            filtered = []
            for sk in strkeys:
                entry = all_chars[sk]
                # Check Korean name, desc, strkey, use_macro, age, job
                if (
                    q_lower in entry.name.lower()
                    or q_lower in entry.desc.lower()
                    or q_lower in entry.strkey.lower()
                    or q_lower in entry.use_macro.lower()
                    or q_lower in entry.age.lower()
                    or q_lower in entry.job.lower()
                ):
                    filtered.append(sk)
                    continue
                # Check translated name
                sids = mega.entity_stringids("character", sk)
                for sid in sorted(sids):
                    if sid.upper().endswith("_NAME"):
                        translated = mega.get_translation(sid, lang)
                        if translated and q_lower in translated.lower():
                            filtered.append(sk)
                            break
            strkeys = filtered

        # Build cards for all matching characters (for sorting)
        cards = []
        for sk in strkeys:
            card = _build_character_card(sk, mega, lang)
            if card:
                cards.append(card)

        # Sort by Korean name
        cards.sort(key=lambda c: c.name_kr)

        total = len(cards)
        paginated = cards[offset: offset + limit]

        return CharacterListResponse(
            characters=paginated,
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
            category_filter=category,
        )
    except Exception as exc:
        logger.error(f"[Character Codex] list_characters failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
