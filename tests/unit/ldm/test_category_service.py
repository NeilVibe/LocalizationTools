"""
Tests for CategoryService -- StringID prefix-based category classification.

Phase 16 Plan 01: Category Clustering
"""

from __future__ import annotations

import pytest

from server.tools.ldm.services.category_service import (
    categorize_by_stringid,
    CategoryService,
)


class TestCategorizeByStringid:
    """Test categorize_by_stringid() function."""

    @pytest.mark.parametrize(
        "string_id,expected",
        [
            ("SID_ITEM_001_NAME", "Item"),
            ("SID_ITEM_999_DESC", "Item"),
            ("SID_CHAR_005_DESC", "Character"),
            ("SID_CHAR_001_NAME", "Character"),
            ("SID_SKILL_010_NAME", "Skill"),
            ("SID_SKILL_042_DESC", "Skill"),
            ("SID_REGION_003_NAME", "Region"),
            ("SID_REGION_012_DESC", "Region"),
            ("SID_GIMMICK_007_DESC", "Gimmick"),
            ("SID_GIMMICK_001_NAME", "Gimmick"),
            ("SID_KNOW_CHAR_001_NAME", "Knowledge"),
            ("SID_KNOW_ITEM_002_DESC", "Knowledge"),
            ("SID_QUEST_050_NAME", "Quest"),
            ("SID_QUEST_001_DESC", "Quest"),
        ],
    )
    def test_known_prefixes(self, string_id: str, expected: str):
        assert categorize_by_stringid(string_id) == expected

    def test_unknown_prefix_returns_other(self):
        assert categorize_by_stringid("RANDOM_STRING") == "Other"
        assert categorize_by_stringid("SID_UNKNOWN_001") == "Other"
        assert categorize_by_stringid("SOMETHING_ELSE") == "Other"

    def test_empty_string_returns_uncategorized(self):
        assert categorize_by_stringid("") == "Uncategorized"

    def test_none_returns_uncategorized(self):
        assert categorize_by_stringid(None) == "Uncategorized"


class TestCategoryServiceCategorizeRow:
    """Test CategoryService.categorize_row() method."""

    def test_categorize_row_sets_category(self):
        svc = CategoryService()
        row = {"string_id": "SID_ITEM_001_NAME", "source": "Sword", "target": "Sword"}
        result = svc.categorize_row(row)
        assert result["category"] == "Item"

    def test_categorize_row_none_string_id(self):
        svc = CategoryService()
        row = {"string_id": None, "source": "Text", "target": "Text"}
        result = svc.categorize_row(row)
        assert result["category"] == "Uncategorized"

    def test_categorize_row_missing_string_id(self):
        svc = CategoryService()
        row = {"source": "Text", "target": "Text"}
        result = svc.categorize_row(row)
        assert result["category"] == "Uncategorized"

    def test_categorize_row_preserves_existing_fields(self):
        svc = CategoryService()
        row = {"string_id": "SID_CHAR_005_DESC", "source": "Hero", "id": 42}
        result = svc.categorize_row(row)
        assert result["source"] == "Hero"
        assert result["id"] == 42
        assert result["category"] == "Character"


class TestCategoryServiceCategorizeRows:
    """Test CategoryService.categorize_rows() batch method."""

    def test_batch_categorize(self):
        svc = CategoryService()
        rows = [
            {"string_id": "SID_ITEM_001_NAME"},
            {"string_id": "SID_CHAR_005_DESC"},
            {"string_id": "SID_QUEST_010_NAME"},
            {"string_id": None},
        ]
        result = svc.categorize_rows(rows)
        assert len(result) == 4
        assert result[0]["category"] == "Item"
        assert result[1]["category"] == "Character"
        assert result[2]["category"] == "Quest"
        assert result[3]["category"] == "Uncategorized"

    def test_batch_empty_list(self):
        svc = CategoryService()
        assert svc.categorize_rows([]) == []


class TestCategoryServiceFallback:
    """Test fallback to TwoTierCategoryMapper when StringID has no match."""

    def test_fallback_unknown_stringid(self):
        """Unknown StringID prefix falls back to 'Other'."""
        svc = CategoryService()
        row = {"string_id": "RANDOM_STRING", "source": "Text"}
        result = svc.categorize_row(row)
        assert result["category"] == "Other"
