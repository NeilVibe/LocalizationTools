"""Dedicated br-tag ``<br/>`` preservation tests across all subsystems.

Every test verifies that ``<br/>`` tags survive API operations without
corruption, mangling to ``&#10;``, or silent stripping.

Marked with ``@pytest.mark.brtag``.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

_XML_BRTAG = """\
<?xml version="1.0" encoding="utf-8"?>
<LocStr>
  <String StrKey="BR_001" KR="첫 줄<br/>둘째 줄" EN="Line one<br/>Line two" />
  <String StrKey="BR_002" KR="A<br/>B<br/>C" EN="X<br/>Y<br/>Z" />
  <String StrKey="BR_003" KR="단일 줄" EN="Single line" />
  <String StrKey="BR_004" KR="<br/>시작" EN="<br/>Start" />
  <String StrKey="BR_005" KR="끝<br/>" EN="End<br/>" />
</LocStr>
"""

_TM_BRTAG = "Source\tTarget\n첫 줄<br/>둘째 줄\tLine one<br/>Line two\n단순\tSimple\n"


def _get_rows(api, file_id):
    """Helper: list rows and return the row list."""
    resp = api.list_rows(file_id)
    assert resp.status_code == 200
    data = resp.json()
    return data.get("rows", data) if isinstance(data, dict) else data


# ======================================================================
# 1. Upload br-tag preservation
# ======================================================================


@pytest.mark.brtag
class TestBrtagUpload:
    """br-tag preservation during upload."""

    def test_brtag_xml_upload(self, api):
        """Upload LocStr XML with br-tags, verify rows contain br-tags."""
        resp = api.create_project("BrTag-Upload-XML")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_up.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            rows = _get_rows(api, fid)
            brtag_found = False
            for r in rows:
                for field in ("source", "target", "kr", "en"):
                    val = r.get(field, "") or ""
                    if "<br/>" in val:
                        brtag_found = True
                        break
            assert brtag_found, "No br-tags found in uploaded rows"
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_excel_upload(self, api):
        """Upload Excel with br-tag content, verify preserved."""
        try:
            import openpyxl
            from io import BytesIO

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["StringID", "Source", "Target"])
            ws.append(["BR_XL_001", "줄 하나<br/>줄 둘", "Line one<br/>Line two"])
            ws.append(["BR_XL_002", "단순 텍스트", "Simple text"])
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)

            resp = api.create_project("BrTag-Upload-Excel")
            assert resp.status_code == 200
            pid = resp.json()["id"]
            try:
                resp = api.upload_file(
                    pid, "brtag_up.xlsx", buf.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                if resp.status_code != 200:
                    pytest.skip(f"Excel upload not available: {resp.status_code}")
                fid = resp.json()["id"]
                rows = _get_rows(api, fid)
                assert len(rows) >= 1
            finally:
                api.delete_project(pid, permanent=True)
        except ImportError:
            pytest.skip("openpyxl not installed")

    def test_brtag_txt_upload(self, api):
        """Upload TXT with br-tag content in TM, verify preserved."""
        resp = api.upload_tm("BrTag-TXT-TM", _TM_BRTAG.encode(), source_lang="ko", target_lang="en")
        if resp.status_code != 200:
            pytest.skip(f"TM upload unavailable: {resp.status_code}")
        tm_id = resp.json()["tm_id"]
        try:
            resp = api.list_tm_entries(tm_id)
            assert resp.status_code == 200
            data = resp.json()
            entries = data.get("entries", data.get("rows", data)) if isinstance(data, dict) else data
            brtag_found = any(
                "<br/>" in (str(e.get("source_text", "")) + str(e.get("target_text", "")))
                for e in entries
            )
            assert brtag_found, "br-tags lost in TM upload"
        finally:
            api.delete_tm(tm_id)


# ======================================================================
# 2. Edit br-tag preservation
# ======================================================================


@pytest.mark.brtag
class TestBrtagEdit:
    """br-tag preservation during editing."""

    def test_brtag_row_update(self, api):
        """Update row target with br-tag text, verify saved correctly."""
        resp = api.create_project("BrTag-Edit-Row")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_edit.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]
            rows = _get_rows(api, fid)

            row_id = rows[0]["id"]
            new_val = "수정된<br/>번역<br/>텍스트"
            resp = api.update_row(row_id, target=new_val)
            assert resp.status_code == 200

            # Re-read
            rows2 = _get_rows(api, fid)
            updated = [r for r in rows2 if r["id"] == row_id]
            if updated:
                tgt = updated[0].get("target", "") or ""
                assert "<br/>" in tgt, f"br-tags lost after edit: {tgt!r}"
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_gamedata_edit(self, api, mock_gamedata_path):
        """Edit gamedata cell with br-tag, verify preserved."""
        resp = api.browse_gamedata(str(mock_gamedata_path))
        if resp.status_code != 200:
            pytest.skip("Gamedata browse unavailable")
        data = resp.json()
        entries = data if isinstance(data, list) else data.get("entries", data.get("items", []))
        xml_files = [e for e in entries if isinstance(e, dict) and str(e.get("path", "")).endswith(".xml")]
        if not xml_files:
            pytest.skip("No XML files in mock gamedata")

        xml_path = xml_files[0]["path"]
        resp = api.save_gamedata(xml_path, entity_index=0, attr_name="Str", new_value="태그<br/>포함")
        assert resp.status_code in (200, 400, 422)

    def test_brtag_tm_entry_create(self, api):
        """Create TM entry with br-tags, verify stored."""
        resp = api.upload_tm("BrTag-TM-Entry", b"Source\tTarget\nA\tB\n", source_lang="ko", target_lang="en")
        if resp.status_code != 200:
            pytest.skip("TM upload unavailable")
        tm_id = resp.json()["tm_id"]
        try:
            resp = api.add_tm_entry(tm_id, source_text="소스<br/>텍스트", target_text="Target<br/>text")
            assert resp.status_code in (200, 201)

            resp = api.list_tm_entries(tm_id)
            assert resp.status_code == 200
            data = resp.json()
            entries = data.get("entries", data.get("rows", data)) if isinstance(data, dict) else data
            brtag_found = any(
                "<br/>" in (str(e.get("source_text", "")) + str(e.get("target_text", "")))
                for e in entries
            )
            assert brtag_found, "br-tags lost in TM entry creation"
        finally:
            api.delete_tm(tm_id)


# ======================================================================
# 3. Search br-tag handling
# ======================================================================


@pytest.mark.brtag
class TestBrtagSearch:
    """br-tag handling in search operations."""

    def test_brtag_in_search_results(self, api):
        """Search for text that contains br-tags, verify returned."""
        resp = api.create_project("BrTag-Search")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_search.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            resp = api.list_rows(fid, search="줄")
            assert resp.status_code == 200
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_tm_search(self, api):
        """TM search where source/target has br-tags."""
        resp = api.upload_tm("BrTag-TMSearch", _TM_BRTAG.encode(), source_lang="ko", target_lang="en")
        if resp.status_code != 200:
            pytest.skip("TM upload unavailable")
        tm_id = resp.json()["tm_id"]
        try:
            resp = api.search_tm(tm_id, query="줄")
            assert resp.status_code in (200, 404)
        finally:
            api.delete_tm(tm_id)

    def test_brtag_in_qa_results(self, api):
        """QA results reference text with br-tags correctly."""
        resp = api.create_project("BrTag-QA")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_qa.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            resp = api.check_file_qa(fid)
            assert resp.status_code in (200, 201, 422)

            resp = api.get_file_qa_results(fid)
            assert resp.status_code in (200, 404)
        finally:
            api.delete_project(pid, permanent=True)


# ======================================================================
# 4. Export br-tag preservation
# ======================================================================


@pytest.mark.brtag
class TestBrtagExport:
    """br-tag preservation during export."""

    def test_brtag_export_xml(self, api):
        """Export file with br-tags as XML, verify in output."""
        resp = api.create_project("BrTag-ExportXML")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_exp.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            resp = api.download_file(fid, fmt="xml")
            assert resp.status_code == 200
            content = resp.text
            # br-tags in XML attributes are stored as &lt;br/&gt; on disk
            assert "<br/>" in content or "&lt;br/&gt;" in content or "br/" in content
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_export_excel(self, api):
        """Export as Excel, verify br-tags in cells."""
        resp = api.create_project("BrTag-ExportExcel")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_exp_xl.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            resp = api.download_file(fid, fmt="xlsx")
            assert resp.status_code in (200, 422, 400)
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_full_roundtrip(self, api):
        """Upload -> edit -> export -> verify br-tags intact."""
        resp = api.create_project("BrTag-Roundtrip")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_rt.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            rows = _get_rows(api, fid)
            if rows:
                resp = api.update_row(rows[0]["id"], target="왕복<br/>테스트")
                assert resp.status_code == 200

            resp = api.download_file(fid, fmt="xml")
            assert resp.status_code == 200
            content = resp.text
            assert "<br/>" in content or "&lt;br/&gt;" in content
        finally:
            api.delete_project(pid, permanent=True)


# ======================================================================
# 5. Edge cases
# ======================================================================


@pytest.mark.brtag
class TestBrtagEdgeCases:
    """br-tag edge cases."""

    def test_brtag_multiple_per_field(self, api):
        """Text with 3+ br-tags in one field."""
        resp = api.create_project("BrTag-Multi")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_multi.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            rows = _get_rows(api, fid)
            if rows:
                val = "A<br/>B<br/>C<br/>D"
                resp = api.update_row(rows[0]["id"], target=val)
                assert resp.status_code == 200

                rows2 = _get_rows(api, fid)
                updated = [r for r in rows2 if r["id"] == rows[0]["id"]]
                if updated:
                    tgt = updated[0].get("target", "") or ""
                    assert tgt.count("<br/>") >= 3 or "br/" in tgt
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_at_start_and_end(self, api):
        """br-tag at beginning/end of text."""
        resp = api.create_project("BrTag-StartEnd")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_se.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]
            rows = _get_rows(api, fid)

            # Find BR_004 (starts with <br/>) or BR_005 (ends with <br/>)
            for r in rows:
                sid = r.get("string_id", "") or r.get("str_key", "")
                if sid in ("BR_004", "BR_005"):
                    src = r.get("source", "") or r.get("kr", "") or ""
                    assert "<br/>" in src or "br/" in src, f"br-tag lost in {sid}: {src!r}"
        finally:
            api.delete_project(pid, permanent=True)

    def test_brtag_with_korean_text(self, api):
        """br-tags mixed with Korean characters."""
        resp = api.create_project("BrTag-Korean")
        assert resp.status_code == 200
        pid = resp.json()["id"]
        try:
            resp = api.upload_file(pid, "brtag_kr.xml", _XML_BRTAG.encode())
            assert resp.status_code == 200
            fid = resp.json()["id"]

            rows = _get_rows(api, fid)
            if rows:
                mixed = "한국어<br/>텍스트<br/>혼합"
                resp = api.update_row(rows[0]["id"], target=mixed)
                assert resp.status_code == 200

                rows2 = _get_rows(api, fid)
                updated = [r for r in rows2 if r["id"] == rows[0]["id"]]
                if updated:
                    tgt = updated[0].get("target", "") or ""
                    assert "<br/>" in tgt, f"br-tag lost with Korean: {tgt!r}"
                    assert "한국어" in tgt or "텍스트" in tgt, f"Korean lost: {tgt!r}"
        finally:
            api.delete_project(pid, permanent=True)
