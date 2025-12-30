# QA Excel Compiler

**Standalone script to compile QA tester Excel files into master sheets.**

---

## What It Does

1. **Collects** QA Excel files from `QAfolder/`
2. **Groups** them by category (Quest, Knowledge, Item, Node, System)
3. **Compiles** into master files with:
   - `COMMENT_{Username}` columns for each tester
   - `STATUS` sheet tracking completion % per user
4. **Saves** to `Masterfolder/`

---

## Installation

```bash
# 1. Navigate to project
cd miniprojects/qa_excel_compiler

# 2. Install dependencies (just openpyxl)
pip install -r requirements.txt
```

---

## Usage

### 1. Drop QA files into `QAfolder/`

**Filename format:** `{Username}_{Category}.xlsx`

Examples:
- `John_Quest.xlsx`
- `Alice_Knowledge.xlsx`
- `Bob_Item.xlsx`

**Valid categories:** Quest, Knowledge, Item, Node, System

### 2. Run the compiler

```bash
python3 compile_qa.py
```

### 3. Check `Masterfolder/` for results

Output files:
- `Master_Quest.xlsx`
- `Master_Knowledge.xlsx`
- `Master_Item.xlsx`
- `Master_Node.xlsx`
- `Master_System.xlsx`

---

## Folder Structure

```
qa_excel_compiler/
├── compile_qa.py         # Main script (standalone)
├── requirements.txt      # Dependencies (openpyxl)
├── README.md             # This file
├── QAfolder/             # DROP QA FILES HERE
│   ├── John_Quest.xlsx
│   ├── Alice_Quest.xlsx
│   └── ...
├── Masterfolder/         # OUTPUT GOES HERE
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   └── ...
└── docs/
    ├── ROADMAP.md        # Project plan
    └── WIP.md            # Technical details
```

---

## Features

### Comment Compilation

Each user gets their own column: `COMMENT_John`, `COMMENT_Alice`, etc.

**Comment format with timestamp:**
```
"The translation is wrong" (date: 251230 1445)

"Previous comment" (date: 251229 1000)
```

- New comments appear on top
- Old comments preserved below
- Duplicate detection prevents re-adding same comment

### Status Tracking

Each master file gets a `STATUS` sheet:

| User  | Sheet1 | Sheet3 | Total |
|-------|--------|--------|-------|
| John  | 85%    | 100%   | 92.5% |
| Alice | 50%    | 75%    | 62.5% |

Completion % = rows with comments / total rows

### Re-run Safe

- Running multiple times won't duplicate comments
- New comments from QA files are appended
- Existing comments preserved

---

## Input File Format

QA files should have these columns:

| Column | Description | Used |
|--------|-------------|------|
| A - Original | Korean source | NO |
| B - ENG | English translation | NO |
| C - StringKey | Identifier | NO |
| D - Command | Dev commands | NO |
| E - STATUS | QA status | NO (future) |
| F - COMMENT | QA feedback | **YES** |
| G - SCREENSHOT | Hyperlink | NO (ignored) |

**Row matching:** By row index (all QA files for same category have identical structure)

---

## Example

**Before (QA files):**

`John_Quest.xlsx`:
| Original | ENG | COMMENT |
|----------|-----|---------|
| 기습 | Ambush | Looks good |
| 낯선 땅 | Strange Lands | Typo here |

`Alice_Quest.xlsx`:
| Original | ENG | COMMENT |
|----------|-----|---------|
| 기습 | Ambush | |
| 낯선 땅 | Strange Lands | Fixed now |

**After (Master file):**

`Master_Quest.xlsx`:
| Original | ENG | COMMENT_John | COMMENT_Alice |
|----------|-----|--------------|---------------|
| 기습 | Ambush | "Looks good" (date: 251230 1500) | |
| 낯선 땅 | Strange Lands | "Typo here" (date: 251230 1500) | "Fixed now" (date: 251230 1502) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No valid QA files found" | Check filename format: `Username_Category.xlsx` |
| "Unknown category" | Use: Quest, Knowledge, Item, Node, System |
| ModuleNotFoundError | Run: `pip install -r requirements.txt` |
| Permission error | Close Excel files before running |

---

## Technical Notes

- Uses `openpyxl` for Excel handling (preserves formatting)
- Row matching by index (not StringKey)
- Columns inserted after existing COMMENT columns
- STATUS sheet recreated on each run

---

*Created: 2025-12-30*
