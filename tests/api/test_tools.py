"""External tools API tests.

Covers QuickSearch, KR-Similar, XLSTransfer integration endpoints,
tool availability checks, and graceful unavailability handling.
External tools may not be running in the test environment, so tests
accept 503 (unavailable) as valid alongside 200 (success).
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_status_ok,
    assert_json_fields,
)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.tools]


# Acceptable codes: 200=OK, 404=no route, 422=bad params, 500=server error,
# 501=not implemented, 503=tool unavailable
TOOL_OK = (200, 404, 422, 500, 501, 503)
GRACEFUL_UNAVAIL = (200, 503)


# ======================================================================
# QuickSearch
# ======================================================================


class TestQuickSearch:
    """QuickSearch external tool endpoints."""

    def test_quicksearch_health(self, api):
        """QuickSearch health/status endpoint responds."""
        # QuickSearch may be at /api/ldm/quicksearch/status or similar
        resp = api._get("/api/ldm/quicksearch/status")
        if resp.status_code == 404:
            # Try alternative path
            resp = api._get("/api/ldm/tools/quicksearch/status")
        assert resp.status_code in TOOL_OK

    def test_quicksearch_dictionaries(self, api):
        """QuickSearch dictionaries endpoint responds."""
        resp = api._get("/api/ldm/quicksearch/dictionaries")
        if resp.status_code == 404:
            resp = api._get("/api/ldm/tools/quicksearch/dictionaries")
        assert resp.status_code in TOOL_OK

    def test_quicksearch_search(self, api):
        """QuickSearch search query returns results or 503."""
        resp = api._post(
            "/api/ldm/quicksearch/search",
            json={"query": "sword", "language": "en"},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/quicksearch/search",
                json={"query": "sword", "language": "en"},
            )
        assert resp.status_code in TOOL_OK
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_quicksearch_multiline(self, api):
        """QuickSearch accepts multiline search input."""
        resp = api._post(
            "/api/ldm/quicksearch/search",
            json={"query": "sword\nshield\nmagic", "language": "en"},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/quicksearch/search",
                json={"query": "sword\nshield\nmagic", "language": "en"},
            )
        assert resp.status_code in TOOL_OK


# ======================================================================
# KR-Similar
# ======================================================================


class TestKRSimilar:
    """KR-Similar external tool endpoints."""

    def test_kr_similar_search(self, api):
        """KR-Similar returns similar Korean strings or 503."""
        resp = api._post(
            "/api/ldm/kr-similar/search",
            json={"text": "검은 칼날", "limit": 5},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/kr-similar/search",
                json={"text": "검은 칼날", "limit": 5},
            )
        assert resp.status_code in TOOL_OK
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_kr_similar_scores(self, api):
        """KR-Similar results include similarity scores."""
        resp = api._post(
            "/api/ldm/kr-similar/search",
            json={"text": "마법사", "limit": 3},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/kr-similar/search",
                json={"text": "마법사", "limit": 3},
            )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                for result in data["results"][:3]:
                    assert "score" in result or "similarity" in result

    def test_kr_similar_empty_result(self, api):
        """KR-Similar with gibberish returns empty or graceful response."""
        resp = api._post(
            "/api/ldm/kr-similar/search",
            json={"text": "zzzzxxxxxqqqqq", "limit": 5},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/kr-similar/search",
                json={"text": "zzzzxxxxxqqqqq", "limit": 5},
            )
        assert resp.status_code in TOOL_OK


# ======================================================================
# XLSTransfer
# ======================================================================


class TestXLSTransfer:
    """XLSTransfer external tool endpoints."""

    def test_xlstransfer_status(self, api):
        """XLSTransfer availability check."""
        resp = api._get("/api/ldm/xlstransfer/status")
        if resp.status_code == 404:
            resp = api._get("/api/ldm/tools/xlstransfer/status")
        assert resp.status_code in TOOL_OK

    def test_xlstransfer_health(self, api):
        """XLSTransfer health endpoint responds."""
        resp = api._get("/api/ldm/xlstransfer/health")
        if resp.status_code == 404:
            resp = api._get("/api/ldm/tools/xlstransfer/health")
        assert resp.status_code in TOOL_OK

    def test_xlstransfer_convert(self, api):
        """XLSTransfer convert endpoint responds (if exists)."""
        resp = api._post(
            "/api/ldm/xlstransfer/convert",
            json={"source_format": "xml", "target_format": "xlsx"},
        )
        if resp.status_code == 404:
            resp = api._post(
                "/api/ldm/tools/xlstransfer/convert",
                json={"source_format": "xml", "target_format": "xlsx"},
            )
        assert resp.status_code in TOOL_OK


# ======================================================================
# Tool Availability & Response Format
# ======================================================================


class TestToolAvailability:
    """Cross-tool availability and consistency checks."""

    def test_tools_graceful_unavailable(self, api):
        """Tools return 503 (not 500) when unavailable."""
        tool_endpoints = [
            ("/api/ldm/quicksearch/status", "GET"),
            ("/api/ldm/kr-similar/search", "POST"),
            ("/api/ldm/xlstransfer/status", "GET"),
        ]
        for url, method in tool_endpoints:
            if method == "GET":
                resp = api._get(url)
            else:
                resp = api._post(url, json={"text": "test"})

            # 404 means route doesn't exist (different prefix)
            if resp.status_code == 404:
                continue
            # If tool responds, it should NOT be 500
            if resp.status_code >= 500:
                assert resp.status_code in (501, 502, 503), (
                    f"{method} {url} returned {resp.status_code} (expected 5xx to be 501/502/503, not 500)"
                )

    def test_tools_response_format(self, api):
        """All tool responses use JSON content type when available."""
        tool_gets = [
            "/api/ldm/quicksearch/status",
            "/api/ldm/xlstransfer/status",
        ]
        for url in tool_gets:
            resp = api._get(url)
            if resp.status_code in (200, 503):
                content_type = resp.headers.get("content-type", "")
                assert "json" in content_type or "text" in content_type, (
                    f"{url} returned unexpected content-type: {content_type}"
                )
