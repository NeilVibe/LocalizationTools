"""
Tests for tracker.masterfile_pending — masterfile-based pending issue extraction.

TDD: Written BEFORE the implementation module exists.
"""
from __future__ import annotations

import os
import sys
import time
import tempfile
from pathlib import Path

import pytest
from openpyxl import Workbook

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tracker.masterfile_pending import build_pending_from_masterfiles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_master(folder: Path, filename: str, sheets: dict, mtime: float | None = None):
    """
    Create a mock masterfile.

    sheets = {
        "SheetName": {
            "headers": ["Col1", "Col2", ...],
            "rows": [
                ["val1", "val2", ...],
                ...
            ],
        },
        ...
    }
    """
    wb = Workbook()
    first = True
    for sheet_name, spec in sheets.items():
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(sheet_name)
        for j, hdr in enumerate(spec["headers"], start=1):
            ws.cell(1, j, hdr)
        for i, row in enumerate(spec["rows"], start=2):
            for j, val in enumerate(row, start=1):
                ws.cell(i, j, val)

    path = folder / filename
    wb.save(path)
    wb.close()

    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dirs(tmp_path):
    en = tmp_path / "Masterfolder_EN"
    cn = tmp_path / "Masterfolder_CN"
    en.mkdir()
    cn.mkdir()
    return en, cn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_master_one_tester(tmp_dirs):
    """1 masterfile, 1 tester, 4 rows with different statuses."""
    en, cn = tmp_dirs

    _make_master(en, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                # ISSUE + empty status -> pending
                ["KR1", "EN1", "S001", "ISSUE", None],
                # ISSUE + FIXED -> fixed
                ["KR2", "EN2", "S002", "ISSUE", "FIXED"],
                # ISSUE + CHECKING -> pending + checking
                ["KR3", "EN3", "S003", "ISSUE", "CHECKING"],
                # No ISSUE -> skip entirely
                ["KR4", "EN4", "S004", None, "FIXED"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    alice = result["Alice"]["Quest"]
    assert alice["active_issues"] == 3
    # Row 1 (empty) -> pending, Row 3 (CHECKING) -> also pending
    assert alice["pending"] == 2
    assert alice["fixed"] == 1
    assert alice["checking"] == 1
    assert alice["reported"] == 0
    assert alice["nonissue"] == 0


def test_two_testers_same_master(tmp_dirs):
    """2 testers with independent columns in the same masterfile."""
    en, cn = tmp_dirs

    _make_master(en, "Master_Item.xlsx", {
        "Items": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
                "TESTER_STATUS_Bob", "STATUS_Bob",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", "FIXED", "ISSUE", "REPORTED"],
                ["KR2", "EN2", "S002", "ISSUE", None, None, "FIXED"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    alice = result["Alice"]["Item"]
    assert alice["active_issues"] == 2
    assert alice["fixed"] == 1
    assert alice["pending"] == 1  # row 2 empty status

    bob = result["Bob"]["Item"]
    assert bob["active_issues"] == 1  # only row 1 has ISSUE
    assert bob["reported"] == 1


def test_latest_file_wins_dedup(tmp_dirs):
    """2 Master_Quest.xlsx at different paths, only latest mtime used."""
    en, cn = tmp_dirs

    sub1 = en / "sub1"
    sub2 = en / "sub2"
    sub1.mkdir()
    sub2.mkdir()

    old_time = time.time() - 3600  # 1 hour ago
    new_time = time.time()

    # Old file: Alice has 2 issues
    _make_master(sub1, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", None],
                ["KR2", "EN2", "S002", "ISSUE", None],
            ],
        },
    }, mtime=old_time)

    # New file: Alice has 1 issue, fixed
    _make_master(sub2, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", "FIXED"],
            ],
        },
    }, mtime=new_time)

    result = build_pending_from_masterfiles(en, cn)

    alice = result["Alice"]["Quest"]
    assert alice["active_issues"] == 1
    assert alice["fixed"] == 1
    assert alice["pending"] == 0


def test_multi_sheet_master(tmp_dirs):
    """Master_Script.xlsx with Sequencer + Dialog sheets, aggregated under 'Script'."""
    en, cn = tmp_dirs

    _make_master(en, "Master_Script.xlsx", {
        "Sequencer_Tab1": {
            "headers": [
                "EventName", "Text", "Translation",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["EVT1", "Hello", "Bonjour", "ISSUE", "FIXED"],
                ["EVT2", "World", "Monde", "ISSUE", None],
            ],
        },
        "Dialog_Tab1": {
            "headers": [
                "EventName", "Text", "Translation",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["DLG1", "Hi", "Salut", "ISSUE", "REPORTED"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    # Both sheets aggregate under "Script" category
    alice = result["Alice"]["Script"]
    assert alice["active_issues"] == 3
    assert alice["fixed"] == 1
    assert alice["pending"] == 1
    assert alice["reported"] == 1


def test_empty_folders(tmp_dirs):
    """No masterfiles -> empty result."""
    en, cn = tmp_dirs
    result = build_pending_from_masterfiles(en, cn)
    assert result == {}


def test_skip_status_sheet(tmp_dirs):
    """STATUS sheet in masterfile is skipped."""
    en, cn = tmp_dirs

    _make_master(en, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", None],
            ],
        },
        "STATUS": {
            "headers": [
                "TESTER_STATUS_Ghost", "STATUS_Ghost",
            ],
            "rows": [
                ["ISSUE", None],
                ["ISSUE", "FIXED"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    # Ghost should NOT appear (STATUS sheet skipped)
    assert "Ghost" not in result
    # Alice from MainQuest should be there
    assert result["Alice"]["Quest"]["active_issues"] == 1


def test_non_issue_variants(tmp_dirs):
    """Both 'NON-ISSUE' and 'NON ISSUE' count as nonissue."""
    en, cn = tmp_dirs

    _make_master(en, "Master_Knowledge.xlsx", {
        "Knowledge": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", "NON-ISSUE"],
                ["KR2", "EN2", "S002", "ISSUE", "NON ISSUE"],
                ["KR3", "EN3", "S003", "ISSUE", "non-issue"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    alice = result["Alice"]["Knowledge"]
    assert alice["nonissue"] == 3
    assert alice["pending"] == 0


def test_en_and_cn_folders(tmp_dirs):
    """Files in both Masterfolder_EN and CN, merged correctly."""
    en, cn = tmp_dirs

    # EN folder: Quest with Alice
    _make_master(en, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ENG)", "STRINGID",
                "TESTER_STATUS_Alice", "STATUS_Alice",
            ],
            "rows": [
                ["KR1", "EN1", "S001", "ISSUE", "FIXED"],
            ],
        },
    })

    # CN folder: Quest with Bob (different tester)
    _make_master(cn, "Master_Quest.xlsx", {
        "MainQuest": {
            "headers": [
                "Korean", "Translation (ZHO-CN)", "STRINGID",
                "TESTER_STATUS_Bob", "STATUS_Bob",
            ],
            "rows": [
                ["KR1", "CN1", "S001", "ISSUE", None],
                ["KR2", "CN2", "S002", "ISSUE", "REPORTED"],
            ],
        },
    })

    result = build_pending_from_masterfiles(en, cn)

    # Alice from EN
    assert result["Alice"]["Quest"]["active_issues"] == 1
    assert result["Alice"]["Quest"]["fixed"] == 1

    # Bob from CN
    assert result["Bob"]["Quest"]["active_issues"] == 2
    assert result["Bob"]["Quest"]["pending"] == 1
    assert result["Bob"]["Quest"]["reported"] == 1
