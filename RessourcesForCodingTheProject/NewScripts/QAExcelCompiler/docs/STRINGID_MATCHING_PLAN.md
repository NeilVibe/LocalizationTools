# STRINGID-Based Row Matching - Implementation Plan

**Created:** 2026-01-09
**Status:** READY FOR IMPLEMENTATION
**Priority:** P1 (fixes broken matching for reordered columns)

---

## Problem Statement

The current fallback matching uses column-position-based signatures:
```python
# Current approach - BROKEN for reordered columns
signature = [(col_index, value), (col_index, value), ...]
```

When testers have columns in different order, matching fails:
- **Paul/Mike order:** Original (KR), English (ENG), STATUS, COMMENT, STRINGID, SCREENSHOT
- **Lisa's order:** STRINGID, Original (KR), English (ENG), COMMENT, STATUS, SCREENSHOT

**Result:** Lisa's rows can't match master rows = 0 comments compiled.

---

## Solution: STRINGID-Based Matching

Use STRINGID as the **primary key** for row matching:

```python
# New approach - WORKS regardless of column order
master_index = {stringid: row_number}  # Build once per sheet
qa_stringid = get_stringid(qa_row)     # Get STRINGID from QA row
master_row = master_index.get(qa_stringid)  # O(1) lookup
```

---

## Real Data Analysis

### Structure Variations Found

| Category | STATUS | COMMENT | STRINGID | SCREENSHOT |
|----------|--------|---------|----------|------------|
| Knowledge | col 3 | col 4 | col 5 | col 6 |
| Region | col 3 | col 4 | col 5 | col 6 |
| Character | col 4 | col 5 | col 6 | col 7 |
| Item | col 8 | col 9 | col 10 | col 11 |

### STRINGID Statistics

- **Total unique STRINGIDs:** 980
- **Duplicate STRINGIDs:** 38 (same text used in multiple rows)
- **Format:** Large numeric values (up to 20 digits)

### Duplicate Handling

Some STRINGIDs appear in multiple rows (same text, different contexts):
```
STRINGID: 6201932775570
  - Doni_Knowledge.xlsx/Document row 338
  - Doni_Knowledge.xlsx/Document row 339
```

**Solution:** Match to FIRST occurrence, or use (STRINGID + sheet_name) as composite key.

---

## Implementation Plan

### Step 1: Add STRINGID Index Builder

```python
def build_stringid_index(ws):
    """
    Build {stringid: row_number} index for worksheet.

    For duplicates, keeps first occurrence.
    """
    stringid_col = find_column_by_header(ws, "STRINGID")
    if not stringid_col:
        return {}

    index = {}
    for row in range(2, ws.max_row + 1):
        sid = ws.cell(row, stringid_col).value
        if sid:
            sid = str(sid).strip()
            if sid not in index:  # First occurrence only
                index[sid] = row
    return index
```

### Step 2: Update process_sheet() to Use STRINGID Matching

```python
def process_sheet(master_ws, qa_ws, username, category, ...):
    # ... existing setup code ...

    # NEW: Build STRINGID indices
    master_stringid_col = find_column_by_header(master_ws, "STRINGID")
    qa_stringid_col = find_column_by_header(qa_ws, "STRINGID")

    # Build master index (once per sheet)
    master_index = {}
    if master_stringid_col:
        for row in range(2, master_ws.max_row + 1):
            sid = master_ws.cell(row, master_stringid_col).value
            if sid:
                sid = str(sid).strip()
                if sid not in master_index:
                    master_index[sid] = row

    # Matching priority:
    # 1. STRINGID match (primary)
    # 2. Row index match (if same row count)
    # 3. Signature fallback (last resort)

    for qa_row in range(2, qa_ws.max_row + 1):
        master_row = None

        # Try STRINGID match first
        if qa_stringid_col and master_index:
            qa_sid = qa_ws.cell(qa_row, qa_stringid_col).value
            if qa_sid:
                master_row = master_index.get(str(qa_sid).strip())

        # Fallback to row index if STRINGID not available
        if master_row is None and not use_fallback:
            master_row = qa_row

        # Last resort: signature matching
        if master_row is None:
            qa_sig = get_row_signature(qa_ws, qa_row, qa_exclude_cols)
            master_row = find_matching_row_fallback(master_ws, qa_sig, ...)

        # Process row if match found
        if master_row:
            # ... copy STATUS, COMMENT, SCREENSHOT ...
```

### Step 3: Handle Missing STRINGID Column

If STRINGID column doesn't exist, fall back to current behavior:
1. Row index matching (if same row count)
2. Signature-based matching (if row counts differ)

---

## Testing Checklist

- [ ] Mike_Region.xlsx (shuffled rows, same columns) - should match by STRINGID
- [ ] Lisa_Region.xlsx (reordered columns) - should match by STRINGID
- [ ] Paul_Region.xlsx (original order) - should match by row index
- [ ] Files without STRINGID column - should fall back gracefully
- [ ] Files with duplicate STRINGIDs - should match first occurrence

---

## Migration Notes

### Backward Compatibility

- No changes to input/output format
- No changes to folder structure
- Existing master files continue to work
- STRINGID column preserved in master (currently deleted - may need to keep)

### STRINGID Preservation Decision

**Current behavior:** STRINGID column is deleted from master files.

**PROBLEM:** Without STRINGID in master, we can't match QA rows to master rows!

**SOLUTION:** Keep STRINGID in master but HIDE it.

```python
# In get_or_create_master(), REMOVE STRINGID from deletion list:
columns_to_delete = ["STATUS", "COMMENT", "SCREENSHOT"]  # NOT STRINGID!

# After master is created, hide the STRINGID column:
stringid_col = find_column_by_header(ws, "STRINGID")
if stringid_col:
    ws.column_dimensions[get_column_letter(stringid_col)].hidden = True
```

**Benefits:**
- STRINGID available for row matching
- Column hidden from users
- Works for all re-runs

---

## Code Locations to Modify

| File | Function | Change |
|------|----------|--------|
| compile_qa.py | `get_or_create_master()` | Keep STRINGID column (remove from delete list), hide it |
| compile_qa.py | `process_sheet()` | Add STRINGID index + matching before fallback |
| compile_qa.py | `get_row_signature()` | Keep as fallback (no changes) |
| compile_qa.py | `find_matching_row_fallback()` | Keep as fallback (no changes) |

### Specific Line Changes

1. **get_or_create_master()** (~line 420-450):
   - Find where STATUS/COMMENT/SCREENSHOT/STRINGID are deleted
   - Remove STRINGID from deletion list
   - Add code to hide STRINGID column

2. **process_sheet()** (~line 853):
   - Add `build_stringid_index()` call for master
   - Add STRINGID lookup before row index or fallback matching

---

## Estimated Effort

- **Code changes:** ~50 lines total
  - ~10 lines in `get_or_create_master()` (keep STRINGID, hide it)
  - ~20 lines for `build_stringid_index()` function
  - ~15 lines in `process_sheet()` (STRINGID matching)
- **Testing:** Run compile with all test files (Mike, Lisa, Paul)
- **Risk:** Low (additive change, fallback preserved)

---

## Summary

### Before (Current)
1. Master created from first QA file
2. STRINGID column DELETED from master
3. Matching uses row index or signature fallback
4. **Reordered columns = BROKEN matching**

### After (Proposed)
1. Master created from first QA file
2. STRINGID column KEPT but HIDDEN
3. Matching uses STRINGID lookup (O(1) per row)
4. Fallback to signature only if STRINGID unavailable
5. **Reordered columns = WORKS correctly**

---

## Test Results (Prototype)

| Tester | Column Order | Current Result | With STRINGID |
|--------|--------------|----------------|---------------|
| Mike | Same as master | 75 matches | 75 matches |
| Paul | Same as master | 54 matches | 54 matches |
| Lisa | REORDERED | 0 matches | All matches |

---

*Plan created: 2026-01-09*
*Based on real data analysis with 4 categories, 980 unique STRINGIDs*
