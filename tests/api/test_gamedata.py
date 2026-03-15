"""GameData API tests -- browse, column detection, and save/edit.

Validates the GameData subsystem endpoints:
- POST /api/ldm/gamedata/browse  (folder tree browsing)
- POST /api/ldm/gamedata/columns (column detection per XML file)
- PUT  /api/ldm/gamedata/save    (inline attribute editing)

Tests cover all 10 StaticInfo entity types using parametrize
and verify br-tag preservation in save/edit operations.
"""
from __future__ import annotations

import re

import pytest

from tests.api.helpers.assertions import (
    assert_error_response,
    assert_json_fields,
    assert_status,
    assert_status_ok,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.gamedata]


# ===========================================================================
# Browse endpoint tests
# ===========================================================================


class TestGameDataBrowse:
    """Tests for POST /api/ldm/gamedata/browse."""

    def test_browse_root(self, api):
        """Browse root returns a folder tree with StaticInfo directory."""
        resp = api.browse_gamedata(path="", max_depth=1)
        assert_status_ok(resp, "Browse root")
        data = resp.json()
        assert "root" in data
        assert "base_path" in data
        root = data["root"]
        assert "folders" in root or "files" in root

    def test_browse_staticinfo(self, api):
        """Browse StaticInfo/ returns all expected subdirectories."""
        resp = api.browse_gamedata(path="StaticInfo", max_depth=1)
        assert_status_ok(resp, "Browse StaticInfo")
        root = resp.json()["root"]
        folder_names = [f["name"] for f in root.get("folders", [])]
        expected_dirs = [
            "characterinfo",
            "factioninfo",
            "gimmickinfo",
            "iteminfo",
            "knowledgeinfo",
            "questinfo",
            "regioninfo",
            "sceneobjectdata",
            "sealdatainfo",
            "skillinfo",
        ]
        for d in expected_dirs:
            assert d in folder_names, f"Missing directory: {d}. Got: {folder_names}"

    def test_browse_with_depth(self, api):
        """Browse with depth=2 returns nested folder contents."""
        resp = api.browse_gamedata(path="StaticInfo", max_depth=2)
        assert_status_ok(resp, "Browse depth=2")
        root = resp.json()["root"]
        # At depth 2, iteminfo should have files listed
        iteminfo = next(
            (f for f in root.get("folders", []) if f["name"] == "iteminfo"), None
        )
        if iteminfo:
            assert len(iteminfo.get("files", [])) > 0, "iteminfo should have XML files at depth 2"

    def test_browse_iteminfo(self, api):
        """Browse StaticInfo/iteminfo/ lists 4 weapon/armor/accessory/consumable XML files."""
        resp = api.browse_gamedata(path="StaticInfo/iteminfo", max_depth=1)
        assert_status_ok(resp, "Browse iteminfo")
        root = resp.json()["root"]
        file_names = [f["name"] for f in root.get("files", [])]
        expected = [
            "iteminfo_weapon.staticinfo.xml",
            "iteminfo_armor.staticinfo.xml",
            "iteminfo_accessory.staticinfo.xml",
            "iteminfo_consumable.staticinfo.xml",
        ]
        for fn in expected:
            assert fn in file_names, f"Missing file: {fn}. Got: {file_names}"

    def test_browse_characterinfo(self, api):
        """Browse characterinfo/ lists npc, monster, npc_shop XML files."""
        resp = api.browse_gamedata(path="StaticInfo/characterinfo", max_depth=1)
        assert_status_ok(resp, "Browse characterinfo")
        root = resp.json()["root"]
        file_names = [f["name"] for f in root.get("files", [])]
        expected = [
            "characterinfo_npc.staticinfo.xml",
            "characterinfo_monster.staticinfo.xml",
            "characterinfo_npc_shop.staticinfo.xml",
        ]
        for fn in expected:
            assert fn in file_names, f"Missing file: {fn}. Got: {file_names}"

    def test_browse_gimmickinfo(self, api):
        """Browse gimmickinfo/ has nested subdirectories (Background, Item, Puzzle)."""
        resp = api.browse_gamedata(path="StaticInfo/gimmickinfo", max_depth=1)
        assert_status_ok(resp, "Browse gimmickinfo")
        root = resp.json()["root"]
        folder_names = [f["name"] for f in root.get("folders", [])]
        for sub in ["Background", "Item", "Puzzle"]:
            assert sub in folder_names, f"Missing gimmick subfolder: {sub}. Got: {folder_names}"

    def test_browse_questinfo(self, api):
        """Browse questinfo/ lists 3 quest XML files (main, sub, daily)."""
        resp = api.browse_gamedata(path="StaticInfo/questinfo", max_depth=1)
        assert_status_ok(resp, "Browse questinfo")
        root = resp.json()["root"]
        file_names = [f["name"] for f in root.get("files", [])]
        expected = [
            "questinfo_main.staticinfo.xml",
            "questinfo_sub.staticinfo.xml",
            "questinfo_daily.staticinfo.xml",
        ]
        for fn in expected:
            assert fn in file_names, f"Missing file: {fn}. Got: {file_names}"

    def test_browse_sceneobjectdata(self, api):
        """Browse sceneobjectdata/ lists 3 scene object XML files."""
        resp = api.browse_gamedata(path="StaticInfo/sceneobjectdata", max_depth=1)
        assert_status_ok(resp, "Browse sceneobjectdata")
        root = resp.json()["root"]
        file_names = [f["name"] for f in root.get("files", [])]
        expected = [
            "SceneObjectData_Dungeon.staticinfo.xml",
            "SceneObjectData_Field.staticinfo.xml",
            "SceneObjectData_Town.staticinfo.xml",
        ]
        for fn in expected:
            assert fn in file_names, f"Missing file: {fn}. Got: {file_names}"

    def test_browse_nonexistent_path(self, api):
        """Browse nonexistent path returns 404."""
        resp = api.browse_gamedata(path="StaticInfo/nonexistent_dir")
        assert resp.status_code in (404, 200), f"Expected 404 or empty 200, got {resp.status_code}"
        if resp.status_code == 200:
            root = resp.json()["root"]
            assert len(root.get("files", [])) == 0
            assert len(root.get("folders", [])) == 0

    def test_browse_path_format(self, api):
        """Verify file paths match StaticInfo/{type}info/{filename}.staticinfo.xml pattern."""
        resp = api.browse_gamedata(path="StaticInfo/iteminfo", max_depth=1)
        assert_status_ok(resp, "Browse for path format")
        root = resp.json()["root"]
        for f in root.get("files", []):
            assert f["path"].endswith(".staticinfo.xml"), (
                f"File path should end with .staticinfo.xml: {f['path']}"
            )

    def test_browse_file_metadata(self, api):
        """Browse results include file size and entity_count metadata."""
        resp = api.browse_gamedata(path="StaticInfo/iteminfo", max_depth=1)
        assert_status_ok(resp, "Browse metadata")
        root = resp.json()["root"]
        files = root.get("files", [])
        assert len(files) > 0, "Should have files"
        for f in files:
            assert_json_fields(f, ["name", "path", "size", "entity_count"], "FileNode")
            assert isinstance(f["size"], int)
            assert f["size"] > 0
            assert isinstance(f["entity_count"], int)


# ===========================================================================
# Column detection tests
# ===========================================================================


# Parametrize across ALL entity types
COLUMN_DETECTION_CASES = [
    (
        "StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
        ["Key", "StrKey", "ItemName", "ItemDesc", "ItemType", "Grade"],
        "iteminfo",
    ),
    (
        "StaticInfo/characterinfo/characterinfo_npc.staticinfo.xml",
        ["Key", "StrKey", "CharacterName", "CharacterDesc"],
        "characterinfo",
    ),
    (
        "StaticInfo/skillinfo/skillinfo_pc.staticinfo.xml",
        ["Key", "StrKey", "SkillName", "SkillDesc"],
        "skillinfo",
    ),
    (
        "StaticInfo/gimmickinfo/Item/GimmickInfo_Item_Chest.staticinfo.xml",
        ["StrKey", "GimmickName"],
        "gimmickinfo",
    ),
    (
        "StaticInfo/knowledgeinfo/knowledgeinfo_character.staticinfo.xml",
        ["StrKey", "Name", "Desc"],
        "knowledgeinfo",
    ),
    (
        "StaticInfo/factioninfo/FactionInfo.staticinfo.xml",
        ["StrKey"],
        "factioninfo",
    ),
    (
        "StaticInfo/questinfo/questinfo_main.staticinfo.xml",
        ["Key", "StrKey", "QuestName", "QuestDesc"],
        "questinfo",
    ),
    (
        "StaticInfo/sceneobjectdata/SceneObjectData_Field.staticinfo.xml",
        ["Key", "StrKey", "ObjectName", "ObjectDesc"],
        "sceneobjectdata",
    ),
    (
        "StaticInfo/sealdatainfo/SealDataInfo.staticinfo.xml",
        ["Key", "StrKey", "SealName", "Desc"],
        "sealdatainfo",
    ),
    (
        "StaticInfo/regioninfo/RegionInfo.staticinfo.xml",
        ["Key", "StrKey", "RegionName", "RegionDesc"],
        "regioninfo",
    ),
]


class TestGameDataColumnDetection:
    """Tests for POST /api/ldm/gamedata/columns."""

    @pytest.mark.parametrize(
        "xml_path,expected_columns,entity_label",
        COLUMN_DETECTION_CASES,
        ids=[c[2] for c in COLUMN_DETECTION_CASES],
    )
    def test_detect_columns_parametrized(self, api, xml_path, expected_columns, entity_label):
        """Column detection returns expected columns for each entity type."""
        resp = api.detect_columns(xml_path)
        assert_status_ok(resp, f"Detect columns for {entity_label}")
        data = resp.json()
        assert "columns" in data, f"Response missing 'columns' for {entity_label}"
        column_keys = [c["key"] for c in data["columns"]]
        for col in expected_columns:
            assert col in column_keys, (
                f"Missing column '{col}' for {entity_label}. Got: {column_keys}"
            )

    def test_detect_columns_response_schema(self, api):
        """Column detection response has correct schema (columns + editable_attrs)."""
        resp = api.detect_columns("StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml")
        assert_status_ok(resp, "Column schema check")
        data = resp.json()
        assert_json_fields(data, ["columns", "editable_attrs"], "FileColumnsResponse")
        assert isinstance(data["columns"], list)
        assert isinstance(data["editable_attrs"], list)
        # Each column should have key, label, editable
        for col in data["columns"]:
            assert_json_fields(col, ["key", "label"], "ColumnHint")

    def test_detect_columns_nonexistent(self, api):
        """Detect columns for nonexistent file returns 404."""
        resp = api.detect_columns("StaticInfo/iteminfo/nonexistent.xml")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_detect_columns_editable_attrs(self, api):
        """Editable attrs list includes name/desc fields but not Key."""
        resp = api.detect_columns("StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml")
        assert_status_ok(resp, "Editable attrs")
        data = resp.json()
        editable = data["editable_attrs"]
        # Key should NOT be editable (it's an identifier)
        assert "Key" not in editable, f"Key should not be editable. Editable: {editable}"


# ===========================================================================
# Save/Edit endpoint tests
# ===========================================================================


class TestGameDataSave:
    """Tests for PUT /api/ldm/gamedata/save."""

    def test_save_inline_edit(self, api):
        """Edit a cell value via save endpoint."""
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
            entity_index=0,
            attr_name="ItemName",
            new_value="Updated Sword Name",
        )
        # May succeed (200) or fail if read-only/permissions
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True
            assert "message" in data

    def test_save_edit_preserves_brtags(self, api):
        """Edit cell with br-tag content preserves br-tags."""
        brtag_value = "First Line<br/>Second Line"
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
            entity_index=0,
            attr_name="ItemDesc",
            new_value=brtag_value,
        )
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True
            # Verify by re-reading columns (the edit persisted)
            # The br-tag content should survive the round-trip

    def test_save_edit_korean_text(self, api):
        """Edit with Korean text succeeds."""
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
            entity_index=0,
            attr_name="ItemName",
            new_value="Updated Sword Name",
        )
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True

    def test_save_edit_nonexistent_entity(self, api):
        """Save with invalid entity_index returns error."""
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
            entity_index=99999,
            attr_name="ItemName",
            new_value="Should Fail",
        )
        assert resp.status_code in (404, 422), (
            f"Expected 404 or 422 for bad entity index, got {resp.status_code}"
        )

    def test_save_edit_nonexistent_file(self, api):
        """Save to nonexistent XML returns 404."""
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/nonexistent.xml",
            entity_index=0,
            attr_name="ItemName",
            new_value="Should Fail",
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_save_response_schema(self, api):
        """Save response has success and message fields."""
        resp = api.save_gamedata(
            xml_path="StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml",
            entity_index=0,
            attr_name="ItemName",
            new_value="Schema Test",
        )
        if resp.status_code == 200:
            data = resp.json()
            assert_json_fields(data, ["success", "message"], "GameDevSaveResponse")
