"""
Category Mapper for EXPORT folder structure.

Scans the EXPORT folder and builds a StringID → Category mapping
based on folder structure. Auto-discovers folder names as categories.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .xml_parser import parse_export_file

logger = logging.getLogger(__name__)


def load_cluster_config(config_path: Path) -> Dict:
    """
    Load optional category cluster configuration from JSON file.

    The config is OPTIONAL - if not present or empty, folder names
    are used directly as categories.

    Args:
        config_path: Path to category_clusters.json

    Returns:
        Dictionary with:
        - clusters: {category_name: [folder_paths]} (optional overrides)
        - default_category: fallback category name
    """
    if not config_path.exists():
        logger.info("No cluster config found. Using auto-discovery (folder names = categories)")
        return {
            "clusters": {},
            "default_category": "Uncategorized"
        }

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Validate required fields
        if "clusters" not in config:
            config["clusters"] = {}
        if "default_category" not in config:
            config["default_category"] = "Uncategorized"

        if config["clusters"]:
            logger.info(f"Loaded cluster config with {len(config['clusters'])} category overrides")
        else:
            logger.info("Cluster config empty. Using auto-discovery (folder names = categories)")

        return config

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cluster config: {e}")
        return {"clusters": {}, "default_category": "Uncategorized"}
    except Exception as e:
        logger.error(f"Error loading cluster config: {e}")
        return {"clusters": {}, "default_category": "Uncategorized"}


def _build_folder_to_category_map(clusters: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build a reverse mapping from folder path to category (for overrides only).

    Args:
        clusters: {category_name: [folder_paths]}

    Returns:
        {folder_path: category_name}
    """
    folder_to_category = {}

    for category, folders in clusters.items():
        for folder in folders:
            # Normalize folder path (use forward slashes)
            normalized = folder.replace('\\', '/').strip('/')
            folder_to_category[normalized] = category
            folder_to_category[normalized.lower()] = category  # Case-insensitive lookup

    return folder_to_category


def _get_category_from_path(file_path: Path, export_folder: Path) -> Optional[str]:
    """
    Extract category from file path.

    AUTO-DISCOVERY LOGIC:
    - Use the TOP-LEVEL folder name as the category
    - e.g., EXPORT/Character/npc.loc.xml → "Character"
    - e.g., EXPORT/System/Quest/main.loc.xml → "System"
    - Files directly in EXPORT root → None (will use default)

    Args:
        file_path: Absolute path to the file
        export_folder: Root EXPORT folder

    Returns:
        Category name (top-level folder) or None if in root
    """
    try:
        relative = file_path.relative_to(export_folder)
        parts = relative.parts

        # Need at least folder + filename
        if len(parts) < 2:
            return None  # File is in EXPORT root

        # First part is the top-level folder = category
        return parts[0]

    except ValueError:
        return None


def build_stringid_category_index(
    export_folder: Path,
    clusters: Dict[str, List[str]],
    default_category: str = "Uncategorized"
) -> Dict[str, str]:
    """
    Scan EXPORT folder and build StringID → Category mapping.

    AUTO-DISCOVERY ALGORITHM:
    1. Walk EXPORT folder recursively
    2. For each .loc.xml file, use TOP-LEVEL folder name as category
    3. If clusters config has overrides, apply them
    4. Extract all StringIDs from file
    5. Assign category to each StringID

    Args:
        export_folder: Path to EXPORT folder
        clusters: {category_name: [folder_paths]} optional overrides
        default_category: Category for files in EXPORT root

    Returns:
        {StringID: Category} mapping
    """
    if not export_folder.exists():
        logger.error(f"EXPORT folder not found: {export_folder}")
        return {}

    # Build override lookup (if any)
    override_map = _build_folder_to_category_map(clusters)
    has_overrides = bool(override_map)

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

        # AUTO-DISCOVER: Get category from top-level folder name
        category = _get_category_from_path(xml_file, export_folder)

        if category is None:
            category = default_category
        else:
            # Check for override in clusters config
            if has_overrides:
                # Get full relative path for override matching
                try:
                    relative = xml_file.relative_to(export_folder)
                    folder_path = str(relative.parent).replace('\\', '/')
                    if folder_path in override_map:
                        category = override_map[folder_path]
                    elif folder_path.lower() in override_map:
                        category = override_map[folder_path.lower()]
                    elif category.lower() in override_map:
                        category = override_map[category.lower()]
                except ValueError:
                    pass

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
    logger.info(f"Auto-discovered categories: {sorted(stats['categories_used'])}")

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
