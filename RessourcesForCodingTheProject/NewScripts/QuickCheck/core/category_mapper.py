"""
Category Mapper for EXPORT folder structure.

Ported from LanguageDataExporter — two-tier clustering algorithm:
- Tier 1 (STORY): Dialog and Sequencer with fine-grained categories
- Tier 2 (GAME_DATA): System/World/None/Platform with keyword clustering

Combined single-pass EXPORT scan: one rglob, one parse per file,
builds both category and filename indexes simultaneously.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from lxml import etree

logger = logging.getLogger(__name__)


def load_cluster_config(config_path: Path) -> Dict:
    """
    Load category cluster configuration from JSON file.
    Graceful fallback if missing or invalid.
    """
    if not config_path.exists():
        logger.info("No cluster config found. Using two-tier defaults.")
        return {"enabled": True, "default_category": "Uncategorized", "tiers": {}}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("enabled", True)
        config.setdefault("default_category", "Uncategorized")
        config.setdefault("tiers", {})
        return config
    except Exception as e:
        logger.error("Error loading cluster config: %s", e)
        return {"enabled": True, "default_category": "Uncategorized", "tiers": {}}


class TwoTierCategoryMapper:
    """
    Maps EXPORT files to categories using two-tier clustering.

    Tier 1 (STORY): Dialog → 4 sub-categories, Sequencer → 'Sequencer'
    Tier 2 (GAME_DATA): Two-phase matching (priority keywords first, then standard patterns)
    """

    DIALOG_CATEGORIES = {
        "aidialog": "AIDialog",
        "narrationdialog": "NarrationDialog",
        "questdialog": "QuestDialog",
        "stageclosedialog": "QuestDialog",
    }

    PRIORITY_KEYWORDS = [
        ("gimmick", "Gimmick"),
        ("item", "Item"),
        ("quest", "Quest"),
        ("skill", "Skill"),
        ("character", "Character"),
        ("region", "Region"),
        ("faction", "Faction"),
    ]

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

    def __init__(self, export_folder: Path, config: Dict):
        self.export_folder = export_folder
        self.default_category = config.get("default_category", "Uncategorized")
        self.enabled = config.get("enabled", True)

    def get_category(self, file_path: Path) -> str:
        """Get category for a file using two-tier clustering."""
        if not self.enabled:
            try:
                relative = file_path.relative_to(self.export_folder)
                parts = relative.parts
                return parts[0] if len(parts) >= 2 else self.default_category
            except ValueError:
                return self.default_category

        try:
            relative = file_path.relative_to(self.export_folder) if file_path.is_absolute() else file_path
        except ValueError:
            return self.default_category

        parts = relative.parts
        if len(parts) < 2:
            return self.default_category

        top_level = parts[0].lower()

        if top_level == "dialog":
            if len(parts) < 3:
                return "AIDialog"
            return self.DIALOG_CATEGORIES.get(parts[1].lower(), "AIDialog")

        if top_level == "sequencer":
            return "Sequencer"

        return self._categorize_gamedata(relative, file_path)

    def _categorize_gamedata(self, relative: Path, file_path: Path) -> str:
        path_str = str(relative).lower().replace("\\", "/")
        filename = file_path.name.lower()
        filename_base = filename[:-8] if filename.endswith(".loc.xml") else (filename[:-4] if filename.endswith(".xml") else filename)

        # Phase 1: Priority keywords
        for keyword, category in self.PRIORITY_KEYWORDS:
            if keyword in filename_base:
                return category

        # Phase 2: Standard patterns
        for match_type, pattern, category in self.STANDARD_PATTERNS:
            if match_type == "folder":
                if f"/{pattern}/" in path_str or path_str.startswith(f"{pattern}/"):
                    return category
                parts = relative.parts
                if len(parts) >= 2 and parts[1].lower() == pattern:
                    return category
            elif match_type == "keyword":
                if pattern in path_str or pattern in filename_base:
                    return category

        return "System_Misc"


def _parse_export_stringids(xml_path: Path) -> List[str]:
    """
    Extract StringId attributes from a .loc.xml file.
    Uses lxml recovery mode. Per-file error handling.
    """
    try:
        parser = etree.XMLParser(recover=True, huge_tree=True)
        tree = etree.parse(str(xml_path), parser)
        root = tree.getroot()
        return [
            elem.get("StringId") or elem.get("StringID") or ""
            for elem in root.xpath("//LocStr")
            if (elem.get("StringId") or elem.get("StringID"))
        ]
    except Exception as e:
        logger.warning("Failed to parse EXPORT file %s: %s", xml_path, e)
        return []


def build_export_indexes(
    export_folder: Path, config: Dict
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Single-pass combined scan of EXPORT folder.
    One rglob, one parse per file, builds both indexes.

    Returns:
        (category_index, filename_index)
        category_index: {StringID: Category}
        filename_index: {StringID: filename_stem}
    """
    if not export_folder.exists():
        logger.error("EXPORT folder not found: %s", export_folder)
        return {}, {}

    mapper = TwoTierCategoryMapper(export_folder, config)
    category_index: Dict[str, str] = {}
    filename_index: Dict[str, str] = {}
    files_processed = 0

    for xml_file in export_folder.rglob("*.loc.xml"):
        files_processed += 1
        category = mapper.get_category(xml_file)
        stem = xml_file.name[:-8] if xml_file.name.endswith(".loc.xml") else xml_file.stem
        string_ids = _parse_export_stringids(xml_file)

        for sid in string_ids:
            if sid not in category_index:
                category_index[sid] = category
            if sid not in filename_index:
                filename_index[sid] = stem

    logger.info(
        "EXPORT scan: %d files, %d StringIDs indexed",
        files_processed, len(filename_index),
    )
    return category_index, filename_index
