# QACompiler Script Performance - Consolidated Investigation Findings

## Date: 2026-02-03

## Status: INVESTIGATION COMPLETE (Pre-Code)

---

## Executive Summary

The investigation identified **7 major performance bottlenecks** in the Script (Sequencer/Dialog) master file building pipeline. Eight parallel investigation agents analyzed the full code path from file loading through post-processing. The core issues are:

1. **Redundant file I/O** -- same files loaded 2-3 times across pipeline phases
2. **Per-row column header scanning** -- O(columns) per row instead of O(1) cached lookups
3. **Massive style object churn** -- 750K+ Alignment/Font/Fill/Border objects created unnecessarily
4. **Multiple full-scan passes** in post-processing over all cells
5. **No use of openpyxl read_only mode** for operations that only read values
6. **Preprocessing results discarded** instead of reused downstream
7. **No shared/cached style objects** -- identical styles recreated per cell

**Combined estimated improvement: 10-50x overall speedup for Script category master builds.**

---

## Bottleneck #1: Redundant File I/O (CRITICAL)

### Problem

Each QA xlsx file is loaded via `safe_load_workbook()` (full mode) **2-3 times** across different pipeline phases:

| Phase | Location | What It Does |
|-------|----------|--------------|
| Phase 1 | `preprocess_script_category()` -- `compiler.py:782` | Scans all QA files to build STATUS universe |
| Phase 2 | `create_filtered_script_template()` source cache -- `compiler.py:996` | Loads QA files as source for rows not in template |
| Phase 3 | `process_category()` main loop -- `compiler.py:1324` | Loads each QA file AGAIN for per-tester processing |

For N tester files: approximately **3N + 2 workbook loads** total (plus template and master loads).

### Verified Code References

```python
# Phase 1: compiler.py:782
wb = safe_load_workbook(xlsx_path)

# Phase 2: compiler.py:996
source_wb_cache[cache_key] = safe_load_workbook(xlsx_path)

# Phase 3: compiler.py:1324
qa_wb = safe_load_workbook(xlsx_path)
```

### Impact

Each `safe_load_workbook()` call:
- Parses the entire ZIP archive (xlsx files are ZIP)
- Creates all Cell objects in memory
- Loads all styles, shared strings, and metadata
- For a 10,000-row file with 20 columns: **2-10 seconds per load**
- 10 tester files x 3 loads = **30 redundant file loads**

### Solution

- Load each QA file **ONCE** and cache the workbook object in a dict keyed by file path
- Pass workbook references through the pipeline instead of file paths
- Use `read_only=True` for phases that only read values (Phase 1 preprocessing)
- Close workbooks explicitly after the pipeline completes

---

## Bottleneck #2: Per-Row Column Header Scanning (CRITICAL)

### Problem

`extract_qa_row_data()` in `matching.py:162` calls `find_column_by_header()` for **EVERY row** in the worksheet:

```python
# matching.py:175 - Called PER ROW
stringid_col = find_column_by_header(qa_ws, "STRINGID")

# matching.py:206 - Called PER ROW (Script categories)
trans_col = get_translation_column_by_name(qa_ws, category)
    # Internally calls: find_column_by_header(ws, "Text")

# matching.py:212 - Called PER ROW (Script categories)
eventname_col = find_column_by_header(qa_ws, "EventName")
```

Each `find_column_by_header()` iterates ALL columns in row 1:

```python
# excel_ops.py:131-153
def find_column_by_header(ws, header_name, case_insensitive=True):
    for col in range(1, ws.max_column + 1):     # O(columns) per call
        header = ws.cell(row=1, column=col).value
        if header:
            header_str = str(header).strip()
            if case_insensitive:
                if header_str.upper() == header_name.upper():
                    return col
    return None
```

### Impact

For 10,000 rows with 20 columns:
- 3 calls per row x 20 columns per call = 60 cell reads per row
- 10,000 rows x 60 = **600,000 unnecessary cell reads**
- These are the SAME columns every time -- the header row never changes

### Solution

Cache column positions **before** the row processing loop. Compute once per worksheet, reuse for all rows:

```python
# Compute ONCE before the loop
col_cache = {
    "STRINGID": find_column_by_header(qa_ws, "STRINGID"),
    "Text": find_column_by_header(qa_ws, "Text"),
    "EventName": find_column_by_header(qa_ws, "EventName"),
}

# Use cached values in extract_qa_row_data()
def extract_qa_row_data(qa_ws, row, category, is_english, col_cache=None):
    stringid_col = col_cache["STRINGID"] if col_cache else find_column_by_header(qa_ws, "STRINGID")
    # ...
```

**Note:** `build_master_index()` in `matching.py:241` also calls `find_column_by_header()` but only ONCE per index build (not per-row), so it is not a bottleneck.

---

## Bottleneck #3: autofit_rows_with_wordwrap() (CRITICAL)

### Problem

`processing.py:1258` creates a **new `Alignment()` object for EVERY cell** in the workbook:

```python
# processing.py:1251-1258
for row in range(1, ws.max_row + 1):        # ALL rows
    for col in range(1, ws.max_column + 1):  # ALL columns
        cell = ws.cell(row=row, column=col)
        cell.alignment = Alignment(wrap_text=True, vertical='top')  # NEW object per cell!
```

This iterates **every sheet**, **every row**, **every column**.

### Impact

For a master workbook with 5 sheets, 5000 rows each, 30 columns:
- 5 x 5000 x 30 = **750,000 new Alignment objects**
- Each `Alignment()` constructor creates a new object
- Each assignment triggers openpyxl's internal style registration (deduplication)
- The deduplication itself has overhead even though openpyxl shares internally

### Solution

1. Create **ONE shared** Alignment object, reuse for all cells:
```python
WRAP_ALIGNMENT = Alignment(wrap_text=True, vertical='top')
# Then in the loop:
cell.alignment = WRAP_ALIGNMENT  # Same object reference
```

2. Only apply to cells that don't already have the correct alignment (check first)
3. Consider skipping hidden rows entirely (they won't be visible)

---

## Bottleneck #4: hide_empty_comment_rows() (HIGH)

### Problem

`processing.py:921-1182` performs **8-10 separate passes** over all cells in every sheet:

| Pass | Lines | What It Does |
|------|-------|-------------|
| 1 | 972-979 | Scan columns for `COMMENT_` headers |
| 2 | 989-1009 | Reset column visibility (nested: each comment col x ALL columns) |
| 3 | 1015-1022 | Scan all rows for comments |
| 4 | 1037-1061 | Column hiding (nested: empty comment cols x ALL columns) |
| 5 | 1065-1085 | Scan for `SCREENSHOT_` columns + scan all rows for content |
| 6 | 1088-1116 | Scan for `TESTER_STATUS_` columns + scan all rows for status |
| 7 | 1126-1146 | Scan for manager `STATUS_` columns + scan all rows |
| 8 | 1172-1174 | Unhide ALL rows |
| 9 | 1177-1180 | Hide rows not in show set |

Each pass iterates some or all of `ws.max_row` rows and/or `ws.max_column` columns.

### Impact

For 5000 rows x 30 columns x 10 passes = **1,500,000+ cell accesses** per sheet.

The **nested loops** in passes 2 and 4 are particularly expensive:
```python
# Pass 2: processing.py:997 - For EACH comment column, scan ALL columns
for col in comment_cols:              # e.g., 5 comment columns
    for search_col in range(1, ws.max_column + 1):  # ALL 30 columns
        # Check if it's a paired column
```
This is O(comment_cols x total_cols) per sheet.

### Solution

**Single-pass approach:**

1. **One header scan:** Collect ALL column metadata in a single pass over row 1:
   - Build dicts: `comment_cols`, `screenshot_cols`, `tester_status_cols`, `manager_status_cols`
   - Map usernames to their column groups: `{username: {comment: col, screenshot: col, status: col, ...}}`

2. **One data scan:** Single pass over all rows collecting:
   - Which rows have comments (and in which columns)
   - Which rows have ISSUE/NO ISSUE/BLOCKED/KOREAN tester status
   - Which rows have FIXED/NON-ISSUE manager status

3. **One apply pass:** Apply all hiding decisions in a single pass:
   - Set column hidden state
   - Set row hidden state

This reduces from ~10 passes to **3 passes** (header scan + data scan + apply).

---

## Bottleneck #5: Per-Cell Style Object Creation (HIGH)

### Problem

`process_sheet()` creates new style objects for **every cell** it writes:

```python
# In the per-row processing loop (processing.py, various locations in process_sheet):

# For COMMENT cells with ISSUE status:
cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")  # NEW
cell.font = Font(name='Calibri', size=11)                                               # NEW
cell.alignment = Alignment(wrap_text=True, vertical='top')                              # NEW
cell.border = Border(                                                                    # NEW
    left=Side(style='thin'),    # NEW Side object
    right=Side(style='thin'),   # NEW Side object
    top=Side(style='thin'),     # NEW Side object
    bottom=Side(style='thin')   # NEW Side object
)

# For STATUS cells: Font + Alignment = 2 objects per cell
# For MANAGER_COMMENT cells: PatternFill + Alignment + Border(4 Sides) = 7 objects per cell
```

### Impact

For 1000 rows with comments across all testers:
- Comment cells: 7+ objects per cell
- Status cells: 2+ objects per cell
- Manager comment cells: 7+ objects per cell
- Total: **7,000-16,000 unnecessary style objects** per sheet
- Each triggers openpyxl internal style registration

### Solution

Pre-create all status-specific style tuples as **module-level constants**:

```python
# Module-level: created ONCE at import time
_ISSUE_FILL = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
_STANDARD_FONT = Font(name='Calibri', size=11)
_WRAP_ALIGNMENT = Alignment(wrap_text=True, vertical='top')
# THIN_BORDER already exists as a module constant in excel_ops.py

STYLE_ISSUE = (_ISSUE_FILL, _STANDARD_FONT, _WRAP_ALIGNMENT, THIN_BORDER)
STYLE_NO_ISSUE = (...)
STYLE_BLOCKED = (...)
STYLE_KOREAN = (...)
```

Reuse the **SAME objects** for all cells of the same type. openpyxl handles this correctly -- assigning the same object to multiple cells is efficient.

**Note:** `excel_ops.py` already uses this pattern for header styles:
```python
# excel_ops.py:368-378 -- EXISTING good pattern
THIN_BORDER = Border(...)       # Module-level constant
HEADER_FILL = PatternFill(...)  # Module-level constant
HEADER_FONT = Font(bold=True)   # Module-level constant
```
The fix is extending this existing pattern to all status-specific styles.

---

## Bottleneck #6: Preprocessing Results Discarded (MEDIUM)

### Problem

`preprocess_script_category()` (compiler.py:730) builds a "universe" of all rows with STATUS, including:
- eventname, text, sheet name, source file paths

But this rich data is **NOT passed** to `process_sheet()`. Instead, `process_sheet()` independently re-scans for STATUS rows:

```python
# processing.py:458-480 - REDUNDANT scan in process_sheet()
rows_to_process = []
if is_script and qa_status_col:
    for qa_row in range(2, qa_ws.max_row + 1):
        status_val = qa_ws.cell(row=qa_row, column=qa_status_col).value
        if status_val and str(status_val).strip():
            rows_to_process.append(qa_row)
```

This is the SAME scan that `preprocess_script_category()` already performed:
```python
# compiler.py:782+ - FIRST scan in preprocessing
wb = safe_load_workbook(xlsx_path)
for ws in wb.worksheets:
    for row in range(2, ws.max_row + 1):
        status_val = ws.cell(row=row, column=status_col).value
        # ... builds universe ...
```

### Impact

Each QA file's rows are scanned for STATUS **twice**:
1. During preprocessing (to build universe)
2. During process_sheet (to filter rows)

For 10 files x 10,000 rows each = **100,000 redundant cell reads**.

### Solution

Pass the universe data (or a per-file subset of `rows_to_process`) from preprocessing into `process_sheet()`. The preprocessing phase already knows exactly which rows have STATUS -- there is no need to scan again.

```python
# Pass pre-computed row list to process_sheet:
process_sheet(master_ws, qa_ws, username, category, ...,
              precomputed_rows=universe_rows_for_file)
```

---

## Bottleneck #7: No read_only Mode (MEDIUM)

### Problem

`safe_load_workbook()` at `excel_ops.py:75` uses default openpyxl mode (full load) for **ALL operations**, including those that only read values:

| Call Site | Operation | Reads Only? |
|-----------|-----------|-------------|
| `compiler.py:782` | `preprocess_script_category()` | YES -- only reads STATUS, EventName, Text |
| `compiler.py:157` | `collect_manager_status()` | YES -- only reads STATUS column values |
| `compiler.py:500` | `collect_fixed_screenshots()` | YES -- only reads STATUS for FIXED check |
| `compiler.py:260` | `collect_manager_stats_for_tracker()` | YES -- only reads STATUS columns |

All four call sites only need cell **values**, not styles, formulas, or images.

### Impact

Full mode (`read_only=False`, the default) loads:
- All cell objects with full style information
- Shared strings table (parsed completely)
- All named ranges, data validations, conditional formatting
- Memory footprint: **3-10x larger** than needed for value-only reads

`read_only=True` mode uses:
- Streaming/lazy evaluation (cells parsed on access)
- No style objects created
- Significantly lower memory usage
- **2-3x faster** for large worksheets

### Solution

Add a `read_only` parameter to the load workflow:

```python
# For scan-only operations:
wb = safe_load_workbook(xlsx_path, read_only=True)
# ... read values ...
wb.close()  # MUST close read_only workbooks explicitly

# For operations that need to modify:
wb = safe_load_workbook(xlsx_path)  # Default full mode
```

**Caveat:** `read_only=True` workbooks:
- Cannot be modified or saved
- Must be explicitly closed (no garbage collection)
- `ws.max_row` may return `None` (need to handle)
- Iterator-based access (can still index cells but less efficient for random access)

---

## Key Architecture Patterns

### Current Script Processing Pipeline

```
PHASE 1: Preprocessing
  preprocess_script_category()
    -> LOAD each QA file (full mode)
    -> Scan STATUS column in every row
    -> Build universe dict: {(EventName, Text): {sheet, sources}}
    -> Close workbooks

PHASE 2: Filtered Template Creation
  create_filtered_script_template()
    -> LOAD template workbook (full mode)
    -> For each universe row:
        -> Copy from template (cell by cell with style copying)
        -> If not in template: LOAD source QA file AGAIN (cached within phase)
    -> Save filtered template

PHASE 3: Master Creation
  get_or_create_master()
    -> LOAD filtered template
    -> Delete STATUS/COMMENT/SCREENSHOT/STRINGID columns

PHASE 4: Per-Tester Processing
  FOR each tester:
    safe_load_workbook(qa_file)    -> LOAD QA file AGAIN (3rd time!)
    FOR each sheet:
      build_master_index()         -> Iterate all master rows, O(1) dict (fast)
      Pre-filter STATUS rows       -> SCAN all QA rows AGAIN (redundant with Phase 1)
      FOR each filtered row:
        extract_qa_row_data()      -> find_column_by_header() x3 PER ROW (slow!)
        find_matching_row_in_master() -> O(1) dict lookup (fast)
        Write COMMENT to master    -> Create 7+ NEW style objects per cell (slow!)
        Write STATUS to master     -> Create 2+ NEW style objects per cell
        Restore manager status     -> Create 7+ NEW style objects per cell

PHASE 5: Post-Processing
  autofit_rows_with_wordwrap()     -> NEW Alignment for EVERY cell (750K+ objects)
  hide_empty_comment_rows()        -> 8-10 passes over ALL cells (1.5M+ reads)

PHASE 6: Save
  master_wb.save()
```

### Proposed Optimized Pipeline

```
PHASE 1: Single Load + Preprocessing
  FOR each QA file:
    LOAD ONCE with read_only=True
    -> Extract ALL needed data:
        - Universe rows (STATUS + EventName + Text)
        - Pre-filtered rows_to_process per file
        - Column positions cached per sheet
    -> Store in pipeline cache dict
    -> Close read_only workbook immediately

PHASE 2: Filtered Template Creation (minimal changes)
  -> Use cached data where possible instead of re-loading source files
  -> Use pre-created shared style objects for cell copying

PHASE 3: Master Creation (no change needed)
  -> Already efficient (one-time operation)

PHASE 4: Per-Tester Processing
  FOR each tester:
    LOAD QA file in full mode ONCE (for cell access)
    -> OR: if read_only suffices, use cached data from Phase 1
    FOR each sheet:
      build_master_index()           -> No change (already efficient)
      Use pre-computed rows_to_process -> Skip redundant STATUS scan
      Cache column positions once     -> No per-row header scanning
      FOR each filtered row:
        Use cached col positions      -> O(1) lookup (was O(cols))
        O(1) dict matching            -> No change (already efficient)
        Write with SHARED style objects -> Same objects reused

PHASE 5: Optimized Post-Processing
  ONE header scan per sheet:
    -> Build complete column metadata map
  ONE data scan per sheet:
    -> Collect ALL row visibility info + content metrics
    -> Apply shared Alignment object (not per-cell creation)
  ONE apply scan per sheet:
    -> Set all column widths
    -> Set all row heights
    -> Set all hidden states

PHASE 6: Save (no change)
  master_wb.save()
```

---

## Estimated Impact per Fix

| # | Fix | Estimated Speedup | Difficulty | Risk |
|---|-----|-------------------|------------|------|
| 2 | Cache column positions (per-row header scan removal) | 5-10x for per-row ops | Easy | Low |
| 5 | Reuse style objects (module-level constants) | 2-5x for styling ops | Easy | Low |
| 7 | read_only=True for scan-only operations | 2-3x for file loading | Easy | Low (caveat: max_row) |
| 1 | Single file load + workbook cache | 2-3x for total I/O | Medium | Medium |
| 4 | Single-pass post-processing (hide_empty_comment_rows) | 3-5x for post-proc | Medium | Medium |
| 3 | Shared Alignment in autofit_rows_with_wordwrap | 2-3x for autofit | Easy | Low |
| 6 | Pass universe/rows downstream (skip redundant scan) | 1.5-2x for STATUS scan | Easy | Low |
| -- | **Combined: ALL fixes** | **10-50x overall** | **Medium** | **Medium** |

**Recommended implementation order:** Start with Easy/Low-risk fixes (#2, #5, #7, #3, #6) first. They provide significant speedup with minimal code change risk. Then tackle Medium-risk fixes (#1, #4) which require more architectural changes.

---

## Files to Modify (Scope)

| File | Line Ranges | Changes Required |
|------|-------------|-----------------|
| `core/matching.py` | 162-234 | Accept optional `col_cache` parameter in `extract_qa_row_data()`, remove per-row `find_column_by_header()` calls |
| `core/processing.py` | 333-532 | Use shared style constants in `process_sheet()`, accept precomputed rows |
| `core/processing.py` | 921-1182 | Refactor `hide_empty_comment_rows()` to single-pass architecture |
| `core/processing.py` | 1185-1278 | Create shared Alignment in `autofit_rows_with_wordwrap()`, skip hidden rows |
| `core/compiler.py` | 730-915 | Cache workbooks and column positions in `preprocess_script_category()` |
| `core/compiler.py` | 916-1050 | Use cached workbooks in `create_filtered_script_template()` source cache |
| `core/compiler.py` | 1189-1400 | Use cached workbooks in `process_category()`, pass precomputed rows |
| `core/excel_ops.py` | 75-124 | Add `read_only` convenience wrapper or parameter documentation |

## Files NOT to Modify

These files are out of scope. No performance issues identified, and changes could break unrelated functionality:

| File | Reason |
|------|--------|
| `core/transfer.py` | Transfer workflow -- separate pipeline, not in scope |
| `core/discovery.py` | Folder discovery -- fast, no bottlenecks |
| `core/populate_new.py` | QAfolderNEW population -- not in build pipeline |
| `core/tracker_update.py` | Tracker-only update -- separate workflow |
| `generators/*.py` | Datasheet generation -- separate pipeline |
| `tracker/*.py` | Tracker data/coverage/daily/total -- separate pipeline |
| `gui/app.py` | GUI layer -- no performance-critical code |
| `config.py` | Configuration -- unless adding new performance constants |
| `tests/*` | All existing tests must continue to pass unchanged |

---

## Verification Strategy

### Output Fidelity Check

Before and after optimization, the output master files must be **functionally identical**:

| Aspect | Must Match |
|--------|-----------|
| Cell values | All data values identical |
| Column order | Same columns in same positions |
| Sheet names | Same sheet names |
| Row order | Same row order within sheets |
| STATUS values | All tester and manager statuses preserved |
| COMMENT data | All comments with metadata preserved |
| SCREENSHOT refs | All screenshot references preserved |
| Hidden state | Same rows/columns/sheets hidden |
| Styling | Visually identical (colors, fonts, borders) |

### Regression Tests

1. All existing tests in `tests/` must pass unchanged
2. Non-Script categories (Quest, Knowledge, Item, etc.) must be unaffected
3. Category clustering (Sequencer + Dialog -> Master_Script.xlsx) must still work
4. Manager status preservation across rebuilds must still work

---

## Appendix A: Key Functions Reference

### Hot Path Functions (Performance Critical)

| Function | File:Line | Called | Fix Priority |
|----------|-----------|-------|-------------|
| `extract_qa_row_data()` | matching.py:162 | Per QA row | CRITICAL (#2) |
| `find_column_by_header()` | excel_ops.py:131 | 3x per row (in extract) | CRITICAL (#2) |
| `process_sheet()` styling | processing.py:333+ | Per matched row | HIGH (#5) |
| `autofit_rows_with_wordwrap()` | processing.py:1185 | Per cell in workbook | CRITICAL (#3) |
| `hide_empty_comment_rows()` | processing.py:921 | 8-10 passes per sheet | HIGH (#4) |

### Warm Path Functions (Loaded Multiple Times)

| Function | File:Line | Loads | Fix Priority |
|----------|-----------|-------|-------------|
| `safe_load_workbook()` in preprocess | compiler.py:782 | Once per QA file | MEDIUM (#1, #7) |
| `safe_load_workbook()` in source cache | compiler.py:996 | Once per unique source | MEDIUM (#1) |
| `safe_load_workbook()` in process loop | compiler.py:1324 | Once per QA file (again) | CRITICAL (#1) |

### Cold Path Functions (Already Efficient)

| Function | File:Line | Notes |
|----------|-----------|-------|
| `build_master_index()` | matching.py:241 | O(n) build, O(1) lookup -- already fast |
| `find_matching_row_in_master()` | matching.py:365 | Dict lookup -- already O(1) |
| `get_or_create_master()` | excel_ops.py:178 | One-time per category -- not a bottleneck |

---

## Appendix B: openpyxl Performance Notes

### read_only=True Mode

```python
wb = openpyxl.load_workbook(path, read_only=True)
# Pros: 2-3x faster load, streaming cell access, lower memory
# Cons: ws.max_row can be None, must close explicitly, no modification
# Use for: preprocess_script_category(), collect_manager_status(), etc.
```

### Style Object Sharing

```python
# openpyxl internally deduplicates styles, but the CREATION cost is still paid
# Creating 750K Alignment objects is slow even if openpyxl stores fewer internally

# GOOD: Create once, assign many times
shared_alignment = Alignment(wrap_text=True, vertical='top')
for cell in cells:
    cell.alignment = shared_alignment  # Fast: just pointer assignment

# BAD: Create new object each time
for cell in cells:
    cell.alignment = Alignment(wrap_text=True, vertical='top')  # Slow: constructor + registration
```

### write_only Mode (Future Consideration)

```python
# write_only=True is the fastest for creating NEW workbooks
# But QACompiler modifies EXISTING workbooks (adds columns to master)
# Not directly applicable without major architecture change
# Consider only if migrating to "build master from scratch" approach
```

---

*This document consolidates findings from 8 parallel investigation agents. No code changes have been made. This is an analysis checkpoint to inform the implementation phase.*
