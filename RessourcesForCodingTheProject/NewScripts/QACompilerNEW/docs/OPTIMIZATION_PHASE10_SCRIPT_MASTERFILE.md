# Phase 10: Script Masterfile Final Performance Pass + Report Table

**Date:** 2026-02-06
**Status:** COMPLETED AND VERIFIED
**Build:** Triggered and passed (GitHub Actions)
**Commit:** `fe7617c`

---

## Context

After Phases 1-9 had optimized the QA Compiler extensively, the Script masterfile build (Dialog + Sequencer categories -> Master_Script.xlsx) remained the slowest part of the compilation. Everything else was fast. This phase targeted the remaining bottlenecks specifically in the Script/Face build path.

**Investigation method:** 8 parallel explore agents analyzed every .py file in QACompilerNEW for remaining performance issues. 6 review agents + 2 explore agents verified all fixes afterward.

---

## Critical Fixes Implemented

### Fix 1: Triple QA Worksheet Preload Elimination

**File:** `core/processing.py` + `core/compiler.py`
**Impact:** HIGH — eliminated 2 redundant full-worksheet loads per QA file

**Problem:** `preload_worksheet_data(qa_ws)` was called 3 separate times for the same worksheet:
1. Once for STATUS scanning (processing.py)
2. Once for row processing (processing.py)
3. Once for word counting (compiler.py)

**Fix:** Moved the single preload BEFORE STATUS scanning so it serves all three purposes. The preloaded data is returned via `result["_preloaded"]` for the word counting step in compiler.py.

```python
# BEFORE: 3 calls to preload_worksheet_data()
qa_col_idx, qa_data_rows = preload_worksheet_data(qa_ws)  # Call 1: STATUS scan
qa_col_idx, qa_data_rows = preload_worksheet_data(qa_ws)  # Call 2: Row processing
wc_col_idx, wc_data_rows = preload_worksheet_data(qa_ws)  # Call 3: Word counting

# AFTER: 1 call, reused everywhere
qa_col_idx, qa_data_rows = preload_worksheet_data(qa_ws)  # Single call
result["_preloaded"] = (qa_col_idx, qa_data_rows)          # Passed to compiler
# STATUS scan, row processing, and word counting all use the same data
```

---

### Fix 2: read_only Mode for Script QA Files

**File:** `core/compiler.py`
**Impact:** HIGH — 3-5x faster QA file loading for Script categories

**Problem:** Script category QA files (Dialog, Sequencer) were opened in standard mode even though they are only read (no writes, no screenshot hyperlinks).

**Fix:** Script categories now use `safe_load_workbook(xlsx_path, read_only=True, data_only=True)`.

```python
# BEFORE: Standard mode (parses styles, formatting, everything)
qa_wb = safe_load_workbook(xlsx_path)

# AFTER: read_only for Script categories (3-5x faster load)
if category.lower() in SCRIPT_TYPE_CATEGORIES:
    qa_wb = safe_load_workbook(xlsx_path, read_only=True, data_only=True)
else:
    qa_wb = safe_load_workbook(xlsx_path)
```

**Why safe:** Script categories have no screenshot hyperlinks (image_mapping = {}), so no ws.cell() writes occur on QA workbooks. All QA data access uses preloaded tuples (iter_rows).

---

### Fix 3: Shared Sheet Data Cache Between Autofit and Hide

**Files:** `core/processing.py` + `core/compiler.py`
**Impact:** MEDIUM — eliminates one full iter_rows pass per sheet

**Problem:** `autofit_rows_with_wordwrap()` loaded all rows via `iter_rows()`. Then `hide_empty_comment_rows()` loaded the exact same rows again via `iter_rows()`. Two full passes over identical data.

**Fix:** `autofit_rows_with_wordwrap()` now returns a `sheet_data_cache` dict. `hide_empty_comment_rows()` accepts an optional `preloaded_sheets` parameter.

```python
# BEFORE: Two independent loads
autofit_rows_with_wordwrap(wb)                    # Loads all rows
hide_empty_comment_rows(wb)                       # Loads all rows AGAIN

# AFTER: Single load, shared cache
sheet_data_cache = autofit_rows_with_wordwrap(wb)  # Loads + returns cache
hide_empty_comment_rows(wb, preloaded_sheets=sheet_data_cache)  # Reuses cache
```

**Backward compatible:** `preloaded_sheets` defaults to `None`, falling back to fresh `iter_rows()`. Both `None` and empty dict are handled safely.

---

### Fix 4: Autofit Pass Merge (3 passes -> 2 passes)

**File:** `core/processing.py`
**Impact:** MEDIUM — eliminates one full ws.cell() pass over all data rows

**Problem:** `autofit_rows_with_wordwrap()` had 3 passes:
- Pass 1: Preload all rows + calculate column widths
- Pass 2: Calculate row heights from content
- Pass 3: Apply `WRAP_TOP_ALIGNMENT` via ws.cell() for every cell

**Fix:** Merged Pass 2 and Pass 3 into one loop. Height calculation and alignment application happen together. Only non-empty comment cells get ws.cell() calls (empty cells and non-comment columns are skipped entirely).

```python
# BEFORE: Separate passes
# Pass 2: Calculate heights
for row_idx, row_tuple in enumerate(all_rows[1:], start=2):
    # ... calculate max_lines
    ws.row_dimensions[row_idx].height = ...

# Pass 3: Apply alignment (ws.cell per cell!)
for row_idx in range(2, len(all_rows) + 1):
    for col_idx in comment_col_indices:
        ws.cell(row=row_idx, column=col_idx + 1).alignment = WRAP_TOP_ALIGNMENT

# AFTER: Single merged pass
for row_idx, row_tuple in enumerate(all_rows[1:], start=2):
    for col_idx in comment_col_indices:
        if cell_value:  # Only non-empty comment cells
            # Calculate height contribution
            # Apply alignment (ws.cell only for non-empty)
            ws.cell(row=row_idx, column=col_idx + 1).alignment = WRAP_TOP_ALIGNMENT
    ws.row_dimensions[row_idx].height = ...
```

---

### Fix 5: Consolidated ws.cell() for Master Comment Cell

**File:** `core/processing.py`
**Impact:** LOW — reduces ws.cell() calls by ~50% for comment writing

**Problem:** Two separate ws.cell() calls for the same master comment cell:
```python
existing = master_ws.cell(row=master_row, column=master_comment_col).value  # Call 1
# ... compute new_value ...
master_ws.cell(row=master_row, column=master_comment_col).value = new_value  # Call 2
```

**Fix:** Single cell reference:
```python
cell = master_ws.cell(row=master_row, column=master_comment_col)
existing = cell.value
# ... compute new_value ...
if new_value != existing:
    cell.value = sanitize_for_excel(new_value)
```

---

### Fix 6: read_only max_column Guard

**File:** `core/excel_ops.py`
**Impact:** CRITICAL (crash prevention) — prevents TypeError on empty sheets in read_only mode

**Problem:** In read_only mode, `ws.max_column` can be `None` for empty worksheets. Three functions used `range(1, ws.max_column + 1)` which crashes with `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`.

**Fix:** Added `max_col = ws.max_column or 0` guard to:
- `find_column_by_header()`
- `build_column_map()`
- `find_column_by_prefix()`

```python
# BEFORE: Crashes on None
for col in range(1, ws.max_column + 1):

# AFTER: Safe (empty range when None)
max_col = ws.max_column or 0
for col in range(1, max_col + 1):
```

**Why `or 0`:** `range(1, 0 + 1)` = `range(1, 1)` = empty range. Functions correctly return `None` / `{}` for empty sheets. Using `or 1` would wastefully scan one column of an empty sheet.

---

### Fix 7: Face iter_rows Conversion

**File:** `core/face_processor.py`
**Impact:** LOW-MEDIUM — faster deduplication scan

**Problem:** `_collect_previous_eventnames()` used a ws.cell() loop to scan old date tabs.

**Fix:** Converted to `iter_rows(min_row=2, max_col=1, values_only=True)`.

---

### Fix 8: Debug Header Scan read_only Compatibility

**File:** `core/processing.py`
**Impact:** LOW (crash prevention) — debug logging no longer crashes in read_only mode

**Problem:** Debug header logging used `ws.cell(row=1, column=col)` in a loop, which is slow in read_only mode and could crash on `ws.max_column + 1` when max_column is None.

**Fix:** Replaced with `iter_rows(min_row=1, max_row=1, values_only=True)`.

---

## Final Report Table (New Feature)

**File:** `core/compiler.py`

Added a clean box-formatted summary table printed in terminal at the end of every compilation:

```
+--------------------------------------------------------------------+
|                      FINAL COMPILATION REPORT                      |
+--------------------------------------------------------------------+
|  Total Time:         2m 35.4s                                      |
+--------------------------------------------------------------------+
|  Testers                   EN           CN        Total            |
|                             5            3            7            |
+--------------------------------------------------------------------+
|  Categories:   Dialog, Face, Quest, Sequencer                      |
+--------------------------------------------------------------------+
|  METRIC                                       COUNT                |
|  ----------------------------------------------------------------  |
|  Total Rows Processed                       123,456                |
|  Done (has status)                           98,765                |
|  NO ISSUE                                    87,654                |
|  ISSUE                                        5,432                |
|  Word Count                               1,234,567                |
+--------------------------------------------------------------------+
|  Master Files Saved: 4                                             |
+--------------------------------------------------------------------+
|  Output EN:    Masterfolder_EN                                     |
|  Output CN:    Masterfolder_CN                                     |
|  Tracker:      LQA_User_Progress_Tracker.xlsx                      |
+--------------------------------------------------------------------+
```

**Features:**
- All lines exactly 70 characters (verified programmatically)
- Dynamic: only shows rows with non-zero values (ISSUE, BLOCKED, KOREAN, MISMATCH, MISSING, Word Count)
- Handles both standard and Face category stats
- Truncates long paths to prevent overflow
- `finalize_futures` guarded against NameError (crash safety)
- `time.time()` captures total elapsed from start to finish

---

## Files Modified

| File | Changes |
|------|---------|
| `core/compiler.py` | `import time`, `compilation_start_time`, Fix 2 (read_only for Script), Fix 1 (reuse _preloaded), Fix 3 (cache pass-through in finalize), Final Report Table |
| `core/processing.py` | Fix 1 (single preload + _preloaded return), Fix 4 (autofit merge), Fix 5 (ws.cell consolidation), Fix 3 (autofit returns cache + hide accepts preloaded_sheets), Fix 8 (debug header iter_rows) |
| `core/excel_ops.py` | Fix 6 (max_column or 0 guard in 3 functions) |
| `core/face_processor.py` | Fix 7 (iter_rows conversion) |

---

## Verification

### Tests
- **12/12 tests pass** after all changes
- Tests ran after every individual fix round

### Review Agents (8 total)
| Agent | Focus | Verdict |
|-------|-------|---------|
| Review #1 | compiler.py changes | All fixes correct, found report table width bugs (fixed) |
| Review #2 | processing.py changes | Preload reuse correct, autofit merge equivalent, backward compatible |
| Review #3 | excel_ops.py changes | `or 0` guard correct, covers all read_only scenarios |
| Review #4 | face_processor.py | iter_rows conversion correct, identical output |
| Review #5 | Report table formatting | Found 5 misaligned lines (61-66 chars instead of 70) — all fixed |
| Review #6 | Thread safety | Core compilation thread-safe, finalize safe (independent wb/path per thread) |
| Explore #1 | Script build path deep scan | Found remaining bottlenecks in tracker modules (not on critical path) |
| Explore #2 | Face/Dialog ws.cell audit | Confirmed no hot-loop ws.cell() remaining in Script/Face path |

### Issues Found and Fixed During Review
1. **Report table line widths** — Testers rows were 61 chars (9 short), Metrics rows were 65 chars (5 short). Fixed with `W = 68` constant and consistent `f"|{content:<{W}}|"` pattern.
2. **Dead variable** — `face_entries_count` was incremented but never used. Removed.
3. **finalize_futures NameError** — If first ThreadPoolExecutor raised before `finalize_futures` was defined, report table would crash. Added `try/except NameError` guard.

### Known Pre-Existing Issues (NOT fixed, not on critical path)
- Debug log buffers (`_SCRIPT_DEBUG_LINES`) not thread-safe (cosmetic log interleaving only)
- Tracker modules still use ws.cell() in loops (not on Script master build path)
- `print()` throughout instead of `logger` (consistent pattern in all NewScripts tools)

---

## Optimization Summary Table (All Phases)

| Phase | Date | What | Speedup |
|-------|------|------|---------|
| 1 | Pre-498 | The Slow Era | Baseline |
| 2 | Build 498 | read_only + column cache | 3-5x load, 4471x lookup |
| 3 | Build 502 | CRITICAL: iter_rows fix for read_only | 10-100x |
| 4 | Post-503 | Single-pass master data collection | 3x fewer file opens |
| 5 | Post-503 | Universe pattern (Script) | 5-10x |
| 6 | Post-503 | Content-based O(1) matching | 100x+ |
| 7 | Build 518 | Style object pooling | 216x |
| 8 | Build 518 | Smart data structures everywhere | Various |
| 9 | Build 519+ | Unified method for data integrity | Correctness fix |
| **10** | **2026-02-06** | **Script masterfile final pass** | **See below** |

### Phase 10 Specific Gains

| Fix | Est. Savings | Description |
|-----|-------------|-------------|
| Triple preload elimination | 1-3s per Script file | Single preload serves STATUS + processing + word count |
| read_only for Script QA | 3-5x faster per QA file load | Streaming XML instead of full parse |
| Shared autofit/hide cache | 0.5-1s per master | One iter_rows pass instead of two |
| Autofit pass merge | 0.3-0.5s per master | 3 passes -> 2 passes |
| ws.cell() consolidation | Minor | One cell reference instead of two |
| max_column guard | Crash prevention | No runtime cost |

---

## Architecture After Phase 10

```
QA File Loading:
  Script categories -> read_only=True (NEW in Phase 10)
  Other categories  -> standard mode (needs ws.cell for hyperlinks)

Data Flow:
  preload_worksheet_data() called ONCE per QA worksheet
    |
    +-> STATUS scanning (uses preloaded tuples)
    +-> Row processing (uses preloaded tuples)
    +-> Word counting (via result["_preloaded"])

Post-Processing:
  autofit_rows_with_wordwrap(wb) -> returns sheet_data_cache
    |
    +-> hide_empty_comment_rows(wb, preloaded_sheets=cache)  (reuses data)

Finalization:
  ThreadPoolExecutor (parallel per master file)
    |
    +-> STATUS sheet update
    +-> Autofit (returns cache)
    +-> Hide empty rows (reuses cache)
    +-> Save

  Final Report Table (timing + stats + output paths)
```

---

*Phase 10 completes the Script masterfile optimization journey. All remaining bottlenecks on the Script/Face critical path have been addressed. Further gains would require fundamental architectural changes (xlsxwriter migration, incremental compilation) which are out of scope.*

*Verified by: 6 review agents + 2 explore agents*
*Tests: 12/12 pass*
*Build: GitHub Actions SUCCESS*
