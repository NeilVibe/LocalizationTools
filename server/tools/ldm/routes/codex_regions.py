"""Region Codex API endpoints -- paginated list, faction tree, detail with knowledge passes.

Phase 49: Region Codex UI + Interactive Map -- thin wrappers around MegaIndex O(1) lookups.
All data comes from MegaIndex D4/D5/D6/D16/C1 dicts.

Endpoints:
  GET /codex/regions/tree      - FactionGroup->Faction->Region hierarchy tree
  GET /codex/regions/{strkey}  - Full region detail with knowledge resolution passes
  GET /codex/regions/          - Paginated region list with faction_group/search filtering
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_items import KnowledgePassEntry
from server.tools.ldm.schemas.codex_regions import (
    FactionGroupNode,
    FactionNode,
    FactionNodeItem,
    FactionTreeResponse,
    RegionCardResponse,
    RegionDetailResponse,
    RegionListResponse,
)
from server.tools.ldm.services.mega_index import get_mega_index


router = APIRouter(prefix="/codex/regions", tags=["Codex Regions"])


# =============================================================================
# Helpers
# =============================================================================


def _find_faction_for_region(strkey: str, mega) -> tuple:
    """Find the parent Faction and FactionGroup for a region node.

    Returns (faction_name, faction_group_name) or (None, None).
    Iterates faction_by_strkey to find a faction whose node_strkeys contains this region.
    """
    for _fk, faction in mega.faction_by_strkey.items():
        if strkey in faction.node_strkeys:
            faction_name = faction.name
            # Resolve group
            faction_group_name = None
            if faction.group_strkey:
                group = mega.faction_group_by_strkey.get(faction.group_strkey)
                if group:
                    faction_group_name = group.group_name
            return faction_name, faction_group_name
    return None, None


def _build_region_card(
    strkey: str,
    mega,
    lang: str,
) -> Optional[RegionCardResponse]:
    """Build a RegionCardResponse from MegaIndex data."""
    entry = mega.get_region(strkey)
    if entry is None:
        return None

    # Korean name: prefer display_name, fallback to name
    name_kr = entry.display_name or entry.name

    # Translated name: find first _NAME StringId
    name_translated = None
    sids = mega.entity_stringids("region", strkey)
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

    # Resolve faction and faction group names
    faction_name, faction_group_name = _find_faction_for_region(strkey, mega)

    return RegionCardResponse(
        strkey=entry.strkey,
        name_kr=name_kr,
        name_translated=name_translated,
        display_name=entry.display_name or None,
        node_type=entry.node_type or None,
        world_position=entry.world_position,
        faction_name=faction_name,
        faction_group_name=faction_group_name,
        image_url=image_url,
        source_file=entry.source_file,
    )


# =============================================================================
# Endpoints
# =============================================================================


# IMPORTANT: /tree MUST be defined BEFORE /{strkey} to avoid FastAPI path conflict
@router.get("/tree", response_model=FactionTreeResponse)
async def get_faction_tree(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get FactionGroup -> Faction -> Region hierarchy tree.

    Returns nested tree structure with region counts per faction and group.
    """
    try:
        mega = get_mega_index()
        faction_groups = mega.get_faction_tree()

        groups = []
        total_factions = 0
        total_regions = 0

        for fg in faction_groups:
            faction_nodes = []
            group_region_count = 0

            for fsk in fg.faction_strkeys:
                faction = mega.faction_by_strkey.get(fsk)
                if faction is None:
                    continue

                region_items = []
                for nsk in faction.node_strkeys:
                    region = mega.get_region(nsk)
                    if region:
                        region_items.append(FactionNodeItem(
                            strkey=region.strkey,
                            name=region.display_name or region.name,
                            node_type=region.node_type or None,
                            has_position=region.world_position is not None,
                        ))

                faction_nodes.append(FactionNode(
                    strkey=faction.strkey,
                    name=faction.name,
                    region_count=len(region_items),
                    regions=region_items,
                ))
                group_region_count += len(region_items)

            # Sort factions by name
            faction_nodes.sort(key=lambda f: f.name)

            groups.append(FactionGroupNode(
                strkey=fg.strkey,
                group_name=fg.group_name,
                faction_count=len(faction_nodes),
                region_count=group_region_count,
                factions=faction_nodes,
            ))
            total_factions += len(faction_nodes)
            total_regions += group_region_count

        # Sort groups by group_name
        groups.sort(key=lambda g: g.group_name)

        return FactionTreeResponse(
            groups=groups,
            total_groups=len(groups),
            total_factions=total_factions,
            total_regions=total_regions,
        )
    except Exception as exc:
        logger.error(f"[Region Codex] get_faction_tree failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strkey}", response_model=RegionDetailResponse)
async def get_region_detail(
    strkey: str,
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get full region detail including knowledge resolution passes and WorldPosition.

    Knowledge resolution:
    - Pass 0: Entities that reference the same KnowledgeKey (siblings)
    - Pass 1: Direct KnowledgeKey resolution
    - Pass 2: Entities with identical Korean name (excluding pass 0/1 hits)
    """
    try:
        mega = get_mega_index()
        entry = mega.get_region(strkey)

        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Region not found: {strkey}",
            )

        # Build base card fields
        card = _build_region_card(strkey, mega, lang)

        # Knowledge Pass 0: entities referencing same knowledge key (knowledge type only)
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
        region_name = entry.display_name or entry.name
        if region_name:
            name_matches = mega.find_by_korean_name(region_name)
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

        # Related entities: all types referencing same knowledge key (excluding self)
        related = []
        if entry.knowledge_key:
            refs = mega.find_by_knowledge_key(entry.knowledge_key)
            for etype, ref_strkey in refs:
                if ref_strkey != strkey:
                    related.append(ref_strkey)

        return RegionDetailResponse(
            strkey=entry.strkey,
            name_kr=card.name_kr if card else (entry.display_name or entry.name),
            name_translated=card.name_translated if card else None,
            display_name=card.display_name if card else (entry.display_name or None),
            node_type=card.node_type if card else (entry.node_type or None),
            world_position=entry.world_position,
            faction_name=card.faction_name if card else None,
            faction_group_name=card.faction_group_name if card else None,
            image_url=card.image_url if card else None,
            source_file=entry.source_file,
            knowledge_key=entry.knowledge_key or None,
            desc_kr=entry.desc or None,
            knowledge_pass_0=pass_0,
            knowledge_pass_1=pass_1,
            knowledge_pass_2=pass_2,
            related_entities=related,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Region Codex] get_region_detail failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=RegionListResponse)
async def list_regions(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    faction_group: Optional[str] = Query(None, description="Filter by FactionGroup StrKey"),
    q: Optional[str] = Query(None, description="Search across names, StrKey, description"),
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get paginated region list with optional faction_group filtering and text search.

    - faction_group: filters regions by FactionGroupEntry membership (all factions in group)
    - q: searches across Korean name, display_name, StrKey, and description
    """
    try:
        mega = get_mega_index()
        all_regions = mega.all_entities("region")

        # Collect strkeys to process
        strkeys = list(all_regions.keys())

        # Faction group filtering: collect all node_strkeys from all factions in the group
        if faction_group:
            fg = mega.faction_group_by_strkey.get(faction_group)
            if fg:
                allowed_strkeys = set()
                for fsk in fg.faction_strkeys:
                    faction = mega.faction_by_strkey.get(fsk)
                    if faction:
                        allowed_strkeys.update(faction.node_strkeys)
                strkeys = [sk for sk in strkeys if sk in allowed_strkeys]
            else:
                strkeys = []

        # Text search filtering
        if q:
            q_lower = q.lower()
            filtered = []
            for sk in strkeys:
                entry = all_regions[sk]
                # Check Korean name, display_name, desc, strkey
                if (
                    q_lower in entry.name.lower()
                    or q_lower in (entry.display_name or "").lower()
                    or q_lower in entry.desc.lower()
                    or q_lower in entry.strkey.lower()
                ):
                    filtered.append(sk)
                    continue
                # Check translated name
                sids = mega.entity_stringids("region", sk)
                for sid in sorted(sids):
                    if sid.upper().endswith("_NAME"):
                        translated = mega.get_translation(sid, lang)
                        if translated and q_lower in translated.lower():
                            filtered.append(sk)
                            break
            strkeys = filtered

        # Build cards for all matching regions (for sorting)
        cards = []
        for sk in strkeys:
            card = _build_region_card(sk, mega, lang)
            if card:
                cards.append(card)

        # Sort by Korean name
        cards.sort(key=lambda c: c.name_kr)

        total = len(cards)
        paginated = cards[offset: offset + limit]

        return RegionListResponse(
            items=paginated,
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
            faction_group_filter=faction_group,
        )
    except Exception as exc:
        logger.error(f"[Region Codex] list_regions failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
