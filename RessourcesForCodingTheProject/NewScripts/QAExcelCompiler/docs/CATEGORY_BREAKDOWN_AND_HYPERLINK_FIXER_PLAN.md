# Feature Plan: Category Breakdown Table + Hyperlink Auto-Fixer + Ranking Table

**Date:** 2026-01-13
**Updated:** 2026-01-13 (v3 - Implementation complete)
**Status:** ✅ IMPLEMENTED
**Target File:** `compile_qa.py`

---

## Overview

Three features implemented for QAExcelCompiler:

1. **Category Breakdown Tables** - Show per-category completion % AND translated word/character count for each tester in the TOTAL tab (separate EN and CN tables)
2. **Hyperlink Auto-Fixer** - Automatically fix missing hyperlinks in SCREENSHOT column during compile
3. **Ranking Table** - Weighted scoring (70% Completion + 30% Actual Issues) with Gold/Silver/Bronze styling

**Additional Changes:**
- Charts removed from both DAILY and TOTAL tabs (too confusing)
- Word/character counts only include DONE rows (rows with STATUS filled)

---

## Feature 1: Category Breakdown Tables

### Problem

Currently, the TOTAL tab aggregates all category data into a single row per user. Managers cannot see:
- Which categories each tester has been working on
- The completion percentage per category
- **The translated word/character count per category**
- Category-level progress tracking

### Solution

Add **TWO new tables** (4th and 5th) in the TOTAL tab:

1. **EN CATEGORY BREAKDOWN** - For English testers (shows WORD count)
2. **CN CATEGORY BREAKDOWN** - For Chinese testers (shows CHARACTER count)

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ EN CATEGORY BREAKDOWN                                                                         │
├──────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┬───────────┤
│ User     │ Quest           │ Knowledge       │ Item            │ Region          │ Total     │
│          │ Done% │ Words   │ Done% │ Words   │ Done% │ Words   │ Done% │ Words   │ Words     │
├──────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────────┤
│ John     │ 85.0% │ 12,450  │ 90.5% │ 8,320   │ -     │ -       │ -     │ -       │ 20,770    │
│ Eric     │ 72.3% │ 9,100   │ -     │ -       │ -     │ -       │ -     │ -       │ 9,100     │
├──────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────────┤
│ TOTAL    │ 78.6% │ 21,550  │ 90.5% │ 8,320   │ -     │ -       │ -     │ -       │ 29,870    │
└──────────┴───────┴─────────┴───────┴─────────┴───────┴─────────┴───────┴─────────┴───────────┘

┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ CN CATEGORY BREAKDOWN                                                                         │
├──────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┬───────────┤
│ User     │ Quest           │ Knowledge       │ Item            │ Region          │ Total     │
│          │ Done% │ Chars   │ Done% │ Chars   │ Done% │ Chars   │ Done% │ Chars   │ Chars     │
├──────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────────┤
│ Lisa     │ -     │ -       │ -     │ -       │ -     │ -       │ 75.2% │ 45,200  │ 45,200    │
│ Mike     │ -     │ -       │ -     │ -       │ -     │ -       │ 68.9% │ 38,100  │ 38,100    │
├──────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────┼─────────┼───────────┤
│ TOTAL    │ -     │ -       │ -     │ -       │ -     │ -       │ 72.0% │ 83,300  │ 83,300    │
└──────────┴───────┴─────────┴───────┴─────────┴───────┴─────────┴───────┴─────────┴───────────┘
```

### Word/Character Count Logic

#### Translation Column Detection
Use existing `TRANSLATION_COLS` mapping:
```python
TRANSLATION_COLS = {
    "Quest": {"eng": 2, "other": 3},
    "Knowledge": {"eng": 2, "other": 3},
    "Character": {"eng": 2, "other": 3},
    "Region": {"eng": 2, "other": 3},
    "Item": {"eng": 5, "other": 7},
    "System": {"eng": 1, "other": 1},
}
```

#### Korean Detection & Filtering
**IMPORTANT:** Cells containing Korean text must be EXCLUDED from word/character count.

Korean Unicode detection (simple and reliable):
```python
def contains_korean(text):
    """Check if text contains Korean characters (Hangul)."""
    if not text:
        return False
    for char in str(text):
        # Hangul Syllables: U+AC00 to U+D7AF (most common)
        # Hangul Jamo: U+1100 to U+11FF
        # Hangul Compatibility Jamo: U+3130 to U+318F
        if '\uAC00' <= char <= '\uD7AF':
            return True
        if '\u1100' <= char <= '\u11FF':
            return True
        if '\u3130' <= char <= '\u318F':
            return True
    return False
```

#### Counting Methods
```python
def count_words_english(text):
    """Count words in English text (split by whitespace)."""
    if not text or contains_korean(text):
        return 0
    return len(str(text).split())

def count_chars_chinese(text):
    """Count characters in Chinese text (excluding whitespace)."""
    if not text or contains_korean(text):
        return 0
    # Remove whitespace, count remaining characters
    return len(str(text).replace(" ", "").replace("\n", "").replace("\t", ""))
```

#### Language Detection per Tester
Use `languageTOtester_list.txt`:
```
ENG
김동헌
황하연
...

ZHO-CN
김춘애
최문석
...
```

Parse to determine: `tester_name -> "EN"` or `"CN"`

### Data Collection

Word/character counts must be collected **during compile** (when reading Master files), not from `_DAILY_DATA`.

New data structure needed:
```python
# Collected during process_category() when reading Master files
category_wordcount = {
    (user, category): {
        "word_count": 12450,  # For EN testers
        "char_count": 0,      # For CN testers (mutually exclusive)
    }
}
```

**Where to collect:**
- In `process_category()` after processing each user's folder
- Read the Master file's translation column
- Sum word/char counts (excluding Korean cells)
- Store in new data structure

### TOTAL Tab Structure (Final)

```
Row 1-N:    EN TESTER STATS table
            - Title row
            - Header row
            - Data rows (1 per EN user)
            - SUBTOTAL row

Row N+2:    CN TESTER STATS table
            - Title row
            - Header row
            - Data rows (1 per CN user)
            - SUBTOTAL row

Row N+4:    GRAND TOTAL row

Row N+6:    EN CATEGORY BREAKDOWN table
            - Title row (blue)
            - Header row (User | Quest Done%/Words | Knowledge Done%/Words | ... | Total Words)
            - Data rows (1 per EN user)
            - TOTAL row

Row N+X:    CN CATEGORY BREAKDOWN table
            - Title row (red)
            - Header row (User | Quest Done%/Chars | Knowledge Done%/Chars | ... | Total Chars)
            - Data rows (1 per CN user)
            - TOTAL row

Row N+Y:    RANKING TABLE
            - Title row (gold gradient)
            - Header row (Rank | User | Lang | Completion% | Actual Issues% | Score)
            - Data rows (sorted by score)
            - Top 3 highlighted: Gold (#FFD700), Silver (#C0C0C0), Bronze (#CD7F32)

(Charts REMOVED - too confusing for stakeholders)
```

### Implementation Details

#### New Helper Functions
```python
def contains_korean(text):
    """Check if text contains Korean characters."""
    ...

def count_translated_content(ws, trans_col, is_english):
    """
    Count words (EN) or characters (CN) in translation column.
    Excludes cells containing Korean.

    Args:
        ws: Worksheet
        trans_col: Translation column index
        is_english: True for word count, False for character count

    Returns:
        int: Total word count (EN) or character count (CN)
    """
    total = 0
    for row in range(2, ws.max_row + 1):
        cell_value = ws.cell(row, trans_col).value
        if not cell_value or contains_korean(cell_value):
            continue
        if is_english:
            total += len(str(cell_value).split())
        else:
            total += len(str(cell_value).replace(" ", "").replace("\n", ""))
    return total
```

#### New Data Collection in process_category()
```python
# After processing user's sheets, collect word/char count
def process_category(category, qa_folders, master_folder, ...):
    ...
    # NEW: Collect word/char counts per user
    wordcount_data = {}
    for qf in qa_folders:
        username = qf["username"]
        is_english = tester_mapping.get(username, "EN") == "EN"
        trans_col = get_translation_column(category, is_english)

        # Read master file and count
        master_path = master_folder / f"Master_{category}.xlsx"
        # Count from user's translation column in master...
        count = count_translated_content(master_ws, trans_col, is_english)
        wordcount_data[(username, category)] = count

    return daily_entries, wordcount_data  # Modified return
```

#### New Section Builder
```python
def build_category_breakdown_section(ws, start_row, latest_data, wordcount_data, users, is_english, tester_mapping):
    """
    Build EN or CN Category Breakdown pivot table.

    Args:
        ws: Worksheet
        start_row: Row to start building
        latest_data: Dict of (user, category) -> {done, total_rows, ...}
        wordcount_data: Dict of (user, category) -> word/char count
        users: List of usernames for this section
        is_english: True for EN (words), False for CN (chars)
        tester_mapping: Dict of username -> language

    Returns:
        next_row: Row after this section
    """
    ...
```

#### Styling
- EN Title: Blue fill (#4472C4), white bold text
- CN Title: Red fill (#C00000), white bold text
- Headers: Light gray fill, bold
- Data cells: Center aligned
- Percentage format for Done%
- Number format with thousands separator for word/char counts
- "-" for categories not worked on
- TOTAL row: Yellow fill, bold

---

## Feature 2: Hyperlink Auto-Fixer

### Problem

Testers sometimes enter screenshot filenames in the SCREENSHOT column without creating hyperlinks. This happens when:
- Copy-pasting filename text instead of inserting hyperlink
- Excel quirks removing hyperlinks
- Manual typing of filename

Result: SCREENSHOT column shows filename text but clicking does nothing.

### Solution

During compile (and OLD→NEW transfer), automatically detect and fix missing hyperlinks:

1. Read SCREENSHOT cell
2. If cell has value (filename) but NO hyperlink attached
3. Search for that file in `QAfolder/{Username}_{Category}/`
4. If found, create hyperlink to the file
5. Log fixed/missing counts

### Current State

- `fix_hyperlinks_gui.py` exists as standalone GUI tool
- Logic exists but NOT integrated into main compile process
- `process_sheet()` assumes hyperlinks already exist and only transforms them

### Implementation Details

#### Location 1: `process_sheet()` (line ~946)

Add hyperlink auto-fix when reading QA file:

```python
# Around line 1087-1137 (SCREENSHOT handling)
qa_screenshot_cell = qa_ws.cell(match_row, qa_screenshot_col)
screenshot_value = qa_screenshot_cell.value
screenshot_hyperlink = qa_screenshot_cell.hyperlink

# NEW: Auto-fix missing hyperlink
if screenshot_value and not screenshot_hyperlink:
    # Search for file in QA folder
    filename = str(screenshot_value).strip()
    actual_file = find_file_in_folder(filename, qa_folder_path)
    if actual_file:
        # Create hyperlink (relative path)
        qa_screenshot_cell.hyperlink = actual_file
        screenshot_hyperlink = qa_screenshot_cell.hyperlink
        # Log: fixed hyperlink
```

#### Location 2: `transfer_sheet_data()` (line ~2759)

Add same logic during OLD→NEW transfer:

```python
# Around line 2808
old_screenshot_cell = old_ws.cell(row, old_screenshot_col)
old_screenshot_value = old_screenshot_cell.value
old_screenshot_hyperlink = old_screenshot_cell.hyperlink

# NEW: Auto-fix missing hyperlink before transfer
if old_screenshot_value and not old_screenshot_hyperlink:
    filename = str(old_screenshot_value).strip()
    actual_file = find_file_in_folder(filename, old_folder_path)
    if actual_file:
        old_screenshot_cell.hyperlink = actual_file
        old_screenshot_hyperlink = old_screenshot_cell.hyperlink
```

#### Helper Function

Reuse from `fix_hyperlinks_gui.py`:

```python
def find_file_in_folder(filename, folder):
    """Search for file in folder (case-insensitive)."""
    if not folder or not folder.exists():
        return None
    filename_lower = filename.lower()
    for f in os.listdir(folder):
        if f.lower() == filename_lower:
            return f
    return None
```

#### Logging

Add counters to track:
- `hyperlinks_fixed`: Count of auto-fixed hyperlinks
- `hyperlinks_missing`: Count of filenames where file not found

Print summary:
```
Processing: Quest [EN] (2 folders)
  John: 45/50 rows matched, 3 hyperlinks auto-fixed
  Eric: 38/42 rows matched, 1 hyperlink auto-fixed, 1 file missing
```

---

## Testing Plan

### Category Breakdown Tables
1. Run compile with existing test data
2. Verify TOTAL tab has **5 tables**:
   - EN TESTER STATS (existing)
   - CN TESTER STATS (existing)
   - GRAND TOTAL (existing)
   - EN CATEGORY BREAKDOWN (new)
   - CN CATEGORY BREAKDOWN (new)
3. Check Done% percentages match `_DAILY_DATA` values
4. Verify word counts for EN testers (manual spot-check)
5. Verify character counts for CN testers (manual spot-check)
6. Confirm Korean cells are excluded from counts
7. Verify "-" shows for unused categories
8. Check TOTAL row sums correctly

### Hyperlink Auto-Fixer
1. Create test file with:
   - Cell with hyperlink (should be unchanged)
   - Cell with filename text, no hyperlink, file EXISTS (should be fixed)
   - Cell with filename text, no hyperlink, file MISSING (should log warning)
2. Run compile
3. Verify hyperlinks created correctly
4. Check log output shows fix counts

---

## Files Modified

| File | Changes |
|------|---------|
| `compile_qa.py` | Add `contains_korean()`, `count_translated_content()`, `build_category_breakdown_section()`, modify `build_total_sheet()`, modify `process_category()`, add `find_file_in_folder()`, modify `process_sheet()`, modify `transfer_sheet_data()` |

---

## Summary of Changes

### TOTAL Tab Final Structure (7 Tables, No Charts)

```
┌─────────────────────────────────────────┐
│ 1. EN TESTER STATS                      │
│    - Columns: User, Done, Issues,       │
│      No Issue, Blocked, Korean          │
│      + Manager cols                     │
│    - SUBTOTAL row                       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 2. CN TESTER STATS                      │
│    - Same columns as EN                 │
│    - SUBTOTAL row                       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 3. GRAND TOTAL                          │
│    - Combined EN + CN totals            │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 4. EN CATEGORY BREAKDOWN                │
│    - Per-category Done% + Word count    │
│    - Blue title bar                     │
│    - Only counts DONE rows              │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 5. CN CATEGORY BREAKDOWN                │
│    - Per-category Done% + Char count    │
│    - Red title bar                      │
│    - Only counts DONE rows              │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 6. EN RANKING                           │
│    - Score = 70% Done + 30% ActualIssues│
│    - SCALAR values, not percentages     │
│    - Gold/Silver/Bronze top 3           │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ 7. CN RANKING                           │
│    - Same scoring as EN                 │
│    - Separate medals per language       │
└─────────────────────────────────────────┘

Notes:
- Charts REMOVED (too confusing)
- Completion% removed from stats tables (already in Category Breakdown)
- "Total" renamed to "Done" for consistency
- Ranking uses SCALAR values (Done count + Actual Issues count)
```

---

## Rollback Plan

Both features are additive:
- Category Breakdown: New sections, doesn't modify existing tables
- Hyperlink Fixer: Only adds hyperlinks, never removes

If issues arise, simply remove the new code sections.

---

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Documentation (this file) | ✅ DONE |
| 2 | Word/char counting helpers + Korean detection | ✅ DONE |
| 3 | Modify `process_category()` to collect word/char counts (DONE rows only) | ✅ DONE |
| 4 | Implement `build_category_breakdown_section()` for EN and CN | ✅ DONE |
| 5 | Modify `build_total_sheet()` to add both breakdown tables | ✅ DONE |
| 6 | Implement Hyperlink Auto-Fixer | ✅ DONE |
| 7 | Remove charts from DAILY and TOTAL tabs | ✅ DONE |
| 8 | Implement `build_ranking_table()` with weighted scoring | ✅ DONE |
| 9 | Test with real data | ✅ DONE |
| 10 | Segmented code review | ✅ DONE |
| 11 | Final commit | ✅ DONE |

**All phases complete. Feature fully implemented and tested.**
