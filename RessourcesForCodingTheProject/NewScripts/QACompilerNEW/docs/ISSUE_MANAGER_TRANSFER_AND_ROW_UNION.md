# ISSUE: Manager Transfer Bug + Row Union Cleanup + Unified Data Model

**Date:** 2026-02-08
**Status:** IN PROGRESS
**Severity:** HIGH

---

## Overview

Three related changes to QACompiler master file generation:

1. **BUG FIX: Tester + Manager data move as ONE UNIT** (CRITICAL)
2. **CLEANUP: Remove old/new QA row coexistence** (row union removal)
3. **BEHAVIOR: Fresh QA file data ADD/OVERWRITE logic** (already partially in place)

---

## The Unified Data Model

### Core Principle

In the master file, each row contains tester AND manager data for each user.
They are ONE UNIT. They must ALWAYS move together. Never separate them.

```
Master Row = {
    stringid,
    translation,
    per_user: {
        "Alice": {
            tester_comment,      ← QA tester wrote this
            tester_status,       ← QA tester set this (ISSUE/NO ISSUE/BLOCKED/KOREAN)
            screenshot,          ← QA tester attached this
            manager_status,      ← Manager responded with this (FIXED/REPORTED/CHECKING/NON-ISSUE)
            manager_comment      ← Manager wrote this
        }
    }
}
```

This unit is:
- **Collected** from old master as one bundle
- **Matched** to new template by (StringID + translation) or (translation only)
- **Applied** to the new master row all at once
- **Never split** — even if manager fields are empty, the unit stays intact

---

## The Full Data Flow

### Phase A: Collect Preserved Data From Old Master

Read old master before deleting it. For each row, collect the FULL unit:

```
OLD MASTER Row 5: StringID=1001, Translation="Kill 10 orcs"
  → Collect ONE UNIT:
    {
      stringid: "1001",
      translation: "Kill 10 orcs",
      users: {
        "Alice": {
          tester_comment: "typo here",
          tester_status: "ISSUE",
          screenshot: "img001.png",
          manager_status: "FIXED",
          manager_comment: "looks good now"
        }
      }
    }

Store under TWO keys:
  Primary:  ("1001", "Kill 10 orcs")         ← StringID + translation
  Fallback: ("__trans__", "Kill 10 orcs")    ← translation only (catches StringID changes)
```

If manager fields are empty, the unit still has tester data (and vice versa).
Empty fields are fine — the unit is the ROW, not just the non-empty parts.

### Phase B: Build New Master From Template

Delete old master. Create fresh master from newest QA template.
Strip tester columns (COMMENT, STATUS, SCREENSHOT) from template — these
get re-added per user during processing.

Cross-category tabs (e.g. Gimmick tabs when Item rebuilds) are preserved
verbatim via `preserved_sheets` mechanism. This is SEPARATE and UNTOUCHED.

### Phase C: Apply Preserved Data To New Master

For each row in the new master template:

```
NEW TEMPLATE Row 8: StringID=2001, Translation="Kill 10 orcs"

1. Try primary key: ("2001", "Kill 10 orcs") → MISS (StringID changed)
2. Try fallback:    ("__trans__", "Kill 10 orcs") → HIT!
3. Apply the FULL UNIT to row 8:
   - tester_comment, tester_status, screenshot
   - manager_status, manager_comment
   All land on the same row. All stay connected.
```

### Phase D: Process Fresh QA Files (ADD / OVERWRITE)

On top of the preserved data, we process FRESH QA files from testers.
Each QA file has the tester's CURRENT comment/status/screenshot.

**Three scenarios per row:**

#### Scenario 1: NO preserved data, QA file HAS data → ADD
```
Preserved: (empty for this row)
QA file:   comment="new issue found", status="ISSUE"
Result:    tester_comment="new issue found", tester_status="ISSUE"
           manager_status=(empty), manager_comment=(empty)
```
Fresh tester data is added. Manager fields stay empty (no response yet).

#### Scenario 2: Preserved data exists, QA file has SAME comment → KEEP ALL
```
Preserved: comment="typo here", manager_status="FIXED", manager_comment="looks good"
QA file:   comment="typo here", status="ISSUE"
Result:    tester_comment="typo here", tester_status="ISSUE"
           manager_status="FIXED", manager_comment="looks good"  ← PRESERVED
```
Tester comment unchanged → manager response still valid → keep everything.

#### Scenario 3: Preserved data exists, QA file has DIFFERENT comment → OVERWRITE + RESET MANAGER
```
Preserved: comment="typo here", manager_status="FIXED", manager_comment="looks good"
QA file:   comment="actually wrong word", status="ISSUE"
Result:    tester_comment="actually wrong word", tester_status="ISSUE"
           manager_status=(DELETED), manager_comment=(DELETED)
```
Tester wrote a NEW comment → the manager's old response was to the OLD comment
→ it's no longer relevant → manager fields get cleared.

**This ensures manager responses are always paired with the tester comment they
were responding to. If the tester changes their feedback, the manager needs to
re-review.**

### Phase E: Hide Rows/Columns/Sheets

Existing hiding logic (unchanged):
- Rows with no ISSUE status → hidden
- Rows resolved by manager (FIXED/NON-ISSUE) → hidden
- Empty COMMENT columns + paired columns → hidden
- Empty sheets → hidden

---

## What Changes

### Change 1: Unified Collection (compiler.py)

**File:** `core/compiler.py` — `collect_all_master_data()` (lines ~172-490)

**Before:** Collects ONLY manager data, keyed by `(StringID, tester_comment)`.
Tester data comes separately from QA files through a different system.

**After:** Collect ALL per-user data (tester + manager) as ONE UNIT per row,
keyed by `(StringID, translation)` primary + `(translation only)` fallback.

Also need to read the translation column during the header scan.
Currently reads: STRINGID, COMMENT_{User}, STATUS_{User}, MANAGER_COMMENT_{User}.
ADD: TESTER_STATUS_{User}, SCREENSHOT_{User}, translation column.

### Change 2: Unified Restoration (processing.py)

**File:** `core/processing.py` — `process_sheet()` (lines ~766-838)

**Before:** Tester data matched by translation (via `find_matching_row_in_master()`).
Manager data matched separately by `(StringID, comment)` key. Two independent systems.

**After:**
1. Preserved unit matched by `(StringID, translation)` or `(translation only)`
2. Apply the FULL unit (tester + manager) to the matched row
3. Then process fresh QA file data on top:
   - Same comment → keep manager data
   - Different comment → overwrite tester, clear manager
   - No preserved data → just add fresh tester data

### Change 3: Remove Row Union (excel_ops.py + compiler.py)

**File:** `core/excel_ops.py` — Remove `merge_missing_rows_into_master()` (line ~987)
**File:** `core/compiler.py` — Remove the call at line ~928

No more appending old QA rows to the master. No more coexistence of old/new rows.
The new template IS the master layout. Period.

### Change 4: Verify (no code change expected)

- Hiding logic → should still work (content-based, not row-origin-based)
- Cross-category tab preservation → untouched (`preserved_sheets` is separate)
- Styling → should still work (autofit, borders, etc.)

---

## What Does NOT Change

- `preserved_sheets` mechanism for cross-category tabs (excel_ops.py:850-941) — UNTOUCHED
- Transfer module (transfer.py) — transfers OLD QA → NEW QA files, separate from master building
- Hiding logic (processing.py:hide_empty_comment_rows) — content-based, still works
- Matching module (matching.py) — still used for row matching within sheets
- Generators — produce datasheets, unrelated to master compilation
- Tracker — reads from compiled master, unrelated to this fix

---

## Cross-Category Tab Preservation (CONFIRMED SAFE)

Clustered categories share master files:
```
Skill + Help       → Master_System.xlsx
Item + Gimmick     → Master_Item.xlsx
Sequencer + Dialog  → Master_Script.xlsx
```

The `preserved_sheets` mechanism in `get_or_create_master()` (excel_ops.py:850-941):
- When Sequencer rebuilds Master_Script.xlsx, Dialog tabs preserved verbatim
- Cell-by-cell copy with full styling, done BEFORE any processing
- Completely SEPARATE from `merge_missing_rows_into_master()`
- Removing row union does NOT affect this

**Confirmed safe.**

---

## Implementation Order

1. **Change 1:** Unified collection from old master (tester + manager as one unit)
2. **Change 2:** Unified restoration to new master (match by StringID+translation / translation)
3. **Change 2b:** ADD/OVERWRITE logic (same comment → keep manager, different → clear manager)
4. **Change 3:** Remove `merge_missing_rows_into_master()` (no more coexisting old/new rows)
5. **Change 4:** Verify hiding, tabs, styling all still work

---

## Test Scenarios

### Unified Data Transfer
- [ ] StringID same, translation same → full unit transferred (tester + manager)
- [ ] StringID changed, translation same → full unit transferred via fallback
- [ ] Manager fields empty → tester data still transferred (unit with empty manager)
- [ ] Tester fields empty → manager data still transferred (unit with empty tester)
- [ ] Multiple users per row → each user's unit independent

### ADD / OVERWRITE Logic
- [ ] No preserved data + QA file has comment → ADD tester data, manager empty
- [ ] Preserved data + QA file SAME comment → KEEP manager data
- [ ] Preserved data + QA file DIFFERENT comment → OVERWRITE tester, CLEAR manager
- [ ] Preserved data + QA file has NO comment → keep preserved as-is

### Row Union Removal
- [ ] New template fewer rows than old → no orphan rows appended
- [ ] Translation matches → data lands on correct row
- [ ] No translation match → data gracefully skipped (not appended)

### Cross-Category Tabs
- [ ] Item rebuild → Gimmick tabs preserved
- [ ] Sequencer rebuild → Dialog tabs preserved
- [ ] System rebuild → Skill/Help tabs preserved

### Hiding Logic
- [ ] Rows with ISSUE → visible
- [ ] Rows with NO ISSUE / BLOCKED / KOREAN → hidden
- [ ] Rows with FIXED / NON-ISSUE manager status → hidden
- [ ] Empty COMMENT columns → hidden with paired columns
- [ ] Empty sheets → hidden

---

## Files Reference

| File | Function | Change |
|------|----------|--------|
| `core/compiler.py:172` | `collect_all_master_data()` | REWRITE: collect full unit per row |
| `core/compiler.py:928` | merge call | REMOVE |
| `core/processing.py:766-838` | manager restoration in `process_sheet()` | REWRITE: unified restoration + ADD/OVERWRITE |
| `core/excel_ops.py:987` | `merge_missing_rows_into_master()` | REMOVE (or dead-code) |
| `core/excel_ops.py:850-941` | `preserved_sheets` in `get_or_create_master()` | UNTOUCHED |
| `core/matching.py` | `find_matching_row_in_master()` | UNTOUCHED (still used for row matching) |
| `core/transfer.py` | Transfer OLD→NEW QA files | UNTOUCHED |
| `config.py:205-212` | `CATEGORY_TO_MASTER` | UNTOUCHED |

---

*Document created 2026-02-08 for session continuity*
*Last updated: 2026-02-08 — full unified data model documented*
