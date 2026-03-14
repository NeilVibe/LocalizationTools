"""
Export Round-Trip Integration Test

Validates that the upload-edit-export pipeline preserves:
1. br-tags in XML attribute values (stored as &lt;br/&gt; on disk)
2. All original attributes (StringId, StrOrigin, Str, Memo, Desc, etc.)
3. XML element ordering and structure
4. Edits to individual rows while preserving other rows

Requirements: EDIT-06 (Export Pipeline)
Prerequisites: Server running at localhost:8888 with admin/admin123
"""

import io
import pytest
import requests
import xml.etree.ElementTree as ET


BASE_URL = "http://localhost:8888"
ADMIN_CREDS = {"username": "admin", "password": "admin123"}


# =============================================================================
# Test XML with br-tags and multiple attributes
# =============================================================================

TEST_XML_CONTENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<LangData>
  <LocStr StringId="BR_001" StrOrigin="첫 줄&lt;br/&gt;둘째 줄" Str="First line&lt;br/&gt;Second line" Memo="has br-tags" Desc="test description" />
  <LocStr StringId="BR_002" StrOrigin="한 줄만" Str="Single line only" Memo="no br" Desc="simple" />
  <LocStr StringId="BR_003" StrOrigin="A&lt;br/&gt;B&lt;br/&gt;C" Str="X&lt;br/&gt;Y&lt;br/&gt;Z" Memo="multi br" Desc="three lines" />
  <LocStr StringId="ATTR_001" StrOrigin="속성 테스트" Str="Attribute test" Memo="memo value" Desc="desc value" Category="UI" Priority="high" />
  <LocStr StringId="ATTR_002" StrOrigin="빈 값" Str="" Memo="" Desc="" />
</LangData>
"""

# Expected in-memory values after XML parsing (ElementTree unescapes &lt;br/&gt; to <br/>)
EXPECTED_BR_SOURCE_1 = "첫 줄<br/>둘째 줄"
EXPECTED_BR_TARGET_1 = "First line<br/>Second line"
EXPECTED_BR_SOURCE_3 = "A<br/>B<br/>C"
EXPECTED_BR_TARGET_3 = "X<br/>Y<br/>Z"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def auth_headers():
    """Get admin auth headers."""
    resp = requests.post(
        f"{BASE_URL}/api/v2/auth/login",
        json=ADMIN_CREDS,
        timeout=10
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def project_id(auth_headers):
    """Get first available project ID."""
    resp = requests.get(f"{BASE_URL}/api/ldm/projects", headers=auth_headers, timeout=10)
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) > 0, "No projects found"
    return projects[0]["id"]


@pytest.fixture
def uploaded_file(auth_headers, project_id):
    """Upload the test XML file and return file info. Cleanup after test."""
    files = {"file": ("roundtrip_test.xml", io.BytesIO(TEST_XML_CONTENT.encode("utf-8")), "application/xml")}
    data = {"project_id": str(project_id), "storage": "server"}

    resp = requests.post(
        f"{BASE_URL}/api/ldm/files/upload",
        files=files,
        data=data,
        headers=auth_headers,
        timeout=30
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    file_info = resp.json()
    file_id = file_info["id"]

    yield file_info

    # Cleanup: delete the test file
    requests.delete(
        f"{BASE_URL}/api/ldm/files/{file_id}",
        headers=auth_headers,
        timeout=10
    )


# =============================================================================
# Tests
# =============================================================================

class TestExportRoundTrip:
    """Test XML upload-export round-trip preserves data integrity."""

    def test_br_tags_preserved_through_roundtrip(self, auth_headers, uploaded_file):
        """Upload XML with br-tags, export, verify br-tags are preserved as &lt;br/&gt; in output."""
        file_id = uploaded_file["id"]

        # Download the exported file
        resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/download",
            headers=auth_headers,
            timeout=30
        )
        assert resp.status_code == 200, f"Download failed: {resp.text}"
        assert resp.headers.get("content-type", "").startswith("application/xml")

        # Parse the exported XML
        exported_xml = resp.content
        root = ET.fromstring(exported_xml)
        elements = root.findall(".//LocStr") or root.findall(".//*")

        # Find elements by StringId
        elem_map = {}
        for elem in elements:
            sid = elem.get("stringid") or elem.get("StringId", "")
            if sid:
                elem_map[sid] = elem

        # Verify BR_001: br-tags preserved
        assert "BR_001" in elem_map, f"BR_001 not found in export. Found: {list(elem_map.keys())}"
        br1 = elem_map["BR_001"]
        br1_source = br1.get("strorigin", "")
        br1_target = br1.get("str", "")

        # In memory, ElementTree gives us <br/> (unescaped)
        # When written to XML, it becomes &lt;br/&gt; (escaped) in the file
        assert "<br/>" in br1_source, f"BR_001 source lost br-tags: '{br1_source}'"
        assert "<br/>" in br1_target, f"BR_001 target lost br-tags: '{br1_target}'"

        # Verify BR_003: multiple br-tags
        assert "BR_003" in elem_map, "BR_003 not found in export"
        br3 = elem_map["BR_003"]
        br3_source = br3.get("strorigin", "")
        br3_target = br3.get("str", "")
        assert br3_source.count("<br/>") == 2, f"BR_003 source should have 2 br-tags: '{br3_source}'"
        assert br3_target.count("<br/>") == 2, f"BR_003 target should have 2 br-tags: '{br3_target}'"

        # Also verify the raw bytes contain &lt;br/&gt; (escaped form in XML)
        raw_text = exported_xml.decode("utf-8")
        assert "&lt;br/&gt;" in raw_text, (
            f"Exported XML should contain &lt;br/&gt; in raw bytes but got:\n{raw_text[:500]}"
        )

    def test_all_attributes_preserved(self, auth_headers, uploaded_file):
        """Upload XML with multiple attributes, export, verify all attributes present."""
        file_id = uploaded_file["id"]

        resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/download",
            headers=auth_headers,
            timeout=30
        )
        assert resp.status_code == 200

        root = ET.fromstring(resp.content)
        elements = root.findall(".//LocStr") or root.findall(".//*")

        elem_map = {}
        for elem in elements:
            sid = elem.get("stringid") or elem.get("StringId", "")
            if sid:
                elem_map[sid] = elem

        # ATTR_001 should have all attributes: Memo, Desc, Category, Priority
        assert "ATTR_001" in elem_map, f"ATTR_001 not found. Keys: {list(elem_map.keys())}"
        attr1 = elem_map["ATTR_001"]

        # Core attributes
        assert attr1.get("stringid") == "ATTR_001"
        assert attr1.get("strorigin") is not None
        assert attr1.get("str") is not None

        # Extra attributes preserved via extra_data
        attr1_attribs = dict(attr1.attrib)
        assert "Memo" in attr1_attribs or "memo" in {k.lower() for k in attr1_attribs}, (
            f"Memo attribute missing. Attributes: {attr1_attribs}"
        )
        assert "Desc" in attr1_attribs or "desc" in {k.lower() for k in attr1_attribs}, (
            f"Desc attribute missing. Attributes: {attr1_attribs}"
        )

        # Category and Priority should also be preserved (via extra_data)
        lower_attribs = {k.lower(): v for k, v in attr1_attribs.items()}
        assert "category" in lower_attribs, f"Category missing. Attributes: {attr1_attribs}"
        assert "priority" in lower_attribs, f"Priority missing. Attributes: {attr1_attribs}"
        assert lower_attribs["category"] == "UI"
        assert lower_attribs["priority"] == "high"

    def test_element_count_preserved(self, auth_headers, uploaded_file):
        """Upload XML with 5 elements, export, verify 5 elements in output."""
        file_id = uploaded_file["id"]

        resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/download",
            headers=auth_headers,
            timeout=30
        )
        assert resp.status_code == 200

        root = ET.fromstring(resp.content)
        elements = root.findall(".//LocStr") or root.findall(".//*")
        # Filter to only direct children that have stringid
        loc_elements = [e for e in elements if e.get("stringid")]

        assert len(loc_elements) == 5, (
            f"Expected 5 elements, got {len(loc_elements)}. "
            f"StringIds: {[e.get('stringid') for e in loc_elements]}"
        )

    def test_edit_then_export_reflects_change(self, auth_headers, uploaded_file):
        """Upload XML, edit a row, export, verify edit appears and other rows unchanged."""
        file_id = uploaded_file["id"]

        # Get the rows to find the row ID for BR_002
        rows_resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/rows?limit=100",
            headers=auth_headers,
            timeout=10
        )
        assert rows_resp.status_code == 200
        rows_data = rows_resp.json()
        rows = rows_data.get("rows", [])

        # Find BR_002 row
        br002_row = None
        for row in rows:
            if row.get("string_id") == "BR_002":
                br002_row = row
                break

        assert br002_row is not None, f"BR_002 row not found. StringIds: {[r.get('string_id') for r in rows]}"

        # Edit the target text
        edit_resp = requests.put(
            f"{BASE_URL}/api/ldm/rows/{br002_row['id']}",
            json={"target": "Edited translation"},
            headers={**auth_headers, "Content-Type": "application/json"},
            timeout=10
        )
        assert edit_resp.status_code == 200, f"Edit failed: {edit_resp.text}"

        # Download and verify
        resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/download",
            headers=auth_headers,
            timeout=30
        )
        assert resp.status_code == 200

        root = ET.fromstring(resp.content)
        elements = root.findall(".//LocStr") or root.findall(".//*")

        elem_map = {}
        for elem in elements:
            sid = elem.get("stringid") or elem.get("StringId", "")
            if sid:
                elem_map[sid] = elem

        # BR_002 should have the edited value
        assert "BR_002" in elem_map, "BR_002 not found after edit"
        assert elem_map["BR_002"].get("str") == "Edited translation", (
            f"Edit not reflected. Got: '{elem_map['BR_002'].get('str')}'"
        )

        # BR_001 should be unchanged (still has br-tags)
        assert "BR_001" in elem_map, "BR_001 missing after edit"
        br1_source = elem_map["BR_001"].get("strorigin", "")
        assert "<br/>" in br1_source, f"BR_001 source corrupted after edit: '{br1_source}'"

    def test_xml_structure_preserved(self, auth_headers, uploaded_file):
        """Verify the exported XML has proper structure: root element, encoding, element tag."""
        file_id = uploaded_file["id"]

        resp = requests.get(
            f"{BASE_URL}/api/ldm/files/{file_id}/download",
            headers=auth_headers,
            timeout=30
        )
        assert resp.status_code == 200

        raw = resp.content.decode("utf-8")

        # Should have XML declaration
        assert "<?xml" in raw, "Missing XML declaration"

        # Should have LangData root element
        root = ET.fromstring(resp.content)
        assert root.tag == "LangData", f"Root element should be LangData, got: {root.tag}"

        # All children should be LocStr elements
        children = list(root)
        for child in children:
            assert child.tag in ("LocStr", "String"), (
                f"Unexpected child tag: {child.tag}. Expected LocStr."
            )
