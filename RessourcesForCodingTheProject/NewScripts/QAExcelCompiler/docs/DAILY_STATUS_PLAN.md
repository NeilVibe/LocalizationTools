# LQA User Progress Tracker - Implementation Plan

## Overview

Enhance QA Excel Compiler to generate:
1. **Master files** (existing) - Each keeps its own STATUS tab per category
2. **LQA_UserProgress_Tracker.xlsx** (NEW) - Combined progress with 3 tabs

---

## Final Output Structure

```
Masterfolder/
├── Master_Quest.xlsx
│   ├── [data sheets]
│   └── STATUS (Quest stats only)
├── Master_Knowledge.xlsx
│   ├── [data sheets]
│   └── STATUS (Knowledge stats only)
├── Master_Item.xlsx
├── Master_Node.xlsx
├── Master_System.xlsx
├── LQA_UserProgress_Tracker.xlsx      # <-- NEW
│   ├── DAILY (all categories combined)
│   ├── TOTAL (all categories combined)
│   └── GRAPHS (charts)
└── Images/
```

---

## LQA_UserProgress_Tracker.xlsx Specification

### Tab 1: DAILY

**Purpose:** Show daily progress per user (all categories combined)

**Layout:**
```
Row 1: "DAILY PROGRESS" (merged across all columns, gold background)
Row 2: Empty (spacing)
Row 3: Headers - merged user names
        | (empty) |   John    |   Alice   |   Bob     |
Row 4: Sub-headers
        |  Date   | Done | Issues | Done | Issues | Done | Issues |
Row 5+: Data rows (one per date, sorted ascending)
        | 01/03   |  57  |   11   |  45  |    5   |  --  |   --   |
        | 01/04   |  --  |   --   |  12  |    2   |  38  |    8   |
Last:   TOTAL row (sum of all days)
        | TOTAL   |  97  |   21   |  57  |    7   |  60  |   13   |
```

**Columns per user:** 2 (Done, Issues)
**Date format:** MM/DD (e.g., 01/05)
**Empty cell:** "--" when user has no submission that day

**Styling:**
- Title row: Gold (#FFD700), bold, centered, merged
- User header row: Light blue (#87CEEB), bold, centered, merged (spans Done+Issues)
- Sub-header row: Light gray (#D3D3D3), bold, centered
- Data rows: Alternating white/#F5F5F5
- TOTAL row: Darker gray (#E6E6E6), bold
- All cells: Thin black borders
- Column widths: Date=12, Done=10, Issues=10

---

### Tab 2: TOTAL

**Purpose:** Show cumulative stats per user (all categories combined)

**Layout:**
```
Row 1: "TOTAL SUMMARY" (merged, gold background)
Row 2: Empty (spacing)
Row 3: Headers
        | User | Completion % | Total | Issues | No Issue | Blocked |
Row 4+: Data rows (one per user, sorted alphabetically)
        | Alice |    100.0%   |   57  |    7   |    47    |    3    |
        | Bob   |     88.0%   |   60  |   13   |    42    |    5    |
        | John  |     95.0%   |   97  |   21   |    68    |    8    |
Last:   TOTAL row (sum/average)
        | TOTAL |     94.3%   |  214  |   41   |   157    |   16    |
```

**Columns:** 6
- User: Username
- Completion %: (Issues + NoIssue + Blocked) / TotalRows * 100
- Total: Total rows processed
- Issues: Count of STATUS="ISSUE"
- No Issue: Count of STATUS="NO ISSUE"
- Blocked: Count of STATUS="BLOCKED"

**Styling:** Same as DAILY tab

---

### Tab 3: GRAPHS

**Purpose:** Visual charts for progress tracking

**Chart 1: Daily Trend (top half)**
- Type: BarChart (clustered)
- X-axis: Dates
- Y-axis: Count
- Series: One per user (Done values)
- Position: A1, width=15, height=10
- Title: "Daily Progress by User"
- Legend: Bottom

**Chart 2: User Completion (bottom half)**
- Type: BarChart (horizontal)
- X-axis: Completion %
- Y-axis: Users
- Series: Completion % per user
- Position: A20, width=12, height=8
- Title: "User Completion Rate"
- Legend: None (single series)

**Colors:**
- John: Blue (#4472C4)
- Alice: Orange (#ED7D31)
- Bob: Green (#70AD47)
- Additional users: cycle through palette

---

### Hidden Sheet: _DAILY_DATA

**Purpose:** Raw data storage for persistence between runs

**Layout:**
```
| Date       | User  | Category  | Done | Issues | NoIssue | Blocked |
|------------|-------|-----------|------|--------|---------|---------|
| 2026-01-03 | John  | Quest     |  32  |   7    |   22    |    3    |
| 2026-01-03 | John  | Knowledge |  25  |   4    |   18    |    3    |
| 2026-01-03 | Alice | Quest     |  45  |   5    |   38    |    2    |
```

**Key:** (Date, User, Category) - unique combination
**Update mode:** REPLACE (same key = overwrite values)
**Date format:** YYYY-MM-DD (for sorting)

---

## Implementation Details

### Phase 1: Configuration

Add to top of `compile_qa.py`:

```python
# === TRACKER CONFIGURATION ===
TRACKER_FILENAME = "LQA_UserProgress_Tracker.xlsx"

TRACKER_STYLES = {
    "title_color": "FFD700",       # Gold
    "header_color": "87CEEB",      # Light blue
    "subheader_color": "D3D3D3",   # Light gray
    "alt_row_color": "F5F5F5",     # Alternating gray
    "total_row_color": "E6E6E6",   # Total row gray
    "border_color": "000000",      # Black
}

CHART_COLORS = ["4472C4", "ED7D31", "70AD47", "FFC000", "5B9BD5", "A5A5A5"]
```

---

### Phase 2: New Functions

#### Function: `get_or_create_tracker()`

```python
def get_or_create_tracker():
    """
    Load existing tracker or create new one with 3 sheets.

    Returns: (workbook, path)
    """
    tracker_path = MASTER_FOLDER / TRACKER_FILENAME

    if tracker_path.exists():
        wb = openpyxl.load_workbook(tracker_path)
    else:
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)
        # Create sheets in order
        wb.create_sheet("DAILY", 0)
        wb.create_sheet("TOTAL", 1)
        wb.create_sheet("GRAPHS", 2)
        wb.create_sheet("_DAILY_DATA", 3)
        # Hide data sheet
        wb["_DAILY_DATA"].sheet_state = 'hidden'

    return wb, tracker_path
```

#### Function: `update_daily_data_sheet(wb, daily_entries)`

```python
def update_daily_data_sheet(wb, daily_entries):
    """
    Update hidden _DAILY_DATA sheet with new entries.

    Args:
        wb: Tracker workbook
        daily_entries: List of dicts with {date, user, category, done, issues, no_issue, blocked}

    Mode: REPLACE - same (date, user, category) overwrites existing row
    """
    ws = wb["_DAILY_DATA"]

    # Ensure headers exist
    if ws.cell(1, 1).value != "Date":
        headers = ["Date", "User", "Category", "Done", "Issues", "NoIssue", "Blocked"]
        for col, header in enumerate(headers, 1):
            ws.cell(1, col, header)

    # Build index of existing rows: (date, user, category) -> row_number
    existing = {}
    for row in range(2, ws.max_row + 1):
        key = (
            ws.cell(row, 1).value,  # Date
            ws.cell(row, 2).value,  # User
            ws.cell(row, 3).value   # Category
        )
        existing[key] = row

    # Update or insert entries
    for entry in daily_entries:
        key = (entry["date"], entry["user"], entry["category"])

        if key in existing:
            row = existing[key]
        else:
            row = ws.max_row + 1
            existing[key] = row

        ws.cell(row, 1, entry["date"])
        ws.cell(row, 2, entry["user"])
        ws.cell(row, 3, entry["category"])
        ws.cell(row, 4, entry["done"])
        ws.cell(row, 5, entry["issues"])
        ws.cell(row, 6, entry["no_issue"])
        ws.cell(row, 7, entry["blocked"])
```

#### Function: `build_daily_sheet(wb)`

```python
def build_daily_sheet(wb):
    """
    Build DAILY sheet from _DAILY_DATA.

    Aggregates by (date, user) - combines all categories.
    """
    ws = wb["DAILY"]
    data_ws = wb["_DAILY_DATA"]

    # Clear existing content
    for row in ws.iter_rows():
        for cell in row:
            cell.value = None

    # Read raw data and aggregate by (date, user)
    # date -> user -> {done, issues}
    daily_data = defaultdict(lambda: defaultdict(lambda: {"done": 0, "issues": 0}))
    users = set()

    for row in range(2, data_ws.max_row + 1):
        date = data_ws.cell(row, 1).value
        user = data_ws.cell(row, 2).value
        done = data_ws.cell(row, 4).value or 0
        issues = data_ws.cell(row, 5).value or 0

        if date and user:
            daily_data[date][user]["done"] += done
            daily_data[date][user]["issues"] += issues
            users.add(user)

    users = sorted(users)
    dates = sorted(daily_data.keys())

    # Build table
    # Row 1: Title
    # Row 2: Empty
    # Row 3: User names (merged)
    # Row 4: Done/Issues headers
    # Row 5+: Data
    # Last: TOTAL

    # ... (styling and cell population code)
```

#### Function: `build_total_sheet(wb)`

```python
def build_total_sheet(wb):
    """
    Build TOTAL sheet from _DAILY_DATA.

    Aggregates by user across all dates and categories.
    """
    # Similar structure to build_daily_sheet
    # Columns: User, Completion %, Total, Issues, No Issue, Blocked
```

#### Function: `build_graphs_sheet(wb)`

```python
def build_graphs_sheet(wb):
    """
    Build GRAPHS sheet with charts.

    Uses openpyxl.chart module.
    """
    from openpyxl.chart import BarChart, Reference

    ws = wb["GRAPHS"]
    daily_ws = wb["DAILY"]
    total_ws = wb["TOTAL"]

    # Chart 1: Daily Trend
    chart1 = BarChart()
    chart1.type = "col"
    chart1.title = "Daily Progress by User"
    # ... configure data references, series, styling

    ws.add_chart(chart1, "A1")

    # Chart 2: User Completion
    chart2 = BarChart()
    chart2.type = "bar"
    chart2.title = "User Completion Rate"
    # ... configure

    ws.add_chart(chart2, "A20")
```

---

### Phase 3: Modify Existing Functions

#### Modify: `process_category()`

**Current:** Returns nothing, just prints stats
**New:** Returns list of daily_entries

```python
def process_category(category, qa_folders):
    """
    Process all QA folders for one category.

    Returns: List of daily_entry dicts for tracker
    """
    # ... existing code ...

    daily_entries = []  # NEW

    for qf in qa_folders:
        # ... existing processing ...

        # Get file modification date
        file_mod_time = datetime.fromtimestamp(qf["xlsx_path"].stat().st_mtime)
        file_mod_date = file_mod_time.strftime("%Y-%m-%d")

        # After processing all sheets for this user, collect entry
        daily_entries.append({
            "date": file_mod_date,
            "user": qf["username"],
            "category": category,
            "done": user_stats[qf["username"]]["issue"] +
                    user_stats[qf["username"]]["no_issue"] +
                    user_stats[qf["username"]]["blocked"],
            "issues": user_stats[qf["username"]]["issue"],
            "no_issue": user_stats[qf["username"]]["no_issue"],
            "blocked": user_stats[qf["username"]]["blocked"]
        })

    # ... existing save code ...

    return daily_entries  # NEW
```

#### Modify: `main()`

```python
def main():
    # ... existing setup code ...

    all_daily_entries = []  # NEW

    # Process each category
    for category in CATEGORIES:
        if category in by_category:
            entries = process_category(category, by_category[category])
            all_daily_entries.extend(entries)  # NEW

    # NEW: Update tracker
    if all_daily_entries:
        print("\n" + "="*60)
        print("Updating LQA User Progress Tracker...")
        print("="*60)

        tracker_wb, tracker_path = get_or_create_tracker()
        update_daily_data_sheet(tracker_wb, all_daily_entries)
        build_daily_sheet(tracker_wb)
        build_total_sheet(tracker_wb)
        build_graphs_sheet(tracker_wb)
        tracker_wb.save(tracker_path)

        print(f"Saved: {tracker_path}")

    # ... existing completion message ...
```

---

## File Modification Summary

| File | Action | Changes |
|------|--------|---------|
| `compile_qa.py` | MODIFY | Add config, 5 new functions, modify 2 existing |

**New code:** ~350 lines
**Modified code:** ~30 lines

---

## Test Plan

### Test Data Setup

Create mock folders with different modification dates:

```bash
# In QAfolder/
mkdir -p John_Quest Alice_Quest Bob_Knowledge

# Create xlsx files with backdated modification times
touch -d "2026-01-03 14:00" John_Quest/LQA_Quest.xlsx
touch -d "2026-01-04 10:00" Alice_Quest/LQA_Quest.xlsx
touch -d "2026-01-04 15:00" Bob_Knowledge/LQA_Knowledge.xlsx
touch -d "2026-01-05 09:00" John_Quest/LQA_Quest.xlsx  # Update John to 01/05
```

### Expected Output

After running `python3 compile_qa.py`:

1. `Master_Quest.xlsx` - STATUS tab with John + Alice
2. `Master_Knowledge.xlsx` - STATUS tab with Bob
3. `LQA_UserProgress_Tracker.xlsx`:
   - DAILY tab: 3 dates (01/03, 01/04, 01/05), 3 users
   - TOTAL tab: 3 users with cumulative stats
   - GRAPHS tab: 2 charts

### Verification Steps

1. Open `LQA_UserProgress_Tracker.xlsx`
2. Check DAILY tab:
   - John has data on 01/05 (updated date)
   - Alice has data on 01/04
   - Bob has data on 01/04
   - TOTAL row sums correctly
3. Check TOTAL tab:
   - All 3 users listed
   - Percentages calculate correctly
4. Check GRAPHS tab:
   - Both charts render
   - Data matches tables

---

## Implementation Order

```
1. Add TRACKER_CONFIG and TRACKER_STYLES to configuration section
2. Implement get_or_create_tracker()
3. Implement update_daily_data_sheet()
4. Implement build_daily_sheet() with full styling
5. Implement build_total_sheet() with full styling
6. Implement build_graphs_sheet() with charts
7. Modify process_category() to return daily_entries
8. Modify main() to call tracker functions
9. Test with existing sample data
10. Verify output
```

---

## Rollback Plan

If issues occur:
1. Tracker functions are additive (don't modify existing Master logic)
2. Can comment out tracker code in main() to disable
3. Master files continue to work independently

---

*Plan finalized: 2026-01-05*
*Ready for implementation*

---

## Update 2026-01-08: DAILY Tab Simplification

### Changes Requested

1. **Remove Comp% and Actual Issues columns from DAILY**
   - Too confusing ("what is Comp%?")
   - Keep only: Done, Issues per user
   - Comp% and Actual Issues remain in TOTAL tab only

2. **Add thick bold lines between users**
   - Clear visual separation between testers
   - Makes it easier to see whose data is whose

3. **Chart uses main table directly**
   - Currently: Separate hidden data table for chart
   - New: Chart references main table columns
   - Cleaner, no duplicate data

### DAILY Tab - New Layout

```
Row 1: "DAILY PROGRESS" (merged, gold)
Row 2: Section headers (Tester Stats | Manager Stats)
Row 3: User names (merged) - THICK BORDER between each user
Row 4: Sub-headers - Date | Done | Issues | Done | Issues | ... | Fixed | Reported | Checking | Pending
Row 5+: Data rows
Last:  TOTAL row

   ║        Kim         ║        Lee         ║  Manager Stats  ║
   ║────────────────────║────────────────────║─────────────────║
   ║  Done  │  Issues   ║  Done  │  Issues   ║ Fix │ Rep │ ... ║
───╬────────┼───────────╬────────┼───────────╬─────┼─────┼─────╬───
01/05 ║   57   │    11     ║   45   │     5     ║  3  │  2  │ ... ║
01/06 ║   23   │     4     ║   --   │    --     ║  1  │  0  │ ... ║

THICK BORDER (║) between user columns and before Manager Stats
Thin border (│) between columns within same user
```

### Columns Per User (DAILY)

**Before:** 4 columns (Done, Issues, Comp %, Actual Issues)
**After:** 2 columns (Done, Issues)

### Border Styles

```python
# Thick border for user separation
thick_side = Side(style='thick', color='000000')

# Thin border for internal columns
thin_side = Side(style='thin', color='000000')

# Apply thick border to LEFT side of first column for each user
# Apply thick border to LEFT side of Manager Stats section
```

### Chart Reference Change

**Before:**
```python
# Build separate data table for chart
chart_data_row = data_row + 3
# ... populate separate table ...
data_ref = Reference(ws, min_col=2, ..., min_row=chart_data_row, ...)
```

**After:**
```python
# Use main table directly for chart
# Done columns are at: 2, 4, 6, ... (every 2nd column starting from 2)
# Reference row 5 (first data row) to row before TOTAL
data_ref = Reference(ws, min_col=2, max_col=num_users*2+1, min_row=4, max_row=data_row-1)
```

### Implementation Steps

1. Update `tester_cols_per_user` from 4 to 2
2. Remove Comp% and Actual Issues from header row
3. Remove Comp% and Actual Issues from data rows
4. Remove Comp% and Actual Issues from TOTAL row calculations
5. Add thick border to left side of each user's first column
6. Remove separate chart data table
7. Update chart Reference to use main table columns
