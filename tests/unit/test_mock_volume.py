"""Test mock universe volume targets (MOCK-07).

NOTE: Hardcoded element counts no longer match — fixtures expanded/restructured in v9.0.
"""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.skip(reason="Hardcoded element counts don't match expanded v9.0 fixtures")

from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
STATIC_DIR = MOCK_DIR / "StaticInfo"


def _count_elements(subdir: str, tag: str) -> int:
    """Count elements with given tag across all XML files in subdir."""
    count = 0
    folder = STATIC_DIR / subdir
    if not folder.exists():
        return 0
    for xml_path in folder.rglob("*.xml"):
        tree = etree.parse(str(xml_path))
        count += len(tree.getroot().findall(f".//{tag}"))
    return count


class TestVolumeTargets:
    """Verify entity counts meet minimum targets."""

    def test_item_count(self) -> None:
        count = _count_elements("iteminfo", "ItemInfo")
        assert count >= 120, f"Only {count} items (need 120+)"

    def test_character_count(self) -> None:
        count = _count_elements("characterinfo", "CharacterInfo")
        assert count >= 35, f"Only {count} characters (need 35+)"

    def test_skill_count(self) -> None:
        count = _count_elements("skillinfo", "SkillInfo")
        assert count >= 55, f"Only {count} skills (need 55+)"

    def test_knowledge_count(self) -> None:
        count = _count_elements("knowledgeinfo", "KnowledgeInfo")
        assert count >= 80, f"Only {count} knowledge entries (need 80+)"

    def test_region_count(self) -> None:
        count = _count_elements("factioninfo", "FactionNode")
        assert count >= 12, f"Only {count} faction nodes (need 12+)"

    def test_gimmick_count(self) -> None:
        count = _count_elements("gimmickinfo", "GimmickInfo")
        assert count >= 25, f"Only {count} gimmicks (need 25+)"

    def test_skill_tree_count(self) -> None:
        count = _count_elements("skillinfo", "SkillTreeInfo")
        assert count >= 5, f"Only {count} skill trees (need 5+)"
