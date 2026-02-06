"""
Category Mapper for EXPORT folder structure.

Implements two-tier clustering algorithm:
- Tier 1 (STORY): Dialog and Sequencer with fine-grained categories
- Tier 2 (GAME_DATA): System/World/None/Platform with keyword clustering
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .xml_parser import parse_export_file

logger = logging.getLogger(__name__)


def load_cluster_config(config_path: Path) -> Dict:
    """
    Load category cluster configuration from JSON file.

    The config controls the two-tier clustering behavior:
    - enabled: Whether to use two-tier clustering
    - tiers: Tier-specific settings
    - default_category: Fallback for unmapped files

    Args:
        config_path: Path to category_clusters.json

    Returns:
        Dictionary with clustering configuration
    """
    if not config_path.exists():
        logger.info("No cluster config found. Using two-tier clustering with defaults.")
        return {
            "enabled": True,
            "default_category": "Uncategorized",
            "tiers": {}
        }

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Ensure required fields
        config.setdefault("enabled", True)
        config.setdefault("default_category", "Uncategorized")
        config.setdefault("tiers", {})

        logger.info(f"Loaded cluster config: two-tier={config.get('enabled', True)}")
        return config

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cluster config: {e}")
        return {"enabled": True, "default_category": "Uncategorized", "tiers": {}}
    except Exception as e:
        logger.error(f"Error loading cluster config: {e}")
        return {"enabled": True, "default_category": "Uncategorized", "tiers": {}}


class TwoTierCategoryMapper:
    """
    Maps EXPORT files to categories using two-tier clustering.

    Tier 1 (STORY): 4 categories ordered by VoiceRecordingSheet
    - Sequencer: All sequencer files (story cutscenes)
    - AIDialog: Ambient/NPC dialog
    - QuestDialog: Quest-related dialog
    - NarrationDialog: Narration/tutorial text

    Tier 2 (GAME_DATA): TWO-PHASE matching algorithm
    - Phase 1: Priority keywords (override folder matching)
    - Phase 2: Standard patterns (folder-first, then keywords)

    Example: World/Knowledge/KnowledgeInfo_Item.xml
    - Phase 1: "item" in filename → Returns "Item" (not Knowledge!)
    """

    # Dialog subfolder → simplified STORY category
    # Maps to the 4 STORY categories from config
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
    # Example: KnowledgeInfo_Item.xml in Knowledge/ folder → Item (not Knowledge)
    PRIORITY_KEYWORDS = [
        ("gimmick", "Gimmick"),  # FIRST - gimmick wins over all other categories
        ("item", "Item"),
        ("quest", "Quest"),
        ("skill", "Skill"),
        ("character", "Character"),
        ("region", "Region"),  # region before faction
        ("faction", "Faction"),
    ]

    # ==========================================================================
    # STANDARD PATTERNS - Folder-first matching (Phase 2)
    # ==========================================================================
    # Only checked if no priority keyword matched.
    STANDARD_PATTERNS = [
        # Special folder mappings (Item shortcuts)
        ("folder", "lookat", "Item"),
        ("folder", "patterndescription", "Item"),
        # Item keywords (fallback if not in priority)
        ("keyword", "weapon", "Item"),
        ("keyword", "armor", "Item"),
        # Note: "itemequip" removed - caught by priority keyword "item"
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

    def __init__(self, export_folder: Path, config: Dict):
        """
        Initialize two-tier category mapper.

        Args:
            export_folder: Root EXPORT folder path
            config: Cluster configuration dict
        """
        self.export_folder = export_folder
        self.config = config
        self.default_category = config.get("default_category", "Uncategorized")
        self.enabled = config.get("enabled", True)

    def get_category(self, file_path: Path) -> str:
        """
        Get category for a file using two-tier clustering.

        Args:
            file_path: Path to the .loc.xml file

        Returns:
            Category string
        """
        if not self.enabled:
            # Fall back to simple top-level folder
            return self._get_simple_category(file_path)

        # Get relative path
        try:
            if file_path.is_absolute():
                relative = file_path.relative_to(self.export_folder)
            else:
                relative = file_path
        except ValueError:
            return self.default_category

        parts = relative.parts
        if len(parts) < 2:
            return self.default_category

        top_level = parts[0].lower()

        # Tier 1: STORY (Dialog and Sequencer)
        if top_level == "dialog":
            return self._categorize_dialog(relative)
        elif top_level == "sequencer":
            return self._categorize_sequencer(file_path)

        # Tier 2: GAME_DATA (System, World, None, Platform)
        return self._categorize_gamedata(relative, file_path)

    def _get_simple_category(self, file_path: Path) -> str:
        """Get simple category from top-level folder."""
        try:
            relative = file_path.relative_to(self.export_folder)
            parts = relative.parts
            if len(parts) < 2:
                return self.default_category
            return parts[0]
        except ValueError:
            return self.default_category

    def _categorize_dialog(self, relative: Path) -> str:
        """Categorize Dialog files by subfolder."""
        parts = relative.parts
        if len(parts) < 3:
            return "AIDialog"  # Default for dialog without subfolder

        subfolder = parts[1].lower()
        return self.DIALOG_CATEGORIES.get(subfolder, "AIDialog")

    def _categorize_sequencer(self, file_path: Path) -> str:
        """
        Return 'Sequencer' for all sequencer files.

        All sequencer content is grouped together and ordered
        by VoiceRecordingSheet EventName for chronological story order.
        """
        return "Sequencer"

    def _categorize_gamedata(self, relative: Path, file_path: Path) -> str:
        """
        Categorize GAME_DATA tier files using TWO-PHASE matching.

        Phase 1: Check PRIORITY KEYWORDS (override folder matching)
        Phase 2: Check STANDARD PATTERNS (folder-first)

        Example: World/Knowledge/KnowledgeInfo_Item.xml
        - Phase 1: "item" in filename → Returns "Item" (not Knowledge!)
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
                logger.debug(f"Priority keyword '{keyword}' matched in {filename} → {category}")
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


def build_stringid_category_index(
    export_folder: Path,
    clusters: Dict,
    default_category: str = "Uncategorized"
) -> Dict[str, str]:
    """
    Scan EXPORT folder and build StringID → Category mapping.

    Uses two-tier clustering algorithm:
    - Tier 1: Dialog (by folder) and Sequencer (by filename)
    - Tier 2: GameData (by keywords)

    Args:
        export_folder: Path to EXPORT folder
        clusters: Cluster configuration (can be legacy format or new format)
        default_category: Category for files in EXPORT root

    Returns:
        {StringID: Category} mapping
    """
    if not export_folder.exists():
        logger.error(f"EXPORT folder not found: {export_folder}")
        return {}

    # Create mapper (handle both old and new config formats)
    if isinstance(clusters, dict) and "enabled" in clusters:
        config = clusters
    else:
        # Legacy format - convert to new format
        config = {
            "enabled": True,
            "default_category": default_category,
            "tiers": {}
        }

    mapper = TwoTierCategoryMapper(export_folder, config)

    # Result: StringID → Category
    stringid_to_category: Dict[str, str] = {}

    # Stats for logging
    stats = {
        "files_processed": 0,
        "stringids_found": 0,
        "categories_used": set(),
    }

    # Walk EXPORT folder recursively
    for xml_file in export_folder.rglob("*.loc.xml"):
        stats["files_processed"] += 1

        # Get category using two-tier clustering
        category = mapper.get_category(xml_file)
        stats["categories_used"].add(category)

        # Extract StringIDs from file
        string_ids = parse_export_file(xml_file)

        # Assign category to each StringID
        for string_id in string_ids:
            if string_id in stringid_to_category:
                # StringID already assigned - log if different category
                existing = stringid_to_category[string_id]
                if existing != category:
                    logger.debug(f"StringID {string_id} in multiple categories: {existing}, {category}")
            else:
                stringid_to_category[string_id] = category
                stats["stringids_found"] += 1

    # Log summary
    logger.info(f"Processed {stats['files_processed']} EXPORT files")
    logger.info(f"Found {stats['stringids_found']} unique StringIDs")
    logger.info(f"Categories: {sorted(stats['categories_used'])}")

    return stringid_to_category


def get_category(
    string_id: str,
    category_index: Dict[str, str],
    default_category: str = "Uncategorized"
) -> str:
    """
    Get category for a StringID.

    Args:
        string_id: The StringID to look up
        category_index: {StringID: Category} mapping
        default_category: Fallback if not found

    Returns:
        Category name
    """
    return category_index.get(string_id, default_category)


def build_stringid_to_toplevel(export_folder: Path) -> Dict[str, str]:
    """
    Build StringID -> Top-level folder mapping.

    Maps each StringID to its top-level folder (Dialog, Sequencer, UI, etc.).
    Used for general SCRIPT category filtering.

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {StringID: TopLevelFolder} mapping
    """
    if not export_folder.exists():
        return {}

    stringid_to_toplevel: Dict[str, str] = {}

    # Get all top-level subfolders
    for toplevel_folder in export_folder.iterdir():
        if not toplevel_folder.is_dir():
            continue

        toplevel_name = toplevel_folder.name

        # Scan all XML files in this folder
        for xml_file in toplevel_folder.rglob("*.loc.xml"):
            string_ids = parse_export_file(xml_file)
            for string_id in string_ids:
                stringid_to_toplevel[string_id] = toplevel_name

    logger.info(f"Built top-level index: {len(stringid_to_toplevel)} StringIDs")
    return stringid_to_toplevel


def build_stringid_to_subfolder(export_folder: Path) -> Dict[str, str]:
    """
    Build StringID -> Subfolder mapping.

    Maps each StringID to its immediate subfolder within the top-level folder.
    Used for exclusion filtering (e.g., exclude NarrationDialog).

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {StringID: Subfolder} mapping
    """
    if not export_folder.exists():
        return {}

    stringid_to_subfolder: Dict[str, str] = {}

    # Get all top-level subfolders
    for toplevel_folder in export_folder.iterdir():
        if not toplevel_folder.is_dir():
            continue

        # Scan all XML files in this folder
        for xml_file in toplevel_folder.rglob("*.loc.xml"):
            # Get relative path from top-level folder
            rel_path = xml_file.relative_to(toplevel_folder)

            # Get immediate subfolder (first part of relative path)
            if len(rel_path.parts) > 1:
                subfolder = rel_path.parts[0]
            else:
                subfolder = ""  # File directly in top-level folder

            string_ids = parse_export_file(xml_file)
            for string_id in string_ids:
                stringid_to_subfolder[string_id] = subfolder

    logger.info(f"Built subfolder index: {len(stringid_to_subfolder)} StringIDs")
    return stringid_to_subfolder


def analyze_categories(export_folder: Path, config: Dict) -> Dict[str, int]:
    """
    Analyze EXPORT folder and return category distribution.

    Args:
        export_folder: Path to EXPORT folder
        config: Cluster configuration

    Returns:
        {category: file_count} mapping
    """
    if not export_folder.exists():
        return {}

    mapper = TwoTierCategoryMapper(export_folder, config)
    category_counts: Dict[str, int] = {}

    for xml_file in export_folder.rglob("*.loc.xml"):
        category = mapper.get_category(xml_file)
        category_counts[category] = category_counts.get(category, 0) + 1

    return category_counts
