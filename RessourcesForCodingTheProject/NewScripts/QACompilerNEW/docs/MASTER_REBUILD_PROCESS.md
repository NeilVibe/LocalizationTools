# QA Compiler: Master Rebuild Process

## Overview

This document explains how the QA Compiler handles master file rebuilding, template selection, and data preservation.

---

## Template Selection

### What is a "Template"?

The **template** is simply the **most recently modified QA file** (by file modification time) for a category. There is NO version tracking or "new vs old template" comparison.

```python
# Most recent file by mtime becomes template
sorted_by_mtime = sorted(qa_folders, key=lambda x: x["xlsx_path"].stat().st_mtime, reverse=True)
template_xlsx = sorted_by_mtime[0]["xlsx_path"]
```

### Example

If you have these Quest QA files:
- `김동헌_Quest/Quest.xlsx` - modified Jan 15
- `황하연_Quest/Quest.xlsx` - modified Feb 1 ← **This becomes template (newest)**

---

## Rebuild vs Skip Logic

### When is a Master Rebuilt?

```python
rebuild = target_master not in processed_masters_en
```

| Scenario | Action |
|----------|--------|
| QA folders exist for category | **REBUILD** master from most recent template |
| NO QA folders for category | **SKIP** - existing master stays 100% intact |

### Clustered Categories

Some categories share the same master file:

| Input Category | Target Master |
|----------------|---------------|
| Sequencer | Master_Script.xlsx |
| Dialog | Master_Script.xlsx |
| Skill | Master_System.xlsx |
| Help | Master_System.xlsx |
| Gimmick | Master_Item.xlsx |

For clustered categories:
1. **First category** (e.g., Sequencer) → `rebuild=True` → Creates fresh master
2. **Subsequent categories** (e.g., Dialog) → `rebuild=False` → Appends new sheets

---

## Tester Data Preservation

### The Problem (Before Fix)

When rebuilding master files, ALL tester column data was lost:
1. Old master deleted
2. New master created from template
3. Only testers PRESENT in current QA folder got columns
4. **Absent testers' data (comments, status, screenshots) permanently lost**

### The Solution (After Fix)

```
BEFORE (Data Loss):              AFTER (Data Preserved):
┌──────────────────┐              ┌──────────────────────────┐
│ DELETE master    │              │ EXTRACT tester data      │
│                  │              │ from old master          │
│ CREATE from      │              │                          │
│ template         │              │ DELETE old master        │
│                  │              │                          │
│ ❌ ALL tester    │              │ CREATE from template     │
│ data LOST        │              │                          │
└──────────────────┘              │ RESTORE tester data      │
                                  │ to matching rows         │
                                  │                          │
                                  │ ✅ ALL data preserved    │
                                  └──────────────────────────┘
```

### Functions Added

1. **`extract_tester_data_from_master()`** - Extracts all tester data before deletion
2. **`restore_tester_data_to_master()`** - Restores data to matching rows after creation

### Content-Based Matching Keys

| Category | Primary Key | Fallback |
|----------|-------------|----------|
| Standard (Quest, Knowledge, etc.) | (STRINGID, Translation) | Translation only |
| Item | (ItemName, ItemDesc, STRINGID) | (ItemName, ItemDesc) |
| Script (Sequencer, Dialog) | (EventName, Text) | EventName only |
| Contents | INSTRUCTIONS | None |

### Data Preserved Per User

- `COMMENT_{user}` - Tester comment with styling
- `TESTER_STATUS_{user}` - Internal status (ISSUE, NO ISSUE, BLOCKED, KOREAN)
- `STATUS_{user}` - Manager status (FIXED, REPORTED, CHECKING, NON-ISSUE)
- `MANAGER_COMMENT_{user}` - Manager notes
- `SCREENSHOT_{user}` - Screenshot hyperlinks (not for Script categories)

---

## Progress Tracker Updates

### UPSERT Logic

The tracker uses **UPSERT** based on `(date, user, category)`:

```python
key = (entry["date"], entry["user"], entry["category"])
row = existing.get(key) or ws.max_row + 1  # Update existing OR insert new
```

### Example: Only Quest file uploaded today

```
Tracker BEFORE:
┌────────────┬─────────┬───────────┬────────┐
│ Date       │ User    │ Category  │ Issues │
├────────────┼─────────┼───────────┼────────┤
│ 2024-01-15 │ 김동헌  │ Quest     │ 5      │  ← OLD
│ 2024-01-15 │ 황하연  │ Item      │ 3      │  ← Untouched
└────────────┴─────────┴───────────┴────────┘

Tracker AFTER (only Quest processed):
┌────────────┬─────────┬───────────┬────────┐
│ Date       │ User    │ Category  │ Issues │
├────────────┼─────────┼───────────┼────────┤
│ 2024-02-05 │ 김동헌  │ Quest     │ 12     │  ← NEW entry
│ 2024-01-15 │ 김동헌  │ Quest     │ 5      │  ← OLD preserved
│ 2024-01-15 │ 황하연  │ Item      │ 3      │  ← Untouched
└────────────┴─────────┴───────────┴────────┘
```

---

## KeyError Protection

Three defensive checks prevent KeyError for clustered categories:

```python
# Check 1: Line 953 - Start of QA folder processing
if username not in user_stats:
    user_stats[username] = {"total": 0, "issue": 0, ...}

# Check 2: Line 1021 - Before stats accumulation
if username not in user_stats:
    user_stats[username] = {"total": 0, "issue": 0, ...}

# Check 3: Line 1078 - Before daily entry creation
if username not in user_stats:
    user_stats[username] = {"total": 0, "issue": 0, ...}
```

---

## Summary

| Feature | Status |
|---------|--------|
| Template = most recent QA file | ✅ Working |
| No QA files = master untouched | ✅ Working |
| Tester data preserved during rebuild | ✅ Implemented |
| KeyError for clustered categories | ✅ Fixed |
| Tracker UPSERT (not overwrite) | ✅ Working |

---

*Last updated: 2026-02-05*
