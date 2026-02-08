# Duplicate Row Replication — Tester+Manager Unit

## Problem

When the master file has duplicate rows (same content key), the current System 1
(extract → rebuild → restore) only handles ONE of them. The rest become ghosts.

### Two bugs with duplicates:

**Bug 1 — Extract side (`extract_tester_data_from_master`, excel_ops.py:494-497):**
```python
sheet_data[content_key][username] = user_data   # last-write-wins
```
If rows 5 and 8 have the same `content_key` and Alice has data on both,
only row 8's data survives extraction. Row 5's data is silently overwritten.

**Bug 2 — Restore side (`restore_tester_data_to_master`, excel_ops.py:667-668):**
```python
master_index["consumed"].add(master_row)
```
The consumed set means only the first matching row gets the restored data.
All other duplicate rows remain empty — "ghost rows" with no tester/manager data.

### Same problem in `process_sheet()` matching (matching.py:474-477):
```python
if key not in index["primary"]:
    index["primary"][key] = row_idx   # first-one-wins
```
Primary index stores only the first row for a given key. When QA comment matches
via primary, it always lands on the first duplicate. Other duplicates never receive
anything.

---

## Proposed Fix: Replicate Across All Duplicates

### Core Idea

When tester+manager data exists for a content key that has multiple rows in the
master, **replicate the same unit on ALL matching rows** — not just the first one.

### Where Duplicates Come From

- Source XML has genuinely repeated entries (same StringID + Translation)
- Different source files contribute same row to same master sheet
- Legacy `merge_missing_rows_into_master()` created them (now removed, but
  existing masters may still contain duplicates from previous compilations)

### The Unit (all 5 fields move together)

| Field | Column Pattern | Source |
|-------|---------------|--------|
| Comment | COMMENT_{User} | QA Tester |
| Tester Status | TESTER_STATUS_{User} | QA Tester |
| Manager Status | STATUS_{User} | Manager |
| Manager Comment | MANAGER_COMMENT_{User} | Manager |
| Screenshot | SCREENSHOT_{User} | QA Tester |

These ALWAYS move as a single unit. Never split.

---

## Implementation Plan

### Step 1: Fix Extract — Collect ALL duplicates, don't overwrite

**File:** `core/excel_ops.py`, `extract_tester_data_from_master()`

**Current structure:**
```python
{sheet_name: {content_key: {username: user_data}}}
```
Problem: One `content_key` → one `user_data` per user. Second duplicate overwrites.

**New structure:** Add a list to accumulate multiple entries per key:
```python
{sheet_name: {content_key: {username: [user_data_1, user_data_2, ...]}}}
```

But actually — for duplicates with the same key, the tester/manager data SHOULD
be identical (they were replicated from the same source). If they differ, it's
because only one row had data (ghost problem). So:

**Solution: Use the `(updated: YYMMDD HHMM)` timestamp.**

Every comment cell already has a timestamp embedded in its metadata:
```
<comment text>
---
stringid:
<stringid value>
(updated: 260208 1430)
```

When two duplicate rows have the same content key, parse the `(updated: ...)`
from each comment and keep the MOST RECENT one.

```python
import re
from datetime import datetime

def _parse_updated_timestamp(comment_value) -> datetime:
    """Extract (updated: YYMMDD HHMM) from comment metadata."""
    if not comment_value:
        return datetime.min
    match = re.search(r'\(updated:\s*(\d{6}\s+\d{4})\)', str(comment_value))
    if match:
        try:
            return datetime.strptime(match.group(1), "%y%m%d %H%M")
        except ValueError:
            pass
    return datetime.min

# Instead of:
sheet_data[content_key][username] = user_data

# Do:
if content_key in sheet_data and username in sheet_data[content_key]:
    existing = sheet_data[content_key][username]
    existing_ts = _parse_updated_timestamp(existing.get("comment"))
    new_ts = _parse_updated_timestamp(user_data.get("comment"))
    if new_ts > existing_ts:
        sheet_data[content_key][username] = user_data
    # else: keep existing (it's newer or equal)
else:
    if content_key not in sheet_data:
        sheet_data[content_key] = {}
    sheet_data[content_key][username] = user_data
```

This ensures we keep the MOST RECENTLY UPDATED data for each content key,
using the timestamp that's already embedded in every comment cell.

### Step 2: Fix Restore — Place on ALL matching rows, not just first

**File:** `core/excel_ops.py`, `restore_tester_data_to_master()`

**Current:** Uses `consumed` set, matches ONE row per content key.

**New:** For each content key, find ALL matching rows and restore to all of them.

```python
# Instead of finding one row and consuming it:
# Find ALL rows matching this content key

matching_rows = []

# Primary match (may have multiple via fallback list)
if primary_key in master_index["primary"]:
    matching_rows.append(master_index["primary"][primary_key])

# Also check fallback for additional duplicate rows
if fallback_key in master_index["fallback"]:
    for row in master_index["fallback"][fallback_key]:
        if row not in matching_rows:
            matching_rows.append(row)

# Restore to ALL matching rows
for master_row in matching_rows:
    master_index["consumed"].add(master_row)
    # ... restore user data to this row ...
```

**Key change:** Don't stop at first match. Iterate all fallback entries too.
Still consume them all to prevent cross-key contamination.

### Step 3: Fix `process_sheet()` matching — Same replication for QA comments

**File:** `core/processing.py`, in the row matching section

This uses `matching.py`'s `find_matching_row_in_master()` which returns ONE row.
For QA comment compilation, this is actually CORRECT — the QA tester wrote ONE
comment, it should go on ONE row. The duplicates will get it via the restore
mechanism (Step 2) on the NEXT compilation cycle.

**No change needed here.** The consumed set in `process_sheet()` correctly prevents
double-writing the same QA comment. The replication happens at the restore level.

---

## Summary of Changes

| File | Function | Change |
|------|----------|--------|
| `core/excel_ops.py` | `extract_tester_data_from_master()` | Merge instead of overwrite for duplicate keys |
| `core/excel_ops.py` | `restore_tester_data_to_master()` | Restore to ALL matching rows, not just first |

**No changes to:** `matching.py`, `processing.py`, `compiler.py`

---

## Example Walkthrough

### Master before compilation:
| Row | StringID | Translation | COMMENT_Alice | STATUS_Alice |
|-----|----------|-------------|---------------|--------------|
| 5 | STR_001 | "Hello" | "Wrong tone" | FIXED |
| 8 | STR_001 | "Hello" | (empty) | (empty) |

Row 8 is a ghost — duplicate content but no tester data.

### After fix — Extract:
Extracts Alice's data from row 5: `{comment: "Wrong tone", manager_status: "FIXED"}`
Row 8 has nothing → row 5's richer data wins.

### After fix — Restore:
Finds ALL rows matching `(STR_001, "Hello")` → rows 5 AND 8.
Restores Alice's unit to BOTH rows.

### Result:
| Row | StringID | Translation | COMMENT_Alice | STATUS_Alice |
|-----|----------|-------------|---------------|--------------|
| 5 | STR_001 | "Hello" | "Wrong tone" | FIXED |
| 8 | STR_001 | "Hello" | "Wrong tone" | FIXED |

Both duplicates now have identical tester+manager data. No more ghosts.

---

## Edge Cases

### Different users on different duplicate rows
If Alice commented on row 5 and Bob commented on row 8 (same content key):
- Extract: Both collected under same key → `{Alice: {...}, Bob: {...}}`
- Restore: Both users' data goes on ALL matching rows (5 and 8)
- Result: Both rows have both Alice and Bob data

### Three+ duplicates
Same logic scales. All N duplicate rows get identical tester+manager data.

### Duplicate removed in new template
If the new template only has ONE row for that content key:
- Restore finds only one row → places merged data there
- No data lost, duplicates naturally resolved

### Fresh QA comment on a duplicate
- `process_sheet()` matches first row via primary (correct)
- On NEXT compilation, restore replicates to all duplicates
- Eventual consistency: all duplicates get same data after one cycle
