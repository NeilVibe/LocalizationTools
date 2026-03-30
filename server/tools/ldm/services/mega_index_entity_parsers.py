"""
MegaIndex Entity Parsers Mixin - Phase 2 entity parsing methods.

Handles: Characters, items, factions/regions, skills, gimmicks.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger

from server.tools.ldm.services.mega_index_helpers import (
    _find_knowledge_key,
    _parse_world_position,
    _safe_parse_xml,
)
from server.tools.ldm.services.mega_index_schemas import (
    CharacterEntry,
    FactionEntry,
    FactionGroupEntry,
    GimmickEntry,
    ItemEntry,
    ItemGroupNode,
    KnowledgeEntry,
    RegionEntry,
    SkillEntry,
)


def _ci_attrs(elem) -> dict:
    """Case-insensitive XML attribute extraction — lowercase keys."""
    return {k.lower(): v for k, v in elem.attrib.items()}


class EntityParsersMixin:
    """Mixin providing Phase 2 entity parsing methods."""

    # Type hints for self.* dicts (populated by MegaIndex.__init__)
    knowledge_by_strkey: Dict[str, KnowledgeEntry]
    character_by_strkey: Dict[str, CharacterEntry]
    item_by_strkey: Dict[str, ItemEntry]
    region_by_strkey: Dict[str, RegionEntry]
    faction_by_strkey: Dict[str, FactionEntry]
    faction_group_by_strkey: Dict[str, FactionGroupEntry]
    skill_by_strkey: Dict[str, SkillEntry]
    gimmick_by_strkey: Dict[str, GimmickEntry]
    item_group_hierarchy: Dict[str, ItemGroupNode]
    region_display_names: Dict[str, str]

    # =========================================================================
    # Phase 2: Entity Parsers
    # =========================================================================

    def _parse_character_info(self, character_folder: Path) -> None:
        """D2: Parse CharacterInfo elements from characterinfo XMLs."""
        try:
            logger.info(f"[MEGAINDEX] Character folder: {character_folder} (is_dir={character_folder.is_dir()})")
            if not character_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Character folder not found: {character_folder}"
                )
                return
            xml_files = list(character_folder.rglob("*.xml"))
            logger.info(f"[MEGAINDEX] Character XMLs found: {len(xml_files)}")
            for xml_path in xml_files:
                root = _safe_parse_xml(xml_path)
                if root is None:
                    logger.warning(f"[MEGAINDEX] Failed to parse: {xml_path.name}")
                    continue
                source_file = xml_path.name
                count_before = len(self.character_by_strkey)
                for elem in root.iter("CharacterInfo"):
                    a = _ci_attrs(elem)
                    strkey = (a.get("strkey") or "").lower()
                    if not strkey:
                        continue
                    knowledge_key = _find_knowledge_key(elem)
                    self.character_by_strkey[strkey] = CharacterEntry(
                        strkey=strkey,
                        name=a.get("charactername") or "",
                        desc=a.get("characterdesc") or "",
                        knowledge_key=knowledge_key,
                        use_macro=a.get("usemacro") or "",
                        age=a.get("age") or "",
                        job=a.get("job") or "",
                        ui_icon_path=a.get("uiiconpath") or "",
                        source_file=source_file,
                    )
                extracted = len(self.character_by_strkey) - count_before
                if extracted > 0:
                    logger.debug(f"[MEGAINDEX] {xml_path.name}: +{extracted} characters")
        except Exception as e:
            logger.exception(f"[MEGAINDEX] Character parse failed: {e}")

    def _parse_item_info(self, item_folder: Path, knowledge_folder: Path) -> None:
        """D3+D14: Parse ItemInfo and ItemGroupInfo for items and hierarchy."""
        # D14: ItemGroupInfo hierarchy
        group_children: Dict[str, List[str]] = {}  # group_strkey -> child groups
        group_items: Dict[str, List[str]] = {}  # group_strkey -> items in group

        try:
            logger.info(f"[MEGAINDEX] Item folder: {item_folder} (is_dir={item_folder.is_dir()})")
            if not item_folder.is_dir():
                logger.warning(f"[MEGAINDEX] Item folder not found: {item_folder}")
                self._parse_items_from_knowledge(knowledge_folder)
                return

            xml_files = list(item_folder.rglob("*.xml"))
            logger.info(f"[MEGAINDEX] Item XMLs found: {len(xml_files)}")
            for xml_path in xml_files:
                root = _safe_parse_xml(xml_path)
                if root is None:
                    logger.debug(f"[MEGAINDEX] Item XML parse failed: {xml_path.name}")
                    continue
                source_file = xml_path.name
                items_before = len(self.item_by_strkey)
                groups_before = len(self.item_group_hierarchy)

                # D14: ItemGroupInfo hierarchy
                for elem in root.iter("ItemGroupInfo"):
                    a = _ci_attrs(elem)
                    gstrkey = (a.get("strkey") or "").lower()
                    if not gstrkey:
                        continue
                    parent_sk = (a.get("parentstrkey") or "").lower()
                    gname = a.get("groupname") or ""

                    # Track children of parent
                    if parent_sk:
                        group_children.setdefault(parent_sk, []).append(gstrkey)

                    # Collect items directly under this group
                    items_in_group: List[str] = []
                    for item_elem in elem.iter("ItemInfo"):
                        ia = _ci_attrs(item_elem)
                        isk = (ia.get("strkey") or "").lower()
                        if isk:
                            items_in_group.append(isk)
                    group_items[gstrkey] = items_in_group

                    self.item_group_hierarchy[gstrkey] = ItemGroupNode(
                        strkey=gstrkey,
                        group_name=gname,
                        parent_strkey=parent_sk,
                        child_strkeys=(),  # filled below
                        item_strkeys=tuple(items_in_group),
                    )

                # D3: ItemInfo entries
                for elem in root.iter("ItemInfo"):
                    a = _ci_attrs(elem)
                    strkey = (a.get("strkey") or "").lower()
                    if not strkey:
                        continue
                    knowledge_key = _find_knowledge_key(elem)

                    # Extract InspectData/PageData
                    inspect_entries: List[Tuple[str, str, str, str]] = []
                    for inspect in elem.iter("InspectData"):
                        for page in inspect.iter("PageData"):
                            pa = _ci_attrs(page)
                            p_desc = pa.get("desc") or ""
                            rk = (pa.get("rewardknowledgekey") or "").lower()
                            k_name = ""
                            k_desc = ""
                            k_src = ""
                            if rk and rk in self.knowledge_by_strkey:
                                ke = self.knowledge_by_strkey[rk]
                                k_name = ke.name
                                k_desc = ke.desc
                                k_src = ke.source_file
                            inspect_entries.append((p_desc, k_name, k_desc, k_src))

                    # Determine group_key from parent ItemGroupInfo
                    group_key = ""
                    parent = elem.getparent()
                    if parent is not None and parent.tag == "ItemGroupInfo":
                        pa = _ci_attrs(parent)
                        group_key = (pa.get("strkey") or "").lower()

                    self.item_by_strkey[strkey] = ItemEntry(
                        strkey=strkey,
                        name=a.get("itemname") or "",
                        desc=a.get("itemdesc") or "",
                        knowledge_key=knowledge_key,
                        group_key=group_key,
                        source_file=source_file,
                        inspect_entries=tuple(inspect_entries),
                    )

                items_added = len(self.item_by_strkey) - items_before
                groups_added = len(self.item_group_hierarchy) - groups_before
                if items_added > 0 or groups_added > 0:
                    logger.debug(f"[MEGAINDEX] {xml_path.name}: +{items_added} items, +{groups_added} groups")

            # Update item_group_hierarchy with child_strkeys
            for gstrkey, node in list(self.item_group_hierarchy.items()):
                children = tuple(group_children.get(gstrkey, []))
                if children:
                    self.item_group_hierarchy[gstrkey] = ItemGroupNode(
                        strkey=node.strkey,
                        group_name=node.group_name,
                        parent_strkey=node.parent_strkey,
                        child_strkeys=children,
                        item_strkeys=node.item_strkeys,
                    )

        except Exception as e:
            logger.exception(f"[MEGAINDEX] Item parse failed: {e}")

        # Also parse items from knowledge folder (MapDataGenerator ITEM mode)
        self._parse_items_from_knowledge(knowledge_folder)

    def _parse_items_from_knowledge(self, knowledge_folder: Path) -> None:
        """Parse items that only exist as KnowledgeInfo entries (not in iteminfo)."""
        # Items in knowledge mode use KnowledgeInfo.StrKey as the entity key
        # Only add if not already in item_by_strkey (avoid duplicates)
        # This covers the MapDataGenerator ITEM mode pattern
        pass  # Knowledge entries are already in knowledge_by_strkey (D1)

    def _parse_faction_info(self, faction_folder: Path) -> None:
        """D4+D5+D6+D16: Parse FactionGroup, Faction, FactionNode, RegionInfo."""
        try:
            logger.info(f"[MEGAINDEX] Faction folder: {faction_folder} (is_dir={faction_folder.is_dir()})")
            if not faction_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Faction folder not found: {faction_folder}"
                )
                return

            xml_files = list(faction_folder.rglob("*.xml"))
            logger.info(f"[MEGAINDEX] Faction XMLs found: {len(xml_files)}")
            fgroups_before = len(self.faction_group_by_strkey)
            factions_before = len(self.faction_by_strkey)
            regions_before = len(self.region_by_strkey)
            for xml_path in xml_files:
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                fg0 = len(self.faction_group_by_strkey)
                fc0 = len(self.faction_by_strkey)
                rg0 = len(self.region_by_strkey)

                # D6: FactionGroup entries
                for elem in root.iter("FactionGroup"):
                    a = _ci_attrs(elem)
                    gstrkey = (a.get("strkey") or "").lower()
                    if not gstrkey:
                        continue
                    faction_strkeys: List[str] = []
                    for faction_elem in elem.iter("Faction"):
                        fa = _ci_attrs(faction_elem)
                        fsk = (fa.get("strkey") or "").lower()
                        if fsk:
                            faction_strkeys.append(fsk)
                    self.faction_group_by_strkey[gstrkey] = FactionGroupEntry(
                        strkey=gstrkey,
                        group_name=a.get("groupname") or a.get("name") or "",
                        knowledge_key=(a.get("knowledgekey") or "").lower(),
                        source_file=source_file,
                        faction_strkeys=tuple(faction_strkeys),
                    )

                # D5: Faction entries
                for elem in root.iter("Faction"):
                    a = _ci_attrs(elem)
                    fstrkey = (a.get("strkey") or "").lower()
                    if not fstrkey:
                        continue
                    node_strkeys: List[str] = []
                    for node_elem in elem.iter("FactionNode"):
                        na = _ci_attrs(node_elem)
                        nsk = (na.get("strkey") or "").lower()
                        if nsk:
                            node_strkeys.append(nsk)

                    # Determine parent group
                    group_strkey = ""
                    parent = elem.getparent()
                    if parent is not None and parent.tag == "FactionGroup":
                        pa = _ci_attrs(parent)
                        group_strkey = (pa.get("strkey") or "").lower()

                    self.faction_by_strkey[fstrkey] = FactionEntry(
                        strkey=fstrkey,
                        name=a.get("name") or "",
                        knowledge_key=(a.get("knowledgekey") or "").lower(),
                        group_strkey=group_strkey,
                        source_file=source_file,
                        node_strkeys=tuple(node_strkeys),
                    )

                # D4: FactionNode entries (regions)
                for elem in root.iter("FactionNode"):
                    a = _ci_attrs(elem)
                    nstrkey = (a.get("strkey") or "").lower()
                    if not nstrkey:
                        continue
                    knowledge_key = (a.get("knowledgekey") or "").lower()
                    wp = _parse_world_position(a.get("worldposition") or "")

                    # Get name from knowledge table if available
                    name = a.get("aliasname") or a.get("name") or ""
                    desc = ""
                    if knowledge_key and knowledge_key in self.knowledge_by_strkey:
                        ke = self.knowledge_by_strkey[knowledge_key]
                        if not name:
                            name = ke.name
                        desc = ke.desc

                    # Determine parent FactionNode
                    parent_strkey = ""
                    parent = elem.getparent()
                    if parent is not None and parent.tag == "FactionNode":
                        pa = _ci_attrs(parent)
                        parent_strkey = (pa.get("strkey") or "").lower()

                    self.region_by_strkey[nstrkey] = RegionEntry(
                        strkey=nstrkey,
                        name=name,
                        desc=desc,
                        knowledge_key=knowledge_key,
                        world_position=wp,
                        node_type=a.get("type") or "",
                        parent_strkey=parent_strkey,
                        source_file=source_file,
                        display_name="",
                    )

                # D16: RegionInfo -> display names
                for elem in root.iter("RegionInfo"):
                    a = _ci_attrs(elem)
                    kk = (a.get("knowledgekey") or "").lower()
                    display_name = a.get("displayname") or ""
                    if kk and display_name:
                        self.region_display_names[kk] = display_name
                        for rstrkey, rentry in self.region_by_strkey.items():
                            if rentry.knowledge_key == kk and not rentry.display_name:
                                self.region_by_strkey[rstrkey] = RegionEntry(
                                    strkey=rentry.strkey,
                                    name=rentry.name,
                                    desc=rentry.desc,
                                    knowledge_key=rentry.knowledge_key,
                                    world_position=rentry.world_position,
                                    node_type=rentry.node_type,
                                    parent_strkey=rentry.parent_strkey,
                                    source_file=rentry.source_file,
                                    display_name=display_name,
                                )

                fg_new = len(self.faction_group_by_strkey) - fg0
                fc_new = len(self.faction_by_strkey) - fc0
                rg_new = len(self.region_by_strkey) - rg0
                if fg_new or fc_new or rg_new:
                    logger.debug(f"[MEGAINDEX]   {source_file}: +{fg_new} groups, +{fc_new} factions, +{rg_new} regions")
            logger.info(
                f"[MEGAINDEX] Faction totals: {len(self.faction_group_by_strkey) - fgroups_before} groups, "
                f"{len(self.faction_by_strkey) - factions_before} factions, "
                f"{len(self.region_by_strkey) - regions_before} regions"
            )
        except Exception as e:
            logger.exception(f"[MEGAINDEX] Faction parse failed: {e}")

    def _parse_skill_info(self, staticinfo_folder: Path) -> None:
        """D7: Parse SkillInfo elements from skillinfo XMLs."""
        try:
            if not staticinfo_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] StaticInfo folder not found: {staticinfo_folder}"
                )
                return
            xml_files = list(staticinfo_folder.rglob("skillinfo_*.xml"))
            logger.info(f"[MEGAINDEX] Skill XMLs found: {len(xml_files)} in {staticinfo_folder}")
            skills_before = len(self.skill_by_strkey)
            for xml_path in xml_files:
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                sk0 = len(self.skill_by_strkey)
                for elem in root.iter("SkillInfo"):
                    a = _ci_attrs(elem)
                    strkey = (a.get("strkey") or "").lower()
                    if not strkey:
                        continue
                    self.skill_by_strkey[strkey] = SkillEntry(
                        strkey=strkey,
                        name=a.get("skillname") or "",
                        desc=a.get("desc") or a.get("skilldesc") or "",
                        learn_knowledge_key=(a.get("learnknowledgekey") or "").lower(),
                        source_file=source_file,
                    )
                sk_new = len(self.skill_by_strkey) - sk0
                if sk_new:
                    logger.debug(f"[MEGAINDEX]   {source_file}: +{sk_new} skills")
            logger.info(f"[MEGAINDEX] Skills total: {len(self.skill_by_strkey) - skills_before} new")
        except Exception as e:
            logger.exception(f"[MEGAINDEX] Skill parse failed: {e}")

    def _parse_gimmick_info(self, staticinfo_folder: Path) -> None:
        """D8: Parse GimmickGroupInfo/GimmickInfo elements."""
        try:
            if not staticinfo_folder.is_dir():
                logger.warning(f"[MEGAINDEX] StaticInfo folder not found for gimmicks: {staticinfo_folder}")
                return
            xml_files = list(staticinfo_folder.rglob("gimmickinfo_*.xml"))
            logger.info(f"[MEGAINDEX] Gimmick XMLs found: {len(xml_files)} in {staticinfo_folder}")
            gimmicks_before = len(self.gimmick_by_strkey)
            for xml_path in xml_files:
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                gk0 = len(self.gimmick_by_strkey)
                for group_elem in root.iter("GimmickGroupInfo"):
                    ga = _ci_attrs(group_elem)
                    gstrkey = (ga.get("strkey") or "").lower()
                    gname = ga.get("gimmickname") or ""
                    # Extract inner GimmickInfo with SealData
                    for gimmick_elem in group_elem.iter("GimmickInfo"):
                        ia = _ci_attrs(gimmick_elem)
                        inner_strkey = (ia.get("strkey") or "").lower()
                        strkey = inner_strkey or gstrkey
                        if not strkey:
                            continue
                        seal_desc = ""
                        for seal in gimmick_elem.iter("SealData"):
                            sa = _ci_attrs(seal)
                            seal_desc = sa.get("desc") or ""
                        self.gimmick_by_strkey[strkey] = GimmickEntry(
                            strkey=strkey,
                            name=gname or ia.get("gimmickname") or "",
                            desc=ia.get("desc") or "",
                            seal_desc=seal_desc,
                            source_file=source_file,
                        )
                    # If no inner GimmickInfo, store the group itself
                    if gstrkey and gstrkey not in self.gimmick_by_strkey:
                        self.gimmick_by_strkey[gstrkey] = GimmickEntry(
                            strkey=gstrkey,
                            name=gname,
                            desc="",
                            seal_desc="",
                            source_file=source_file,
                        )
                gk_new = len(self.gimmick_by_strkey) - gk0
                if gk_new:
                    logger.debug(f"[MEGAINDEX]   {source_file}: +{gk_new} gimmicks")
            logger.info(f"[MEGAINDEX] Gimmicks total: {len(self.gimmick_by_strkey) - gimmicks_before} new")
        except Exception as e:
            logger.exception(f"[MEGAINDEX] Gimmick parse failed: {e}")
