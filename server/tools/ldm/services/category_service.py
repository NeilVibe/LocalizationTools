"""
CategoryService -- LanguageDataExporter two-tier category classification.

Fully grafted from LDE's TwoTierCategoryMapper logic:
1. Build reverse map: StringID → export filename (from MegaIndex D17)
2. Categorize by export filename using LDE's exact algorithm:
   - Tier 1 (STORY): Dialog subfolder → AIDialog/QuestDialog/NarrationDialog/Sequencer
   - Tier 2 (GAME_DATA): Priority keywords in filename → Item/Quest/Skill/etc.
   - Tier 2 fallback: Folder name matching → Knowledge/Character/Region/etc.
3. Fallback: StringID prefix + keyword matching (when MegaIndex not available)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from loguru import logger


# =============================================================================
# LDE Two-Tier Category Logic (grafted from category_mapper.py)
# =============================================================================

# Tier 1: Dialog subfolder → STORY categories
DIALOG_CATEGORIES = {
    "aidialog": "AIDialog",
    "narrationdialog": "NarrationDialog",
    "questdialog": "QuestDialog",
    "stageclosedialog": "QuestDialog",
}

# Tier 2: Priority keywords — checked FIRST, before folder matching
# Example: KnowledgeInfo_Item.xml → "Item" (not Knowledge!)
PRIORITY_KEYWORDS = [
    ("gimmick", "Gimmick"),
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
]

# Tier 2: Standard folder/keyword patterns
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


def categorize_by_export_path(export_filename: str) -> str:
    """LDE's exact two-tier algorithm on export filename.

    Args:
        export_filename: e.g. "Dialog_QuestDialog_QuestInfo" or "World_Item_ItemEquipInfo"
    """
    if not export_filename:
        return "Other"

    lower = export_filename.lower()

    # Tier 1: Check if it's a Dialog/Sequencer file
    if "dialog" in lower or "sequencer" in lower:
        if "sequencer" in lower:
            return "Sequencer"
        # Check dialog subfolder
        for subfolder, category in DIALOG_CATEGORIES.items():
            if subfolder in lower:
                return category
        return "Dialog"

    # Tier 2 Phase 1: Priority keywords in filename (override folder matching)
    for keyword, category in PRIORITY_KEYWORDS:
        if keyword in lower:
            return category

    # Tier 2 Phase 2: Standard folder/keyword patterns
    for match_type, pattern, category in STANDARD_PATTERNS:
        if match_type == "folder":
            # Check folder-like segments (split by _ or /)
            parts = lower.replace("/", "_").replace("\\", "_").split("_")
            if pattern in parts:
                return category
        elif match_type == "keyword":
            if pattern in lower:
                return category

    return "Other"


# =============================================================================
# Fallback: StringID-based matching (when MegaIndex not available)
# =============================================================================

STRINGID_PREFIX_TO_CATEGORY = [
    ("SID_KNOW_", "Knowledge"), ("SID_GIMMICK_", "Gimmick"), ("SID_ITEM_", "Item"),
    ("SID_CHAR_", "Character"), ("SID_SKILL_", "Skill"), ("SID_REGION_", "Region"),
    ("SID_QUEST_", "Quest"), ("STR_KNOW_", "Knowledge"), ("STR_GIMMICK_", "Gimmick"),
    ("STR_ITEM_", "Item"), ("STR_CHAR_", "Character"), ("STR_SKILL_", "Skill"),
    ("STR_REGION_", "Region"), ("STR_QUEST_", "Quest"), ("STR_DIALOG_", "Dialog"),
    ("STR_SCRIPT_", "Script"), ("STR_UI_", "UI"), ("STR_SYSTEM_", "System"),
]

KEYWORD_TO_CATEGORY = [
    ("gimmick", "Gimmick"), ("item", "Item"), ("equip", "Item"), ("quest", "Quest"),
    ("skill", "Skill"), ("character", "Character"), ("npc", "Character"),
    ("region", "Region"), ("faction", "Faction"), ("knowledge", "Knowledge"),
    ("dialog", "Dialog"), ("sequencer", "Sequencer"), ("script", "Script"),
]


def categorize_by_stringid(string_id: Optional[str]) -> str:
    """Fallback categorization from StringID prefix + keyword."""
    if not string_id:
        return "Uncategorized"
    string_id = str(string_id)
    upper_id = string_id.upper()
    for prefix, category in STRINGID_PREFIX_TO_CATEGORY:
        if upper_id.startswith(prefix):
            return category
    lower_id = string_id.lower()
    for keyword, category in KEYWORD_TO_CATEGORY:
        if keyword in lower_id:
            return category
    return "Other"


# =============================================================================
# CategoryService
# =============================================================================


class CategoryService:
    """LDE two-tier category classification, fully grafted into LocaNext.

    Primary: MegaIndex D17 (export_file_stringids) → reverse map → LDE algorithm
    Fallback: C7 (stringid_to_entity) → entity type mapping
    Fallback: StringID prefix + keyword matching
    """

    def __init__(self):
        self._stringid_to_export: Optional[Dict[str, str]] = None
        self._mega_checked = False

    def _build_reverse_map(self):
        """Build StringID → export_filename from MegaIndex D17."""
        if self._mega_checked:
            return
        try:
            from server.tools.ldm.services.mega_index import get_mega_index
            mega = get_mega_index()
            if not mega._built:
                return  # Don't set _mega_checked — allow retry when MegaIndex is ready
            self._mega_checked = True

            # D17: export_file_stringids = {export_filename: {sid1, sid2, ...}}
            # Reverse it: {sid: export_filename}
            if mega.export_file_stringids:
                reverse = {}
                for export_name, sids in mega.export_file_stringids.items():
                    for sid in sids:
                        reverse[sid] = export_name
                self._stringid_to_export = reverse
                logger.info(f"[CATEGORY] Built reverse map: {len(reverse)} StringIDs → export filenames (LDE algorithm)")

            # Also cache entity map for fallback
            self._entity_map = mega.stringid_to_entity if len(mega.stringid_to_entity) > 0 else None
        except Exception as e:
            logger.debug(f"[CATEGORY] MegaIndex not available: {e}")

    def categorize_row(self, row: Dict) -> Dict:
        """Categorize using LDE's exact algorithm."""
        string_id = row.get("string_id")
        if not string_id:
            row["category"] = "Uncategorized"
            return row

        string_id = str(string_id)
        self._build_reverse_map()

        # Phase 1: LDE two-tier via export filename (best accuracy)
        if self._stringid_to_export:
            export_name = self._stringid_to_export.get(string_id)
            if export_name:
                row["category"] = categorize_by_export_path(export_name)
                return row

        # Phase 2: MegaIndex entity type (C7)
        if hasattr(self, '_entity_map') and self._entity_map:
            entity = self._entity_map.get(string_id.lower())
            if entity:
                entity_type = entity[0].lower()
                TYPE_MAP = {
                    "item": "Item", "character": "Character", "knowledge": "Knowledge",
                    "skill": "Skill", "gimmick": "Gimmick", "region": "Region",
                    "faction": "Faction", "quest": "Quest",
                }
                row["category"] = TYPE_MAP.get(entity_type, entity_type.capitalize())
                return row

        # Phase 3: StringID prefix + keyword fallback
        row["category"] = categorize_by_stringid(string_id)
        return row

    def categorize_rows(self, rows: List[Dict]) -> List[Dict]:
        """Batch-categorize."""
        for row in rows:
            self.categorize_row(row)
        return rows
