"""
Category Mapper for EXPORT folder structure.

Ported from LanguageDataExporter's TwoTierCategoryMapper.
Maps StringIDs to categories using two-tier clustering:
- Tier 1 (STORY): Dialog and Sequencer with fine-grained categories
- Tier 2 (GAME_DATA): System/World/None/Platform with keyword clustering
"""

import logging
from pathlib import Path
from typing import Dict, List

from .xml_parser import parse_xml_file, iter_locstr_elements

logger = logging.getLogger(__name__)


# Dialog subfolder -> simplified STORY category
DIALOG_CATEGORIES = {
    "aidialog": "AIDialog",
    "narrationdialog": "NarrationDialog",
    "questdialog": "QuestDialog",
    "stageclosedialog": "QuestDialog",
}

# Priority keywords checked FIRST, before folder matching.
# Example: KnowledgeInfo_Item.xml in Knowledge/ folder -> Item (not Knowledge!)
PRIORITY_KEYWORDS = [
    ("gimmick", "Gimmick"),
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
]

# Standard patterns - folder-first matching (Phase 2)
STANDARD_PATTERNS = [
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


def categorize_file(file_path: Path, export_folder: Path) -> str:
    """
    Get category for a .loc.xml file using two-tier clustering.

    Args:
        file_path: Path to the .loc.xml file
        export_folder: Root EXPORT folder path

    Returns:
        Category string
    """
    try:
        if file_path.is_absolute():
            relative = file_path.relative_to(export_folder)
        else:
            relative = file_path
    except ValueError:
        return "Uncategorized"

    parts = relative.parts
    if len(parts) < 2:
        return "Uncategorized"

    top_level = parts[0].lower()

    # Tier 1: STORY (Dialog and Sequencer)
    if top_level == "dialog":
        if len(parts) < 3:
            return "AIDialog"
        subfolder = parts[1].lower()
        return DIALOG_CATEGORIES.get(subfolder, "AIDialog")

    if top_level == "sequencer":
        return "Sequencer"

    # Tier 2: GAME_DATA - two-phase matching
    path_str = str(relative).lower().replace("\\", "/")
    filename = file_path.name.lower()

    if filename.endswith(".loc.xml"):
        filename_base = filename[:-8]
    elif filename.endswith(".xml"):
        filename_base = filename[:-4]
    else:
        filename_base = filename

    # Phase 1: Priority keywords
    for keyword, category in PRIORITY_KEYWORDS:
        if keyword in filename_base:
            return category

    # Phase 2: Standard patterns (folder-first)
    for match_type, pattern, category in STANDARD_PATTERNS:
        if match_type == "folder":
            if f"/{pattern}/" in path_str or path_str.startswith(f"{pattern}/"):
                return category
            if len(parts) >= 2 and parts[1].lower() == pattern:
                return category
        elif match_type == "keyword":
            if pattern in path_str or pattern in filename_base:
                return category

    return "System_Misc"


def build_stringid_category_index(export_folder: Path) -> Dict[str, str]:
    """
    Scan EXPORT folder and build StringID -> Category mapping.

    Args:
        export_folder: Path to EXPORT folder

    Returns:
        {StringID: Category} mapping
    """
    if not export_folder.exists():
        logger.error(f"EXPORT folder not found: {export_folder}")
        return {}

    stringid_to_category: Dict[str, str] = {}
    files_processed = 0
    categories_used = set()

    for xml_file in export_folder.rglob("*.loc.xml"):
        files_processed += 1
        category = categorize_file(xml_file, export_folder)
        categories_used.add(category)

        try:
            root = parse_xml_file(xml_file)
        except Exception as e:
            logger.warning(f"Failed to parse {xml_file.name}: {e}")
            continue

        for elem in iter_locstr_elements(root):
            string_id = (elem.get('StringId') or elem.get('StringID') or
                         elem.get('stringid') or elem.get('STRINGID'))
            if string_id and string_id not in stringid_to_category:
                stringid_to_category[string_id] = category

    logger.info(f"Processed {files_processed} EXPORT files")
    logger.info(f"Found {len(stringid_to_category)} unique StringIDs")
    logger.info(f"Categories: {sorted(categories_used)}")

    return stringid_to_category
