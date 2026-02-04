# Performance Postmortem: read_only + ws.cell() Disaster

## Date: 2026-02-03
## Builds: 498-503
## Status: FIXED

---

## What Happened

An "optimization" in Build 498 introduced `read_only=True` to openpyxl workbook opens.
This made file **opening** 3-5x faster but made cell **access** 700x slower per call,
resulting in the tool freezing for 10+ minutes on Master_Quest.xlsx (11 sheets).

The user reported: *"Opening: Master_Quest.xlsx... 11 sheets"* and then complete freeze.
No progress, no logs, nothing. The tool appeared dead.

---

## Root Cause

### openpyxl's Two Modes

| Mode | `safe_load_workbook(path)` | `safe_load_workbook(path, read_only=True)` |
|------|---------------------------|-------------------------------------------|
| **File open** | Slower (loads all styles, formatting) | 3-5x faster (skips styles) |
| **`ws.cell(row, col)`** | O(1) dict lookup | O(n) XML re-parse from beginning |
| **`iter_rows(values_only=True)`** | O(n) sequential | O(n) streaming (correct way) |

In **normal mode**, cells are stored in a dict-like structure. `ws.cell(row, col)` is a
simple lookup - O(1).

In **read_only mode**, the worksheet is a streaming XML parser. `ws.cell(row, col)` forces
it to re-parse the XML from the beginning of the sheet every single time. A call to
`ws.cell(row=3000, col=5)` parses 3000 rows of XML just to return one value.

### Benchmark Results (3000-row test file)

```
ws.cell() on row 1:      1.16ms per call
ws.cell() on row 1500: 417.16ms per call  (360x slower)
ws.cell() on row 3000: 832.44ms per call  (720x slower)

Simulated pattern (100 rows x 5 users x 3 calls): 22.5 seconds
Extrapolated for 3000 rows x 5 users: 22,924 seconds (6.4 HOURS)
```

### Timeline of the Bug

| Build | Commit | Change | Impact |
|-------|--------|--------|--------|
| Pre-498 | `b060273` | 3 separate functions, NO read_only | Normal speed. Files opened 3x each but ws.cell() was O(1) |
| 498 | `651d08d` | Added `read_only=True` to preprocess_script_category | Script categories slowed down |
| 499 | `f4f46b7` | Consolidated into `collect_all_master_data()` with `read_only=True` + `ws.cell()` | **CATASTROPHIC**. Master data collection frozen 10+ min |
| 501 | `082bed2` | Added terminal progress logging | Logging couldn't print because code was frozen before reaching print statements |
| 502 | `6a500bc` | **FIX**: Converted `collect_all_master_data()` to `iter_rows` | Master collection fixed. Script QA still slow |
| 503 | `f50fdf1` | **FIX**: Removed `read_only=True` from QA file opens + streaming headers in preprocess | All remaining anti-patterns fixed |

---

## What Was Fixed

### Build 502: collect_all_master_data() (the main freeze)

**Before** (broken):
```python
wb = safe_load_workbook(master_path, read_only=True, data_only=True)
# ...
for row in range(2, ws.max_row + 1):
    status_value = ws.cell(row=row, column=status_col).value  # O(n) per call!
```

**After** (fixed):
```python
wb = safe_load_workbook(master_path, read_only=True, data_only=True)
# ...
header_iter = ws.iter_rows(min_row=1, max_row=1, values_only=True)
header_tuple = next(header_iter, None)  # Single streaming read

for row_tuple in ws.iter_rows(min_row=2, values_only=True):
    status_value = row_tuple[status_idx]  # O(1) tuple index!
```

### Build 503: process_category() QA file opens

**Before** (broken for Script categories):
```python
if is_script_category:
    qa_wb = safe_load_workbook(xlsx_path, read_only=True, data_only=True)
else:
    qa_wb = safe_load_workbook(xlsx_path)
```

**After** (all categories use normal mode):
```python
qa_wb = safe_load_workbook(xlsx_path)
```

Rationale: `process_sheet()`, `extract_qa_row_data()`, and the word-counting loop all
use `ws.cell()` per row. In normal mode this is O(1). The 3-5x faster open from
read_only is negligible compared to the per-row access cost.

### Build 503: preprocess_script_category() headers

**Before** (broken):
```python
# 4x find_column_by_header() calls — each uses ws.cell() loop on read_only ws
status_col = find_column_by_header(ws, "STATUS")
# ...
# Header collection with ws.cell() loop
for col in range(1, total_cols + 1):
    header_row.append(ws.cell(row=1, column=col).value)
```

**After** (streaming):
```python
# Single streaming header scan
col_map = build_column_map(ws)
status_col = col_map.get("STATUS")
# ...
# Streaming header collection
header_iter = ws.iter_rows(min_row=1, max_row=1, max_col=total_cols, values_only=True)
headers[sheet_name] = list(next(header_iter, None) or [])
```

---

## Current State (Build 503)

### Where read_only=True Is Still Used

| Location | Function | Why It's OK |
|----------|----------|-------------|
| `compiler.py:250` | `collect_all_master_data()` | All access via `iter_rows` (streaming). No `ws.cell()` |
| `compiler.py:561` | `preprocess_script_category()` | Headers via `build_column_map` (streaming). Data via `iter_rows`. No `ws.cell()` |

### Where Normal Mode Is Used

| Location | Function | Why Normal Mode |
|----------|----------|-----------------|
| `compiler.py:951` | `process_category()` QA files | `process_sheet()` uses `ws.cell()` per row. Must be O(1) |
| Various | Master workbooks | Written to, cannot be read_only |

---

## Rules for Future Optimization

### NEVER combine read_only=True with ws.cell()

```
RULE: If you use read_only=True, you MUST use iter_rows(values_only=True).
      If you need ws.cell(), use normal mode (no read_only).
      There is NO middle ground.
```

### When to Use read_only=True

- Function only READS data (never writes)
- ALL cell access converted to `iter_rows(values_only=True)` + tuple indexing
- Pre-compute 0-based column indices from header tuple
- Use `build_column_map(ws)` instead of `find_column_by_header(ws, name)`

### When to Use Normal Mode

- Function writes to the worksheet
- Function passes worksheet to other functions that use `ws.cell()`
- Function uses random access patterns (jumping to specific rows)
- Not worth the complexity of converting all access to streaming

---

## What to Monitor

### Performance Indicators

Watch terminal output during compilation for these timing signals:

1. **"Collecting master data..."** phase
   - Should complete in seconds, not minutes
   - Each master file should show per-sheet progress rapidly
   - If stuck on "Opening: Master_X.xlsx... N sheets" for >10s, something is wrong

2. **Per-category processing** ("Processing: Quest [EN]")
   - Each QA file should show sheet progress within seconds
   - Word counting should not be a bottleneck

3. **Autofit/Hide phases**
   - Per-sheet progress should flow continuously
   - These operate on normal-mode master workbooks, so ws.cell() is fine

### Red Flags

- Any phase taking >30 seconds with no progress output
- Disproportionate time on one master file vs others
- Memory usage climbing continuously (would indicate a different problem)

---

## Potential Future Optimizations

### 1. Pre-cache QA Row Data for process_sheet() (Medium effort, Medium impact)

Currently `process_sheet()` calls `ws.cell()` per row on normal-mode QA files. This is
O(1) per access, so not catastrophic. But pre-reading all rows into a list of tuples
would eliminate dict lookups entirely:

```python
# Pre-read all QA data into memory
qa_data = list(ws.iter_rows(min_row=2, values_only=True))
for row_idx, row_tuple in enumerate(qa_data, start=2):
    status = row_tuple[status_idx]
    # ...
```

**When to consider**: If QA files grow beyond 10,000 rows per sheet.

### 2. Parallel Category Processing (High effort, High impact)

Currently categories are processed sequentially. Each category is independent (separate
master file). Could use `concurrent.futures.ProcessPoolExecutor` to process multiple
categories in parallel.

**When to consider**: If total compilation time exceeds 5 minutes with many categories.

### 3. Incremental Compilation (High effort, Very high impact)

Currently reprocesses ALL QA files every run. Could track file modification times and
only reprocess changed files, merging results with cached data.

**When to consider**: If the same compilation is run frequently with few changes.

### 4. Convert build_master_index() to Streaming (Low effort, Low impact)

In `matching.py`, `build_master_index()` uses `ws.cell()` per row on master worksheets.
These are normal mode so it's O(1), but converting to `iter_rows` would be marginally
faster by eliminating dict overhead.

**When to consider**: If master files grow beyond 20,000 rows.

---

## Lessons Learned

1. **"Optimization" that changes access patterns can be a deoptimization.** Adding
   `read_only=True` saved milliseconds on file open but cost minutes on cell access.

2. **Always benchmark after optimization.** The 3-5x faster open claim was correct but
   irrelevant — the dominant cost was the 700x slower per-cell access.

3. **Terminal progress logging is essential.** Without per-sheet progress prints, the
   tool appeared dead. Build 501 added logging but the code was frozen before reaching
   the print statements. Both logging AND performance must work together.

4. **read_only mode is an all-or-nothing commitment.** You cannot partially use it —
   either ALL access is streaming (iter_rows) or you use normal mode.
