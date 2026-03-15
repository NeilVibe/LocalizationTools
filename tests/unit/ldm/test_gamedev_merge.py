"""
Tests for GameDevMergeService -- parallel tree walk diff + in-place apply.

Covers all 5 GMERGE requirements:
- GMERGE-01: Diff detection (unchanged, modified, added, removed)
- GMERGE-02: Node-level operations (apply add/remove/modify)
- GMERGE-03: Attribute-level merge (single attr change, attr add, attr remove)
- GMERGE-04: Depth handling (child, sub-child, beyond max_depth)
- GMERGE-05: Position/document order preservation
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from lxml import etree

from server.tools.ldm.file_handlers.xml_handler import parse_gamedev_nodes
from server.tools.ldm.services.gamedev_merge import (
    AttributeChange,
    ChangeType,
    GameDevMergeResult,
    GameDevMergeService,
    NodeChange,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "xml"
SAMPLE_XML = FIXTURES_DIR / "gamedev_sample.xml"


def _load_xml(path: Path) -> etree._Element:
    """Parse XML file and return root element."""
    return etree.parse(str(path)).getroot()


def _rows_from_xml(path: Path, max_depth: int = 3) -> list[dict]:
    """Parse XML file into Game Dev rows."""
    root = _load_xml(path)
    return parse_gamedev_nodes(root, max_depth=max_depth)


def _modify_row_attr(rows: list[dict], row_index: int, attr_name: str, new_value: str) -> list[dict]:
    """Return a copy of rows with one attribute changed."""
    rows = copy.deepcopy(rows)
    rows[row_index]["extra_data"]["attributes"][attr_name] = new_value
    return rows


def _add_row(rows: list[dict], position: int, tag: str, attributes: dict, depth: int) -> list[dict]:
    """Return a copy of rows with a new row inserted at position."""
    rows = copy.deepcopy(rows)
    new_row = {
        "row_num": position,
        "string_id": None,
        "source": tag,
        "target": ", ".join(f"{k}={v}" for k, v in list(attributes.items())[:3]),
        "status": "pending",
        "extra_data": {
            "node_name": tag,
            "attributes": attributes,
            "values": None,
            "children_count": 0,
            "depth": depth,
        },
    }
    rows.insert(position - 1, new_row)
    # Re-number rows
    for i, r in enumerate(rows):
        r["row_num"] = i + 1
    return rows


def _remove_row(rows: list[dict], row_index: int) -> list[dict]:
    """Return a copy of rows with one row removed."""
    rows = copy.deepcopy(rows)
    del rows[row_index]
    # Re-number rows
    for i, r in enumerate(rows):
        r["row_num"] = i + 1
    return rows


# ============================================================
# GMERGE-01: Diff Detection
# ============================================================

class TestDiffDetection:
    """Tests for diff_trees detecting changes between original XML and current rows."""

    def setup_method(self):
        self.service = GameDevMergeService()
        self.original_root = _load_xml(SAMPLE_XML)
        self.original_rows = _rows_from_xml(SAMPLE_XML)

    def test_unchanged_returns_no_changes(self):
        """When rows match original, diff returns 0 changes."""
        changes = self.service.diff_trees(self.original_root, self.original_rows)
        non_unchanged = [c for c in changes if c.change_type != ChangeType.UNCHANGED]
        assert len(non_unchanged) == 0

    def test_modified_attribute_detected(self):
        """When one attribute changes, diff returns exactly 1 MODIFIED change."""
        # Change Iron Sword Value from 150 to 200
        rows = _modify_row_attr(self.original_rows, 0, "Value", "200")
        changes = self.service.diff_trees(self.original_root, rows)
        modified = [c for c in changes if c.change_type == ChangeType.MODIFIED]
        assert len(modified) == 1
        assert modified[0].tag == "Item"
        # Check attribute change details
        attr_changes = modified[0].attribute_changes
        value_change = [a for a in attr_changes if a.name == "Value"]
        assert len(value_change) == 1
        assert value_change[0].old_value == "150"
        assert value_change[0].new_value == "200"

    def test_added_node_detected(self):
        """When a new row is added, diff returns 1 ADDED change."""
        rows = _add_row(
            self.original_rows,
            position=5,
            tag="Item",
            attributes={"Name": "Fire Staff", "Type": "Weapon", "Value": "350"},
            depth=1,
        )
        changes = self.service.diff_trees(self.original_root, rows)
        added = [c for c in changes if c.change_type == ChangeType.ADDED]
        assert len(added) == 1
        assert added[0].tag == "Item"

    def test_removed_node_detected(self):
        """When a row is removed, diff returns 1 REMOVED change."""
        # Remove Healing Potion (Item at index 4 = row for Healing Potion's Item element)
        # Find the Healing Potion Item row
        hp_index = None
        for i, r in enumerate(self.original_rows):
            if r["extra_data"]["node_name"] == "Item" and r["extra_data"]["attributes"].get("Name") == "Healing Potion":
                hp_index = i
                break
        assert hp_index is not None, "Healing Potion not found"
        # Also remove its child Stats row
        rows = copy.deepcopy(self.original_rows)
        # Remove Healing Potion and its Stats child (next row)
        rows = _remove_row(rows, hp_index + 1)  # Stats child first (after Healing Potion)
        rows = _remove_row(rows, hp_index)  # Then Healing Potion itself
        changes = self.service.diff_trees(self.original_root, rows)
        removed = [c for c in changes if c.change_type == ChangeType.REMOVED]
        assert len(removed) >= 1  # At least the Item node is detected as removed

    def test_result_counts(self):
        """GameDevMergeResult counts changed, added, removed correctly."""
        rows = _modify_row_attr(self.original_rows, 0, "Value", "200")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        assert isinstance(result, GameDevMergeResult)
        assert result.changed_nodes >= 1
        assert result.total_nodes > 0


# ============================================================
# GMERGE-02: Node-Level Operations
# ============================================================

class TestNodeOperations:
    """Tests for apply_changes on the lxml tree."""

    def setup_method(self):
        self.service = GameDevMergeService()
        self.original_root = _load_xml(SAMPLE_XML)
        self.original_rows = _rows_from_xml(SAMPLE_XML)

    def test_apply_modified_updates_attributes(self):
        """MODIFIED change updates the correct element's attributes."""
        rows = _modify_row_attr(self.original_rows, 0, "Value", "999")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        # Parse output and check
        output_root = etree.fromstring(result.output_xml)
        first_item = output_root[0]
        assert first_item.get("Value") == "999"

    def test_apply_added_inserts_element(self):
        """ADDED change inserts a new element."""
        rows = _add_row(
            self.original_rows,
            position=5,
            tag="Item",
            attributes={"Name": "Fire Staff", "Type": "Weapon", "Value": "350"},
            depth=1,
        )
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        # Should have one more Item than original
        original_items = self.original_root.findall("Item")
        output_items = output_root.findall("Item")
        assert len(output_items) == len(original_items) + 1

    def test_apply_removed_deletes_element(self):
        """REMOVED change removes the element from the tree."""
        # Remove Healing Potion and its child
        hp_index = None
        for i, r in enumerate(self.original_rows):
            if r["extra_data"]["node_name"] == "Item" and r["extra_data"]["attributes"].get("Name") == "Healing Potion":
                hp_index = i
                break
        assert hp_index is not None
        rows = _remove_row(copy.deepcopy(self.original_rows), hp_index + 1)
        rows = _remove_row(rows, hp_index)
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        # Healing Potion should not exist
        names = [item.get("Name") for item in output_root.findall("Item")]
        assert "Healing Potion" not in names


# ============================================================
# GMERGE-03: Attribute-Level Merge
# ============================================================

class TestAttributeMerge:
    """Tests for attribute-level precision in merge."""

    def setup_method(self):
        self.service = GameDevMergeService()

    def test_single_attribute_change_preserves_others(self):
        """When one attribute changes, others stay the same."""
        rows = _rows_from_xml(SAMPLE_XML)
        rows = _modify_row_attr(rows, 0, "Value", "999")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        first_item = output_root[0]
        assert first_item.get("Value") == "999"
        assert first_item.get("Name") == "Iron Sword"
        assert first_item.get("Type") == "Weapon"
        assert first_item.get("Grade") == "Common"

    def test_new_attribute_added(self):
        """When a new attribute is added, it appears without affecting existing ones."""
        rows = _rows_from_xml(SAMPLE_XML)
        rows = copy.deepcopy(rows)
        # Add a new attribute to first Item
        rows[0]["extra_data"]["attributes"]["NewAttr"] = "test_value"
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        first_item = output_root[0]
        assert first_item.get("NewAttr") == "test_value"
        assert first_item.get("Name") == "Iron Sword"

    def test_attribute_removed(self):
        """When an attribute is removed, it disappears without affecting siblings."""
        rows = _rows_from_xml(SAMPLE_XML)
        rows = copy.deepcopy(rows)
        # Remove Grade from first Item
        del rows[0]["extra_data"]["attributes"]["Grade"]
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        first_item = output_root[0]
        assert first_item.get("Grade") is None
        assert first_item.get("Name") == "Iron Sword"
        assert first_item.get("Value") == "150"


# ============================================================
# GMERGE-04: Depth Handling
# ============================================================

class TestDepthHandling:
    """Tests for correct handling of nested elements at different depths."""

    def setup_method(self):
        self.service = GameDevMergeService()

    def test_child_element_change_detected(self):
        """Changes in child elements (depth 2) are detected and applied."""
        rows = _rows_from_xml(SAMPLE_XML)
        # Find Stats element under Iron Sword (depth 2)
        stats_idx = None
        for i, r in enumerate(rows):
            if r["extra_data"]["node_name"] == "Stats" and "Attack" in r["extra_data"]["attributes"]:
                stats_idx = i
                break
        assert stats_idx is not None
        rows = _modify_row_attr(rows, stats_idx, "Attack", "50")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        stats = output_root[0].find("Stats")
        assert stats.get("Attack") == "50"

    def test_sub_child_element_change_detected(self):
        """Changes in sub-child elements (depth 3) are detected and applied."""
        rows = _rows_from_xml(SAMPLE_XML)
        # Find Modifier under Effect under Iron Sword (depth 3)
        modifier_idx = None
        for i, r in enumerate(rows):
            if r["extra_data"]["node_name"] == "Modifier" and r["extra_data"]["attributes"].get("Stat") == "Attack":
                modifier_idx = i
                break
        assert modifier_idx is not None
        rows = _modify_row_attr(rows, modifier_idx, "Value", "+15")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        modifier = output_root[0].find(".//Modifier[@Stat='Attack']")
        assert modifier is not None
        assert modifier.get("Value") == "+15"

    def test_beyond_max_depth_preserved(self):
        """Nodes beyond max_depth in original tree are preserved unchanged."""
        # Parse with max_depth=1 (only top-level Items)
        rows = _rows_from_xml(SAMPLE_XML, max_depth=1)
        original_root = _load_xml(SAMPLE_XML)
        # All rows should be Items (depth 1 only)
        for r in rows:
            assert r["extra_data"]["depth"] == 1
        # Merge should preserve sub-elements unchanged
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows, max_depth=1)
        output_root = etree.fromstring(result.output_xml)
        # Stats/Effect/Modifier should still exist
        stats = output_root[0].find("Stats")
        assert stats is not None
        assert stats.get("Attack") == "25"


# ============================================================
# GMERGE-05: Position/Document Order Preservation
# ============================================================

class TestDocumentOrder:
    """Tests for output XML maintaining original document order."""

    def setup_method(self):
        self.service = GameDevMergeService()

    def test_modified_element_stays_in_place(self):
        """Modified elements maintain their position in document order."""
        rows = _rows_from_xml(SAMPLE_XML)
        rows = _modify_row_attr(rows, 0, "Value", "999")
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        items = output_root.findall("Item")
        # Iron Sword still first
        assert items[0].get("Name") == "Iron Sword"
        assert items[0].get("Value") == "999"
        # Order preserved for rest
        assert items[1].get("Name") == "Healing Potion"
        assert items[2].get("Name") == "Dragon Shield"

    def test_added_element_at_correct_position(self):
        """Added elements are inserted at their intended position."""
        rows = _rows_from_xml(SAMPLE_XML)
        # Add a new top-level Item after Healing Potion (position after Healing Potion subtree)
        # Find where Dragon Shield starts
        dragon_idx = None
        for i, r in enumerate(rows):
            if r["extra_data"]["node_name"] == "Item" and r["extra_data"]["attributes"].get("Name") == "Dragon Shield":
                dragon_idx = i
                break
        assert dragon_idx is not None
        rows = _add_row(
            rows,
            position=dragon_idx + 1,  # Insert before Dragon Shield
            tag="Item",
            attributes={"Name": "New Weapon", "Type": "Weapon", "Value": "100"},
            depth=1,
        )
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        items = output_root.findall("Item")
        names = [i.get("Name") for i in items]
        # New Weapon should be between Healing Potion and Dragon Shield
        assert "New Weapon" in names
        new_idx = names.index("New Weapon")
        dragon_new_idx = names.index("Dragon Shield")
        assert new_idx < dragon_new_idx

    def test_removed_element_no_position_shift(self):
        """Removing elements does not incorrectly shift remaining positions."""
        rows = _rows_from_xml(SAMPLE_XML)
        # Remove Healing Potion and its Stats child
        hp_index = None
        for i, r in enumerate(rows):
            if r["extra_data"]["node_name"] == "Item" and r["extra_data"]["attributes"].get("Name") == "Healing Potion":
                hp_index = i
                break
        assert hp_index is not None
        rows = _remove_row(copy.deepcopy(rows), hp_index + 1)  # Stats child
        rows = _remove_row(rows, hp_index)  # Healing Potion
        result = self.service.merge(SAMPLE_XML.read_bytes(), rows)
        output_root = etree.fromstring(result.output_xml)
        items = output_root.findall("Item")
        names = [i.get("Name") for i in items]
        assert names == ["Iron Sword", "Dragon Shield", "Magic Ring", "Shadow Cloak"]
