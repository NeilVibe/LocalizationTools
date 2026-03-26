"""
MegaIndex Builders Mixin - Phase 6 reverse and Phase 7 composed dict builders.

Handles: All _build_* methods that construct reverse lookup and composed dictionaries.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from server.tools.ldm.services.mega_index_helpers import (
    _ENTITY_TYPE_MAP,
    _get_export_key,
    _normalize_strorigin,
)
from server.tools.ldm.services.mega_index_schemas import (
    CharacterEntry,
    FactionEntry,
    GimmickEntry,
    ItemEntry,
    KnowledgeEntry,
    RegionEntry,
    SkillEntry,
)


class BuildersMixin:
    """Mixin providing Phase 6 (reverse) and Phase 7 (composed) dict builders."""

    # Type hints for self.* dicts (populated by MegaIndex.__init__)
    knowledge_by_strkey: Dict[str, KnowledgeEntry]
    character_by_strkey: Dict[str, CharacterEntry]
    item_by_strkey: Dict[str, ItemEntry]
    region_by_strkey: Dict[str, RegionEntry]
    faction_by_strkey: Dict[str, FactionEntry]
    skill_by_strkey: Dict[str, SkillEntry]
    gimmick_by_strkey: Dict[str, GimmickEntry]
    dds_by_stem: Dict[str, Path]
    wem_by_event: Dict[str, Path]
    event_to_stringid: Dict[str, str]
    stringid_to_strorigin: Dict[str, str]
    stringid_to_translations: Dict[str, Dict[str, str]]
    export_file_stringids: Dict[str, Set[str]]
    strorigin_to_stringids: Dict[str, List[str]]
    stringid_to_event: Dict[str, str]
    name_kr_to_strkeys: Dict[str, List[Tuple[str, str]]]
    knowledge_key_to_entities: Dict[str, List[Tuple[str, str]]]
    ui_texture_to_strkeys: Dict[str, List[str]]
    source_file_to_strkeys: Dict[str, List[Tuple[str, str]]]
    group_key_to_items: Dict[str, List[str]]
    strkey_to_image_path: Dict[str, Path]
    strkey_to_audio_path: Dict[str, Path]
    stringid_to_audio_path: Dict[str, Path]
    event_to_script_kr: Dict[str, str]
    event_to_script_eng: Dict[str, str]
    entity_strkey_to_stringids: Dict[str, Set[str]]
    stringid_to_entity: Dict[str, Tuple[str, str]]

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
