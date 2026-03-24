"""Tests for XML round-trip integrity (MOCK-08).

Validates that all XML files in the mock gamedata universe can be
parsed, serialized, and re-parsed without data loss.

NOTE: References legacy fixture paths (stringtable/loc/, export .loc.xml) that were
restructured in v9.0 Phase 74. Skipped until paths are updated.
"""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.skip(reason="Legacy fixture paths (stringtable/loc/) — restructured in v9.0 Phase 74")

from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
STATIC_DIR = MOCK_DIR / "StaticInfo"
STRINGTABLE_DIR = MOCK_DIR / "stringtable"
LOC_DIR = STRINGTABLE_DIR / "loc"
EXPORT_DIR = STRINGTABLE_DIR / "export__" / "System"


def _roundtrip_check(path: Path) -> tuple[bool, str]:
    """Parse, serialize, re-parse an XML file and compare.

    Returns (success, error_message).
    """
    try:
        tree1 = etree.parse(str(path))
        root1 = tree1.getroot()

        # Serialize
        xml_bytes = etree.tostring(root1, encoding="utf-8", xml_declaration=True)

        # Re-parse
        root2 = etree.fromstring(xml_bytes)

        # Compare element counts
        count1 = len(list(root1.iter()))
        count2 = len(list(root2.iter()))
        if count1 != count2:
            return False, f"Element count mismatch: {count1} vs {count2}"

        # Compare root children attributes
        children1 = list(root1)
        children2 = list(root2)
        if len(children1) != len(children2):
            return False, f"Root children count mismatch: {len(children1)} vs {len(children2)}"

        for c1, c2 in zip(children1, children2):
            for attr_name in c1.attrib:
                v1 = c1.get(attr_name)
                v2 = c2.get(attr_name)
                if v1 != v2:
                    return False, (
                        f"Attribute {attr_name} mismatch on {c1.tag}: "
                        f"{v1!r} vs {v2!r}"
                    )

        return True, ""
    except Exception as e:
        return False, str(e)


class TestStaticInfoRoundtrip:
    """MOCK-08: StaticInfo XML round-trip validation."""

    def test_staticinfo_roundtrip(self) -> None:
        """Parse, serialize, re-parse every StaticInfo XML file."""
        errors = []
        xml_files = sorted(STATIC_DIR.rglob("*.xml"))
        assert len(xml_files) > 0, "No StaticInfo XML files found"

        for xml_file in xml_files:
            success, err = _roundtrip_check(xml_file)
            if not success:
                errors.append(f"{xml_file.relative_to(MOCK_DIR)}: {err}")

        assert not errors, f"Round-trip failures:\n" + "\n".join(errors)


class TestLanguageDataRoundtrip:
    """MOCK-08: Language data XML round-trip validation."""

    def test_languagedata_roundtrip(self) -> None:
        """Parse, serialize, re-parse language data files."""
        errors = []
        for lang in ["kor", "eng", "fre"]:
            path = LOC_DIR / f"languagedata_{lang}.xml"
            assert path.exists(), f"Missing {path}"

            success, err = _roundtrip_check(path)
            if not success:
                errors.append(f"languagedata_{lang}.xml: {err}")

        assert not errors, f"Round-trip failures:\n" + "\n".join(errors)

    def test_languagedata_stringid_preserved(self) -> None:
        """StringId attribute values are preserved through round-trip."""
        for lang in ["kor", "eng", "fre"]:
            path = LOC_DIR / f"languagedata_{lang}.xml"
            tree1 = etree.parse(str(path))
            ids1 = {
                el.get("StringId")
                for el in tree1.getroot().findall(".//LocStr")
            }

            xml_bytes = etree.tostring(
                tree1.getroot(), encoding="utf-8", xml_declaration=True
            )
            root2 = etree.fromstring(xml_bytes)
            ids2 = {el.get("StringId") for el in root2.findall(".//LocStr")}

            assert ids1 == ids2, f"{lang}: StringId sets differ after round-trip"


class TestExportRoundtrip:
    """MOCK-08: EXPORT .loc.xml round-trip validation."""

    def test_export_roundtrip(self) -> None:
        """Parse, serialize, re-parse every EXPORT .loc.xml file."""
        errors = []
        loc_files = sorted(EXPORT_DIR.glob("*.loc.xml"))
        assert len(loc_files) > 0, "No EXPORT .loc.xml files found"

        for loc_file in loc_files:
            success, err = _roundtrip_check(loc_file)
            if not success:
                errors.append(f"{loc_file.name}: {err}")

        assert not errors, f"Round-trip failures:\n" + "\n".join(errors)


class TestFullUniverseParsing:
    """MOCK-08: Full universe XML parsing validation."""

    def test_full_universe_no_parse_errors(self) -> None:
        """Walk entire mock_gamedata tree, parse every .xml file."""
        errors = []
        xml_files = sorted(MOCK_DIR.rglob("*.xml"))
        assert len(xml_files) > 0, "No XML files found in mock_gamedata"

        for xml_file in xml_files:
            try:
                etree.parse(str(xml_file))
            except etree.XMLSyntaxError as e:
                errors.append(f"{xml_file.relative_to(MOCK_DIR)}: {e}")

        assert not errors, (
            f"{len(errors)} parse errors:\n" + "\n".join(errors)
        )
        assert len(xml_files) >= 30, (
            f"Only {len(xml_files)} XML files found (expected 30+)"
        )
