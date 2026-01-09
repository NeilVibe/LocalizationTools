# QA Excel Compiler - Implementation Details

**Created:** 2025-12-30 | **Status:** ✅ IMPLEMENTED | **Updated:** 2026-01-07

---

## DONE: Data Refresh & Clean Output ✅ (2026-01-07)

**Goal:** Ensure clean, consistent output regardless of tester's Excel settings

**Implementation:**

### 1. Clear Tester AutoFilters
- Removes any filter dropdown/sorting from tester files
- Master output is always clean

### 2. Reset Hidden Rows
- Unhides ALL rows first before applying our hiding logic
- Prevents tester's hidden rows from affecting output

### 3. Hide Empty User Columns
- If `COMMENT_{User}` column is empty in a sheet, hide it
- Also hides paired `SCREENSHOT_{User}` and `STATUS_{User}` columns
- Per-sheet basis (user may have comments in Sheet1 but not Sheet2)

### 4. Refresh Base Data Columns
- ALL columns are refreshed from QA files EXCEPT:
  - STATUS, COMMENT, SCREENSHOT (specially handled)
  - COMMENT_{User}, SCREENSHOT_{User}, STATUS_{User} (user-specific)
- Ensures master always has latest base data

### 5. Item Category A-Z Sorting
- **EN Item:** Sorted A-Z by `ItemName(ENG)` column to match tester order
- **CN Item:** Original order (no sorting)
- Testers sort their Item files A-Z, so master must match

### 6. Word Wrap + Autofit Row Heights
- All cells get `wrap_text=True`
- Row heights calculated based on content (line breaks + text length)
- Max height capped at 300 points

---

## DONE: EN/CN Language Separation ✅ (2026-01-06)

**Goal:** Separate Master files by language (EN vs CN)

**Implementation:**
- Tester→Language mapping loaded from `languageTOtester_list.txt`
- Two Master folders: `Masterfolder_EN/` and `Masterfolder_CN/`
- Testers auto-routed based on mapping (defaults to EN if not found)
- Progress Tracker at root level, combines all language data
- TOTAL sheet shows separate sections: "EN TESTER STATS" (blue) and "CN TESTER STATS" (red)
- Grand total row combines all languages

**Mapping File Format (`languageTOtester_list.txt`):**
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

---

## DONE: Auto-Hide Empty Rows & Sheets ✅ (2026-01-06)

**Goal:** Focus on issues by hiding rows/sheets with no comments

**Implementation:**
- Post-process `hide_empty_comment_rows(wb, context_rows=1)` runs after compilation
- **Sheet hiding:** Sheets with NO comments at all are hidden entirely (tab hidden)
- **Row hiding:** Rows with ALL `COMMENT_{User}` columns empty are hidden
- **Context rows:** Adjacent rows (1 above/below) to commented rows stay visible
- Data preserved - nothing deleted, just hidden

**Output:**
```
  Hidden sheets (no comments): Sheet2, Sheet3
  Hidden: 5 rows with no comments (unhide in Excel if needed)
```

**To unhide in Excel:**
- Sheets: Right-click any tab → "Unhide" → select sheet
- Rows: `Home > Format > Hide & Unhide > Unhide Rows`

---

## DONE: Chart Standardization ✅ (2026-01-06)

**Goal:** Make DAILY and TOTAL sheets use identical clustered bar chart style

### DAILY Sheet Charts ✅
1. **Chart 1: "Daily Progress: Done by Tester"**
   - X-axis: Dates (MM/DD)
   - Y-axis: Done count
   - Series: Each tester as colored bar
   - Dynamic width: `max(15, 6 + num_dates * 2)`

2. **Chart 2: "Daily Progress: Actual Issues % by Tester"**
   - X-axis: Dates (MM/DD)
   - Y-axis: Actual Issues %
   - Placed BELOW first chart (15 rows spacing)

### TOTAL Sheet Charts ✅
1. **Chart 1: "Total Progress: Done by Tester"**
   - X-axis: Tester names
   - Y-axis: Done count (cumulative)
   - Dynamic width: `max(15, 6 + num_users * 2)`

2. **Chart 2: "Total Progress: Actual Issues % by Tester"**
   - X-axis: Tester names
   - Y-axis: Actual Issues %
   - Placed BELOW first chart (15 rows spacing)

### Key Principle
Both sheets use **identical chart style** - clustered vertical bars that expand horizontally.
Only difference: DAILY uses dates on X-axis, TOTAL uses tester names.

---

## DONE: GRAPHS Tab Redesign ✅ (DEPRECATED)

**Status:** SUPERSEDED by embedded charts in DAILY/TOTAL

**Old plan:** [GRAPHS_REDESIGN_PLAN.md](GRAPHS_REDESIGN_PLAN.md) - no longer applies

---

## Quick Summary

| Aspect | Detail |
|--------|--------|
| **Goal** | Compile QA folders into 5 master sheets with image consolidation |
| **Input** | `QAfolder/{Username}_{Category}/` (folder with xlsx + images) |
| **Output** | `Masterfolder/Master_{Category}.xlsx` + `Masterfolder/Images/` |
| **Key Features** | Paired COMMENT/SCREENSHOT columns, Image consolidation, Hyperlink transformation, Status tracking |
| **Styling** | Unified blue theme for COMMENT/SCREENSHOT (headers + cells), preserves custom colors on re-runs |

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

def format_comment(new_comment, string_id=None, existing_comment=None, file_mod_time=None):
    """
    Format comment with StringID and file modification time.

    Format (with stringid):
        <comment text>
        ---
        stringid:
        <stringid value>
        (updated: YYMMDD HHMM)

    Format (without stringid):
        <comment text>
        ---
        (updated: YYMMDD HHMM)

    REPLACE MODE: New comments replace old entirely.
    DUPLICATE CHECK: Split on '---' delimiter to compare original text.
    """
    if not new_comment or str(new_comment).strip() == "":
        return existing_comment

    new_text = str(new_comment).strip()

    # Check for duplicate by splitting on --- delimiter
    if existing_comment and "\n---\n" in str(existing_comment):
        existing_original = str(existing_comment).split("\n---\n")[0].strip()
        if existing_original == new_text:
            return existing_comment  # Skip duplicate

    timestamp = file_mod_time.strftime("%y%m%d %H%M") if file_mod_time else datetime.now().strftime("%y%m%d %H%M")

    if string_id and str(string_id).strip():
        return f"{new_text}\n---\nstringid:\n{str(string_id).strip()}\n(updated: {timestamp})"
    else:
        return f"{new_text}\n---\n(updated: {timestamp})"
```

### 4.1 Cell Styling

**Unified blue theme** for both COMMENT and SCREENSHOT columns:

| Element | Color | Code |
|---------|-------|------|
| Header fill | Light blue | `87CEEB` |
| Header border | Blue | `4472C4` |
| Cell fill (on update) | Light blue | `E6F3FF` |
| Cell border | Sky blue | `87CEEB` |
| Hyperlink font | Blue | `0000FF` |
| Warning font (missing image) | Orange | `FF6600` |

**Custom color protection:**
- Styling only applies when value is NEW (different from existing)
- If team manually colors a cell, it won't be overwritten on re-runs
- Duplicate detection prevents unnecessary updates

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
| 기습 | Ambush | 10001 | | Looks good\n---\nstringid:\n10001\n(updated: 251230 1500) | |
| 낯선 땅 | Strange Lands | 1000157 | | Typo here\n---\nstringid:\n1000157\n(updated: 251230 1500) | Fixed now\n---\nstringid:\n1000157\n(updated: 251230 1502) |

**Master_Quest.xlsx - STATUS:**
| User | Sheet1 | Sheet3 | Total |
|------|--------|--------|-------|
| Alice | 50% | 0% | 25% |
| John | 100% | 0% | 50% |

---

## Implementation Order

1. **Phase 1: File Handling** (Core) ✅
   - [x] `discover_qa_folders()` - Find and parse QA folders
   - [x] `get_or_create_master()` - Handle master file I/O
   - [x] Basic main loop structure

2. **Phase 2: Comment Logic** (Core) ✅
   - [x] `get_or_create_user_comment_column()` - Add user columns
   - [x] Row-by-row processing (index matching)
   - [x] `format_comment()` - Append with datetime

3. **Phase 3: Status Tracking** (Core) ✅
   - [x] Calculate user status in `process_sheet()`
   - [x] `update_status_sheet()` - Build STATUS tab

4. **Phase 4: Polish** ✅
   - [x] Error handling and validation
   - [x] Progress logging
   - [ ] CLI arguments (skipped - not needed)

5. **Phase 5: Image Compilation** ✅ (NEW)
   - [x] `copy_images_with_unique_names()` - Copy to Images/
   - [x] `get_or_create_user_screenshot_column()` - Paired with COMMENT
   - [x] Hyperlink transformation in `process_sheet()`

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

## IMAGE COMPILATION SYSTEM (NEW)

### Overview

**Change:** Remove MasterUI logic. Instead, compile ALL images from QA folders into a centralized `Masterfolder/Images/` folder with proper hyperlink management.

### New Input Structure

```
QAfolder/
├── John_Quest/                    # Folder name = {Username}_{Category}
│   ├── LQA_Quest.xlsx             # Only 1 xlsx per folder (any name)
│   ├── 10034.png                  # Images referenced in xlsx
│   ├── 919193.png
│   └── screenshot_ui.png
├── Alice_Quest/
│   ├── LQA_Quest.xlsx
│   ├── 10034.png                  # SAME NAME as John's! (duplicate)
│   └── bug_report.png
├── John_Knowledge/
│   ├── LQA_Knowledge.xlsx
│   └── 55221.png
└── Bob_Item/
    ├── LQA_Item.xlsx
    └── item_bug.png
```

**Key Points:**
- Folder name format: `{Username}_{Category}`
- Exactly 1 `.xlsx` file per folder (name doesn't matter)
- Images are hyperlinked in xlsx with **RELATIVE paths** (e.g., `10034.png` or `./10034.png`)
- Same image filename can exist in different user folders (duplicates)

### New Output Structure

```
Masterfolder/
├── Master_Quest.xlsx              # Hyperlinks point to Images/
├── Master_Knowledge.xlsx
├── Master_Item.xlsx
├── Master_Node.xlsx
├── Master_System.xlsx
└── Images/                        # ALL images consolidated here
    ├── John_Quest_10034.png       # Renamed: {Username}_{Category}_{Original}
    ├── John_Quest_919193.png
    ├── John_Quest_screenshot_ui.png
    ├── Alice_Quest_10034.png      # Alice's 10034.png (no collision)
    ├── Alice_Quest_bug_report.png
    ├── John_Knowledge_55221.png
    └── Bob_Item_item_bug.png
```

### Duplicate Image Naming Strategy

**Problem:** Multiple users may have images with the same filename (e.g., `10034.png`).

**Solution:** Prefix every image with `{Username}_{Category}_`

```python
def get_unique_image_name(username, category, original_filename):
    """
    Generate unique image filename to avoid collisions.

    Input:  "10034.png" from John_Quest folder
    Output: "John_Quest_10034.png"
    """
    return f"{username}_{category}_{original_filename}"
```

**Why this works:**
- Username + Category is always unique per QA file
- Preserves original filename for traceability
- No collision possible even with 100+ testers

### Paired Columns: COMMENT + SCREENSHOT per User

**Master file structure:**
```
Original | ENG | ... | COMMENT_John | SCREENSHOT_John | COMMENT_Alice | SCREENSHOT_Alice | ...
```

**Why paired:**
- Comment and screenshot are related (user explains issue + shows it)
- One hyperlink per cell (Excel limitation)
- Easy to see who reported what with visual evidence

**Column creation order:**
1. Find or create `COMMENT_{User}` column
2. Create `SCREENSHOT_{User}` immediately after it

### Hyperlink Transformation Logic

**Before (in QA xlsx):** Relative path to local folder
```
=HYPERLINK("10034.png", "View")
=HYPERLINK("./screenshot.png", "View")
```

**After (in Master xlsx):** Relative path to Images/ folder
```
=HYPERLINK("Images/John_Quest_10034.png", "View")
=HYPERLINK("Images/John_Quest_screenshot.png", "View")
```

**Implementation:**

```python
import os
import shutil
from openpyxl.worksheet.hyperlink import Hyperlink

def process_images_and_hyperlinks(qa_folder_path, username, category, master_ws, images_folder):
    """
    1. Find all images in QA folder
    2. Copy to Images/ with unique names
    3. Update hyperlinks in master worksheet
    """
    qa_folder = Path(qa_folder_path)
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

    # Build mapping: original_name -> new_name
    image_mapping = {}

    for img_file in qa_folder.iterdir():
        if img_file.suffix.lower() in image_extensions:
            original_name = img_file.name
            new_name = f"{username}_{category}_{original_name}"

            # Copy image to Images/ folder
            dest_path = images_folder / new_name
            shutil.copy2(img_file, dest_path)

            image_mapping[original_name] = new_name

    # Update hyperlinks in worksheet
    update_hyperlinks(master_ws, image_mapping)

    return image_mapping


def update_hyperlinks(ws, image_mapping):
    """
    Scan worksheet for hyperlinks pointing to images.
    Update them to point to Images/{new_name}.
    """
    for row in ws.iter_rows():
        for cell in row:
            if cell.hyperlink:
                target = cell.hyperlink.target
                if target:
                    # Extract filename from relative path
                    original_name = os.path.basename(target)

                    if original_name in image_mapping:
                        new_name = image_mapping[original_name]
                        cell.hyperlink.target = f"Images/{new_name}"
```

### File Discovery Changes

**Old logic:** Look for `{Username}_{Category}.xlsx` files directly

**New logic:** Look for `{Username}_{Category}/` folders, find xlsx inside

```python
def discover_qa_folders(qa_folder):
    """
    Find all QA folders and extract metadata.

    Returns: List of dicts with {folder_path, xlsx_path, username, category, images}
    """
    results = []

    for folder in Path(qa_folder).iterdir():
        if not folder.is_dir():
            continue

        # Skip hidden/temp folders
        if folder.name.startswith('.') or folder.name.startswith('~'):
            continue

        # Parse folder name: {Username}_{Category}
        parts = folder.name.split('_')
        if len(parts) < 2:
            print(f"WARN: Invalid folder name format: {folder.name}")
            continue

        username = parts[0]
        category = '_'.join(parts[1:])  # Handle categories with underscores

        # Find xlsx file (must be exactly 1)
        xlsx_files = list(folder.glob("*.xlsx"))
        xlsx_files = [f for f in xlsx_files if not f.name.startswith("~$")]

        if len(xlsx_files) == 0:
            print(f"WARN: No xlsx in folder: {folder.name}")
            continue
        if len(xlsx_files) > 1:
            print(f"WARN: Multiple xlsx in folder: {folder.name}, using first")

        xlsx_path = xlsx_files[0]

        # Find images
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        images = [f for f in folder.iterdir()
                  if f.suffix.lower() in image_extensions]

        results.append({
            "folder_path": folder,
            "xlsx_path": xlsx_path,
            "username": username,
            "category": category,
            "images": images
        })

    return results
```

### Updated Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INPUT                                      │
├─────────────────────────────────────────────────────────────────────┤
│  QAfolder/                                                           │
│  ├── John_Quest/           ─┐                                       │
│  │   ├── LQA.xlsx           │                                       │
│  │   └── *.png              ├─→ Group by Category                   │
│  ├── Alice_Quest/          ─┘                                       │
│  │   ├── LQA.xlsx                                                   │
│  │   └── *.png                                                      │
│  └── ...                                                            │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PROCESSING                                   │
├─────────────────────────────────────────────────────────────────────┤
│  For each category:                                                  │
│                                                                      │
│  1. Load/Create Master_{Category}.xlsx                              │
│  2. Create Masterfolder/Images/ if not exists                       │
│  3. For each QA folder in category:                                 │
│     a. Extract username from folder name                            │
│     b. Find xlsx and images in folder                               │
│     c. Copy images → Images/{Username}_{Category}_{filename}        │
│     d. Process xlsx:                                                │
│        - Update COMMENT_{user} columns                              │
│        - Transform hyperlinks to new image paths                    │
│     e. Calculate completion stats                                   │
│  4. Create/Update STATUS sheet                                      │
│  5. Save Master file                                                │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Masterfolder/                                                       │
│  ├── Master_Quest.xlsx      # Hyperlinks → Images/John_Quest_*.png  │
│  ├── Master_Knowledge.xlsx                                          │
│  ├── Master_Item.xlsx                                               │
│  ├── Master_Node.xlsx                                               │
│  ├── Master_System.xlsx                                             │
│  └── Images/                # ALL images with unique names           │
│      ├── John_Quest_10034.png                                       │
│      ├── Alice_Quest_10034.png                                      │
│      └── ...                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Edge Cases

| Case | Handling |
|------|----------|
| No images in folder | Process xlsx normally, no image copying |
| Image in xlsx not found in folder | Log warning, skip hyperlink update (orange color) |
| Hyperlink to external URL | Skip (only process local file paths) |
| Very long image filename | Truncate original name, keep prefix |
| Image already exists in Images/ | Overwrite (same user re-submitting) |
| Broken hyperlink in xlsx | Log warning, preserve as-is |
| Unlinked images in folder | **Currently copied anyway** (see Future Improvements) |

### Future Improvements

| Feature | Description | Priority |
|---------|-------------|----------|
| Smart image copying | Only copy images that are actually hyperlinked in xlsx | LOW |
| CLI arguments | `--dry-run`, `--backup` flags | LOW |

### MasterUI Removal

**REMOVED:** The MasterUI feature that collected all screenshot issues into a separate file.

**Reason:** No longer needed. All images are now properly compiled into `Images/` folder with hyperlinks preserved in their respective master files.

---

---

## UPCOMING: Migration Support (Phase 10) 🚧

**Goal:** Transfer tester work when QA file structure changes (new columns, row reorder)

**Status:** PLANNED - See [MIGRATION_PLAN.md](MIGRATION_PLAN.md)

### GUI Addition

```
┌─────────────────────────────────────────────────────────────────┐
│                    QA Excel Compiler                             │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────────────────┐   ┌─────────────────────────┐     │
│   │   Transfer QA Files     │   │   Build Masterfiles     │     │
│   └─────────────────────────┘   └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### New Folders

| Folder | Purpose |
|--------|---------|
| `QAfolderOLD/` | OLD structure QA files (with tester work) |
| `QAfolderNEW/` | NEW structure QA files (empty) |
| `QAfolder/` | Working folder (output of transfer, input for build) |

### Matching Strategy

**2-step cascade:**
1. Translation + STRINGID → exact match
2. Translation only → content match

### Datasheet Generators

Scripts that create QA source files moved to `datasheet_generators/`:
- `fullquest15.py` - Quest data
- `fullknowledge14.py` - Knowledge data
- `fullitem25.py` - Item data
- `fullregion7.py` - Region data
- `fullcharacter1.py` - Character data
- `fullgimmick1.py` - Gimmick data

---

*WIP created 2025-12-30*
*Updated 2025-12-30: Added StringID parsing, column styling, future features*
*Updated 2026-01-02: Added IMAGE COMPILATION SYSTEM - folder-based input, centralized Images/ output, duplicate naming strategy*
*Updated 2026-01-03: Clean comment format with --- delimiter, unified blue styling for COMMENT/SCREENSHOT*
*Updated 2026-01-09: Added Phase 10 Migration Support section, datasheet_generators folder*
