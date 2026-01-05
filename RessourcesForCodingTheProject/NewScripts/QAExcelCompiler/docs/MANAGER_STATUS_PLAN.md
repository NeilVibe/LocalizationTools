# Manager Status Feature - Implementation Plan

## Overview

Add manager workflow to QA Excel Compiler:
1. **STATUS_{User}** columns in Master files for managers to mark FIXED/REPORTED
2. **Preprocess** existing Master files to collect manager statuses
3. **Preserve** manager statuses when re-compiling
4. **Aggregate** manager stats (Fixed/Reported) in Tracker alongside tester stats

---

## Current vs New Flow

### Current Flow
```
QAfolder/ ──────────────────────────────────────────→ Masterfolder/
           compile_qa.py                              ├── Master_*.xlsx
                                                      └── LQA_Tester_ProgressTracker.xlsx
```

### New Flow
```
Masterfolder/ (existing) ──→ PREPROCESS ──→ Collect manager STATUS
                                                    │
QAfolder/ ─────────────────→ COMPILE ───────────────┤
                                                    │
                                                    ▼
                                            Masterfolder/ (updated)
                                            ├── Master_*.xlsx (with STATUS preserved)
                                            └── LQA_Tester_ProgressTracker.xlsx
                                                ├── DAILY (Tester + Manager stats)
                                                ├── TOTAL (Tester + Manager stats)
                                                └── GRAPHS (includes Fixed/Reported)
```

---

## Master File Structure

### Current
```
| ... | COMMENT_John | SCREENSHOT_John | COMMENT_Alice | SCREENSHOT_Alice |
|-----|--------------|-----------------|---------------|------------------|
|     | "Bug here"   | img.png         | "Typo found"  | typo.png         |
```

### New (with Manager STATUS)
```
| ... | COMMENT_John | STATUS_John | SCREENSHOT_John | COMMENT_Alice | STATUS_Alice | SCREENSHOT_Alice |
|-----|--------------|-------------|-----------------|---------------|--------------|------------------|
|     | "Bug here"   | FIXED       | img.png         | "Typo found"  | REPORTED     | typo.png         |
|     | "Wrong text" |             |                 | "Missing"     | FIXED        |                  |
```

**Column order per user:** COMMENT_{User} → STATUS_{User} → SCREENSHOT_{User}

**Valid STATUS values:** FIXED, REPORTED, CHECKING, (empty)

---

## Manager Workflow

1. Compiler generates Master files with empty STATUS_{User} columns
2. Manager opens Master file in Excel
3. Manager reviews each COMMENT_{User}
4. Manager enters FIXED or REPORTED in STATUS_{User}
5. Manager saves file
6. Next compile run preserves these values

---

## Tracker Updates

### DAILY Tab (New Columns)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DAILY PROGRESS                                     │
├─────────┬─────────────────────────────┬─────────────────────────────────────────┤
│         │      Tester Stats           │              Manager Stats                        │
├─────────┼───────┬─────────┬───────────┼─────────┬──────────┬──────────┬────────────────────┤
│  Date   │ Done  │ Issues  │ Completion│  Fixed  │ Reported │ Checking │ Pending            │
├─────────┼───────┼─────────┼───────────┼─────────┼──────────┼──────────┼────────────────────┤
│  01/03  │  77   │   15    │   15.4%   │    8    │    4     │    1     │    2               │
│  01/04  │  55   │   10    │   26.4%   │    5    │    3     │    1     │    1               │
│  01/05  │  62   │   12    │   38.8%   │    6    │    4     │    1     │    1               │
├─────────┼───────┼─────────┼───────────┼─────────┼──────────┼──────────┼────────────────────┤
│  TOTAL  │  194  │   37    │   38.8%   │   19    │   11     │    3     │    4               │
└─────────┴───────┴─────────┴───────────┴─────────┴──────────┴──────────┴────────────────────┘
```

**New columns:**
- **Fixed**: Count of STATUS_{User} = "FIXED"
- **Reported**: Count of STATUS_{User} = "REPORTED"
- **Checking**: Count of STATUS_{User} = "CHECKING"
- **Pending**: Issues with no manager status (Issues - Fixed - Reported - Checking)

### TOTAL Tab (New Columns)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        TOTAL SUMMARY                                             │
├────────┬──────────────┬───────┬─────────┬──────────┬─────────┬────────┬──────────┬────────┬──────┤
│  User  │ Completion % │ Done  │ Issues  │ No Issue │ Blocked │ Fixed  │ Reported │Checking│Pending│
├────────┼──────────────┼───────┼─────────┼──────────┼─────────┼────────┼──────────┼────────┼──────┤
│  John  │    95.0%     │   97  │   21    │    68    │    8    │   14   │    4     │   2    │   1  │
│ Alice  │   100.0%     │   57  │    7    │    47    │    3    │    5   │    1     │   1    │   0  │
│  Bob   │    88.0%     │   60  │   13    │    42    │    5    │    7   │    3     │   2    │   1  │
├────────┼──────────────┼───────┼─────────┼──────────┼─────────┼────────┼──────────┼────────┼──────┤
│ TOTAL  │    94.3%     │  214  │   41    │   157    │   16    │   26   │    8     │   5    │   2  │
└────────┴──────────────┴───────┴─────────┴──────────┴─────────┴────────┴──────────┴────────┴──────┘
```

### GRAPHS Tab (New Chart)

Add third chart: **Issue Resolution Status**
- Stacked bar or pie chart
- Shows: Fixed vs Reported vs Pending
- Per user or total

---

## Data Storage

### _DAILY_DATA Sheet (Updated)

```
| Date       | User  | Category  | Done | Issues | NoIssue | Blocked | Fixed | Reported |
|------------|-------|-----------|------|--------|---------|---------|-------|----------|
| 2026-01-03 | John  | Quest     |  32  |   7    |   22    |    3    |   5   |    1     |
| 2026-01-03 | John  | Knowledge |  25  |   4    |   18    |    3    |   3   |    1     |
| 2026-01-04 | Alice | Quest     |  45  |   5    |   38    |    2    |   3   |    1     |
```

**New columns:** Fixed, Reported

---

## Implementation Phases

### Phase 1: Add STATUS_{User} Column Creation

**Modify:** `get_or_create_user_comment_column()` or create new function

```python
def get_or_create_user_status_column(ws, username, after_comment_col):
    """
    Find or create STATUS_{username} column after COMMENT_{username}.

    Args:
        ws: Worksheet
        username: User identifier
        after_comment_col: Column index of COMMENT_{username}

    Returns: Column index (1-based)
    """
    col_name = f"STATUS_{username}"

    # Check if exists
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header and str(header).strip() == col_name:
            return col

    # Create at max_column + 1 (will be inserted in correct position)
    new_col = ws.max_column + 1
    cell = ws.cell(row=1, column=new_col)
    cell.value = col_name

    # Styling: Light green for manager columns
    cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
    cell.font = Font(bold=True)
    cell.alignment = Alignment(horizontal='center', vertical='center')

    return new_col
```

**Update column order:** COMMENT → STATUS → SCREENSHOT per user

### Phase 2: Preprocess - Collect Manager Status

**New function:** `collect_manager_status()`

```python
def collect_manager_status():
    """
    Read existing Master files and collect all STATUS_{User} values.

    Returns: Dict structure
    {
        "Quest": {
            "Sheet1": {
                row_number: {
                    "John": "FIXED",
                    "Alice": "REPORTED"
                }
            }
        }
    }
    """
    manager_status = {}

    for category in CATEGORIES:
        master_path = MASTER_FOLDER / f"Master_{category}.xlsx"
        if not master_path.exists():
            continue

        wb = openpyxl.load_workbook(master_path)
        manager_status[category] = {}

        for sheet_name in wb.sheetnames:
            if sheet_name == "STATUS":
                continue

            ws = wb[sheet_name]
            manager_status[category][sheet_name] = {}

            # Find all STATUS_{User} columns
            status_cols = {}
            for col in range(1, ws.max_column + 1):
                header = ws.cell(row=1, column=col).value
                if header and str(header).startswith("STATUS_"):
                    username = str(header).replace("STATUS_", "")
                    status_cols[username] = col

            # Collect values per row
            for row in range(2, ws.max_row + 1):
                row_status = {}
                for username, col in status_cols.items():
                    value = ws.cell(row=row, column=col).value
                    if value and str(value).strip().upper() in ["FIXED", "REPORTED"]:
                        row_status[username] = str(value).strip().upper()

                if row_status:
                    manager_status[category][sheet_name][row] = row_status

        wb.close()

    return manager_status
```

### Phase 3: Preserve Manager Status

**Modify:** `process_sheet()` to accept and restore manager status

```python
def process_sheet(master_ws, qa_ws, username, category, image_mapping=None,
                  xlsx_path=None, manager_status=None):
    """
    Process sheet with manager status preservation.

    Args:
        ...existing args...
        manager_status: Dict of {row: {user: status}} for this sheet
    """
    # ... existing processing ...

    # After creating STATUS_{username} column, restore values
    if manager_status:
        status_col = get_or_create_user_status_column(master_ws, username, comment_col)
        for row, user_statuses in manager_status.items():
            if username in user_statuses:
                master_ws.cell(row=row, column=status_col).value = user_statuses[username]
```

### Phase 4: Collect Manager Stats for Tracker

**New function:** `collect_manager_stats_for_tracker()`

```python
def collect_manager_stats_for_tracker():
    """
    Read all Master files and count FIXED/REPORTED per user per category.

    Returns: List of dicts for tracker
    [
        {
            "date": "2026-01-05",  # Use current date or file mod date
            "user": "John",
            "category": "Quest",
            "fixed": 5,
            "reported": 2
        }
    ]
    """
    # Read each Master file
    # Find STATUS_{User} columns
    # Count FIXED and REPORTED per user
    # Return entries for tracker
```

### Phase 5: Update Tracker with Manager Stats

**Modify:** `update_daily_data_sheet()` to include Fixed/Reported

```python
# Add new columns to _DAILY_DATA
headers = ["Date", "User", "Category", "Done", "Issues", "NoIssue", "Blocked", "Fixed", "Reported"]
```

**Modify:** `build_daily_sheet()` and `build_total_sheet()` to show new columns

**Modify:** `build_graphs_sheet()` to add Issue Resolution chart

### Phase 6: Update Main Flow

```python
def main():
    # ... existing setup ...

    # NEW: Preprocess - collect manager status from existing Master files
    print("Collecting manager status from existing Master files...")
    manager_status = collect_manager_status()

    # Process categories (pass manager_status)
    all_daily_entries = []
    for category in CATEGORIES:
        if category in by_category:
            entries = process_category(category, by_category[category], manager_status)
            all_daily_entries.extend(entries)

    # NEW: Collect manager stats for tracker
    manager_entries = collect_manager_stats_for_tracker()

    # Update tracker with both tester and manager stats
    if all_daily_entries or manager_entries:
        tracker_wb, tracker_path = get_or_create_tracker()
        update_daily_data_sheet(tracker_wb, all_daily_entries, manager_entries)
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)
        build_graphs_sheet(tracker_wb)
        tracker_wb.save(tracker_path)
```

---

## Column Order in Master Files

For each user, columns appear in this order:
1. `COMMENT_{User}` - Tester's comment
2. `STATUS_{User}` - Manager's status (FIXED/REPORTED)
3. `SCREENSHOT_{User}` - Tester's screenshot

Example with 2 users:
```
| COMMENT_John | STATUS_John | SCREENSHOT_John | COMMENT_Alice | STATUS_Alice | SCREENSHOT_Alice |
```

---

## Styling

| Column | Header Color | Cell Color |
|--------|--------------|------------|
| COMMENT_{User} | Light Blue (#87CEEB) | Light Blue (#E6F3FF) |
| STATUS_{User} | Light Green (#90EE90) | White (user fills) |
| SCREENSHOT_{User} | Light Blue (#87CEEB) | Light Blue (#E6F3FF) |

**STATUS values styling:**
- FIXED: Green text (#228B22)
- REPORTED: Orange text (#FF8C00)
- Empty: No styling

---

## File Changes Summary

| File | Action | Changes |
|------|--------|---------|
| `compile_qa.py` | MODIFY | Add 4 new functions, modify 5 existing |

**New functions:**
1. `get_or_create_user_status_column()`
2. `collect_manager_status()`
3. `collect_manager_stats_for_tracker()`
4. `merge_tester_and_manager_entries()`

**Modified functions:**
1. `process_sheet()` - Add STATUS column, preserve manager values
2. `process_category()` - Pass manager_status, return manager entries
3. `update_daily_data_sheet()` - Add Fixed/Reported columns
4. `build_daily_sheet()` - Show Fixed/Reported/Pending
5. `build_total_sheet()` - Show Fixed/Reported/Pending
6. `build_graphs_sheet()` - Add resolution chart
7. `main()` - Add preprocess step

**Estimated new code:** ~250 lines

---

## Implementation Order

```
1. Add get_or_create_user_status_column() function
2. Update process_sheet() to create STATUS columns in correct order
3. Add collect_manager_status() function
4. Update process_sheet() to preserve manager status
5. Add collect_manager_stats_for_tracker() function
6. Update _DAILY_DATA schema with Fixed/Reported columns
7. Update build_daily_sheet() with manager stats
8. Update build_total_sheet() with manager stats
9. Update build_graphs_sheet() with resolution chart
10. Update main() with preprocess step
11. Test with mock data
12. Update README
```

---

## Test Scenarios

### Test 1: Fresh Start (No Existing Master Files)
- Run compiler
- Verify STATUS_{User} columns are created (empty)
- Verify tracker shows 0 Fixed/Reported

### Test 2: With Existing Manager Status
1. Run compiler (creates Master files)
2. Manually add FIXED/REPORTED to some STATUS cells
3. Run compiler again
4. Verify STATUS values are preserved
5. Verify tracker shows correct Fixed/Reported counts

### Test 3: New QA Files Added
1. Have existing Master with manager status
2. Add new QA folder
3. Run compiler
4. Verify old status preserved + new comments added

---

## Rollback Plan

If issues occur:
1. Manager status functions are additive
2. Can disable by commenting out preprocess in main()
3. Existing Master files won't be corrupted (only new columns added)

---

*Plan created: 2026-01-05*
*Ready for implementation*
