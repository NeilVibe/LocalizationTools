"""
CategoryService -- Content category classification using LanguageDataExporter patterns.

Two-phase matching (ported from LanguageDataExporter/exporter/category_mapper.py):
1. StringID prefix matching (fast path: SID_ITEM_, SID_KNOW_, etc.)
2. Keyword matching in StringID (priority keywords: item, quest, skill, etc.)
3. Source text heuristic (dialog patterns, system patterns)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger


# =============================================================================
# Phase 1: StringID Prefix Mapping (fast path)
# =============================================================================

STRINGID_PREFIX_TO_CATEGORY: List[tuple[str, str]] = [
    ("SID_KNOW_", "Knowledge"),
    ("SID_GIMMICK_", "Gimmick"),
    ("SID_ITEM_", "Item"),
    ("SID_CHAR_", "Character"),
    ("SID_SKILL_", "Skill"),
    ("SID_REGION_", "Region"),
    ("SID_QUEST_", "Quest"),
    ("STR_KNOW_", "Knowledge"),
    ("STR_GIMMICK_", "Gimmick"),
    ("STR_ITEM_", "Item"),
    ("STR_CHAR_", "Character"),
    ("STR_SKILL_", "Skill"),
    ("STR_REGION_", "Region"),
    ("STR_QUEST_", "Quest"),
    ("STR_DIALOG_", "Dialog"),
    ("STR_SCRIPT_", "Script"),
    ("STR_UI_", "UI"),
    ("STR_SYSTEM_", "System"),
]


# =============================================================================
# Phase 2: Keyword Matching (LanguageDataExporter PRIORITY_KEYWORDS pattern)
# Checked if no prefix matches. Order matters — first match wins.
# =============================================================================

KEYWORD_TO_CATEGORY: List[tuple[str, str]] = [
    ("gimmick", "Gimmick"),
    ("item", "Item"),
    ("equip", "Item"),
    ("weapon", "Item"),
    ("armor", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("npc", "Character"),
    ("monster", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
    ("knowledge", "Knowledge"),
    ("dialog", "Dialog"),
    ("dialogue", "Dialog"),
    ("sequencer", "Sequencer"),
    ("narration", "Dialog"),
    ("script", "Script"),
    ("ui_", "UI"),
    ("localstring", "UI"),
    ("symbol", "UI"),
    ("tutorial", "Tutorial"),
    ("cutscene", "Sequencer"),
    ("cinematic", "Sequencer"),
]


# =============================================================================
# Public API
# =============================================================================


def categorize_by_stringid(string_id: Optional[str]) -> str:
    """Classify a row's content category using two-phase matching.

    Phase 1: Prefix match on StringID (O(k) where k = prefix count)
    Phase 2: Keyword search in StringID (O(j) where j = keyword count)

    Args:
        string_id: The StringID value.

    Returns:
        Category string.
    """
    if not string_id:
        return "Uncategorized"

    string_id = str(string_id)  # Guard against non-string types from DB
    upper_id = string_id.upper()

    # Phase 1: Prefix match (fast path)
    for prefix, category in STRINGID_PREFIX_TO_CATEGORY:
        if upper_id.startswith(prefix):
            return category

    # Phase 2: Keyword match (LanguageDataExporter pattern)
    lower_id = string_id.lower()
    for keyword, category in KEYWORD_TO_CATEGORY:
        if keyword in lower_id:
            return category

    return "Other"


class CategoryService:
    """Service for categorizing translation rows by content type.

    Three-phase categorization:
    1. MegaIndex entity lookup (C7: stringid_to_entity) — most accurate
    2. StringID prefix matching (fast path)
    3. Keyword matching in StringID (LanguageDataExporter pattern)
    """

    def __init__(self):
        self._mega_index = None
        self._mega_checked = False

    def _get_mega_index(self):
        """Lazy-load MegaIndex if available (built after path configure)."""
        if self._mega_checked:
            return self._mega_index
        self._mega_checked = True
        try:
            from server.tools.ldm.services.mega_index import get_mega_index
            mega = get_mega_index()
            if mega._built and len(mega.stringid_to_entity) > 0:
                self._mega_index = mega
                logger.info(f"[CATEGORY] Using MegaIndex C7: {len(mega.stringid_to_entity)} StringID→entity mappings")
        except Exception:
            pass
        return self._mega_index

    def _categorize_via_megaindex(self, string_id: str) -> Optional[str]:
        """Phase 0: Use MegaIndex C7 (stringid_to_entity) for exact categorization."""
        mega = self._get_mega_index()
        if not mega:
            return None
        entity = mega.stringid_to_entity.get(string_id)
        if entity:
            entity_type, _ = entity
            # Map entity types to category names
            TYPE_MAP = {
                "item": "Item", "character": "Character", "knowledge": "Knowledge",
                "skill": "Skill", "gimmick": "Gimmick", "region": "Region",
                "faction": "Faction", "quest": "Quest",
            }
            return TYPE_MAP.get(entity_type.lower(), entity_type.capitalize())
        return None

    def categorize_row(self, row: Dict) -> Dict:
        """Add 'category' key to a row dict."""
        string_id = row.get("string_id")

        # Phase 0: MegaIndex exact match (best accuracy)
        if string_id:
            mega_cat = self._categorize_via_megaindex(str(string_id))
            if mega_cat:
                row["category"] = mega_cat
                return row

        # Phase 1+2: Prefix + keyword fallback
        row["category"] = categorize_by_stringid(string_id)
        return row

    def categorize_rows(self, rows: List[Dict]) -> List[Dict]:
        """Batch-categorize a list of row dicts."""
        for row in rows:
            self.categorize_row(row)
        return rows
