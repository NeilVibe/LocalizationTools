# QACompiler Script Performance Optimization - Starting Document

## Date: 2026-02-03

## Status: INVESTIGATION PHASE (Pre-Code)

---

## 1. Problem Statement

QACompiler's **Master File Building** for the **Script** category (Sequencer + Dialog) is too slow when dealing with thousands of rows.

### The Scale Problem

Script files (Sequencer and Dialog) are fundamentally different from other QA categories (Quest, Knowledge, Item, etc.). While a typical Quest file might have 200-500 rows, Script files routinely contain **10,000+ rows** because they represent every event/dialog line in the game. Testers review only a fraction of these rows, but the raw files contain all of them.

### Current Optimization Already in Place

The codebase already has a preprocessing step (`preprocess_script_category()` in `compiler.py:730`) that:

1. Scans all QA files for the Script category
2. Collects only rows that have a STATUS value (i.e., rows a tester actually reviewed)
3. Builds a "universe" of checked rows, keyed by `(EventName, Text)`
4. Creates a filtered template workbook (`create_filtered_script_template()` at `compiler.py:916`) containing only those rows

This preprocessing reduces the row count by roughly 99% (from 10,000+ rows down to maybe 50-200 rows that testers actually marked).

### Why It Is Still Slow

Despite the 99% row reduction, the build process is still unacceptably slow. The suspected bottlenecks are:

1. **Cell-by-cell styling operations** -- Every cell gets individual Font, PatternFill, Alignment, and Border objects created and applied
2. **Excel I/O with openpyxl** -- Loading and saving large workbooks, even filtered ones, involves significant overhead
3. **Row matching overhead** -- Content-based matching requires building indexes and performing lookups per row
4. **Style object creation** -- Creating new `Font()`, `PatternFill()`, `Border()` objects for every cell instead of reusing shared style objects
5. **Redundant column lookups** -- `find_column_by_header()` iterates all columns for every call, and gets called multiple times per row
6. **Source workbook caching** -- The filtered template creation opens and caches source workbooks but still does cell-by-cell reads
7. **Debug logging overhead** -- Extensive `_script_debug_log()` calls accumulating string buffers in memory

---

## 2. Architecture Context

### How Master File Building Works (Script Category)

The full pipeline for building a Script master file:

```
Step 1: Discovery
  discover_qa_folders() -> finds all tester QA folders
  group_folders_by_language() -> splits into EN/CN groups

Step 2: Category Clustering
  Sequencer + Dialog -> both map to "Script" master file
  (CATEGORY_TO_MASTER: Sequencer -> Script, Dialog -> Script)

Step 3: Preprocessing (Script-specific optimization)
  preprocess_script_category(qa_folders) -> scans ALL QA files
    For each file:
      safe_load_workbook(xlsx_path)          # Full workbook load
      For each sheet:
        find_column_by_header(ws, "STATUS")  # Linear scan of headers
        find_column_by_header(ws, "Text")    # Linear scan of headers
        find_column_by_header(ws, "EventName") # Linear scan of headers
        For each row:
          Read STATUS, EventName, Text
          If STATUS non-empty -> add to universe dict

Step 4: Filtered Template Creation
  create_filtered_script_template(template_path, universe)
    Load template workbook
    Create new workbook
    For each sheet in template:
      Copy header row (cell by cell with style copying)
      Build template_rows index {(eventname, text): row}
      For each universe row in this sheet:
        Copy entire row from template (cell by cell)
        Apply styles per cell (Font, Fill, Alignment, Border)
        If row not in template, fetch from source workbook

Step 5: Master File Generation
  get_or_create_master(category, master_folder, template_file)
    If rebuild mode: delete old master, create from filtered template
    Cleans template (removes STATUS/COMMENT/SCREENSHOT/STRINGID cols)

Step 6: Per-Tester Processing
  For each tester's QA folder:
    safe_load_workbook(qa_xlsx)              # Another full workbook load
    For each sheet:
      process_sheet(master_ws, qa_ws, username, category, ...)
        build_master_index(master_ws, category)  # Iterates all master rows
        For each QA row (pre-filtered by STATUS):
          extract_qa_row_data(qa_ws, row, category)
            find_column_by_header(qa_ws, "STRINGID")  # Per-row header scan!
            find_column_by_header(qa_ws, "EventName")  # Per-row header scan!
          find_matching_row_in_master(qa_row_data, master_index, category)
          Write COMMENT to master (with styling)
          Write TESTER_STATUS to master (with styling)
          Restore manager status (with styling)
    Save master workbook

Step 7: Post-Processing
  hide_empty_comment_rows()
  autofit_rows_with_wordwrap()
  sort_worksheet_az() (for Item category only)
```

### Key Files and Their Roles

| File | Role | Lines (approx) |
|------|------|----------------|
| `core/compiler.py` | Orchestration, preprocessing, template creation | 1100+ |
| `core/processing.py` | Sheet processing, comment/status writing, styling | 600+ |
| `core/matching.py` | Index building, content-based row matching | 580+ |
| `core/excel_ops.py` | Workbook load/save, column operations, image copy | 480+ |
| `config.py` | Categories, column mappings, paths | 200+ |

### Matching Strategy for Script Category

Script-type categories (Sequencer/Dialog) use a specific matching strategy:

- **Primary key**: `(Translation_Text, EventName)` -- both must match
- **Fallback key**: `EventName` only -- when text changes but event is same
- **Index structure**: `build_master_index()` creates O(1) lookup dict
- **Consumed set**: Tracks which master rows have been matched (prevents duplicates)

---

## 3. Requirements

### Absolute Requirements (Non-Negotiable)

1. **Backward Compatible** -- The optimized code must produce the exact same output files. Same columns, same data, same styling, same behavior. No user-visible changes.

2. **Only Master File Building** -- The optimization scope is strictly limited to the Build Master Files workflow. The following must NOT be touched:
   - Transfer workflow (`core/transfer.py`)
   - Datasheet Generation (`generators/*.py`)
   - Tracker logic (only performance of master building, not tracker update logic itself)

3. **Preserve All Data Integrity**:
   - STATUS values (ISSUE, NO ISSUE, NON-ISSUE, BLOCKED, KOREAN)
   - COMMENT data with full formatting (text + stringid + timestamp)
   - SCREENSHOT references and image copying
   - Manager status (FIXED, REPORTED, CHECKING, NON-ISSUE) preservation across rebuilds
   - Manager comment preservation
   - Category clustering (Sequencer + Dialog -> Script master file)

4. **Dramatically Faster** -- Not a 10-20% improvement. The goal is a **drastic** speedup (e.g., from minutes to seconds for 10,000+ row files).

### Nice-to-Have

- Memory usage reduction
- Progress reporting during long operations
- Reduced disk I/O (fewer temp file creations)

---

## 4. Investigation Plan (12 Agents)

### Wave 1: Exploration (8 agents, parallel)

| Agent | Task | Target |
|-------|------|--------|
| **1** | Starting Document | This document (you are reading it) |
| **2** | QACompiler Script Flow | Deep dive into `compiler.py` Script processing pipeline: `preprocess_script_category()`, `create_filtered_script_template()`, the full orchestration flow for Script category |
| **3** | QACompiler Processing | Deep dive into `processing.py` Script sheet handling: `process_sheet()`, styling operations, column creation, comment formatting |
| **4** | QACompiler Matching | Deep dive into `matching.py` Script-specific matching logic: `build_master_index()`, `find_matching_row_in_master()`, `extract_qa_row_data()` for Script type |
| **5** | QACompiler Excel Ops | Deep dive into `excel_ops.py` styling and bottlenecks: `safe_load_workbook()`, `get_or_create_master()`, `find_column_by_header()`, style helpers |
| **6** | QACompiler Preprocessing | Deep dive into Script preprocessing optimization: how the universe is built, filtered template creation, cell-by-cell copying overhead |
| **7** | VRSManager Structure | Find and explore VRSManager project (or LanguageDataExporter which handles VRS ordering), understand Excel handling patterns |
| **8** | VRSManager Performance | Deep dive into fast Excel processing patterns: xlsxwriter usage, batch operations, style reuse |

### Wave 2: Synthesis (4 agents, after Wave 1)

| Agent | Task | Target |
|-------|------|--------|
| **9** | Memory Documents | Create knowledge documents from all findings, consolidate bottleneck analysis |
| **10** | Test File Creator | Create 10,000 row Script test Excel file for benchmarking |
| **11** | Code Review | Review bottleneck code with specific optimization recommendations |
| **12** | Master Plan | Synthesize everything into actionable, prioritized optimization plan |

---

## 5. Expected Deliverables

1. **This starting document** (committed before any code changes)
2. **Memory documents** with all findings from Wave 1 agents
3. **Test Excel file** (10,000 rows) for Script benchmarking with realistic data
4. **Bottleneck analysis** with profiling data or estimates
5. **Master optimization plan** with prioritized actions
6. **Git commit of preparation phase** (stable revision checkpoint before any code changes)

---

## 6. Key Areas to Investigate

### 6.1 openpyxl Performance

**Question**: Is cell-by-cell writing the primary bottleneck?

**What to look for**:
- In `create_filtered_script_template()` (compiler.py:916): The function copies rows cell-by-cell, creating new Font/PatternFill/Alignment objects for every single cell
- In `process_sheet()` (processing.py:333): Every comment cell gets individual style objects created
- In `get_or_create_master()` (excel_ops.py:178): Template copying does cell-by-cell iteration with `copy()` calls on every style property

**Known openpyxl performance patterns**:
- Creating style objects (Font, PatternFill, Border) is expensive
- Shared styles (reusing the same object) are dramatically faster
- `write_only` mode exists for write-heavy workloads but has limitations

### 6.2 Row Matching Complexity

**Question**: Is content-based matching efficient, or are there hidden O(n^2) patterns?

**What to look for**:
- `build_master_index()` (matching.py:241) builds an O(1) lookup dict -- this is already optimized
- BUT `extract_qa_row_data()` (matching.py:162) calls `find_column_by_header()` for EVERY row, which is an O(columns) scan
- The "consumed" set prevents duplicate matches -- verify this works correctly with large datasets
- The legacy `find_matching_row_for_transfer()` uses O(n) linear scan -- verify Script path does not use this

### 6.3 Sheet Iteration Patterns

**Question**: How are source sheets being read?

**What to look for**:
- `safe_load_workbook()` loads the entire workbook into memory, including all sheets
- For Script files with 10,000+ rows and many columns, this is a significant memory allocation
- Consider: Can we use `read_only=True` mode for source files we only read from?
- Consider: Can we use `data_only=True` to skip formula evaluation?

### 6.4 Styling Operations

**Question**: Are styles being applied efficiently?

**What to look for**:
- `process_sheet()` creates new Font/PatternFill/Border/Alignment objects per cell
- These objects are immutable in openpyxl -- creating identical ones is wasteful
- Pattern: Create style objects ONCE, reuse for all cells of the same type
- The `_safe_get_color_rgb()` helper suggests color handling is already a known pain point
- `style_header_cell()` and `THIN_BORDER` in excel_ops.py show some style reuse, but it is incomplete

### 6.5 Memory Usage

**Question**: Are entire workbooks loaded when only partial data is needed?

**What to look for**:
- `preprocess_script_category()` loads every QA file fully to scan for STATUS values
- `collect_manager_status()` loads every master file fully to read manager STATUS columns
- `collect_fixed_screenshots()` loads every master file fully to check FIXED status
- For a rebuild, all three of these run, potentially loading the same files multiple times

### 6.6 VRSManager / LanguageDataExporter Patterns

**Question**: What techniques does the LanguageDataExporter use for fast Excel I/O?

**What to look for**:
- The LanguageDataExporter uses **xlsxwriter** (not openpyxl) for writing
- xlsxwriter is write-only and significantly faster for generating new files
- It supports batch format application
- Column widths are set declaratively
- No need to load existing workbook -- writes from scratch
- The `VRSOrderer` handles large datasets (voice recording sheets can be huge)

**Key insight**: QACompiler uses openpyxl for both reading AND writing. If we can separate concerns (openpyxl for reading existing files, xlsxwriter for writing new masters), we might get a massive speedup.

---

## 7. Suspected Bottleneck Ranking (Hypothesis)

Based on code review, ranked from most likely to least likely:

| Rank | Bottleneck | Location | Estimated Impact |
|------|-----------|----------|-----------------|
| 1 | Cell-by-cell style creation | `create_filtered_script_template()`, `process_sheet()` | HIGH -- new Font/Fill/Border per cell |
| 2 | Redundant `find_column_by_header()` calls | `extract_qa_row_data()` in matching.py | HIGH -- O(cols) per row, called per row |
| 3 | Full workbook loads for read-only operations | `preprocess_script_category()`, `collect_manager_status()` | MEDIUM -- openpyxl default mode loads styles |
| 4 | Multiple passes over same files | Preprocess + Manager Status + Build | MEDIUM -- same files loaded 2-3 times |
| 5 | Debug logging string accumulation | `_script_debug_log()` everywhere | LOW-MEDIUM -- string concat in hot loops |
| 6 | Source workbook cache in template creation | `get_source_row_data()` in compiler.py | LOW -- cache helps but cell reads are slow |
| 7 | `copy()` calls on style objects | `get_or_create_master()` template copying | LOW -- only happens once per master |

---

## 8. Constraints

### Must NOT Change

- Transfer workflow (`core/transfer.py`) -- untouched
- Datasheet Generation (`generators/*.py`) -- untouched
- Tracker logic (update logic in `tracker/`) -- untouched (only master building performance)
- GUI (`gui/app.py`) -- untouched
- Config (`config.py`) -- untouched unless adding new performance config
- Tests (`tests/`) -- all existing tests must pass unchanged

### Must Preserve Exactly

- All STATUS data (ISSUE, NO ISSUE, NON-ISSUE, BLOCKED, KOREAN)
- All COMMENT data with formatting (text + stringid separator + timestamp)
- All SCREENSHOT references
- All Manager STATUS (FIXED, REPORTED, CHECKING, NON-ISSUE) across rebuilds
- All Manager COMMENT data across rebuilds
- Image copying behavior (including FIXED skip optimization)
- Category clustering: Sequencer + Dialog -> Master_Script.xlsx
- Column ordering in master files
- Sheet names in master files
- Row ordering within sheets

---

## 9. Success Criteria

| Criterion | Metric |
|-----------|--------|
| **Speed** | Master file building for Script category with 10,000+ rows completes in seconds, not minutes |
| **Correctness** | All existing test scenarios pass unchanged |
| **Output fidelity** | Output files are functionally identical to current output (same data, same styling, same structure) |
| **No regressions** | Non-Script categories (Quest, Knowledge, Item, etc.) are unaffected |
| **Backward compatible** | Drop-in replacement -- no changes to calling code or configuration |

---

## 10. Reference: Current File Structure

```
QACompilerNEW/
  core/
    compiler.py       # Orchestration, preprocessing, template creation
    processing.py     # Sheet processing, comment/status writing
    matching.py       # Content-based row matching, index building
    excel_ops.py      # Workbook operations, styling, image copy
    discovery.py      # QA folder discovery
    transfer.py       # Transfer workflow (DO NOT TOUCH)
    populate_new.py   # New file population
    tracker_update.py # Tracker update logic
  generators/         # Datasheet generation (DO NOT TOUCH)
  tracker/            # Tracker data/coverage (DO NOT TOUCH logic)
  gui/                # GUI (DO NOT TOUCH)
  tests/
    test_script_preprocessing.py  # Script preprocessing tests
    test_script_collection.py     # Script collection tests
    test_manager_stats.py         # Manager stats tests
    test_user_scenario.py         # User scenario tests
    create_mock_fixture.py        # Test fixture creator
  config.py           # Central configuration
  main.py             # Entry point
  docs/               # Documentation (this file lives here)
```

---

## 11. Reference: Key Functions to Profile

When benchmarking, these are the functions to time individually:

```python
# Preprocessing phase
preprocess_script_category()          # compiler.py:730
create_filtered_script_template()     # compiler.py:916

# Master creation phase
get_or_create_master()                # excel_ops.py:178
safe_load_workbook()                  # excel_ops.py:75

# Per-tester processing phase
process_sheet()                       # processing.py:333
  build_master_index()                # matching.py:241
  extract_qa_row_data()               # matching.py:162
  find_matching_row_in_master()       # matching.py:365
  find_column_by_header()             # excel_ops.py:131

# Post-processing phase
hide_empty_comment_rows()             # processing.py
autofit_rows_with_wordwrap()          # processing.py

# Pre-build collection phase
collect_manager_status()              # compiler.py:221
collect_fixed_screenshots()           # compiler.py:141
collect_manager_stats_for_tracker()   # compiler.py:427
```

---

## 12. Reference: LanguageDataExporter as Performance Reference

The LanguageDataExporter project (`NewScripts/LanguageDataExporter/`) handles large Excel files efficiently using:

- **xlsxwriter** for writing (not openpyxl)
- **Batch format creation** -- formats defined once, applied to ranges
- **No style copying** -- writes fresh with predefined formats
- **VRS ordering** -- handles large Voice Recording Sheet data for sorting

This project is the closest reference for "fast Excel handling" patterns in the codebase and should be studied for applicable techniques.

---

*This document was created as the starting point for a 12-agent investigation into QACompiler Script performance optimization. No code changes have been made. This is a read-only analysis checkpoint.*
