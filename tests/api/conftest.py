"""
Shared fixtures for API tests.

Provides session-scoped fixtures for authentication, project/folder/file/TM
lifecycle management, and a typed APIClient wrapper.  All fixtures use ``yield``
so that cleanup (project/TM deletion) runs automatically on session teardown.
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — ensure project root is importable
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from server.main import app


# ---------------------------------------------------------------------------
# Core client / auth
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Create a TestClient for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, str]:
    """Authenticate as admin and return bearer-token headers.

    Tries form-data first (OAuth2 spec), then falls back to JSON body.
    Raises ``RuntimeError`` if neither succeeds so that downstream tests
    fail loudly rather than silently running unauthenticated.
    """
    # Attempt 1: form data (OAuth2 password flow)
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    # Attempt 2: JSON body
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    raise RuntimeError(
        f"Admin login failed.  Last response: {response.status_code} "
        f"{response.text[:300]}"
    )


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_project_id(client: TestClient, auth_headers: dict[str, str]):
    """Create a dedicated test project; delete it on teardown."""
    resp = client.post(
        "/api/ldm/projects",
        headers=auth_headers,
        json={"name": "API-Test-Project-E2E", "description": "Automated test project"},
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.text}"
    project_id: int = resp.json()["id"]

    yield project_id

    # Teardown — permanent delete
    client.delete(
        f"/api/ldm/projects/{project_id}",
        headers=auth_headers,
        params={"permanent": True},
    )


@pytest.fixture(scope="session")
def test_folder_id(
    client: TestClient,
    auth_headers: dict[str, str],
    test_project_id: int,
):
    """Create a test folder inside the test project; delete on teardown."""
    resp = client.post(
        "/api/ldm/folders",
        headers=auth_headers,
        json={"name": "TestFolder-E2E", "project_id": test_project_id},
    )
    assert resp.status_code == 200, f"Folder creation failed: {resp.text}"
    folder_id: int = resp.json()["id"]

    yield folder_id

    # Cleanup handled by project deletion (cascade)


# ---------------------------------------------------------------------------
# File upload fixtures
# ---------------------------------------------------------------------------

_SAMPLE_LOCSTR_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LocStr>
  <String StrKey="TEST_001" KR="테스트 텍스트" EN="Test text" />
  <String StrKey="TEST_002" KR="두 번째<br/>줄" EN="Second line" />
  <String StrKey="TEST_003" KR="세 번째 항목" EN="Third item" />
</LocStr>
"""


@pytest.fixture(scope="session")
def uploaded_xml_file_id(
    client: TestClient,
    auth_headers: dict[str, str],
    test_project_id: int,
):
    """Upload a small LocStr XML file and return its file id."""
    resp = client.post(
        "/api/ldm/files/upload",
        headers=auth_headers,
        data={"project_id": str(test_project_id)},
        files={"file": ("test_locstr.xml", _SAMPLE_LOCSTR_XML.encode(), "text/xml")},
    )
    if resp.status_code != 200:
        pytest.skip(f"XML upload failed ({resp.status_code}): {resp.text[:200]}")
    yield resp.json()["id"]


@pytest.fixture(scope="session")
def uploaded_excel_file_id(
    client: TestClient,
    auth_headers: dict[str, str],
    test_project_id: int,
):
    """Upload a small Excel file and return its file id.

    Uses openpyxl to create a minimal .xlsx in memory.
    """
    try:
        import openpyxl
        from io import BytesIO

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["StringID", "Source", "Target"])
        ws.append(["ITEM_001", "검", "Sword"])
        ws.append(["ITEM_002", "방패", "Shield"])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        resp = client.post(
            "/api/ldm/files/upload",
            headers=auth_headers,
            data={"project_id": str(test_project_id)},
            files={"file": ("test_items.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        if resp.status_code != 200:
            pytest.skip(f"Excel upload failed ({resp.status_code}): {resp.text[:200]}")
        yield resp.json()["id"]
    except ImportError:
        pytest.skip("openpyxl not installed — cannot create Excel fixture")


# ---------------------------------------------------------------------------
# TM lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_tm_id(
    client: TestClient,
    auth_headers: dict[str, str],
):
    """Create a test Translation Memory; delete on teardown."""
    sample_tm_content = (
        "Source\tTarget\n"
        "검\tSword\n"
        "방패\tShield\n"
        "마법\tMagic\n"
    )

    resp = client.post(
        "/api/ldm/tm/upload",
        headers=auth_headers,
        data={"name": "E2E-Test-TM", "source_lang": "ko", "target_lang": "en", "auto_index": "false"},
        files={"file": ("test_tm.txt", sample_tm_content.encode(), "text/plain")},
    )
    if resp.status_code != 200:
        pytest.skip(f"TM upload failed ({resp.status_code}): {resp.text[:200]}")
    tm_id: int = resp.json()["tm_id"]

    yield tm_id

    # Teardown
    client.delete(f"/api/ldm/tm/{tm_id}", headers=auth_headers)


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_gamedata_path() -> Path:
    """Absolute path to ``tests/fixtures/mock_gamedata/``."""
    p = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
    assert p.is_dir(), f"mock_gamedata not found at {p}"
    return p


@pytest.fixture(scope="session")
def mock_uploads_path() -> Path:
    """Absolute path to ``tests/fixtures/mock_uploads/``."""
    p = Path(__file__).parent.parent / "fixtures" / "mock_uploads"
    assert p.is_dir(), f"mock_uploads not found at {p}"
    return p


# ---------------------------------------------------------------------------
# Typed API client wrapper
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api(client: TestClient, auth_headers: dict[str, str]):
    """Return an :class:`APIClient` instance pre-configured with auth."""
    from tests.api.helpers.api_client import APIClient

    return APIClient(client=client, auth_headers=auth_headers)
