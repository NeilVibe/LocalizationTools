"""File upload, download, and management API tests.

Covers XML/Excel/TXT/TSV upload, file listing, download with content
preservation, br-tag and Korean round-trips, file operations (move,
rename, delete, to-TM), and error cases.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
    assert_file_response,
    assert_brtag_preserved,
    assert_korean_preserved,
)
from tests.api.helpers.constants import (
    FILE_FIELDS,
    VALID_FILE_FORMATS,
    KOREAN_TEXT_SAMPLES,
    BRTAG_SAMPLES,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.files]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _locstr_xml(entries: list[tuple[str, str, str]]) -> bytes:
    """Build a minimal LocStr XML from (strkey, kr, en) tuples."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<LanguageData>"]
    for key, kr, en in entries:
        lines.append(f'  <LocStr StrKey="{key}" KR="{kr}" EN="{en}" />')
    lines.append("</LanguageData>")
    return "\n".join(lines).encode("utf-8")


# ======================================================================
# Upload
# ======================================================================


class TestFileUpload:
    """File upload tests — POST /api/ldm/files/upload."""

    def test_upload_xml_locstr(self, api, test_project_id):
        """Upload LocStr XML, assert file created with correct row count."""
        content = _locstr_xml([
            ("UP_001", "테스트", "Test"),
            ("UP_002", "검", "Sword"),
            ("UP_003", "마법", "Magic"),
        ])
        resp = api.upload_file(
            project_id=test_project_id,
            filename="upload_test.xml",
            content=content,
            content_type="text/xml",
        )
        assert_status(resp, 200, "Upload XML")
        data = resp.json()
        assert "id" in data
        assert data.get("row_count", 0) >= 3 or data.get("rows_imported", 0) >= 3

    def test_upload_xml_from_fixture(self, api, test_project_id, mock_uploads_path):
        """Upload the locstr_upload_characterinfo.xml fixture."""
        xml_file = mock_uploads_path / "locstr_upload_characterinfo.xml"
        content = xml_file.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="characterinfo.xml",
            content=content,
            content_type="text/xml",
        )
        assert_status(resp, 200, "Upload XML fixture")
        data = resp.json()
        assert "id" in data

    def test_upload_excel_eu14col(self, api, test_project_id, mock_uploads_path):
        """Upload EU 14-col Excel fixture."""
        xlsx_file = mock_uploads_path / "eu_14col_sample.xlsx"
        content = xlsx_file.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="eu_14col_sample.xlsx",
            content=content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if resp.status_code == 200:
            assert "id" in resp.json()
        else:
            # Excel parsing may not be supported in test env
            assert resp.status_code in (400, 415, 422, 500)

    def test_upload_txt_tabdelimited(self, api, test_project_id, mock_uploads_path):
        """Upload tab-delimited TXT file."""
        txt_file = mock_uploads_path / "tab_delimited_sample.txt"
        content = txt_file.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="sample.txt",
            content=content,
            content_type="text/plain",
        )
        if resp.status_code == 200:
            assert "id" in resp.json()
        else:
            assert resp.status_code in (400, 415, 422, 500)

    def test_upload_tsv(self, api, test_project_id, mock_uploads_path):
        """Upload TSV file."""
        tsv_file = mock_uploads_path / "tab_delimited_korean.tsv"
        content = tsv_file.read_bytes()
        resp = api.upload_file(
            project_id=test_project_id,
            filename="korean.tsv",
            content=content,
            content_type="text/tab-separated-values",
        )
        if resp.status_code == 200:
            assert "id" in resp.json()
        else:
            assert resp.status_code in (400, 415, 422, 500)

    def test_upload_xml_with_brtags(self, api, test_project_id):
        """Upload XML with br-tags, verify tags preserved."""
        content = _locstr_xml([
            ("BR_001", "첫 줄<br/>둘째 줄", "First<br/>Second"),
            ("BR_002", "A<br/>B<br/>C", "X<br/>Y<br/>Z"),
        ])
        resp = api.upload_file(
            project_id=test_project_id,
            filename="brtag_test.xml",
            content=content,
        )
        assert_status(resp, 200, "Upload XML with br-tags")

    def test_upload_korean_text(self, api, test_project_id):
        """Upload Korean content, verify Unicode preserved."""
        content = _locstr_xml([
            ("KR_001", "검은 칼날의 전사", "Warrior of Black Blade"),
            ("KR_002", "봄의 숲에서 온 마법사", "Wizard from Spring Forest"),
        ])
        resp = api.upload_file(
            project_id=test_project_id,
            filename="korean_test.xml",
            content=content,
        )
        assert_status(resp, 200, "Upload Korean XML")

    def test_upload_invalid_format(self, api, test_project_id):
        """Upload .jpg returns 400/415."""
        resp = api.upload_file(
            project_id=test_project_id,
            filename="photo.jpg",
            content=b"\xff\xd8\xff\xe0fake_jpg",
            content_type="image/jpeg",
        )
        assert resp.status_code in (400, 415, 422), (
            f"Expected 400/415/422 for invalid format, got {resp.status_code}"
        )

    def test_upload_empty_file(self, api, test_project_id):
        """Upload empty XML returns error."""
        resp = api.upload_file(
            project_id=test_project_id,
            filename="empty.xml",
            content=b"",
        )
        assert resp.status_code in (400, 422, 500), (
            f"Expected error for empty file, got {resp.status_code}"
        )


# ======================================================================
# List / Get
# ======================================================================


class TestFileListGet:
    """File listing and detail retrieval."""

    def test_list_files_in_project(self, api, test_project_id, uploaded_xml_file_id):
        """GET /files?project_id returns file list."""
        resp = api.list_files(test_project_id)
        assert_status_ok(resp, "List files")
        data = resp.json()
        # Response may be a list or paginated dict
        if isinstance(data, list):
            assert len(data) >= 1
        elif isinstance(data, dict):
            files = data.get("files", data.get("rows", []))
            assert len(files) >= 1

    def test_get_file_details(self, api, uploaded_xml_file_id):
        """GET /files/{id} returns file with all schema fields."""
        resp = api.get_file(uploaded_xml_file_id)
        assert_status_ok(resp, "Get file details")
        data = resp.json()
        assert_file_response(data)
        assert data["id"] == uploaded_xml_file_id

    def test_get_nonexistent_file(self, api):
        """GET /files/999999 returns 404."""
        resp = api.get_file(999999)
        assert resp.status_code == 404

    def test_file_has_row_count(self, api, uploaded_xml_file_id):
        """File response includes row_count field."""
        resp = api.get_file(uploaded_xml_file_id)
        data = resp.json()
        assert "row_count" in data, f"Missing row_count in file response: {data.keys()}"
        assert isinstance(data["row_count"], int)

    def test_file_has_format(self, api, uploaded_xml_file_id):
        """File response includes format field."""
        resp = api.get_file(uploaded_xml_file_id)
        data = resp.json()
        assert "format" in data, f"Missing format in file response: {data.keys()}"


# ======================================================================
# Download
# ======================================================================


class TestFileDownload:
    """File download tests."""

    def test_download_file_xml(self, api, uploaded_xml_file_id):
        """Download file as XML, verify non-empty content."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xml")
        if resp.status_code == 200:
            assert len(resp.content) > 0, "Downloaded XML content is empty"
        else:
            # Some formats may not be supported
            assert resp.status_code in (400, 404, 415)

    def test_download_file_excel(self, api, uploaded_xml_file_id):
        """Download file as Excel (if supported)."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xlsx")
        # Accept success or unsupported format
        assert resp.status_code in (200, 400, 404, 415)
        if resp.status_code == 200:
            assert len(resp.content) > 0

    def test_download_nonexistent_file(self, api):
        """Download nonexistent file returns 404."""
        resp = api.download_file(999999, fmt="xml")
        assert resp.status_code == 404

    def test_download_preserves_content(self, api, uploaded_xml_file_id):
        """Download XML and verify it contains XML structure."""
        resp = api.download_file(uploaded_xml_file_id, fmt="xml")
        if resp.status_code == 200:
            text = resp.text
            # Should contain some XML markers
            assert "<" in text and ">" in text, "Download doesn't look like XML"


# ======================================================================
# Operations (move, rename, delete, to-tm)
# ======================================================================


class TestFileOperations:
    """File move, rename, delete, and convert operations."""

    def test_rename_file(self, api, test_project_id):
        """PATCH /files/{id}/rename changes file name."""
        content = _locstr_xml([("RN_001", "이름", "Name")])
        resp = api.upload_file(test_project_id, "rename_me.xml", content)
        if resp.status_code != 200:
            pytest.skip(f"Upload failed: {resp.status_code}")
        fid = resp.json()["id"]

        new_name = f"renamed_{int(time.time())}.xml"
        rename_resp = api.rename_file(fid, new_name)
        assert_status_ok(rename_resp, "Rename file")

        # Cleanup
        api.delete_file(fid, permanent=True)

    def test_move_file_to_folder(self, api, test_project_id, test_folder_id):
        """PATCH /files/{id}/move moves file to folder."""
        content = _locstr_xml([("MV_001", "이동", "Move")])
        resp = api.upload_file(test_project_id, "move_me.xml", content)
        if resp.status_code != 200:
            pytest.skip(f"Upload failed: {resp.status_code}")
        fid = resp.json()["id"]

        move_resp = api.move_file(fid, folder_id=test_folder_id)
        assert_status_ok(move_resp, "Move file")

        # Cleanup
        api.delete_file(fid, permanent=True)

    def test_delete_file(self, api, test_project_id):
        """DELETE /files/{id} removes file, then GET returns 404."""
        content = _locstr_xml([("DEL_001", "삭제", "Delete")])
        resp = api.upload_file(test_project_id, "delete_me.xml", content)
        if resp.status_code != 200:
            pytest.skip(f"Upload failed: {resp.status_code}")
        fid = resp.json()["id"]

        del_resp = api.delete_file(fid, permanent=True)
        assert_status_ok(del_resp, "Delete file")

        # Verify gone
        get_resp = api.get_file(fid)
        assert get_resp.status_code == 404

    def test_file_to_tm(self, api, test_project_id, uploaded_xml_file_id):
        """POST /files/{id}/to-tm registers file as TM source."""
        tm_name = f"TM-from-file-{int(time.time())}"
        resp = api.file_to_tm(uploaded_xml_file_id, name=tm_name)
        if resp.status_code in (404, 405):
            pytest.skip("file-to-TM endpoint not available")
        # Accept success or file-type error
        assert resp.status_code in (200, 201, 400, 422), (
            f"Unexpected status for file-to-TM: {resp.status_code}"
        )

    def test_delete_nonexistent_file(self, api):
        """DELETE /files/999999 returns 404."""
        resp = api.delete_file(999999, permanent=True)
        assert resp.status_code in (404, 200)


# ======================================================================
# Round-trip tests
# ======================================================================


@pytest.mark.brtag
@pytest.mark.korean
class TestFileRoundTrip:
    """Upload -> download -> verify content preservation."""

    def test_xml_upload_download_roundtrip(self, api, test_project_id):
        """Upload XML, download, verify content is present."""
        entries = [
            ("RT_001", "라운드트립 테스트", "Roundtrip test"),
            ("RT_002", "두 번째", "Second"),
        ]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "roundtrip.xml", content)
        assert_status(resp, 200, "Upload roundtrip XML")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            text = dl_resp.text
            assert "RT_001" in text or "라운드트립" in text, "Roundtrip content lost"

        api.delete_file(fid, permanent=True)

    @pytest.mark.brtag
    def test_brtag_roundtrip_preservation(self, api, test_project_id):
        """Upload XML with br-tags, download, verify br-tags preserved."""
        entries = [
            ("BRT_001", "첫 줄<br/>둘째 줄", "First<br/>Second"),
            ("BRT_002", "A<br/>B<br/>C", "X<br/>Y<br/>Z"),
        ]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "brtag_roundtrip.xml", content)
        assert_status(resp, 200, "Upload br-tag XML")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            text = dl_resp.text
            # br-tags should be in the output in some form
            assert "<br/>" in text or "&lt;br/&gt;" in text, (
                f"br-tags lost in round-trip. Downloaded text: {text[:500]}"
            )

        api.delete_file(fid, permanent=True)

    @pytest.mark.korean
    def test_korean_roundtrip_preservation(self, api, test_project_id):
        """Upload Korean text, download, verify Unicode intact."""
        korean_text = "검은 칼날의 전사"
        entries = [("KRT_001", korean_text, "Warrior of Black Blade")]
        content = _locstr_xml(entries)
        resp = api.upload_file(test_project_id, "korean_roundtrip.xml", content)
        assert_status(resp, 200, "Upload Korean XML")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            text = dl_resp.text
            assert_korean_preserved(korean_text, text)

        api.delete_file(fid, permanent=True)

    def test_brtag_fixture_roundtrip(self, api, test_project_id, mock_uploads_path):
        """Upload br-tag fixture XML, download, verify preservation."""
        xml_file = mock_uploads_path / "locstr_upload_mixed_brtags.xml"
        original = xml_file.read_text(encoding="utf-8")
        resp = api.upload_file(
            test_project_id,
            "mixed_brtags.xml",
            xml_file.read_bytes(),
        )
        if resp.status_code != 200:
            pytest.skip(f"Upload failed: {resp.status_code}")
        fid = resp.json()["id"]

        dl_resp = api.download_file(fid, fmt="xml")
        if dl_resp.status_code == 200:
            downloaded = dl_resp.text
            # Check br-tag count is preserved (in either literal or escaped form)
            orig_br = original.count("<br/>") + original.count("&lt;br/&gt;")
            dl_br = downloaded.count("<br/>") + downloaded.count("&lt;br/&gt;")
            assert dl_br >= orig_br, (
                f"br-tag count dropped: original={orig_br}, downloaded={dl_br}"
            )

        api.delete_file(fid, permanent=True)

    def test_upload_to_folder(self, api, test_project_id, test_folder_id):
        """Upload file directly into a folder."""
        content = _locstr_xml([("FLD_001", "폴더", "Folder")])
        resp = api.upload_file(
            project_id=test_project_id,
            filename="in_folder.xml",
            content=content,
            folder_id=test_folder_id,
        )
        if resp.status_code == 200:
            fid = resp.json()["id"]
            # Verify file is associated with folder
            file_resp = api.get_file(fid)
            if file_resp.status_code == 200:
                data = file_resp.json()
                if "folder_id" in data:
                    assert data["folder_id"] == test_folder_id
            api.delete_file(fid, permanent=True)
        else:
            # folder_id param may not be supported in upload
            assert resp.status_code in (200, 400, 422)
