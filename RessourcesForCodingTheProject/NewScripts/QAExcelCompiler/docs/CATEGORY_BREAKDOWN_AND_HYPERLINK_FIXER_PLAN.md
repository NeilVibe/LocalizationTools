# Feature Plan: Category Breakdown Table + Hyperlink Auto-Fixer

**Date:** 2026-01-13
**Status:** PLANNED
**Target File:** `compile_qa.py`

---

## Overview

Two new features for QAExcelCompiler:

1. **Category Breakdown Table** - Show per-category completion % for each tester in the TOTAL tab
2. **Hyperlink Auto-Fixer** - Automatically fix missing hyperlinks in SCREENSHOT column during compile

---

## Feature 1: Category Breakdown Table

### Problem

Currently, the TOTAL tab aggregates all category data into a single row per user. Managers cannot see:
- Which categories each tester has been working on
- The completion percentage per category
- Category-level progress tracking

### Solution

Add a **4th table** in the TOTAL tab showing a pivot-style breakdown:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CATEGORY BREAKDOWN                                                          │
├──────────┬────────┬───────────┬────────┬────────┬────────┬───────┬─────────┤
│ User     │ Quest  │ Knowledge │ Item   │ Region │ System │ Char  │ Total   │
├──────────┼────────┼───────────┼────────┼────────┼────────┼───────┼─────────┤
│ John     │ 85.0%  │ 90.5%     │ -      │ -      │ -      │ -     │ 87.2%   │
│ Eric     │ 72.3%  │ -         │ -      │ -      │ -      │ -     │ 72.3%   │
│ Lisa     │ -      │ -         │ -      │ 75.2%  │ -      │ -     │ 75.2%   │
│ Mike     │ -      │ -         │ -      │ 68.9%  │ -      │ -     │ 68.9%   │
│ Doni     │ -      │ 82.1%     │ -      │ -      │ -      │ -     │ 82.1%   │
│ Jojo     │ -      │ -         │ -      │ -      │ -      │ 91.0% │ 91.0%   │
├──────────┼────────┼───────────┼────────┼────────┼────────┼───────┼─────────┤
│ TOTAL    │ 78.6%  │ 86.3%     │ -      │ 72.0%  │ -      │ 91.0% │ 81.4%   │
└──────────┴────────┴───────────┴────────┴────────┴────────┴───────┴─────────┘
```

### Data Source

The data already exists in `_DAILY_DATA` sheet:
```
Schema: Date | User | Category | TotalRows | Done | Issues | NoIssue | Blocked | ...
```

Currently, `build_total_sheet()` aggregates this by user (summing across categories). We will:
1. Keep the existing per-user aggregation (tables 1-3)
2. Add a new section using the per-category data from `latest_data[(user, category)]`

### TOTAL Tab Structure (After Change)

```
Row 1-N:    EN TESTER STATS table (existing)
            - Title row
            - Header row
            - Data rows (1 per EN user)
            - SUBTOTAL row

Row N+2:    CN TESTER STATS table (existing)
            - Title row
            - Header row
            - Data rows (1 per CN user)
            - SUBTOTAL row

Row N+4:    GRAND TOTAL row (existing)

Row N+6:    CATEGORY BREAKDOWN table (NEW)
            - Title row
            - Header row (User | Quest | Knowledge | Item | Region | System | Character | Total)
            - Data rows (1 per user, all users combined)
            - TOTAL row (category totals)

Row N+X:    Charts (existing, repositioned)
```

### Implementation Details

#### Location in Code
- Function: `build_total_sheet()` (line ~2191)
- Add new section after GRAND TOTAL, before charts

#### Logic
```python
def build_category_breakdown_section(ws, start_row, latest_data, all_users):
    """
    Build Category Breakdown pivot table.

    Args:
        ws: Worksheet
        start_row: Row to start building
        latest_data: Dict of (user, category) -> {done, total_rows, ...}
        all_users: List of all usernames

    Returns:
        next_row: Row after this section
    """
    CATEGORIES = ["Quest", "Knowledge", "Item", "Region", "System", "Character"]

    # Build pivot: user -> {category -> completion %}
    pivot = {}
    for (user, category), data in latest_data.items():
        if user not in pivot:
            pivot[user] = {}
        total_rows = data["total_rows"]
        done = data["done"]
        pct = round(done / total_rows * 100, 1) if total_rows > 0 else 0
        pivot[user][category] = pct

    # Write table...
```

#### Styling
- Title: Dark purple fill (#5B2C6F), white bold text
- Headers: Light gray fill, bold
- Data cells: Center aligned, percentage format
- "-" for categories not worked on (empty/no data)
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

### Category Breakdown Table
1. Run compile with existing test data
2. Verify TOTAL tab has 4 tables
3. Check percentages match manual calculation
4. Verify "-" shows for unused categories
5. Check TOTAL row sums correctly

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
| `compile_qa.py` | Add `build_category_breakdown_section()`, modify `build_total_sheet()`, add `find_file_in_folder()`, modify `process_sheet()`, modify `transfer_sheet_data()` |

---

## Rollback Plan

Both features are additive:
- Category Breakdown: New section, doesn't modify existing tables
- Hyperlink Fixer: Only adds hyperlinks, never removes

If issues arise, simply remove the new code sections.

---

## Timeline

1. **Phase 1**: Documentation (this file) - DONE
2. **Phase 2**: Implement Category Breakdown table
3. **Phase 3**: Implement Hyperlink Auto-Fixer
4. **Phase 4**: Test with real data
5. **Phase 5**: Commit final version
