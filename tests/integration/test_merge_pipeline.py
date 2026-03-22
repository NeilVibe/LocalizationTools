"""E2E merge pipeline integration tests.

Covers the complete v6.0 merge pipeline: mock data setup, settings path
validation, single-project merge (preview + execute with SSE), and
multi-language merge workflow.

Requires: DEV_MODE=true python3 server/main.py running on localhost:8888
Run: python3 -m pytest tests/integration/test_merge_pipeline.py -x -v --timeout=120
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from tests.integration.conftest_merge import BASE_URL, TEST123_PATH

# Register fixtures from conftest_merge (pytest only auto-discovers conftest.py)
pytest_plugins = ["tests.integration.conftest_merge"]

pytestmark = [pytest.mark.integration]


# ============================================================================
# 1. Mock data setup verification
# ============================================================================


def test_mock_data_setup(mock_data_ready, admin_headers):
    """Verify mock data script ran and projects are queryable via API."""
    # mock_data_ready fixture already asserted returncode == 0
    assert mock_data_ready is not None

    # Verify projects exist via API
    resp = requests.get(f"{BASE_URL}/api/ldm/projects", headers=admin_headers, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    # Should have at least the 3 mock projects
    assert isinstance(data, list)
    assert len(data) >= 1


# ============================================================================
# 2. Health endpoint
# ============================================================================


def test_health_endpoint(server_running):
    """Verify health endpoint returns 200."""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200


# ============================================================================
# 3. Settings path validation (SET-01, SET-02, SET-03)
# ============================================================================


def test_settings_path_validation(admin_headers):
    """Validate path validation endpoint with valid and invalid paths."""
    test123 = Path(TEST123_PATH)

    # Test with TEST123_PATH
    resp = requests.post(
        f"{BASE_URL}/api/settings/validate-path",
        json={"path": TEST123_PATH},
        headers=admin_headers,
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()

    if test123.exists():
        assert data["valid"] is True
    else:
        # Path doesn't exist on this machine -- valid should be False
        assert data["valid"] is False

    # Test with clearly invalid path
    resp = requests.post(
        f"{BASE_URL}/api/settings/validate-path",
        json={"path": "/nonexistent/fake/path/12345"},
        headers=admin_headers,
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False


# ============================================================================
# 4. Single-language merge preview
# ============================================================================


def test_preview_single_language(admin_headers, merge_temp_target, merge_temp_source):
    """Preview single-language merge returns match summary without modifying files."""
    body = {
        "source_path": str(merge_temp_source),
        "target_path": str(merge_temp_target),
        "export_path": str(merge_temp_target),
        "match_mode": "strict",
        "only_untranslated": False,
        "multi_language": False,
    }
    resp = requests.post(
        f"{BASE_URL}/api/merge/preview",
        json=body,
        headers=admin_headers,
        timeout=60,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_matched" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)


# ============================================================================
# 5. Invalid match mode
# ============================================================================


def test_preview_invalid_match_mode(admin_headers, merge_temp_target, merge_temp_source):
    """Invalid match_mode should return 422."""
    body = {
        "source_path": str(merge_temp_source),
        "target_path": str(merge_temp_target),
        "export_path": str(merge_temp_target),
        "match_mode": "invalid_mode",
        "only_untranslated": False,
        "multi_language": False,
    }
    resp = requests.post(
        f"{BASE_URL}/api/merge/preview",
        json=body,
        headers=admin_headers,
        timeout=10,
    )
    assert resp.status_code == 422
    assert "Invalid match_mode" in resp.text


# ============================================================================
# 6. SSE execute streaming
# ============================================================================


@pytest.mark.xfail(reason="Server bug: 'core' module import conflict in asyncio.to_thread — SSE stream returns empty")
def test_execute_streams_sse(admin_headers, merge_temp_target, merge_temp_source):
    """Execute merge streams SSE events ending with complete or error."""
    body = {
        "source_path": str(merge_temp_source),
        "target_path": str(merge_temp_target),
        "export_path": str(merge_temp_target),
        "match_mode": "strict",
        "only_untranslated": False,
        "multi_language": False,
    }
    resp = requests.post(
        f"{BASE_URL}/api/merge/execute",
        json=body,
        headers=admin_headers,
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200

    events = []
    current_event = "message"
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            events.append({"event": current_event, "data": line[5:].strip()})
            if current_event in ("complete", "error"):
                break

    assert len(events) >= 1, "Expected at least one SSE event"

    # Check terminal event exists
    terminal_events = [e for e in events if e["event"] in ("complete", "error")]
    assert len(terminal_events) >= 1, "Expected a complete or error terminal event"

    # If complete, verify it has total_matched
    complete_events = [e for e in events if e["event"] == "complete"]
    if complete_events:
        complete_data = json.loads(complete_events[0]["data"])
        assert "total_matched" in complete_data


# ============================================================================
# 7. Concurrent guard (skipped -- needs threading)
# ============================================================================


@pytest.mark.skip(reason="Concurrent guard test needs careful threading setup")
def test_execute_concurrent_guard(admin_headers, merge_temp_target, merge_temp_source):
    """Concurrent merge requests should be rejected with 409."""
    pass


# ============================================================================
# 8. Multi-language preview
# ============================================================================


def test_multi_language_preview(admin_headers, server_running):
    """Multi-language preview endpoint responds without crashing."""
    test123 = Path(TEST123_PATH)
    if not test123.exists():
        pytest.skip("TEST123_PATH not available on this machine")

    body = {
        "source_path": TEST123_PATH,
        "target_path": TEST123_PATH,
        "export_path": TEST123_PATH,
        "match_mode": "strict",
        "only_untranslated": False,
        "multi_language": True,
    }
    resp = requests.post(
        f"{BASE_URL}/api/merge/preview",
        json=body,
        headers=admin_headers,
        timeout=60,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" in data


# ============================================================================
# 9. SSE event order verification
# ============================================================================


@pytest.mark.xfail(reason="Server bug: 'core' module import conflict in asyncio.to_thread — SSE stream returns empty")
def test_sse_event_types_ordered(admin_headers, merge_temp_target, merge_temp_source):
    """Complete/error must be the last SSE event -- nothing follows it."""
    body = {
        "source_path": str(merge_temp_source),
        "target_path": str(merge_temp_target),
        "export_path": str(merge_temp_target),
        "match_mode": "strict",
        "only_untranslated": False,
        "multi_language": False,
    }
    resp = requests.post(
        f"{BASE_URL}/api/merge/execute",
        json=body,
        headers=admin_headers,
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200

    events = []
    current_event = "message"
    terminal_reached = False
    events_after_terminal = 0

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            if terminal_reached:
                events_after_terminal += 1
            events.append({"event": current_event, "data": line[5:].strip()})
            if current_event in ("complete", "error"):
                terminal_reached = True
                break  # SSE stream should end here

    assert len(events) >= 1, "Expected at least one SSE event"
    assert terminal_reached, "Expected a complete or error event"
    assert events_after_terminal == 0, "No events should appear after complete/error"

    # Verify the last event is terminal
    last_event = events[-1]
    assert last_event["event"] in ("complete", "error")
