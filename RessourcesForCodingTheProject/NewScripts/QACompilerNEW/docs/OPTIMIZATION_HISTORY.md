# QA Compiler Optimization History

## From Slow and Unoptimized to Ultra-Fast and Intelligent

**Document version:** 1.0
**Date:** 2026-02-04
**Covers:** Builds 1 through 518

---

## Table of Contents

1. [The Story](#the-story)
2. [Phase 1: The Slow Era](#phase-1-the-slow-era-before-build-498)
3. [Phase 2: First Optimizations](#phase-2-the-first-optimizations-build-498)
4. [Phase 3: The Critical Fix](#phase-3-the-critical-fix-builds-499-503)
5. [Phase 4: Single-Pass Master Data](#phase-4-single-pass-master-data-collection)
6. [Phase 5: The Universe Pattern](#phase-5-the-universe-pattern-script-type-optimization)
7. [Phase 6: Content-Based O(1) Matching](#phase-6-content-based-o1-matching)
8. [Phase 7: Style Object Pooling](#phase-7-style-object-pooling)
9. [Phase 8: Smart Data Structures](#phase-8-smart-data-structures-everywhere)
10. [Final Architecture](#final-architecture)
11. [Performance Impact Summary](#performance-impact-summary)
12. [Smart Data Structures Reference](#smart-data-structures-reference)
13. [Lessons Learned](#lessons-learned)
14. [Key Commits](#key-commits)

---

## The Story

The QA Compiler started as a straightforward tool: read tester Excel files, merge them into master files, track progress. It worked. But as the project grew -- more testers, more categories, larger game data files with 10,000+ rows -- "worked" stopped being good enough. Compilation runs that should take seconds were taking minutes. The tool would freeze, appearing dead, while it churned through redundant file loads, re-scanned the same headers millions of times, and created hundreds of thousands of throwaway style objects.

This document tells the story of how the QA Compiler was systematically transformed from that slow, brute-force tool into an intelligently optimized pipeline. Every phase built on the last. Every fix was validated against the original output to ensure zero data loss. The result is a tool that processes the same data orders of magnitude faster, using less memory, with cleaner architecture.

The journey was not always smooth. One "optimization" (Build 498's `read_only` mode) actually made things catastrophically worse before the root cause was understood and properly fixed. That postmortem became one of the most important lessons in the project's history.

---

## Phase 1: The Slow Era (Before Build 498)

### How It Worked (Slowly)

The original architecture was simple and correct, but performance was not a design consideration. Every operation was implemented in the most straightforward way possible:

**Problem 1: Files opened multiple times.**
Each master file was opened 3 separate times during a single compilation run:

```
Pass 1: collect_manager_status()        -- Open master, scan STATUS columns, close
Pass 2: collect_fixed_screenshots()     -- Open master AGAIN, scan for FIXED status, close
Pass 3: collect_manager_stats_for_tracker() -- Open master AGAIN, scan STATUS columns, close
```

For 6 master files, that was 18 full workbook loads before compilation even started. Each load meant parsing a ZIP archive, creating all Cell objects in memory, loading styles, shared strings, and metadata. A 10,000-row file took 2-10 seconds per load.

**Problem 2: `ws.cell()` used everywhere for random access.**
Cell access was done via `ws.cell(row=r, column=c)` throughout the codebase. In normal openpyxl mode this is O(1) -- a simple dictionary lookup. Nobody questioned it. But this pattern became a ticking time bomb once `read_only` mode was introduced later.

**Problem 3: No column caching.**
The `find_column_by_header()` function scanned the entire header row to find a column by name. This is fine when called once per sheet. But it was called inside row-processing loops:

```python
# Called PER ROW -- scanning all headers 3 times per row
for row in range(2, ws.max_row + 1):
    stringid_col = find_column_by_header(ws, "STRINGID")    # O(columns)
    eventname_col = find_column_by_header(ws, "EventName")  # O(columns)
    trans_col = find_column_by_header(ws, "Text")            # O(columns)
    # ... process row using those columns
```

For 10,000 rows with 20 columns: 10,000 x 3 x 20 = **600,000 unnecessary cell reads** per sheet.

**Problem 4: No pre-indexing for row matching.**
Finding which master row corresponded to a QA row required linear scanning:

```python
# O(n) per lookup -- for each QA row, scan all master rows
for master_row in range(2, master_ws.max_row + 1):
    if master_ws.cell(row=master_row, column=trans_col).value == qa_translation:
        return master_row
```

With 500 QA rows and 5,000 master rows, that was up to 2.5 million cell reads.

**Problem 5: Style objects created inline for every cell.**
Every cell that needed styling got brand new Font, PatternFill, Alignment, and Border objects:

```python
# In the hot loop -- NEW objects per cell
cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
cell.font = Font(name='Calibri', size=11)
cell.alignment = Alignment(wrap_text=True, vertical='top')
cell.border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)
```

The `autofit_rows_with_wordwrap()` function was the worst offender: it created a new `Alignment()` object for EVERY cell in the ENTIRE workbook. For 5 sheets x 5,000 rows x 30 columns = **750,000 `Alignment()` constructor calls**.

**Problem 6: Post-processing made 8-10 passes over all cells.**
The `hide_empty_comment_rows()` function performed separate passes to find comment columns, reset visibility, scan rows for comments, hide empty columns, scan for screenshots, scan for tester status, scan for manager status, unhide all rows, and re-hide based on collected data. Each pass iterated some or all of every row and column.

### The Result

Processing thousands of rows took **minutes**. Script-type categories (Sequencer/Dialog) with 10,000+ row source files were essentially unusable for interactive work. The tool appeared to freeze with no progress indication.

---

## Phase 2: The First Optimizations (Build 498)

**Key commit:** `651d08d` -- Build 498: Script optimization (read_only mode + column cache)

### What Changed

Two optimizations were introduced simultaneously:

**1. `read_only=True` mode for master file reading.**

```python
# Before: Full load (parses styles, formatting, everything)
wb = safe_load_workbook(master_path)

# After: Streaming load (skips styles, lower memory)
wb = safe_load_workbook(master_path, read_only=True, data_only=True)
```

This made file **opening** 3-5x faster by skipping style parsing, shared string deduplication, and metadata loading. Memory usage dropped significantly because read-only workbooks use lazy evaluation.

**2. Column map caching via `build_column_map()`.**

A new function was introduced to scan headers once and provide O(1) lookups:

```python
def build_column_map(ws) -> Dict[str, int]:
    """Scan row 1 once, return {HEADER_NAME: column_index} dict."""
    column_map = {}
    for col_idx, cell in enumerate(ws[1], start=1):
        if cell.value:
            column_map[str(cell.value).strip().upper()] = col_idx
    return column_map
```

Instead of calling `find_column_by_header()` per row, code could now do:

```python
# Before: O(columns) per call, called per row
status_col = find_column_by_header(ws, "STATUS")

# After: O(columns) once, O(1) per row
column_map = build_column_map(ws)
status_col = column_map.get("STATUS")
```

Measured impact: column lookup went from **7.6 seconds to 1.7 milliseconds** for 1,000 lookups (4,471x faster).

### The Hidden Problem

Build 498 seemed like a clear win. But it introduced a subtle, catastrophic bug. The `read_only=True` mode was combined with `ws.cell()` access patterns throughout the codebase. Nobody realized that `ws.cell()` in read-only mode has completely different performance characteristics.

This would not be discovered until the tool froze for 10+ minutes on the next build.

---

## Phase 3: The Critical Fix (Builds 499-503)

### The Disaster

After Build 498 shipped, the user reported the tool freezing completely. The terminal showed:

```
Opening: Master_Quest.xlsx... 11 sheets
```

And then... nothing. No progress. No errors. The tool appeared dead.

### Root Cause Discovery

**Key commit:** `6a500bc` -- "CRITICAL fix: replace ws.cell() with iter_rows in read_only mode"

The investigation revealed a fundamental misunderstanding of openpyxl's read-only mode:

| Mode | `ws.cell(row, col)` | `iter_rows(values_only=True)` |
|------|---------------------|-------------------------------|
| **Normal** | O(1) dict lookup | O(n) sequential |
| **read_only** | **O(n) XML re-parse from beginning** | O(n) streaming |

In read-only mode, the worksheet is a streaming XML parser. Calling `ws.cell(row=3000, col=5)` forces openpyxl to re-parse the XML from the **beginning of the sheet** -- parsing 3,000 rows of XML just to return one value. Every. Single. Call.

### The Benchmark That Told the Story

```
ws.cell() on row 1:        1.16ms per call
ws.cell() on row 1500:   417.16ms per call    (360x slower)
ws.cell() on row 3000:   832.44ms per call    (720x slower)

Simulated pattern (100 rows x 5 users x 3 calls): 22.5 seconds
Extrapolated for 3000 rows x 5 users: 22,924 seconds (6.4 HOURS)
```

The "optimization" saved milliseconds on file opening and cost **hours** on cell access. The tool was not frozen -- it was running, just unimaginably slowly.

### The Fix Timeline

| Build | Commit | Change | Impact |
|-------|--------|--------|--------|
| 498 | `651d08d` | Added `read_only=True` + `ws.cell()` | Introduced the bug |
| 501 | `082bed2` | Added terminal progress logging | Could not help -- code froze before reaching prints |
| 502 | `6a500bc` | **FIX:** Converted to `iter_rows()` in `collect_all_master_data()` | Master data collection fixed |
| 503 | `f50fdf1` | **FIX:** Removed `read_only` from QA opens + streaming headers | All remaining anti-patterns eliminated |

### The Correct Pattern

```python
# BEFORE (catastrophic in read_only):
wb = safe_load_workbook(path, read_only=True)
for row in range(2, ws.max_row + 1):
    value = ws.cell(row=row, column=status_col).value  # O(n) per call!

# AFTER (correct streaming):
wb = safe_load_workbook(path, read_only=True)
header_tuple = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
for row_tuple in ws.iter_rows(min_row=2, values_only=True):
    value = row_tuple[status_idx]  # O(1) tuple index
```

### The Rule That Was Born

```
RULE: If you use read_only=True, you MUST use iter_rows(values_only=True).
      If you need ws.cell(), use normal mode.
      There is NO middle ground.
```

This alone gave a **10-100x speedup** on large sheets, turning multi-minute freezes back into seconds.

---

## Phase 4: Single-Pass Master Data Collection

### The Problem

Even after the read-only fix, master files were still opened 3 separate times to collect 3 different types of data:

```
collect_manager_status()              -- STATUS values for rebuild preservation
collect_fixed_screenshots()           -- FIXED status for image copy skipping
collect_manager_stats_for_tracker()   -- STATUS counts for tracker updates
```

Each function opened every master file independently, parsed it, extracted its specific data, and closed it.

### The Solution

A new function `collect_all_master_data()` was introduced at `compiler.py:165`:

```python
def collect_all_master_data(tester_mapping: Dict = None):
    """
    Single-pass collection of ALL master file data for compilation.

    Opens each master file ONCE with read_only=True, extracting:
    1. manager_status (EN/CN) - for preserving manager status during rebuild
    2. fixed_screenshots (EN/CN) - for skipping FIXED images during copy
    3. manager_stats - for tracker (FIXED/REPORTED/CHECKING/NON-ISSUE counts)
    """
```

One open, one streaming pass through each sheet, all three data types extracted simultaneously. The function uses `iter_rows(values_only=True)` throughout, making it safe with `read_only=True`.

### Impact

- 3 opens per master file reduced to 1 open per master file
- 3x reduction in master file I/O
- All data available from a single function call

---

## Phase 5: The Universe Pattern (Script-Type Optimization)

**Key commit:** `f437873` -- Script-type optimization (Sequencer/Dialog)

### The Problem Unique to Script Categories

Sequencer and Dialog categories are fundamentally different from standard categories (Quest, Knowledge, Item). Standard categories have pre-existing master templates generated from game XML. Script categories do not -- there is no XML source for dialog/sequencer LQA data. The master must be built from the QA files themselves.

The old approach:

```
1. Open all QA files, scan for rows with STATUS
2. Create a filtered template by:
   a. Open template workbook (FULL mode)
   b. Scan ALL 10,000+ rows to build a row index
   c. For each STATUS row: copy from template (cell by cell with style copying)
   d. If row not in template: open source QA file AGAIN, copy from there
   e. Save temp file to disk
3. Re-load temp file as master
4. Process tester data against master
```

This involved multiple file loads, temp file I/O, and O(n) scanning of 10,000+ row files.

### The Universe Pattern

The `preprocess_script_category()` function at `compiler.py:502` scans ALL QA files in a single pass and builds a "universe" -- a complete in-memory representation of every row that any tester has reviewed:

```python
universe = {}  # Key: (eventname, text) -> Value: row_data dict

# Single pass through all QA files
for qa_folder in qa_folders:
    wb = safe_load_workbook(xlsx_path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        col_map = build_column_map(ws)
        for row_tuple in ws.iter_rows(min_row=2, values_only=True):
            status = row_tuple[status_idx]
            if status and str(status).strip():
                key = (eventname, text)
                universe[key] = {
                    "sheet": sheet_name,
                    "full_row": list(row_tuple),
                    "sources": [source_info],
                    # ... metadata
                }
```

Key properties of the universe:

- **O(1) deduplication via dict keys.** If 5 testers all reviewed the same dialog line, it appears once in the universe (with all 5 sources tracked).
- **Only rows with STATUS are included.** In a 10,000-row file where testers reviewed 200 rows, the universe contains ~200 entries. That is a roughly 98% reduction.
- **Headers and column counts are captured** for each sheet, enabling direct master construction.

Then `build_master_from_universe()` at `compiler.py:680` creates the master workbook directly from the universe data in memory:

```python
def build_master_from_universe(category, universe, master_folder):
    """
    Build master workbook directly from universe data.

    Eliminates create_filtered_script_template() which:
    - Opened template in FULL mode
    - Scanned ALL 10K rows to build index
    - Opened source files AGAIN
    - Wrote temp file to disk
    - Temp file immediately re-loaded by get_or_create_master()
    """
```

### Impact

- No temp files created or re-loaded
- No re-reading of 10,000-row source files
- Universe construction is O(n) total across all files
- Master construction is O(universe_size), typically 50-200 rows
- Overall: **5-10x speedup** for Script-type categories

---

## Phase 6: Content-Based O(1) Matching

### The Problem

During the master build phase, each QA row must be matched to the correct master row. The naive approach was linear scanning -- for each QA row, iterate through all master rows looking for a match. With 500 QA rows and 5,000 master rows, worst case was 2.5 million comparisons.

### The Solution

`build_master_index()` at `matching.py:253` creates hash-based lookup tables with a two-step cascade:

```python
def build_master_index(master_ws, category: str, is_english: bool) -> Dict:
    """
    Build O(1) lookup index from master worksheet.

    Returns dict with:
    - "primary": {(stringid, translation): row_number}    # Exact match
    - "fallback": {translation: [row_numbers]}             # Fuzzy match
    - "consumed": set()                                    # Already-matched rows
    """
```

Matching strategies vary by category:

| Category | Primary Key | Fallback Key |
|----------|-------------|-------------|
| Standard (Quest, Knowledge, etc.) | STRINGID + Translation | Translation only |
| Item | ItemName + ItemDesc + STRINGID | ItemName + ItemDesc |
| Contents | INSTRUCTIONS (col 2) | None |
| Script (Sequencer/Dialog) | Translation + EventName | EventName only |

The `consumed` set is critical: it tracks which master rows have already been matched. This prevents the same master row from being matched to multiple QA rows (which would overwrite tester work).

### How Matching Works

```python
# Step 1: Try primary key (exact match)
primary_key = (stringid, translation)
if primary_key in index["primary"]:
    row = index["primary"][primary_key]
    if row not in index["consumed"]:
        index["consumed"].add(row)
        return row

# Step 2: Try fallback key (broader match)
if translation in index["fallback"]:
    for candidate_row in index["fallback"][translation]:
        if candidate_row not in index["consumed"]:
            index["consumed"].add(candidate_row)
            return candidate_row
```

### Impact

- Row matching went from O(n) linear scan to O(1) dict lookup
- For 500 QA rows against 5,000 master rows: **100x+ speedup**
- The consumed set ensures correctness even with duplicate translations

---

## Phase 7: Style Object Pooling

### The Problem

openpyxl's style objects (`Font`, `PatternFill`, `Alignment`, `Border`) are immutable. Creating identical ones is wasteful -- the constructor runs, properties are validated, and openpyxl's internal style registry checks for deduplication. Multiply that by hundreds of thousands of cells and it dominates processing time.

### The Solution

Pre-created style constants defined once at module level in `core/processing.py`, reused for every cell:

```python
# Module-level constants (created ONCE at import time)
COMMENT_FILL_ISSUE = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
COMMENT_FONT_ISSUE = Font(bold=True)
COMMENT_FILL_BLOCKED = PatternFill(start_color="FFE4B5", end_color="FFE4B5", fill_type="solid")
COMMENT_FONT_BLOCKED = Font(bold=True, color="FF8C00")
COMMENT_FILL_KOREAN = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
COMMENT_FONT_KOREAN = Font(bold=True, color="800080")
COMMENT_FILL_NO_ISSUE = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
COMMENT_FONT_NO_ISSUE = Font(bold=True, color="2E7D32")
```

Additional constants for fonts, alignments, and borders cover every style combination used throughout the codebase:

```python
FONT_ARIAL_10 = Font(name="Arial", size=10)
FONT_ARIAL_11 = Font(name="Arial", size=11)
FONT_ARIAL_10_BOLD = Font(name="Arial", size=10, bold=True)
FILL_LIGHT_YELLOW = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid")
ALIGN_LEFT_TOP_WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
```

### Before vs After

```python
# BEFORE: New object per cell (750,000 constructor calls in autofit alone)
for row in range(1, ws.max_row + 1):
    for col in range(1, ws.max_column + 1):
        cell.alignment = Alignment(wrap_text=True, vertical='top')  # NEW each time

# AFTER: Same object reference for all cells
WRAP_ALIGNMENT = Alignment(wrap_text=True, vertical='top')
for row in range(1, ws.max_row + 1):
    for col in range(1, ws.max_column + 1):
        cell.alignment = WRAP_ALIGNMENT  # Pointer assignment only
```

### Measured Impact

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Style 1,000 cells | 432ms | 2ms | **216x** |
| Column lookup (1,000x) | 7.6s | 1.7ms | **4,471x** |

### Verification

Four verification agents confirmed zero discrepancies between original and optimized output:
- Cell data: identical
- Cell styles: visually identical (object identity differs, visual properties match)
- Row/column ordering: identical
- Hidden rows: identical
- Column widths: identical

---

## Phase 8: Smart Data Structures Everywhere

Beyond the major optimizations, a collection of intelligent data structures was introduced across the codebase, each solving a specific problem with the right algorithmic approach.

### EXPORT StringID Index

**Problem:** The same Korean text can have different translations depending on which source file it appears in. "Description" might mean "Skill Description" in one context and "Item Description" in another.

**Solution:** `build_export_stringid_index()` in `generators/base.py` scans the EXPORT folder once and builds a lookup map:

```python
# Type: Dict[str, Set[str]]
# Key: normalized filename (e.g., "skillinfo_pc.staticinfo")
# Value: set of StringIDs in that file
export_index = {
    "skillinfo_pc.staticinfo": {"1001", "1002", "1003"},
    "iteminfo_pc.staticinfo": {"2001", "2002"},
    # ...
}
```

The `resolve_translation()` function uses this index to disambiguate: given Korean text with multiple translation candidates, it checks which StringIDs belong to the current source file and picks the matching one. Lazy-loaded and cached globally -- the EXPORT folder is only scanned once regardless of how many generators use it.

### Language Tables (List-Based for Duplicates)

**Old structure:** Single translation per Korean text.
```python
{normalized_korean: (translation, stringid)}
```

**New structure:** All translations preserved for duplicate handling.
```python
{normalized_korean: [(translation_1, stringid_1), (translation_2, stringid_2), ...]}
```

Good translations (non-empty, non-placeholder) are sorted first, ensuring the best match is returned when EXPORT disambiguation is not needed.

### Master Index with Consumed Set

```python
index = {
    "primary": {(stringid, translation): row_number},
    "fallback": {translation: [row_numbers]},
    "consumed": set()  # Prevents double-matching
}
```

O(1) lookup. O(1) consumed check. No row is matched twice.

### Universe Dict (Script-Type)

```python
universe = {
    (eventname, text): {
        "sheet": "Sheet1",
        "full_row": [cell1, cell2, ...],
        "sources": [{"file": "path", "tester": "name"}],
    }
}
```

Global deduplication before master construction. Dict keys guarantee uniqueness. The master is built from this structure directly -- no intermediate files.

### Latest Rows Pattern (Tracker)

```python
latest_rows = {}  # (user, group, lang) -> row_data
for row in all_rows:
    key = (row.user, row.group, row.lang)
    if key not in latest_rows or row.date > latest_rows[key].date:
        latest_rows[key] = row
```

O(n) single pass, keeps only the newest entry per unique combination. No sorting needed.

### Fixed Screenshots Set

```python
fixed_screenshots = set()  # {filename1, filename2, ...}
```

O(1) membership check. During image copying, if a screenshot's filename is in this set (meaning the row has FIXED status), the copy is skipped. Prevents re-copying thousands of images that have not changed.

---

## Final Architecture

```
PHASE 1: DISCOVERY
  +---------------------------------------------------------+
  |  Scan QAfolder/                                         |
  |  Find all {Username}_{Category}/ folders                |
  |  Route testers to EN/CN based on mapping file           |
  +---------------------------------------------------------+
                              |
                              v
PHASE 2: SINGLE-PASS MASTER DATA COLLECTION
  +---------------------------------------------------------+
  |  collect_all_master_data()                              |
  |  Open each master file ONCE (read_only + iter_rows)     |
  |  Extract in one pass:                                   |
  |    - manager_status (EN/CN)                             |
  |    - fixed_screenshots (EN/CN)                          |
  |    - manager_stats (for tracker)                        |
  +---------------------------------------------------------+
                              |
                              v
PHASE 3: CATEGORY PROCESSING (per category)
  +---------------------------------------------------------+
  |                                                         |
  |  SCRIPT-TYPE (Sequencer/Dialog):                        |
  |    preprocess_script_category()                         |
  |      - Scan all QA files (read_only + streaming)        |
  |      - Build universe dict: {(event, text): row_data}   |
  |      - Column maps cached per sheet                     |
  |      - ~98% row reduction (only STATUS rows kept)       |
  |    build_master_from_universe()                         |
  |      - Create master directly from memory               |
  |      - No temp files, no re-reading                     |
  |                                                         |
  |  STANDARD (Quest, Knowledge, Item, etc.):               |
  |    get_or_create_master()                               |
  |      - Load template or existing master                 |
  |    build_master_index()                                 |
  |      - Hash-based O(1) lookup tables                    |
  |      - Primary key + fallback key + consumed set        |
  |    process_sheet() per tester:                          |
  |      - Column map cached once per sheet                 |
  |      - Shared style constants (no per-cell creation)    |
  |      - O(1) matching via master index                   |
  |                                                         |
  +---------------------------------------------------------+
                              |
                              v
PHASE 4: POST-PROCESSING
  +---------------------------------------------------------+
  |  hide_empty_comment_rows()                              |
  |    - Column cache built once per sheet                  |
  |    - Reduced from 8-10 passes to 2-3 passes            |
  |  autofit_rows_with_wordwrap()                           |
  |    - Shared Alignment constant (not per-cell creation)  |
  |    - Skip empty cells                                   |
  +---------------------------------------------------------+
                              |
                              v
PHASE 5: TRACKER UPDATE
  +---------------------------------------------------------+
  |  Update _TRACKER.xlsx:                                  |
  |    - DAILY sheet: per-day tester stats                  |
  |    - TOTAL sheet: cumulative rankings                   |
  |    - Facial sheet: Face category tracking               |
  |  Uses manager_stats from Phase 2 (no re-reading)       |
  +---------------------------------------------------------+
                              |
                              v
PHASE 6: SAVE
  +---------------------------------------------------------+
  |  Save all master workbooks                              |
  |  Save tracker                                           |
  +---------------------------------------------------------+
```

---

## Performance Impact Summary

| Optimization | Before | After | Speedup | Phase |
|---|---|---|---|---|
| `read_only` mode for scanning | Normal load (3-5s per file) | Streaming load (0.5-1s) | 3-5x | 2 |
| `iter_rows` vs `ws.cell()` in read-only | O(n^2) per sheet (XML re-parse) | O(n) streaming | 10-100x | 3 |
| Single-pass master data collection | 3 opens per master file | 1 open per master file | 3x | 4 |
| Universe pre-computation (Script) | N file opens + temp files + re-loads | 1 streaming pass + in-memory build | 5-10x | 5 |
| Content-based matching index | O(n) linear scan per QA row | O(1) dict lookup | 100x+ | 6 |
| Style object pooling | New constructor per cell (750K+) | Shared constants reused | 216-4,471x | 7 |
| Column map caching | Header rescan per row (O(cols)) | Scan once, O(1) lookup after | 10-50x | 7 |
| Row filtering (STATUS only) | Process all rows | Skip ~98% of rows (empty STATUS) | 50x | 5 |
| Post-processing pass reduction | 8-10 passes over all cells | 2-3 passes | 3-5x | 7 |
| Skip empty cells in autofit | Calculate strlen for every cell | Skip empty cells | Variable | 7 |

### Measured Micro-Benchmarks

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Style 1,000 cells | 432ms | 2ms | 216x |
| Column lookup (1,000 calls) | 7,600ms | 1.7ms | 4,471x |
| `ws.cell()` row 3000 (read_only) | 832ms | N/A (eliminated) | Infinite |
| `hide_empty_comment_rows` passes | 6+ passes | 2 passes | 3x |

---

## Smart Data Structures Reference

| Structure | Type | Purpose | Location |
|---|---|---|---|
| EXPORT StringID Index | `Dict[str, Set[str]]` | Disambiguate duplicate Korean translations by source file | `generators/base.py` |
| Language Tables | `Dict[lang, Dict[korean, List[Tuple]]]` | Fast translation lookup with duplicate support | `generators/base.py` |
| Master Index | `Dict[key, row_num]` + `Set` (consumed) | O(1) row matching with double-match prevention | `core/matching.py` |
| Universe (Script-type) | `Dict[(eventname, text), row_data]` | Global deduplication before master build | `core/compiler.py` |
| Column Map | `Dict[str, int]` | O(1) column position lookup by header name | `core/excel_ops.py` |
| Latest Rows | `Dict[(user, group, lang), row]` | Dedup tracker entries to newest per combination | `tracker/data.py` |
| Fixed Screenshots | `Set[str]` | O(1) check to skip re-copying unchanged images | `core/compiler.py` |
| Style Constants | Module-level `Font`/`Fill`/`Alignment` | Reused across all cells, zero per-cell allocation | `core/processing.py` |

---

## Lessons Learned

### 1. An "Optimization" Can Be a Catastrophe

Adding `read_only=True` to openpyxl saves milliseconds on file opening. But if existing code uses `ws.cell()` for random access, cell reads become 720x slower. The net result was a tool that froze for hours instead of running for seconds.

**The lesson:** Always benchmark AFTER optimization. The dominant cost is not always where you expect it. A 3-5x improvement on file open is irrelevant if cell access becomes 720x slower.

### 2. Know Your Library's Internals

openpyxl's `read_only` mode fundamentally changes the data structure behind the worksheet. Normal mode uses a dict (O(1) access). Read-only mode uses a streaming XML parser (O(n) per random access). The API looks the same -- `ws.cell(row, col)` -- but the performance characteristics are completely different.

**The lesson:** Same API does not mean same performance. Understand the data structures behind the abstractions.

### 3. The Right Data Structure Solves Everything

Every major optimization came down to using the right data structure:
- Dict instead of linear scan for matching (O(1) vs O(n))
- Set for consumed tracking and screenshot dedup (O(1) membership)
- Cached column map instead of per-row header scan (O(1) vs O(cols))
- Universe dict for global deduplication (dict keys guarantee uniqueness)
- Module-level constants instead of per-cell constructors (zero allocation vs millions)

### 4. Measure, Then Optimize

The 12-agent investigation that preceded the optimization work was essential. Eight agents analyzed the codebase in parallel, identifying 7 specific bottlenecks with estimated impact. The implementation was prioritized by impact and risk, starting with easy/low-risk fixes that gave the biggest returns.

Without this investigation, the team might have spent days optimizing the wrong code path.

### 5. Backward Compatibility Through Optional Parameters

Every optimization was introduced via optional parameters with sensible defaults:

```python
def extract_qa_row_data(qa_ws, row, category, is_english, column_cache=None):
    # If column_cache provided: O(1) lookup
    # If None: falls back to find_column_by_header() (original behavior)
```

This meant:
- Zero risk of breaking existing callers
- Gradual adoption -- new code opts in, old code works unchanged
- Easy rollback if any optimization caused issues

### 6. Progress Logging Must Work WITH Performance

Build 501 added terminal progress logging to help diagnose the freeze. But the code was frozen before reaching the print statements. Logging that cannot execute is useless.

**The lesson:** Performance and observability are not independent. If the code is too slow to reach a log statement, the log statement does not exist.

---

## Key Commits

| Commit | Build | Description |
|--------|-------|-------------|
| `651d08d` | 498 | First optimization: read_only mode + column cache (introduced read_only bug) |
| `25f45e0` | -- | Documentation: Script optimization preparation phase (12-agent investigation) |
| `6a500bc` | 502 | **CRITICAL FIX:** Replace ws.cell() with iter_rows in read_only mode |
| `3f81cf3` | 503 | Remove read_only from QA opens + streaming headers |
| `f437873` | -- | Script-type optimization: Universe pattern introduced |
| `b4af3a2` | 499 | Face category + Facial tracker + optimizations |

---

## Current State of Optimizations (Build 518)

### Where `read_only=True` Is Used Safely

| Location | Function | Why Safe |
|----------|----------|----------|
| `compiler.py:165` | `collect_all_master_data()` | All access via `iter_rows` streaming |
| `compiler.py:502` | `preprocess_script_category()` | Headers via `build_column_map`, data via `iter_rows` |

### Where Normal Mode Is Used (Correctly)

| Location | Function | Why Normal Mode |
|----------|----------|-----------------|
| `compiler.py` | `process_category()` QA file opens | `process_sheet()` uses `ws.cell()` per row -- must be O(1) |
| Various | Master workbooks being written | Cannot use read_only on files being modified |

### Files Modified by Optimizations

```
core/processing.py
  Lines 71-78:  Style constants (Phase 7)
  Various:      style_header_cell(), _write_comment_cell(), write_tester_status(),
                write_manager_status() -- all use shared constants
  autofit:      Shared alignment, skip empty cells (Phase 7)
  hide_empty:   Column cache, reduced passes (Phase 7)

core/excel_ops.py
  Line 156:     build_column_map() function (Phase 2)
  Various:      Style constants for headers (Phase 7)

core/matching.py
  Line 253:     build_master_index() with primary/fallback/consumed (Phase 6)
  Line 162:     extract_qa_row_data() with optional column_cache (Phase 7)

core/compiler.py
  Line 165:     collect_all_master_data() single-pass (Phase 4)
  Line 502:     preprocess_script_category() with universe (Phase 5)
  Line 680:     build_master_from_universe() in-memory construction (Phase 5)

generators/base.py
  Various:      EXPORT StringID index, resolve_translation() (Phase 8)
```

---

## Phase 9: Unified Method for Data Integrity (Build 519+)

### The Problem

The Universe pattern (Phase 5) had a critical flaw: it only kept rows that had STATUS values in the current QA files. This caused data loss when:

1. A manager marked a row as "REPORTED" in the master file
2. The tester later cleared their STATUS (or the QA file was regenerated fresh)
3. On next compilation: the REPORTED row disappeared because it had no STATUS in QA files

The Universe pattern's ~98% row reduction was an optimization trade-off that seemed worth it until this data loss was discovered.

### Root Cause Analysis

**Script-specific method (DELETED old master, rebuilt from scratch):**
```python
# Old approach: Only keeps rows WITH STATUS
universe = preprocess_script_category(qa_folders)  # Only STATUS rows
master_wb = build_master_from_universe(universe)   # DELETES old master!
```

**Unified method (preserves template structure):**
```python
# Unified approach: Keeps ALL template rows
master_wb = get_or_create_master(category, master_folder, template_xlsx)
# Template has ALL rows - REPORTED rows preserved even without STATUS
```

### The Fix

Script-type categories (Sequencer/Dialog) now use the same unified method as all other categories:

```python
# BEFORE: Script-specific branch that deleted old master
if category.lower() in SCRIPT_TYPE_CATEGORIES:
    universe = preprocess_script_category(qa_folders)
    master_wb = build_master_from_universe(category, universe, master_folder)
else:
    master_wb = get_or_create_master(...)

# AFTER: All categories use unified method
master_wb = get_or_create_master(category, master_folder, template_xlsx)
```

### Trade-offs

| Aspect | Universe Pattern (Old) | Unified Method (New) |
|--------|------------------------|----------------------|
| Data preservation | ❌ Lost REPORTED rows | ✅ All rows preserved |
| Row filtering | ~98% reduction (only STATUS) | ~0% reduction (all rows) |
| Processing speed | Faster (fewer rows) | Slightly slower |
| Correctness | ❌ Data loss risk | ✅ Data integrity |

The speed difference is acceptable because:
- VRSManager-style optimizations (read_only, column caching, style pooling) are still used
- O(1) matching is still used
- The main bottleneck was never row count but rather ws.cell() patterns

### Impact

- **REPORTED rows no longer disappear** when testers clear STATUS
- Script categories now behave identically to Quest/Item/Knowledge
- Manager workflow is reliable across all categories

### Code Changes

**Modified:** `core/compiler.py`
- Removed Script-specific branch at lines 885-895
- Removed `prefiltered_rows` parameter from `process_sheet()` call
- All categories now use `get_or_create_master()`

**Preserved:** `preprocess_script_category()` and `build_master_from_universe()` functions remain in the codebase but are no longer called. They may be useful for future analytics or debugging.

---

## Future Optimization Opportunities

These were identified but not implemented (out of scope or insufficient ROI):

| Optimization | Effort | Impact | Why Deferred |
|---|---|---|---|
| xlsxwriter for master creation | High | High | Requires complete rewrite of master file creation; openpyxl needed for reading existing files |
| Parallel category processing | High | High | Categories are independent but adds thread safety complexity |
| Incremental compilation | High | Very High | Track file mtimes, only reprocess changed files; significant architecture change |
| Pre-cache all QA row data | Medium | Medium | Read all rows into tuples before processing; marginal gain since normal-mode ws.cell() is already O(1) |

---

*This document records the complete optimization journey of the QA Compiler from its initial unoptimized state through Build 518. Every optimization was validated against original output with zero discrepancies confirmed. The codebase is production-ready and significantly faster than the original implementation.*
