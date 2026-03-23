"""
Shared fixtures for merge pipeline integration tests.

Provides admin auth, mock data setup, and temporary merge directories
for the E2E merge pipeline test suite.

Requires: DEV_MODE=true python3 server/main.py running on localhost:8888
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import requests

# ============================================================================
# Constants
# ============================================================================

BASE_URL = "http://localhost:8888"
TEST123_PATH = "/mnt/c/Users/MYCOM/Desktop/oldoldVold/test123"
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def server_running():
    """Skip entire module if server is not running."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        resp.raise_for_status()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        pytest.skip("Server not running at localhost:8888")


@pytest.fixture(scope="module")
def admin_headers(server_running):
    """Get admin auth headers via the self-healing token mechanism."""
    from tests.conftest import get_admin_token_with_retry

    token = get_admin_token_with_retry()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def mock_data_ready(server_running):
    """Run setup_mock_data.py to create fresh mock projects."""
    result = subprocess.run(
        ["python3", "scripts/setup_mock_data.py", "--confirm-wipe"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"setup_mock_data.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    yield result.stdout + result.stderr


@pytest.fixture
def merge_temp_target(tmp_path):
    """Create a temporary target directory with a minimal languagedata XML."""
    target_dir = tmp_path / "merge_target"
    target_dir.mkdir()

    test123 = Path(TEST123_PATH)
    source_file = test123 / "languagedata_fr PC 0904 1847.txt"

    if source_file.exists():
        shutil.copy2(source_file, target_dir / "languagedata_FRE.xml")
    else:
        # Create minimal XML for environments without test123
        xml_content = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<LanguageData>\n"
            '  <LocStr StringID="TEST_001" StrOrigin="Hello" Str="" Category="SCRIPT"/>\n'
            '  <LocStr StringID="TEST_002" StrOrigin="World" Str="" Category="SCRIPT"/>\n'
            "</LanguageData>\n"
        )
        (target_dir / "languagedata_FRE.xml").write_text(xml_content, encoding="utf-8")

    return target_dir


@pytest.fixture
def merge_temp_source(tmp_path):
    """Create a temporary source directory with a corrections XML."""
    source_dir = tmp_path / "merge_source"
    source_dir.mkdir()

    xml_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<LanguageData>\n"
        '  <LocStr StringID="TEST_001" StrOrigin="Hello" Str="Bonjour" Category="SCRIPT"/>\n'
        "</LanguageData>\n"
    )
    (source_dir / "corrections_FRE.xml").write_text(xml_content, encoding="utf-8")

    return source_dir
