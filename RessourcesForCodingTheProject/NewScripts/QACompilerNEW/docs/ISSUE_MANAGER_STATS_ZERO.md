# ISSUE: Manager Stats Show ZERO (Tester Issues Not Counted)

**Status:** OPEN - AWAITING USER LOG
**Priority:** CRITICAL
**Date:** 2026-01-23
**Updated:** 2026-01-23 20:50 (ULTRA-GRANULAR LOGGING IMPLEMENTED)
**Reported By:** User
**Commit:** 94069ec

---

## CURRENT STATUS

### What's Done ✅
1. **Ultra-granular logging implemented** in `core/compiler.py`
2. **Test scenarios created** in `tests/test_user_scenario.py`
3. **Code pushed to GitHub** - commit 94069ec

### What's Needed ⏳
1. User copies updated `core/compiler.py` to Windows
2. User runs full compilation on REAL data
3. User sends `MANAGER_STATS_DEBUG.log` file
4. Claude analyzes log to find exact root cause

### File to Update on Windows
```
core/compiler.py  →  Copy to Windows QACompilerNEW folder
```

### Log File to Send Back
```
MANAGER_STATS_DEBUG.log  →  Created after running compilation
```

---

## Problem Statement

**Tester submits issues → Manager sees them in Master file → But tracker shows 0 pending**

The Progress Tracker shows **ZERO** manager stats (F=0 R=0 C=0 N=0) for certain categories, even though:
1. Testers have submitted QA files with issues
2. Manager can SEE the issues in the Master file
3. Manager has NOT processed them yet (should show as REPORTED/pending)

---

## Latest Debug Changes (2026-01-23)

Added MORE granular logging to `core/compiler.py`:

1. **ALL non-empty STATUS values** - Now scans ENTIRE column, not just first 10 rows
2. **Row numbers** - Shows exact row where each value is found
3. **Total count** - Shows total non-empty values per user
4. **ZERO warning** - Explicit warning if column is completely empty
5. **Unrecognized statuses** - Logs any STATUS value that's not FIXED/REPORTED/CHECKING/NON-ISSUE

### To Run Debug

1. Copy updated `core/compiler.py` to Windows
2. Run **full compilation** (not tracker-only update)
3. Check `MANAGER_STATS_DEBUG.log`
4. Send log file

### What To Look For

**Scenario A: STATUS column is empty**
```
[유지윤] WARNING: ZERO non-empty STATUS values in column 5!
Script/유지윤: F=0 R=0 C=0 N=0 | PENDING=47
```
→ Manager hasn't filled in STATUS yet, but there ARE 47 pending issues

**Scenario B: STATUS has values but not recognized**
```
[유지윤] TOTAL non-empty STATUS values: 47
UNRECOGNIZED STATUS VALUES: ['row5:ISSUE', 'row10:이슈']
Script/유지윤: F=0 R=0 C=0 N=0
```
→ Values exist but use different text (maybe Korean or different format)

**Scenario C: Column detection wrong**
```
ALL HEADERS: [col1:Korean, col2:Translation, col3:STATUS, col4:COMMENT]
STATUS_ columns: NONE FOUND
```
→ Header format is "STATUS" not "STATUS_{User}" - different structure

**New: PENDING count**
Now logs `PENDING=X` which is:
- Rows where COMMENT_{User} has content (tester wrote something)
- BUT STATUS_{User} is empty or not FIXED/NON-ISSUE (manager hasn't resolved)

---

## Evidence from Logs

### Script Category - ALL ZEROS

From `LOG FOR CLAUDE 0123 1647.txt` lines 521-534:

```
=== SCRIPT [EN] ===
Master file: C:\Users\PEARL\Desktop\QACompiler_v26.122.1852_Source\Masterfolder_EN\Master_Script.xlsx
Sheets found: ['STATUS', 'English Script', 'Work Transform']
  Sheet 'English Script': rows=1778, cols=16
    STATUS_ columns: ['유지윤', '조서영']
    Sample STATUS values: {'유지윤': ['(empty)'], '조서영': ['(empty)']}
    Script/유지윤: F=0 R=0 C=0 N=0    ← ALL ZEROS!
    Script/조서영: F=0 R=0 C=0 N=0    ← ALL ZEROS!
  Sheet 'Work Transform': rows=7954, cols=20
    STATUS_ columns: ['김정원', '김찬용', '황하연']
    Sample STATUS values: {'김정원': ['(empty)'], '김찬용': ['(empty)'], '황하연': ['(empty)']}
    Script/김정원: F=0 R=0 C=0 N=0   ← ALL ZEROS!
    Script/김찬용: F=0 R=0 C=0 N=0   ← ALL ZEROS!
    Script/황하연: F=0 R=0 C=0 N=0   ← ALL ZEROS!
```

### Compare: Quest Category - HAS DATA

```
=== QUEST [EN] ===
  Sheet 'Main Quest': rows=990, cols=44
    STATUS_ columns: ['김선우', '김정원', '김찬용', '김헌동', '성가은', '이재환', '장어진', '황하연']
    Sample STATUS values: {'김선우': ['(empty)'], '김정원': ['(empty)'], '김찬용': ['FIXED'], ...}
    Quest/김찬용: F=13 R=1 C=0 N=34   ← HAS DATA!
    Quest/성가은: F=23 R=2 C=0 N=36   ← HAS DATA!
```

### MISS Details

```
MISS DETAILS: ['유지윤/Sequencer:ZERO', '조서영/Sequencer:ZERO', '황하연/Dialog:ZERO', '김정원/Dialog:ZERO', ...]
```

---

## Root Cause Hypothesis

The code reads `STATUS_{User}` columns to count manager stats. For Script category:
- **Sample STATUS values show ALL `(empty)`** - but user confirms file HAS actual values
- Code is NOT reading the STATUS values correctly for Script

**Possible causes:**
1. Column detection bug specific to Script category
2. Row iteration bug (starting at wrong row?)
3. Sheet name mismatch (looking at wrong sheet?)
4. STATUS column header format different in Script files

---

## User Confirmation

> "masterfile look fine. i see the comment i see the status i see the people i see the matching manager status/comments as well"

This confirms: **DATA EXISTS IN FILE, CODE IS NOT READING IT**

---

## Affected Users/Categories

From MISS DETAILS:
- 유지윤/Sequencer
- 조서영/Sequencer
- 황하연/Dialog
- 김정원/Dialog
- 김찬용/Dialog
- 김정원/Quest (ZERO stats)
- 김헌동/Quest (ZERO stats)
- 김선우/Knowledge (ZERO)
- 유지윤/Knowledge (ZERO)
- 장어진/Knowledge (ZERO)
- 조서영/Knowledge (ZERO)

---

## Files to Investigate

| File | Function | What to Check |
|------|----------|---------------|
| `core/compiler.py` | `collect_manager_stats_for_tracker()` | How STATUS_ columns are detected and read |
| `core/compiler.py` | Line ~350-400 | Sample STATUS value collection logic |

---

## Debug Questions

1. **Is the STATUS_ column being found?** → Yes, logs show `STATUS_ columns: ['유지윤', '조서영']`
2. **Are rows being iterated?** → Shows `rows=1778` so data exists
3. **Why are ALL sample values (empty)?** → THIS IS THE BUG LOCATION

---

## Next Steps

1. Add debug logging to show EXACT row/column being read for STATUS values
2. Print first 10 non-empty STATUS values found
3. Check if there's a row offset issue (headers at wrong row?)
4. Check if column index is off-by-one

---

## Session History

| Date | Action | Result |
|------|--------|--------|
| 2026-01-23 | Initial investigation | Found case sensitivity bug (NOT THE ROOT CAUSE) |
| 2026-01-23 | User reports still broken | Confirmed - Script shows ALL ZEROS |
| 2026-01-23 | Log analysis | Found Sample STATUS always (empty) for Script |
| 2026-01-23 20:48 | **ULTRA-GRANULAR LOGGING** | Implemented full logging - every row, every cell |
| 2026-01-23 20:50 | **Pushed to GitHub** | Commit 94069ec - awaiting user test |

---

## Related Files

- `LOG FOR CLAUDE 0123 1647.txt` - Full debug log with ZEROS
- `LOGS FOR CLAUDE 0123 TRACKER.txt` - Tracker update log
- `ISSUE_TRACKER_INVESTIGATION_SESSION.md` - Previous investigation (WRONG FIX)

---

## What The New Logging Captures

The `MANAGER_STATS_DEBUG.log` file will show:

```
================================================================================
MANAGER STATS COLLECTION - ULTRA GRANULAR DEBUG LOG
================================================================================

[CONFIG] All settings, folder paths, category mappings
[CONFIG] Tester mapping: who belongs to EN vs CN

[CATEGORY LOOP] For each category:
    - Target master file path
    - File exists? Yes/No
    - Already processed? Yes/No

[SHEET] For each sheet in workbook:
    - All column headers with type identification
    - STATUS_{User} columns found
    - COMMENT_{User} columns found
    - TESTER_STATUS_{User} columns found

[ROW] For each data row:
    [ROW 5] ID=EVT001
      [유지윤] STATUS='FIXED' COMMENT='Typo' -> COUNTED as FIXED
      [조서영] STATUS='' COMMENT='Issue here' -> PENDING (no manager status)

[SUMMARY] Per-sheet and global totals
    - Total FIXED/REPORTED/CHECKING/NON-ISSUE
    - Total PENDING (issues awaiting manager review)
    - Any UNRECOGNIZED status values
```

---

## Quick Reference

| Item | Value |
|------|-------|
| **Updated File** | `core/compiler.py` |
| **GitHub Commit** | 94069ec |
| **Output Log** | `MANAGER_STATS_DEBUG.log` |
| **Test File** | `tests/test_user_scenario.py` |
| **Issue Doc** | This file |
