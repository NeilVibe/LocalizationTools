"""
MegaIndex API Mixin - All public accessor methods.

Handles: Entity lookups, media lookups, localization lookups, bridge lookups,
reverse lookups, hierarchy accessors, and bulk/stats methods.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from server.tools.ldm.services.mega_index_helpers import (
    LANG_TO_AUDIO,
    _ENTITY_TYPE_MAP,
    _normalize_strorigin,
)
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


class ApiMixin:
    """Mixin providing all public API methods for MegaIndex."""

    # Type hints for self.* dicts (populated by MegaIndex.__init__)
    knowledge_by_strkey: Dict[str, KnowledgeEntry]
    character_by_strkey: Dict[str, CharacterEntry]
    item_by_strkey: Dict[str, ItemEntry]
    region_by_strkey: Dict[str, RegionEntry]
    faction_by_strkey: Dict[str, FactionEntry]
    faction_group_by_strkey: Dict[str, FactionGroupEntry]
    skill_by_strkey: Dict[str, SkillEntry]
    gimmick_by_strkey: Dict[str, GimmickEntry]
    quest_by_strkey: Dict[str, QuestEntry]
    dds_by_stem: Dict[str, Path]
    wem_by_event: Dict[str, Path]
    wem_by_event_en: Dict[str, Path]
    wem_by_event_kr: Dict[str, Path]
    wem_by_event_zh: Dict[str, Path]
    event_to_stringid: Dict[str, str]
    stringid_to_strorigin: Dict[str, str]
    stringid_to_translations: Dict[str, Dict[str, str]]
    item_group_hierarchy: Dict[str, ItemGroupNode]
    knowledge_group_hierarchy: Dict[str, KnowledgeGroupNode]
    region_display_names: Dict[str, str]
    export_file_stringids: Dict[str, Set[str]]
    ordered_export_index: Dict[str, Dict[str, List[str]]]
    strkey_to_devmemo: Dict[str, str]
    event_to_export_path: Dict[str, str]
    event_to_xml_order: Dict[str, int]
    name_kr_to_strkeys: Dict[str, List[Tuple[str, str]]]
    knowledge_key_to_entities: Dict[str, List[Tuple[str, str]]]
    stringid_to_event: Dict[str, str]
    ui_texture_to_strkeys: Dict[str, List[str]]
    source_file_to_strkeys: Dict[str, List[Tuple[str, str]]]
    strorigin_to_stringids: Dict[str, List[str]]
    group_key_to_items: Dict[str, List[str]]
    strkey_to_image_path: Dict[str, Path]
    strkey_to_audio_path: Dict[str, Path]
    stringid_to_audio_path: Dict[str, Path]
    stringid_to_audio_path_en: Dict[str, Path]
    stringid_to_audio_path_kr: Dict[str, Path]
    stringid_to_audio_path_zh: Dict[str, Path]
    event_to_script_kr: Dict[str, str]
    event_to_script_eng: Dict[str, str]
    entity_strkey_to_stringids: Dict[str, Set[str]]
    stringid_to_entity: Dict[str, Tuple[str, str]]
    _built: bool
    _build_time: float

    # =========================================================================
    # Public API: Direct Entity Lookups
    # =========================================================================

    def get_knowledge(self, strkey: str) -> Optional[KnowledgeEntry]:
        """O(1) knowledge entity lookup by StrKey."""
        return self.knowledge_by_strkey.get(strkey.lower())

    def get_character(self, strkey: str) -> Optional[CharacterEntry]:
        """O(1) character entity lookup by StrKey."""
        return self.character_by_strkey.get(strkey.lower())

    def get_item(self, strkey: str) -> Optional[ItemEntry]:
        """O(1) item entity lookup by StrKey."""
        return self.item_by_strkey.get(strkey.lower())

    def get_region(self, strkey: str) -> Optional[RegionEntry]:
        """O(1) region entity lookup by StrKey."""
        return self.region_by_strkey.get(strkey.lower())

    def get_skill(self, strkey: str) -> Optional[SkillEntry]:
        """O(1) skill entity lookup by StrKey."""
        return self.skill_by_strkey.get(strkey.lower())

    def get_gimmick(self, strkey: str) -> Optional[GimmickEntry]:
        """O(1) gimmick entity lookup by StrKey."""
        return self.gimmick_by_strkey.get(strkey.lower())

    def get_quest(self, strkey: str) -> Optional[QuestEntry]:
        """O(1) quest entity lookup by StrKey."""
        return self.quest_by_strkey.get(strkey.lower())

    def get_entity(self, entity_type: str, strkey: str) -> Optional[Any]:
        """O(1) entity lookup by type and StrKey."""
        entity_type = entity_type.lower()
        attr_name = _ENTITY_TYPE_MAP.get(entity_type)
        if not attr_name:
            return None
        d = getattr(self, attr_name, {})
        return d.get(strkey.lower())

    # =========================================================================
    # Public API: Media Lookups
    # =========================================================================

    def get_image_path(self, strkey: str) -> Optional[Path]:
        """C1: StrKey -> first image DDS path (backward compat)."""
        return self.strkey_to_image_path.get(strkey.lower())

    def get_image_paths(self, strkey: str) -> List[Path]:
        """C1: StrKey -> ALL image DDS paths (greedy, unique, deduped by stem)."""
        return self.strkey_to_image_paths.get(strkey.lower(), [])

    def get_audio_path_by_event(self, event_name: str) -> Optional[Path]:
        """D10: Event name -> WEM audio path."""
        return self.wem_by_event.get(event_name.lower())

    def get_audio_path_by_stringid(self, string_id: str) -> Optional[Path]:
        """C3: StringId -> audio WEM path."""
        return self.stringid_to_audio_path.get(string_id.lower())

    def get_dds_path(self, texture_name: str) -> Optional[Path]:
        """D9: Texture name (stem) -> DDS path."""
        return self.dds_by_stem.get(texture_name.lower())

    def get_audio_path_by_stringid_for_lang(self, string_id: str, file_language: str) -> Optional[Path]:
        """C3 language-aware: StringId + file language -> correct WEM path.

        Routes through LANG_TO_AUDIO mapping:
        - Latin langs (eng, fre, ger, etc.) -> English(US) audio
        - KOR, JPN, ZHO-TW -> Korean audio
        - ZHO-CN -> Chinese(PRC) audio

        Falls back to English if language unknown.
        """
        lang_key = LANG_TO_AUDIO.get(file_language.lower(), "en")
        sid_lower = string_id.lower()
        if lang_key == "kr":
            return self.stringid_to_audio_path_kr.get(sid_lower)
        elif lang_key == "zh":
            return self.stringid_to_audio_path_zh.get(sid_lower)
        else:
            return self.stringid_to_audio_path_en.get(sid_lower)

    def get_audio_path_by_event_for_lang(self, event_name: str, file_language: str) -> Optional[Path]:
        """D10 language-aware: Event name + file language -> correct WEM path."""
        lang_key = LANG_TO_AUDIO.get(file_language.lower(), "en")
        en_lower = event_name.lower()
        if lang_key == "kr":
            return self.wem_by_event_kr.get(en_lower)
        elif lang_key == "zh":
            return self.wem_by_event_zh.get(en_lower)
        else:
            return self.wem_by_event_en.get(en_lower)

    # =========================================================================
    # Public API: Localization Lookups
    # =========================================================================

    def get_strorigin(self, string_id: str) -> Optional[str]:
        """D12: StringId -> Korean StrOrigin text."""
        return self.stringid_to_strorigin.get(string_id.lower())

    def get_translation(self, string_id: str, lang: str) -> Optional[str]:
        """D13: StringId + language -> translated text."""
        translations = self.stringid_to_translations.get(string_id.lower(), {})
        return translations.get(lang.lower())

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
        return self.stringid_to_entity.get(string_id.lower())

    def entity_stringids(self, entity_type: str, strkey: str) -> Set[str]:
        """C6: Entity (type, strkey) -> set of StringIds."""
        return self.entity_strkey_to_stringids.get(strkey.lower(), set())

    def event_to_stringid_lookup(self, event_name: str) -> Optional[str]:
        """D11: Event name -> StringId."""
        return self.event_to_stringid.get(event_name.lower())

    def stringid_to_event_lookup(self, string_id: str) -> Optional[str]:
        """R3: StringId -> event name."""
        return self.stringid_to_event.get(string_id.lower())

    # =========================================================================
    # Public API: Reverse Lookups
    # =========================================================================

    def find_by_korean_name(self, name_kr: str) -> List[Tuple[str, str]]:
        """R1: Korean name -> list of (entity_type, strkey) matches."""
        return self.name_kr_to_strkeys.get(name_kr.lower(), [])

    def find_by_knowledge_key(self, key: str) -> List[Tuple[str, str]]:
        """R2: Knowledge key -> list of (entity_type, strkey) that reference it."""
        return self.knowledge_key_to_entities.get(key.lower(), [])

    def find_by_source_file(self, filename: str) -> List[Tuple[str, str]]:
        """R5: Source filename -> list of (entity_type, strkey) from that file."""
        return self.source_file_to_strkeys.get(filename.lower(), [])

    def find_stringids_by_korean(self, text: str) -> List[str]:
        """R6: Korean text (normalized+lowercased) -> list of matching StringIds."""
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
            "quest": len(self.quest_by_strkey),
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
                "D7b_quest": len(self.quest_by_strkey),
                "D9_dds": len(self.dds_by_stem),
                "D10_wem": len(self.wem_by_event),
                "D10_wem_en": len(self.wem_by_event_en),
                "D10_wem_kr": len(self.wem_by_event_kr),
                "D10_wem_zh": len(self.wem_by_event_zh),
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
