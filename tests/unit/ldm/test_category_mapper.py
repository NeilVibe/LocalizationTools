"""
Tests for TwoTierCategoryMapper -- string type classification.

Phase 5.1: Contextual Intelligence & QA Engine (Plan 01)
"""

from __future__ import annotations

import pytest

from server.tools.ldm.services.category_mapper import (
    TwoTierCategoryMapper,
    categorize_string,
)


# =============================================================================
# Tier 1: STORY Patterns
# =============================================================================


class TestTier1Story:
    """Test Tier 1 STORY pattern detection (dialog, sequencer)."""

    def test_dialog_path_returns_dialog(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/dialog/npc_quest_dialog.xml", "Hello brave warrior")
        assert result == "Dialog"

    def test_sequencer_path_returns_sequencer(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/sequencer/seq_intro.xml", "text")
        assert result == "Sequencer"


# =============================================================================
# Tier 2: GAME_DATA Priority Keywords
# =============================================================================


class TestTier2GameData:
    """Test Tier 2 GAME_DATA priority keyword matching."""

    def test_iteminfo_returns_item(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/iteminfo/iteminfo_sword.xml", "Iron Sword")
        assert result == "Item"

    def test_characterinfo_returns_character(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/characterinfo/characterinfo_hero.xml", "Hero")
        assert result == "Character"

    def test_questinfo_returns_quest(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/questinfo/questinfo_main.xml", "Main Quest")
        assert result == "Quest"

    def test_skillinfo_returns_skill(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/skillinfo/skillinfo_fire.xml", "text")
        assert result == "Skill"

    def test_gimmick_returns_gimmick(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/gimmickinfo/gimmick_trap.xml", "text")
        assert result == "Gimmick"

    def test_region_returns_region(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/regioninfo/regioninfo_map.xml", "text")
        assert result == "Region"

    def test_faction_returns_faction(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/factioninfo/factioninfo_alliance.xml", "text")
        assert result == "Faction"


# =============================================================================
# Fallback
# =============================================================================


class TestFallback:
    """Test fallback to 'Other' for unrecognized paths."""

    def test_unknown_path_returns_other(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("path/unknown/other.xml", "text")
        assert result == "Other"

    def test_empty_path_returns_other(self):
        mapper = TwoTierCategoryMapper()
        result = mapper.categorize("", "text")
        assert result == "Other"


# =============================================================================
# Batch
# =============================================================================


class TestBatch:
    """Test categorize_batch() handles list of (path, text) pairs."""

    def test_batch_categorization(self):
        mapper = TwoTierCategoryMapper()
        items = [
            ("path/dialog/npc.xml", "Hello"),
            ("path/iteminfo/item.xml", "Sword"),
            ("path/unknown/x.xml", "text"),
        ]
        results = mapper.categorize_batch(items)
        assert results == ["Dialog", "Item", "Other"]

    def test_empty_batch(self):
        mapper = TwoTierCategoryMapper()
        results = mapper.categorize_batch([])
        assert results == []


# =============================================================================
# Module-level convenience function
# =============================================================================


class TestConvenienceFunction:
    """Test categorize_string() module-level function."""

    def test_categorize_string_works(self):
        result = categorize_string("path/dialog/npc.xml", "Hello")
        assert result == "Dialog"

    def test_categorize_string_item(self):
        result = categorize_string("path/iteminfo/item.xml", "Sword")
        assert result == "Item"
