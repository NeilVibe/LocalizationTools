"""
MegaIndex - Unified game data index with 35 dicts and O(1) lookups.

Thin orchestrator that composes 4 mixin modules via multiple inheritance.
Owns: __init__ (all 35 dict declarations), build() pipeline, singleton.
Delegates: parsing, building, and API to mixin classes.

Phase 45: MegaIndex Foundation Infrastructure (Plan 03)
ARCH-02: Decomposed into 6 modules (Phase 92)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from server.tools.ldm.services.mega_index_api import ApiMixin
from server.tools.ldm.services.mega_index_builders import BuildersMixin
from server.tools.ldm.services.mega_index_data_parsers import DataParsersMixin
from server.tools.ldm.services.mega_index_entity_parsers import EntityParsersMixin
from server.tools.ldm.services.mega_index_schemas import (
    CharacterEntry,
    FactionEntry,
    FactionGroupEntry,
    GimmickEntry,
    ItemEntry,
    ItemGroupNode,
    KnowledgeEntry,
    KnowledgeGroupNode,
    QuestEntry,
    RegionEntry,
    SkillEntry,
)
from server.tools.ldm.services.perforce_path_service import get_perforce_path_service

# Re-export helpers for backward compatibility (callers/tools may import these)
from server.tools.ldm.services.mega_index_helpers import (  # noqa: F401
    LANG_TO_AUDIO,
    _BR_TAG_RE,
    _ENTITY_TYPE_MAP,
    _PLACEHOLDER_SUFFIX_RE,
    _WHITESPACE_RE,
    _find_knowledge_key,
    _get_export_key,
    _get_stringid,
    _normalize_strorigin,
    _parse_world_position,
    _safe_parse_xml,
)


# =============================================================================
# MegaIndex
# =============================================================================


class MegaIndex(DataParsersMixin, EntityParsersMixin, BuildersMixin, ApiMixin):
    """Unified game data index with 35 dicts and O(1) lookups in every direction.

    Build pipeline follows 7-phase order from MEGAINDEX_DESIGN.md Section 3.
    All parse methods are wrapped in try/except for graceful degradation.
    """

    def __init__(self) -> None:
        super().__init__()  # Cooperative MRO — propagates through all mixins
        # === Phase 1: Foundation (Direct Dicts) ===
        self.knowledge_by_strkey: Dict[str, KnowledgeEntry] = {}  # D1
        self.dds_by_stem: Dict[str, Path] = {}  # D9
        self.wem_by_event: Dict[str, Path] = {}  # D10 (backward compat alias -> English)
        self.wem_by_event_en: Dict[str, Path] = {}  # D10a: English(US) audio
        self.wem_by_event_kr: Dict[str, Path] = {}  # D10b: Korean audio
        self.wem_by_event_zh: Dict[str, Path] = {}  # D10c: Chinese(PRC) audio
        self.knowledge_group_hierarchy: Dict[str, KnowledgeGroupNode] = {}  # D15

        # === Phase 2: Entity Parse ===
        self.character_by_strkey: Dict[str, CharacterEntry] = {}  # D2
        self.item_by_strkey: Dict[str, ItemEntry] = {}  # D3
        self.region_by_strkey: Dict[str, RegionEntry] = {}  # D4
        self.faction_by_strkey: Dict[str, FactionEntry] = {}  # D5
        self.faction_group_by_strkey: Dict[str, FactionGroupEntry] = {}  # D6
        self.skill_by_strkey: Dict[str, SkillEntry] = {}  # D7
        self.gimmick_by_strkey: Dict[str, GimmickEntry] = {}  # D8
        self.quest_by_strkey: Dict[str, QuestEntry] = {}  # D7b (quests)
        self.item_group_hierarchy: Dict[str, ItemGroupNode] = {}  # D14
        self.region_display_names: Dict[str, str] = {}  # D16
        # Greedy DDS: texture refs collected during entity parsing
        self.entity_texture_refs: Dict[str, List[str]] = {}  # strkey -> [texture_value, ...]

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
        self.strkey_to_image_paths: Dict[str, List[Path]] = {}  # C1 (greedy: multiple images per entity)
        self.strkey_to_image_path: Dict[str, Path] = {}  # C1 compat (first image only)
        self.strkey_to_audio_path: Dict[str, Path] = {}  # C2
        self.stringid_to_audio_path: Dict[str, Path] = {}  # C3 (backward compat -> English)
        self.stringid_to_audio_path_en: Dict[str, Path] = {}  # C3a
        self.stringid_to_audio_path_kr: Dict[str, Path] = {}  # C3b
        self.stringid_to_audio_path_zh: Dict[str, Path] = {}  # C3c
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
        audio_folder_kr = paths.get("audio_folder_kr", Path("/nonexistent"))
        audio_folder_zh = paths.get("audio_folder_zh", Path("/nonexistent"))
        export_folder = paths.get("export_folder", Path("/nonexistent"))
        loc_folder = paths.get("loc_folder", Path("/nonexistent"))

        # StaticInfo root = parent of knowledge_folder (for skill, gimmick, devmemo)
        staticinfo_folder = knowledge_folder.parent if knowledge_folder != Path("/nonexistent") else Path("/nonexistent")
        # Item folder = sibling of other staticinfo folders
        item_folder = staticinfo_folder / "iteminfo"

        # Log ALL resolved paths for debugging
        logger.info(f"[MEGAINDEX] Resolved paths:")
        logger.info(f"  knowledge_folder: {knowledge_folder} (exists={knowledge_folder.is_dir() if knowledge_folder != Path('/nonexistent') else False})")
        logger.info(f"  character_folder: {character_folder} (exists={character_folder.is_dir() if character_folder != Path('/nonexistent') else False})")
        logger.info(f"  faction_folder:   {faction_folder} (exists={faction_folder.is_dir() if faction_folder != Path('/nonexistent') else False})")
        logger.info(f"  item_folder:      {item_folder} (exists={item_folder.is_dir()})")
        logger.info(f"  staticinfo_folder:{staticinfo_folder} (exists={staticinfo_folder.is_dir() if staticinfo_folder != Path('/nonexistent') else False})")
        logger.info(f"  texture_folder:   {texture_folder} (exists={texture_folder.is_dir() if texture_folder != Path('/nonexistent') else False})")
        logger.info(f"  audio_folder:     {audio_folder} (exists={audio_folder.is_dir() if audio_folder != Path('/nonexistent') else False})")
        logger.info(f"  audio_folder_kr:  {audio_folder_kr} (exists={audio_folder_kr.is_dir() if audio_folder_kr != Path('/nonexistent') else False})")
        logger.info(f"  audio_folder_zh:  {audio_folder_zh} (exists={audio_folder_zh.is_dir() if audio_folder_zh != Path('/nonexistent') else False})")
        logger.info(f"  export_folder:    {export_folder} (exists={export_folder.is_dir() if export_folder != Path('/nonexistent') else False})")
        logger.info(f"  loc_folder:       {loc_folder} (exists={loc_folder.is_dir() if loc_folder != Path('/nonexistent') else False})")

        logger.info("[MEGAINDEX] Starting 7-phase build pipeline...")

        # ----- Phase 1: Foundation -----
        self._scan_dds_textures(texture_folder)
        self._scan_wem_files_all_languages(audio_folder, audio_folder_kr, audio_folder_zh)
        self.wem_by_event = self.wem_by_event_en  # Backward compat alias
        self._parse_knowledge_info(knowledge_folder)
        logger.info(
            f"[MEGAINDEX] Phase 1 complete: {len(self.knowledge_by_strkey)} knowledge, "
            f"{len(self.dds_by_stem)} DDS, WEM EN={len(self.wem_by_event_en)} "
            f"KR={len(self.wem_by_event_kr)} ZH={len(self.wem_by_event_zh)}, "
            f"{len(self.knowledge_group_hierarchy)} knowledge groups"
        )

        # ----- Phase 2: Entity Parse -----
        self._parse_character_info(character_folder)
        self._parse_item_info(item_folder, knowledge_folder)
        self._parse_faction_info(faction_folder)
        self._parse_skill_info(staticinfo_folder)
        self._parse_gimmick_info(staticinfo_folder)
        self._parse_quest_info(staticinfo_folder)
        logger.info(
            f"[MEGAINDEX] Phase 2 complete: {len(self.character_by_strkey)} characters, "
            f"{len(self.item_by_strkey)} items, {len(self.region_by_strkey)} regions, "
            f"{len(self.faction_by_strkey)} factions, {len(self.skill_by_strkey)} skills, "
            f"{len(self.gimmick_by_strkey)} gimmicks, {len(self.quest_by_strkey)} quests"
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


# =============================================================================
# Singleton
# =============================================================================

_mega_index: Optional[MegaIndex] = None


def get_mega_index() -> MegaIndex:
    """Get or create the singleton MegaIndex instance."""
    global _mega_index
    if _mega_index is None:
        logger.info("[MEGAINDEX] Creating singleton MegaIndex instance")
        _mega_index = MegaIndex()
    else:
        logger.debug("[MEGAINDEX] Returning existing MegaIndex (is_built=%s)", _mega_index._built)
    return _mega_index
