"""Tests for GameDataBrowseService.

Phase 18: Game Dev Grid -- folder scanning and column detection.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from lxml import etree


class TestScanFolder:
    """Tests for scan_folder method."""

    def _create_xml(self, path: Path, tag: str, count: int, attrs: dict | None = None) -> None:
        """Helper to create a minimal XML file with N entities."""
        root = etree.Element("Root")
        for i in range(count):
            child = etree.SubElement(root, tag)
            child.set("Key", f"key_{i}")
            if attrs:
                for k, v in attrs.items():
                    child.set(k, v)
        tree = etree.ElementTree(root)
        tree.write(str(path), encoding="UTF-8", xml_declaration=True)

    def test_scan_folder(self, tmp_path: Path) -> None:
        """Given a directory with XML files, returns tree with folder/file info."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        # Create structure: root/items.xml (3 entities), root/chars.xml (2 entities)
        self._create_xml(tmp_path / "items.xml", "ItemInfo", 3)
        self._create_xml(tmp_path / "chars.xml", "CharacterInfo", 2)

        svc = GameDataBrowseService(base_dir=tmp_path)
        result = svc.scan_folder(str(tmp_path))

        assert result.name == tmp_path.name
        assert len(result.files) == 2
        file_names = {f.name for f in result.files}
        assert "items.xml" in file_names
        assert "chars.xml" in file_names

        items_file = next(f for f in result.files if f.name == "items.xml")
        assert items_file.entity_count == 3

    def test_scan_folder_empty(self, tmp_path: Path) -> None:
        """Given an empty directory, returns tree with empty lists."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        svc = GameDataBrowseService(base_dir=tmp_path)
        result = svc.scan_folder(str(tmp_path))

        assert result.folders == []
        assert result.files == []

    def test_scan_folder_nested(self, tmp_path: Path) -> None:
        """Given nested directories, returns recursive tree."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        subdir = tmp_path / "data" / "items"
        subdir.mkdir(parents=True)
        self._create_xml(subdir / "weapons.xml", "ItemInfo", 5)

        svc = GameDataBrowseService(base_dir=tmp_path)
        result = svc.scan_folder(str(tmp_path))

        assert len(result.folders) == 1
        assert result.folders[0].name == "data"
        assert len(result.folders[0].folders) == 1
        assert result.folders[0].folders[0].name == "items"
        assert len(result.folders[0].folders[0].files) == 1
        assert result.folders[0].folders[0].files[0].entity_count == 5

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Given a nonexistent path, raises ValueError."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        svc = GameDataBrowseService(base_dir=tmp_path)

        with pytest.raises(ValueError, match="does not exist|not found"):
            svc.scan_folder("/nonexistent/path/that/does/not/exist")


class TestDetectColumns:
    """Tests for detect_columns method."""

    def test_detect_columns(self, tmp_path: Path) -> None:
        """Given an XML file with ItemInfo entities, returns column hints."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        xml_path = tmp_path / "items.xml"
        root = etree.Element("Root")
        item = etree.SubElement(root, "ItemInfo")
        item.set("Key", "sword_01")
        item.set("ItemName", "Iron Sword")
        item.set("ItemDesc", "A basic sword")
        item.set("Grade", "1")
        etree.ElementTree(root).write(str(xml_path), encoding="UTF-8", xml_declaration=True)

        svc = GameDataBrowseService(base_dir=tmp_path)
        result = svc.detect_columns(str(xml_path))

        col_keys = {c.key for c in result.columns}
        assert "Key" in col_keys
        assert "ItemName" in col_keys
        assert "ItemDesc" in col_keys
        assert "Grade" in col_keys

        # ItemName and ItemDesc should be editable for ItemInfo
        editable_cols = {c.key for c in result.columns if c.editable}
        assert "ItemName" in editable_cols
        assert "ItemDesc" in editable_cols
        assert "Key" not in editable_cols

    def test_detect_editable_attrs(self, tmp_path: Path) -> None:
        """Given entity tag name, editable_attrs returns correct list."""
        from server.tools.ldm.services.gamedata_browse_service import GameDataBrowseService

        xml_path = tmp_path / "skills.xml"
        root = etree.Element("Root")
        skill = etree.SubElement(root, "SkillInfo")
        skill.set("StrKey", "skill_01")
        skill.set("SkillName", "Fireball")
        skill.set("SkillDesc", "Casts fire")
        etree.ElementTree(root).write(str(xml_path), encoding="UTF-8", xml_declaration=True)

        svc = GameDataBrowseService(base_dir=tmp_path)
        result = svc.detect_columns(str(xml_path))

        assert "SkillName" in result.editable_attrs
        assert "SkillDesc" in result.editable_attrs
