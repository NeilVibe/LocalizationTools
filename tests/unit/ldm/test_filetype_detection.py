"""
Tests for file type detection (Translator vs Game Dev) and Game Dev node parsing.

Covers:
- parse_xml_file returns file_type="translator" for LocStr XML files
- parse_xml_file returns file_type="gamedev" for non-LocStr XML files
- parse_gamedev_nodes produces rows with node_name, attributes, values, children_count
- Game Dev rows use source=node tag, target=formatted attributes summary
- Game Dev rows have status="pending" and string_id=None
- Comments and processing instructions are skipped
- Empty XML with no elements returns empty rows with file_type="gamedev"
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.ldm.file_handlers.xml_handler import parse_xml_file, parse_gamedev_nodes


FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "xml"


class TestFileTypeDetection:
    """Test that parse_xml_file sets file_type in metadata."""

    def test_locstr_file_detected_as_translator(self):
        """XML files with LocStr nodes are detected as 'translator' type."""
        content = (FIXTURES / "locstr_sample.xml").read_bytes()
        rows, metadata = parse_xml_file(content, "locstr_sample.xml")
        assert metadata["file_type"] == "translator"
        assert len(rows) > 0

    def test_gamedev_file_detected_as_gamedev(self):
        """XML files without LocStr nodes are detected as 'gamedev' type."""
        content = (FIXTURES / "gamedev_sample.xml").read_bytes()
        rows, metadata = parse_xml_file(content, "gamedev_sample.xml")
        assert metadata["file_type"] == "gamedev"
        assert len(rows) > 0

    def test_empty_xml_detected_as_gamedev(self):
        """Empty XML with no LocStr nodes and no other elements returns gamedev."""
        content = b'<?xml version="1.0" encoding="utf-8"?>\n<EmptyRoot />'
        rows, metadata = parse_xml_file(content, "empty.xml")
        assert metadata["file_type"] == "gamedev"
        assert len(rows) == 0


class TestGameDevNodeParsing:
    """Test parse_gamedev_nodes produces correct row structures."""

    @pytest.fixture
    def gamedev_root(self):
        """Parse gamedev_sample.xml and return root element."""
        from server.tools.ldm.services.xml_parsing import get_xml_parsing_engine
        engine = get_xml_parsing_engine()
        content = (FIXTURES / "gamedev_sample.xml").read_bytes()
        root, _ = engine.parse_bytes(content, "gamedev_sample.xml")
        return root

    def test_rows_have_extra_data_fields(self, gamedev_root):
        """Game Dev rows have node_name, attributes, values, children_count in extra_data."""
        rows = parse_gamedev_nodes(gamedev_root)
        assert len(rows) > 0
        for row in rows:
            extra = row["extra_data"]
            assert "node_name" in extra
            assert "attributes" in extra
            assert "values" in extra
            assert "children_count" in extra
            assert "depth" in extra

    def test_rows_use_source_as_tag_target_as_attributes(self, gamedev_root):
        """Game Dev rows reuse source/target fields (source=node tag, target=formatted attrs)."""
        rows = parse_gamedev_nodes(gamedev_root)
        # First Item element
        item_rows = [r for r in rows if r["source"] == "Item"]
        assert len(item_rows) >= 5  # 5 Item elements in fixture
        first_item = item_rows[0]
        assert first_item["source"] == "Item"
        # Target should contain formatted attributes
        assert "Name=Iron Sword" in first_item["target"]

    def test_rows_have_pending_status_and_no_string_id(self, gamedev_root):
        """Game Dev rows have status='pending' and string_id=None."""
        rows = parse_gamedev_nodes(gamedev_root)
        for row in rows:
            assert row["status"] == "pending"
            assert row["string_id"] is None

    def test_comments_and_pis_are_skipped(self, gamedev_root):
        """Comments and processing instructions are skipped in Game Dev parsing."""
        rows = parse_gamedev_nodes(gamedev_root)
        for row in rows:
            # No comment or PI nodes should appear
            assert not row["source"].startswith("<!--")
            assert not row["source"].startswith("<?")
            # node_name should be a valid element tag
            assert row["extra_data"]["node_name"] not in ("Comment", "ProcessingInstruction")

    def test_children_count_correct(self, gamedev_root):
        """children_count reflects actual direct children count."""
        rows = parse_gamedev_nodes(gamedev_root)
        # "Iron Sword" Item has 2 children: Stats and Effect
        iron_sword = [r for r in rows if r["extra_data"].get("attributes", {}).get("Name") == "Iron Sword"][0]
        assert iron_sword["extra_data"]["children_count"] == 2

    def test_depth_tracking(self, gamedev_root):
        """Depth indicates distance from root element."""
        rows = parse_gamedev_nodes(gamedev_root)
        # Item elements are at depth 1 (direct children of root)
        item_rows = [r for r in rows if r["source"] == "Item"]
        for item in item_rows:
            assert item["extra_data"]["depth"] == 1
        # Stats elements are at depth 2
        stats_rows = [r for r in rows if r["source"] == "Stats"]
        for stat in stats_rows:
            assert stat["extra_data"]["depth"] == 2

    def test_attributes_truncated_in_target(self, gamedev_root):
        """Target shows at most 3 attributes, truncated with '...'."""
        rows = parse_gamedev_nodes(gamedev_root)
        # "Iron Sword" has 4 attrs: Name, Type, Value, Grade
        iron_sword = [r for r in rows if r["extra_data"].get("attributes", {}).get("Name") == "Iron Sword"][0]
        # Should show first 3 and indicate truncation
        assert "..." in iron_sword["target"]

    def test_row_nums_are_sequential(self, gamedev_root):
        """Row numbers are sequential starting from 1."""
        rows = parse_gamedev_nodes(gamedev_root)
        for i, row in enumerate(rows, 1):
            assert row["row_num"] == i
