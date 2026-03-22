"""
Tests for Merge API (Phase 58, Plan 01)

Tests preview endpoints with mocked transfer_adapter functions.
Uses a minimal test app (no DB init) to isolate merge API testing.
"""
from __future__ import annotations

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
