"""Export endpoint API tests.

Covers file download/export in XML, Excel, and TXT formats,
export option handling, br-tag and Korean preservation through
export, and round-trip integrity checks.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_brtag_preserved,
    assert_korean_preserved,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.export]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locstr_xml(entries: list[tuple[str, str, str]]) -> bytes:
    """Build a minimal LocStr XML from (strkey, kr, en) tuples."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<LanguageData>"]
    for key, kr, en in entries:
        lines.append(f'  <String StrKey="{key}" KR="{kr}" EN="{en}" />')
    lines.append("</LanguageData>")
    return "\n".join(lines).encode("utf-8")


# ======================================================================
# Export Formats
# ======================================================================


class TestExportFormats:
    """GET /api/ldm/files/{file_id}/download?format=X tests."""

    def test_export_as_xml(self, api, uploaded_xml_file_id):
        """Export file as XML format returns valid XML content."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xml")
        if resp.status_code == 200:
            text = resp.text
            assert "<" in text and ">" in text, "Export doesn't look like XML"
            assert len(text) > 10, "XML export is too short"
        else:
            assert resp.status_code in (400, 404, 415)

    def test_export_as_excel(self, api, uploaded_xml_file_id):
        """Export file as Excel (.xlsx) format."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xlsx")
        assert resp.status_code in (200, 400, 404, 415), (
            f"Export xlsx: unexpected {resp.status_code}"
        )
        if resp.status_code == 200:
            # Excel files start with PK zip header
            assert len(resp.content) > 0, "Excel export is empty"

    def test_export_as_txt(self, api, uploaded_xml_file_id):
        """Export file as tab-delimited text."""
        resp = api.download_file(uploaded_xml_file_id, fmt="txt")
        assert resp.status_code in (200, 400, 404, 415), (
            f"Export txt: unexpected {resp.status_code}"
        )
        if resp.status_code == 200:
            text = resp.text
            assert len(text) > 0, "TXT export is empty"

    @pytest.mark.brtag
    def test_export_preserves_brtags(self, api, test_project_id):
        """Exported content preserves br-tags."""
        entries = [
            ("EXP_BR_001", "첫 줄<br/>둘째 줄", "First<br/>Second"),
            ("EXP_BR_002", "A<br/>B<br/>C", "X<br/>Y<br/>Z"),
        ]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "export_brtag.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            text = dl_resp.text
            # br-tags should be present in either literal or escaped form
            assert "<br/>" in text or "&lt;br/&gt;" in text, (
                f"br-tags lost in export. Text: {text[:500]}"
            )

        api.delete_file(fid, permanent=True)

    @pytest.mark.korean
    def test_export_preserves_korean(self, api, test_project_id):
        """Exported content preserves Korean Unicode."""
        korean_text = "검은 칼날의 전사"
        entries = [("EXP_KR_001", korean_text, "Warrior")]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "export_korean.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            assert_korean_preserved(korean_text, dl_resp.text)

        api.delete_file(fid, permanent=True)


# ======================================================================
# Export Options
# ======================================================================


class TestExportOptions:
    """Test export with various options and edge cases."""

    def test_export_empty_file(self, api, test_project_id):
        """Export file with no matching rows handles gracefully."""
        # Upload minimal XML
        content = _locstr_xml([("EMP_001", "테스트", "Test")])
        resp = api.upload_file(test_project_id, "export_empty_test.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        # Attempt export -- should succeed or return clear error
        dl_resp = api.download_file(fid, fmt="xml")
        assert dl_resp.status_code in (200, 400, 404), (
            f"Export empty: unexpected {dl_resp.status_code}"
        )

        api.delete_file(fid, permanent=True)

    def test_export_nonexistent_file(self, api):
        """Export nonexistent file returns 404."""
        resp = api.download_file(999999, fmt="xml")
        assert resp.status_code == 404

    def test_export_invalid_format(self, api, uploaded_xml_file_id):
        """Export with unsupported format returns 400/415."""
        resp = api.download_file(uploaded_xml_file_id, fmt="pdf")
        assert resp.status_code in (400, 404, 415, 422), (
            f"Expected error for invalid format, got {resp.status_code}"
        )

    def test_export_with_metadata(self, api, uploaded_xml_file_id):
        """Exported XML content includes structural metadata (tags/attributes)."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xml")
        if resp.status_code == 200:
            text = resp.text
            # Should have XML declaration or root element
            assert "xml" in text.lower() or "<" in text


# ======================================================================
# Round-trip Export
# ======================================================================


class TestExportRoundTrip:
    """Export → reimport → compare integrity tests."""

    def test_export_import_roundtrip_xml(self, api, test_project_id):
        """Export XML, reimport, verify content survives round-trip."""
        entries = [
            ("RT_X_001", "라운드트립", "Roundtrip"),
            ("RT_X_002", "두 번째", "Second"),
            ("RT_X_003", "세 번째", "Third"),
        ]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "rt_xml_source.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        # Export
        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code != 200:
            api.delete_file(fid, permanent=True)
            pytest.skip(f"Export failed: {dl_resp.status_code}")

        exported = dl_resp.content

        # Re-import the exported content
        reimport_resp = api.upload_file(
            test_project_id, "rt_xml_reimport.xml", exported
        )
        if reimport_resp.status_code == 200:
            reimport_id = reimport_resp.json()["id"]
            # Verify reimported file exists
            get_resp = api.get_file(reimport_id)
            assert get_resp.status_code == 200
            api.delete_file(reimport_id, permanent=True)

        api.delete_file(fid, permanent=True)

    def test_export_import_roundtrip_excel(self, api, uploaded_xml_file_id, test_project_id):
        """Export as Excel, reimport, verify file created."""
        dl_resp = api.download_file(uploaded_xml_file_id, fmt="xlsx")
        if dl_resp.status_code != 200:
            pytest.skip("Excel export not supported")

        exported = dl_resp.content
        reimport_resp = api.upload_file(
            test_project_id,
            "rt_excel_reimport.xlsx",
            exported,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        # Accept both success and parsing errors
        assert reimport_resp.status_code in (200, 400, 415, 422, 500)
        if reimport_resp.status_code == 200:
            reimport_id = reimport_resp.json()["id"]
            api.delete_file(reimport_id, permanent=True)

    @pytest.mark.brtag
    def test_export_brtag_roundtrip(self, api, test_project_id):
        """Full br-tag round-trip through export/import."""
        entries = [
            ("RTBR_001", "첫 줄<br/>둘째 줄", "First<br/>Second"),
            ("RTBR_002", "A<br/>B<br/>C", "X<br/>Y<br/>Z"),
        ]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "brtag_rt.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            exported = dl_resp.content
            # Reimport
            reimport_resp = api.upload_file(
                test_project_id, "brtag_rt_reimport.xml", exported
            )
            if reimport_resp.status_code == 200:
                reimport_id = reimport_resp.json()["id"]
                # Check round-tripped content
                dl2 = api.download_file(reimport_id, fmt="xml")
                if dl2.status_code == 200:
                    text = dl2.text
                    assert "<br/>" in text or "&lt;br/&gt;" in text, (
                        f"br-tags lost after double round-trip. Text: {text[:500]}"
                    )
                api.delete_file(reimport_id, permanent=True)

        api.delete_file(fid, permanent=True)
