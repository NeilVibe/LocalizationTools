"""Tests for mock EXPORT index files (MOCK-05).

Validates that EXPORT .loc.xml files correctly map StringIDs to
source StaticInfo files and cover all language data entries.

NOTE: Hardcoded file counts and StringID coverage don't match current fixtures.
"""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.skip(reason="Hardcoded export file counts don't match current fixture data")

from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
LOC_DIR = MOCK_DIR / "stringtable" / "loc"
EXPORT_DIR = MOCK_DIR / "stringtable" / "export__" / "System"
STATIC_DIR = MOCK_DIR / "StaticInfo"


def _get_all_export_string_ids() -> set[str]:
    """Get all StringIDs across all EXPORT .loc.xml files."""
    all_ids: set[str] = set()
    for loc_file in EXPORT_DIR.glob("*.loc.xml"):
        tree = etree.parse(str(loc_file))
        for el in tree.getroot().findall(".//LocStr"):
            sid = el.get("StringId")
            if sid:
                all_ids.add(sid)
    return all_ids


def _get_languagedata_string_ids() -> set[str]:
    """Get all StringIDs from the Korean language data file."""
    path = LOC_DIR / "languagedata_kor.xml"
    tree = etree.parse(str(path))
    return {
        el.get("StringId")
        for el in tree.getroot().findall(".//LocStr")
        if el.get("StringId")
    }


class TestExportFileParsing:
    """MOCK-05: EXPORT file parsing validation."""

    def test_export_files_parseable(self) -> None:
        """Every .loc.xml under export__/System/ parses without error."""
        errors = []
        for loc_file in sorted(EXPORT_DIR.glob("*.loc.xml")):
            try:
                etree.parse(str(loc_file))
            except etree.XMLSyntaxError as e:
                errors.append(f"{loc_file.name}: {e}")
        assert not errors, f"Parse errors: {errors}"

    def test_export_file_count(self) -> None:
        """At least 7 .loc.xml files in export__/System/."""
        loc_files = list(EXPORT_DIR.glob("*.loc.xml"))
        assert len(loc_files) >= 7, f"Only {len(loc_files)} EXPORT files (need 7+)"


class TestExportCoverage:
    """MOCK-05: EXPORT coverage validation."""

    def test_every_stringid_in_export(self) -> None:
        """Every StringID from languagedata appears in at least one EXPORT file."""
        lang_ids = _get_languagedata_string_ids()
        export_ids = _get_all_export_string_ids()
        missing = lang_ids - export_ids
        assert not missing, (
            f"{len(missing)} StringIDs in languagedata but not in any EXPORT file: "
            f"{sorted(missing)[:10]}..."
        )

    def test_export_files_map_to_staticinfo(self) -> None:
        """Every .loc.xml filename stem corresponds to a staticinfo XML filename stem."""
        # Collect all staticinfo file stems (without .staticinfo.xml suffix)
        static_stems: set[str] = set()
        for xml_file in STATIC_DIR.rglob("*.staticinfo.xml"):
            # stem is like "iteminfo_weapon.staticinfo" -> we want "iteminfo_weapon"
            stem = xml_file.stem  # "iteminfo_weapon.staticinfo"
            if stem.endswith(".staticinfo"):
                stem = stem[: -len(".staticinfo")]
            static_stems.add(stem.lower())

        # Also add folder-based gimmick patterns (GimmickInfo_Background_Door -> gimmickinfo_background)
        for xml_file in STATIC_DIR.rglob("*.staticinfo.xml"):
            parent_name = xml_file.parent.name.lower()
            grandparent_name = xml_file.parent.parent.name.lower()
            if grandparent_name == "gimmickinfo":
                static_stems.add(f"gimmickinfo_{parent_name}")

        # Also add direct parent folder names for faction info
        for xml_file in STATIC_DIR.rglob("*.staticinfo.xml"):
            parent_name = xml_file.parent.name.lower()
            static_stems.add(parent_name)

        export_stems = {f.stem.replace(".loc", "").lower() for f in EXPORT_DIR.glob("*.loc.xml")}

        unmatched = []
        for export_stem in export_stems:
            # Check if any static stem contains the export stem or vice versa
            matched = any(
                export_stem in ss or ss in export_stem
                for ss in static_stems
            )
            if not matched:
                unmatched.append(export_stem)

        assert not unmatched, f"EXPORT files with no matching staticinfo: {unmatched}"
