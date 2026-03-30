"""Item Codex API endpoints -- bulk list, group filtering, detail, group tree, search.

Phase 46: Item Codex UI -- thin wrappers around MegaIndex O(1) lookups.
All data comes from MegaIndex (built in Phase 45).

Endpoints:
  GET /codex/items           - Bulk item list with group/search filtering
  GET /codex/items/groups    - Item group hierarchy tree for tab navigation
  GET /codex/items/{strkey}  - Full item detail with knowledge resolution passes
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from server.utils.dependencies import get_current_active_user_async
from server.tools.ldm.schemas.codex_items import (
    InspectDataEntry,
    ItemCardResponse,
    ItemDetailResponse,
    ItemGroupTreeNode,
    ItemGroupTreeResponse,
    ItemListResponse,
    KnowledgePassEntry,
)
from server.tools.ldm.services.mega_index import get_mega_index


router = APIRouter(prefix="/codex/items", tags=["Codex Items"])


# =============================================================================
# Helpers
# =============================================================================


def _build_item_card(
    strkey: str,
    mega,
    group_tree: dict,
    lang: str,
) -> ItemCardResponse:
    """Build an ItemCardResponse from MegaIndex data."""
    entry = mega.get_item(strkey)
    if entry is None:
        return None

    # Translated name: find first _NAME StringId
    name_translated = None
    sids = mega.entity_stringids("item", strkey)
    for sid in sorted(sids):
        if sid.upper().endswith("_NAME"):
            name_translated = mega.get_translation(sid, lang)
            if name_translated:
                break

    # Image URLs from greedy DDS scan, fallback to knowledge UITextureName
    image_urls = [str(p) for p in mega.get_image_paths(strkey)]
    if not image_urls and entry.knowledge_key:
        knowledge = mega.get_knowledge(entry.knowledge_key)
        if knowledge and knowledge.ui_texture_name:
            image_urls = [f"/api/ldm/mapdata/thumbnail/{knowledge.ui_texture_name}"]

    # Group name
    group_name = None
    if entry.group_key:
        group_node = group_tree.get(entry.group_key)
        if group_node:
            group_name = group_node.group_name

    return ItemCardResponse(
        strkey=entry.strkey,
        name_kr=entry.name,
        name_translated=name_translated,
        desc_kr=entry.desc or None,
        group_name=group_name,
        group_key=entry.group_key or None,
        image_urls=image_urls,
        source_file=entry.source_file,
    )


def _collect_descendant_groups(group_tree: dict, root_key: str) -> set:
    """Recursively collect all descendant group strkeys including root."""
    result = {root_key}
    node = group_tree.get(root_key)
    if node:
        for child_key in node.child_strkeys:
            result |= _collect_descendant_groups(group_tree, child_key)
    return result


def _build_group_tree_node(
    group_tree: dict, strkey: str
) -> Optional[ItemGroupTreeNode]:
    """Recursively build ItemGroupTreeNode from MegaIndex group hierarchy."""
    node = group_tree.get(strkey)
    if node is None:
        return None

    children = []
    for child_key in node.child_strkeys:
        child_node = _build_group_tree_node(group_tree, child_key)
        if child_node:
            children.append(child_node)

    return ItemGroupTreeNode(
        strkey=node.strkey,
        group_name=node.group_name,
        parent_strkey=node.parent_strkey or None,
        child_count=len(node.child_strkeys),
        item_count=len(node.item_strkeys),
        children=children,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/groups", response_model=ItemGroupTreeResponse)
async def get_item_groups(
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get the ItemGroupInfo hierarchy tree for tab navigation.

    Returns nested tree structure with item counts per group.
    """
    try:
        mega = get_mega_index()
        group_tree = mega.get_item_group_tree()

        # Build nested tree from roots (parent_strkey == "")
        roots = []
        total_items = 0
        for key, node in group_tree.items():
            if not node.parent_strkey:
                tree_node = _build_group_tree_node(group_tree, key)
                if tree_node:
                    roots.append(tree_node)
            total_items += len(node.item_strkeys)

        # Sort roots by group_name
        roots.sort(key=lambda n: n.group_name)

        return ItemGroupTreeResponse(
            groups=roots,
            total_groups=len(group_tree),
            total_items=total_items,
        )
    except Exception as exc:
        logger.error(f"[Item Codex] get_item_groups failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strkey}", response_model=ItemDetailResponse)
async def get_item_detail(
    strkey: str,
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get full item detail including knowledge resolution passes and InspectData.

    Knowledge resolution:
    - Pass 0: Entities that reference the same KnowledgeKey (siblings)
    - Pass 1: Direct KnowledgeKey resolution
    - Pass 2: Entities with identical Korean name (excluding pass 0/1 hits)
    """
    try:
        mega = get_mega_index()
        entry = mega.get_item(strkey)

        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Item not found: {strkey}",
            )

        group_tree = mega.get_item_group_tree()

        # Build base card fields
        card = _build_item_card(strkey, mega, group_tree, lang)

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

        # InspectData
        inspect_data = [
            InspectDataEntry(
                desc=ie[0],
                knowledge_name=ie[1],
                knowledge_desc=ie[2],
                source=ie[3],
            )
            for ie in entry.inspect_entries
        ]

        # Related entities (all types referencing same knowledge key, excluding self)
        related = []
        if entry.knowledge_key:
            refs = mega.find_by_knowledge_key(entry.knowledge_key)
            for etype, ref_strkey in refs:
                if ref_strkey != strkey:
                    related.append(ref_strkey)

        return ItemDetailResponse(
            strkey=entry.strkey,
            name_kr=entry.name,
            name_translated=card.name_translated if card else None,
            desc_kr=entry.desc or None,
            group_name=card.group_name if card else None,
            group_key=entry.group_key or None,
            image_urls=card.image_urls if card else [],
            source_file=entry.source_file,
            knowledge_key=entry.knowledge_key,
            knowledge_pass_0=pass_0,
            knowledge_pass_1=pass_1,
            knowledge_pass_2=pass_2,
            inspect_data=inspect_data,
            related_entities=related,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Item Codex] get_item_detail failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=ItemListResponse)
async def list_items(
    group: Optional[str] = Query(None, description="Filter by ItemGroupInfo StrKey"),
    q: Optional[str] = Query(None, description="Search across names, StrKey, description"),
    lang: str = Query("eng"),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get all items with optional group filtering and text search.

    - group: filters items by ItemGroupNode membership (including descendants)
    - q: searches across Korean name, translated name, StrKey, and description
    """
    try:
        mega = get_mega_index()
        all_items = mega.all_entities("item")
        group_tree = mega.get_item_group_tree()

        # Collect strkeys to process
        strkeys = list(all_items.keys())

        # Group filtering: collect all descendant group strkeys
        if group:
            allowed_groups = _collect_descendant_groups(group_tree, group)
            strkeys = [
                sk for sk in strkeys
                if all_items[sk].group_key in allowed_groups
            ]

        # Text search filtering
        if q:
            q_lower = q.lower()
            filtered = []
            for sk in strkeys:
                entry = all_items[sk]
                # Check Korean name, desc, strkey
                if (
                    q_lower in (entry.name or "").lower()
                    or q_lower in (entry.desc or "").lower()
                    or q_lower in (entry.strkey or "").lower()
                ):
                    filtered.append(sk)
                    continue
                # Check translated name
                sids = mega.entity_stringids("item", sk)
                for sid in sorted(sids):
                    if sid.upper().endswith("_NAME"):
                        translated = mega.get_translation(sid, lang)
                        if translated and q_lower in translated.lower():
                            filtered.append(sk)
                            break
            strkeys = filtered

        # Build cards for all matching items (for sorting)
        cards = []
        for sk in strkeys:
            card = _build_item_card(sk, mega, group_tree, lang)
            if card:
                cards.append(card)

        # Sort by Korean name
        cards.sort(key=lambda c: c.name_kr)

        return ItemListResponse(
            items=cards,
            total=len(cards),
            group_filter=group,
        )
    except Exception as exc:
        logger.error(f"[Item Codex] list_items failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
