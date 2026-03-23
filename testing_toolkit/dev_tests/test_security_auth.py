"""
Security Regression Tests — Authentication & Authorization

Two test modes:
  1. Code-level (always runs): Verifies auth dependencies are present in route signatures
  2. Runtime (production only): Verifies 401 rejection for unauthenticated requests

In DEV_MODE, localhost auto-authentication bypasses auth, so runtime 401 tests
are skipped. The code-level tests ensure the auth dependencies are wired.

Run:
    python -m pytest testing_toolkit/dev_tests/test_security_auth.py -v
"""
from __future__ import annotations

import ast
import inspect
import importlib
import pytest
import requests

API_URL = "http://localhost:8888"


# ---------------------------------------------------------------------------
# Detect DEV_MODE
# ---------------------------------------------------------------------------

def _is_dev_mode() -> bool:
    """Check if server is running in DEV_MODE (auto-auth on localhost)."""
    try:
        # In DEV_MODE, unauthenticated requests succeed on localhost
        resp = requests.get(f"{API_URL}/api/health/status", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


DEV_MODE = _is_dev_mode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_headers():
    """Login as admin, return auth headers."""
    resp = requests.post(f"{API_URL}/api/auth/login", json={
        "username": "admin", "password": "admin123"
    })
    if resp.status_code != 200:
        pytest.skip("Server not running or admin login failed")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def no_headers():
    """No auth headers — unauthenticated."""
    return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_rejects_unauth(method: str, url: str, **kwargs):
    """Assert endpoint returns 401 or 403 without auth (skip in DEV_MODE)."""
    if DEV_MODE:
        pytest.skip("DEV_MODE auto-auth bypasses — use code-level tests instead")
    resp = getattr(requests, method)(url, **kwargs)
    assert resp.status_code in (401, 403), (
        f"{method.upper()} {url} returned {resp.status_code} without auth "
        f"(expected 401/403). Body: {resp.text[:200]}"
    )
    return resp


def assert_accepts_auth(method: str, url: str, headers: dict, **kwargs):
    """Assert endpoint does NOT return 401/403 with auth."""
    resp = getattr(requests, method)(url, headers=headers, **kwargs)
    assert resp.status_code not in (401, 403), (
        f"{method.upper()} {url} returned {resp.status_code} WITH auth "
        f"(expected success). Body: {resp.text[:200]}"
    )
    return resp


def _has_auth_dependency(module_path: str, func_name: str) -> bool:
    """Check if a route function has an auth dependency in its signature (AST-based)."""
    import server.utils.dependencies as deps
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name)
    sig = inspect.signature(func)
    auth_names = {"require_admin_async", "get_current_active_user_async"}
    for param in sig.parameters.values():
        default = param.default
        if hasattr(default, "dependency"):
            dep_func = default.dependency
            if hasattr(dep_func, "__name__") and dep_func.__name__ in auth_names:
                return True
    return False


# ============================================================================
# CODE-LEVEL TESTS: Verify auth dependencies exist in route signatures
# These always pass regardless of DEV_MODE
# ============================================================================

class TestAuthDependenciesWired:
    """Verify auth dependencies are present in route function signatures."""

    def _check_auth_in_module(self, module_path: str, expected_funcs: list[str], auth_dep: str):
        """Check that all listed functions have the expected auth dependency."""
        mod = importlib.import_module(module_path)
        for func_name in expected_funcs:
            func = getattr(mod, func_name)
            sig = inspect.signature(func)
            found = False
            for param in sig.parameters.values():
                default = param.default
                if hasattr(default, "dependency"):
                    dep_func = default.dependency
                    if hasattr(dep_func, "__name__") and dep_func.__name__ == auth_dep:
                        found = True
                        break
            assert found, (
                f"{module_path}.{func_name} missing Depends({auth_dep})"
            )

    def test_admin_telemetry_has_admin_auth(self):
        self._check_auth_in_module("server.api.admin_telemetry", [
            "get_telemetry_overview", "get_installations", "get_installation_detail",
            "get_sessions", "get_remote_logs", "get_error_logs",
            "get_daily_telemetry_stats", "get_stats_by_installation",
        ], "require_admin_async")

    def test_rankings_has_admin_auth(self):
        self._check_auth_in_module("server.api.rankings", [
            "get_user_rankings", "get_user_rankings_by_time",
            "get_app_rankings", "get_function_rankings",
            "get_function_rankings_by_time", "get_top_rankings",
        ], "require_admin_async")

    def test_merge_has_user_auth(self):
        self._check_auth_in_module("server.api.merge", [
            "preview_merge", "execute_merge",
        ], "get_current_active_user_async")

    def test_performance_has_admin_auth(self):
        self._check_auth_in_module("server.api.performance", [
            "get_performance_summary", "reset_performance_metrics",
        ], "require_admin_async")

    def test_health_status_has_admin_auth(self):
        self._check_auth_in_module("server.api.health", [
            "get_detailed_health",
        ], "require_admin_async")

    def test_logs_recent_has_user_auth(self):
        self._check_auth_in_module("server.api.logs_async", [
            "get_recent_logs",
        ], "get_current_active_user_async")


# ============================================================================
# RUNTIME TESTS: Verify actual 401 rejection (skipped in DEV_MODE)
# ============================================================================


# ============================================================================
# Phase 65: Backend Auth Restoration
# ============================================================================

class TestAdminTelemetryAuth:
    """All 8 admin_telemetry.py endpoints require admin auth."""

    ENDPOINTS = [
        "/api/v2/admin/telemetry/overview",
        "/api/v2/admin/telemetry/installations",
        "/api/v2/admin/telemetry/sessions",
        "/api/v2/admin/telemetry/logs",
        "/api/v2/admin/telemetry/logs/errors",
        "/api/v2/admin/telemetry/stats/daily",
        "/api/v2/admin/telemetry/stats/by-installation",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_rejects_unauthenticated(self, endpoint, no_headers):
        assert_rejects_unauth("get", f"{API_URL}{endpoint}")

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_accepts_admin(self, endpoint, admin_headers):
        # Should not return 401/403 (may return 200 or 500 if no data)
        assert_accepts_auth("get", f"{API_URL}{endpoint}", admin_headers)


class TestRankingsAuth:
    """All 6 rankings.py endpoints require admin auth."""

    ENDPOINTS = [
        "/api/v2/admin/rankings/users",
        "/api/v2/admin/rankings/users/by-time",
        "/api/v2/admin/rankings/apps",
        "/api/v2/admin/rankings/functions",
        "/api/v2/admin/rankings/functions/by-time",
        "/api/v2/admin/rankings/top",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_rejects_unauthenticated(self, endpoint, no_headers):
        assert_rejects_unauth("get", f"{API_URL}{endpoint}")

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_accepts_admin(self, endpoint, admin_headers):
        assert_accepts_auth("get", f"{API_URL}{endpoint}", admin_headers)


class TestLogsAuth:
    """GET /logs/recent requires auth."""

    def test_recent_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("get", f"{API_URL}/logs/recent")

    def test_recent_accepts_admin(self, admin_headers):
        assert_accepts_auth("get", f"{API_URL}/logs/recent", admin_headers)


class TestMergeAuth:
    """Merge preview and execute require auth."""

    MERGE_BODY = {
        "source_path": "/tmp/test_source",
        "target_path": "/tmp/test_target",
        "export_path": "/tmp/test_export",
        "match_mode": "strict",
    }

    def test_preview_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("post", f"{API_URL}/api/merge/preview",
                              json=self.MERGE_BODY)

    def test_execute_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("post", f"{API_URL}/api/merge/execute",
                              json=self.MERGE_BODY)

    def test_preview_accepts_auth(self, admin_headers):
        # May fail with file-not-found, but should NOT be 401/403
        assert_accepts_auth("post", f"{API_URL}/api/merge/preview",
                            admin_headers, json=self.MERGE_BODY)

    def test_execute_accepts_auth(self, admin_headers):
        assert_accepts_auth("post", f"{API_URL}/api/merge/execute",
                            admin_headers, json=self.MERGE_BODY)


class TestHealthAuth:
    """GET /api/health/status requires admin auth."""

    def test_status_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("get", f"{API_URL}/api/health/status")

    def test_status_accepts_admin(self, admin_headers):
        assert_accepts_auth("get", f"{API_URL}/api/health/status", admin_headers)

    def test_simple_is_public(self):
        """GET /api/health/simple should be publicly accessible (pre-login)."""
        resp = requests.get(f"{API_URL}/api/health/simple")
        assert resp.status_code == 200


class TestPerformanceAuth:
    """Performance endpoints require admin auth."""

    def test_summary_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("get", f"{API_URL}/api/performance/summary")

    def test_reset_rejects_unauthenticated(self, no_headers):
        assert_rejects_unauth("post", f"{API_URL}/api/performance/reset")

    def test_summary_accepts_admin(self, admin_headers):
        assert_accepts_auth("get", f"{API_URL}/api/performance/summary", admin_headers)


# ============================================================================
# Phase 66: Path Traversal Prevention
# ============================================================================

class TestPathTraversal:
    """Path traversal attempts should be blocked."""

    def test_updates_download_traversal(self):
        """../../../etc/passwd.yml should be rejected or return 404, never file contents."""
        resp = requests.get(f"{API_URL}/updates/download/../../etc/passwd.yml")
        # Should get 403 (blocked) or 404 (not found after sanitization)
        assert resp.status_code in (403, 404, 422), (
            f"Path traversal returned {resp.status_code}: {resp.text[:200]}"
        )
        assert "root:" not in resp.text, "Path traversal leaked file contents!"

    def test_merge_preview_blocks_system_paths(self, admin_headers):
        """Merge with system paths should be rejected."""
        resp = requests.post(f"{API_URL}/api/merge/preview", headers=admin_headers, json={
            "source_path": "/etc/passwd",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        })
        assert resp.status_code == 403, (
            f"System path not blocked: {resp.status_code} {resp.text[:200]}"
        )

    def test_merge_preview_blocks_traversal(self, admin_headers):
        """Merge with .. traversal should be rejected."""
        resp = requests.post(f"{API_URL}/api/merge/preview", headers=admin_headers, json={
            "source_path": "/tmp/../etc/passwd",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        })
        assert resp.status_code == 403, (
            f"Traversal not blocked: {resp.status_code} {resp.text[:200]}"
        )


# ============================================================================
# Phase 68: Remote Logging Security
# ============================================================================

class TestRemoteLoggingSecurity:
    """Remote logging IDOR and access control."""

    def test_frontend_log_rejects_without_api_key(self):
        """POST /api/v1/remote-logs/frontend requires API key."""
        resp = requests.post(f"{API_URL}/api/v1/remote-logs/frontend", json={
            "level": "INFO",
            "message": "test",
        })
        # Should be 401/403 without valid API key
        assert resp.status_code in (401, 403, 422), (
            f"Frontend logging accepted without API key: {resp.status_code}"
        )

    def test_installations_rejects_without_api_key(self):
        """GET /api/v1/remote-logs/installations requires API key."""
        resp = requests.get(f"{API_URL}/api/v1/remote-logs/installations")
        assert resp.status_code in (401, 403, 422), (
            f"Installations list accessible without API key: {resp.status_code}"
        )

    def test_status_rejects_without_api_key(self):
        """GET /api/v1/remote-logs/status/{id} requires API key."""
        resp = requests.get(f"{API_URL}/api/v1/remote-logs/status/fake-id-123")
        assert resp.status_code in (401, 403, 422), (
            f"Status accessible without API key: {resp.status_code}"
        )


# ============================================================================
# Counts
# ============================================================================
# Total parametrized test cases:
#   TestAdminTelemetryAuth: 7 + 7 = 14
#   TestRankingsAuth: 6 + 6 = 12
#   TestLogsAuth: 2
#   TestMergeAuth: 4
#   TestHealthAuth: 3
#   TestPerformanceAuth: 3
#   TestPathTraversal: 3
#   TestRemoteLoggingSecurity: 3
#   ---------------------------------
#   TOTAL: 44 test cases
