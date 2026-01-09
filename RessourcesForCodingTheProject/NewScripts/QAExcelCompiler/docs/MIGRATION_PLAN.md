# QA File Migration - Implementation Plan

**Created:** 2026-01-09
**Status:** READY FOR IMPLEMENTATION
**Priority:** P0 (enables structure changes without data loss)

---

## Problem Statement

When QA file structures change (new columns, row reorder, new rows), we need to:
1. **Transfer tester work** from OLD QA files to NEW QA files
2. **Preserve manager status** from OLD master files to NEW master files

Without this, all tester comments and manager statuses would be lost on structure change.

---

## Solution: Two-Phase Migration with GUI

### GUI Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    QA Excel Compiler                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────┐   ┌─────────────────────────┐     │
│   │   Transfer QA Files     │   │   Build Masterfiles     │     │
│   │                         │   │                         │     │
│   │  QAfolderOLD → QAfolder │   │  QAfolder → Masterfolder│     │
│   └─────────────────────────┘   └─────────────────────────┘     │
│                                                                  │
│   Status: Ready                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Button 1: Transfer QA Files**
- Reads OLD QA files from `QAfolderOLD/`
- Reads NEW QA files from `QAfolderNEW/`
- Matches by `{Name}_{Category}` folder name
- Transfers COMMENT/STATUS/SCREENSHOT using content matching
- Outputs to `QAfolder/` (ready for master build)

**Button 2: Build Masterfiles**
- Existing compile logic
- Reads from `QAfolder/`
- Preserves manager status from OLD master files
- Outputs to `Masterfolder_EN/` and `Masterfolder_CN/`

---

## Folder Structure

```
QAExcelCompiler/
├── compile_qa.py              # Main script with GUI
├── QAfolderOLD/               # OLD structure QA files (input)
│   ├── John_Quest/
│   │   ├── LQA_Quest.xlsx     # Old structure
│   │   └── *.png
│   ├── Alice_Knowledge/
│   └── ...
├── QAfolderNEW/               # NEW structure QA files (input)
│   ├── John_Quest/
│   │   ├── LQA_Quest.xlsx     # New structure (empty comments)
│   │   └── *.png
│   ├── Alice_Knowledge/
│   └── ...
├── QAfolder/                  # WORKING folder (output of transfer, input for build)
│   ├── John_Quest/
│   │   ├── LQA_Quest.xlsx     # New structure WITH transferred comments
│   │   └── *.png
│   └── ...
├── Masterfolder_EN/           # EN master output
├── Masterfolder_CN/           # CN master output
└── LQA_Tester_ProgressTracker.xlsx
```

---

## Phase 1: Transfer QA Files

### Matching Algorithm (2-Step Cascade)

```python
def find_matching_row(old_row, new_ws):
    """
    Find matching row in NEW file for OLD row data.

    Step 1: Try Translation + STRINGID match (exact)
    Step 2: Fall back to Translation only (content match)
    """
    old_translation = old_row["translation"]  # ENG or Original column
    old_stringid = old_row["stringid"]

    # Step 1: Exact match (Translation + STRINGID)
    for new_row in new_ws:
        if (new_row["translation"] == old_translation and
            new_row["stringid"] == old_stringid):
            return new_row

    # Step 2: Content match (Translation only)
    for new_row in new_ws:
        if new_row["translation"] == old_translation:
            return new_row

    return None  # No match found
```

### Transfer Process

```
For each {Name}_{Category} in QAfolderOLD:
  1. Find matching folder in QAfolderNEW
  2. Load OLD xlsx, extract:
     - COMMENT values (with their row content)
     - STATUS values
     - SCREENSHOT hyperlinks
  3. Load NEW xlsx
  4. For each OLD row with data:
     a. Find matching NEW row (cascade match)
     b. Copy COMMENT, STATUS, SCREENSHOT to NEW row
  5. Save to QAfolder/{Name}_{Category}/
  6. Copy images from OLD folder to QAfolder/
```

### What Gets Transferred

| Column | Transfer? | Notes |
|--------|-----------|-------|
| STATUS | YES | ISSUE/NO ISSUE/BLOCKED |
| COMMENT | YES | Full text with metadata |
| SCREENSHOT | YES | Hyperlink (images copied separately) |
| STRINGID | NO | Comes from NEW file |
| Original/ENG | NO | Comes from NEW file |

### Column Detection (Dynamic)

The matching algorithm needs to find STRINGID and Translation columns dynamically since headers vary by category.

**STRINGID Column:**
- Header: `STRINGID` (exact, all categories use this)

**Translation Column by Category:**

| Category | Language | Translation Column |
|----------|----------|-------------------|
| **Quest, Knowledge, Character, Region** | ENG | Col 2: `ENG` or `English (ENG)` |
| **Quest, Knowledge, Character, Region** | Other | Col 3: `{LANG}` or `Translation ({LANG})` |
| **Item** | ENG | Col 5-6: `ItemName(ENG)`, `ItemDesc(ENG)` |
| **Item** | Other | Col 7-8: `ItemName({LANG})`, `ItemDesc({LANG})` |

**File structure examples:**

```
Quest/Knowledge/Character/Region (ENG):
  Col 1: Original (KR)
  Col 2: ENG ← Translation
  Col 3+: StringKey, Command, STATUS, COMMENT, STRINGID, SCREENSHOT

Quest/Knowledge/Character/Region (Other language, e.g. FRE):
  Col 1: Original (KR)
  Col 2: ENG (reference)
  Col 3: FRE ← Translation
  Col 4+: StringKey, Command, STATUS, COMMENT, STRINGID, SCREENSHOT

Item (ENG):
  Col 1-2: Filename, SubGroup
  Col 3-4: ItemName(KOR), ItemDesc(KOR)
  Col 5-6: ItemName(ENG), ItemDesc(ENG) ← Translation
  Col 7+: ItemKey, STATUS, COMMENT, STRINGID, SCREENSHOT

Item (Other language, e.g. FRE):
  Col 1-2: Filename, SubGroup
  Col 3-4: ItemName(KOR), ItemDesc(KOR)
  Col 5-6: ItemName(ENG), ItemDesc(ENG) (reference)
  Col 7-8: ItemName(FRE), ItemDesc(FRE) ← Translation
  Col 9+: ItemKey, STATUS, COMMENT, STRINGID, SCREENSHOT
```

**Implementation:**

```python
def get_translation_column(category, is_english):
    """
    Get the translation column index based on category and language.

    For Item: Uses ItemName column (primary text for matching)
    For Others: Uses the main translation column
    """
    if category == "Item":
        return 5 if is_english else 7  # ItemName(ENG) or ItemName({LANG})
    else:
        return 2 if is_english else 3  # ENG or {LANG}

def is_english_file(xlsx_path):
    """Detect if file is English based on filename or content."""
    name = xlsx_path.name.upper()
    return "ENG" in name or "_EN" in name or not any(
        lang in name for lang in ["FRE", "ZHO", "JPN", "DEU", "SPA"]
    )
```

**Reference:** See `datasheet_generators/*.py` for exact column structures per category.

### Transfer Report (Terminal Output)

After transfer completes, print a summary report showing success rate per tester:

```
═══════════════════════════════════════════════════════════════════════════════
                              TRANSFER REPORT
═══════════════════════════════════════════════════════════════════════════════

Tester              Category      Total   STRINGID+Trans   Trans Only   Success %
───────────────────────────────────────────────────────────────────────────────
김동헌              Quest           245            230           12       98.8%
김동헌              Knowledge       189            185            4      100.0%
황하연              Quest           245            220           20       97.9%
황하연              Item            312            290           15       97.8%
김춘애              Quest           245            198           30       93.1%
최문석              Knowledge       189            150           25       92.6%
...
───────────────────────────────────────────────────────────────────────────────
TOTAL                              1425           1273          106       96.8%
═══════════════════════════════════════════════════════════════════════════════

Legend:
  Total          = Rows with COMMENT or STATUS in OLD file (work to transfer)
  STRINGID+Trans = Matched by STRINGID + Translation text (exact match)
  Trans Only     = Matched by Translation text only (fallback match)
  Unmatched      = Total - STRINGID+Trans - Trans Only (not transferred)
  Success %      = (STRINGID+Trans + Trans Only) / Total × 100
```

**Report Data Structure:**

```python
transfer_stats = {
    ("김동헌", "Quest"): {
        "total": 245,           # Rows with work in OLD file
        "stringid_match": 230,  # Matched by STRINGID + Translation
        "trans_only": 12,       # Matched by Translation only
        "unmatched": 3,         # Could not find in NEW file
    },
    ...
}

def print_transfer_report(stats):
    """Print formatted transfer report to terminal."""
    print("═" * 79)
    print("                              TRANSFER REPORT")
    print("═" * 79)
    print()
    print(f"{'Tester':<20}{'Category':<14}{'Total':>7}{'STRINGID+Trans':>17}{'Trans Only':>13}{'Success %':>12}")
    print("─" * 79)

    grand_total = grand_stringid = grand_trans = 0

    for (tester, category), data in sorted(stats.items()):
        total = data["total"]
        stringid = data["stringid_match"]
        trans = data["trans_only"]
        success = (stringid + trans) / total * 100 if total > 0 else 0

        print(f"{tester:<20}{category:<14}{total:>7}{stringid:>17}{trans:>13}{success:>11.1f}%")

        grand_total += total
        grand_stringid += stringid
        grand_trans += trans

    print("─" * 79)
    grand_success = (grand_stringid + grand_trans) / grand_total * 100 if grand_total > 0 else 0
    print(f"{'TOTAL':<20}{'':<14}{grand_total:>7}{grand_stringid:>17}{grand_trans:>13}{grand_success:>11.1f}%")
    print("═" * 79)
```

---

## Phase 2: Build Masterfiles (Enhanced)

### Manager Status Preservation

```
1. Load OLD Masterfolder_EN/ and Masterfolder_CN/
2. Build lookup table:
   KEY: TESTER_COMMENT (extracted text, no timestamp)
   VALUE: MANAGER_STATUS (FIXED/REPORTED/CHECKING)

3. Build NEW master files from QAfolder/
4. For each COMMENT_{User} cell:
   a. Extract comment text (existing regex)
   b. Lookup in manager status table
   c. If found, set STATUS_{User} = matched status
5. Post-processing (hiding, styling)
```

### Comment Text Extraction (Existing Logic)

```python
def extract_comment_text(full_comment):
    """
    Extract original comment text from formatted comment.

    Input:  "Translation issue\n---\nstringid:\n10001\n(updated: 251230 1500)"
    Output: "Translation issue"
    """
    if "\n---\n" in full_comment:
        return full_comment.split("\n---\n")[0].strip()
    return full_comment.strip()
```

---

## Implementation Steps

### Step 1: Add GUI Framework

```python
import tkinter as tk
from tkinter import ttk, messagebox

class QACompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("QA Excel Compiler")
        self.root.geometry("400x200")

        # Transfer button
        ttk.Button(
            root,
            text="Transfer QA Files\n(QAfolderOLD → QAfolder)",
            command=self.transfer_qa_files
        ).pack(pady=20, padx=40, fill='x')

        # Build button
        ttk.Button(
            root,
            text="Build Masterfiles\n(QAfolder → Masterfolder)",
            command=self.build_masterfiles
        ).pack(pady=20, padx=40, fill='x')

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var).pack(pady=10)

    def transfer_qa_files(self):
        # Phase 1 logic
        pass

    def build_masterfiles(self):
        # Phase 2 logic (existing compile + manager preservation)
        pass
```

### Step 2: Implement Transfer Logic

```python
def transfer_qa_files():
    """
    Transfer tester work from QAfolderOLD to QAfolderNEW, output to QAfolder.
    """
    old_folders = discover_qa_folders(SCRIPT_DIR / "QAfolderOLD")
    new_folders = discover_qa_folders(SCRIPT_DIR / "QAfolderNEW")

    # Match by Name_Category
    for old_folder in old_folders:
        name_cat = f"{old_folder['username']}_{old_folder['category']}"

        # Find matching NEW folder
        new_folder = next(
            (f for f in new_folders
             if f"{f['username']}_{f['category']}" == name_cat),
            None
        )

        if not new_folder:
            print(f"WARN: No NEW folder for {name_cat}")
            continue

        # Transfer data
        transfer_folder_data(old_folder, new_folder, output_dir=SCRIPT_DIR / "QAfolder")
```

### Step 3: Implement Manager Status Preservation

```python
def collect_manager_status_by_comment(master_folder):
    """
    Build lookup: comment_text → manager_status
    """
    lookup = {}  # {comment_text: {user: status}}

    for master_file in master_folder.glob("Master_*.xlsx"):
        wb = load_workbook(master_file)
        for ws in wb.worksheets:
            if ws.title == "STATUS":
                continue

            # Find COMMENT_{User} and STATUS_{User} columns
            for col in range(1, ws.max_column + 1):
                header = ws.cell(1, col).value
                if header and header.startswith("COMMENT_"):
                    user = header.replace("COMMENT_", "")
                    status_col = find_column_by_header(ws, f"STATUS_{user}")

                    if status_col:
                        for row in range(2, ws.max_row + 1):
                            comment = ws.cell(row, col).value
                            status = ws.cell(row, status_col).value

                            if comment and status:
                                comment_text = extract_comment_text(str(comment))
                                if comment_text not in lookup:
                                    lookup[comment_text] = {}
                                lookup[comment_text][user] = status

    return lookup
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| OLD folder not in NEW | Skip with warning |
| NEW folder not in OLD | Process normally (no transfer needed) |
| Row in OLD not found in NEW | Skip with warning, log unmatched |
| Multiple matches for translation | Use first match |
| Empty QAfolderOLD | Skip transfer, just copy QAfolderNEW → QAfolder |
| Empty QAfolderNEW | Error: "No NEW files to transfer to" |

---

## Testing Checklist

- [ ] Transfer: John_Quest OLD → NEW (same rows, different columns)
- [ ] Transfer: Alice_Knowledge OLD → NEW (some rows removed in NEW)
- [ ] Transfer: Bob_Item OLD → NEW (new rows added in NEW)
- [ ] Manager status preservation: FIXED status survives rebuild
- [ ] Manager status preservation: REPORTED status survives rebuild
- [ ] Images copied correctly from OLD to QAfolder
- [ ] Progress tracker rebuilt correctly after migration

---

## File Changes Required

| File | Change |
|------|--------|
| compile_qa.py | Add GUI, transfer logic, manager preservation |
| README.md | Document new folder structure |
| ROADMAP.md | Add Phase 10: Migration Support |

---

## Summary

```
BEFORE MIGRATION:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ QAfolderOLD  │     │ QAfolderNEW  │     │ Old Master   │
│ (has work)   │     │ (empty)      │     │ (has status) │
└──────────────┘     └──────────────┘     └──────────────┘

AFTER TRANSFER:
┌──────────────┐
│   QAfolder   │  ← NEW structure + OLD work
└──────────────┘

AFTER BUILD:
┌──────────────┐
│ New Master   │  ← NEW structure + OLD work + OLD manager status
└──────────────┘
```

---

*Plan created: 2026-01-09*
*Updated: 2026-01-09 - Added Column Detection section and Transfer Report terminal output*
*Updated: 2026-01-09 - Detailed translation column positions per category (Item uses col 5-6/7-8, others use col 2/3)*
*Based on user requirements for structure migration without data loss*
