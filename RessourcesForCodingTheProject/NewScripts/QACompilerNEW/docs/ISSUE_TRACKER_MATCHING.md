# ISSUE: Progress Tracker Matching Problems

**Status:** OPEN - Under Investigation
**Priority:** HIGH (MISS issue) / LOW (double-counting)
**Date:** 2026-01-23

> **See Also:** [ISSUE_TRACKER_INVESTIGATION_SESSION.md](ISSUE_TRACKER_INVESTIGATION_SESSION.md) for full investigation notes

---

## Summary

The Progress Tracker (`LQA_Tester_ProgressTracker.xlsx`) has inconsistent stat collection:
- **Some stats HIT** (appear correctly)
- **Some stats MISS** (don't appear at all)

The master file building works correctly. The problem is isolated to the **tracker logic**.

---

## Two Issues Identified

### Issue 1: MISS - Stats Not Appearing (HIGH PRIORITY)

**Symptom:** Some tester or manager stats don't appear in the tracker even though they exist in the source files.

**Suspected Cause:** Matching logic mismatch somewhere in the pipeline.

**Affected Files:**
- `tracker/data.py` - `update_daily_data_sheet()` - writes stats to `_DAILY_DATA`
- `core/compiler.py` - `collect_manager_stats_for_tracker()` - collects manager stats from Master files

**Debug Points:**
1. Does `daily_entries` contain all expected tester stats?
2. Does `manager_stats` contain all expected manager stats?
3. Does the lookup in `update_daily_data_sheet()` find the correct mapping?

**Debug Log Location:** `MANAGER_STATS_DEBUG.log` in QACompilerNEW folder

---

### Issue 2: Double-Counting for Clustered Categories (LOW PRIORITY)

**Symptom:** Clustered categories (Sequencer/Dialog → Script, Skill/Help → System) may have inflated manager stats.

**Cause:** Manager stats are stored at MASTER level (combined), but tester stats are stored at CATEGORY level (separate). When lookup happens, each category gets the FULL combined stats.

**Example:**
- Alice submits Sequencer (5 issues) and Dialog (3 issues)
- Manager marks 4 as FIXED in Master_Script.xlsx (combined)
- Tracker writes: Sequencer row gets fixed=4, Dialog row gets fixed=4
- TOTAL aggregates: 4+4=8 but actual is 4

**Status:** Documented. Will fix later. Not blocking.

---

## Data Flow Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TESTER STATS FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  QAfolder/Username_Category/          process_category()                     │
│  ├── file.xlsx                   ──►  Creates daily_entry:                   │
│  │   └── STATUS column                 {                                     │
│  │       - ISSUE                         "user": "Username",                 │
│  │       - NO ISSUE                      "category": "Sequencer",  ◄── ORIGINAL
│  │       - BLOCKED                       "issues": 5,                        │
│  │       - KOREAN                        "no_issue": 3,                      │
│  │                                       ...                                 │
│  │                                     }                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MANAGER STATS FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Masterfolder_EN/                 collect_manager_stats_for_tracker()        │
│  ├── Master_Script.xlsx      ──►  Returns manager_stats:                     │
│  │   ├── Sequencer_Sheet1          {                                         │
│  │   │   └── STATUS_Username         "Script": {           ◄── TARGET MASTER │
│  │   │       - FIXED                   "Username": {                         │
│  │   │       - REPORTED                  "fixed": 4,                         │
│  │   │       - CHECKING                  "reported": 2,                      │
│  │   │       - NON-ISSUE                 ...                                 │
│  │   ├── Dialog_Sheet1               }                                       │
│  │   │   └── STATUS_Username       }                                         │
│  │                               }                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRACKER WRITE FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  update_daily_data_sheet(daily_entries, manager_stats):                      │
│                                                                              │
│  For each entry in daily_entries:                                            │
│    category = entry["category"]           # "Sequencer" (ORIGINAL)           │
│    user = entry["user"]                   # "Username"                       │
│                                                                              │
│    lookup_category = get_target_master_category(category)                    │
│                      # "Sequencer" → "Script"                                │
│                                                                              │
│    category_stats = manager_stats.get(lookup_category, {})                   │
│                     # manager_stats["Script"]                                │
│                                                                              │
│    user_manager_stats = category_stats.get(user, default)                    │
│                         # manager_stats["Script"]["Username"]                │
│                                                                              │
│    ┌─────────────────────────────────────────────────────┐                   │
│    │  POTENTIAL MISS POINTS:                             │                   │
│    │  1. lookup_category not in manager_stats → NO_CAT   │                   │
│    │  2. user not in category_stats → NO_USER            │                   │
│    │  3. all stats are 0 → ZERO                          │                   │
│    └─────────────────────────────────────────────────────┘                   │
│                                                                              │
│    Write to _DAILY_DATA row:                                                 │
│      - Tester stats from entry (issues, no_issue, blocked, korean)           │
│      - Manager stats from lookup (fixed, reported, checking, nonissue)       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Category Mapping Reference

| Original Category | Target Master | Master File |
|-------------------|---------------|-------------|
| Quest | Quest | Master_Quest.xlsx |
| Knowledge | Knowledge | Master_Knowledge.xlsx |
| Item | Item | Master_Item.xlsx |
| Region | Region | Master_Region.xlsx |
| System | System | Master_System.xlsx |
| Character | Character | Master_Character.xlsx |
| Contents | Contents | Master_Contents.xlsx |
| **Skill** | **System** | Master_System.xlsx |
| **Help** | **System** | Master_System.xlsx |
| **Gimmick** | **Item** | Master_Item.xlsx |
| **Sequencer** | **Script** | Master_Script.xlsx |
| **Dialog** | **Script** | Master_Script.xlsx |

Clustered categories (bold) share a master file.

---

## Debug Checklist

### To investigate MISS:

1. **Check `daily_entries`** - Are all expected tester entries present?
   - Add logging in `process_category()` at line ~1097

2. **Check `manager_stats`** - Are all expected manager stats present?
   - Review `MANAGER_STATS_DEBUG.log` after compilation
   - Verify all STATUS_* columns are found

3. **Check lookup mapping** - Does the lookup find the right stats?
   - Review `=== LOOKUP PHASE ===` section in debug log
   - Look for `MISS DETAILS:` line

4. **Check username consistency** - Do usernames match exactly?
   - Whitespace differences: "Alice" vs "Alice "
   - Encoding differences (Korean names)
   - Case sensitivity

5. **Check category consistency** - Do category names match?
   - Folder name vs CATEGORY list in config.py
   - Case sensitivity: "Sequencer" vs "sequencer"

---

## Files to Examine

| File | Function | Role |
|------|----------|------|
| `config.py` | `CATEGORY_TO_MASTER` | Defines clustering |
| `config.py` | `get_target_master_category()` | Converts original → target |
| `core/compiler.py` | `collect_manager_stats_for_tracker()` | Reads Master files |
| `core/compiler.py` | `process_category()` | Creates daily_entries |
| `tracker/data.py` | `update_daily_data_sheet()` | Writes to tracker |

---

## Next Steps

1. Get specific examples of MISS cases from real data
2. Add granular logging to identify exact failure point
3. Compare usernames character-by-character if needed
4. Fix the matching logic once root cause identified

---

## Related Docs

- [TECHNICAL_MATCHING_SYSTEM.md](TECHNICAL_MATCHING_SYSTEM.md) - Row matching in master files
- [SESSION_TRACKER_MASTERFILE_UPDATE.md](SESSION_TRACKER_MASTERFILE_UPDATE.md) - Tracker update workflow
