"""
MegaIndex - Unified game data index with 35 dicts and O(1) lookups.

Thin orchestrator that composes 4 mixin modules via multiple inheritance.
Owns: __init__ (all 35 dict declarations), build() pipeline, singleton.
Delegates: parsing, building, and API to mixin classes.

Phase 45: MegaIndex Foundation Infrastructure (Plan 03)
ARCH-02: Decomposed into 6 modules (Phase 92)
"""

from __future__ import annotations

import threading
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
        super().__init__()  # Cooperative MRO -- propagates through all mixins
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
        self._build_lock = threading.Lock()

    # =========================================================================
    # Build Pipeline
    # =========================================================================

    def _reset(self) -> None:
        """Clear all 35 dicts so rebuild starts from clean state.

        Called at the start of build() to ensure stale data from a previous
        branch/drive configuration is not carried over.
        """
        # Phase 1: Foundation
        self.knowledge_by_strkey.clear()
        self.dds_by_stem.clear()
        self.wem_by_event.clear()
        self.wem_by_event_en.clear()
        self.wem_by_event_kr.clear()
        self.wem_by_event_zh.clear()
        self.knowledge_group_hierarchy.clear()
        # Phase 2: Entity Parse
        self.character_by_strkey.clear()
        self.item_by_strkey.clear()
        self.region_by_strkey.clear()
        self.faction_by_strkey.clear()
        self.faction_group_by_strkey.clear()
        self.skill_by_strkey.clear()
        self.gimmick_by_strkey.clear()
        self.quest_by_strkey.clear()
        self.item_group_hierarchy.clear()
        self.region_display_names.clear()
        self.entity_texture_refs.clear()
        # Phase 3: Localization
        self.event_to_stringid.clear()
        self.stringid_to_strorigin.clear()
        self.stringid_to_translations.clear()
        self.export_file_stringids.clear()
        self.ordered_export_index.clear()
        self.event_to_export_path.clear()
        self.event_to_xml_order.clear()
        # Phase 5: Broad Scan
        self.strkey_to_devmemo.clear()
        # Phase 6: Reverse Dicts
        self.name_kr_to_strkeys.clear()
        self.knowledge_key_to_entities.clear()
        self.stringid_to_event.clear()
        self.ui_texture_to_strkeys.clear()
        self.source_file_to_strkeys.clear()
        self.strorigin_to_stringids.clear()
        self.group_key_to_items.clear()
        # Phase 7: Composed Dicts
        self.strkey_to_image_paths.clear()
        self.strkey_to_image_path.clear()
        self.strkey_to_audio_path.clear()
        self.stringid_to_audio_path.clear()
        self.stringid_to_audio_path_en.clear()
        self.stringid_to_audio_path_kr.clear()
        self.stringid_to_audio_path_zh.clear()
        self.event_to_script_kr.clear()
        self.event_to_script_eng.clear()
        self.entity_strkey_to_stringids.clear()
        self.stringid_to_entity.clear()
        # State
        self._built = False
        self._build_time = 0.0

    def build(self, preload_langs: Optional[List[str]] = None, on_progress: Any = None) -> None:
        """Build all 35 dicts from game data XMLs in 7-phase pipeline.

        Args:
            preload_langs: Languages to preload translations for.
                          Defaults to ["eng", "kor"].
            on_progress: Optional callback(phase: int, total: int, description: str, stats: str)
                        called after each build phase for progress tracking.

        Raises:
            RuntimeError: If a build is already in progress (concurrent build guard).
        """
        if not self._build_lock.acquire(blocking=False):
            logger.warning("[MEGAINDEX] Build already in progress -- skipping duplicate request")
            raise RuntimeError("MegaIndex build already in progress")

        try:
            self._build_locked(preload_langs, on_progress)
        finally:
            self._build_lock.release()

    def _build_locked(self, preload_langs: Optional[List[str]], on_progress: Any) -> None:
        """Internal build implementation -- must be called with _build_lock held."""
        if preload_langs is None:
            preload_langs = ["eng", "kor"]

        # Reset all dicts to ensure clean state on rebuild
        self._reset()
        logger.info("[MEGAINDEX] All dicts cleared for fresh rebuild")

        t0 = time.time()
        path_svc = get_perforce_path_service()

        try:
            paths = path_svc.get_all_resolved()
        except Exception as e:
            logger.warning(f"[MEGAINDEX] Could not resolve paths: {e}")
            paths = {}

        # Resolve key folders -- None if path not configured (never use hardcoded fallback)
        def _path_or_none(key: str):
            v = paths.get(key)
            if v is None:
                logger.warning(f"[MEGAINDEX] Path not configured: {key}")
                return None
            if not isinstance(v, (str, Path)):
                logger.error(f"[MEGAINDEX] Path {key} has unexpected type {type(v)}: {v}")
                return None
            return Path(v) if isinstance(v, str) else v

        knowledge_folder = _path_or_none("knowledge_folder")
        character_folder = _path_or_none("character_folder")
        faction_folder = _path_or_none("faction_folder")
        texture_folder = _path_or_none("texture_folder")
        audio_folder = _path_or_none("audio_folder")
        audio_folder_kr = _path_or_none("audio_folder_kr")
        audio_folder_zh = _path_or_none("audio_folder_zh")
        export_folder = _path_or_none("export_folder")
        loc_folder = _path_or_none("loc_folder")

        # StaticInfo root = parent of knowledge_folder (for skill, gimmick, devmemo)
        staticinfo_folder = knowledge_folder.parent if knowledge_folder else None
        # Item folder = sibling of other staticinfo folders
        item_folder = staticinfo_folder / "iteminfo" if staticinfo_folder else None

        # Log ALL resolved paths for debugging
        _folders = {
            "knowledge_folder": knowledge_folder, "character_folder": character_folder,
            "faction_folder": faction_folder, "item_folder": item_folder,
            "staticinfo_folder": staticinfo_folder, "texture_folder": texture_folder,
            "audio_folder": audio_folder, "audio_folder_kr": audio_folder_kr,
            "audio_folder_zh": audio_folder_zh, "export_folder": export_folder,
            "loc_folder": loc_folder,
        }
        logger.info("[MEGAINDEX] Resolved paths:")
        for name, folder in _folders.items():
            exists = folder.is_dir() if folder else False
            logger.info(f"  {name}: {folder or 'NOT CONFIGURED'} (exists={exists})")

        # Determine build context for logging
        drive = path_svc.get_status().get("drive", "?")
        branch = path_svc.get_status().get("branch", "?")
        build_label = f"{drive}:/{branch}"
        logger.info(f"[MEGAINDEX] Starting 7-phase build pipeline on {build_label}...")

        def _progress(phase: int, desc: str, stats: str) -> None:
            """Emit progress callback + log. Callback errors are non-fatal."""
            logger.info(f"[MEGAINDEX] Phase {phase}/7 complete: {stats}")
            if on_progress:
                try:
                    on_progress(phase, 7, desc, stats)
                except Exception as e:
                    logger.warning(f"[MEGAINDEX] Progress callback failed at phase {phase}: {e}")

        # ----- Phase 1: Foundation -----
        if texture_folder:
            self._scan_dds_textures(texture_folder)
        # Scan each audio language independently (some may be unconfigured)
        if audio_folder:
            self._scan_wem_into(audio_folder, self.wem_by_event_en, "EN")
        if audio_folder_kr:
            self._scan_wem_into(audio_folder_kr, self.wem_by_event_kr, "KR")
        if audio_folder_zh:
            self._scan_wem_into(audio_folder_zh, self.wem_by_event_zh, "ZH")
        self.wem_by_event = self.wem_by_event_en  # Backward compat alias
        if knowledge_folder:
            self._parse_knowledge_info(knowledge_folder)
        _progress(1, "Foundation -- textures, audio, knowledge", (
            f"{len(self.knowledge_by_strkey)} knowledge, "
            f"{len(self.dds_by_stem)} DDS, WEM EN={len(self.wem_by_event_en)} "
            f"KR={len(self.wem_by_event_kr)} ZH={len(self.wem_by_event_zh)}, "
            f"{len(self.knowledge_group_hierarchy)} knowledge groups"
        ))

        # ----- Phase 2: Entity Parse -----
        if character_folder:
            self._parse_character_info(character_folder)
        if item_folder and knowledge_folder:
            self._parse_item_info(item_folder, knowledge_folder)
        if faction_folder:
            self._parse_faction_info(faction_folder)
        if staticinfo_folder:
            self._parse_skill_info(staticinfo_folder)
            self._parse_gimmick_info(staticinfo_folder)
            self._parse_quest_info(staticinfo_folder)
        _progress(2, "Entity Parse -- characters, items, factions, skills, quests", (
            f"{len(self.character_by_strkey)} characters, "
            f"{len(self.item_by_strkey)} items, {len(self.region_by_strkey)} regions, "
            f"{len(self.faction_by_strkey)} factions, {len(self.skill_by_strkey)} skills, "
            f"{len(self.gimmick_by_strkey)} gimmicks, {len(self.quest_by_strkey)} quests"
        ))

        # ----- Phase 3: Localization -----
        if loc_folder:
            self._parse_loc_strorigin(loc_folder)
            self._parse_loc_translations(loc_folder, preload_langs)
        if export_folder:
            self._parse_export_events(export_folder)
            self._parse_export_loc(export_folder)
        _progress(3, "Localization -- strings, translations, exports", (
            f"{len(self.stringid_to_strorigin)} strorigins, "
            f"{len(self.event_to_stringid)} event->stringid, "
            f"{len(self.export_file_stringids)} export files"
        ))

        # ----- Phase 4: VRS chronological reorder -----
        vrs_folder = paths.get("vrs_folder")
        if vrs_folder:
            self._apply_vrs_order(Path(vrs_folder))
        else:
            logger.info("[MEGAINDEX] VRS folder not configured -- using raw XML order")
        _progress(4, "VRS reorder", "chronological order applied")

        # ----- Phase 5: Broad Scan -----
        if staticinfo_folder:
            self._scan_devmemo(staticinfo_folder)
        _progress(5, "Broad Scan -- developer memos", (
            f"{len(self.strkey_to_devmemo)} devmemo entries"
        ))

        # ----- Phase 6: Reverse Dicts -----
        self._build_name_kr_to_strkeys()
        self._build_knowledge_key_to_entities()
        self._build_stringid_to_event()
        self._build_ui_texture_to_strkeys()
        self._build_source_file_to_strkeys()
        self._build_strorigin_to_stringids()
        self._build_group_key_to_items()
        _progress(6, "Reverse Dicts -- R1-R7 lookup indexes", (
            f"R1={len(self.name_kr_to_strkeys)}, "
            f"R2={len(self.knowledge_key_to_entities)}, R3={len(self.stringid_to_event)}, "
            f"R4={len(self.ui_texture_to_strkeys)}, R5={len(self.source_file_to_strkeys)}, "
            f"R6={len(self.strorigin_to_stringids)}, R7={len(self.group_key_to_items)}"
        ))

        # ----- Phase 7: Composed Dicts -----
        self._build_strkey_to_image_path()
        self._build_strkey_to_audio_path()
        self._build_stringid_to_audio_path()
        self._build_event_to_script_kr()
        self._build_event_to_script_eng()
        self._build_entity_strkey_to_stringids()
        self._build_stringid_to_entity_map()
        _progress(7, "Composed Dicts -- C1-C7 image/audio/entity chains", (
            f"C1={len(self.strkey_to_image_path)}, "
            f"C2={len(self.strkey_to_audio_path)}, C3={len(self.stringid_to_audio_path)}, "
            f"C4={len(self.event_to_script_kr)}, C5={len(self.event_to_script_eng)}, "
            f"C6={len(self.entity_strkey_to_stringids)}, C7={len(self.stringid_to_entity)}"
        ))

        self._build_time = time.time() - t0
        self._built = True
        logger.success(f"[MEGAINDEX] BUILD COMPLETE on {build_label} in {self._build_time:.2f}s")


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
