# Investigation Session: Tracker Stats MISS Issue

**Date:** 2026-01-23
**Status:** WAITING FOR DEBUG LOG (code confirmed buggy, Master has data)
**Priority:** HIGH

---

## Problem Statement

The Progress Tracker (`LQA_Tester_ProgressTracker.xlsx`) shows incorrect stats:
- Both **tester stats** AND **manager stats** are MISSING
- Affects ALL categories (Quest, Dialog, Sequencer, etc.)
- Dialog and Sequencer show **0**
- Other categories are "drastically low"
- Debug log shows `name/category MISS` entries

---

## Investigation Summary

### What Was Investigated

1. **Tester stats aggregation** - how QA file STATUS values are counted
2. **Manager stats aggregation** - how Master file STATUS_{User} values are counted
3. **Username parsing** - how folder names are parsed for usernames
4. **Two compilation paths** - compiler.py vs tracker_update.py
5. **Row matching logic** - how QA rows match to Master rows
6. **Daily entries population** - how stats get into the tracker

---

## Key Findings

### Finding #1: Stats Only Count MATCHED Rows

**Location:** `core/processing.py` lines 420-428

```python
master_row, match_type = find_matching_row_in_master(qa_row_data, master_index, category)

if master_row is None:
    result["match_stats"]["unmatched"] += 1
    continue  # ROW SKIPPED - NOT COUNTED IN STATS!

result["stats"]["total"] += 1  # Only counted if matched
```

**Impact:** If QA rows can't match Master rows, tester stats will be "drastically low" because unmatched rows are skipped entirely.

---

### Finding #2: Script Categories (Sequencer/Dialog) Pre-filter

**Location:** `core/processing.py` lines 394-407, `core/compiler.py` lines 929-931

```python
# Pre-filter: Only rows WITH status
if status_val and str(status_val).strip():
    rows_to_process.append(qa_row)

# If no rows have STATUS
if universe["row_count"] == 0:
    print(f"  [SKIP] No rows with STATUS found in any QA file")
    return daily_entries  # EMPTY LIST = 0 stats!
```

**Impact:** Sequencer/Dialog categories return 0 stats if no QA rows have STATUS values.

---

### Finding #3: Two Different Compilation Paths

| Aspect | Full Compilation (`compiler.py`) | Tracker-Only (`tracker_update.py`) |
|--------|----------------------------------|-------------------------------------|
| **QA Folder** | `QAfolder/` | `TrackerUpdateFolder/QAfolder/` |
| **Master Folder** | `Masterfolder_EN/`, `CN/` | `TrackerUpdateFolder/Masterfolder_EN/`, `CN/` |
| **Tester Stats** | Counts only MATCHED rows | Counts directly from STATUS column |
| **Manager Dates** | Uses today's date | Uses Master file mtime |
| **Matching Required** | YES | NO |

**Impact:** If matching is broken, full compilation shows low stats, but tracker-only would show correct stats!

---

### Finding #4: Matching Logic by Category

| Category | Primary Match (Exact) | Fallback Match |
|----------|----------------------|----------------|
| **Standard** (Quest, Knowledge, etc.) | `(STRINGID, Translation)` | `Translation` only |
| **Item** | `(ItemName, ItemDesc, STRINGID)` | `(ItemName, ItemDesc)` |
| **Contents** | `INSTRUCTIONS` | None |
| **Script** (Sequencer, Dialog) | `(Translation, EventName)` | `EventName` only |

**Why Matching Can Fail:**
1. Missing required columns (STRINGID, EventName, Text)
2. Empty required fields
3. Content mismatch between QA file and Master template
4. Row already consumed (duplicate handling)

---

### Finding #5: Manager Stats Category Mismatch (Potential Bug)

**Location:** `tracker/data.py` lines 207-231

```python
# Second loop uses TARGET category for key
for category, users in manager_stats.items():  # category = "Script"
    key = (str(file_date), user, category)  # KEY = (date, user, "Script")

    if key in existing_date_user_cat:  # But rows have "Sequencer"/"Dialog"!
        # NEVER MATCHES because key mismatch
```

**Impact:** The second loop in `update_daily_data_sheet()` can't find existing rows because it looks for "Script" but rows are stored as "Sequencer" or "Dialog".

**Note:** The FIRST loop handles this correctly by converting category before lookup. The second loop is redundant for normal compilation mode.

---

### Finding #6: No Per-Row Debug Logging (Fixed!)

Match failures were **SILENT**. Only aggregate counts were logged.

**Fix Applied:** Added granular debug logging to `core/matching.py`:
- Logs index building (keys indexed, sample keys)
- Logs each unmatched row with details (STRINGID, Translation, EventName)
- Output written to `MATCHING_DEBUG.log`

---

## Data Flow Diagrams

### Tester Stats Flow

```
QAfolder/Username_Category/file.xlsx
    ↓
discover_qa_folders() - parse folder name
    ↓ username, category
process_category() - for each QA folder
    ↓
process_sheet() - for each sheet
    ├─ build_master_index() - create lookup index from Master
    ├─ FOR EACH QA ROW:
    │   ├─ extract_qa_row_data() - get STRINGID, Translation
    │   ├─ find_matching_row_in_master() - lookup in index
    │   │   ├─ MATCH FOUND → count stats
    │   │   └─ NO MATCH → skip row (stats not counted!)
    │   └─ Count: issue, no_issue, blocked, korean
    ↓
daily_entry = {date, user, category, issues, no_issue, blocked, korean, done, word_count}
    ↓
update_daily_data_sheet() - write to _DAILY_DATA
```

### Manager Stats Flow

```
Masterfolder_EN/Master_{Category}.xlsx
    ↓
collect_manager_stats_for_tracker()
    ├─ FOR EACH CATEGORY:
    │   ├─ target = get_target_master_category(category)  # Sequencer→Script
    │   ├─ master_path = Master_{target}.xlsx
    │   ├─ Find STATUS_{User} column headers
    │   └─ Count: FIXED, REPORTED, CHECKING, NON-ISSUE per user
    ↓
manager_stats = {
    "Script": {"Alice": {fixed: 3, reported: 1, ...}},
    "Quest": {"Bob": {fixed: 1, ...}}
}
    ↓
update_daily_data_sheet()
    ├─ First loop: For each daily_entry
    │   ├─ lookup_category = get_target_master_category(entry["category"])
    │   ├─ user_stats = manager_stats[lookup_category][user]
    │   └─ Write tester stats + manager stats to row
    └─ Second loop: Manager-only rows (has key mismatch bug)
```

---

## Debug Files Created/Enhanced

| File | Purpose |
|------|---------|
| `MATCHING_DEBUG.log` | **NEW** - Per-row match failures with details |
| `MANAGER_STATS_DEBUG.log` | Manager stats collection + lookup phase |
| Console output | `[DEBUG] daily_entry:` lines, `[WARN]` for unmatched |

---

## Potential Root Causes (Ranked)

1. **HIGH: Row matching failing** - QA rows can't match Master rows → stats skipped
2. **HIGH: Script pre-filter** - No STATUS values in Sequencer/Dialog → 0 stats
3. **MEDIUM: Master file missing** - No Master_{Category}.xlsx → NO_CAT miss
4. **MEDIUM: STATUS columns missing** - No STATUS_{User} headers → NO_USER miss
5. **LOW: Double-counting** - Clustered categories get same manager stats (documented, not urgent)

---

## Next Steps to Debug

1. **Run compilation** and check `MATCHING_DEBUG.log` for unmatched rows
2. **Check console output** for `[WARN] ... UNMATCHED` messages
3. **Verify Master files exist** in `Masterfolder_EN/` and `Masterfolder_CN/`
4. **Verify STATUS_{User} columns** exist in Master files
5. **Compare QA file content** with Master template content

---

## Files Modified

| File | Changes |
|------|---------|
| `core/matching.py` | Added granular debug logging for match failures |
| `docs/ISSUE_TRACKER_MATCHING.md` | Initial issue documentation |
| `docs/ISSUE_TRACKER_INVESTIGATION_SESSION.md` | This file - full investigation notes |

---

## Category Mapping Reference

```python
CATEGORY_TO_MASTER = {
    "Skill": "System",      # Skill → Master_System.xlsx
    "Help": "System",       # Help → Master_System.xlsx
    "Gimmick": "Item",      # Gimmick → Master_Item.xlsx
    "Sequencer": "Script",  # Sequencer → Master_Script.xlsx
    "Dialog": "Script",     # Dialog → Master_Script.xlsx
}
# Others map to themselves: Quest→Quest, Knowledge→Knowledge, etc.
```

---

## Code References

| Location | Description |
|----------|-------------|
| `core/compiler.py:293-408` | `collect_manager_stats_for_tracker()` |
| `core/compiler.py:874-1131` | `process_category()` |
| `core/compiler.py:1080-1098` | Daily entry creation |
| `core/processing.py:305-660` | `process_sheet()` |
| `core/processing.py:420-434` | Match check and stats counting |
| `core/matching.py:195-320` | `build_master_index()` |
| `core/matching.py:322-427` | `find_matching_row_in_master()` |
| `tracker/data.py:75-232` | `update_daily_data_sheet()` |
| `tracker/data.py:139-177` | First loop - correct category handling |
| `tracker/data.py:207-231` | Second loop - has key mismatch issue |

---

## Session 2: Deep Investigation (2026-01-23)

### Key Finding from Log Analysis

**Master_Script.xlsx STATUS_{User} columns are EMPTY across ALL rows, not just first 10.**

| Category | Sample (first 10 rows) | Final Counts | Status |
|----------|------------------------|--------------|--------|
| Character | `(empty)` | F=17 R=7 C=2 N=113 | ✓ Data exists in later rows |
| System | `(empty)` | F=29 R=0 C=0 N=27 | ✓ Data exists in later rows |
| **Script** | `(empty)` | **F=0 R=0 C=0 N=0** | ❌ No data ANYWHERE |

### Debug Logging Added

Added granular debug logging to diagnose the issue:

**1. `collect_manager_status()` in compiler.py:**
- Logs all headers found in Script sheets
- Logs COMMENT_, STATUS_ column detection
- Logs number of entries collected
- Logs STRINGID/EventName column detection

**2. `process_sheet()` in processing.py:**
- Logs manager_status keys available
- Logs QA MEMO column detection
- Logs first 5 row lookup attempts (tester comment, key, found status)

### To Run Debug

Run **full compilation** (not tracker update) to see the debug output:
```
python gui/app.py  # Then click "Compile"
```

Watch for:
```
[DEBUG] collect_manager_status: Sequencer/English Script
  All headers: [...]
  COMMENT_ cols: [...]
  STATUS_ cols: [...]
  Collected entries: X

[DEBUG] process_sheet: Sequencer/English Script/유지윤
  manager_status keys (sheet-level): X
  QA MEMO column: X
  [DEBUG] Row 2: tester_comment='...'
  [DEBUG] Row 2: key=(...), found=True/False
```

### Possible Root Causes

1. **No COMMENT_{User} columns in Master_Script.xlsx** - Manager status collection requires tester comments
2. **MEMO column not found in QA files** - Lookup requires MEMO text
3. **EventName mismatch** - Key uses EventName, if different between old/new build, no match
4. **Manager never filled in status** - Not a bug, just missing data

### Next Steps

1. Run full compilation with debug logs
2. Check if COMMENT_{User} columns exist in Master_Script.xlsx
3. Check if QA MEMO column has text
4. Verify EventName consistency between QA and Master

---

## Session 3: Code Bug Confirmed (2026-01-23)

### CRITICAL DISCOVERY

**User confirmed Master_Script.xlsx HAS the data:**
> "masterfile look fine. i see the comment i see the status i see the people i see the matching manager status/comments as well"

**This confirms: CODE BUG, not missing data.**

The code reads the STATUS_{User} columns as empty, but the actual file contains data. Something in the collection logic is failing silently.

### Status: WAITING FOR DEBUG LOG

**Current Status:** `WAITING_FOR_DEBUG_LOG`

### What Was Done

1. Added automatic debug logging to `SCRIPT_DEBUG.log` file
2. Logging added to both `core/compiler.py` and `core/processing.py`
3. Debug functions: `_script_debug_log()`, `_script_debug_flush()`, `_script_debug_clear()`
4. Log is cleared at start of each compilation, writes automatically

### Files Modified (Commit on GitHub)

| File | Changes |
|------|---------|
| `core/compiler.py` | Added Script debug logging in `collect_manager_status()` |
| `core/processing.py` | Added Script debug logging in `process_sheet()` |

### User Action Required

1. **Download updated files** from GitHub:
   - `core/compiler.py`
   - `core/processing.py`
2. **Run FULL compilation** (not tracker-only update)
3. **Send `SCRIPT_DEBUG.log`** file (created in QACompilerNEW folder)

### What the Debug Log Will Show

The log captures:

**Collection Phase (`[COLLECT]`):**
```
[HH:MM:SS] [COLLECT] Sequencer/English Script
[HH:MM:SS]   All headers: [list of all column headers]
[HH:MM:SS]   COMMENT_ cols: {user: col_idx, ...}
[HH:MM:SS]   STATUS_ cols: {user: col_idx, ...}
[HH:MM:SS]   STRINGID col: X
[HH:MM:SS]   EventName col: X
[HH:MM:SS]   Collected entries: N
```

**Processing Phase (`[PROCESS]`):**
```
[HH:MM:SS] [PROCESS] Sequencer/English Script/유지윤
[HH:MM:SS]   manager_status keys (sheet-level): N
[HH:MM:SS]   Sample keys: [(stringid, comment), ...]
[HH:MM:SS]   QA MEMO column: X
[HH:MM:SS]   [DEBUG] Row 2: tester_comment='...'
[HH:MM:SS]   [DEBUG] Row 2: key=(...), found=True/False
```

### What to Look For (Scenarios)

**Scenario A: No COMMENT_ columns found**
```
COMMENT_ cols: {}
```
→ Bug: Manager status collection requires COMMENT_{User} columns but they're not being detected

**Scenario B: COMMENT_ columns found but 0 entries collected**
```
COMMENT_ cols: {'유지윤': 5, ...}
Collected entries: 0
```
→ Bug: Columns exist but iteration logic isn't capturing the data

**Scenario C: Entries collected but not found during lookup**
```
Collected entries: 50
...
[DEBUG] Row 2: key=(...), found=False
```
→ Bug: Keys don't match between collection and lookup (STRINGID/EventName mismatch)

**Scenario D: Everything looks correct**
```
Collected entries: 50
[DEBUG] Row 2: key=(...), found=True
```
→ Bug is elsewhere (tracker write phase)

### Hypothesis

Based on log analysis showing `F=0 R=0 C=0 N=0` for Script while other categories work:

1. **Most likely:** COMMENT_{User} columns in Master_Script.xlsx are not being detected (different header format?)
2. **Second:** EventName column not found (Script uses EventName, not STRINGID for matching)
3. **Third:** Manager status IS collected but keying is wrong during restoration

The debug log will definitively answer which scenario applies.

---

## Related Documentation

- [ISSUE_TRACKER_MATCHING.md](ISSUE_TRACKER_MATCHING.md) - Initial issue documentation
- [TECHNICAL_MATCHING_SYSTEM.md](TECHNICAL_MATCHING_SYSTEM.md) - Detailed matching logic
- [SESSION_TRACKER_MASTERFILE_UPDATE.md](SESSION_TRACKER_MASTERFILE_UPDATE.md) - Tracker update workflow
