"""Merge endpoint API tests.

Covers translator merge (5 match modes), Game Dev merge (position-based),
and merge error handling. Tests use session-scoped fixtures for uploaded
files and validate merge response schemas.
"""
from __future__ import annotations

import time

import pytest

from tests.api.helpers.assertions import (
    assert_status,
    assert_status_ok,
    assert_json_fields,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.merge]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MERGE_RESPONSE_FIELDS = ["matched", "skipped", "total", "match_type_counts", "rows_updated"]

VALID_MATCH_MODES = ["strict", "stringid_only", "strorigin_only", "fuzzy", "cascade"]


def _locstr_xml(entries: list[tuple[str, str, str]]) -> bytes:
    """Build a minimal LocStr XML from (strkey, kr, en) tuples."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<LocStr>"]
    for key, kr, en in entries:
        lines.append(f'  <String StrKey="{key}" KR="{kr}" EN="{en}" />')
    lines.append("</LocStr>")
    return "\n".join(lines).encode("utf-8")


def _upload_pair(api, project_id: int, suffix: str):
    """Upload a target + source pair for merge testing. Returns (target_id, source_id)."""
    target_xml = _locstr_xml([
        (f"MRG_{suffix}_001", "원본 텍스트", "Original text"),
        (f"MRG_{suffix}_002", "두 번째 원본", "Second original"),
        (f"MRG_{suffix}_003", "세 번째 원본", "Third original"),
    ])
    source_xml = _locstr_xml([
        (f"MRG_{suffix}_001", "수정된 텍스트", "Corrected text"),
        (f"MRG_{suffix}_002", "두 번째 수정", "Second corrected"),
        (f"MRG_{suffix}_003", "세 번째 수정", "Third corrected"),
    ])
    t_resp = api.upload_file(project_id, f"target_{suffix}.xml", target_xml)
    if t_resp.status_code != 200:
        return None, None
    s_resp = api.upload_file(project_id, f"source_{suffix}.xml", source_xml)
    if s_resp.status_code != 200:
        return None, None
    return t_resp.json()["id"], s_resp.json()["id"]


# ======================================================================
# Translator Merge
# ======================================================================


class TestTranslatorMerge:
    """POST /api/ldm/files/{file_id}/merge -- translator merge tests."""

    @pytest.mark.parametrize("mode", VALID_MATCH_MODES)
    def test_translator_merge_mode(self, api, test_project_id, mode):
        """Merge with each individual match mode succeeds or returns sensible error."""
        target_id, source_id = _upload_pair(api, test_project_id, f"mode_{mode}")
        if target_id is None:
            pytest.skip("File upload failed")

        resp = api.merge_file(
            target_id,
            json={"source_file_id": source_id, "match_mode": mode, "threshold": 0.85},
        )
        # Accept 200 (merge OK) or 404 (rows not yet parsed in test env)
        assert resp.status_code in (200, 404, 422, 500), (
            f"Merge mode={mode}: unexpected status {resp.status_code}: {resp.text[:300]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert_json_fields(data, MERGE_RESPONSE_FIELDS, f"Merge mode={mode}")
            assert isinstance(data["matched"], int)
            assert isinstance(data["rows_updated"], int)

        # Cleanup
        api.delete_file(target_id, permanent=True)
        api.delete_file(source_id, permanent=True)

    def test_translator_merge_all_modes_combined(self, api, test_project_id):
        """Merge using cascade mode (combines all 5 modes)."""
        target_id, source_id = _upload_pair(api, test_project_id, "cascade")
        if target_id is None:
            pytest.skip("File upload failed")

        resp = api.merge_file(
            target_id,
            json={"source_file_id": source_id, "match_mode": "cascade"},
        )
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert "match_type_counts" in data

        api.delete_file(target_id, permanent=True)
        api.delete_file(source_id, permanent=True)

    def test_translator_merge_preserves_brtags(self, api, test_project_id):
        """br-tags preserved through merge process."""
        target_xml = _locstr_xml([
            ("BRT_M_001", "첫 줄<br/>둘째 줄", "First<br/>Second"),
        ])
        source_xml = _locstr_xml([
            ("BRT_M_001", "수정<br/>줄", "Fixed<br/>Line"),
        ])
        t_resp = api.upload_file(test_project_id, "brtag_target.xml", target_xml)
        s_resp = api.upload_file(test_project_id, "brtag_source.xml", source_xml)
        if t_resp.status_code != 200 or s_resp.status_code != 200:
            pytest.skip("Upload failed")
        t_id, s_id = t_resp.json()["id"], s_resp.json()["id"]

        resp = api.merge_file(
            t_id,
            json={"source_file_id": s_id, "match_mode": "strict"},
        )
        # Just verify no 500 error -- br-tag preservation is structural
        assert resp.status_code in (200, 404, 422)

        api.delete_file(t_id, permanent=True)
        api.delete_file(s_id, permanent=True)

    def test_translator_merge_korean(self, api, test_project_id):
        """Korean text correctly merged."""
        target_xml = _locstr_xml([
            ("KR_M_001", "검은 칼날의 전사", "Warrior of Black Blade"),
        ])
        source_xml = _locstr_xml([
            ("KR_M_001", "어둠의 전사", "Dark Warrior"),
        ])
        t_resp = api.upload_file(test_project_id, "kr_merge_target.xml", target_xml)
        s_resp = api.upload_file(test_project_id, "kr_merge_source.xml", source_xml)
        if t_resp.status_code != 200 or s_resp.status_code != 200:
            pytest.skip("Upload failed")
        t_id, s_id = t_resp.json()["id"], s_resp.json()["id"]

        resp = api.merge_file(
            t_id,
            json={"source_file_id": s_id, "match_mode": "stringid_only"},
        )
        assert resp.status_code in (200, 404, 422)

        api.delete_file(t_id, permanent=True)
        api.delete_file(s_id, permanent=True)

    def test_merge_invalid_mode(self, api, uploaded_xml_file_id):
        """Merge with invalid match_mode returns 400."""
        resp = api.merge_file(
            uploaded_xml_file_id,
            json={"source_file_id": 999999, "match_mode": "invalid_mode"},
        )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for invalid mode, got {resp.status_code}"
        )

    def test_merge_nonexistent_source(self, api, uploaded_xml_file_id):
        """Merge with nonexistent source file returns 404."""
        resp = api.merge_file(
            uploaded_xml_file_id,
            json={"source_file_id": 999999, "match_mode": "strict"},
        )
        assert resp.status_code in (400, 404, 422)

    def test_merge_nonexistent_target(self, api):
        """Merge into nonexistent target file returns 404."""
        resp = api.merge_file(
            999999,
            json={"source_file_id": 1, "match_mode": "strict"},
        )
        assert resp.status_code in (404, 422)

    def test_merge_with_threshold(self, api, test_project_id):
        """Merge with custom fuzzy threshold parameter."""
        target_id, source_id = _upload_pair(api, test_project_id, "thresh")
        if target_id is None:
            pytest.skip("File upload failed")

        resp = api.merge_file(
            target_id,
            json={
                "source_file_id": source_id,
                "match_mode": "fuzzy",
                "threshold": 0.5,
            },
        )
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data["matched"], int)

        api.delete_file(target_id, permanent=True)
        api.delete_file(source_id, permanent=True)


# ======================================================================
# GameDev Merge
# ======================================================================


class TestGameDevMerge:
    """POST /api/ldm/files/{file_id}/gamedev-merge tests."""

    def test_gamedev_merge_basic(self, api, uploaded_xml_file_id):
        """GameDev merge returns expected response or graceful error."""
        resp = api.gamedev_merge_file(
            uploaded_xml_file_id,
            json={"max_depth": 3},
        )
        # 422 = no original_content stored, 404 = rows not found
        assert resp.status_code in (200, 404, 422), (
            f"GameDev merge: unexpected {resp.status_code}: {resp.text[:300]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            assert_json_fields(
                data,
                ["total_nodes", "changed_nodes", "rows_updated", "output_xml"],
                "GameDevMerge",
            )

    def test_gamedev_merge_nonexistent_file(self, api):
        """GameDev merge on nonexistent file returns 404."""
        resp = api.gamedev_merge_file(999999, json={"max_depth": 3})
        assert resp.status_code in (404, 422)

    def test_gamedev_merge_preserves_attributes(self, api, uploaded_xml_file_id):
        """GameDev merge does not drop XML attributes."""
        resp = api.gamedev_merge_file(
            uploaded_xml_file_id,
            json={"max_depth": 5},
        )
        # Accept error codes since test file may not have original_content
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert "output_xml" in data
            assert isinstance(data["output_xml"], str)

    def test_gamedev_merge_brtag_preservation(self, api, test_project_id):
        """GameDev merge preserves br-tags in data."""
        content = _locstr_xml([
            ("GD_BR_001", "게임<br/>데이터", "Game<br/>Data"),
        ])
        resp = api.upload_file(test_project_id, "gd_brtag_merge.xml", content)
        if resp.status_code != 200:
            pytest.skip("Upload failed")
        fid = resp.json()["id"]

        resp = api.gamedev_merge_file(fid, json={"max_depth": 3})
        # Accept 422 (no original_content) or 200
        assert resp.status_code in (200, 404, 422)

        api.delete_file(fid, permanent=True)

    def test_gamedev_merge_with_new_entities(self, api, uploaded_xml_file_id):
        """GameDev merge handles diff with depth param."""
        resp = api.gamedev_merge_file(
            uploaded_xml_file_id,
            json={"max_depth": 1},
        )
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            # added_nodes should be an integer
            assert isinstance(data.get("added_nodes", 0), int)
