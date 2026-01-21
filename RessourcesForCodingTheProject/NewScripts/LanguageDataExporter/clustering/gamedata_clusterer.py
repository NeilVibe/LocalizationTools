"""
GameData Clusterer - Classifies GAME_DATA tier content by keywords.

GameData categories are determined by folder paths and filename keywords:
- Item: item, weapon, armor, itemequip, LookAt/, PatternDescription/
- Quest: quest, Quest/, schedule_
- Character: character, Character/, Npc/, monster, animal
- Gimmick: gimmick, Gimmick/
- Skill: skill, Skill/
- Knowledge: knowledge, Knowledge/
- Faction: faction, Faction/
- UI: Ui/, LocalStringInfo, SymbolText
- Region: region, Region/
- System_Misc: (default fallback)

Special Rules:
- LookAt/ folder → Item (readable items in game)
- PatternDescription/ folder → Item (item patterns)
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# GameData keyword categories
# Each tuple: (match_type, pattern, category)
# match_type: "folder" (in path), "keyword" (in path or filename)
GAMEDATA_PATTERNS: List[Tuple[str, str, str]] = [
    # Special folder mappings first (more specific)
    ("folder", "lookat", "Item"),
    ("folder", "patterndescription", "Item"),

    # Item-related
    ("keyword", "item", "Item"),
    ("keyword", "weapon", "Item"),
    ("keyword", "armor", "Item"),
    ("keyword", "itemequip", "Item"),

    # Quest-related
    ("folder", "quest", "Quest"),
    ("keyword", "schedule_", "Quest"),

    # Character-related
    ("folder", "character", "Character"),
    ("folder", "npc", "Character"),
    ("keyword", "monster", "Character"),
    ("keyword", "animal", "Character"),

    # Other categories
    ("folder", "gimmick", "Gimmick"),
    ("folder", "skill", "Skill"),
    ("folder", "knowledge", "Knowledge"),
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

    This clusterer handles files in System, World, None, and Platform folders.
    Categories are determined by matching folder names and filename keywords.
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
        Get category for a gamedata file based on path and filename keywords.

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

        # Check patterns in order
        for match_type, pattern, category in GAMEDATA_PATTERNS:
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
        Get information about all gamedata patterns.

        Returns:
            List of dicts with match_type, pattern, and category info
        """
        return [
            {
                "type": mtype,
                "pattern": pattern,
                "category": category,
            }
            for mtype, pattern, category in GAMEDATA_PATTERNS
        ]

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
