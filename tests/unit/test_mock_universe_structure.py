"""Test mock universe folder structure and XML parseability (MOCK-01)."""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
STATIC_DIR = MOCK_DIR / "StaticInfo"


EXPECTED_DIRS = [
    "iteminfo",
    "characterinfo",
    "skillinfo",
    "knowledgeinfo",
    "factioninfo",
    "factioninfo/NodeWaypointInfo",
    "gimmickinfo/Background",
    "gimmickinfo/Item",
    "gimmickinfo/Puzzle",
]


class TestStaticInfoDirectories:
    """Verify all expected directories exist under StaticInfo/."""

    @pytest.mark.parametrize("subdir", EXPECTED_DIRS)
    def test_directory_exists(self, subdir: str) -> None:
        path = STATIC_DIR / subdir
        assert path.is_dir(), f"Missing directory: {path}"

    def test_all_9_directories_exist(self) -> None:
        """Summary check: all 9 expected subdirectories exist."""
        missing = [d for d in EXPECTED_DIRS if not (STATIC_DIR / d).is_dir()]
        assert not missing, f"Missing directories: {missing}"


class TestXmlFilesParseable:
    """Verify all XML files under StaticInfo/ are parseable."""

    def test_xml_files_parseable(self) -> None:
        xml_files = list(STATIC_DIR.rglob("*.xml"))
        assert len(xml_files) >= 10, f"Only {len(xml_files)} XML files (need 10+)"

        errors = []
        for xml_path in xml_files:
            try:
                etree.parse(str(xml_path))
            except etree.XMLSyntaxError as e:
                errors.append(f"{xml_path.name}: {e}")

        assert not errors, f"Parse errors:\n" + "\n".join(errors)


class TestFilenameConventions:
    """Verify all files match *.staticinfo.xml pattern."""

    def test_filename_conventions(self) -> None:
        xml_files = list(STATIC_DIR.rglob("*.xml"))
        non_matching = [
            f.name for f in xml_files if not f.name.endswith(".staticinfo.xml")
        ]
        assert not non_matching, f"Files not matching convention: {non_matching}"
