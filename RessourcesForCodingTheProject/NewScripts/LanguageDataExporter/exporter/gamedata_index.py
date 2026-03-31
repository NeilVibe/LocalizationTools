"""
GameData Reverse Index — Korean Text → Name/Desc Attribute Classification.

Parses StaticInfo, staticinfo_quest, staticinfo_dialog XMLs to build a reverse
lookup: given a Korean text (StrOrigin from LanguageData), determine whether it
appears as a Name-type attribute or a Desc-type attribute in GameData.

Name-type attributes are glossary-worthy (entity labels).
Desc-type attributes are descriptions (not glossary-worthy).

Attribute classification:
  NAME: Name, GroupName, CharacterName, GimmickName, DevMemo, DevComment, DisplayName
  DESC: Desc, QuestDescription, LevelData.Desc

Category is derived from the source filename using the same keyword-matching
logic as QACompiler's gamedata_clusterer (priority keywords + folder patterns).
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree as ET

logger = logging.getLogger(__name__)

# =============================================================================
# ATTRIBUTE CLASSIFICATION
# =============================================================================

# Attributes that indicate "this is a name/label" — glossary-worthy
NAME_ATTRIBUTES = {
    "Name", "GroupName", "CharacterName", "GimmickName",
    "DevMemo", "DevComment", "DisplayName",
}

# Attributes that indicate "this is a description" — NOT glossary-worthy
DESC_ATTRIBUTES = {
    "Desc", "QuestDescription",
}

# All Korean-bearing attributes to scan
ALL_KOREAN_ATTRIBUTES = NAME_ATTRIBUTES | DESC_ATTRIBUTES


# =============================================================================
# CATEGORY CLASSIFICATION (from filename, same as QACompiler)
# =============================================================================

# Priority keywords checked FIRST (override folder matching)
PRIORITY_KEYWORDS: List[Tuple[str, str]] = [
    ("gimmick", "Gimmick"),
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
]

# Standard folder/keyword patterns (phase 2)
STANDARD_PATTERNS: List[Tuple[str, str, str]] = [
    ("folder", "lookat", "Item"),
    ("folder", "patterndescription", "Item"),
    ("keyword", "weapon", "Item"),
    ("keyword", "armor", "Item"),
    ("folder", "quest", "Quest"),
    ("keyword", "schedule_", "Quest"),
    ("folder", "character", "Character"),
    ("folder", "npc", "Character"),
    ("keyword", "monster", "Character"),
    ("keyword", "animal", "Character"),
    ("folder", "skill", "Skill"),
    ("folder", "knowledge", "Knowledge"),
    ("folder", "faction", "Faction"),
    ("folder", "ui", "UI"),
    ("keyword", "localstringinfo", "UI"),
    ("keyword", "symboltext", "UI"),
    ("folder", "region", "Region"),
]


def classify_category(file_path: Path, base_folder: Path) -> str:
    """Classify a GameData file into a category using two-phase keyword matching.

    Same logic as QACompiler's GameDataClusterer.
    """
    try:
        relative = file_path.relative_to(base_folder)
    except ValueError:
        relative = file_path

    path_str = str(relative).lower().replace("\\", "/")
    filename = file_path.name.lower()

    # Remove extensions for matching
    filename_base = filename
    for ext in (".staticinfo.xml", ".seqc", ".xml"):
        if filename_base.endswith(ext):
            filename_base = filename_base[:-len(ext)]
            break

    # Phase 1: Priority keywords
    for keyword, category in PRIORITY_KEYWORDS:
        if keyword in filename_base:
            return category

    # Phase 2: Standard patterns
    for match_type, pattern, category in STANDARD_PATTERNS:
        if match_type == "folder":
            if f"/{pattern}/" in path_str or path_str.startswith(f"{pattern}/"):
                return category
        elif match_type == "keyword":
            if pattern in path_str or pattern in filename_base:
                return category

    return "System_Misc"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GameDataEntry:
    """A Korean text found in GameData with its attribute classification."""
    korean_text: str        # The Korean text (raw, not normalized)
    attr_type: str          # "Name" or "Desc"
    attr_name: str          # Exact attribute name (e.g., "CharacterName", "Desc")
    category: str           # Derived category (Knowledge, Item, Quest, etc.)
    filename: str           # Source GameData filename
    strkey: str             # StrKey of the element (if available)
    tag: str                # XML element tag (e.g., "KnowledgeInfo", "CharacterInfo")


# =============================================================================
# XML SANITIZATION (same as QACompiler base.py — battle-tested)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')
_br_tag_re = re.compile(r'<br\s*/?>', flags=re.IGNORECASE)
_whitespace_re = re.compile(r'\s+', flags=re.UNICODE)


def _sanitize_xml(raw: str) -> str:
    """Battle-tested XML sanitization from QACompiler."""
    raw = _bad_entity_re.sub("&amp;", raw)
    # Handle <seg> newlines
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    raw = re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)
    # Escape < inside attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    # Escape & inside attribute values
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)
    return raw


def _parse_xml_file(path: Path) -> Optional[ET._Element]:
    """Parse a GameData XML file with sanitization and recovery."""
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        logger.warning("Failed to read %s", path)
        return None

    cleaned = _sanitize_xml(raw)
    wrapped = f"<ROOT>\n{cleaned}\n</ROOT>"

    try:
        return ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(huge_tree=True)
        )
    except ET.XMLSyntaxError:
        pass

    try:
        return ET.fromstring(
            wrapped.encode("utf-8"),
            parser=ET.XMLParser(recover=True, huge_tree=True)
        )
    except ET.XMLSyntaxError:
        logger.warning("XML parse error: %s", path)
        return None


# =============================================================================
# KOREAN DETECTION
# =============================================================================

_korean_re = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]')


def _contains_korean(text: str) -> bool:
    """Check if text contains Korean characters (full 3-range coverage)."""
    return bool(_korean_re.search(text)) if text else False


# =============================================================================
# PLACEHOLDER NORMALIZATION (same as QACompiler base.py)
# =============================================================================

_placeholder_suffix_re = re.compile(r'\{([^#}]+)#[^}]+\}')


def normalize_text(text: str) -> str:
    """Normalize text for matching (same as QACompiler's normalize_placeholders)."""
    if not text:
        return ""
    text = _placeholder_suffix_re.sub(r'{\1}', text)
    text = _br_tag_re.sub(' ', text)
    text = _whitespace_re.sub(' ', text).strip()
    return text


# =============================================================================
# REVERSE INDEX BUILDER
# =============================================================================

class GameDataReverseIndex:
    """Reverse index: normalized Korean text → GameDataEntry list.

    Parses all GameData XMLs across StaticInfo, staticinfo_quest, staticinfo_dialog
    and classifies each Korean attribute value as Name-type or Desc-type.
    """

    def __init__(self):
        # {normalized_korean → [GameDataEntry, ...]}
        self._index: Dict[str, List[GameDataEntry]] = {}
        self._stats = {
            "files_parsed": 0,
            "name_entries": 0,
            "desc_entries": 0,
            "total_korean_texts": 0,
        }

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    @property
    def name_count(self) -> int:
        """Number of unique Korean texts classified as Name."""
        return sum(
            1 for entries in self._index.values()
            if any(e.attr_type == "Name" for e in entries)
        )

    @property
    def total_entries(self) -> int:
        return len(self._index)

    def build(
        self,
        folders: List[Path],
        progress_callback: Optional[callable] = None,
    ) -> int:
        """Build the reverse index from GameData folders.

        Args:
            folders: List of StaticInfo folder paths to scan
            progress_callback: Optional callback(message_str)

        Returns:
            Total unique Korean texts indexed
        """
        self._index.clear()
        self._stats = {
            "files_parsed": 0,
            "name_entries": 0,
            "desc_entries": 0,
            "total_korean_texts": 0,
        }

        # Collect all XML files
        xml_files: List[Tuple[Path, Path]] = []  # (file_path, base_folder)
        for folder in folders:
            if not folder.exists():
                logger.info("GameData folder not found (skipping): %s", folder)
                continue
            for dp, _, files in os.walk(folder):
                for fn in files:
                    if fn.lower().endswith((".xml", ".seqc")):
                        xml_files.append((Path(dp) / fn, folder))

        total_files = len(xml_files)
        logger.info("GameData reverse index: scanning %d XML files from %d folders",
                     total_files, len(folders))

        for idx, (file_path, base_folder) in enumerate(xml_files):
            if progress_callback and idx % 50 == 0:
                progress_callback(f"Indexing GameData: {idx}/{total_files} files...")

            root = _parse_xml_file(file_path)
            if root is None:
                continue

            category = classify_category(file_path, base_folder)
            filename = file_path.stem  # e.g., "knowledgeinfo_node.staticinfo"

            self._extract_from_tree(root, category, filename, file_path.name)
            self._stats["files_parsed"] += 1

        self._stats["total_korean_texts"] = len(self._index)

        logger.info(
            "GameData reverse index built: %d unique Korean texts "
            "(%d Name, %d Desc) from %d files",
            self._stats["total_korean_texts"],
            self._stats["name_entries"],
            self._stats["desc_entries"],
            self._stats["files_parsed"],
        )

        return self._stats["total_korean_texts"]

    def _extract_from_tree(
        self,
        root: ET._Element,
        category: str,
        filename: str,
        full_filename: str,
    ) -> None:
        """Extract all Korean Name/Desc attribute values from an XML tree."""
        for elem in root.iter():
            strkey = (elem.get("StrKey") or "").strip()

            for attr_name in ALL_KOREAN_ATTRIBUTES:
                value = (elem.get(attr_name) or "").strip()
                if not value or not _contains_korean(value):
                    continue

                # Classify attribute type
                if attr_name in NAME_ATTRIBUTES:
                    attr_type = "Name"
                    self._stats["name_entries"] += 1
                else:
                    attr_type = "Desc"
                    self._stats["desc_entries"] += 1

                normalized = normalize_text(value)
                if not normalized:
                    continue

                entry = GameDataEntry(
                    korean_text=value,
                    attr_type=attr_type,
                    attr_name=attr_name,
                    category=category,
                    filename=filename,
                    strkey=strkey,
                    tag=elem.tag,
                )

                if normalized not in self._index:
                    self._index[normalized] = []

                # Avoid exact duplicates
                existing = self._index[normalized]
                is_dup = any(
                    e.attr_type == attr_type
                    and e.category == category
                    and e.filename == filename
                    for e in existing
                )
                if not is_dup:
                    self._index[normalized].append(entry)

    def lookup(self, korean_text: str) -> Optional[List[GameDataEntry]]:
        """Look up a Korean text in the reverse index.

        Args:
            korean_text: Korean text (will be normalized)

        Returns:
            List of GameDataEntry matches, or None if not found
        """
        normalized = normalize_text(korean_text)
        if not normalized:
            return None
        return self._index.get(normalized)

    def is_name(self, korean_text: str) -> bool:
        """Check if a Korean text is classified as a Name attribute.

        If the text appears as BOTH Name and Desc in different contexts,
        Name wins (it IS a glossary term that also has a description use).
        """
        entries = self.lookup(korean_text)
        if not entries:
            return False
        return any(e.attr_type == "Name" for e in entries)

    def get_category(self, korean_text: str) -> str:
        """Get the primary category for a Korean text.

        Prefers Name-type entries for category if the text appears in multiple contexts.
        """
        entries = self.lookup(korean_text)
        if not entries:
            return ""
        # Prefer Name-type entry's category
        for e in entries:
            if e.attr_type == "Name":
                return e.category
        return entries[0].category

    def get_best_entry(self, korean_text: str) -> Optional[GameDataEntry]:
        """Get the best matching GameDataEntry (prefers Name-type)."""
        entries = self.lookup(korean_text)
        if not entries:
            return None
        for e in entries:
            if e.attr_type == "Name":
                return e
        return entries[0]

    def get_all_name_texts(self) -> List[str]:
        """Get all normalized Korean texts classified as Name."""
        return [
            key for key, entries in self._index.items()
            if any(e.attr_type == "Name" for e in entries)
        ]
