"""Tests for GameDataTreeService -- hierarchical XML tree parsing.

Phase 27: Tree Backend -- lxml-based tree walking for nested XML game data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.ldm.schemas.gamedata import TreeNode, GameDataTreeResponse
from server.tools.ldm.services.gamedata_tree_service import GameDataTreeService

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "mock_gamedata"
STATIC_INFO = FIXTURES / "StaticInfo"


@pytest.fixture
def svc() -> GameDataTreeService:
    """Create a GameDataTreeService rooted at the fixtures directory."""
    return GameDataTreeService(base_dir=FIXTURES)


# ── Test 1: TreeNode schema fields ──────────────────────────────────────────


def test_tree_node_schema_fields():
    """TreeNode has all required fields: tag, attributes, children, parent_id, node_id, editable_attrs."""
    node = TreeNode(node_id="test_0", tag="TestTag", attributes={"Key": "1"})
    assert node.tag == "TestTag"
    assert node.attributes == {"Key": "1"}
    assert node.children == []
    assert node.parent_id is None
    assert node.node_id == "test_0"
    assert node.editable_attrs == []


# ── Test 2: parse_file returns 6 SkillTreeInfo root nodes ───────────────────


def test_parse_skilltreeinfo_root_count(svc: GameDataTreeService):
    """parse_file on SkillTreeInfo returns 6 SkillTreeInfo root nodes."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    assert isinstance(result, GameDataTreeResponse)
    assert result.entity_type == "SkillTreeInfo"
    assert len(result.roots) == 6


# ── Test 3: SkillTreeInfo has nested SkillNode children ─────────────────────


def test_skilltreeinfo_has_nested_children(svc: GameDataTreeService):
    """Each SkillTreeInfo root has SkillNode children nested by ParentNodeId."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    first_tree = result.roots[0]
    assert first_tree.tag == "SkillTreeInfo"
    # SkillNodes should be nested, not flat -- first tree has 9 nodes in a chain
    assert len(first_tree.children) >= 1  # at least one root-level SkillNode
    # The tree should have depth > 1 (nested via ParentNodeId)
    child = first_tree.children[0]
    assert child.tag == "SkillNode"
    assert len(child.children) >= 1  # has nested children


# ── Test 4: ParentNodeId=0 becomes direct child, ParentNodeId=N nests ──────


def test_parent_node_id_resolution(svc: GameDataTreeService):
    """SkillNode ParentNodeId=0 is direct child; ParentNodeId=1 is child of NodeId=1."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    first_tree = result.roots[0]
    # ParentNodeId=0 → direct child of SkillTreeInfo
    root_skill = first_tree.children[0]
    assert root_skill.attributes.get("ParentNodeId") == "0"
    assert root_skill.attributes.get("NodeId") == "1"

    # NodeId=2 has ParentNodeId=1, so it should be child of NodeId=1
    child_of_1 = root_skill.children[0]
    assert child_of_1.attributes.get("ParentNodeId") == "1"
    assert child_of_1.attributes.get("NodeId") == "2"


# ── Test 5: GimmickInfo XML-nested children ─────────────────────────────────


def test_gimmick_xml_nested_children(svc: GameDataTreeService):
    """GimmickGroupInfo has XML-nested GimmickInfo > SealData children."""
    xml_path = str(
        STATIC_INFO / "gimmickinfo" / "Item" / "GimmickInfo_Item_Chest.staticinfo.xml"
    )
    result = svc.parse_file(xml_path)

    assert result.entity_type == "GimmickGroupInfo"
    assert len(result.roots) == 9  # 9 GimmickGroupInfo entries

    first_group = result.roots[0]
    assert first_group.tag == "GimmickGroupInfo"
    # Should have GimmickInfo child
    assert len(first_group.children) >= 1
    gimmick = first_group.children[0]
    assert gimmick.tag == "GimmickInfo"
    # GimmickInfo should have SealData child
    assert len(gimmick.children) >= 1
    seal = gimmick.children[0]
    assert seal.tag == "SealData"


# ── Test 6: KnowledgeInfo flat (no nesting) ─────────────────────────────────


def test_knowledgeinfo_flat_no_nesting(svc: GameDataTreeService):
    """KnowledgeInfo entries are flat -- no parent/child nesting."""
    xml_path = str(
        STATIC_INFO / "knowledgeinfo" / "knowledgeinfo_character.staticinfo.xml"
    )
    result = svc.parse_file(xml_path)

    assert result.entity_type == "KnowledgeInfo"
    assert len(result.roots) == 36  # 36 KnowledgeInfo entries

    # Each root should have zero children (flat)
    for root_node in result.roots:
        assert root_node.tag == "KnowledgeInfo"
        assert len(root_node.children) == 0


# ── Test 7: parse_folder returns combined tree ──────────────────────────────


def test_parse_folder_combined_tree(svc: GameDataTreeService):
    """parse_folder on StaticInfo returns combined tree across all XML files."""
    result = svc.parse_folder(str(STATIC_INFO))

    assert len(result.files) > 0
    assert result.total_nodes > 0
    assert result.base_path == str(STATIC_INFO)

    # Should have files from multiple subdirectories
    entity_types = {f.entity_type for f in result.files}
    assert "SkillTreeInfo" in entity_types or "KnowledgeInfo" in entity_types


# ── Test 8: max_depth limiting ──────────────────────────────────────────────


def test_max_depth_limits_children(svc: GameDataTreeService):
    """max_depth=0 returns nodes with no children; max_depth=1 returns 1 level."""
    xml_path = str(
        STATIC_INFO / "gimmickinfo" / "Item" / "GimmickInfo_Item_Chest.staticinfo.xml"
    )

    # max_depth=0 → no children at all
    result_depth0 = svc.parse_file(xml_path, max_depth=0)
    for root_node in result_depth0.roots:
        assert len(root_node.children) == 0

    # max_depth=1 → one level of children, but no grandchildren
    result_depth1 = svc.parse_file(xml_path, max_depth=1)
    for root_node in result_depth1.roots:
        for child in root_node.children:
            assert len(child.children) == 0

    # max_depth=-1 (unlimited) → has grandchildren
    result_unlimited = svc.parse_file(xml_path, max_depth=-1)
    has_grandchildren = False
    for root_node in result_unlimited.roots:
        for child in root_node.children:
            if len(child.children) > 0:
                has_grandchildren = True
    assert has_grandchildren


# ── Test 9: Malformed XML handled gracefully ────────────────────────────────


def test_malformed_xml_handled(svc: GameDataTreeService, tmp_path: Path):
    """Malformed XML is handled gracefully via lxml recover=True."""
    # Create a malformed XML file within the fixtures base
    malformed = FIXTURES / "_test_malformed.xml"
    try:
        malformed.write_text(
            '<?xml version="1.0"?><Root><Item Key="1" Name="Test"/><Broken></Root>',
            encoding="utf-8",
        )
        result = svc.parse_file(str(malformed))
        # Should still return something (partial parse) or raise cleanly
        assert isinstance(result, GameDataTreeResponse)
    finally:
        malformed.unlink(missing_ok=True)


# ── Test 10: File not found raises ──────────────────────────────────────────


def test_file_not_found_raises(svc: GameDataTreeService):
    """Nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        svc.parse_file(str(STATIC_INFO / "nonexistent.xml"))
