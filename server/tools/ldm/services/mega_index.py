"""
MegaIndex - Unified game data index with 35 dicts and O(1) lookups.

Parses ALL game data XMLs once and builds a complete graph of interconnected
dictionaries. Every entity (item, character, region, knowledge, audio) becomes
reachable from every key type (StrKey, StringId, KnowledgeKey, EventName,
UITextureName) in O(1) time.

Phase 45: MegaIndex Foundation Infrastructure (Plan 03)
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger
from lxml import etree

from server.tools.ldm.services.mega_index_schemas import (
    CharacterEntry,
    FactionEntry,
    FactionGroupEntry,
    GimmickEntry,
    ItemEntry,
    ItemGroupNode,
    KnowledgeEntry,
    KnowledgeGroupNode,
    RegionEntry,
    SkillEntry,
)
from server.tools.ldm.services.perforce_path_service import get_perforce_path_service


# =============================================================================
# Constants
# =============================================================================

# Case-insensitive StringId attribute extraction (from STRINGID_AUDIO_CHAIN.md)
STRINGID_ATTRS = ["StringId", "StringID", "stringid"]

# StrOrigin normalization patterns (from QACompiler base.py)
_BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_PLACEHOLDER_SUFFIX_RE = re.compile(r"\{([^#}]+)#[^}]+\}")
_WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)

# Entity type -> dict attribute mapping for generic access
_ENTITY_TYPE_MAP = {
    "knowledge": "knowledge_by_strkey",
    "character": "character_by_strkey",
    "item": "item_by_strkey",
    "region": "region_by_strkey",
    "faction": "faction_by_strkey",
    "faction_group": "faction_group_by_strkey",
    "skill": "skill_by_strkey",
    "gimmick": "gimmick_by_strkey",
}


# =============================================================================
# Helpers
# =============================================================================


def _get_stringid(elem: Any) -> str:
    """Extract StringId from XML element with case-insensitive attr matching."""
    for attr in STRINGID_ATTRS:
        val = elem.get(attr)
        if val:
            return val
    return ""


def _normalize_strorigin(text: str) -> str:
    """Normalize StrOrigin for reverse lookup: strip # suffixes, br->space, collapse ws."""
    if not text:
        return ""
    text = _PLACEHOLDER_SUFFIX_RE.sub(r"{\1}", text)
    text = _BR_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _get_export_key(filename: str) -> str:
    """Convert data filename to export lookup key (normalized stem)."""
    return filename.lower().replace(".xml", "").replace(".loc", "")


def _safe_parse_xml(xml_path: Path) -> Optional[Any]:
    """Parse XML file with error handling. Returns root element or None."""
    try:
        tree = etree.parse(str(xml_path))
        return tree.getroot()
    except etree.XMLSyntaxError:
        try:
            tree = etree.parse(
                str(xml_path), parser=etree.XMLParser(recover=True, huge_tree=True)
            )
            return tree.getroot()
        except Exception:
            logger.warning(f"[MEGAINDEX] Failed to parse XML: {xml_path}")
            return None
    except Exception as e:
        logger.warning(f"[MEGAINDEX] Error reading {xml_path}: {e}")
        return None


def _parse_world_position(wp_str: str) -> Optional[Tuple[float, float, float]]:
    """Parse WorldPosition string to (x, y, z) tuple."""
    if not wp_str:
        return None
    try:
        parts = wp_str.strip("()").split(",")
        if len(parts) == 3:
            return (
                float(parts[0].strip()),
                float(parts[1].strip()),
                float(parts[2].strip()),
            )
    except (ValueError, IndexError):
        pass
    return None


def _find_knowledge_key(elem: Any) -> str:
    """Search element and direct children for KnowledgeKey or RewardKnowledgeKey."""
    for attr in ("KnowledgeKey", "RewardKnowledgeKey"):
        val = elem.get(attr) or ""
        if val:
            return val
    for child in elem:
        if child.tag in ("InspectData", "PageData"):
            continue
        for attr in ("KnowledgeKey", "RewardKnowledgeKey"):
            val = child.get(attr) or ""
            if val:
                return val
    return ""


# =============================================================================
# MegaIndex
# =============================================================================


class MegaIndex:
    """Unified game data index with 35 dicts and O(1) lookups in every direction.

    Build pipeline follows 7-phase order from MEGAINDEX_DESIGN.md Section 3.
    All parse methods are wrapped in try/except for graceful degradation.
    """

    def __init__(self) -> None:
        # === Phase 1: Foundation (Direct Dicts) ===
        self.knowledge_by_strkey: Dict[str, KnowledgeEntry] = {}  # D1
        self.dds_by_stem: Dict[str, Path] = {}  # D9
        self.wem_by_event: Dict[str, Path] = {}  # D10
        self.knowledge_group_hierarchy: Dict[str, KnowledgeGroupNode] = {}  # D15

        # === Phase 2: Entity Parse ===
        self.character_by_strkey: Dict[str, CharacterEntry] = {}  # D2
        self.item_by_strkey: Dict[str, ItemEntry] = {}  # D3
        self.region_by_strkey: Dict[str, RegionEntry] = {}  # D4
        self.faction_by_strkey: Dict[str, FactionEntry] = {}  # D5
        self.faction_group_by_strkey: Dict[str, FactionGroupEntry] = {}  # D6
        self.skill_by_strkey: Dict[str, SkillEntry] = {}  # D7
        self.gimmick_by_strkey: Dict[str, GimmickEntry] = {}  # D8
        self.item_group_hierarchy: Dict[str, ItemGroupNode] = {}  # D14
        self.region_display_names: Dict[str, str] = {}  # D16

        # === Phase 3: Localization ===
        self.event_to_stringid: Dict[str, str] = {}  # D11
        self.stringid_to_strorigin: Dict[str, str] = {}  # D12
        self.stringid_to_translations: Dict[str, Dict[str, str]] = {}  # D13
        self.export_file_stringids: Dict[str, Set[str]] = {}  # D17
        self.ordered_export_index: Dict[str, Dict[str, List[str]]] = {}  # D18
        self.event_to_export_path: Dict[str, str] = {}  # D20
        self.event_to_xml_order: Dict[str, int] = {}  # D21

        # === Phase 5: Broad Scan ===
        self.strkey_to_devmemo: Dict[str, str] = {}  # D19

        # === Phase 6: Reverse Dicts ===
        self.name_kr_to_strkeys: Dict[str, List[Tuple[str, str]]] = {}  # R1
        self.knowledge_key_to_entities: Dict[str, List[Tuple[str, str]]] = {}  # R2
        self.stringid_to_event: Dict[str, str] = {}  # R3
        self.ui_texture_to_strkeys: Dict[str, List[str]] = {}  # R4
        self.source_file_to_strkeys: Dict[str, List[Tuple[str, str]]] = {}  # R5
        self.strorigin_to_stringids: Dict[str, List[str]] = {}  # R6
        self.group_key_to_items: Dict[str, List[str]] = {}  # R7

        # === Phase 7: Composed Dicts ===
        self.strkey_to_image_path: Dict[str, Path] = {}  # C1
        self.strkey_to_audio_path: Dict[str, Path] = {}  # C2
        self.stringid_to_audio_path: Dict[str, Path] = {}  # C3
        self.event_to_script_kr: Dict[str, str] = {}  # C4
        self.event_to_script_eng: Dict[str, str] = {}  # C5
        self.entity_strkey_to_stringids: Dict[str, Set[str]] = {}  # C6
        self.stringid_to_entity: Dict[str, Tuple[str, str]] = {}  # C7

        # === State ===
        self._built: bool = False
        self._build_time: float = 0.0

    # =========================================================================
    # Build Pipeline
    # =========================================================================

    def build(self, preload_langs: Optional[List[str]] = None) -> None:
        """Build all 35 dicts from game data XMLs in 7-phase pipeline.

        Args:
            preload_langs: Languages to preload translations for.
                          Defaults to ["eng", "kor"].
        """
        if preload_langs is None:
            preload_langs = ["eng", "kor"]

        t0 = time.time()
        path_svc = get_perforce_path_service()

        try:
            paths = path_svc.get_all_resolved()
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Could not resolve paths: {e}")
            paths = {}

        # Resolve key folders with graceful fallback
        knowledge_folder = paths.get("knowledge_folder", Path("/nonexistent"))
        character_folder = paths.get("character_folder", Path("/nonexistent"))
        faction_folder = paths.get("faction_folder", Path("/nonexistent"))
        texture_folder = paths.get("texture_folder", Path("/nonexistent"))
        audio_folder = paths.get("audio_folder", Path("/nonexistent"))
        export_folder = paths.get("export_folder", Path("/nonexistent"))
        loc_folder = paths.get("loc_folder", Path("/nonexistent"))

        # StaticInfo root = parent of knowledge_folder (for skill, gimmick, devmemo)
        staticinfo_folder = knowledge_folder.parent if knowledge_folder != Path("/nonexistent") else Path("/nonexistent")
        # Item folder = sibling of other staticinfo folders
        item_folder = staticinfo_folder / "iteminfo"

        logger.info("[MEGAINDEX] Starting 7-phase build pipeline...")

        # ----- Phase 1: Foundation -----
        self._scan_dds_textures(texture_folder)
        self._scan_wem_files(audio_folder)
        self._parse_knowledge_info(knowledge_folder)
        logger.info(
            f"[MEGAINDEX] Phase 1 complete: {len(self.knowledge_by_strkey)} knowledge, "
            f"{len(self.dds_by_stem)} DDS, {len(self.wem_by_event)} WEM, "
            f"{len(self.knowledge_group_hierarchy)} knowledge groups"
        )

        # ----- Phase 2: Entity Parse -----
        self._parse_character_info(character_folder)
        self._parse_item_info(item_folder, knowledge_folder)
        self._parse_faction_info(faction_folder)
        self._parse_skill_info(staticinfo_folder)
        self._parse_gimmick_info(staticinfo_folder)
        logger.info(
            f"[MEGAINDEX] Phase 2 complete: {len(self.character_by_strkey)} characters, "
            f"{len(self.item_by_strkey)} items, {len(self.region_by_strkey)} regions, "
            f"{len(self.faction_by_strkey)} factions, {len(self.skill_by_strkey)} skills, "
            f"{len(self.gimmick_by_strkey)} gimmicks"
        )

        # ----- Phase 3: Localization -----
        self._parse_loc_strorigin(loc_folder)
        self._parse_loc_translations(loc_folder, preload_langs)
        self._parse_export_events(export_folder)
        self._parse_export_loc(export_folder)
        logger.info(
            f"[MEGAINDEX] Phase 3 complete: {len(self.stringid_to_strorigin)} strorigins, "
            f"{len(self.event_to_stringid)} event->stringid, "
            f"{len(self.export_file_stringids)} export files"
        )

        # ----- Phase 4: VRS (skipped for now) -----
        logger.info("[MEGAINDEX] VRS ordering skipped (future enhancement)")

        # ----- Phase 5: Broad Scan -----
        self._scan_devmemo(staticinfo_folder)
        logger.info(
            f"[MEGAINDEX] Phase 5 complete: {len(self.strkey_to_devmemo)} devmemo entries"
        )

        # ----- Phase 6: Reverse Dicts -----
        self._build_name_kr_to_strkeys()
        self._build_knowledge_key_to_entities()
        self._build_stringid_to_event()
        self._build_ui_texture_to_strkeys()
        self._build_source_file_to_strkeys()
        self._build_strorigin_to_stringids()
        self._build_group_key_to_items()
        logger.info(
            f"[MEGAINDEX] Phase 6 complete: R1={len(self.name_kr_to_strkeys)}, "
            f"R2={len(self.knowledge_key_to_entities)}, R3={len(self.stringid_to_event)}, "
            f"R4={len(self.ui_texture_to_strkeys)}, R5={len(self.source_file_to_strkeys)}, "
            f"R6={len(self.strorigin_to_stringids)}, R7={len(self.group_key_to_items)}"
        )

        # ----- Phase 7: Composed Dicts -----
        self._build_strkey_to_image_path()
        self._build_strkey_to_audio_path()
        self._build_stringid_to_audio_path()
        self._build_event_to_script_kr()
        self._build_event_to_script_eng()
        self._build_entity_strkey_to_stringids()
        self._build_stringid_to_entity_map()
        logger.info(
            f"[MEGAINDEX] Phase 7 complete: C1={len(self.strkey_to_image_path)}, "
            f"C2={len(self.strkey_to_audio_path)}, C3={len(self.stringid_to_audio_path)}, "
            f"C4={len(self.event_to_script_kr)}, C5={len(self.event_to_script_eng)}, "
            f"C6={len(self.entity_strkey_to_stringids)}, C7={len(self.stringid_to_entity)}"
        )

        self._build_time = time.time() - t0
        self._built = True
        logger.info(f"[MEGAINDEX] Build complete in {self._build_time:.2f}s")

    # =========================================================================
    # Phase 1: Foundation Parsers
    # =========================================================================

    def _scan_dds_textures(self, texture_folder: Path) -> None:
        """D9: Scan texture folder for DDS files. Key=stem.lower(), Value=Path."""
        try:
            if not texture_folder.is_dir():
                logger.warning(f"[MEGAINDEX] Texture folder not found: {texture_folder}")
                return
            for dds_path in texture_folder.rglob("*.dds"):
                stem_lower = dds_path.stem.lower()
                self.dds_by_stem[stem_lower] = dds_path
        except Exception as e:
            logger.warning(f"[MEGAINDEX] DDS scan failed: {e}")

    def _scan_wem_files(self, audio_folder: Path) -> None:
        """D10: Scan audio folder for WEM files. Key=stem.lower(), Value=Path."""
        try:
            if not audio_folder.is_dir():
                logger.warning(f"[MEGAINDEX] Audio folder not found: {audio_folder}")
                return
            for wem_path in audio_folder.rglob("*.wem"):
                stem_lower = wem_path.stem.lower()
                self.wem_by_event[stem_lower] = wem_path
        except Exception as e:
            logger.warning(f"[MEGAINDEX] WEM scan failed: {e}")

    def _parse_knowledge_info(self, knowledge_folder: Path) -> None:
        """D1+D15: Parse KnowledgeInfo and KnowledgeGroupInfo in single pass."""
        try:
            if not knowledge_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Knowledge folder not found: {knowledge_folder}"
                )
                return
            for xml_path in knowledge_folder.rglob("*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name

                # D1: KnowledgeInfo entries
                for elem in root.iter("KnowledgeInfo"):
                    strkey = elem.get("StrKey") or ""
                    if not strkey:
                        continue
                    self.knowledge_by_strkey[strkey] = KnowledgeEntry(
                        strkey=strkey,
                        name=elem.get("Name") or "",
                        desc=elem.get("Desc") or "",
                        ui_texture_name=elem.get("UITextureName") or "",
                        group_key=elem.get("KnowledgeGroupKey")
                        or elem.get("GroupKey")
                        or "",
                        source_file=source_file,
                    )

                # D15: KnowledgeGroupInfo entries
                for elem in root.iter("KnowledgeGroupInfo"):
                    strkey = elem.get("StrKey") or ""
                    if not strkey:
                        continue
                    # Collect child knowledge entries in this group
                    child_strkeys: List[str] = []
                    for child in elem.iter("KnowledgeInfo"):
                        csk = child.get("StrKey") or ""
                        if csk:
                            child_strkeys.append(csk)
                    self.knowledge_group_hierarchy[strkey] = KnowledgeGroupNode(
                        strkey=strkey,
                        group_name=elem.get("GroupName") or elem.get("Name") or "",
                        child_strkeys=tuple(child_strkeys),
                    )
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Knowledge parse failed: {e}")

    # =========================================================================
    # Phase 2: Entity Parsers
    # =========================================================================

    def _parse_character_info(self, character_folder: Path) -> None:
        """D2: Parse CharacterInfo elements from characterinfo XMLs."""
        try:
            if not character_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Character folder not found: {character_folder}"
                )
                return
            for xml_path in character_folder.rglob("*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                for elem in root.iter("CharacterInfo"):
                    strkey = elem.get("StrKey") or ""
                    if not strkey:
                        continue
                    knowledge_key = _find_knowledge_key(elem)
                    self.character_by_strkey[strkey] = CharacterEntry(
                        strkey=strkey,
                        name=elem.get("CharacterName") or "",
                        desc=elem.get("CharacterDesc") or "",
                        knowledge_key=knowledge_key,
                        use_macro=elem.get("UseMacro") or "",
                        age=elem.get("Age") or "",
                        job=elem.get("Job") or "",
                        ui_icon_path=elem.get("UIIconPath") or "",
                        source_file=source_file,
                    )
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Character parse failed: {e}")

    def _parse_item_info(self, item_folder: Path, knowledge_folder: Path) -> None:
        """D3+D14: Parse ItemInfo and ItemGroupInfo for items and hierarchy."""
        # D14: ItemGroupInfo hierarchy
        group_children: Dict[str, List[str]] = {}  # group_strkey -> child groups
        group_items: Dict[str, List[str]] = {}  # group_strkey -> items in group

        try:
            if not item_folder.is_dir():
                logger.warning(f"[MEGAINDEX] Item folder not found: {item_folder}")
                # Also try knowledge folder for items in knowledge mode
                self._parse_items_from_knowledge(knowledge_folder)
                return

            for xml_path in item_folder.rglob("*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name

                # D14: ItemGroupInfo hierarchy
                for elem in root.iter("ItemGroupInfo"):
                    gstrkey = elem.get("StrKey") or ""
                    if not gstrkey:
                        continue
                    parent_sk = elem.get("ParentStrKey") or ""
                    gname = elem.get("GroupName") or ""

                    # Track children of parent
                    if parent_sk:
                        group_children.setdefault(parent_sk, []).append(gstrkey)

                    # Collect items directly under this group
                    items_in_group: List[str] = []
                    for item_elem in elem.iter("ItemInfo"):
                        isk = item_elem.get("StrKey") or ""
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
                    strkey = elem.get("StrKey") or ""
                    if not strkey:
                        continue
                    knowledge_key = _find_knowledge_key(elem)

                    # Extract InspectData/PageData
                    inspect_entries: List[Tuple[str, str, str, str]] = []
                    for inspect in elem.iter("InspectData"):
                        for page in inspect.iter("PageData"):
                            p_desc = page.get("Desc") or ""
                            rk = page.get("RewardKnowledgeKey") or ""
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
                        group_key = parent.get("StrKey") or ""

                    self.item_by_strkey[strkey] = ItemEntry(
                        strkey=strkey,
                        name=elem.get("ItemName") or "",
                        desc=elem.get("ItemDesc") or "",
                        knowledge_key=knowledge_key,
                        group_key=group_key,
                        source_file=source_file,
                        inspect_entries=tuple(inspect_entries),
                    )

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
            logger.warning(f"[MEGAINDEX] Item parse failed: {e}")

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
            if not faction_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Faction folder not found: {faction_folder}"
                )
                return

            for xml_path in faction_folder.rglob("*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name

                # D6: FactionGroup entries
                for elem in root.iter("FactionGroup"):
                    gstrkey = elem.get("StrKey") or ""
                    if not gstrkey:
                        continue
                    faction_strkeys: List[str] = []
                    for faction_elem in elem.iter("Faction"):
                        fsk = faction_elem.get("StrKey") or ""
                        if fsk:
                            faction_strkeys.append(fsk)
                    self.faction_group_by_strkey[gstrkey] = FactionGroupEntry(
                        strkey=gstrkey,
                        group_name=elem.get("GroupName") or elem.get("Name") or "",
                        knowledge_key=elem.get("KnowledgeKey") or "",
                        source_file=source_file,
                        faction_strkeys=tuple(faction_strkeys),
                    )

                # D5: Faction entries
                for elem in root.iter("Faction"):
                    fstrkey = elem.get("StrKey") or ""
                    if not fstrkey:
                        continue
                    node_strkeys: List[str] = []
                    for node_elem in elem.iter("FactionNode"):
                        nsk = node_elem.get("StrKey") or ""
                        if nsk:
                            node_strkeys.append(nsk)

                    # Determine parent group
                    group_strkey = ""
                    parent = elem.getparent()
                    if parent is not None and parent.tag == "FactionGroup":
                        group_strkey = parent.get("StrKey") or ""

                    self.faction_by_strkey[fstrkey] = FactionEntry(
                        strkey=fstrkey,
                        name=elem.get("Name") or "",
                        knowledge_key=elem.get("KnowledgeKey") or "",
                        group_strkey=group_strkey,
                        source_file=source_file,
                        node_strkeys=tuple(node_strkeys),
                    )

                # D4: FactionNode entries (regions)
                for elem in root.iter("FactionNode"):
                    nstrkey = elem.get("StrKey") or ""
                    if not nstrkey:
                        continue
                    knowledge_key = elem.get("KnowledgeKey") or ""
                    wp = _parse_world_position(elem.get("WorldPosition") or "")

                    # Get name from knowledge table if available
                    name = elem.get("AliasName") or elem.get("Name") or ""
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
                        parent_strkey = parent.get("StrKey") or ""

                    self.region_by_strkey[nstrkey] = RegionEntry(
                        strkey=nstrkey,
                        name=name,
                        desc=desc,
                        knowledge_key=knowledge_key,
                        world_position=wp,
                        node_type=elem.get("Type") or "",
                        parent_strkey=parent_strkey,
                        source_file=source_file,
                        display_name="",
                    )

                # D16: RegionInfo -> display names
                for elem in root.iter("RegionInfo"):
                    kk = elem.get("KnowledgeKey") or ""
                    display_name = elem.get("DisplayName") or ""
                    if kk and display_name:
                        self.region_display_names[kk] = display_name
                        # Update region entry display_name if it exists
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

        except Exception as e:
            logger.warning(f"[MEGAINDEX] Faction parse failed: {e}")

    def _parse_skill_info(self, staticinfo_folder: Path) -> None:
        """D7: Parse SkillInfo elements from skillinfo XMLs."""
        try:
            if not staticinfo_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] StaticInfo folder not found: {staticinfo_folder}"
                )
                return
            for xml_path in staticinfo_folder.rglob("skillinfo_*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                for elem in root.iter("SkillInfo"):
                    strkey = elem.get("StrKey") or ""
                    if not strkey:
                        continue
                    self.skill_by_strkey[strkey] = SkillEntry(
                        strkey=strkey,
                        name=elem.get("SkillName") or "",
                        desc=elem.get("Desc") or elem.get("SkillDesc") or "",
                        learn_knowledge_key=elem.get("LearnKnowledgeKey") or "",
                        source_file=source_file,
                    )
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Skill parse failed: {e}")

    def _parse_gimmick_info(self, staticinfo_folder: Path) -> None:
        """D8: Parse GimmickGroupInfo/GimmickInfo elements."""
        try:
            if not staticinfo_folder.is_dir():
                return
            for xml_path in staticinfo_folder.rglob("gimmickinfo_*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                source_file = xml_path.name
                for group_elem in root.iter("GimmickGroupInfo"):
                    gstrkey = group_elem.get("StrKey") or ""
                    gname = group_elem.get("GimmickName") or ""
                    # Extract inner GimmickInfo with SealData
                    for gimmick_elem in group_elem.iter("GimmickInfo"):
                        inner_strkey = gimmick_elem.get("StrKey") or ""
                        strkey = inner_strkey or gstrkey
                        if not strkey:
                            continue
                        seal_desc = ""
                        for seal in gimmick_elem.iter("SealData"):
                            seal_desc = seal.get("Desc") or ""
                        self.gimmick_by_strkey[strkey] = GimmickEntry(
                            strkey=strkey,
                            name=gname or gimmick_elem.get("GimmickName") or "",
                            desc=gimmick_elem.get("Desc") or "",
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
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Gimmick parse failed: {e}")

    # =========================================================================
    # Phase 3: Localization Parsers
    # =========================================================================

    def _parse_loc_strorigin(self, loc_folder: Path) -> None:
        """D12: Parse languagedata_KOR.xml for StringId -> StrOrigin mapping."""
        try:
            if not loc_folder.is_dir():
                logger.warning(f"[MEGAINDEX] Loc folder not found: {loc_folder}")
                return
            # Look for Korean language data file
            kor_files = list(loc_folder.glob("**/languagedata_[Kk][Oo][Rr]*.xml"))
            if not kor_files:
                # Try broader pattern
                kor_files = [
                    f for f in loc_folder.rglob("*.xml")
                    if "kor" in f.stem.lower() and "languagedata" in f.stem.lower()
                ]
            for kor_path in kor_files:
                root = _safe_parse_xml(kor_path)
                if root is None:
                    continue
                for elem in root.iter("LocStr"):
                    sid = _get_stringid(elem)
                    if not sid:
                        continue
                    strorigin = elem.get("StrOrigin") or ""
                    if strorigin:
                        self.stringid_to_strorigin[sid] = strorigin
        except Exception as e:
            logger.warning(f"[MEGAINDEX] StrOrigin parse failed: {e}")

    def _parse_loc_translations(
        self, loc_folder: Path, langs: List[str]
    ) -> None:
        """D13: Parse languagedata_{code}.xml for each preloaded language."""
        try:
            if not loc_folder.is_dir():
                return
            for xml_path in loc_folder.rglob("*.xml"):
                stem = xml_path.stem.lower()
                if not stem.startswith("languagedata_"):
                    continue
                # Extract language code
                lang = stem.split("_", 1)[1]
                if lang == "kor":
                    continue  # Korean is strorigin, not translation
                if lang not in langs:
                    continue
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                for elem in root.iter("LocStr"):
                    sid = _get_stringid(elem)
                    if not sid:
                        continue
                    text = elem.get("Str") or ""
                    if text:
                        if sid not in self.stringid_to_translations:
                            self.stringid_to_translations[sid] = {}
                        self.stringid_to_translations[sid][lang] = text
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Translation parse failed: {e}")

    def _parse_export_events(self, export_folder: Path) -> None:
        """D11+D20+D21: Parse export XMLs for event->stringid mapping."""
        try:
            if not export_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] Export folder not found: {export_folder}"
                )
                return
            global_order = 0
            for xml_path in sorted(export_folder.rglob("*.xml")):
                # Skip .loc.xml files (handled by _parse_export_loc)
                if xml_path.name.endswith(".loc.xml"):
                    continue
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue

                # Relative path from export root
                try:
                    rel_dir = str(xml_path.relative_to(export_folder).parent)
                except ValueError:
                    rel_dir = ""

                for elem in root.iter():
                    event_name = (
                        elem.get("SoundEventName")
                        or elem.get("EventName")
                        or ""
                    )
                    sid = _get_stringid(elem)
                    if event_name and sid:
                        event_lower = event_name.lower()
                        self.event_to_stringid[event_lower] = sid  # D11
                        self.event_to_export_path[event_lower] = rel_dir  # D20
                        self.event_to_xml_order[event_lower] = global_order  # D21
                        global_order += 1
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Export events parse failed: {e}")

    def _parse_export_loc(self, export_folder: Path) -> None:
        """D17+D18: Parse export .loc.xml files for StringId sets and ordered index."""
        try:
            if not export_folder.is_dir():
                return
            for xml_path in sorted(export_folder.rglob("*.loc.xml")):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue

                filename_key = _get_export_key(xml_path.name)
                sids: Set[str] = set()
                kor_map: Dict[str, List[str]] = {}

                for elem in root.iter("LocStr"):
                    sid = _get_stringid(elem)
                    origin = elem.get("StrOrigin") or ""
                    if sid:
                        sids.add(sid)
                    if origin and sid:
                        norm = _normalize_strorigin(origin)
                        if norm:
                            kor_map.setdefault(norm, []).append(sid)

                if sids:
                    if filename_key in self.export_file_stringids:
                        self.export_file_stringids[filename_key].update(sids)
                    else:
                        self.export_file_stringids[filename_key] = sids

                if kor_map:
                    if filename_key in self.ordered_export_index:
                        existing = self.ordered_export_index[filename_key]
                        for norm_text, sid_list in kor_map.items():
                            existing.setdefault(norm_text, []).extend(sid_list)
                    else:
                        self.ordered_export_index[filename_key] = kor_map
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Export loc parse failed: {e}")

    # =========================================================================
    # Phase 5: Broad Scan
    # =========================================================================

    def _scan_devmemo(self, staticinfo_folder: Path) -> None:
        """D19: Broad scan of StaticInfo for StrKey -> DevMemo/DevComment."""
        try:
            if not staticinfo_folder.is_dir():
                logger.warning(
                    f"[MEGAINDEX] StaticInfo folder not found: {staticinfo_folder}"
                )
                return
            for xml_path in staticinfo_folder.rglob("*.xml"):
                root = _safe_parse_xml(xml_path)
                if root is None:
                    continue
                for elem in root.iter():
                    strkey = elem.get("StrKey")
                    if not strkey:
                        continue
                    korean = elem.get("DevMemo") or elem.get("DevComment") or ""
                    if korean and strkey.lower() not in self.strkey_to_devmemo:
                        self.strkey_to_devmemo[strkey.lower()] = korean
        except Exception as e:
            logger.warning(f"[MEGAINDEX] DevMemo scan failed: {e}")

    # =========================================================================
    # Phase 6: Reverse Dict Builders
    # =========================================================================

    def _build_name_kr_to_strkeys(self) -> None:
        """R1: Invert name fields from D1, D2, D3, D4."""
        result: Dict[str, List[Tuple[str, str]]] = {}
        entity_dicts = [
            ("knowledge", self.knowledge_by_strkey),
            ("character", self.character_by_strkey),
            ("item", self.item_by_strkey),
            ("region", self.region_by_strkey),
        ]
        for entity_type, d in entity_dicts:
            for strkey, entry in d.items():
                name = entry.name
                if name:
                    result.setdefault(name, []).append((entity_type, strkey))
        self.name_kr_to_strkeys = result

    def _build_knowledge_key_to_entities(self) -> None:
        """R2: Scan D2, D3, D4, D7 for knowledge_key references."""
        result: Dict[str, List[Tuple[str, str]]] = {}
        entity_dicts: List[Tuple[str, dict]] = [
            ("character", self.character_by_strkey),
            ("item", self.item_by_strkey),
            ("region", self.region_by_strkey),
            ("skill", self.skill_by_strkey),
        ]
        for entity_type, d in entity_dicts:
            for strkey, entry in d.items():
                kk = getattr(entry, "knowledge_key", "") or getattr(
                    entry, "learn_knowledge_key", ""
                )
                if kk:
                    result.setdefault(kk, []).append((entity_type, strkey))
        self.knowledge_key_to_entities = result

    def _build_stringid_to_event(self) -> None:
        """R3: Invert D11 (event_to_stringid)."""
        result: Dict[str, str] = {}
        for event_lower, sid in self.event_to_stringid.items():
            result[sid] = event_lower
        self.stringid_to_event = result

    def _build_ui_texture_to_strkeys(self) -> None:
        """R4: Invert D1.ui_texture_name (lowercased)."""
        result: Dict[str, List[str]] = {}
        for strkey, entry in self.knowledge_by_strkey.items():
            tex = entry.ui_texture_name
            if tex:
                result.setdefault(tex.lower(), []).append(strkey)
        self.ui_texture_to_strkeys = result

    def _build_source_file_to_strkeys(self) -> None:
        """R5: Scan all entity dicts for source_file grouping."""
        result: Dict[str, List[Tuple[str, str]]] = {}
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey, entry in d.items():
                sf = getattr(entry, "source_file", "")
                if sf:
                    result.setdefault(sf, []).append((entity_type, strkey))
        self.source_file_to_strkeys = result

    def _build_strorigin_to_stringids(self) -> None:
        """R6: Invert D12 with StrOrigin normalization."""
        result: Dict[str, List[str]] = {}
        for sid, strorigin in self.stringid_to_strorigin.items():
            normalized = _normalize_strorigin(strorigin)
            if normalized:
                result.setdefault(normalized, []).append(sid)
        self.strorigin_to_stringids = result

    def _build_group_key_to_items(self) -> None:
        """R7: From D3, accumulate items per group_key."""
        result: Dict[str, List[str]] = {}
        for strkey, entry in self.item_by_strkey.items():
            gk = entry.group_key
            if gk:
                result.setdefault(gk, []).append(strkey)
        self.group_key_to_items = result

    # =========================================================================
    # Phase 7: Composed Dict Builders
    # =========================================================================

    def _build_strkey_to_image_path(self) -> None:
        """C1: StrKey -> KnowledgeInfo.UITextureName -> DDS path."""
        for strkey, entry in self.knowledge_by_strkey.items():
            tex = entry.ui_texture_name
            if tex:
                dds = self.dds_by_stem.get(tex.lower())
                if dds:
                    self.strkey_to_image_path[strkey] = dds

    def _build_strkey_to_audio_path(self) -> None:
        """C2: Entity StrKey -> knowledge_key -> event -> WEM path (complex chain)."""
        # For each entity with a knowledge_key, try to find an event that maps to audio
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey, entry in d.items():
                kk = getattr(entry, "knowledge_key", "") or getattr(
                    entry, "learn_knowledge_key", ""
                )
                if not kk:
                    continue
                # Check if any event references this entity's StringIds
                # via entity_strkey_to_stringids (not yet built) -- skip for now
                # Direct path: check if event_name matches strkey pattern
                sk_lower = strkey.lower()
                wem = self.wem_by_event.get(sk_lower)
                if wem:
                    self.strkey_to_audio_path[strkey] = wem

    def _build_stringid_to_audio_path(self) -> None:
        """C3: StringId -> event_name (R3) -> WEM path (D10)."""
        for sid, event_lower in self.stringid_to_event.items():
            wem = self.wem_by_event.get(event_lower)
            if wem:
                self.stringid_to_audio_path[sid] = wem

    def _build_event_to_script_kr(self) -> None:
        """C4: event -> StringId (D11) -> StrOrigin (D12)."""
        for event_lower, sid in self.event_to_stringid.items():
            origin = self.stringid_to_strorigin.get(sid)
            if origin:
                self.event_to_script_kr[event_lower] = origin

    def _build_event_to_script_eng(self) -> None:
        """C5: event -> StringId (D11) -> ENG translation (D13)."""
        for event_lower, sid in self.event_to_stringid.items():
            translations = self.stringid_to_translations.get(sid, {})
            eng = translations.get("eng")
            if eng:
                self.event_to_script_eng[event_lower] = eng

    def _build_entity_strkey_to_stringids(self) -> None:
        """C6: Entity StrKey -> source_file -> export StringIds + Korean text matching."""
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey, entry in d.items():
                source_file = getattr(entry, "source_file", "")
                if not source_file:
                    continue

                source_stem = _get_export_key(source_file)
                valid_sids = self.export_file_stringids.get(source_stem, set())
                if not valid_sids:
                    continue

                # Collect Korean texts from entity
                korean_texts: List[str] = []
                name = getattr(entry, "name", "")
                desc = getattr(entry, "desc", "")
                if name:
                    korean_texts.append(name)
                if desc:
                    korean_texts.append(desc)

                matched_sids: Set[str] = set()
                for kor_text in korean_texts:
                    normalized = _normalize_strorigin(kor_text)
                    if not normalized:
                        continue
                    candidates = self.strorigin_to_stringids.get(normalized, [])
                    for sid in candidates:
                        if sid in valid_sids:
                            matched_sids.add(sid)

                if matched_sids:
                    self.entity_strkey_to_stringids[strkey] = matched_sids

    def _build_stringid_to_entity_map(self) -> None:
        """C7: Invert C6 -- StringId -> (entity_type, strkey)."""
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey in d:
                sids = self.entity_strkey_to_stringids.get(strkey, set())
                for sid in sids:
                    if sid not in self.stringid_to_entity:
                        self.stringid_to_entity[sid] = (entity_type, strkey)

    # =========================================================================
    # Public API: Direct Entity Lookups
    # =========================================================================

    def get_knowledge(self, strkey: str) -> Optional[KnowledgeEntry]:
        """O(1) knowledge entity lookup by StrKey."""
        return self.knowledge_by_strkey.get(strkey)

    def get_character(self, strkey: str) -> Optional[CharacterEntry]:
        """O(1) character entity lookup by StrKey."""
        return self.character_by_strkey.get(strkey)

    def get_item(self, strkey: str) -> Optional[ItemEntry]:
        """O(1) item entity lookup by StrKey."""
        return self.item_by_strkey.get(strkey)

    def get_region(self, strkey: str) -> Optional[RegionEntry]:
        """O(1) region entity lookup by StrKey."""
        return self.region_by_strkey.get(strkey)

    def get_skill(self, strkey: str) -> Optional[SkillEntry]:
        """O(1) skill entity lookup by StrKey."""
        return self.skill_by_strkey.get(strkey)

    def get_gimmick(self, strkey: str) -> Optional[GimmickEntry]:
        """O(1) gimmick entity lookup by StrKey."""
        return self.gimmick_by_strkey.get(strkey)

    def get_entity(self, entity_type: str, strkey: str) -> Optional[Any]:
        """O(1) entity lookup by type and StrKey."""
        entity_type = entity_type.lower()
        attr_name = _ENTITY_TYPE_MAP.get(entity_type)
        if not attr_name:
            return None
        d = getattr(self, attr_name, {})
        return d.get(strkey)

    # =========================================================================
    # Public API: Media Lookups
    # =========================================================================

    def get_image_path(self, strkey: str) -> Optional[Path]:
        """C1: StrKey -> image DDS path."""
        return self.strkey_to_image_path.get(strkey)

    def get_audio_path_by_event(self, event_name: str) -> Optional[Path]:
        """D10: Event name -> WEM audio path."""
        return self.wem_by_event.get(event_name.lower())

    def get_audio_path_by_stringid(self, string_id: str) -> Optional[Path]:
        """C3: StringId -> audio WEM path."""
        return self.stringid_to_audio_path.get(string_id)

    def get_dds_path(self, texture_name: str) -> Optional[Path]:
        """D9: Texture name (stem) -> DDS path."""
        return self.dds_by_stem.get(texture_name.lower())

    # =========================================================================
    # Public API: Localization Lookups
    # =========================================================================

    def get_strorigin(self, string_id: str) -> Optional[str]:
        """D12: StringId -> Korean StrOrigin text."""
        return self.stringid_to_strorigin.get(string_id)

    def get_translation(self, string_id: str, lang: str) -> Optional[str]:
        """D13: StringId + language -> translated text."""
        translations = self.stringid_to_translations.get(string_id, {})
        return translations.get(lang)

    def get_script_kr(self, event_name: str) -> Optional[str]:
        """C4: Event name -> Korean script line."""
        return self.event_to_script_kr.get(event_name.lower())

    def get_script_eng(self, event_name: str) -> Optional[str]:
        """C5: Event name -> English script line."""
        return self.event_to_script_eng.get(event_name.lower())

    # =========================================================================
    # Public API: Bridge Lookups (StringId <-> StrKey)
    # =========================================================================

    def stringid_to_entity_lookup(
        self, string_id: str
    ) -> Optional[Tuple[str, str]]:
        """C7: StringId -> (entity_type, strkey)."""
        return self.stringid_to_entity.get(string_id)

    def entity_stringids(self, entity_type: str, strkey: str) -> Set[str]:
        """C6: Entity (type, strkey) -> set of StringIds."""
        return self.entity_strkey_to_stringids.get(strkey, set())

    def event_to_stringid_lookup(self, event_name: str) -> Optional[str]:
        """D11: Event name -> StringId."""
        return self.event_to_stringid.get(event_name.lower())

    def stringid_to_event_lookup(self, string_id: str) -> Optional[str]:
        """R3: StringId -> event name."""
        return self.stringid_to_event.get(string_id)

    # =========================================================================
    # Public API: Reverse Lookups
    # =========================================================================

    def find_by_korean_name(self, name_kr: str) -> List[Tuple[str, str]]:
        """R1: Korean name -> list of (entity_type, strkey) matches."""
        return self.name_kr_to_strkeys.get(name_kr, [])

    def find_by_knowledge_key(self, key: str) -> List[Tuple[str, str]]:
        """R2: Knowledge key -> list of (entity_type, strkey) that reference it."""
        return self.knowledge_key_to_entities.get(key, [])

    def find_by_source_file(self, filename: str) -> List[Tuple[str, str]]:
        """R5: Source filename -> list of (entity_type, strkey) from that file."""
        return self.source_file_to_strkeys.get(filename, [])

    def find_stringids_by_korean(self, text: str) -> List[str]:
        """R6: Korean text (normalized) -> list of matching StringIds."""
        normalized = _normalize_strorigin(text)
        return self.strorigin_to_stringids.get(normalized, [])

    # =========================================================================
    # Public API: Hierarchy
    # =========================================================================

    def get_item_group_tree(self) -> Dict[str, ItemGroupNode]:
        """D14: Full item group hierarchy."""
        return self.item_group_hierarchy

    def get_knowledge_group_tree(self) -> Dict[str, KnowledgeGroupNode]:
        """D15: Full knowledge group hierarchy."""
        return self.knowledge_group_hierarchy

    def get_faction_tree(self) -> List[FactionGroupEntry]:
        """D6: All faction groups with nested factions and nodes."""
        return list(self.faction_group_by_strkey.values())

    # =========================================================================
    # Public API: Bulk and Stats
    # =========================================================================

    def all_entities(self, entity_type: str) -> Dict[str, Any]:
        """Return all entities of a given type."""
        entity_type = entity_type.lower()
        attr_name = _ENTITY_TYPE_MAP.get(entity_type)
        if not attr_name:
            return {}
        return getattr(self, attr_name, {})

    def entity_counts(self) -> Dict[str, int]:
        """Return count of each entity type."""
        return {
            "knowledge": len(self.knowledge_by_strkey),
            "character": len(self.character_by_strkey),
            "item": len(self.item_by_strkey),
            "region": len(self.region_by_strkey),
            "faction": len(self.faction_by_strkey),
            "faction_group": len(self.faction_group_by_strkey),
            "skill": len(self.skill_by_strkey),
            "gimmick": len(self.gimmick_by_strkey),
        }

    def stats(self) -> Dict[str, Any]:
        """Return comprehensive build statistics."""
        counts = self.entity_counts()
        return {
            "built": self._built,
            "build_time": self._build_time,
            "entity_counts": counts,
            "total_entities": sum(counts.values()),
            "dict_sizes": {
                # Direct
                "D1_knowledge": len(self.knowledge_by_strkey),
                "D2_character": len(self.character_by_strkey),
                "D3_item": len(self.item_by_strkey),
                "D4_region": len(self.region_by_strkey),
                "D5_faction": len(self.faction_by_strkey),
                "D6_faction_group": len(self.faction_group_by_strkey),
                "D7_skill": len(self.skill_by_strkey),
                "D8_gimmick": len(self.gimmick_by_strkey),
                "D9_dds": len(self.dds_by_stem),
                "D10_wem": len(self.wem_by_event),
                "D11_event_to_stringid": len(self.event_to_stringid),
                "D12_strorigin": len(self.stringid_to_strorigin),
                "D13_translations": len(self.stringid_to_translations),
                "D14_item_groups": len(self.item_group_hierarchy),
                "D15_knowledge_groups": len(self.knowledge_group_hierarchy),
                "D16_region_display": len(self.region_display_names),
                "D17_export_files": len(self.export_file_stringids),
                "D18_ordered_export": len(self.ordered_export_index),
                "D19_devmemo": len(self.strkey_to_devmemo),
                "D20_event_export_path": len(self.event_to_export_path),
                "D21_event_xml_order": len(self.event_to_xml_order),
                # Reverse
                "R1_name_kr": len(self.name_kr_to_strkeys),
                "R2_knowledge_key": len(self.knowledge_key_to_entities),
                "R3_sid_to_event": len(self.stringid_to_event),
                "R4_texture_to_strkeys": len(self.ui_texture_to_strkeys),
                "R5_source_file": len(self.source_file_to_strkeys),
                "R6_strorigin_to_sids": len(self.strorigin_to_stringids),
                "R7_group_to_items": len(self.group_key_to_items),
                # Composed
                "C1_strkey_to_image": len(self.strkey_to_image_path),
                "C2_strkey_to_audio": len(self.strkey_to_audio_path),
                "C3_sid_to_audio": len(self.stringid_to_audio_path),
                "C4_event_script_kr": len(self.event_to_script_kr),
                "C5_event_script_eng": len(self.event_to_script_eng),
                "C6_entity_to_sids": len(self.entity_strkey_to_stringids),
                "C7_sid_to_entity": len(self.stringid_to_entity),
            },
        }


# =============================================================================
# Singleton
# =============================================================================

_mega_index: Optional[MegaIndex] = None


def get_mega_index() -> MegaIndex:
    """Get or create the singleton MegaIndex instance."""
    global _mega_index
    if _mega_index is None:
        _mega_index = MegaIndex()
    return _mega_index
