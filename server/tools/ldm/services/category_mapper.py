"""
Two-Tier Category Mapper -- String type classification.

Ported from QuickCheck's TwoTierCategoryMapper. Classifies strings into
categories using a two-tier algorithm:
- Tier 1 (STORY): Detects dialog and sequencer paths
- Tier 2 (GAME_DATA): Priority keyword matching in file paths

Phase 5.1: Contextual Intelligence & QA Engine (Plan 01)
"""

from __future__ import annotations

from typing import List, Tuple

from loguru import logger


# =============================================================================
# Constants
# =============================================================================

# Tier 2 priority keywords: checked in order against file path (lowercased)
PRIORITY_KEYWORDS: List[Tuple[str, str]] = [
    ("gimmick", "Gimmick"),
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
    ("npc", "NPC"),
    ("monster", "Monster"),
    ("buff", "Buff"),
    ("achievement", "Achievement"),
    ("tutorial", "Tutorial"),
    ("loading", "Loading"),
]

# Tier 1 STORY: dialog sub-categories
DIALOG_SUBCATEGORIES = {
    "npc": "NPC Dialog",
    "system": "System Dialog",
    "cutscene": "Cutscene Dialog",
    "tutorial": "Tutorial Dialog",
}


# =============================================================================
# TwoTierCategoryMapper
# =============================================================================


class TwoTierCategoryMapper:
    """Classifies strings into categories using two-tier algorithm.

    Tier 1 (STORY):
        - dialog/ in path -> "Dialog" (with sub-category detection)
        - sequencer/ in path -> "Sequencer"

    Tier 2 (GAME_DATA):
        - Priority keyword matching against file path
        - Falls back to "Other" if no match
    """

    def categorize(self, file_path: str, text: str = "") -> str:
        """Classify a string based on its file path and content.

        Args:
            file_path: Source file path (e.g., "path/dialog/npc_quest.xml").
            text: The string content (currently used for future extensions).

        Returns:
            Category string (e.g., "Dialog", "Item", "Character", "Other").
        """
        path_lower = file_path.lower()

        # Tier 1: STORY patterns
        if "/dialog/" in path_lower or "\\dialog\\" in path_lower or path_lower.startswith("dialog/"):
            return "Dialog"

        if "/sequencer/" in path_lower or "\\sequencer\\" in path_lower or path_lower.startswith("sequencer/"):
            return "Sequencer"

        # Tier 2: GAME_DATA priority keywords
        for keyword, category in PRIORITY_KEYWORDS:
            if keyword in path_lower:
                return category

        # Fallback
        return "Other"

    def categorize_batch(self, items: List[Tuple[str, str]]) -> List[str]:
        """Batch categorization of (path, text) pairs.

        Args:
            items: List of (file_path, text) tuples.

        Returns:
            List of category strings in same order.
        """
        return [self.categorize(path, text) for path, text in items]


# =============================================================================
# Module-level convenience function
# =============================================================================

_default_mapper: TwoTierCategoryMapper = TwoTierCategoryMapper()


def categorize_string(file_path: str, text: str = "") -> str:
    """Convenience wrapper using default mapper instance.

    Args:
        file_path: Source file path.
        text: The string content.

    Returns:
        Category string.
    """
    return _default_mapper.categorize(file_path, text)
