"""
GameData Clusterer - Classifies GAME_DATA tier content by keywords.

TWO-PHASE MATCHING ALGORITHM:
1. PRIORITY KEYWORDS (checked FIRST, override folder matching):
   - item → Item
   - quest → Quest
   - skill → Skill
   - character → Character
   - faction → Faction
   - region → Region

2. STANDARD PATTERNS (folder-first, then keywords):
   - LookAt/, PatternDescription/ → Item
   - Quest/ → Quest
   - Character/, Npc/ → Character
   - Gimmick/ → Gimmick
   - Skill/ → Skill
   - Knowledge/ → Knowledge (only if no priority keyword!)
   - Faction/ → Faction
   - Ui/ → UI
   - Region/ → Region
   - (default) → System_Misc

Example: World/Knowledge/KnowledgeInfo_Item.xml
- Phase 1: "item" in filename → Returns "Item" (not Knowledge!)
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# PRIORITY KEYWORDS - Checked FIRST, before any folder matching!
# =============================================================================
# These keywords in filename/path OVERRIDE folder-based categorization.
# Example: KnowledgeInfo_Item.xml in Knowledge/ folder → Item (not Knowledge)

PRIORITY_KEYWORDS: List[Tuple[str, str]] = [
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("faction", "Faction"),
    ("region", "Region"),
]

# =============================================================================
# STANDARD PATTERNS - Folder-first matching (Phase 2)
# =============================================================================
# Only checked if no priority keyword matched.
# Each tuple: (match_type, pattern, category)
# match_type: "folder" (in path), "keyword" (in path or filename)

STANDARD_PATTERNS: List[Tuple[str, str, str]] = [
    # Special folder mappings (Item shortcuts)
    ("folder", "lookat", "Item"),
    ("folder", "patterndescription", "Item"),

    # Item keywords (fallback if not in priority)
    ("keyword", "weapon", "Item"),
    ("keyword", "armor", "Item"),
    ("keyword", "itemequip", "Item"),

    # Quest folder + keywords
    ("folder", "quest", "Quest"),
    ("keyword", "schedule_", "Quest"),

    # Character folders + keywords
    ("folder", "character", "Character"),
    ("folder", "npc", "Character"),
    ("keyword", "monster", "Character"),
    ("keyword", "animal", "Character"),

    # Other category folders
    ("folder", "gimmick", "Gimmick"),
    ("folder", "skill", "Skill"),
    ("folder", "knowledge", "Knowledge"),  # Only if no priority keyword!
    ("folder", "faction", "Faction"),
    ("folder", "ui", "UI"),
    ("keyword", "localstringinfo", "UI"),
    ("keyword", "symboltext", "UI"),
    ("folder", "region", "Region"),
]

# Default category for files that don't match any pattern
DEFAULT_GAMEDATA_CATEGORY = "System_Misc"


class GameDataClusterer:
    """
    Classifies GAME_DATA tier content based on keywords and folder paths.

    Uses TWO-PHASE matching:
    1. Priority keywords (item, quest, skill, character, faction, region)
    2. Standard folder/keyword patterns

    This ensures files like KnowledgeInfo_Item.xml go to Item, not Knowledge.
    """

    def __init__(self, export_folder: Path):
        """
        Initialize gamedata clusterer.

        Args:
            export_folder: Root EXPORT folder path
        """
        self.export_folder = export_folder

    def get_category(self, file_path: Path) -> str:
        """
        Get category for a gamedata file using TWO-PHASE matching.

        Phase 1: Check PRIORITY KEYWORDS (override folder matching)
        Phase 2: Check STANDARD PATTERNS (folder-first)

        Args:
            file_path: Path to the file

        Returns:
            GameData category (e.g., "Item", "Quest", "Character")
        """
        # Get path relative to EXPORT folder
        try:
            if file_path.is_absolute():
                relative = file_path.relative_to(self.export_folder)
            else:
                relative = file_path
        except ValueError:
            relative = file_path

        # Normalize path for matching (lowercase, forward slashes)
        path_str = str(relative).lower().replace("\\", "/")
        filename = file_path.name.lower()

        # Remove extension for filename matching
        if filename.endswith(".loc.xml"):
            filename_base = filename[:-8]
        elif filename.endswith(".xml"):
            filename_base = filename[:-4]
        else:
            filename_base = filename

        # =====================================================================
        # PHASE 1: Priority Keywords (checked FIRST!)
        # =====================================================================
        for keyword, category in PRIORITY_KEYWORDS:
            if keyword in filename_base:
                logger.debug(f"Priority keyword '{keyword}' matched in {filename} → {category}")
                return category

        # =====================================================================
        # PHASE 2: Standard Patterns (folder-first)
        # =====================================================================
        for match_type, pattern, category in STANDARD_PATTERNS:
            if match_type == "folder":
                # Check if pattern appears as a folder in path
                if f"/{pattern}/" in path_str or path_str.startswith(f"{pattern}/"):
                    return category
            elif match_type == "keyword":
                # Check if pattern appears anywhere in path or filename
                if pattern in path_str or pattern in filename_base:
                    return category

        return DEFAULT_GAMEDATA_CATEGORY

    def get_pattern_info(self) -> List[Dict]:
        """
        Get information about all patterns (priority + standard).

        Returns:
            List of dicts with match_type, pattern, and category info
        """
        patterns = []

        # Priority keywords
        for keyword, category in PRIORITY_KEYWORDS:
            patterns.append({
                "type": "priority_keyword",
                "pattern": keyword,
                "category": category,
            })

        # Standard patterns
        for mtype, pattern, category in STANDARD_PATTERNS:
            patterns.append({
                "type": mtype,
                "pattern": pattern,
                "category": category,
            })

        return patterns

    def scan_gamedata_files(self, folders: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Scan specified folders and count files by category.

        Args:
            folders: List of top-level folders to scan (default: System, World, None, Platform)

        Returns:
            Dict mapping category to file count
        """
        if folders is None:
            folders = ["System", "World", "None", "Platform"]

        category_counts: Dict[str, int] = {}

        for folder_name in folders:
            folder_path = self.export_folder / folder_name
            if not folder_path.exists():
                continue

            for xml_file in folder_path.rglob("*.loc.xml"):
                category = self.get_category(xml_file)
                category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts

    def analyze_uncategorized(self, folders: Optional[List[str]] = None) -> List[str]:
        """
        Find files that fall into System_Misc (uncategorized).

        Useful for identifying patterns that might need new categories.

        Args:
            folders: List of top-level folders to scan

        Returns:
            List of paths for uncategorized files
        """
        if folders is None:
            folders = ["System", "World", "None", "Platform"]

        uncategorized: List[str] = []

        for folder_name in folders:
            folder_path = self.export_folder / folder_name
            if not folder_path.exists():
                continue

            for xml_file in folder_path.rglob("*.loc.xml"):
                category = self.get_category(xml_file)
                if category == DEFAULT_GAMEDATA_CATEGORY:
                    try:
                        relative = xml_file.relative_to(self.export_folder)
                        uncategorized.append(str(relative))
                    except ValueError:
                        uncategorized.append(str(xml_file))

        return uncategorized
