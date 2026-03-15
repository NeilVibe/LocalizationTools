"""
CategoryService -- StringID prefix-based content category classification.

Phase 16 Plan 01: Category Clustering

Classifies translation rows by content type using StringID prefix as fast path.
Falls back to TwoTierCategoryMapper for file-path-based classification.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger


# =============================================================================
# StringID Prefix to Category Mapping
# =============================================================================

# Ordered by specificity: longer prefixes first to avoid false matches
# e.g., SID_KNOW_ must be checked before SID_ generic fallback
STRINGID_PREFIX_TO_CATEGORY: List[tuple[str, str]] = [
    ("SID_KNOW_", "Knowledge"),
    ("SID_GIMMICK_", "Gimmick"),
    ("SID_ITEM_", "Item"),
    ("SID_CHAR_", "Character"),
    ("SID_SKILL_", "Skill"),
    ("SID_REGION_", "Region"),
    ("SID_QUEST_", "Quest"),
]


# =============================================================================
# Public API
# =============================================================================


def categorize_by_stringid(string_id: Optional[str]) -> str:
    """Classify a row's content category from its StringID prefix.

    O(k) prefix lookup where k = number of known prefixes (currently 7).

    Args:
        string_id: The StringID value (e.g., "SID_ITEM_001_NAME").

    Returns:
        Category string: "Item", "Character", "Skill", "Region",
        "Gimmick", "Knowledge", "Quest", "Other", or "Uncategorized".
    """
    if not string_id:
        return "Uncategorized"

    upper_id = string_id.upper()
    for prefix, category in STRINGID_PREFIX_TO_CATEGORY:
        if upper_id.startswith(prefix):
            return category

    return "Other"


class CategoryService:
    """Service for categorizing translation rows by content type.

    Primary: StringID prefix-based classification (fast, O(1) per row).
    Fallback: TwoTierCategoryMapper for file-path heuristics (not used in
    current implementation since StringID coverage is sufficient).
    """

    def categorize_row(self, row: Dict) -> Dict:
        """Add 'category' key to a row dict based on its string_id.

        Args:
            row: Row dict with optional 'string_id' key.

        Returns:
            Same row dict with 'category' key added.
        """
        string_id = row.get("string_id")
        row["category"] = categorize_by_stringid(string_id)
        return row

    def categorize_rows(self, rows: List[Dict]) -> List[Dict]:
        """Batch-categorize a list of row dicts.

        Args:
            rows: List of row dicts.

        Returns:
            Same list with 'category' key added to each row.
        """
        for row in rows:
            self.categorize_row(row)
        return rows
