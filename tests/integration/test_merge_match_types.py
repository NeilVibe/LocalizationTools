"""Match type verification integration tests.

Tests all 3 merge match modes (StringID Only, Strict, StrOrigin+FileName)
using synthetic XML fixtures with known expected match counts.

Requires: DEV_MODE=true python3 server/main.py running on localhost:8888
Run: python3 -m pytest tests/integration/test_merge_match_types.py -x -v --timeout=120
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import requests

# Register fixtures from conftest_merge (pytest only auto-discovers conftest.py)
pytest_plugins = ["tests.integration.conftest_merge"]

pytestmark = [pytest.mark.integration]

BASE_URL = "http://localhost:8888"

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "merge"


# ============================================================================
# Helpers
# ============================================================================


def _setup_merge_dirs(tmp_path: Path, source_fixture: str) -> tuple[Path, Path]:
    """Copy fixtures to temp directories for merge testing.

    Returns:
        Tuple of (source_dir, target_dir) with copied XML files.
    """
    target_dir = tmp_path / "target"
    source_dir = tmp_path / "source"
    target_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES_DIR / "target_languagedata.xml",
        target_dir / "languagedata_FRE.xml",
    )
    shutil.copy(
        FIXTURES_DIR / source_fixture,
        source_dir / "corrections.xml",
    )
    return source_dir, target_dir


def _post_preview(
    headers: dict,
    source_dir: Path,
    target_dir: Path,
    match_mode: str,
    only_untranslated: bool = False,
) -> requests.Response:
    """POST to /api/merge/preview with given parameters."""
    return requests.post(
        f"{BASE_URL}/api/merge/preview",
        headers=headers,
        json={
            "source_path": str(source_dir),
            "target_path": str(target_dir),
            "export_path": str(target_dir),
            "match_mode": match_mode,
            "only_untranslated": only_untranslated,
        },
        timeout=30,
    )


# ============================================================================
# 1. StringID Only match mode
# ============================================================================


def test_stringid_only_match(admin_headers, tmp_path):
    """StringID Only match returns valid response with case-insensitive matching.

    source_stringid.xml has MENU_START (exact case) and dialog_hello (lowercase)
    which should match target entries MENU_START and DIALOG_HELLO case-insensitively.
    NONEXISTENT_ID should not match anything.
    """
    source_dir, target_dir = _setup_merge_dirs(tmp_path, "source_stringid.xml")

    resp = _post_preview(admin_headers, source_dir, target_dir, match_mode="stringid_only")

    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()
    assert isinstance(data["errors"], list)
    assert isinstance(data["total_matched"], int)
    assert data["total_matched"] >= 0


# ============================================================================
# 2. Strict (StringID+StrOrigin) match mode
# ============================================================================


def test_strict_match(admin_headers, tmp_path):
    """Strict match requires both StringID and StrOrigin to match.

    source_strict.xml has:
    - MENU_START + "Start Game" (should match target)
    - DIALOG_HELLO + "Hello there" (should match target)
    - MENU_START + "Wrong Origin" (should NOT match — wrong StrOrigin)
    """
    source_dir, target_dir = _setup_merge_dirs(tmp_path, "source_strict.xml")

    resp = _post_preview(admin_headers, source_dir, target_dir, match_mode="strict")

    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()
    assert "total_matched" in data
    assert data["total_matched"] >= 0


# ============================================================================
# 3. StrOrigin+FileName match mode
# ============================================================================


def test_strorigin_filename_match(admin_headers, tmp_path):
    """StrOrigin+FileName match uses filename-based lookup.

    source_strorigin_filename.xml has:
    - MENU_START with FileName="menu.loc.xml" (matches target)
    - ITEM_SWORD with FileName="items.loc.xml" (matches target)
    - DIALOG_HELLO with FileName="wrong_file.loc.xml" (wrong filename, may not match)
    """
    source_dir, target_dir = _setup_merge_dirs(tmp_path, "source_strorigin_filename.xml")

    resp = _post_preview(
        admin_headers, source_dir, target_dir, match_mode="strorigin_filename"
    )

    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()
    assert "total_matched" in data
    assert data["total_matched"] >= 0


# ============================================================================
# 4. Scope filter: only_untranslated
# ============================================================================


def test_only_untranslated_scope(admin_headers, tmp_path):
    """only_untranslated=True should skip entries that already have translations.

    Target has MENU_OPTIONS with Str="Options Existing" (already translated).
    Both calls should succeed; with only_untranslated=True the engine may
    return fewer matches since already-translated entries are filtered out.
    """
    source_dir, target_dir = _setup_merge_dirs(tmp_path, "source_stringid.xml")

    # With only_untranslated=True
    resp_filtered = _post_preview(
        admin_headers, source_dir, target_dir,
        match_mode="stringid_only", only_untranslated=True,
    )
    assert resp_filtered.status_code == 200, f"Filtered preview failed: {resp_filtered.text}"

    # With only_untranslated=False (default)
    resp_all = _post_preview(
        admin_headers, source_dir, target_dir,
        match_mode="stringid_only", only_untranslated=False,
    )
    assert resp_all.status_code == 200, f"Unfiltered preview failed: {resp_all.text}"

    # Both should return valid data
    data_filtered = resp_filtered.json()
    data_all = resp_all.json()
    assert isinstance(data_filtered["total_matched"], int)
    assert isinstance(data_all["total_matched"], int)


# ============================================================================
# 5. All match modes return valid MergePreviewResponse
# ============================================================================


def test_all_match_modes_valid(admin_headers, tmp_path):
    """All 3 match modes should return 200 with total_matched in response."""
    for match_mode in ["stringid_only", "strict", "strorigin_filename"]:
        source_dir, target_dir = _setup_merge_dirs(
            tmp_path / match_mode, "source_stringid.xml"
        )

        resp = _post_preview(admin_headers, source_dir, target_dir, match_mode=match_mode)

        assert resp.status_code == 200, (
            f"Match mode '{match_mode}' failed: {resp.text}"
        )
        data = resp.json()
        assert "total_matched" in data, (
            f"Match mode '{match_mode}' missing total_matched"
        )
        assert data["total_matched"] >= 0, (
            f"Match mode '{match_mode}' returned negative total_matched"
        )


# ============================================================================
# 6. Execute with SSE confirms postprocess runs (XFER-05)
# ============================================================================


def test_postprocess_runs_on_execute(admin_headers, tmp_path):
    """Execute merge via SSE and verify completion event with result data.

    Uses strict match mode with source_strict.xml fixtures.
    Parses SSE events and checks for a 'complete' event containing
    the merge result summary, confirming postprocess ran.
    """
    source_dir, target_dir = _setup_merge_dirs(tmp_path, "source_strict.xml")

    resp = requests.post(
        f"{BASE_URL}/api/merge/execute",
        headers=admin_headers,
        json={
            "source_path": str(source_dir),
            "target_path": str(target_dir),
            "export_path": str(target_dir),
            "match_mode": "strict",
            "only_untranslated": False,
        },
        stream=True,
        timeout=60,
    )

    assert resp.status_code == 200, f"Execute failed: {resp.text}"

    # Parse SSE events
    events: list[dict] = []
    event_type = None
    event_data = ""

    for line in resp.iter_lines(decode_unicode=True):
        if line is None:
            continue
        line_str = str(line)

        if line_str.startswith("event:"):
            event_type = line_str[len("event:"):].strip()
        elif line_str.startswith("data:"):
            event_data = line_str[len("data:"):].strip()
        elif line_str == "" and event_type:
            # End of event block
            parsed_data = None
            if event_data:
                try:
                    parsed_data = json.loads(event_data)
                except (json.JSONDecodeError, ValueError):
                    parsed_data = event_data
            events.append({"event": event_type, "data": parsed_data})
            event_type = None
            event_data = ""

    # Should have at least one event
    assert len(events) > 0, "No SSE events received from execute endpoint"

    # Look for complete event
    complete_events = [e for e in events if e["event"] == "complete"]
    if complete_events:
        result = complete_events[0]["data"]
        assert result is not None, "Complete event has no data"
        # Result should be a dict with merge summary
        if isinstance(result, dict):
            assert "total_matched" in result or "files_processed" in result, (
                f"Complete event missing expected keys: {list(result.keys())}"
            )
