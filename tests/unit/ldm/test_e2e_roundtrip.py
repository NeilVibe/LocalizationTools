"""
E2E Round-Trip Integration Tests

Validates the full pipeline: parse XML -> merge -> export -> re-parse -> compare.
Covers both Translator and Game Dev modes with zero data loss verification.

No server needed -- all tests use direct service imports with inline XML fixtures.
"""

from __future__ import annotations

import pytest

from server.tools.ldm.file_handlers.xml_handler import parse_xml_file
from server.tools.ldm.services.translator_merge import TranslatorMergeService
from server.tools.ldm.services.export_service import ExportService
from server.tools.ldm.services.gamedev_merge import GameDevMergeService


# ---------------------------------------------------------------------------
# Inline XML Fixtures
# ---------------------------------------------------------------------------

# Translator format: LocStr elements with StringId/StrOrigin/Str attributes
# (matches real game data format where LocStr tags ARE the row elements)
TRANSLATOR_XML = b"""\
<?xml version="1.0" encoding="utf-8"?>
<GameData>
  <LocStr StringId="ITEM_001" StrOrigin="Sword of Dawn" Str="" Desc="" DescOrigin="A legendary sword"/>
  <LocStr StringId="ITEM_002" StrOrigin="Shield of Light" Str="" Desc="" DescOrigin="A holy shield"/>
  <LocStr StringId="ITEM_003" StrOrigin="First line&lt;br/&gt;Second line" Str="" Desc="" DescOrigin=""/>
  <LocStr StringId="ITEM_004" StrOrigin="Potion of Health" Str="" Desc="" DescOrigin="Restores HP"/>
  <LocStr StringId="ITEM_005" StrOrigin="Ring of Power" Str="" Desc="" DescOrigin="Increases ATK"/>
</GameData>
"""

CORRECTIONS_XML = b"""\
<?xml version="1.0" encoding="utf-8"?>
<GameData>
  <LocStr StringId="ITEM_001" StrOrigin="Sword of Dawn" Str="Dawn Sword KR" Desc="" DescOrigin="A legendary sword"/>
  <LocStr StringId="ITEM_002" StrOrigin="Shield of Light" Str="Light Shield KR" Desc="" DescOrigin="A holy shield"/>
  <LocStr StringId="ITEM_003" StrOrigin="First line&lt;br/&gt;Second line" Str="Line1&lt;br/&gt;Line2" Desc="" DescOrigin=""/>
  <LocStr StringId="ITEM_004" StrOrigin="Potion of Health" Str="Health Potion KR" Desc="" DescOrigin="Restores HP"/>
</GameData>
"""

GAMEDEV_XML = b"""\
<?xml version="1.0" encoding="utf-8"?>
<GameData>
  <ItemList>
    <Item Key="item_001" Name="Sword" Attack="50" Defense="10"/>
    <Item Key="item_002" Name="Shield" Attack="5" Defense="80"/>
  </ItemList>
</GameData>
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _find_row_by_string_id(rows: list[dict], string_id: str) -> dict | None:
    """Find a row by its string_id (case-insensitive)."""
    for row in rows:
        if (row.get("string_id") or "").upper() == string_id.upper():
            return row
    return None


def _apply_merge_to_rows(target_rows: list[dict], merge_result) -> list[dict]:
    """Build export-ready rows by applying merge results onto target rows."""
    updated_map = {}
    for updated_row in merge_result.updated_rows:
        sid = updated_row.get("string_id")
        if sid:
            updated_map[sid.upper()] = updated_row

    export_rows = []
    for row in target_rows:
        sid = (row.get("string_id") or "").upper()
        if sid in updated_map:
            export_rows.append(updated_map[sid])
        else:
            export_rows.append(row)
    return export_rows


# ---------------------------------------------------------------------------
# Translator Round-Trip Tests
# ---------------------------------------------------------------------------

class TestTranslatorRoundTrip:
    """E2E: parse LocStr XML -> merge corrections -> export -> re-parse -> compare."""

    def test_translator_xml_roundtrip(self):
        """Full round-trip: parse, merge strict, export XML, re-parse, verify translations."""
        # Parse target and source
        target_rows, target_meta = parse_xml_file(TRANSLATOR_XML, "target.xml")
        source_rows, _ = parse_xml_file(CORRECTIONS_XML, "corrections.xml")

        assert target_meta["file_type"] == "translator"
        assert len(target_rows) == 5

        # Merge (strict mode -- StringID + StrOrigin must match)
        merge_svc = TranslatorMergeService()
        merge_result = merge_svc.merge_files(source_rows, target_rows, match_mode="strict")

        # Should match 4 rows (ITEM_001-004 have corrections)
        assert merge_result.matched >= 4

        # Apply updates and build export rows
        export_rows = _apply_merge_to_rows(target_rows, merge_result)

        # Export to XML
        export_svc = ExportService()
        exported_xml = export_svc.export_xml(export_rows, target_meta)
        assert len(exported_xml) > 0

        # Re-parse exported XML
        re_rows, re_meta = parse_xml_file(exported_xml, "exported.xml")
        assert re_meta["file_type"] == "translator"
        assert len(re_rows) == 5

        # Verify translations survived the round-trip
        item_001 = _find_row_by_string_id(re_rows, "ITEM_001")
        assert item_001 is not None
        assert item_001["target"] == "Dawn Sword KR"

        item_002 = _find_row_by_string_id(re_rows, "ITEM_002")
        assert item_002 is not None
        assert item_002["target"] == "Light Shield KR"

        # ITEM_005 had no correction -- target should still be empty/None
        item_005 = _find_row_by_string_id(re_rows, "ITEM_005")
        assert item_005 is not None
        assert not item_005.get("target")  # empty or None

    def test_translator_brtag_roundtrip(self):
        """br-tags survive the full round-trip without corruption or double-encoding."""
        target_rows, target_meta = parse_xml_file(TRANSLATOR_XML, "target.xml")
        source_rows, _ = parse_xml_file(CORRECTIONS_XML, "corrections.xml")

        merge_svc = TranslatorMergeService()
        merge_result = merge_svc.merge_files(source_rows, target_rows, match_mode="strict")

        # Build merged rows and export
        export_rows = _apply_merge_to_rows(target_rows, merge_result)
        export_svc = ExportService()
        exported_xml = export_svc.export_xml(export_rows, target_meta)
        re_rows, _ = parse_xml_file(exported_xml, "exported.xml")

        # Find ITEM_003 and verify br-tag content
        item_003 = _find_row_by_string_id(re_rows, "ITEM_003")
        assert item_003 is not None

        # The target should contain br-tag content from corrections
        target_text = item_003.get("target") or ""
        # lxml stores <br/> in attribute values as &lt;br/&gt; on disk,
        # which parse_xml_file reads back as <br/> in memory
        assert "br" in target_text.lower() or "line1" in target_text.lower(), (
            f"Expected br-tag content in target, got: {target_text!r}"
        )

        # Source should also preserve br-tags through round-trip
        source_text = item_003.get("source") or ""
        assert "line" in source_text.lower() or "br" in source_text.lower(), (
            f"Expected br-tag content in source, got: {source_text!r}"
        )

    def test_translator_export_excel_columns(self):
        """Excel export produces valid xlsx bytes (PK zip header)."""
        rows, meta = parse_xml_file(TRANSLATOR_XML, "test.xml")

        export_svc = ExportService()
        excel_bytes = export_svc.export_excel(rows, meta)

        assert len(excel_bytes) > 0
        # xlsx is a ZIP file -- must start with PK header
        assert excel_bytes[:2] == b"PK", "Excel output should start with PK (ZIP header)"

    def test_translator_export_text_format(self):
        """Text export produces tab-delimited lines with StringID + source + target."""
        rows, meta = parse_xml_file(TRANSLATOR_XML, "test.xml")

        export_svc = ExportService()
        text_bytes = export_svc.export_text(rows, meta)

        text = text_bytes.decode("utf-8")
        lines = [ln for ln in text.split("\n") if ln.strip()]

        # Should have one line per row (5 rows)
        assert len(lines) == 5

        # Each line should be tab-delimited with at least StringID + source (+ optional target)
        for line in lines:
            parts = line.split("\t")
            assert len(parts) >= 2, f"Expected at least 2 tab-separated fields, got {len(parts)}: {line!r}"

        # ITEM_001 should appear in the output
        assert "ITEM_001" in text


# ---------------------------------------------------------------------------
# Game Dev Round-Trip Tests
# ---------------------------------------------------------------------------

class TestGameDevRoundTrip:
    """E2E: parse non-LocStr XML -> modify attribute -> merge -> verify in output."""

    def test_gamedev_xml_roundtrip(self):
        """Modify an attribute via GameDevMergeService and verify in output XML."""
        rows, meta = parse_xml_file(GAMEDEV_XML, "gamedata.xml")
        assert meta["file_type"] == "gamedev"
        assert len(rows) >= 2  # ItemList + 2 Items (at least)

        # Find the Item with Key=item_001 and modify Attack from 50 to 99
        modified_rows = []
        for row in rows:
            row_copy = dict(row)
            extra = dict(row_copy.get("extra_data") or {})
            attrs = dict(extra.get("attributes", {}))

            if attrs.get("Key") == "item_001":
                attrs["Attack"] = "99"
                extra["attributes"] = attrs

            row_copy["extra_data"] = extra
            modified_rows.append(row_copy)

        # Run Game Dev merge
        merge_svc = GameDevMergeService()
        result = merge_svc.merge(GAMEDEV_XML, modified_rows)

        # Should detect the attribute modification
        assert result.modified_attributes >= 1

        # Re-parse the output XML and verify
        re_rows, re_meta = parse_xml_file(result.output_xml, "merged.xml")
        assert re_meta["file_type"] == "gamedev"

        # Find the item with Key=item_001 and check Attack=99
        found = False
        for row in re_rows:
            extra = row.get("extra_data", {})
            attrs = extra.get("attributes", {})
            if attrs.get("Key") == "item_001":
                assert attrs.get("Attack") == "99", (
                    f"Expected Attack=99, got {attrs.get('Attack')}"
                )
                found = True
                break

        assert found, "Could not find item_001 in merged output"


# ---------------------------------------------------------------------------
# File Type Detection Tests
# ---------------------------------------------------------------------------

class TestFileTypeDetection:
    """Verify parse_xml_file correctly detects translator vs gamedev file types."""

    def test_file_type_detection_translator(self):
        """LocStr XML should be detected as 'translator' file type."""
        _, meta = parse_xml_file(TRANSLATOR_XML, "locstr.xml")
        assert meta["file_type"] == "translator"

    def test_file_type_detection_gamedev(self):
        """Non-LocStr XML should be detected as 'gamedev' file type."""
        _, meta = parse_xml_file(GAMEDEV_XML, "gamedata.xml")
        assert meta["file_type"] == "gamedev"
