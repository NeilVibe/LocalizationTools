# QACompiler: Active vs Overall Issue Tracking

**Date:** 2026-03-25
**Status:** APPROVED (brainstorm + tribunal validated)
**Scope:** Progress Tracker PENDING calculation redesign

---

## Problem

PENDING issues grow forever. QA files contain stale issues for StringIDs that no longer exist in the game data. When masterfiles are recompiled, those rows vanish from the master but persist in QA files. The tracker blindly counts all QA file issues, so PENDING inflates with unresolvable items.

## Core Concept: Two Tiers of Issue Counting

### OVERALL ISSUES (from QA files — existing behavior, unchanged)
- Total issues the tester ever reported across all QA files
- Includes stale/outdated issues for rows no longer in the game
- Historical record of tester productivity
- Source: `count_sheet_stats()` scanning STATUS column in QA xlsx files

### ACTIVE ISSUES (from latest masterfile per category — NEW)
- Issues that currently exist in the most recent masterfile
- Subset of OVERALL — only what's "alive" in the game data
- Source: latest `Master_*.xlsx` per unique category from `Masterfolder_EN`/`CN`

### STALE ISSUES (derived)
- `STALE = OVERALL - ACTIVE`
- Issues that were reported but no longer exist in the masterfile
- Diagnostic signal — high stale count means game data changed significantly

## Masterfile "Living Dataset" Construction

1. Scan `Masterfolder_EN` and `Masterfolder_CN`
2. Find all `Master_*.xlsx` files (skip `~$` temp files)
3. Extract category from filename: `Master_{category}.xlsx` -> `category`
4. Group by `(category, lang)` — e.g., `(Quest, EN)`, `(Item, CN)`
5. Per group, keep ONLY the most recent file by mtime
6. Skip Face category (non-standard filenames, already zeroed in tracker)
7. This set = the "living dataset"

## Paired Status Reading (from masterfile)

Each masterfile row has two status columns per tester, on the SAME row:

| Column | Owner | Values |
|--------|-------|--------|
| `TESTER_STATUS_{username}` | Tester | ISSUE, NO ISSUE, BLOCKED, KOREAN, empty |
| `STATUS_{username}` | Manager | FIXED, REPORTED, CHECKING, NON-ISSUE, empty |

### Pairing Logic

For each row where `TESTER_STATUS_{username}` = "ISSUE":

| STATUS_{username} (Manager) | Counts As |
|---|---|
| _(empty)_ | **PENDING** |
| CHECKING | **PENDING** (still unresolved) |
| FIXED | **FIXED** |
| REPORTED | **REPORTED** |
| NON-ISSUE / NON ISSUE | **NON-ISSUE** |

Rows where `TESTER_STATUS_{username}` is NOT "ISSUE" are ignored (not an issue row for that tester).

### Per-Tester Output Structure

```
{
    "UserA": {
        "Quest": {
            "active_issues": 25,   # TESTER_STATUS = ISSUE in masterfile
            "pending": 10,         # manager empty or CHECKING
            "fixed": 8,
            "reported": 5,
            "checking": 3,         # subset of pending
            "nonissue": 2
        },
        "Item": { ... },
        ...
    }
}
```

## What Changes Where

### NEW: `tracker/masterfile_pending.py`
Single responsibility: read masterfiles, return paired status counts.

```
build_pending_from_masterfiles(
    masterfolder_en: Path,
    masterfolder_cn: Path,
    tester_mapping: dict
) -> dict[username, dict[category, StatusCounts]]
```

- Scans both folders, dedup to latest per (category, lang)
- Reads `TESTER_STATUS_{user}` + `STATUS_{user}` columns per sheet
- Uses `read_only=True` + `iter_rows(values_only=True)` (NEVER ws.cell())
- Skips STATUS sheet, skips Face category
- Returns pure data structure — no file writes, no side effects

### MODIFIED: `tracker/data.py`
- Add `masterfile_pending` column to `_DAILY_DATA` (new column after existing ones)
- `update_daily_data_sheet()` writes the new column from masterfile data

### MODIFIED: `tracker/total.py`
- `read_latest_data_for_total()` reads new `masterfile_pending` column
- PENDING on TOTAL sheet uses `masterfile_pending` instead of `max(0, issues - fixed - reported - nonissue)`
- Keep OVERALL ISSUES column (from QA files) for reference
- Script types (Sequencer/Dialog/Face) still zeroed as before

### MODIFIED: `core/tracker_update.py`
- Both `update_tracker_only()` and `update_tracker_flat_dump()` call `build_pending_from_masterfiles()`
- Pass result into `update_daily_data_sheet()`
- For flat_dump: masterfile folders discovered during `discover_flat_dump()` are reused
- For standard: reads from `MASTER_FOLDER_EN`/`CN` (compilation output folders)

### UNCHANGED
- QA file scanning (`count_sheet_stats`, `count_qa_folder_stats`) — untouched
- Masterfile compilation (`compiler.py`) — untouched
- Done/total_rows/word_count calculations — untouched
- DAILY sheet — untouched (uses _DAILY_DATA as before)

## Category Clustering Awareness

Master filenames use clustered categories:

| Master File | Contains |
|---|---|
| Master_Script.xlsx | Sequencer + Dialog sheets |
| Master_System.xlsx | System + Help sheets |
| Master_Item.xlsx | Item + Gimmick sheets |
| All others | Single category per file |

The reader must handle multi-sheet masters correctly — scan ALL sheets (except STATUS), using `TESTER_STATUS_{user}` columns found in each sheet.

## Edge Cases

1. **No masterfile for a category** — ACTIVE = 0, all QA issues are stale for that category
2. **Masterfile has no TESTER_STATUS columns** — Category was never compiled with QA data, skip
3. **Manager status typos** — Normalize to uppercase, handle "NON-ISSUE" and "NON ISSUE" variants
4. **Empty masterfile sheets** — Skip (max_row < 2)
5. **Tester not in tester_mapping** — Default to "EN" (existing behavior)
6. **Script types** — Already zeroed in total.py, keep that behavior

## Timing Note

If tracker update runs WITHOUT recompiling masterfiles first, the masterfile may be stale relative to QA files. This is acceptable — PENDING reflects the compiled state, not the raw QA state. The QA file OVERALL count still shows the full picture.
