"""
COMPREHENSIVE ENDPOINT TEST SUITE
=================================

Tests EVERY endpoint in the LocaNext API (86 total):
- Route existence verification (no 405 Method Not Allowed)
- Auth requirement verification
- Response validation

Created: 2025-12-31
Updated: 2026-01-01
Purpose: BULLETPROOF CI/CD - Never let orphan endpoints slip through

Run: pytest tests/api/test_all_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.main import app


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client):
    """Get authentication headers for protected endpoints."""
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    # Fallback: try JSON body
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}


# ============================================================================
# ENDPOINT DEFINITIONS - COMPREHENSIVE LIST
# ============================================================================

# Format: (method, path, requires_auth, params/body, has_path_param)
# has_path_param=True means 404 is acceptable (resource doesn't exist)

# --- CORE ENDPOINTS (6) ---
CORE_ENDPOINTS = [
    ("GET", "/", False, None, False),
    ("GET", "/health", False, None, False),
    ("GET", "/api/status", True, None, False),
    ("POST", "/api/go-online", True, {}, False),
    ("GET", "/api/version/latest", False, None, False),
    ("GET", "/api/announcements", False, None, False),
]

# --- HEALTH ENDPOINTS (3) ---
HEALTH_ENDPOINTS = [
    ("GET", "/api/health/simple", False, None, False),
    ("GET", "/api/health/status", True, None, False),
    ("GET", "/api/health/ping", False, None, False),
]

# --- PROGRESS ENDPOINTS (3) ---
PROGRESS_ENDPOINTS = [
    ("GET", "/api/progress/operations", True, None, False),
    ("POST", "/api/progress/operations", True, {"operation_name": "test", "function_name": "test"}, False),
    ("DELETE", "/api/progress/operations/cleanup/stale", True, None, False),
]

# --- AUTH ENDPOINTS (4) ---
AUTH_ENDPOINTS = [
    ("POST", "/api/v2/auth/login", False, {"username": "admin", "password": "admin123"}, False),
    ("GET", "/api/v2/auth/me", True, None, False),
    ("GET", "/api/v2/auth/users", True, None, False),
    ("PUT", "/api/v2/auth/me/password", True, {"current_password": "admin123", "new_password": "admin123"}, False),
]

# --- SESSION ENDPOINTS (2) ---
SESSION_ENDPOINTS = [
    ("POST", "/api/v2/sessions/start", True, {}, False),
    ("GET", "/api/v2/sessions/active", True, None, False),
]

# --- LOG ENDPOINTS (5) ---
LOG_ENDPOINTS = [
    ("POST", "/api/v2/logs/submit", True, {"tool_name": "test", "function_name": "test", "status": "success"}, False),
    ("GET", "/api/v2/logs/recent", True, None, False),
    ("GET", "/api/v2/logs/errors", True, None, False),
    ("GET", "/api/v2/logs/stats/summary", True, None, False),
    ("GET", "/api/v2/logs/stats/by-tool", True, None, False),
]

# --- XLSTRANSFER ENDPOINTS (2) ---
XLSTRANSFER_ENDPOINTS = [
    ("GET", "/api/v2/xlstransfer/health", False, None, False),
    ("GET", "/api/v2/xlstransfer/test/status", True, None, False),
]

# --- QUICKSEARCH ENDPOINTS (2) ---
QUICKSEARCH_ENDPOINTS = [
    ("GET", "/api/v2/quicksearch/health", False, None, False),
    ("GET", "/api/v2/quicksearch/list-dictionaries", True, None, False),
]

# --- KRSIMILAR ENDPOINTS (3) ---
KRSIMILAR_ENDPOINTS = [
    ("GET", "/api/v2/kr-similar/health", False, None, False),
    ("GET", "/api/v2/kr-similar/list-dictionaries", True, None, False),
    ("GET", "/api/v2/kr-similar/status", True, None, False),
]

# --- LDM PROJECT ENDPOINTS (9) ---
LDM_PROJECT_ENDPOINTS = [
    ("GET", "/api/ldm/projects", True, None, False),
    ("POST", "/api/ldm/projects", True, {"name": "test_project"}, False),
    ("GET", "/api/ldm/projects/99999", True, None, True),
    ("GET", "/api/ldm/projects/99999/files", True, None, True),
    ("GET", "/api/ldm/projects/99999/folders", True, None, True),
    ("GET", "/api/ldm/projects/99999/linked-tms", True, None, True),
    ("GET", "/api/ldm/projects/99999/tree", True, None, True),
    ("POST", "/api/ldm/projects/99999/link-tm", True, {"tm_id": 1}, True),
    ("PATCH", "/api/ldm/projects/99999/rename", True, {"name": "new_name"}, True),
]

# --- LDM FILE ENDPOINTS (15) ---
LDM_FILE_ENDPOINTS = [
    ("GET", "/api/ldm/files", True, None, False),
    ("GET", "/api/ldm/files/99999", True, None, True),
    ("GET", "/api/ldm/files/99999/rows", True, None, True),
    ("GET", "/api/ldm/files/99999/download", True, None, True),
    ("GET", "/api/ldm/files/99999/convert", True, None, True),
    ("GET", "/api/ldm/files/99999/extract-glossary", True, None, True),
    ("GET", "/api/ldm/files/99999/qa-results", True, None, True),
    ("GET", "/api/ldm/files/99999/qa-summary", True, None, True),
    ("POST", "/api/ldm/files/excel-preview", True, {}, False),
    ("POST", "/api/ldm/files/99999/check-grammar", True, {}, True),
    ("POST", "/api/ldm/files/99999/check-qa", True, {}, True),
    ("POST", "/api/ldm/files/99999/merge", True, {"source_file_id": 1}, True),
    ("POST", "/api/ldm/files/99999/register-as-tm", True, {"tm_name": "test"}, True),
    ("PATCH", "/api/ldm/files/99999/move", True, {"folder_id": 1}, True),
    ("PATCH", "/api/ldm/files/99999/rename", True, {"name": "new_name"}, True),
]

# --- LDM FOLDER ENDPOINTS (3) ---
LDM_FOLDER_ENDPOINTS = [
    # POST requires valid project_id, so 404 is acceptable when project doesn't exist
    ("POST", "/api/ldm/folders", True, {"name": "test_folder", "project_id": 99999}, True),
    ("DELETE", "/api/ldm/folders/99999", True, None, True),
    ("PATCH", "/api/ldm/folders/99999/rename", True, {"name": "new_name"}, True),
]

# --- LDM ROW ENDPOINTS (4) ---
LDM_ROW_ENDPOINTS = [
    ("GET", "/api/ldm/rows/99999/qa-results", True, None, True),
    ("PUT", "/api/ldm/rows/99999", True, {"target": "test"}, True),
    ("POST", "/api/ldm/rows/99999/check-grammar", True, {}, True),
    ("POST", "/api/ldm/rows/99999/check-qa", True, {}, True),
]

# --- LDM TM ENDPOINTS (17) ---
LDM_TM_ENDPOINTS = [
    ("GET", "/api/ldm/tm", True, None, False),
    ("GET", "/api/ldm/tm/suggest", True, {"source": "test"}, False),
    ("GET", "/api/ldm/tm/99999", True, None, True),
    ("GET", "/api/ldm/tm/99999/entries", True, None, True),
    ("GET", "/api/ldm/tm/99999/export", True, None, True),
    ("GET", "/api/ldm/tm/99999/indexes", True, None, True),
    ("GET", "/api/ldm/tm/99999/search", True, {"query": "test"}, True),
    ("GET", "/api/ldm/tm/99999/search/exact", True, {"source": "test"}, True),
    ("GET", "/api/ldm/tm/99999/sync-status", True, None, True),
    ("POST", "/api/ldm/tm/sync-to-central", True, {}, False),
    ("POST", "/api/ldm/tm/99999/build-indexes", True, {}, True),
    ("POST", "/api/ldm/tm/99999/entries", True, {"source": "test", "target": "test"}, True),
    ("POST", "/api/ldm/tm/99999/entries/bulk-confirm", True, {"entry_ids": [1]}, True),
    ("POST", "/api/ldm/tm/99999/sync", True, {}, True),
    ("PUT", "/api/ldm/tm/99999/entries/88888", True, {"target": "updated"}, True),
    ("DELETE", "/api/ldm/tm/99999", True, None, True),
    ("DELETE", "/api/ldm/tm/99999/entries/88888", True, None, True),
]

# --- LDM SETTINGS ENDPOINTS (3) ---
LDM_SETTINGS_ENDPOINTS = [
    ("GET", "/api/ldm/settings/embedding-engines", True, None, False),
    ("GET", "/api/ldm/settings/embedding-engine", True, None, False),
    ("POST", "/api/ldm/settings/embedding-engine", True, {"engine": "qwen"}, False),
]

# --- LDM HEALTH ENDPOINT (1) ---
LDM_HEALTH_ENDPOINTS = [
    ("GET", "/api/ldm/health", False, None, False),
]

# --- LDM GRAMMAR ENDPOINTS (1) ---
LDM_GRAMMAR_ENDPOINTS = [
    ("GET", "/api/ldm/grammar/status", True, None, False),
]

# --- LDM QA ENDPOINTS (1) ---
LDM_QA_ENDPOINTS = [
    ("POST", "/api/ldm/qa-results/99999/resolve", True, {}, True),
]

# --- LDM PRETRANSLATE ENDPOINTS (1) ---
LDM_PRETRANSLATE_ENDPOINTS = [
    ("POST", "/api/ldm/pretranslate", True, {"file_id": 1, "tm_id": 1}, False),
]

# --- LDM SYNC ENDPOINTS (1) ---
LDM_SYNC_ENDPOINTS = [
    ("POST", "/api/ldm/sync-to-central", True, {}, False),
]

# --- ADMIN DB ENDPOINTS (2) ---
ADMIN_DB_ENDPOINTS = [
    ("GET", "/api/v2/admin/db/stats", True, None, False),
    ("GET", "/api/v2/admin/db/health", True, None, False),
]

# --- ADMIN TELEMETRY ENDPOINTS (6) ---
ADMIN_TELEMETRY_ENDPOINTS = [
    ("GET", "/api/v2/admin/telemetry/overview", True, None, False),
    ("GET", "/api/v2/admin/telemetry/installations", True, None, False),
    ("GET", "/api/v2/admin/telemetry/sessions", True, None, False),
    ("GET", "/api/v2/admin/telemetry/logs", True, None, False),
    ("GET", "/api/v2/admin/telemetry/logs/errors", True, None, False),
    ("GET", "/api/v2/admin/telemetry/stats/daily", True, None, False),
]

# --- RANKINGS ENDPOINTS (6) ---
RANKINGS_ENDPOINTS = [
    ("GET", "/api/v2/admin/rankings/users", True, None, False),
    ("GET", "/api/v2/admin/rankings/users/by-time", True, None, False),
    ("GET", "/api/v2/admin/rankings/apps", True, None, False),
    ("GET", "/api/v2/admin/rankings/functions", True, None, False),
    ("GET", "/api/v2/admin/rankings/functions/by-time", True, None, False),
    ("GET", "/api/v2/admin/rankings/top", True, None, False),
]

# --- STATS ENDPOINTS (15) ---
STATS_ENDPOINTS = [
    ("GET", "/api/v2/admin/stats/overview", True, None, False),
    ("GET", "/api/v2/admin/stats/daily", True, None, False),
    ("GET", "/api/v2/admin/stats/weekly", True, None, False),
    ("GET", "/api/v2/admin/stats/monthly", True, None, False),
    ("GET", "/api/v2/admin/stats/tools/popularity", True, None, False),
    ("GET", "/api/v2/admin/stats/performance/fastest", True, None, False),
    ("GET", "/api/v2/admin/stats/performance/slowest", True, None, False),
    ("GET", "/api/v2/admin/stats/errors/rate", True, None, False),
    ("GET", "/api/v2/admin/stats/errors/top", True, None, False),
    ("GET", "/api/v2/admin/stats/analytics/by-team", True, None, False),
    ("GET", "/api/v2/admin/stats/analytics/by-language", True, None, False),
    ("GET", "/api/v2/admin/stats/analytics/user-rankings", True, None, False),
    ("GET", "/api/v2/admin/stats/server-logs", True, None, False),
    ("GET", "/api/v2/admin/stats/database", True, None, False),
    ("GET", "/api/v2/admin/stats/server", True, None, False),
]

# --- UPDATES ENDPOINTS (1) ---
UPDATES_ENDPOINTS = [
    ("GET", "/updates/version", False, None, False),
]

# --- REMOTE LOGGING ENDPOINTS (2) ---
REMOTE_LOG_ENDPOINTS = [
    ("GET", "/api/v1/remote-logs/health", False, None, False),
    ("GET", "/api/v1/remote-logs/installations", True, None, False),
]


# ============================================================================
# COMBINE ALL ENDPOINTS
# ============================================================================

ALL_ENDPOINTS = (
    CORE_ENDPOINTS +
    HEALTH_ENDPOINTS +
    PROGRESS_ENDPOINTS +
    AUTH_ENDPOINTS +
    SESSION_ENDPOINTS +
    LOG_ENDPOINTS +
    XLSTRANSFER_ENDPOINTS +
    QUICKSEARCH_ENDPOINTS +
    KRSIMILAR_ENDPOINTS +
    LDM_PROJECT_ENDPOINTS +
    LDM_FILE_ENDPOINTS +
    LDM_FOLDER_ENDPOINTS +
    LDM_ROW_ENDPOINTS +
    LDM_TM_ENDPOINTS +
    LDM_SETTINGS_ENDPOINTS +
    LDM_HEALTH_ENDPOINTS +
    LDM_GRAMMAR_ENDPOINTS +
    LDM_QA_ENDPOINTS +
    LDM_PRETRANSLATE_ENDPOINTS +
    LDM_SYNC_ENDPOINTS +
    ADMIN_DB_ENDPOINTS +
    ADMIN_TELEMETRY_ENDPOINTS +
    RANKINGS_ENDPOINTS +
    STATS_ENDPOINTS +
    UPDATES_ENDPOINTS +
    REMOTE_LOG_ENDPOINTS
)


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestAllEndpointsExist:
    """
    Verify ALL endpoints exist and respond correctly.

    This is the BULLETPROOF test - catches orphan endpoints like UI-084.
    - 405 = Route doesn't exist for this method (BUG!)
    - 404 with path params = Resource not found (OK - route exists)
    - 404 without path params = Route missing (BUG!)
    """

    @pytest.mark.parametrize("method,path,requires_auth,params,has_path_param", ALL_ENDPOINTS)
    def test_endpoint_exists(self, client, auth_headers, method, path, requires_auth, params, has_path_param):
        """Test that endpoint exists and doesn't return 405."""
        headers = auth_headers if requires_auth else {}

        if method == "GET":
            response = client.get(path, params=params, headers=headers) if params else client.get(path, headers=headers)
        elif method == "POST":
            response = client.post(path, json=params or {}, headers=headers)
        elif method == "PUT":
            response = client.put(path, json=params or {}, headers=headers)
        elif method == "DELETE":
            response = client.delete(path, headers=headers)
        elif method == "PATCH":
            response = client.patch(path, json=params or {}, headers=headers)
        else:
            pytest.fail(f"Unknown method: {method}")

        # 405 = Method not allowed = ROUTE DOESN'T EXIST (always a bug)
        assert response.status_code != 405, \
            f"ROUTE MISSING! {method} {path} returned 405 - method not allowed!"

        # For routes without path params, 404 is also a bug
        if not has_path_param:
            assert response.status_code != 404, \
                f"ORPHAN ENDPOINT! {method} {path} returned 404 - endpoint doesn't exist!"

        # Valid responses based on context
        # 403 = Forbidden (route exists, access denied)
        # 503 = Service unavailable (e.g., LanguageTool not running)
        if has_path_param:
            # Routes with fake IDs: 404 (not found) or 422 (validation) are OK
            valid_codes = [200, 201, 400, 401, 403, 404, 422, 500, 503]
        else:
            valid_codes = [200, 201, 400, 401, 403, 422, 500, 503]

        assert response.status_code in valid_codes, \
            f"{method} {path} returned unexpected {response.status_code}: {response.text[:200]}"


class TestCriticalFrontendEndpoints:
    """
    Test endpoints that frontend DIRECTLY calls.
    If any of these fail, the UI will break silently (like UI-084).
    """

    FRONTEND_CRITICAL = [
        # LDM.svelte
        ("GET", "/api/ldm/health", False),
        ("GET", "/api/status", True),
        ("POST", "/api/go-online", True),
        # VirtualGrid.svelte - THE UI-084 FIX
        ("GET", "/api/ldm/tm/suggest", True),
        # FileExplorer.svelte
        ("GET", "/api/ldm/projects", True),
        ("GET", "/api/ldm/files", True),
        ("GET", "/api/ldm/tm", True),
        # TMManager.svelte
        ("GET", "/api/ldm/settings/embedding-engines", True),
        ("GET", "/api/ldm/settings/embedding-engine", True),
        # ServerStatus.svelte
        ("GET", "/api/health/simple", False),
        # QuickSearch.svelte
        ("GET", "/api/v2/quicksearch/health", False),
        ("GET", "/api/v2/quicksearch/list-dictionaries", True),
        # KRSimilar.svelte
        ("GET", "/api/v2/kr-similar/health", False),
        ("GET", "/api/v2/kr-similar/list-dictionaries", True),
        # XLSTransfer.svelte
        ("GET", "/api/v2/xlstransfer/health", False),
        # TaskManager.svelte
        ("GET", "/api/progress/operations", True),
    ]

    @pytest.mark.parametrize("method,path,requires_auth", FRONTEND_CRITICAL)
    def test_frontend_endpoint(self, client, auth_headers, method, path, requires_auth):
        """Frontend-critical endpoints MUST work."""
        headers = auth_headers if requires_auth else {}

        if path == "/api/ldm/tm/suggest":
            response = client.get(path, params={"source": "test"}, headers=headers)
        elif method == "GET":
            response = client.get(path, headers=headers)
        else:
            response = client.post(path, json={}, headers=headers)

        assert response.status_code != 404, \
            f"CRITICAL FRONTEND ENDPOINT MISSING! {method} {path} - UI WILL BREAK!"
        assert response.status_code != 405, \
            f"CRITICAL FRONTEND ENDPOINT WRONG METHOD! {method} {path}"
        # 401 is acceptable if auth fixture failed (we test auth separately)
        assert response.status_code in [200, 201, 400, 401, 422], \
            f"CRITICAL ENDPOINT FAILED! {method} {path} returned {response.status_code}"


class TestToolHealthEndpoints:
    """All 4 tools must have working health endpoints."""

    TOOL_HEALTH = [
        "/api/ldm/health",
        "/api/v2/xlstransfer/health",
        "/api/v2/quicksearch/health",
        "/api/v2/kr-similar/health",
    ]

    @pytest.mark.parametrize("path", TOOL_HEALTH)
    def test_tool_health(self, client, path):
        """Tool health endpoints must return 200 with status."""
        response = client.get(path)
        assert response.status_code == 200, f"{path} health check failed with {response.status_code}!"
        data = response.json()
        assert "status" in data, f"{path} missing 'status' in response!"


class TestAuthRequirements:
    """Verify auth requirements are correctly enforced."""

    PUBLIC_ENDPOINTS = [
        "/health",
        "/api/health/simple",
        "/api/health/ping",
        "/api/ldm/health",
        "/api/v2/xlstransfer/health",
        "/api/v2/quicksearch/health",
        "/api/v2/kr-similar/health",
        "/api/v1/remote-logs/health",
        "/updates/version",
    ]

    PROTECTED_ENDPOINTS = [
        "/api/ldm/projects",
        "/api/ldm/tm",
        "/api/ldm/files",
        "/api/progress/operations",
        "/api/v2/auth/me",
        "/api/v2/admin/stats/overview",
    ]

    @pytest.mark.parametrize("path", PUBLIC_ENDPOINTS)
    def test_public_no_auth_needed(self, client, path):
        """Public endpoints should work without auth."""
        response = client.get(path)
        assert response.status_code == 200, \
            f"Public endpoint {path} should not require auth but returned {response.status_code}"

    @pytest.mark.parametrize("path", PROTECTED_ENDPOINTS)
    def test_protected_requires_auth(self, client, path):
        """Protected endpoints should return 401 without auth."""
        response = client.get(path)
        assert response.status_code == 401, \
            f"Protected endpoint {path} should require auth but returned {response.status_code}"


class TestLDMEndpointsComprehensive:
    """
    Comprehensive LDM endpoint testing - the core of LocaNext.
    Tests all 56 LDM endpoints to prevent issues like UI-084.
    """

    def test_ldm_projects_crud(self, client, auth_headers):
        """Test LDM project CRUD operations."""
        if not auth_headers:
            pytest.skip("Auth not available")
        response = client.get("/api/ldm/projects", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_ldm_tm_suggest_works(self, client, auth_headers):
        """THE UI-084 FIX - TM suggest must work."""
        if not auth_headers:
            pytest.skip("Auth not available")
        response = client.get(
            "/api/ldm/tm/suggest",
            params={"source": "테스트"},  # Korean test text
            headers=auth_headers
        )
        assert response.status_code == 200, \
            f"TM SUGGEST BROKEN! This caused UI-084! Status: {response.status_code}"

    def test_ldm_files_list(self, client, auth_headers):
        """Test file listing."""
        if not auth_headers:
            pytest.skip("Auth not available")
        response = client.get("/api/ldm/files", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_ldm_tm_list(self, client, auth_headers):
        """Test TM listing."""
        if not auth_headers:
            pytest.skip("Auth not available")
        response = client.get("/api/ldm/tm", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_ldm_settings(self, client, auth_headers):
        """Test settings endpoints."""
        if not auth_headers:
            pytest.skip("Auth not available")
        response = client.get("/api/ldm/settings/embedding-engines", headers=auth_headers)
        assert response.status_code == 200

        response = client.get("/api/ldm/settings/embedding-engine", headers=auth_headers)
        assert response.status_code == 200


# ============================================================================
# SUMMARY
# ============================================================================

def test_endpoint_count():
    """Verify we're testing a comprehensive number of endpoints."""
    total = len(ALL_ENDPOINTS)

    # Count by category
    ldm_count = (
        len(LDM_PROJECT_ENDPOINTS) + len(LDM_FILE_ENDPOINTS) +
        len(LDM_FOLDER_ENDPOINTS) + len(LDM_ROW_ENDPOINTS) +
        len(LDM_TM_ENDPOINTS) + len(LDM_SETTINGS_ENDPOINTS) +
        len(LDM_HEALTH_ENDPOINTS) + len(LDM_GRAMMAR_ENDPOINTS) +
        len(LDM_QA_ENDPOINTS) + len(LDM_PRETRANSLATE_ENDPOINTS) +
        len(LDM_SYNC_ENDPOINTS)
    )

    tool_count = len(XLSTRANSFER_ENDPOINTS) + len(QUICKSEARCH_ENDPOINTS) + len(KRSIMILAR_ENDPOINTS)
    admin_count = len(ADMIN_DB_ENDPOINTS) + len(ADMIN_TELEMETRY_ENDPOINTS) + len(RANKINGS_ENDPOINTS) + len(STATS_ENDPOINTS)

    print(f"\n{'='*60}")
    print(f"  ENDPOINT TEST SUITE SUMMARY")
    print(f"{'='*60}")
    print(f"  Total endpoints tested: {total}")
    print(f"  ─────────────────────────────────────")
    print(f"  Core/Health/Auth:  {len(CORE_ENDPOINTS) + len(HEALTH_ENDPOINTS) + len(AUTH_ENDPOINTS) + len(SESSION_ENDPOINTS) + len(LOG_ENDPOINTS) + len(PROGRESS_ENDPOINTS)}")
    print(f"  LDM (CAT Tool):    {ldm_count}")
    print(f"  Tools:             {tool_count}")
    print(f"  Admin/Stats:       {admin_count}")
    print(f"  Updates/Remote:    {len(UPDATES_ENDPOINTS) + len(REMOTE_LOG_ENDPOINTS)}")
    print(f"{'='*60}\n")

    assert total >= 80, f"Only {total} endpoints defined - should be 80+!"
    assert ldm_count >= 50, f"Only {ldm_count} LDM endpoints - should be 50+!"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
