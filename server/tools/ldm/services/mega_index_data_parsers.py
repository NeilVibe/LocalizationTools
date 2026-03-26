"""
MegaIndex Data Parsers Mixin - Phase 1, 3, and 5 parsing methods.

Handles: DDS texture scanning, WEM audio scanning, knowledge parsing,
localization (strorigin, translations), export events/loc, and devmemo scanning.

Extracted from mega_index.py during ARCH-02 decomposition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from server.tools.ldm.services.mega_index_helpers import (
    _get_export_key,
    _get_stringid,
    _normalize_strorigin,
    _safe_parse_xml,
)
from server.tools.ldm.services.mega_index_schemas import (
    KnowledgeEntry,
    KnowledgeGroupNode,
)


class DataParsersMixin:
    """Mixin providing Phase 1 (foundation), Phase 3 (localization), and Phase 5 (broad scan) parsers."""

    # Type hints for self.* dicts (populated by MegaIndex.__init__)
    knowledge_by_strkey: Dict[str, KnowledgeEntry]
    dds_by_stem: Dict[str, Path]
    wem_by_event: Dict[str, Path]
    knowledge_group_hierarchy: Dict[str, KnowledgeGroupNode]
    event_to_stringid: Dict[str, str]
    stringid_to_strorigin: Dict[str, str]
    stringid_to_translations: Dict[str, Dict[str, str]]
    export_file_stringids: Dict[str, Set[str]]
    ordered_export_index: Dict[str, Dict[str, List[str]]]
    event_to_export_path: Dict[str, str]
    event_to_xml_order: Dict[str, int]
    strkey_to_devmemo: Dict[str, str]

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
