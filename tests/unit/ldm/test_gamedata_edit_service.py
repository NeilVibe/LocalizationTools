"""Tests for GameDataEditService.

Phase 18: Game Dev Grid -- XML attribute editing with br-tag preservation.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from lxml import etree


class TestUpdateAttribute:
    """Tests for update_entity_attribute method."""

    def _create_xml(self, path: Path, tag: str = "ItemInfo", count: int = 3) -> None:
        """Helper to create a minimal XML file."""
        root = etree.Element("Root")
        for i in range(count):
            child = etree.SubElement(root, tag)
            child.set("Key", f"key_{i}")
            child.set("ItemName", f"Item {i}")
            child.set("ItemDesc", f"Description {i}")
        tree = etree.ElementTree(root)
        tree.write(str(path), encoding="UTF-8", xml_declaration=True)

    def test_update_attribute(self, tmp_path: Path) -> None:
        """Given valid path/index/attr, updates the attribute and saves."""
        from server.tools.ldm.services.gamedata_edit_service import GameDataEditService

        xml_path = tmp_path / "items.xml"
        self._create_xml(xml_path)

        svc = GameDataEditService(base_dir=tmp_path)
        result = svc.update_entity_attribute(
            xml_path=str(xml_path),
            entity_index=1,
            attr_name="ItemName",
            new_value="Updated Sword",
        )

        assert result is True

        # Verify on disk
        tree = etree.parse(str(xml_path))
        entities = list(tree.getroot())
        assert entities[1].get("ItemName") == "Updated Sword"

    def test_br_tag_round_trip(self, tmp_path: Path) -> None:
        """Given text with <br/> tags, saves to XML, re-reads, and br-tags are preserved."""
        from server.tools.ldm.services.gamedata_edit_service import GameDataEditService

        xml_path = tmp_path / "items.xml"
        self._create_xml(xml_path)

        svc = GameDataEditService(base_dir=tmp_path)
        text_with_br = "First line<br/>Second line<br/>Third line"

        result = svc.update_entity_attribute(
            xml_path=str(xml_path),
            entity_index=0,
            attr_name="ItemDesc",
            new_value=text_with_br,
        )

        assert result is True

        # Re-read and verify br-tags survive round-trip
        tree = etree.parse(str(xml_path))
        entities = list(tree.getroot())
        value_on_disk = entities[0].get("ItemDesc")
        assert value_on_disk == text_with_br

    def test_update_attribute_invalid_index(self, tmp_path: Path) -> None:
        """Given out-of-range entity index, returns False without crashing."""
        from server.tools.ldm.services.gamedata_edit_service import GameDataEditService

        xml_path = tmp_path / "items.xml"
        self._create_xml(xml_path, count=2)

        svc = GameDataEditService(base_dir=tmp_path)
        result = svc.update_entity_attribute(
            xml_path=str(xml_path),
            entity_index=99,
            attr_name="ItemName",
            new_value="Nope",
        )

        assert result is False

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Given a path outside allowed base, raises ValueError."""
        from server.tools.ldm.services.gamedata_edit_service import GameDataEditService

        svc = GameDataEditService(base_dir=tmp_path)

        with pytest.raises(ValueError, match="outside.*allowed"):
            svc.update_entity_attribute(
                xml_path="/etc/passwd",
                entity_index=0,
                attr_name="Key",
                new_value="hack",
            )
