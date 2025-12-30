# QA Excel Compiler - Implementation Details

**Created:** 2025-12-30 | **Status:** PLANNING

---

## Quick Summary

| Aspect | Detail |
|--------|--------|
| **Goal** | Compile 20+ QA Excel files into 5 master sheets |
| **Input** | `QAfolder/{Username}_{Category}.xlsx` |
| **Output** | `Masterfolder/Master_{Category}.xlsx` |
| **Key Features** | Comment aggregation, Status tracking, Auto-update |

---

## File Structure Analysis

Based on `ExampleForXLSCompiler.xlsx`:

```
Sheets: ['Sheet1', 'Sheet3']  # Multiple sheets per file

Columns per sheet:
├── Original      # Korean source text (read-only)
├── ENG           # English translation (read-only)
├── StringKey     # Optional identifier (not used for matching)
├── Command       # Dev commands (read-only)
├── STATUS        # QA fills this (OK/ERROR/PENDING/etc)
├── COMMENT       # QA feedback text
└── SCREENSHOT    # Hyperlink (IGNORED in compilation)
```

---

## Core Logic

### 1. File Discovery

```python
def discover_qa_files(qa_folder):
    """
    Find all QA Excel files and parse their metadata.

    Returns: List of dicts with {filepath, username, category}
    """
    files = []
    for f in Path(qa_folder).glob("*.xlsx"):
        # Skip temp files
        if f.name.startswith("~$"):
            continue

        # Parse: Username_Category.xlsx
        parts = f.stem.split("_")
        if len(parts) >= 2:
            files.append({
                "filepath": f,
                "username": parts[0],
                "category": parts[1]
            })
        else:
            print(f"WARN: Invalid filename format: {f.name}")

    return files
```

### 2. Row Matching Strategy

**Primary Key:** Row index

**Why this works:** Within each category, all QA testers receive the SAME base file with identical structure. Different categories have different structures, but we only compile within the same category.

**Fallback Algorithm (if row index fails):**

If rows get shifted/inserted for some reason, use composite key matching:
- Take any 2+ non-editable cell values from the row (Original, ENG, StringKey, Command)
- If 2+ values match between QA row and master row = same row

```python
def find_matching_row_fallback(master_ws, qa_row_values):
    """
    Fallback: Match by 2+ cell values from non-editable columns.

    Non-editable columns: Original (A), ENG (B), StringKey (C), Command (D)
    Editable columns (excluded): STATUS (E), COMMENT (F), SCREENSHOT (G)
    """
    qa_key_values = qa_row_values[:4]  # First 4 columns (A-D)

    for master_row_idx in range(2, master_ws.max_row + 1):
        master_key_values = [master_ws.cell(row=master_row_idx, column=c).value for c in range(1, 5)]

        # Count matching cells (ignore None/empty)
        matches = sum(1 for q, m in zip(qa_key_values, master_key_values)
                     if q and m and str(q).strip() == str(m).strip())

        if matches >= 2:
            return master_row_idx

    return None  # No match found
```

**When to use fallback:**
- Primary (row index) should work 99% of the time
- Fallback only if row counts mismatch or structure appears shifted

```python
def process_rows(master_ws, qa_ws, username, col_index):
    """
    Match QA rows to master rows by row index.

    All sheets are identical in structure, so row N in QA file
    corresponds to row N in master file.
    """
    for row_idx in range(2, qa_ws.max_row + 1):  # Skip header (row 1)
        # Get COMMENT value from QA file (column 6 = F = COMMENT)
        qa_comment = qa_ws.cell(row=row_idx, column=6).value

        if qa_comment and str(qa_comment).strip():
            # Update master at same row, user's comment column
            update_comment_cell(master_ws, row_idx, col_index, qa_comment)
```

### 3. Comment Column Management

```python
def ensure_comment_column(df, username):
    """
    Ensure COMMENT_{username} column exists.

    Returns column name.
    """
    col_name = f"COMMENT_{username}"

    if col_name not in df.columns:
        # Insert after last COMMENT_ column, or after Command
        comment_cols = [c for c in df.columns if c.startswith("COMMENT_")]
        if comment_cols:
            insert_pos = df.columns.get_loc(comment_cols[-1]) + 1
        else:
            insert_pos = df.columns.get_loc("Command") + 1

        df.insert(insert_pos, col_name, "")

    return col_name
```

### 4. Comment Update Logic

```python
from datetime import datetime

def update_comment(existing_comment, new_comment):
    """
    Append new comment with datetime, keeping history.

    Format:
    "New comment text" (date: YYMMDD HHMM)

    "Old comment text" (date: YYMMDD HHMM)
    """
    if pd.isna(new_comment) or str(new_comment).strip() == "":
        return existing_comment

    timestamp = datetime.now().strftime("%y%m%d %H%M")
    formatted_new = f'"{new_comment}" (date: {timestamp})'

    if pd.isna(existing_comment) or str(existing_comment).strip() == "":
        return formatted_new
    else:
        # New on top, old below
        return f"{formatted_new}\n\n{existing_comment}"
```

### 5. Status Calculation

```python
def calculate_user_status(df, username):
    """
    Calculate completion % for a user's comments.

    Completion = non-empty COMMENT_{user} cells / total rows * 100
    """
    col_name = f"COMMENT_{username}"

    if col_name not in df.columns:
        return 0.0

    total = len(df)
    if total == 0:
        return 100.0

    filled = df[col_name].notna() & (df[col_name].astype(str).str.strip() != "")
    completed = filled.sum()

    return round(completed / total * 100, 1)
```

### 6. STATUS Sheet Structure

```python
def create_status_sheet(workbook, users, sheet_stats):
    """
    Create/update STATUS sheet with completion tracking.

    | User  | Sheet1 | Sheet3 | ... | Total |
    |-------|--------|--------|-----|-------|
    | John  | 85%    | 100%   | ... | 92%   |
    | Alice | 50%    | 75%    | ... | 62%   |
    """
    # Create sheet if not exists
    if "STATUS" not in workbook.sheetnames:
        ws = workbook.create_sheet("STATUS")
    else:
        ws = workbook["STATUS"]
        ws.delete_rows(1, ws.max_row)  # Clear existing

    # Header row
    sheets = list(sheet_stats.keys())
    headers = ["User"] + sheets + ["Total"]
    ws.append(headers)

    # Data rows
    for user in sorted(users):
        row = [user]
        total_pct = []

        for sheet in sheets:
            pct = sheet_stats[sheet].get(user, 0.0)
            row.append(f"{pct}%")
            total_pct.append(pct)

        # Calculate total average
        avg = round(sum(total_pct) / len(total_pct), 1) if total_pct else 0.0
        row.append(f"{avg}%")

        ws.append(row)

    return ws
```

---

## Main Compilation Flow

```python
def compile_qa_files():
    """
    Main compilation workflow.
    """
    QA_FOLDER = Path("./QAfolder")
    MASTER_FOLDER = Path("./Masterfolder")
    CATEGORIES = ["Quest", "Knowledge", "Item", "Node", "System"]

    # 1. Discover QA files
    qa_files = discover_qa_files(QA_FOLDER)
    if not qa_files:
        print("No QA files found in QAfolder/")
        return

    print(f"Found {len(qa_files)} QA files")

    # 2. Group by category
    by_category = {}
    for qf in qa_files:
        cat = qf["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(qf)

    # 3. Process each category
    for category in CATEGORIES:
        if category not in by_category:
            print(f"SKIP: No files for category '{category}'")
            continue

        master_path = MASTER_FOLDER / f"Master_{category}.xlsx"
        process_category(category, by_category[category], master_path)

    print("\nCompilation complete!")


def process_category(category, qa_files, master_path):
    """
    Process all QA files for one category into its master file.
    """
    print(f"\n=== Processing {category} ({len(qa_files)} files) ===")

    # Load or create master workbook
    if master_path.exists():
        master_wb = openpyxl.load_workbook(master_path)
        print(f"  Loaded existing: {master_path.name}")
    else:
        # Create from first QA file as template
        first_file = qa_files[0]["filepath"]
        master_wb = openpyxl.load_workbook(first_file)
        print(f"  Created new master from: {first_file.name}")

    # Track all users for STATUS sheet
    all_users = set()
    sheet_stats = {}  # {sheet_name: {user: pct}}

    # Process each QA file
    for qf in qa_files:
        username = qf["username"]
        filepath = qf["filepath"]
        all_users.add(username)

        print(f"  Processing: {filepath.name} (user: {username})")

        qa_wb = openpyxl.load_workbook(filepath)

        for sheet_name in qa_wb.sheetnames:
            if sheet_name == "STATUS":
                continue  # Skip if QA file has STATUS sheet

            if sheet_name not in master_wb.sheetnames:
                print(f"    WARN: Sheet '{sheet_name}' not in master, skipping")
                continue

            # Process this sheet
            process_sheet(master_wb, sheet_name, qa_wb[sheet_name], username)

            # Calculate status
            master_df = sheet_to_dataframe(master_wb[sheet_name])
            pct = calculate_user_status(master_df, username)

            if sheet_name not in sheet_stats:
                sheet_stats[sheet_name] = {}
            sheet_stats[sheet_name][username] = pct

        qa_wb.close()

    # Update STATUS sheet
    create_status_sheet(master_wb, all_users, sheet_stats)

    # Save master
    master_wb.save(master_path)
    print(f"  Saved: {master_path.name}")
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INPUT                                      │
├─────────────────────────────────────────────────────────────────────┤
│  QAfolder/                                                           │
│  ├── John_Quest.xlsx     ─┐                                         │
│  ├── Alice_Quest.xlsx    ─┼─→ Group by Category                      │
│  ├── Bob_Quest.xlsx      ─┘                                         │
│  ├── John_Knowledge.xlsx ─┐                                         │
│  └── Alice_Knowledge.xlsx─┘                                         │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PROCESSING                                   │
├─────────────────────────────────────────────────────────────────────┤
│  For each category (Quest, Knowledge, Item, Node, System):           │
│                                                                       │
│  1. Load/Create Master_{Category}.xlsx                               │
│  2. For each QA file in category:                                    │
│     a. Extract username from filename                                │
│     b. For each sheet:                                               │
│        - Match rows by row index (identical structure)               │
│        - Ensure COMMENT_{username} column exists                     │
│        - Update comments (append with datetime)                      │
│     c. Calculate completion % for STATUS                             │
│  3. Create/Update STATUS sheet with all users                        │
│  4. Save Master file                                                 │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Masterfolder/                                                       │
│  ├── Master_Quest.xlsx                                              │
│  │   ├── Sheet1      # Data + COMMENT_John, COMMENT_Alice, etc      │
│  │   ├── Sheet3      # Data + COMMENT_John, COMMENT_Alice, etc      │
│  │   └── STATUS      # Completion % per user                         │
│  ├── Master_Knowledge.xlsx                                          │
│  ├── Master_Item.xlsx                                               │
│  ├── Master_Node.xlsx                                               │
│  └── Master_System.xlsx                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Example Transformations

### Before (QA Files)

**John_Quest.xlsx - Sheet1:**
| Original | ENG | StringKey | STATUS | COMMENT |
|----------|-----|-----------|--------|---------|
| 기습 | Ambush | 10001 | OK | Looks good |
| 낯선 땅 | Strange Lands | 1000157 | ERROR | Typo here |

**Alice_Quest.xlsx - Sheet1:**
| Original | ENG | StringKey | STATUS | COMMENT |
|----------|-----|-----------|--------|---------|
| 기습 | Ambush | 10001 | | |
| 낯선 땅 | Strange Lands | 1000157 | OK | Fixed now |

### After (Master File)

**Master_Quest.xlsx - Sheet1:**
| Original | ENG | StringKey | Command | COMMENT_John | COMMENT_Alice |
|----------|-----|-----------|---------|--------------|---------------|
| 기습 | Ambush | 10001 | | "Looks good" (date: 251230 1500) | |
| 낯선 땅 | Strange Lands | 1000157 | | "Typo here" (date: 251230 1500) | "Fixed now" (date: 251230 1502) |

**Master_Quest.xlsx - STATUS:**
| User | Sheet1 | Sheet3 | Total |
|------|--------|--------|-------|
| Alice | 50% | 0% | 25% |
| John | 100% | 0% | 50% |

---

## Implementation Order

1. **Phase 1: File Handling** (Core)
   - [ ] `discover_qa_files()` - Find and parse QA files
   - [ ] `load_or_create_master()` - Handle master file I/O
   - [ ] Basic main loop structure

2. **Phase 2: Comment Logic** (Core)
   - [ ] `ensure_comment_column()` - Add user columns
   - [ ] Row-by-row processing (index matching)
   - [ ] `update_comment()` - Append with datetime

3. **Phase 3: Status Tracking** (Core)
   - [ ] `calculate_user_status()` - Completion %
   - [ ] `create_status_sheet()` - Build STATUS tab

4. **Phase 4: Polish**
   - [ ] Error handling and validation
   - [ ] Progress logging
   - [ ] CLI arguments

---

## Open Questions

| Question | Decision |
|----------|----------|
| What if row counts differ? | Process up to min(master, qa) rows |
| What if sheet names differ between QA files? | Only process sheets that exist in master |
| What if QA file has new sheets not in master? | Skip with warning |
| Should we preserve Excel formatting? | Yes, use openpyxl (not pandas for write) |
| Backup before overwrite? | Optional (--backup flag) |

---

## Future Features (TODO)

### Category-Specific Column Deletion

**Request:** Some QA files have too many columns. When creating master file, delete additional columns for SPECIFIC categories (e.g., Item, Quest).

**Implementation Plan:**
```python
# Configuration dict for category-specific columns to delete
CATEGORY_COLUMNS_TO_DELETE = {
    "Item": ["ExtraCol1", "ExtraCol2"],
    "Quest": ["UnneededCol"],
    # Add more as needed
}

def get_or_create_master(category, template_file):
    # ... existing code ...

    # Category-specific column deletion
    if category in CATEGORY_COLUMNS_TO_DELETE:
        for col_name in CATEGORY_COLUMNS_TO_DELETE[category]:
            col = find_column_by_header(ws, col_name)
            if col:
                ws.delete_cols(col)
```

**Status:** PLANNED - awaiting user specification of which columns to delete per category.

---

*WIP created 2025-12-30*
*Updated 2025-12-30: Added StringID parsing, column styling, future features*
