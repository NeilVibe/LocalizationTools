# QACompiler Tracker Fix — Active Plan

**Started:** 2026-03-25
**Updated:** 2026-03-26
**Status:** IN PROGRESS — waiting for debug log from user

---

## Problem Statement

Progress Tracker PENDING count is inflated ("exploding"). The new masterfile-based pending system shows way more pending than expected, even after multiple fixes.

## What We Built (2026-03-25)

New two-tier issue tracking replacing the old formula-based pending:

| Metric | Source | Column in _DAILY_DATA |
|--------|--------|-----------------------|
| Done, No Issue, Blocked, Korean | QA files (unchanged) | 5, 7, 8, 14 |
| Issues (overall from QA) | QA files (unchanged) | 6 |
| Fixed, Reported, Checking, NonIssue | Old aggregate_manager_stats (unchanged) | 9-12 |
| **Issues (displayed on TOTAL)** | **NEW: masterfile TESTER_STATUS_{user}=ISSUE** | 15 |
| **Pending (displayed on TOTAL)** | **NEW: masterfile TESTER_STATUS=ISSUE + STATUS empty/CHECKING** | 16 |
| ActiveFixed/Reported/Checking/NonIssue | NEW: masterfile paired columns | 17-20 |

### Files Created/Modified

| File | What |
|------|------|
| `tracker/masterfile_pending.py` | NEW — reads latest masterfiles, returns paired status counts |
| `tracker/data.py` | MODIFIED — 6 new columns (15-20) in _DAILY_DATA |
| `tracker/total.py` | MODIFIED — Issues/Pending from masterfile, removed old formula |
| `core/tracker_update.py` | MODIFIED — wired into flat_dump + tracker-only paths |
| `core/compiler.py` | MODIFIED — wired into main compile path |
| `tests/test_masterfile_pending.py` | NEW — 9 unit tests |
| `tests/test_active_pending_integration.py` | NEW — 4 integration tests |
| `tests/test_proof_overall_vs_active.py` | NEW — 3 proof tests |

### Fixes Applied (8 review fixes + 3 additional)

1. Workload data migration: find columns by header name, not offset
2. Flat dump EN/CN detection: walk ancestors, not parent.name
3. Empty row guard: `if not any(row)` for iter_rows
4. Manager-only zero-init for cols 15-20
5. Stale comment updated to "20 columns"
6. Fallback guard: only trigger when no master files exist
7. Username .strip() on extraction
8. Active data in debug logging
9. Script/Face categories excluded from active pending
10. Master category dedup (Item+Gimmick counted once)
11. Old Pending formula removed — Issues/Pending now fully masterfile-based

---

## Current Issue: Pending Bloat

**Symptom:** Pending count is much higher than expected, even with:
- Fresh tracker (erased each time)
- Only 1 masterfile per category (manually verified)
- Script/Face excluded
- Dedup fix applied

**Diagnosis status:** Debug log system added (v055h). Writes `MASTERFILE_PENDING_DEBUG.log` to SCRIPT_DIR. Shows:
- Which masterfiles found
- Per-sheet: which TESTER_STATUS/STATUS columns, for which users
- Raw STATUS value distribution per user
- Sample rows
- Per-user per-category totals

**WAITING FOR:** User to upload the log file.

### Hypotheses (to check with log)

1. **STATUS_{user} contains tester values ("ISSUE") not manager responses** — `_classify_status` treats unknown values as pending. If STATUS_{user} still has "ISSUE" (never overwritten by manager), it counts as pending.
2. **Multiple testers per masterfile** — each tester's TESTER_STATUS column counted independently. If 5 testers each marked 200 rows, total = 1000 issues.
3. **Old tester columns preserved** — masterfile rebuild preserves ALL TESTER_STATUS columns from previous compilations. Inactive testers' old issues still counted.
4. **Unexpected STATUS values** — the log will show exact distribution of raw STATUS values to identify what's being classified as pending.

---

## Phase 2: Masterfile Compilation Data Loss Investigation

**Symptom:** User's colleague reports data loss during masterfile compilation — previous master data not preserved.

**Diagnosis plan:**
1. Add comprehensive logging to `extract_tester_data_from_master()` and `restore_tester_data_to_master()` in `core/excel_ops.py`
2. Log: how many entries extracted, how many restored, how many orphaned
3. Log: matching key failures (StringID mismatch, translation text change)
4. Log: content key collisions (duplicate rows with different manager data)
5. Write to `MASTERFILE_COMPILE_DEBUG.log` in SCRIPT_DIR

**Known data loss scenarios (from code review):**
- Translation text changed between compilations → old tester data orphaned
- Translation column header changed in generator → ALL data lost for that category
- Tester changed their comment → manager STATUS/COMMENT cleared (intentional)
- >50% orphan rate → .bak preserved (safety net exists)

**Action:** Build a similar debug log system for the compilation pipeline AFTER solving the pending bloat.

---

## Execution Order

```
1. [WAITING] User uploads MASTERFILE_PENDING_DEBUG.log
2. [TODO]    Analyze log — find root cause of pending bloat
3. [TODO]    Fix root cause
4. [TODO]    Verify fix with user
5. [TODO]    Remove debug logging (or make it optional)
6. [TODO]    Build compilation debug log system
7. [TODO]    User tests compilation with debug log
8. [TODO]    Analyze compilation log for data loss
9. [TODO]    Fix any compilation issues found
10. [TODO]   Final cleanup + memory update
```

---

## Build History

| Build | Commit | What |
|-------|--------|------|
| v055 | f50304a-7595265 | Initial feature: 5 tasks, 15 tests |
| v055b | 6fa6c2c5 | Fix loguru → stdlib logging |
| v055c | c12c2b4c | Exclude Script/Face from active pending |
| v055d | 3aab36f2 | Issues/Pending fully masterfile-based, old formula removed |
| v055e | 31fbd37b | Dedup active data by master category |
| v055f | ccc38e77 | Diagnostic dump (first version) |
| v055g | 481e1afc | Full diagnostic log |
| v055h | 9f283648 | Fix log path for PyInstaller (SCRIPT_DIR) |
