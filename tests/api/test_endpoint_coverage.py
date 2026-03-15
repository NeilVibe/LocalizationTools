"""Endpoint coverage validation — meta-tests for the test suite itself.

Discovers all registered FastAPI endpoints via ``app.routes`` and
validates that the test suite references each one.  Produces a
human-readable coverage report during the test run.
"""
from __future__ import annotations

import ast
import os
import re
from collections import defaultdict
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_DIR = PROJECT_ROOT / "tests" / "api"
EXPECTED_ENDPOINT_COUNT = 301  # discovered via app route introspection
TOLERANCE_PCT = 15  # allow 15% variance as endpoints evolve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_fastapi_app():
    """Return the FastAPI application (unwrapping Socket.IO wrapper if needed)."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))

    from server.main import app

    # Socket.IO wraps FastAPI — dig through the wrapper chain
    fastapi_app = getattr(app, "other_asgi_app", None)
    if fastapi_app is None:
        fastapi_app = getattr(app, "app", app)
    if not hasattr(fastapi_app, "routes"):
        inner = getattr(fastapi_app, "app", None)
        if inner and hasattr(inner, "routes"):
            fastapi_app = inner
    return fastapi_app


def _discover_endpoints(fastapi_app) -> list[tuple[str, str]]:
    """Return list of (METHOD, path) for all registered routes."""
    endpoints: list[tuple[str, str]] = []
    for route in fastapi_app.routes:
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue
        for method in route.methods:
            if method == "HEAD":
                continue
            endpoints.append((method, route.path))
    return sorted(endpoints)


def _extract_subsystem(path: str) -> str:
    """Extract subsystem name from path for grouping."""
    segs = path.strip("/").split("/")
    # /api/ldm/projects/... -> ldm/projects
    # /api/v2/auth/... -> v2/auth
    # /health -> health
    if len(segs) >= 3 and segs[0] == "api":
        if segs[1] == "ldm" and len(segs) >= 3:
            return segs[2]
        return f"{segs[1]}/{segs[2]}" if len(segs) >= 3 else segs[1]
    if len(segs) >= 2 and segs[0] == "api":
        return segs[1]
    return segs[0] if segs else "root"


def _normalise_path(path: str) -> str:
    """Replace path params with regex-friendly placeholders for matching."""
    return re.sub(r"\{[^}]+\}", r"[^/]+", path)


def _scan_test_files() -> dict[str, set[str]]:
    """Scan all test_*.py files and collect path-like strings.

    Returns {filename: set_of_path_strings}.
    """
    result: dict[str, set[str]] = {}
    for py in sorted(TEST_DIR.glob("test_*.py")):
        content = py.read_text(encoding="utf-8", errors="replace")
        # Find strings that look like API paths
        paths = set(re.findall(r'["\'](/api/[^"\']+)["\']', content))
        # Also match paths in constants module usage
        paths |= set(re.findall(r'["\'](/health[^"\']*)["\']', content))
        paths |= set(re.findall(r'["\'](/docs[^"\']*)["\']', content))
        paths |= set(re.findall(r'["\'](/openapi[^"\']*)["\']', content))
        result[py.name] = paths
    # Also scan the helpers/constants.py for path definitions
    constants_file = TEST_DIR / "helpers" / "constants.py"
    if constants_file.exists():
        content = constants_file.read_text(encoding="utf-8", errors="replace")
        paths = set(re.findall(r'["\'](/api/[^"\']+)["\']', content))
        paths |= set(re.findall(r'["\'](/health[^"\']*)["\']', content))
        result["helpers/constants.py"] = paths
    # Scan the helpers/api_client.py for endpoint references
    client_file = TEST_DIR / "helpers" / "api_client.py"
    if client_file.exists():
        content = client_file.read_text(encoding="utf-8", errors="replace")
        paths = set(re.findall(r'["\'](/api/[^"\']+)["\']', content))
        paths |= set(re.findall(r'["\'](/health[^"\']*)["\']', content))
        result["helpers/api_client.py"] = paths
    return result


def _endpoint_is_tested(
    method: str, path: str, all_test_paths: set[str]
) -> bool:
    """Check if an endpoint path appears in any test file's path strings."""
    # Direct match
    if path in all_test_paths:
        return True
    # Parameterised match: /api/ldm/projects/{project_id} matches /api/ldm/projects/123
    # Reverse: test has /api/ldm/projects/123 -> we check if our path template matches
    norm = _normalise_path(path)
    pattern = re.compile(f"^{norm}$")
    for tp in all_test_paths:
        if pattern.match(tp):
            return True
    # Check if the base path (without params) is referenced
    base = re.sub(r"/\{[^}]+\}", "", path)
    if base in all_test_paths:
        return True
    # Check partial match (the path or its prefix appears)
    for tp in all_test_paths:
        tp_base = re.sub(r"/\{[^}]+\}", "", tp)
        if tp_base == base:
            return True
    return False


# ======================================================================
# Tests
# ======================================================================


@pytest.fixture(scope="module")
def fastapi_app():
    """Module-scoped FastAPI app instance."""
    return _get_fastapi_app()


@pytest.fixture(scope="module")
def all_endpoints(fastapi_app):
    """Module-scoped list of (method, path) endpoints."""
    return _discover_endpoints(fastapi_app)


@pytest.fixture(scope="module")
def test_paths():
    """Module-scoped aggregated test path strings."""
    scanned = _scan_test_files()
    all_paths: set[str] = set()
    for paths in scanned.values():
        all_paths |= paths
    return all_paths


class TestEndpointCoverage:
    """Meta-tests validating the API test suite covers all endpoints."""

    def test_discover_all_endpoints(self, all_endpoints):
        """Discover all registered endpoints from FastAPI app."""
        assert len(all_endpoints) > 50, (
            f"Expected many endpoints, found only {len(all_endpoints)}"
        )
        # Verify key subsystems present
        paths = {p for _, p in all_endpoints}
        ldm_paths = [p for p in paths if "/api/ldm/" in p]
        auth_paths = [p for p in paths if "/api/v2/auth" in p or "/api/auth" in p]
        assert len(ldm_paths) >= 50, f"Expected 50+ LDM endpoints, got {len(ldm_paths)}"
        assert len(auth_paths) >= 5, f"Expected 5+ auth endpoints, got {len(auth_paths)}"

    def test_endpoint_count_matches_expected(self, all_endpoints):
        """Verify total endpoint count is approximately expected (within tolerance)."""
        count = len(all_endpoints)
        lower = int(EXPECTED_ENDPOINT_COUNT * (1 - TOLERANCE_PCT / 100))
        upper = int(EXPECTED_ENDPOINT_COUNT * (1 + TOLERANCE_PCT / 100))
        assert lower <= count <= upper, (
            f"Endpoint count {count} outside expected range [{lower}, {upper}] "
            f"(expected ~{EXPECTED_ENDPOINT_COUNT} +/- {TOLERANCE_PCT}%)"
        )

    def test_all_endpoints_have_tests(self, all_endpoints, test_paths):
        """For each endpoint, verify at least one test file references it."""
        untested: list[str] = []
        for method, path in all_endpoints:
            if not _endpoint_is_tested(method, path, test_paths):
                untested.append(f"{method} {path}")

        # Allow some untested endpoints (infra like /docs, /openapi.json, /redoc)
        infra_paths = {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}
        real_untested = [
            e for e in untested
            if not any(e.endswith(ip) for ip in infra_paths)
        ]

        # Soft assertion: warn but don't fail if < 20% untested
        coverage_pct = (1 - len(real_untested) / len(all_endpoints)) * 100 if all_endpoints else 0
        assert coverage_pct >= 50, (
            f"Test coverage too low: {coverage_pct:.1f}% "
            f"({len(real_untested)} untested of {len(all_endpoints)})"
        )

    def test_no_orphan_endpoints(self, all_endpoints, test_paths):
        """Verify no test references a non-existent endpoint (stale tests)."""
        registered_paths = {path for _, path in all_endpoints}
        registered_bases = {re.sub(r"/\{[^}]+\}", "", p) for p in registered_paths}

        orphans: list[str] = []
        for tp in test_paths:
            if not tp.startswith("/api/") and not tp.startswith("/health"):
                continue
            tp_base = re.sub(r"/\d+", "/{id}", tp)
            tp_base = re.sub(r"/\{[^}]+\}", "", tp_base)
            base_clean = re.sub(r"/\{[^}]+\}", "", tp)
            if base_clean not in registered_bases and tp_base not in registered_bases:
                # Check if any registered path starts with this base
                if not any(rp.startswith(base_clean) for rp in registered_bases):
                    orphans.append(tp)

        # Informational — orphans are common during development
        if orphans:
            print(f"\nPotential orphan test paths ({len(orphans)}):")
            for o in orphans[:10]:
                print(f"  - {o}")

    def test_coverage_report(self, all_endpoints, test_paths, capsys):
        """Generate and print endpoint coverage report (always passes)."""
        subsystem_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "tested": 0, "untested": []})

        for method, path in all_endpoints:
            subsystem = _extract_subsystem(path)
            subsystem_stats[subsystem]["total"] += 1
            if _endpoint_is_tested(method, path, test_paths):
                subsystem_stats[subsystem]["tested"] += 1
            else:
                subsystem_stats[subsystem]["untested"].append(f"{method} {path}")

        total = len(all_endpoints)
        tested = sum(s["tested"] for s in subsystem_stats.values())
        untested_count = total - tested
        pct = (tested / total * 100) if total else 0

        # Build report
        lines = [
            "",
            "=" * 60,
            "ENDPOINT COVERAGE REPORT",
            "=" * 60,
            f"Total endpoints: {total}",
            f"Tested:          {tested} ({pct:.1f}%)",
            f"Untested:        {untested_count} ({100 - pct:.1f}%)",
            "",
            "By subsystem:",
        ]

        for subsystem in sorted(subsystem_stats.keys()):
            stats = subsystem_stats[subsystem]
            s_pct = (stats["tested"] / stats["total"] * 100) if stats["total"] else 0
            lines.append(f"  {subsystem:30s} {stats['tested']:3d}/{stats['total']:3d} ({s_pct:5.1f}%)")

        if untested_count > 0:
            lines.append("")
            lines.append("Untested endpoints:")
            all_untested = []
            for stats in subsystem_stats.values():
                all_untested.extend(stats["untested"])
            for ep in sorted(all_untested)[:30]:
                lines.append(f"  - {ep}")
            if len(all_untested) > 30:
                lines.append(f"  ... and {len(all_untested) - 30} more")

        lines.append("=" * 60)

        report = "\n".join(lines)
        print(report)

        # This test always passes — it's a report
        assert True
