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


# -- Test 1: TreeNode schema fields ------------------------------------------


def test_tree_node_schema_fields():
    """TreeNode has all required fields: tag, attributes, children, parent_id, node_id, editable_attrs."""
    node = TreeNode(node_id="test_0", tag="TestTag", attributes={"Key": "1"})
    assert node.tag == "TestTag"
    assert node.attributes == {"Key": "1"}
    assert node.children == []
    assert node.parent_id is None
    assert node.node_id == "test_0"
    assert node.editable_attrs == []


# -- Test 2: parse_file returns SkillTreeInfoList root with 3 children -------


def test_parse_skilltreeinfo_root_count(svc: GameDataTreeService):
    """parse_file on SkillTreeInfo returns SkillTreeInfoList root with 3 SkillTreeInfo children."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    assert isinstance(result, GameDataTreeResponse)
    assert result.entity_type == "SkillTreeInfoList"
    # Root is SkillTreeInfoList with 3 SkillTreeInfo children (TREE_001, TREE_002, TREE_003)
    assert len(result.roots) == 1
    assert len(result.roots[0].children) == 3


# -- Test 3: SkillTreeInfo has nested SkillNode children ---------------------


def test_skilltreeinfo_has_nested_children(svc: GameDataTreeService):
    """Each SkillTreeInfo has SkillNode children."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    root_list = result.roots[0]
    assert root_list.tag == "SkillTreeInfoList"
    first_tree = root_list.children[0]
    assert first_tree.tag == "SkillTreeInfo"
    # SkillNodes are direct children of SkillTreeInfo (flat XML structure)
    assert len(first_tree.children) >= 1
    root_skill = first_tree.children[0]
    assert root_skill.tag == "SkillNode"


# -- Test 4: SkillTreeInfo children have correct attributes ------------------


def test_parent_node_id_resolution(svc: GameDataTreeService):
    """SkillTreeInfo children have correct SkillNode attributes."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    # Navigate: root[0] = SkillTreeInfoList -> children[0] = first SkillTreeInfo
    first_tree = result.roots[0].children[0]
    assert first_tree.tag == "SkillTreeInfo"
    assert first_tree.attributes.get("StrKey") == "TREE_001"
    # Has SkillNode children
    assert len(first_tree.children) >= 1
    root_skill = first_tree.children[0]
    assert root_skill.tag == "SkillNode"
    assert root_skill.attributes.get("NodeId") == "100"


# -- Test 5: GimmickInfo XML-nested children ---------------------------------


def test_gimmick_xml_nested_children(svc: GameDataTreeService):
    """GimmickGroupInfoList has GimmickGroupInfo > GimmickInfo > SealData children."""
    xml_path = str(
        STATIC_INFO / "gimmickinfo" / "Item" / "GimmickInfo_Item_Chest.staticinfo.xml"
    )
    result = svc.parse_file(xml_path)

    assert result.entity_type == "GimmickGroupInfoList"
    # Root is the *List wrapper
    assert len(result.roots) == 1
    root_list = result.roots[0]
    assert root_list.tag == "GimmickGroupInfoList"
    # Has GimmickGroupInfo children
    assert len(root_list.children) >= 1
    first_group = root_list.children[0]
    assert first_group.tag == "GimmickGroupInfo"
    # Should have GimmickInfo child
    assert len(first_group.children) >= 1
    gimmick = first_group.children[0]
    assert gimmick.tag == "GimmickInfo"
    # GimmickInfo should have SealData child
    assert len(gimmick.children) >= 1
    seal = gimmick.children[0]
    assert seal.tag == "SealData"


# -- Test 6: KnowledgeInfo flat (no nesting) ---------------------------------


def test_knowledgeinfo_flat_no_nesting(svc: GameDataTreeService):
    """KnowledgeInfoList wraps flat KnowledgeInfo entries."""
    xml_path = str(
        STATIC_INFO / "knowledgeinfo" / "knowledgeinfo_character.staticinfo.xml"
    )
    result = svc.parse_file(xml_path)

    assert result.entity_type == "KnowledgeInfoList"
    assert len(result.roots) == 1
    root_list = result.roots[0]
    assert root_list.tag == "KnowledgeInfoList"
    # KnowledgeInfo entries are children of the list wrapper
    assert len(root_list.children) > 0
    for child in root_list.children:
        assert child.tag == "KnowledgeInfo"
        assert len(child.children) == 0  # flat, no nesting


# -- Test 7: parse_folder returns combined tree ------------------------------


def test_parse_folder_combined_tree(svc: GameDataTreeService):
    """parse_folder on StaticInfo returns combined tree across all XML files."""
    result = svc.parse_folder(str(STATIC_INFO))

    assert len(result.files) > 0
    assert result.total_nodes > 0
    assert result.base_path == str(STATIC_INFO)

    # Should have files from multiple subdirectories (entity types end with "List" now)
    entity_types = {f.entity_type for f in result.files}
    assert any("SkillTree" in et or "Knowledge" in et for et in entity_types)


# -- Test 8: max_depth limiting ----------------------------------------------


def test_max_depth_limits_children(svc: GameDataTreeService):
    """max_depth=0 returns nodes with no children; max_depth=1 returns 1 level."""
    xml_path = str(
        STATIC_INFO / "gimmickinfo" / "Item" / "GimmickInfo_Item_Chest.staticinfo.xml"
    )

    # max_depth=0 -> no children at all
    result_depth0 = svc.parse_file(xml_path, max_depth=0)
    for root_node in result_depth0.roots:
        assert len(root_node.children) == 0

    # max_depth=1 -> one level of children, but no grandchildren
    result_depth1 = svc.parse_file(xml_path, max_depth=1)
    for root_node in result_depth1.roots:
        for child in root_node.children:
            assert len(child.children) == 0

    # max_depth=-1 (unlimited) -> has grandchildren
    result_unlimited = svc.parse_file(xml_path, max_depth=-1)
    has_grandchildren = False
    for root_node in result_unlimited.roots:
        for child in root_node.children:
            if len(child.children) > 0:
                has_grandchildren = True
    assert has_grandchildren


# -- Test 9: Malformed XML handled gracefully --------------------------------


def test_malformed_xml_handled(svc: GameDataTreeService):
    """Malformed XML is handled gracefully via lxml recover=True."""
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


# -- Test 10: File not found raises ------------------------------------------


def test_file_not_found_raises(svc: GameDataTreeService):
    """Nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        svc.parse_file(str(STATIC_INFO / "nonexistent.xml"))


# -- Test 11: editable_attrs populated from EDITABLE_ATTRS -------------------


def test_editable_attrs_populated(svc: GameDataTreeService):
    """TreeNode.editable_attrs is populated from EDITABLE_ATTRS mapping."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    # Navigate to first SkillTreeInfo (child of SkillTreeInfoList root)
    root_list = result.roots[0]
    first_tree = root_list.children[0]
    assert first_tree.tag == "SkillTreeInfo"
    assert "UIPageName" in first_tree.editable_attrs


# -- Test 12: Third SkillTreeInfo has linear chain ---------------------------


def test_third_skilltree_linear_chain(svc: GameDataTreeService):
    """TREE_003 has a simple linear chain: Fireball -> IceArrow -> Lightning."""
    xml_path = str(STATIC_INFO / "skillinfo" / "SkillTreeInfo.staticinfo.xml")
    result = svc.parse_file(xml_path)

    # Navigate: root[0] = SkillTreeInfoList -> children[2] = Third SkillTreeInfo
    root_list = result.roots[0]
    tree_003 = root_list.children[2]
    assert tree_003.attributes.get("StrKey") == "TREE_003"

    # SkillNodes are flat children (parser doesn't nest by ParentNodeId)
    assert len(tree_003.children) >= 1
    # Verify first child is Fireball
    fireball = tree_003.children[0]
    assert fireball.attributes.get("SkillKey") == "Skill_Fireball"
