"""
Tests for Merge API (Phase 58)

Tests preview and execute endpoints with mocked transfer_adapter functions.
Uses a minimal test app (no DB init) to isolate merge API testing.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.merge import router

# Minimal test app with just the merge router
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


# ============================================================================
# Mock data
# ============================================================================

MOCK_SINGLE_RESULT = {
    "match_mode": "strict",
    "files_processed": 2,
    "total_corrections": 150,
    "total_matched": 45,
    "total_updated": 0,
    "total_not_found": 105,
    "total_skipped": 0,
    "total_skipped_translated": 12,
    "file_results": {
        "languagedata_FRE.xml": {"matched": 45, "skipped_translated": 12},
    },
    "errors": [],
}

MOCK_MULTI_RESULT = {
    "scan": {
        "languages": {
            "FRE": ["/tmp/corrections_FRE.xml"],
            "ENG": ["/tmp/corrections_ENG.xml"],
        },
        "total_files": 2,
        "language_count": 2,
        "unrecognized": [],
        "warnings": [],
    },
    "per_language": {
        "FRE": {"matched": 60, "updated": 0, "not_found": 90, "skipped": 0, "errors": 0},
        "ENG": {"matched": 60, "updated": 0, "not_found": 90, "skipped": 0, "errors": 0},
    },
    "total_matched": 120,
    "total_skipped": 0,
    "total_errors": 0,
}

MOCK_SCAN_RESULT = {
    "languages": {"FRE": ["/tmp/corrections_FRE.xml"]},
    "total_files": 1,
    "language_count": 1,
    "unrecognized": [],
    "warnings": [],
}


# ============================================================================
# Tests
# ============================================================================


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_transfer", return_value=MOCK_SINGLE_RESULT)
def test_preview_dry_run(mock_transfer, mock_wsl):
    """POST /api/merge/preview returns dry-run summary for single-language mode."""
    response = client.post(
        "/api/merge/preview",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_matched"] == 45
    assert data["files_processed"] == 2
    assert data["per_language"] is None
    assert data["scan"] is None
    # Verify dry_run=True was passed
    mock_transfer.assert_called_once()
    call_kwargs = mock_transfer.call_args[1]
    assert call_kwargs["dry_run"] is True


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_multi_language_transfer", return_value=MOCK_MULTI_RESULT)
def test_preview_multi_language(mock_multi_transfer, mock_wsl):
    """POST /api/merge/preview with multi_language=true returns per-language breakdown."""
    response = client.post(
        "/api/merge/preview",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
            "multi_language": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["per_language"] is not None
    assert "FRE" in data["per_language"]
    assert "ENG" in data["per_language"]
    assert data["scan"] is not None
    assert data["total_matched"] == 120
    # Verify dry_run=True was passed
    mock_multi_transfer.assert_called_once()
    call_kwargs = mock_multi_transfer.call_args[1]
    assert call_kwargs["dry_run"] is True


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
def test_preview_invalid_match_mode(mock_wsl):
    """POST /api/merge/preview with invalid match_mode returns 422."""
    response = client.post(
        "/api/merge/preview",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "invalid_mode",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert "invalid_mode" in data["detail"]


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_transfer", return_value=MOCK_SINGLE_RESULT)
def test_preview_overwrite_warnings(mock_transfer, mock_wsl):
    """POST /api/merge/preview with only_untranslated=false extracts overwrite warnings."""
    response = client.post(
        "/api/merge/preview",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
            "only_untranslated": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["overwrite_warnings"]) > 0
    assert "languagedata_FRE.xml" in data["overwrite_warnings"][0]
    assert "45 entries will be overwritten" in data["overwrite_warnings"][0]


# ============================================================================
# SSE helper
# ============================================================================


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE events from a text/event-stream response body.

    Handles both \\n and \\r\\n line endings (sse-starlette uses \\r\\n).
    """
    events = []
    current: dict = {}
    for line in response_text.replace("\r\n", "\n").split("\n"):
        if line.startswith("event:"):
            current["event"] = line[6:].strip()
        elif line.startswith("data:"):
            current["data"] = line[5:].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


# ============================================================================
# Execute endpoint tests (Plan 02)
# ============================================================================


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_transfer")
def test_execute_sse_stream(mock_transfer, mock_wsl):
    """POST /api/merge/execute streams SSE events with progress and complete."""
    def fake_transfer(
        source_path="", target_path="", export_path="",
        match_mode="strict", only_untranslated=False,
        stringid_all_categories=False, dry_run=False,
        progress_callback=None, log_callback=None,
    ):
        if progress_callback:
            progress_callback("Processing file.xml (1/1)")
        return MOCK_SINGLE_RESULT

    mock_transfer.side_effect = fake_transfer

    response = client.post(
        "/api/merge/execute",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = parse_sse_events(response.text)
    event_types = [e.get("event") for e in events]
    assert "progress" in event_types, f"Expected progress event, got: {event_types}"
    assert "complete" in event_types, f"Expected complete event, got: {event_types}"


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_transfer", return_value=MOCK_SINGLE_RESULT)
def test_execute_completion_summary(mock_transfer, mock_wsl):
    """POST /api/merge/execute complete event contains full result as JSON."""
    response = client.post(
        "/api/merge/execute",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        },
    )
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    complete_events = [e for e in events if e.get("event") == "complete"]
    assert len(complete_events) == 1, f"Expected 1 complete event, got {len(complete_events)}"

    data = json.loads(complete_events[0]["data"])
    assert "total_matched" in data
    assert "files_processed" in data
    assert "match_mode" in data
    assert data["total_matched"] == 45


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_transfer", side_effect=RuntimeError("Test error"))
def test_execute_error_event(mock_transfer, mock_wsl):
    """POST /api/merge/execute sends error SSE event on exception."""
    response = client.post(
        "/api/merge/execute",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
        },
    )
    assert response.status_code == 200  # SSE always starts 200

    events = parse_sse_events(response.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) >= 1, f"Expected error event, got: {[e.get('event') for e in events]}"
    assert "Test error" in error_events[0]["data"]


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
def test_execute_conflict_409(mock_wsl):
    """POST /api/merge/execute returns 409 if merge already in progress."""
    import server.api.merge as merge_module

    original = merge_module._merge_in_progress
    try:
        merge_module._merge_in_progress = True
        response = client.post(
            "/api/merge/execute",
            json={
                "source_path": "/tmp/source",
                "target_path": "/tmp/target",
                "export_path": "/tmp/export",
                "match_mode": "strict",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "error" in data
        assert "already in progress" in data["error"]
    finally:
        merge_module._merge_in_progress = original


@patch("server.api.merge.translate_wsl_path", side_effect=lambda p: p)
@patch("server.api.merge.execute_multi_language_transfer", return_value=MOCK_MULTI_RESULT)
def test_execute_multi_language_stream(mock_multi_transfer, mock_wsl):
    """POST /api/merge/execute with multi_language=true uses multi-language transfer."""
    response = client.post(
        "/api/merge/execute",
        json={
            "source_path": "/tmp/source",
            "target_path": "/tmp/target",
            "export_path": "/tmp/export",
            "match_mode": "strict",
            "multi_language": True,
        },
    )
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    complete_events = [e for e in events if e.get("event") == "complete"]
    assert len(complete_events) == 1

    data = json.loads(complete_events[0]["data"])
    assert "per_language" in data
    mock_multi_transfer.assert_called_once()
