"""
Two-Tier Category Mapper -- LDE's battle-tested category classification.

Grafted from: RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/exporter/category_mapper.py

Implements two-tier clustering algorithm:
- Tier 1 (STORY): Dialog subfolder -> 4 categories; Sequencer -> 1 category
- Tier 2 (GAME_DATA): Priority keywords FIRST (override folder matching),
  then standard folder/keyword patterns

Also provides:
- Korean text detection (3-range: syllables + jamo + compat jamo)
- FileName index builder (StringID -> .loc.xml stem mapping)
- Text state detection (KOREAN vs TRANSLATED)

Phase 98 Plan 04: MEGA Graft -- LDE Battle-Tested Techniques
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger


# =============================================================================
# Korean Detection -- 3-range coverage per korean-regex.md rule
# =============================================================================

# Korean: syllables (AC00-D7AF) + Jamo (1100-11FF) + Compat Jamo (3130-318F)
_KOREAN_RE = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')


def contains_korean(text: str) -> bool:
    """Check if text contains any Korean characters (3-range coverage).

    Covers:
    - Hangul Syllables (U+AC00-U+D7AF): Full composed syllables
    - Hangul Jamo (U+1100-U+11FF): Leading/vowel/trailing Jamo
    - Hangul Compatibility Jamo (U+3130-U+318F): Single consonants/vowels
    """
    if not text:
        return False
    return bool(_KOREAN_RE.search(text))


def get_text_state(text: str) -> str:
    """Return 'KOREAN' if text contains Korean, else 'TRANSLATED'.

    Used for untranslated text detection in GameData grid:
    - KOREAN = text still contains Korean source -> untranslated
    - TRANSLATED = text has been localized
    """
    return "KOREAN" if contains_korean(text) else "TRANSLATED"


# =============================================================================
# TwoTierCategoryMapper -- Exact LDE algorithm
# =============================================================================


class TwoTierCategoryMapper:
    """
    Maps GameData XML files to categories using LDE's two-tier clustering.

    Tier 1 (STORY): Dialog subfolder -> 4 categories; Sequencer -> 1 category
    Tier 2 (GAME_DATA): TWO-PHASE matching algorithm
    - Phase 1: Priority keywords (override folder matching)
    - Phase 2: Standard patterns (folder-first, then keywords)

    Example: World/Knowledge/KnowledgeInfo_Item.xml
    - Phase 1: "item" in filename -> Returns "Item" (not Knowledge!)

    Grafted from: LanguageDataExporter/exporter/category_mapper.py
    """

    # Dialog subfolder -> simplified STORY category
    DIALOG_CATEGORIES = {
        "aidialog": "AIDialog",
        "narrationdialog": "NarrationDialog",
        "questdialog": "QuestDialog",
        "stageclosedialog": "QuestDialog",  # StageClose is quest-related
    }

    # ==========================================================================
    # PRIORITY KEYWORDS - Checked FIRST, before any folder matching!
    # ==========================================================================
    # These keywords in filename OVERRIDE folder-based categorization.
    # Example: KnowledgeInfo_Item.xml in Knowledge/ folder -> Item (not Knowledge)
    PRIORITY_KEYWORDS: List[Tuple[str, str]] = [
        ("gimmick", "Gimmick"),   # FIRST - gimmick wins over all other categories
        ("item", "Item"),
        ("quest", "Quest"),
        ("skill", "Skill"),
        ("character", "Character"),
        ("region", "Region"),     # region before faction
        ("faction", "Faction"),
    ]

    # ==========================================================================
    # STANDARD PATTERNS - Folder-first matching (Phase 2)
    # ==========================================================================
    # Only checked if no priority keyword matched.
    STANDARD_PATTERNS: List[Tuple[str, str, str]] = [
        # Special folder mappings (Item shortcuts)
        ("folder", "lookat", "Item"),
        ("folder", "patterndescription", "Item"),
        # Item keywords (fallback if not in priority)
        ("keyword", "weapon", "Item"),
        ("keyword", "armor", "Item"),
        # Quest folder + keywords
        ("folder", "quest", "Quest"),
        ("keyword", "schedule_", "Quest"),
        # Character folders + keywords
        ("folder", "character", "Character"),
        ("folder", "npc", "Character"),
        ("keyword", "monster", "Character"),
        ("keyword", "animal", "Character"),
        # Other category folders (gimmick handled by priority keyword)
        ("folder", "skill", "Skill"),
        ("folder", "knowledge", "Knowledge"),  # Only if no priority keyword!
        ("folder", "faction", "Faction"),
        ("folder", "ui", "UI"),
        ("keyword", "localstringinfo", "UI"),
        ("keyword", "symboltext", "UI"),
        ("folder", "region", "Region"),
    ]

    def __init__(self, base_folder: Path):
        """Initialize two-tier category mapper.

        Args:
            base_folder: Root folder (EXPORT folder or gamedata base directory)
        """
        self.base_folder = base_folder

    def get_category(self, file_path: Path) -> str:
        """Get category for a file using two-tier clustering.

        Args:
            file_path: Path to the .loc.xml or .xml file

        Returns:
            Category string (e.g., "Item", "Quest", "AIDialog", "Sequencer")
        """
        try:
            if file_path.is_absolute():
                relative = file_path.relative_to(self.base_folder)
            else:
                relative = file_path
        except ValueError:
            return "System_Misc"

        parts = relative.parts
        if len(parts) < 2:
            return "System_Misc"

        top_level = parts[0].lower()

        # Tier 1: STORY (Dialog and Sequencer)
        if top_level == "dialog":
            return self._categorize_dialog(relative)
        elif top_level == "sequencer":
            return "Sequencer"

        # Tier 2: GAME_DATA (System, World, None, Platform)
        return self._categorize_gamedata(relative, file_path)

    def _categorize_dialog(self, relative: Path) -> str:
        """Categorize Dialog files by subfolder."""
        parts = relative.parts
        if len(parts) < 3:
            return "AIDialog"  # Default for dialog without subfolder

        subfolder = parts[1].lower()
        return self.DIALOG_CATEGORIES.get(subfolder, "AIDialog")

    def _categorize_gamedata(self, relative: Path, file_path: Path) -> str:
        """Categorize GAME_DATA tier files using TWO-PHASE matching.

        Phase 1: Check PRIORITY KEYWORDS (override folder matching)
        Phase 2: Check STANDARD PATTERNS (folder-first)

        Example: World/Knowledge/KnowledgeInfo_Item.xml
        - Phase 1: "item" in filename -> Returns "Item" (not Knowledge!)
        """
        path_str = str(relative).lower().replace("\\", "/")
        filename = file_path.name.lower()

        # Remove extension for matching
        if filename.endswith(".loc.xml"):
            filename_base = filename[:-8]
        elif filename.endswith(".xml"):
            filename_base = filename[:-4]
        else:
            filename_base = filename

        # =====================================================================
        # PHASE 1: Priority Keywords (checked FIRST!)
        # =====================================================================
        for keyword, category in self.PRIORITY_KEYWORDS:
            if keyword in filename_base:
                logger.debug(f"Priority keyword '{keyword}' matched in {filename} -> {category}")
                return category

        # =====================================================================
        # PHASE 2: Standard Patterns (folder-first)
        # =====================================================================
        for match_type, pattern, category in self.STANDARD_PATTERNS:
            if match_type == "folder":
                # Check if pattern appears as folder in path
                if f"/{pattern}/" in path_str or path_str.startswith(f"{pattern}/"):
                    return category
                # Also check second-level folder
                parts = relative.parts
                if len(parts) >= 2 and parts[1].lower() == pattern:
                    return category
            elif match_type == "keyword":
                # Check if pattern appears anywhere in path or filename
                if pattern in path_str or pattern in filename_base:
                    return category

        return "System_Misc"


# =============================================================================
# FileName Index Builder
# =============================================================================


def build_filename_index(base_folder: Path) -> Dict[str, str]:
    """Build StringID -> .loc.xml filename stem index by scanning XML files.

    Uses regex on raw text (fast) rather than full XML parse.
    First occurrence wins for duplicate StringIDs.

    Args:
        base_folder: Root folder to scan for XML files

    Returns:
        {StringID: filename_stem} mapping
    """
    index: Dict[str, str] = {}
    if not base_folder.exists():
        return index

    for xml_file in base_folder.rglob("*.xml"):
        stem = xml_file.stem
        if stem.endswith(".loc"):
            stem = stem[:-4]
        # Quick scan: find StrKey attributes
        try:
            text = xml_file.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'StrKey="([^"]+)"', text):
                sid = match.group(1)
                if sid not in index:  # First occurrence wins
                    index[sid] = stem
        except Exception:
            continue

    logger.info(f"Built filename index: {len(index)} StringIDs mapped")
    return index


# =============================================================================
# Legacy API compatibility (used by categorize_string callers)
# =============================================================================


def categorize_string(file_path: str, text: str = "") -> str:
    """Convenience wrapper using path-based categorization.

    Args:
        file_path: Source file path (e.g., "path/dialog/npc_quest.xml").
        text: The string content (unused, kept for API compat).

    Returns:
        Category string.
    """
    path_lower = file_path.lower()

    # Tier 1: STORY patterns
    if "/dialog/" in path_lower or "\\dialog\\" in path_lower or path_lower.startswith("dialog/"):
        return "Dialog"
    if "/sequencer/" in path_lower or "\\sequencer\\" in path_lower or path_lower.startswith("sequencer/"):
        return "Sequencer"

    # Tier 2: GAME_DATA priority keywords
    for keyword, category in TwoTierCategoryMapper.PRIORITY_KEYWORDS:
        if keyword in path_lower:
            return category

    return "Other"
