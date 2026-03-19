# PLAN: Masterfile Manager Data & Beauty Fix

**Date:** 2026-03-19
**Status:** ✅ IMPLEMENTED (2026-03-19) + HIVE REVIEWED
**Severity:** HIGH — Affects ALL categories (initially reported as Quest-only, confirmed systemic)
**Related:** `ISSUE_MANAGER_TRANSFER_AND_ROW_UNION.md` (STATUS: IN PROGRESS — this plan completes it)

---

## Problem Statement

Three systemic bugs in masterfile compilation across ALL categories:

| # | Bug | Impact |
|---|-----|--------|
| 1 | **Manager STATUS not transferred** — manager status values (FIXED, REPORTED, CHECKING, NON ISSUE) disappear when master is rebuilt | Managers lose all their review work |
| 2 | **Manager COMMENT not transferred** — same phenomenon, manager comments vanish | Managers have to re-review everything |
| 3 | **No formatting/colors** — old masterfile had beautiful colors, new one is plain. No visual distinction between QA tester data and Manager data | Hard to read, unprofessional |

**Additional requirement:** Master files should have a beautiful, clear dictionary layout with visual separation between QA Tester Data sections and Manager Data sections.

---

## Root Cause Analysis

### System Architecture (Current)

```
MASTER FILE REBUILD PIPELINE:
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 1. EXTRACT       │ ──→ │ 2. REBUILD        │ ──→ │ 3. RESTORE       │
│ Old Master Data  │     │ Fresh Template    │     │ Data to New      │
│ (excel_ops.py    │     │ from Generator    │     │ Master           │
│  :289-566)       │     │                   │     │ (excel_ops.py    │
│                  │     │                   │     │  :569-807)       │
└─────────────────┘     └──────────────────┘     └──────────────────┘
     ✅ Works              ✅ Works                 ⚠️ MATCHING FAILS
     Extracts all          Creates new master       (stringid,trans)
     manager data          from fresh datasheets    key mismatch →
                                                    data orphaned
```

### Why Data Gets Lost

**Step 1 (Extract) — WORKS:**
`extract_tester_data_from_master()` correctly extracts:
- `manager_status` (from `STATUS_{username}` columns)
- `manager_comment` (from `MANAGER_COMMENT_{username}` columns)
- `tester_status`, `comment`, `screenshot`

**Step 2 (Rebuild) — WORKS but destroys old master:**
Fresh template replaces old master entirely.

**Step 3 (Restore) — FAILS for many rows:**
`restore_tester_data_to_master()` tries to match by `(stringid, translation)`:
```python
# excel_ops.py:669-675
if stringid and translation:                    # ← BOTH must be truthy
    pk = (stringid, translation)
    if pk in master_index.get("all_primary", {}):  # ← Must find exact match
        matching_rows = list(master_index["all_primary"][pk])
```

**Failure modes:**
1. STRINGID changes between compilations → primary match fails
2. Translation column detection fails → `content_key = None` → row skipped entirely
3. Empty StringKey on group header rows (Quest depth-0 rows) → `stringid` is empty → `if stringid and translation` fails → NO fallback attempted
4. Fallback exists (translation-only) but ONLY runs after primary fails — if stringid is empty, code goes to `else` branch at line 669 and the `if stringid and translation` check blocks it

**Bug #3 (formatting):**
The restoration code DOES apply colored fonts (MANAGER_FONT_FIXED, etc.) at lines 770-779. But:
- Only applies to rows that successfully match (orphaned rows get nothing)
- No overall sheet formatting (alternating row colors, section borders, etc.)
- No visual dictionary layout separating tester vs manager sections

---

## Fix Plan (4 Changes)

### Change 1: Fix Matching Logic (CRITICAL — Root Cause)

**File:** `core/excel_ops.py`
**Lines:** 669-675, 701-708
**Impact:** Fixes bugs #1 and #2

**Problem:** When `stringid` is empty (group headers, some row types), the condition `if stringid and translation` blocks BOTH primary AND fallback matching.

**Fix:**
```python
# BEFORE (broken):
else:
    if len(content_key) >= 2:
        stringid, translation = content_key[0], content_key[1]
        if stringid and translation:          # ← Empty stringid = SKIP
            pk = (stringid, translation)
            if pk in master_index.get("all_primary", {}):
                matching_rows = list(master_index["all_primary"][pk])

# AFTER (fixed):
else:
    if len(content_key) >= 2:
        stringid, translation = content_key[0], content_key[1]
        if translation:                       # ← Only require translation
            if stringid:
                pk = (stringid, translation)
                if pk in master_index.get("all_primary", {}):
                    matching_rows = list(master_index["all_primary"][pk])
            # If no stringid OR no primary match, try fallback immediately
            if not matching_rows and translation in master_index.get("fallback", {}):
                for row in master_index["fallback"][translation]:
                    if row not in master_index["consumed"]:
                        matching_rows.append(row)
                        break
```

**Also fix extraction side** (line 442-443):
```python
# BEFORE:
if translation:
    content_key = (stringid, translation)    # ← Empty stringid → key is ("", "text")

# AFTER:
if translation:
    content_key = (stringid or "", translation)  # ← Explicitly empty string (same behavior, just explicit)
```

**Test:** Before fix, run compilation and count orphaned rows. After fix, orphaned should drop to near-zero.

---

### Change 2: Add Manager STATUS Dropdown to Master Files

**File:** `core/processing.py` — in `process_sheet()` or wherever master user columns are finalized
**Impact:** Fixes "no dropdown selection" part of bug #1

**What exists:**
- `MANAGER_STATUS_OPTIONS = ["FIXED", "REPORTED", "CHECKING", "NON ISSUE"]` (config.py:343)
- `add_manager_dropdown()` function (excel_ops.py:1230-1259)
- Called from `get_or_create_user_status_column()` — but ONLY when creating NEW columns

**Problem:** When columns already exist from the template, `get_or_create_user_status_column()` finds the existing column and returns WITHOUT adding the dropdown.

**Fix:** After ALL user data is restored, re-apply dropdown validation to ALL `STATUS_{username}` columns:
```python
# At the END of master sheet processing (after restore_tester_data_to_master)
for username in all_usernames:
    status_col = find_column_by_header(ws, f"STATUS_{username}")
    if status_col:
        add_manager_dropdown(ws, col=status_col, start_row=2, end_row=ws.max_row)
```

---

### Change 3: Beautiful Master File Formatting

**File:** `core/excel_ops.py` — new function `beautify_master_sheet()`
**Impact:** Fixes bug #3

**Design — Visual Dictionary Layout:**

```
┌─────────────┬─────────────┬─────────────┬───────────────────────────────┬─────────────────────────────────┐
│  CONTENT    │  CONTENT    │  CONTENT    │  ████ QA TESTER: Alice ████  │  ████ MANAGER: Alice ████      │
│  StringID   │  Korean     │  English    │  COMMENT  │ STATUS │ SCREEN │  STATUS   │ COMMENT             │
├─────────────┼─────────────┼─────────────┼───────────┼────────┼────────┼───────────┼─────────────────────┤
│  STR_001    │  한국어      │  English    │  typo     │ ISSUE  │ img.png│  FIXED    │ corrected           │
│  STR_002    │  한국어      │  English    │           │        │        │           │                     │
│  STR_003    │  한국어      │  English    │  wrong    │ ISSUE  │        │  CHECKING │ reviewing           │
└─────────────┴─────────────┴─────────────┴───────────┴────────┴────────┴───────────┴─────────────────────┘
```

**Color scheme:**
```python
# Content columns (static data)
CONTENT_HEADER_FILL = PatternFill("solid", fgColor="4472C4")    # Dark blue
CONTENT_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)

# QA Tester section header
TESTER_HEADER_FILL = PatternFill("solid", fgColor="70AD47")     # Green
TESTER_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)

# Manager section header
MANAGER_HEADER_FILL = PatternFill("solid", fgColor="ED7D31")    # Orange
MANAGER_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)

# Data row alternating fills
ROW_FILL_A = PatternFill("solid", fgColor="F2F2F2")            # Light gray
ROW_FILL_B = PatternFill("solid", fgColor="FFFFFF")            # White

# Status-specific cell colors (existing, keep)
ISSUE_FILL = PatternFill("solid", fgColor="FFC7CE")            # Light red
NO_ISSUE_FILL = PatternFill("solid", fgColor="C6EFCE")         # Light green
FIXED_FILL = PatternFill("solid", fgColor="B4C6E7")            # Light blue
CHECKING_FILL = PatternFill("solid", fgColor="FFE699")         # Light yellow
REPORTED_FILL = PatternFill("solid", fgColor="D9E2F3")         # Very light blue

# Borders
SECTION_BORDER = Border(
    left=Side(style="medium", color="000000"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF")
)
```

**Implementation:**
```python
def beautify_master_sheet(ws, user_columns_map: Dict[str, Dict[str, int]]):
    """
    Apply beautiful formatting to a master sheet.

    Groups columns visually:
    1. Content columns (blue headers) — StringID, Korean, Translation, etc.
    2. Per-user QA Tester section (green headers) — COMMENT, TESTER_STATUS, SCREENSHOT
    3. Per-user Manager section (orange headers) — STATUS (manager), MANAGER_COMMENT

    Adds:
    - Color-coded headers with section labels
    - Alternating row fills
    - Medium border between sections
    - Status-specific cell coloring
    - Auto-fit column widths
    """
```

**When to call:** After `restore_tester_data_to_master()` completes, call `beautify_master_sheet()` on each worksheet.

---

### Change 4: Add Debug Logging for Match Failures

**File:** `core/excel_ops.py`
**Lines:** Near 717-718 (orphan counting)

**Add logging to see EXACTLY which rows are orphaned and why:**
```python
if unmatched:
    print(f"    ⚠️ ORPHANED {len(unmatched)} content keys:")
    for ck in list(unmatched)[:10]:  # Show first 10
        users = list(sheet_data[ck].keys())
        has_manager = any("manager_status" in sheet_data[ck][u] for u in users)
        print(f"      Key={ck}, Users={users}, HasManagerData={has_manager}")
```

---

## Implementation Order

```
1. Change 4: Debug logging (5 min)        ← See current failure rate
2. Change 1: Fix matching logic (30 min)  ← Core fix, eliminates data loss
3. Change 2: Manager dropdown (15 min)    ← Re-apply dropdowns after restore
4. Change 3: Beautiful formatting (45 min) ← Visual polish
```

**Total estimated changes:** ~150 lines across 2 files

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `core/excel_ops.py` | Fix matching (Change 1), Debug logging (Change 4), Beautify function (Change 3) | 669-708, 717-718, new function |
| `core/processing.py` | Re-apply manager dropdown after restoration (Change 2) | After restore call |

---

## Test Plan

| # | Test | Expected |
|---|------|----------|
| 1 | Compile Quest with manager data in old master | Manager STATUS and COMMENT appear in new master |
| 2 | Compile Item with manager data in old master | Same — confirms systemic fix |
| 3 | Check STATUS_{user} columns have dropdown | FIXED, REPORTED, CHECKING, NON ISSUE available |
| 4 | Check visual formatting | Blue content headers, green tester headers, orange manager headers |
| 5 | Count orphaned rows before/after fix | Should drop from many to near-zero |
| 6 | Group header rows (empty StringKey) matched | Fallback by translation should catch these |

---

## Progress Tracker Verdict

**TRACKER IS CORRECT** — No bugs found in progress tracking logic:
- Same `count_sheet_stats()` for all categories
- Quest maps to itself (identity mapping)
- All STATUS variants handled
- Manager stats aggregation uses same column detection
- Extensive debug logging available via `TRACKER_UPDATE_DEBUG.log`

**If tracker shows wrong numbers:** The issue is UPSTREAM (master file has lost manager data due to the matching bug above). Fix the master compilation → tracker automatically gets correct data.

---

*Plan ready for implementation. Approx 150 lines, 2 files, 4 changes.*
