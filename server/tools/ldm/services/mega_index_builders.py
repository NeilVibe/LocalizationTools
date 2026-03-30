"""
MegaIndex Builders Mixin - Phase 6 reverse and Phase 7 composed dict builders.

Handles: All _build_* methods that construct reverse lookup and composed dictionaries.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

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
    wem_by_event_en: Dict[str, Path]
    wem_by_event_kr: Dict[str, Path]
    wem_by_event_zh: Dict[str, Path]
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
    strkey_to_image_paths: Dict[str, List[Path]]
    strkey_to_image_path: Dict[str, Path]
    entity_texture_refs: Dict[str, List[str]]
    strkey_to_audio_path: Dict[str, Path]
    stringid_to_audio_path: Dict[str, Path]
    stringid_to_audio_path_en: Dict[str, Path]
    stringid_to_audio_path_kr: Dict[str, Path]
    stringid_to_audio_path_zh: Dict[str, Path]
    event_to_script_kr: Dict[str, str]
    event_to_script_eng: Dict[str, str]
    entity_strkey_to_stringids: Dict[str, Set[str]]
    stringid_to_entity: Dict[str, Tuple[str, str]]

    # =========================================================================
    # Phase 6: Reverse Dict Builders
    # =========================================================================

    def _build_name_kr_to_strkeys(self) -> None:
        """R1: Invert name fields from D1, D2, D3, D4. Keys lowercased."""
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
                    result.setdefault(name.lower(), []).append((entity_type, strkey))
        self.name_kr_to_strkeys = result
        logger.debug(f"[MEGAINDEX] R1 name_kr_to_strkeys: {len(result)} unique names")

    def _build_knowledge_key_to_entities(self) -> None:
        """R2: Scan D2, D3, D4, D7 for knowledge_key references. Keys lowercased."""
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
                    result.setdefault(kk.lower(), []).append((entity_type, strkey))
        self.knowledge_key_to_entities = result
        logger.debug(f"[MEGAINDEX] R2 knowledge_key_to_entities: {len(result)} keys")

    def _build_stringid_to_event(self) -> None:
        """R3: Invert D11 (event_to_stringid)."""
        result: Dict[str, str] = {}
        for event_lower, sid in self.event_to_stringid.items():
            result[sid] = event_lower
        self.stringid_to_event = result
        logger.debug(f"[MEGAINDEX] R3 stringid_to_event: {len(result)} mappings")

    def _build_ui_texture_to_strkeys(self) -> None:
        """R4: Invert D1.ui_texture_name (lowercased)."""
        result: Dict[str, List[str]] = {}
        for strkey, entry in self.knowledge_by_strkey.items():
            tex = entry.ui_texture_name
            if tex:
                result.setdefault(tex.lower(), []).append(strkey)
        self.ui_texture_to_strkeys = result
        logger.debug(f"[MEGAINDEX] R4 ui_texture_to_strkeys: {len(result)} textures")

    def _build_source_file_to_strkeys(self) -> None:
        """R5: Scan all entity dicts for source_file grouping. Keys lowercased."""
        result: Dict[str, List[Tuple[str, str]]] = {}
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey, entry in d.items():
                sf = getattr(entry, "source_file", "")
                if sf:
                    result.setdefault(sf.lower(), []).append((entity_type, strkey))
        self.source_file_to_strkeys = result
        logger.debug(f"[MEGAINDEX] R5 source_file_to_strkeys: {len(result)} files")

    def _build_strorigin_to_stringids(self) -> None:
        """R6: Invert D12 with StrOrigin normalization."""
        result: Dict[str, List[str]] = {}
        for sid, strorigin in self.stringid_to_strorigin.items():
            normalized = _normalize_strorigin(strorigin)
            if normalized:
                result.setdefault(normalized, []).append(sid)
        self.strorigin_to_stringids = result
        logger.debug(f"[MEGAINDEX] R6 strorigin_to_stringids: {len(result)} unique origins")

    def _build_group_key_to_items(self) -> None:
        """R7: From D3, accumulate items per group_key. Keys lowercased."""
        result: Dict[str, List[str]] = {}
        for strkey, entry in self.item_by_strkey.items():
            gk = entry.group_key
            if gk:
                result.setdefault(gk.lower(), []).append(strkey)
        self.group_key_to_items = result
        logger.debug(f"[MEGAINDEX] R7 group_key_to_items: {len(result)} groups")

    # =========================================================================
    # Phase 7: Composed Dict Builders
    # =========================================================================

    def _find_dds(self, ui_texture_name: str) -> Optional[Path]:
        """GRAFTED from MDG DDSIndex.find() — exact same lookup chain.

        1. Strip path components (/ or \\)
        2. Try stem without extension
        3. Try with original casing
        4. Try stem + .dds
        5. FALLBACK: substring match (either direction)
        """
        if not ui_texture_name:
            return None
        name = ui_texture_name.lower().strip()

        # Strip path components (MDG: remove everything before last / or \\)
        if "/" in name or "\\" in name:
            name = name.replace("\\", "/").split("/")[-1]

        # Remove .dds extension for lookup
        lookup_name = name
        if lookup_name.endswith(".dds"):
            lookup_name = lookup_name[:-4]

        # Attempt 1: stem without extension
        if lookup_name in self.dds_by_stem:
            return self.dds_by_stem[lookup_name]

        # Attempt 2: with .dds extension (hits dual-key slot)
        if name in self.dds_by_stem:
            return self.dds_by_stem[name]

        # Attempt 3: add .dds
        name_with_ext = lookup_name + ".dds"
        if name_with_ext in self.dds_by_stem:
            return self.dds_by_stem[name_with_ext]

        # Attempt 4: FALLBACK — substring match (MDG safety net)
        for key in self.dds_by_stem:
            if lookup_name in key or key in lookup_name:
                logger.debug(f"[MEGAINDEX] DDS fuzzy match: '{ui_texture_name}' -> '{key}'")
                return self.dds_by_stem[key]

        logger.debug(f"[MEGAINDEX] DDS NOT FOUND: '{ui_texture_name}' (tried: '{lookup_name}')")
        return None

    def _build_strkey_to_image_path(self) -> None:
        """C1: Greedy multi-source DDS image resolution.

        Three-phase image lookup:
          Phase A: KnowledgeEntry.ui_texture_name (original, highest priority)
          Phase B: entity_texture_refs collected during parsing (greedy scan of all
                   texture/icon/image attributes from XML nodes + immediate children)
          Phase C: Korean name R1 fallback — if entity has same Korean name as another
                   entity that HAS images, inherit those images

        Result: strkey_to_image_paths[strkey] = [Path, ...] (unique, deduped by stem)
        Backward compat: strkey_to_image_path[strkey] = first Path
        """
        # Phase A: Knowledge UITextureName (original path)
        phase_a_hits = 0
        for strkey, entry in self.knowledge_by_strkey.items():
            tex = entry.ui_texture_name
            if tex:
                dds = self._find_dds(tex)
                if dds:
                    self.strkey_to_image_paths.setdefault(strkey, []).append(dds)
                    phase_a_hits += 1

        # Phase B: Greedy texture refs from entity parsing
        phase_b_hits = 0
        for strkey, refs in self.entity_texture_refs.items():
            for ref_val in refs:
                dds = self._find_dds(ref_val)
                if dds:
                    existing = self.strkey_to_image_paths.setdefault(strkey, [])
                    # Dedup by stem
                    if not any(p.stem == dds.stem for p in existing):
                        existing.append(dds)
                        phase_b_hits += 1

        # Phase C: Korean name R1 fallback — entities with matching Korean names share images
        phase_c_hits = 0
        all_entity_dicts = [
            self.character_by_strkey, self.item_by_strkey,
            self.skill_by_strkey, self.gimmick_by_strkey,
        ]
        for entity_dict in all_entity_dicts:
            for strkey, entry in entity_dict.items():
                if strkey in self.strkey_to_image_paths:
                    continue  # Already has images
                name_kr = getattr(entry, "name", "").strip().lower()
                if not name_kr:
                    continue
                # Look up entities with same Korean name via R1
                matches = self.name_kr_to_strkeys.get(name_kr, [])
                for match_type, match_strkey in matches:
                    if match_strkey == strkey:
                        continue
                    donor_images = self.strkey_to_image_paths.get(match_strkey, [])
                    if donor_images:
                        existing = self.strkey_to_image_paths.setdefault(strkey, [])
                        for dds in donor_images:
                            if not any(p.stem == dds.stem for p in existing):
                                existing.append(dds)
                                phase_c_hits += 1
                        break  # One donor is enough

        # Backward compat: strkey_to_image_path = first image
        for strkey, paths in self.strkey_to_image_paths.items():
            if paths:
                self.strkey_to_image_path[strkey] = paths[0]

        total = len(self.strkey_to_image_paths)
        logger.info(
            f"[MEGAINDEX] C1 greedy images: {total} entities with images "
            f"(A={phase_a_hits} knowledge, B={phase_b_hits} greedy attrs, C={phase_c_hits} kr-name fallback)"
        )

    def _build_strkey_to_audio_path(self) -> None:
        """C2: Entity StrKey -> knowledge_key -> event -> WEM path (complex chain).

        Uses wem_by_event_en for backward compat (C2 is entity-based, not file-language-based).
        """
        # For each entity with a knowledge_key, try to find an event that maps to audio
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey, entry in d.items():
                kk = getattr(entry, "knowledge_key", "") or getattr(
                    entry, "learn_knowledge_key", ""
                )
                if not kk:
                    continue
                # Direct path: check if event_name matches strkey pattern
                sk_lower = strkey.lower()
                wem = self.wem_by_event_en.get(sk_lower)
                if wem:
                    self.strkey_to_audio_path[strkey] = wem
        logger.debug(f"[MEGAINDEX] C2 strkey_to_audio_path: {len(self.strkey_to_audio_path)} resolved")

    def _build_stringid_to_audio_path(self) -> None:
        """C3: StringId -> event_name (R3) -> WEM path (D10), per language."""
        for sid, event_lower in self.stringid_to_event.items():
            # English
            wem = self.wem_by_event_en.get(event_lower)
            if wem:
                self.stringid_to_audio_path_en[sid] = wem
            # Korean
            wem = self.wem_by_event_kr.get(event_lower)
            if wem:
                self.stringid_to_audio_path_kr[sid] = wem
            # Chinese
            wem = self.wem_by_event_zh.get(event_lower)
            if wem:
                self.stringid_to_audio_path_zh[sid] = wem
        # Backward compat: default = English
        self.stringid_to_audio_path = self.stringid_to_audio_path_en
        logger.debug(
            f"[MEGAINDEX] C3 stringid_to_audio_path: EN={len(self.stringid_to_audio_path_en)}, "
            f"KR={len(self.stringid_to_audio_path_kr)}, ZH={len(self.stringid_to_audio_path_zh)}"
        )

    def _build_event_to_script_kr(self) -> None:
        """C4: event -> StringId (D11) -> StrOrigin (D12)."""
        for event_lower, sid in self.event_to_stringid.items():
            origin = self.stringid_to_strorigin.get(sid)
            if origin:
                self.event_to_script_kr[event_lower] = origin
        logger.debug(f"[MEGAINDEX] C4 event_to_script_kr: {len(self.event_to_script_kr)} scripts")

    def _build_event_to_script_eng(self) -> None:
        """C5: event -> StringId (D11) -> ENG translation (D13)."""
        for event_lower, sid in self.event_to_stringid.items():
            translations = self.stringid_to_translations.get(sid, {})
            eng = translations.get("eng")
            if eng:
                self.event_to_script_eng[event_lower] = eng
        logger.debug(f"[MEGAINDEX] C5 event_to_script_eng: {len(self.event_to_script_eng)} scripts")

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
        logger.debug(f"[MEGAINDEX] C6 entity_strkey_to_stringids: {len(self.entity_strkey_to_stringids)} entities mapped to StringIDs")

    def _build_stringid_to_entity_map(self) -> None:
        """C7: Invert C6 -- StringId -> (entity_type, strkey)."""
        for entity_type, attr_name in _ENTITY_TYPE_MAP.items():
            d = getattr(self, attr_name, {})
            for strkey in d:
                sids = self.entity_strkey_to_stringids.get(strkey, set())
                for sid in sids:
                    if sid not in self.stringid_to_entity:
                        self.stringid_to_entity[sid] = (entity_type, strkey)
        logger.debug(f"[MEGAINDEX] C7 stringid_to_entity: {len(self.stringid_to_entity)} StringIDs mapped to entities")
