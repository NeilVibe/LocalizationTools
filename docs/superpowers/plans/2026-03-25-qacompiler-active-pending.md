# QACompiler Active Pending Implementation Plan — COMPLETED 2026-03-25

> **STATUS: IMPLEMENTED.** See commits 1891283d, 89660e88.

**Goal:** Replace the PENDING calculation so it reflects only issues living in the most recent masterfile per category, not stale QA file issues.

**Architecture:** New `tracker/masterfile_pending.py` module reads latest masterfiles, pairs `TESTER_STATUS_{user}` with `STATUS_{user}` on each row, returns pending/fixed/reported/checking/nonissue counts per tester per category. Existing QA file aggregation stays untouched for OVERALL stats. `_DAILY_DATA` gets new columns for active issue data. `total.py` reads active pending instead of computing `issues - fixed - reported - nonissue`.

**Tech Stack:** Python 3.10, openpyxl (read_only mode), existing QACompiler test patterns.

**Spec:** `docs/superpowers/specs/2026-03-25-qacompiler-active-pending-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| CREATE | `tracker/masterfile_pending.py` | Read latest masterfiles, return paired status counts per tester |
| CREATE | `tests/test_masterfile_pending.py` | Unit tests for the new module |
| MODIFY | `tracker/data.py:70-85` | Add active issue columns to `DAILY_DATA_HEADERS` |
| MODIFY | `tracker/data.py:88-210` | Write active data into `_DAILY_DATA` rows |
| MODIFY | `tracker/total.py:155-156` | Add "Active Issues" + "Active Pending" to `MANAGER_HEADERS` |
| MODIFY | `tracker/total.py:225-370` | Read active pending from new columns in `read_latest_data_for_total()` |
| MODIFY | `tracker/total.py:469-548` | Use active pending in `build_tester_section()` |
| MODIFY | `core/tracker_update.py:523-560` | Call `build_pending_from_masterfiles()` in flat_dump path |
| MODIFY | `core/tracker_update.py:1033-1170` | Call `build_pending_from_masterfiles()` in standard path |

All paths relative to: `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/`

---

### Task 1: Create `masterfile_pending.py` — Test First

**Files:**
- Create: `tests/test_masterfile_pending.py`
- Create: `tracker/masterfile_pending.py`

- [ ] **Step 1: Write failing test — single masterfile, one tester**

```python
"""Tests for tracker/masterfile_pending.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import openpyxl
import tempfile
import shutil


def _make_master(folder: Path, category: str, sheets: dict):
    """Helper: create a Master_{category}.xlsx with given sheet data.

    sheets = {
        "SheetName": {
            "headers": ["STRINGID", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
            "rows": [
                ["100001", "Hello", "ISSUE", ""],
                ["100002", "World", "ISSUE", "FIXED"],
                ["100003", "Bye",   "NO ISSUE", ""],
            ]
        }
    }
    """
    wb = openpyxl.Workbook()
    del wb["Sheet"]
    for sheet_name, data in sheets.items():
        ws = wb.create_sheet(sheet_name)
        for col, h in enumerate(data["headers"], 1):
            ws.cell(1, col, h)
        for row_idx, row_data in enumerate(data["rows"], 2):
            for col, val in enumerate(row_data, 1):
                ws.cell(row_idx, col, val)
    path = folder / f"Master_{category}.xlsx"
    wb.save(path)
    wb.close()
    return path


class TestBuildPendingFromMasterfiles:
    """Test build_pending_from_masterfiles()."""

    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.en_folder = self.tmpdir / "Masterfolder_EN"
        self.cn_folder = self.tmpdir / "Masterfolder_CN"
        self.en_folder.mkdir()
        self.cn_folder.mkdir()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_single_master_one_tester(self):
        """One masterfile, one tester: 3 ISSUE rows, 1 FIXED, 1 empty, 1 CHECKING."""
        _make_master(self.en_folder, "Quest", {
            "Quest": {
                "headers": ["STRINGID", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["100001", "Hello",   "ISSUE", ""],          # pending
                    ["100002", "World",   "ISSUE", "FIXED"],     # fixed
                    ["100003", "Bye",     "ISSUE", "CHECKING"],  # pending (checking)
                    ["100004", "Again",   "NO ISSUE", ""],       # not an issue
                ],
            }
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        assert "UserA" in result
        quest = result["UserA"]["Quest"]
        assert quest["active_issues"] == 3    # 3 rows with TESTER_STATUS=ISSUE
        assert quest["pending"] == 2          # empty + CHECKING
        assert quest["fixed"] == 1
        assert quest["reported"] == 0
        assert quest["checking"] == 1
        assert quest["nonissue"] == 0

    def test_two_testers_same_master(self):
        """Two testers in one masterfile, independent counts."""
        _make_master(self.en_folder, "Item", {
            "Item": {
                "headers": ["STRINGID", "TEXT",
                            "TESTER_STATUS_Alice", "STATUS_Alice",
                            "TESTER_STATUS_Bob", "STATUS_Bob"],
                "rows": [
                    ["200001", "Sword",  "ISSUE", "FIXED",    "ISSUE", ""],
                    ["200002", "Shield", "ISSUE", "",         "NO ISSUE", ""],
                    ["200003", "Potion", "ISSUE", "REPORTED", "ISSUE", "NON-ISSUE"],
                ],
            }
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        alice = result["Alice"]["Item"]
        assert alice["active_issues"] == 3
        assert alice["pending"] == 1      # row 200002
        assert alice["fixed"] == 1        # row 200001
        assert alice["reported"] == 1     # row 200003

        bob = result["Bob"]["Item"]
        assert bob["active_issues"] == 2  # rows 200001, 200003
        assert bob["pending"] == 1        # row 200001
        assert bob["nonissue"] == 1       # row 200003

    def test_latest_file_wins_dedup(self):
        """Two Master_Quest.xlsx with different mtimes — only latest is read."""
        import time

        # Older file: UserA has 5 issues all pending
        _make_master(self.en_folder, "Quest", {
            "Quest": {
                "headers": ["STRINGID", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["100001", "Old1", "ISSUE", ""],
                    ["100002", "Old2", "ISSUE", ""],
                    ["100003", "Old3", "ISSUE", ""],
                    ["100004", "Old4", "ISSUE", ""],
                    ["100005", "Old5", "ISSUE", ""],
                ],
            }
        })

        # Ensure different mtime (1 second later)
        time.sleep(1.1)

        # Create subfolder to simulate a second copy (same Masterfolder)
        # Actually: rglob finds nested files too. Put newer one in subfolder.
        sub = self.en_folder / "latest"
        sub.mkdir()
        _make_master(sub, "Quest", {
            "Quest": {
                "headers": ["STRINGID", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["100001", "New1", "ISSUE", "FIXED"],
                    ["100002", "New2", "ISSUE", ""],
                ],
            }
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        # Latest file has 2 rows: 1 fixed, 1 pending
        quest = result["UserA"]["Quest"]
        assert quest["active_issues"] == 2
        assert quest["pending"] == 1
        assert quest["fixed"] == 1

    def test_multi_sheet_master(self):
        """Master_Script.xlsx has Sequencer + Dialog sheets."""
        _make_master(self.en_folder, "Script", {
            "Sequencer": {
                "headers": ["EVENTNAME", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["EVT001", "Line1", "ISSUE", ""],
                    ["EVT002", "Line2", "ISSUE", "FIXED"],
                ],
            },
            "Dialog": {
                "headers": ["EVENTNAME", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["DLG001", "Talk1", "ISSUE", "REPORTED"],
                ],
            }
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        # Script category aggregates both sheets
        script = result["UserA"]["Script"]
        assert script["active_issues"] == 3
        assert script["pending"] == 1      # EVT001
        assert script["fixed"] == 1        # EVT002
        assert script["reported"] == 1     # DLG001

    def test_empty_folders(self):
        """No masterfiles → empty result."""
        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)
        assert result == {}

    def test_skip_status_sheet(self):
        """STATUS sheet in masterfile should be skipped."""
        wb = openpyxl.Workbook()
        del wb["Sheet"]
        # Real data sheet
        ws = wb.create_sheet("Quest")
        ws.cell(1, 1, "STRINGID")
        ws.cell(1, 2, "TEXT")
        ws.cell(1, 3, "TESTER_STATUS_UserA")
        ws.cell(1, 4, "STATUS_UserA")
        ws.cell(2, 1, "100001")
        ws.cell(2, 2, "Hello")
        ws.cell(2, 3, "ISSUE")
        ws.cell(2, 4, "")
        # STATUS sheet (should be skipped)
        ws2 = wb.create_sheet("STATUS")
        ws2.cell(1, 1, "TESTER_STATUS_FakeUser")
        ws2.cell(2, 1, "ISSUE")
        path = self.en_folder / "Master_Quest.xlsx"
        wb.save(path)
        wb.close()

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        assert "UserA" in result
        assert "FakeUser" not in result

    def test_non_issue_variants(self):
        """NON-ISSUE and NON ISSUE both count as nonissue."""
        _make_master(self.en_folder, "Character", {
            "Character": {
                "headers": ["STRINGID", "TEXT", "TESTER_STATUS_UserA", "STATUS_UserA"],
                "rows": [
                    ["300001", "NPC1", "ISSUE", "NON-ISSUE"],
                    ["300002", "NPC2", "ISSUE", "NON ISSUE"],
                    ["300003", "NPC3", "ISSUE", ""],
                ],
            }
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(self.en_folder, self.cn_folder)

        char = result["UserA"]["Character"]
        assert char["nonissue"] == 2
        assert char["pending"] == 1
```

- [ ] **Step 2: Run tests — expect FAIL (module doesn't exist)**

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW && python -m pytest tests/test_masterfile_pending.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'tracker.masterfile_pending'`

- [ ] **Step 3: Implement `tracker/masterfile_pending.py`**

```python
"""
Masterfile Pending Reader
=========================
Read latest masterfiles per category, return paired tester/manager status counts.

Single responsibility: given Masterfolder paths, return active issue data per tester.
No file writes, no side effects — pure data reader.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.excel_ops import safe_load_workbook


def _discover_latest_masterfiles(folder: Path) -> Dict[str, Path]:
    """Find the most recent Master_*.xlsx per category in a folder.

    Scans recursively (rglob) to handle nested structures.
    Groups by category name (part after 'Master_' in filename).
    Keeps only the file with the highest mtime per category.

    Returns:
        Dict mapping category name -> Path to latest masterfile.
    """
    if not folder.exists():
        return {}

    # category -> (mtime, path)
    candidates: Dict[str, Tuple[float, Path]] = {}

    for master_path in folder.rglob("Master_*.xlsx"):
        if master_path.name.startswith("~"):
            continue

        category = master_path.stem.replace("Master_", "", 1)
        if not category:
            continue

        mtime = master_path.stat().st_mtime
        if category not in candidates or mtime > candidates[category][0]:
            candidates[category] = (mtime, master_path)

    return {cat: path for cat, (_, path) in candidates.items()}


def _read_master_statuses(master_path: Path, category: str) -> Dict[str, Dict[str, int]]:
    """Read TESTER_STATUS_{user} and STATUS_{user} columns from a masterfile.

    For each sheet (except STATUS), finds paired columns and counts:
    - active_issues: rows where TESTER_STATUS_{user} = ISSUE
    - pending: active issues where STATUS_{user} is empty or CHECKING
    - fixed: active issues where STATUS_{user} = FIXED
    - reported: active issues where STATUS_{user} = REPORTED
    - checking: active issues where STATUS_{user} = CHECKING
    - nonissue: active issues where STATUS_{user} = NON-ISSUE or NON ISSUE

    Args:
        master_path: Path to Master_*.xlsx file.
        category: Category name for logging.

    Returns:
        Dict mapping username -> {active_issues, pending, fixed, reported, checking, nonissue}
    """
    user_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"active_issues": 0, "pending": 0, "fixed": 0,
                 "reported": 0, "checking": 0, "nonissue": 0}
    )

    try:
        wb = safe_load_workbook(master_path, read_only=True, data_only=True)
    except Exception:
        return dict(user_counts)

    try:
        for sheet_name in wb.sheetnames:
            if sheet_name == "STATUS":
                continue

            ws = wb[sheet_name]
            if ws.max_row is None or ws.max_row < 2:
                continue
            if ws.max_column is None or ws.max_column < 1:
                continue

            # Scan headers for TESTER_STATUS_{user} and STATUS_{user} columns
            header_iter = ws.iter_rows(min_row=1, max_row=1,
                                       max_col=ws.max_column, values_only=True)
            header_tuple = next(header_iter, None)
            if not header_tuple:
                continue

            # Build column maps: username -> (tester_status_idx, manager_status_idx)
            tester_status_cols: Dict[str, int] = {}   # username -> 0-based col idx
            manager_status_cols: Dict[str, int] = {}   # username -> 0-based col idx

            for col_idx, header_val in enumerate(header_tuple):
                if not header_val:
                    continue
                h = str(header_val).strip()
                h_upper = h.upper()

                if h_upper.startswith("TESTER_STATUS_"):
                    username = h[14:]  # len("TESTER_STATUS_") = 14
                    tester_status_cols[username] = col_idx
                elif h_upper.startswith("STATUS_") and not h_upper.startswith("TESTER_STATUS_"):
                    username = h[7:]  # len("STATUS_") = 7
                    manager_status_cols[username] = col_idx

            if not tester_status_cols:
                continue

            # Scan data rows
            for row_tuple in ws.iter_rows(min_row=2, max_col=ws.max_column,
                                           values_only=True):
                for username, ts_idx in tester_status_cols.items():
                    # Get tester status
                    tester_val = row_tuple[ts_idx] if ts_idx < len(row_tuple) else None
                    if not tester_val:
                        continue
                    tester_upper = str(tester_val).strip().upper()
                    if tester_upper != "ISSUE":
                        continue

                    # This row is an active issue for this tester
                    user_counts[username]["active_issues"] += 1

                    # Get manager status (paired column)
                    ms_idx = manager_status_cols.get(username)
                    manager_val = None
                    if ms_idx is not None and ms_idx < len(row_tuple):
                        manager_val = row_tuple[ms_idx]

                    if not manager_val or str(manager_val).strip() == "":
                        user_counts[username]["pending"] += 1
                    else:
                        mv = str(manager_val).strip().upper()
                        if mv == "FIXED":
                            user_counts[username]["fixed"] += 1
                        elif mv == "REPORTED":
                            user_counts[username]["reported"] += 1
                        elif mv == "CHECKING":
                            user_counts[username]["checking"] += 1
                            user_counts[username]["pending"] += 1  # checking = still pending
                        elif mv in ("NON-ISSUE", "NON ISSUE"):
                            user_counts[username]["nonissue"] += 1
                        else:
                            # Unknown manager status — treat as pending
                            user_counts[username]["pending"] += 1
    finally:
        wb.close()

    return dict(user_counts)


def build_pending_from_masterfiles(
    masterfolder_en: Path,
    masterfolder_cn: Path,
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """Build active pending counts from latest masterfiles per category.

    Scans both EN and CN masterfolders. For each unique category, keeps
    only the most recent file (by mtime). Reads paired TESTER_STATUS / STATUS
    columns to count active issues and their resolution state per tester.

    Args:
        masterfolder_en: Path to Masterfolder_EN.
        masterfolder_cn: Path to Masterfolder_CN.

    Returns:
        Nested dict: {username: {category: {active_issues, pending, fixed,
        reported, checking, nonissue}}}
    """
    # Discover latest masterfiles from both folders
    en_masters = _discover_latest_masterfiles(masterfolder_en)
    cn_masters = _discover_latest_masterfiles(masterfolder_cn)

    # Merge: if same category in both, keep the one with latest mtime
    all_masters: Dict[str, Path] = {}
    all_categories = set(en_masters.keys()) | set(cn_masters.keys())

    for cat in all_categories:
        en_path = en_masters.get(cat)
        cn_path = cn_masters.get(cat)
        if en_path and cn_path:
            en_mtime = en_path.stat().st_mtime
            cn_mtime = cn_path.stat().st_mtime
            all_masters[cat] = en_path if en_mtime >= cn_mtime else cn_path
        elif en_path:
            all_masters[cat] = en_path
        else:
            all_masters[cat] = cn_path

    # Read paired statuses from each masterfile
    # Result: {username: {category: counts}}
    result: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(dict)

    for category, master_path in sorted(all_masters.items()):
        user_counts = _read_master_statuses(master_path, category)
        for username, counts in user_counts.items():
            result[username][category] = counts

    return dict(result)
```

- [ ] **Step 4: Run tests — expect ALL PASS**

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW && python -m pytest tests/test_masterfile_pending.py -v
```
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tracker/masterfile_pending.py RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tests/test_masterfile_pending.py
git commit -m "feat(qacompiler): add masterfile_pending reader with TDD tests

New module reads latest masterfiles per category, pairs TESTER_STATUS
with STATUS columns, returns active issue counts per tester."
```

---

### Task 2: Add Active Columns to `_DAILY_DATA`

**Files:**
- Modify: `tracker/data.py:70-85` (headers)
- Modify: `tracker/data.py:88-210` (write logic)

- [ ] **Step 1: Add new headers to DAILY_DATA_HEADERS**

In `tracker/data.py`, change line 70-85:

```python
DAILY_DATA_HEADERS = [
    "Date",        # 1
    "User",        # 2
    "Category",    # 3
    "TotalRows",   # 4
    "Done",        # 5
    "Issues",      # 6  (OVERALL — from QA files, unchanged)
    "NoIssue",     # 7
    "Blocked",     # 8
    "Fixed",       # 9
    "Reported",    # 10
    "Checking",    # 11
    "NonIssue",    # 12
    "WordCount",   # 13
    "Korean",      # 14
    "ActiveIssues",    # 15  (NEW — from masterfile)
    "ActivePending",   # 16  (NEW — from masterfile)
    "ActiveFixed",     # 17  (NEW — from masterfile)
    "ActiveReported",  # 18  (NEW — from masterfile)
    "ActiveChecking",  # 19  (NEW — from masterfile)
    "ActiveNonIssue",  # 20  (NEW — from masterfile)
]
```

- [ ] **Step 2: Update `update_daily_data_sheet()` signature**

Add `active_pending_data` parameter:

```python
def update_daily_data_sheet(
    wb: openpyxl.Workbook,
    daily_entries: List[Dict],
    manager_stats: Dict = None,
    manager_dates: Dict = None,
    active_pending_data: Dict = None,   # NEW: from build_pending_from_masterfiles()
) -> None:
```

- [ ] **Step 3: Write active data into new columns**

After existing line 209 (writing Korean to col 14), add:

```python
        # Active issue data from masterfile (cols 15-20)
        if active_pending_data:
            user_active = active_pending_data.get(user, {})
            # Map folder category to master category for lookup
            active_cat = get_target_master_category(category)
            cat_active = user_active.get(active_cat, {})
            ws.cell(row, 15, cat_active.get("active_issues", 0))
            ws.cell(row, 16, cat_active.get("pending", 0))
            ws.cell(row, 17, cat_active.get("fixed", 0))
            ws.cell(row, 18, cat_active.get("reported", 0))
            ws.cell(row, 19, cat_active.get("checking", 0))
            ws.cell(row, 20, cat_active.get("nonissue", 0))
        else:
            for col in range(15, 21):
                ws.cell(row, col, 0)
```

- [ ] **Step 4: Update header check to expect 20 columns**

Change line 117:
```python
    if ws.cell(1, 1).value != "Date" or ws.max_column < 20:
```

- [ ] **Step 5: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tracker/data.py
git commit -m "feat(qacompiler): add active issue columns to _DAILY_DATA schema

Columns 15-20: ActiveIssues, ActivePending, ActiveFixed, ActiveReported,
ActiveChecking, ActiveNonIssue — sourced from masterfile paired statuses."
```

---

### Task 3: Update TOTAL Sheet to Use Active Pending

**Files:**
- Modify: `tracker/total.py:155-156` (headers)
- Modify: `tracker/total.py:225-370` (read function)
- Modify: `tracker/total.py:469-548` (build function)

- [ ] **Step 1: Add Active Issues and Active Pending to MANAGER_HEADERS**

Change line 155-156:

```python
TESTER_HEADERS = ["User", "Done", "Issues", "No Issue", "Blocked", "Korean"]
MANAGER_HEADERS = ["Fixed", "Reported", "NonIssue", "Checking", "Pending", "Active Issues", "Active Pending"]
```

- [ ] **Step 2: Update `read_latest_data_for_total()` to read new columns**

In the `latest_data[key]` dict assignment (around line 274-288), add:

```python
            latest_data[key] = {
                "date": date,
                "category": category,
                "total_rows": raw_total_rows,
                "done": raw_done,
                "issues": raw_issues,
                "no_issue": data_ws.cell(row, 7).value or 0,
                "blocked": data_ws.cell(row, 8).value or 0,
                "fixed": data_ws.cell(row, 9).value or 0,
                "reported": data_ws.cell(row, 10).value or 0,
                "checking": data_ws.cell(row, 11).value or 0,
                "nonissue": data_ws.cell(row, 12).value or 0,
                "word_count": data_ws.cell(row, 13).value or 0,
                "korean": data_ws.cell(row, 14).value or 0,
                # NEW: Active data from masterfile
                "active_issues": data_ws.cell(row, 15).value or 0,
                "active_pending": data_ws.cell(row, 16).value or 0,
            }
```

- [ ] **Step 3: Aggregate active data in user_data**

In the aggregation loop (around line 303-319), add:

```python
        user_data[user]["active_issues"] += data.get("active_issues", 0)
        user_data[user]["active_pending"] += data.get("active_pending", 0)
```

And update the defaultdict factory (around line 291-294):

```python
    user_data = defaultdict(lambda: {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0,
        "fixed": 0, "reported": 0, "checking": 0, "nonissue": 0, "korean": 0,
        "active_issues": 0, "active_pending": 0
    })
```

- [ ] **Step 4: Update `build_tester_section()` to display active columns**

In the data row writing (around line 469-518), add active_issues and active_pending to row_data:

```python
        active_issues_val = data.get("active_issues", 0)
        active_pending_val = data.get("active_pending", 0)

        # Row data: Tester Stats + Manager Stats (now includes Active columns)
        row_data = [user, done, issues, no_issue, blocked, korean,
                    fixed, reported, nonissue, checking, pending,
                    active_issues_val, active_pending_val]
```

Update section_total accumulation:

```python
        section_total["active_issues"] += active_issues_val
        section_total["active_pending"] += active_pending_val
```

And add to section_total init (around line 461-464):

```python
    section_total = {
        "total_rows": 0, "done": 0, "issues": 0, "no_issue": 0, "blocked": 0, "korean": 0,
        "fixed": 0, "reported": 0, "checking": 0, "pending": 0, "nonissue": 0,
        "actual_done": 0, "active_issues": 0, "active_pending": 0
    }
```

- [ ] **Step 5: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tracker/total.py
git commit -m "feat(qacompiler): display Active Issues and Active Pending on TOTAL sheet

TOTAL sheet now shows both OVERALL pending (from QA files) and
ACTIVE pending (from masterfile). Active = only issues living in
the most recent masterfile per category."
```

---

### Task 4: Wire Into Tracker Update Paths

**Files:**
- Modify: `core/tracker_update.py:523-560` (flat_dump path)
- Modify: `core/tracker_update.py:1033-1170` (standard path)

- [ ] **Step 1: Wire into `update_tracker_flat_dump()`**

After the existing `aggregate_manager_stats_from_files()` call (around line 540-550), add:

```python
    # Build active pending from discovered masterfiles
    from tracker.masterfile_pending import build_pending_from_masterfiles

    # Find Masterfolder_EN and CN from the flat dump discovery
    # Reuse the master_files list — extract unique parent folders
    en_folders = set()
    cn_folders = set()
    for mpath in master_files:
        parent_name = mpath.parent.name
        if "EN" in parent_name:
            en_folders.add(mpath.parent)
        elif "CN" in parent_name:
            cn_folders.add(mpath.parent)

    # Use the first found folder for each language (or empty Path)
    en_folder = next(iter(en_folders), Path("/nonexistent"))
    cn_folder = next(iter(cn_folders), Path("/nonexistent"))
    active_pending_data = build_pending_from_masterfiles(en_folder, cn_folder)
    _log(f"Active pending: {len(active_pending_data)} testers with active issues")
```

Then pass `active_pending_data` to `update_daily_data_sheet()`:

```python
    update_daily_data_sheet(tracker_wb, entries, manager_stats, manager_dates,
                           active_pending_data=active_pending_data)
```

- [ ] **Step 2: Wire into `update_tracker_only()`**

After the existing `aggregate_manager_stats()` call (around line 1122), add:

```python
    # Build active pending from compilation output masterfiles
    from tracker.masterfile_pending import build_pending_from_masterfiles
    from config import MASTER_FOLDER_EN, MASTER_FOLDER_CN
    active_pending_data = build_pending_from_masterfiles(MASTER_FOLDER_EN, MASTER_FOLDER_CN)
    _log(f"Active pending: {len(active_pending_data)} testers with active issues")
```

Then pass to `update_daily_data_sheet()` (around line 1155):

```python
    update_daily_data_sheet(tracker_wb, entries, manager_stats, manager_dates,
                           active_pending_data=active_pending_data)
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW && python -m pytest tests/ -v 2>&1 | tail -20
```
Expected: all existing tests still pass

- [ ] **Step 4: Run the new masterfile_pending tests**

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW && python -m pytest tests/test_masterfile_pending.py -v
```
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QACompilerNEW/core/tracker_update.py
git commit -m "feat(qacompiler): wire masterfile pending into both tracker update paths

Both update_tracker_only() and update_tracker_flat_dump() now call
build_pending_from_masterfiles() and pass active data to _DAILY_DATA."
```

---

### Task 5: Integration Test — End-to-End Scenario

**Files:**
- Create: `tests/test_active_pending_integration.py`

- [ ] **Step 1: Write integration test — stale issues don't inflate pending**

```python
"""Integration test: stale QA issues should NOT inflate active pending."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import openpyxl
import tempfile
import shutil
import pytest


def _make_qa_file(folder: Path, username: str, category: str, issues: int, no_issues: int):
    """Create a QA file with given issue/no-issue counts."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = category
    ws.cell(1, 1, "STRINGID")
    ws.cell(1, 2, "TEXT")
    ws.cell(1, 3, "STATUS")
    row = 2
    for i in range(issues):
        ws.cell(row, 1, str(900000 + i))
        ws.cell(row, 2, f"Issue text {i}")
        ws.cell(row, 3, "ISSUE")
        row += 1
    for i in range(no_issues):
        ws.cell(row, 1, str(800000 + i))
        ws.cell(row, 2, f"OK text {i}")
        ws.cell(row, 3, "NO ISSUE")
        row += 1
    qa_dir = folder / f"{username}_{category}"
    qa_dir.mkdir(parents=True, exist_ok=True)
    path = qa_dir / f"{username}_{category}.xlsx"
    wb.save(path)
    wb.close()
    return path


def _make_master(folder: Path, category: str, tester_issues: dict):
    """Create masterfile with only 'living' rows.

    tester_issues = {
        "UserA": [
            ("900000", "Issue text 0", "ISSUE", ""),        # pending
            ("900001", "Issue text 1", "ISSUE", "FIXED"),   # fixed
        ]
    }
    """
    wb = openpyxl.Workbook()
    del wb["Sheet"]
    ws = wb.create_sheet(category)

    # Build headers
    headers = ["STRINGID", "TEXT"]
    for user in tester_issues:
        headers.extend([f"TESTER_STATUS_{user}", f"STATUS_{user}"])
    for col, h in enumerate(headers, 1):
        ws.cell(1, col, h)

    # Build rows
    # All users must have same number of rows (masterfile is a single table)
    first_user = list(tester_issues.keys())[0]
    num_rows = len(tester_issues[first_user])
    for row_idx in range(num_rows):
        row_data = tester_issues[first_user][row_idx]
        ws.cell(row_idx + 2, 1, row_data[0])  # STRINGID
        ws.cell(row_idx + 2, 2, row_data[1])  # TEXT
        col = 3
        for user in tester_issues:
            user_row = tester_issues[user][row_idx]
            ws.cell(row_idx + 2, col, user_row[2])      # TESTER_STATUS
            ws.cell(row_idx + 2, col + 1, user_row[3])  # STATUS (manager)
            col += 2

    path = folder / f"Master_{category}.xlsx"
    wb.save(path)
    wb.close()


class TestStalePendingElimination:
    """Verify stale QA issues don't inflate active pending."""

    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_stale_issues_excluded_from_active(self):
        """QA file has 10 issues, masterfile only has 3 → active=3, not 10."""
        en_folder = self.tmpdir / "Masterfolder_EN"
        en_folder.mkdir()
        cn_folder = self.tmpdir / "Masterfolder_CN"
        cn_folder.mkdir()

        # Masterfile: only 3 of the tester's 10 issues exist
        _make_master(en_folder, "Quest", {
            "UserA": [
                ("900000", "Issue 0", "ISSUE", ""),        # pending
                ("900001", "Issue 1", "ISSUE", "FIXED"),   # fixed
                ("900002", "Issue 2", "ISSUE", "CHECKING"),# checking (pending)
            ]
        })

        from tracker.masterfile_pending import build_pending_from_masterfiles
        result = build_pending_from_masterfiles(en_folder, cn_folder)

        # Only 3 active issues, not 10
        quest = result["UserA"]["Quest"]
        assert quest["active_issues"] == 3
        assert quest["pending"] == 2   # empty + CHECKING
        assert quest["fixed"] == 1
        assert quest["checking"] == 1
```

- [ ] **Step 2: Run integration test**

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW && python -m pytest tests/test_active_pending_integration.py -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tests/test_active_pending_integration.py
git commit -m "test(qacompiler): integration test verifying stale issues excluded from active pending"
```

---

## Execution Order

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
  │         │         │         │         │
  │         │         │         │         └─ Integration test
  │         │         │         └─ Wire into tracker_update paths
  │         │         └─ TOTAL sheet reads active pending
  │         └─ _DAILY_DATA gets new columns
  └─ New module + unit tests (TDD)
```

Each task produces a working commit. Tasks are sequential (each depends on prior).
