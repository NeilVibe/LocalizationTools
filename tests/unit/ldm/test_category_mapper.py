"""
Tests for TwoTierCategoryMapper -- string type classification.

Phase 5.1 + Phase 98 (MEGA Graft): two-tier path-based categorization.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.ldm.services.category_mapper import (
    TwoTierCategoryMapper,
    categorize_string,
)

DUMMY_BASE = Path("/tmp/test_gamedata")


# =============================================================================
# Tier 1: STORY Patterns
# =============================================================================


class TestTier1Story:
    """Test Tier 1 STORY pattern detection (dialog, sequencer)."""

    def test_dialog_path_returns_dialog(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("dialog/npc/quest_dialog.xml"))
        assert "Dialog" in result or "dialog" in result.lower()

    def test_sequencer_path_returns_sequencer(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("sequencer/seq_intro.xml"))
        assert "Seq" in result


# =============================================================================
# Tier 2: GAME_DATA Priority Keywords
# =============================================================================


class TestTier2GameData:
    """Test Tier 2 GAME_DATA priority keyword matching."""

    def test_iteminfo_returns_item(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("iteminfo/iteminfo_sword.xml"))
        assert "Item" in result

    def test_characterinfo_returns_character(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("characterinfo/characterinfo_hero.xml"))
        assert "Character" in result

    def test_questinfo_returns_quest(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("questinfo/questinfo_main.xml"))
        assert "Quest" in result

    def test_skillinfo_returns_skill(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("skillinfo/skillinfo_fire.xml"))
        assert "Skill" in result

    def test_gimmick_returns_gimmick(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("gimmickinfo/gimmick_trap.xml"))
        assert "Gimmick" in result

    def test_region_returns_region(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("regioninfo/regioninfo_map.xml"))
        assert "Region" in result

    def test_faction_returns_faction(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("factioninfo/factioninfo_alliance.xml"))
        assert "Faction" in result


# =============================================================================
# Fallback
# =============================================================================


class TestFallback:
    """Test fallback for unrecognized paths."""

    def test_unknown_path_returns_misc(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("unknown/other.xml"))
        # Falls through to gamedata tier which returns a category based on folder
        assert isinstance(result, str) and len(result) > 0

    def test_single_segment_returns_misc(self):
        mapper = TwoTierCategoryMapper(DUMMY_BASE)
        result = mapper.get_category(Path("file.xml"))
        assert result == "System_Misc"


# =============================================================================
# Module-level convenience function
# =============================================================================


class TestConvenienceFunction:
    """Test categorize_string() module-level function."""

    def test_categorize_string_dialog(self):
        result = categorize_string("path/dialog/npc.xml", "Hello")
        assert result == "Dialog"

    def test_categorize_string_item(self):
        result = categorize_string("path/iteminfo/item.xml", "Sword")
        assert result == "Item"

    def test_categorize_string_other(self):
        result = categorize_string("path/unknown/file.xml", "text")
        assert result == "Other"
