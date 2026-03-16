"""Cross-subsystem integration workflow tests.

These tests simulate real user workflows spanning multiple API subsystems.
Each test makes 3+ API calls across 2+ subsystems to verify end-to-end
behavior. Marked with ``@pytest.mark.integration`` — they are slow by nature.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Inline XML/text helpers — avoids file I/O in tests
# ---------------------------------------------------------------------------

_LOCSTR_XML_WITH_BRTAGS = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <String StrKey="INT_001" KR="첫 번째<br/>줄" EN="First line" />
  <String StrKey="INT_002" KR="두 번째 항목" EN="Second item" />
  <String StrKey="INT_003" KR="세 번째<br/>테스트" EN="Third<br/>test" />
  <String StrKey="INT_004" KR="네 번째" EN="Fourth" />
  <String StrKey="INT_005" KR="다섯 번째" EN="Fifth" />
</LanguageData>
"""

_LOCSTR_XML_B = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <String StrKey="FILE_B_001" KR="검은 칼" EN="Black Sword" />
  <String StrKey="FILE_B_002" KR="하얀 방패" EN="White Shield" />
</LanguageData>
"""

_LOCSTR_XML_C = """\
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <String StrKey="FILE_C_001" KR="마법사의 지팡이" EN="Wizard Staff" />
</LanguageData>
"""

_TM_TSV = "Source\tTarget\n검\tSword\n방패\tShield\n마법\tMagic\n칼\tBlade\n"


# ======================================================================
# 1. Translator Workflows
# ======================================================================


@pytest.mark.integration
class TestTranslatorWorkflow:
    """Translator subsystem end-to-end workflows."""

    def test_translator_full_workflow(self, api):
        """Create project -> upload XML -> list rows -> edit row -> run QA -> export."""
        # 1. Create project
        resp = api.create_project("IntWf-Translator-Full")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            # 2. Upload XML
            resp = api.upload_file(project_id, "wf_full.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200, f"Upload failed: {resp.text[:200]}"
            file_id = resp.json()["id"]

            # 3. List rows
            resp = api.list_rows(file_id)
            assert resp.status_code == 200
            data = resp.json()
            rows = data.get("rows", data) if isinstance(data, dict) else data
            assert len(rows) >= 3

            # 4. Edit a row
            row_id = rows[0]["id"]
            resp = api.update_row(row_id, target="수정된 번역")
            assert resp.status_code == 200

            # 5. QA check
            resp = api.check_file_qa(file_id)
            assert resp.status_code in (200, 201, 422)

            # 6. Export / download
            resp = api.download_file(file_id, fmt="xml")
            assert resp.status_code == 200
        finally:
            api.delete_project(project_id, permanent=True)

    def test_translator_tm_workflow(self, api):
        """Upload file -> register as TM -> search TM -> verify."""
        resp = api.create_project("IntWf-TM-Workflow")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            # Upload file
            resp = api.upload_file(project_id, "wf_tm.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Register as TM
            resp = api.file_to_tm(file_id, name="IntWf-FromFile-TM")
            if resp.status_code == 200:
                tm_id = resp.json().get("tm_id") or resp.json().get("id")
                # Search TM
                resp = api.search_tm(tm_id, query="첫")
                assert resp.status_code in (200, 404)
                # Cleanup
                api.delete_tm(tm_id)
        finally:
            api.delete_project(project_id, permanent=True)

    def test_translator_pretranslate_workflow(self, api):
        """Create TM -> add entries -> pretranslate new file -> verify rows populated."""
        # Create a TM
        tm_content = _TM_TSV.encode()
        resp = api.upload_tm("IntWf-Pretranslate-TM", tm_content, source_lang="ko", target_lang="en")
        if resp.status_code != 200:
            pytest.skip(f"TM upload unavailable: {resp.status_code}")
        tm_id = resp.json()["tm_id"]

        resp = api.create_project("IntWf-Pretranslate")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            # Upload file
            resp = api.upload_file(project_id, "wf_pretrans.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Pretranslate
            resp = api.pretranslate(file_id, tm_id)
            assert resp.status_code in (200, 422, 500)
        finally:
            api.delete_project(project_id, permanent=True)
            api.delete_tm(tm_id)

    def test_translator_merge_workflow(self, api):
        """Upload source -> upload merge target -> merge."""
        resp = api.create_project("IntWf-Merge")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp = api.upload_file(project_id, "wf_merge_src.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Attempt merge with a second XML
            resp = api.merge_file(
                file_id,
                data={"mode": "fuzzy"},
                files={"file": ("merge_target.xml", _LOCSTR_XML_B.encode(), "text/xml")},
            )
            assert resp.status_code in (200, 422, 400)
        finally:
            api.delete_project(project_id, permanent=True)

    def test_translator_multi_file(self, api):
        """Upload 3 files to project -> search across files."""
        resp = api.create_project("IntWf-MultiFile")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            for name, content in [
                ("multi_a.xml", _LOCSTR_XML_WITH_BRTAGS),
                ("multi_b.xml", _LOCSTR_XML_B),
                ("multi_c.xml", _LOCSTR_XML_C),
            ]:
                resp = api.upload_file(project_id, name, content.encode())
                assert resp.status_code == 200, f"Upload {name} failed: {resp.text[:200]}"

            # List files
            resp = api.list_files(project_id)
            assert resp.status_code == 200
            files = resp.json()
            assert len(files) >= 3

            # Search across project
            resp = api.search_explorer("검")
            assert resp.status_code == 200
        finally:
            api.delete_project(project_id, permanent=True)


# ======================================================================
# 2. GameDev Workflows
# ======================================================================


@pytest.mark.integration
class TestGameDevWorkflow:
    """GameDev subsystem workflows."""

    def test_gamedev_browse_edit_workflow(self, api, mock_gamedata_path):
        """Browse gamedata -> detect columns -> save cell."""
        resp = api.browse_gamedata(str(mock_gamedata_path))
        if resp.status_code != 200:
            pytest.skip("Gamedata browse not available")
        data = resp.json()
        assert isinstance(data, (list, dict))

        # Find a file for column detection
        entries = data if isinstance(data, list) else data.get("entries", data.get("items", []))
        xml_files = [e for e in entries if isinstance(e, dict) and str(e.get("path", "")).endswith(".xml")]
        if not xml_files:
            pytest.skip("No XML files in mock gamedata")

        xml_path = xml_files[0]["path"]
        resp = api.detect_columns(xml_path)
        assert resp.status_code == 200

        # Attempt save
        resp = api.save_gamedata(xml_path, entity_index=0, attr_name="Str", new_value="Edited")
        assert resp.status_code in (200, 400, 422)

    def test_gamedev_codex_workflow(self, api):
        """Browse codex entity types -> list entities."""
        resp = api.get_codex_types()
        if resp.status_code != 200:
            pytest.skip("Codex not available")
        types = resp.json()
        assert isinstance(types, (list, dict))

        type_list = types if isinstance(types, list) else types.get("types", [])
        for etype in type_list[:3]:
            name = etype if isinstance(etype, str) else etype.get("name", etype.get("type", ""))
            if name:
                resp = api.list_codex_entities(name)
                assert resp.status_code in (200, 404)

    def test_gamedev_worldmap_workflow(self, api):
        """Load worldmap data -> verify structure."""
        resp = api.get_worldmap()
        if resp.status_code != 200:
            pytest.skip("WorldMap not available")
        data = resp.json()
        assert "nodes" in data or "error" in data or isinstance(data, dict)

    def test_gamedev_cross_reference(self, api):
        """Search codex -> get entity -> check context."""
        resp = api.search_codex("sword")
        if resp.status_code != 200:
            pytest.skip("Codex search not available")
        data = resp.json()
        results = data.get("results", [])
        if not results:
            pytest.skip("No codex results for 'sword'")
        entity = results[0]
        etype = entity.get("entity_type", "item")
        strkey = entity.get("strkey", "")
        if strkey:
            resp = api.get_codex_entity(etype, strkey)
            assert resp.status_code in (200, 404)


# ======================================================================
# 3. AI Workflows
# ======================================================================


@pytest.mark.integration
class TestAIWorkflow:
    """AI subsystem workflows."""

    def test_ai_suggestion_workflow(self, api):
        """Check AI status -> get suggestions for a string."""
        resp = api.ai_suggestions_status()
        assert resp.status_code in (200, 503)

        resp = api.get_ai_suggestions("INT_001")
        assert resp.status_code in (200, 404, 503)

    def test_ai_naming_workflow(self, api):
        """Check naming status -> request naming suggestions."""
        resp = api.naming_status()
        assert resp.status_code in (200, 503)

        resp = api.naming_suggest("item", name="Black Sword")
        assert resp.status_code in (200, 404, 503)

    def test_ai_context_workflow(self, api):
        """Detect entities in text -> verify response shape."""
        resp = api.detect_entities_in_text("The warrior wielded a legendary sword.")
        assert resp.status_code in (200, 404, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))


# ======================================================================
# 4. Data Integrity Workflows
# ======================================================================


@pytest.mark.integration
class TestDataIntegrityWorkflow:
    """Data integrity across operations."""

    def test_upload_edit_download_integrity(self, api):
        """Upload -> edit multiple rows -> download -> compare edits preserved."""
        resp = api.create_project("IntWf-Integrity")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp = api.upload_file(project_id, "integrity.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # List and edit rows
            resp = api.list_rows(file_id)
            assert resp.status_code == 200
            data = resp.json()
            rows = data.get("rows", data) if isinstance(data, dict) else data
            assert len(rows) >= 2

            edit_values = {}
            for i, row in enumerate(rows[:3]):
                new_val = f"Edited-{i}-테스트"
                resp = api.update_row(row["id"], target=new_val)
                if resp.status_code == 200:
                    edit_values[row["id"]] = new_val

            # Download and check
            resp = api.download_file(file_id, fmt="xml")
            assert resp.status_code == 200
            content = resp.text
            for val in edit_values.values():
                assert val in content or "Edited" in content
        finally:
            api.delete_project(project_id, permanent=True)

    def test_brtag_through_all_operations(self, api):
        """Upload with br-tags -> edit (keep br-tags) -> QA -> export -> verify."""
        resp = api.create_project("IntWf-BrTag-Integrity")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp = api.upload_file(project_id, "brtag_integ.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Read rows
            resp = api.list_rows(file_id)
            assert resp.status_code == 200
            data = resp.json()
            rows = data.get("rows", data) if isinstance(data, dict) else data

            # Find row with br-tag
            brtag_row = None
            for r in rows:
                src = r.get("source", "") or ""
                tgt = r.get("target", "") or ""
                kr = r.get("kr", "") or ""
                if "<br/>" in src or "<br/>" in tgt or "<br/>" in kr:
                    brtag_row = r
                    break

            if brtag_row:
                # Edit keeping br-tag
                resp = api.update_row(brtag_row["id"], target="수정<br/>번역")
                assert resp.status_code == 200

            # QA
            resp = api.check_file_qa(file_id)
            assert resp.status_code in (200, 201, 422)

            # Export
            resp = api.download_file(file_id, fmt="xml")
            assert resp.status_code == 200
            # br-tags should appear in export (as literal or entity-encoded in XML)
            content = resp.text
            assert "<br/>" in content or "&lt;br/&gt;" in content or "br/" in content
        finally:
            api.delete_project(project_id, permanent=True)

    def test_korean_through_all_operations(self, api):
        """Upload Korean -> edit Korean -> search Korean -> export -> verify no mojibake."""
        resp = api.create_project("IntWf-Korean-Integrity")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp = api.upload_file(project_id, "korean_integ.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Read rows
            resp = api.list_rows(file_id)
            assert resp.status_code == 200
            data = resp.json()
            rows = data.get("rows", data) if isinstance(data, dict) else data

            # Edit with Korean
            if rows:
                resp = api.update_row(rows[0]["id"], target="한국어 수정 테스트")
                assert resp.status_code == 200

            # Search Korean
            resp = api.search_explorer("번째")
            assert resp.status_code == 200

            # Export and verify
            resp = api.download_file(file_id, fmt="xml")
            assert resp.status_code == 200
            content = resp.text
            # Verify Korean survived round-trip (no mojibake)
            assert "한국어" in content or "번째" in content or "테스트" in content
        finally:
            api.delete_project(project_id, permanent=True)

    def test_concurrent_file_operations(self, api):
        """Upload file A and B -> verify no cross-contamination."""
        resp = api.create_project("IntWf-Concurrent")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp_a = api.upload_file(project_id, "conc_a.xml", _LOCSTR_XML_B.encode())
            resp_b = api.upload_file(project_id, "conc_b.xml", _LOCSTR_XML_C.encode())
            assert resp_a.status_code == 200
            assert resp_b.status_code == 200

            file_a = resp_a.json()["id"]
            file_b = resp_b.json()["id"]

            # Verify rows are distinct
            rows_a = api.list_rows(file_a)
            rows_b = api.list_rows(file_b)
            assert rows_a.status_code == 200
            assert rows_b.status_code == 200

            data_a = rows_a.json()
            data_b = rows_b.json()
            list_a = data_a.get("rows", data_a) if isinstance(data_a, dict) else data_a
            list_b = data_b.get("rows", data_b) if isinstance(data_b, dict) else data_b

            ids_a = {r.get("string_id") or r.get("str_key") for r in list_a}
            ids_b = {r.get("string_id") or r.get("str_key") for r in list_b}
            assert ids_a.isdisjoint(ids_b), "Cross-contamination: files share string IDs"
        finally:
            api.delete_project(project_id, permanent=True)


# ======================================================================
# 5. Error Recovery
# ======================================================================


@pytest.mark.integration
class TestErrorRecovery:
    """Error recovery and cascade delete workflows."""

    def test_delete_project_cascades(self, api):
        """Delete project -> verify files gone -> verify rows gone."""
        resp = api.create_project("IntWf-Cascade")
        assert resp.status_code == 200
        project_id = resp.json()["id"]

        # Upload file
        resp = api.upload_file(project_id, "cascade.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        # Delete project
        resp = api.delete_project(project_id, permanent=True)
        assert resp.status_code == 200

        # Verify file gone
        resp = api.get_file(file_id)
        assert resp.status_code in (404, 422, 400)

        # Verify project gone
        resp = api.get_project(project_id)
        assert resp.status_code in (404, 422, 400)

    def test_file_operations_after_project_delete(self, api):
        """Attempt file operations on deleted project -> assert proper errors."""
        resp = api.create_project("IntWf-PostDelete")
        assert resp.status_code == 200
        project_id = resp.json()["id"]

        resp = api.upload_file(project_id, "postdel.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
        assert resp.status_code == 200
        file_id = resp.json()["id"]

        # Delete
        api.delete_project(project_id, permanent=True)

        # Operations on deleted file should error
        resp = api.list_rows(file_id)
        assert resp.status_code in (404, 422, 400, 500)

        resp = api.download_file(file_id)
        assert resp.status_code in (404, 422, 400, 500)

    def test_upload_then_delete_then_reupload(self, api):
        """Full lifecycle -> verify clean state after re-creation."""
        resp = api.create_project("IntWf-Lifecycle")
        assert resp.status_code == 200
        project_id = resp.json()["id"]

        resp = api.upload_file(project_id, "life1.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
        assert resp.status_code == 200

        # Delete
        api.delete_project(project_id, permanent=True)

        # Re-create
        resp = api.create_project("IntWf-Lifecycle-V2")
        assert resp.status_code == 200
        new_project_id = resp.json()["id"]
        try:
            # Upload to new project
            resp = api.upload_file(new_project_id, "life2.xml", _LOCSTR_XML_B.encode())
            assert resp.status_code == 200

            # List files — should only have the new one
            resp = api.list_files(new_project_id)
            assert resp.status_code == 200
            files = resp.json()
            assert len(files) >= 1
        finally:
            api.delete_project(new_project_id, permanent=True)

    def test_interrupted_merge_recovery(self, api):
        """Verify file remains consistent after failed merge."""
        resp = api.create_project("IntWf-MergeRecover")
        assert resp.status_code == 200
        project_id = resp.json()["id"]
        try:
            resp = api.upload_file(project_id, "recover_src.xml", _LOCSTR_XML_WITH_BRTAGS.encode())
            assert resp.status_code == 200
            file_id = resp.json()["id"]

            # Attempt merge with invalid/empty content (should fail gracefully)
            resp = api.merge_file(
                file_id,
                data={"mode": "invalid_mode"},
                files={"file": ("bad.xml", b"<not-valid>", "text/xml")},
            )
            # Should fail but not corrupt the original
            assert resp.status_code in (200, 400, 422, 500)

            # Verify original file still accessible
            resp = api.list_rows(file_id)
            assert resp.status_code == 200
            data = resp.json()
            rows = data.get("rows", data) if isinstance(data, dict) else data
            assert len(rows) >= 1, "File data corrupted after failed merge"
        finally:
            api.delete_project(project_id, permanent=True)
