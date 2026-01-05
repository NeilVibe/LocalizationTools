# QA Excel Compiler

**Standalone script to compile QA tester Excel files into master sheets.**

---

## What It Does

1. **Collects** QA Excel files from `QAfolder/`
2. **Groups** them by category (Quest, Knowledge, Item, Node, System)
3. **Compiles** into master files with:
   - `COMMENT_{Username}` columns for each tester
   - `STATUS` sheet tracking completion % per user
4. **Generates Progress Tracker** with:
   - **DAILY** tab - per-user daily progress based on file modification dates
   - **TOTAL** tab - cumulative stats per user across all categories
   - **GRAPHS** tab - visual charts for progress tracking
5. **Saves** to `Masterfolder/`

---

## Installation

```bash
# 1. Navigate to project
cd RessourcesForCodingTheProject/NewScripts/QAExcelCompiler

# 2. Install dependencies (just openpyxl)
pip install -r requirements.txt
```

---

## Usage

### 1. Drop QA folders into `QAfolder/`

**Folder format:** `{Username}_{Category}/` containing xlsx + images

Examples:
```
QAfolder/
├── John_Quest/
│   ├── LQA_Quest.xlsx      # Any xlsx name works (only 1 per folder)
│   ├── 10034.png           # Images referenced in xlsx
│   └── screenshot.png
├── Alice_Quest/
│   ├── LQA_Quest.xlsx
│   └── 10034.png           # Same name OK - will be renamed
└── Bob_Item/
    ├── LQA_Item.xlsx
    └── bug.png
```

**Valid categories:** Quest, Knowledge, Item, Region, System, Character

### 2. Run the compiler

```bash
python3 compile_qa.py
```

### 3. Check `Masterfolder/` for results

Output structure:
```
Masterfolder/
├── Master_Quest.xlsx              # QA data + STATUS per category
├── Master_Knowledge.xlsx
├── Master_Item.xlsx
├── Master_Region.xlsx
├── Master_System.xlsx
├── Master_Character.xlsx
├── LQA_Tester_ProgressTracker.xlsx  # Combined progress tracker
│   ├── DAILY                      # Daily progress per user
│   ├── TOTAL                      # Cumulative stats
│   └── GRAPHS                     # Visual charts
└── Images/                        # ALL images consolidated
    ├── John_Quest_10034.png       # {User}_{Category}_{original}
    └── ...
```

---

## Folder Structure

```
QAExcelCompiler/
├── compile_qa.py         # Main script (standalone)
├── requirements.txt      # Dependencies (openpyxl)
├── README.md             # This file
├── QAfolder/             # DROP QA FOLDERS HERE
│   ├── John_Quest/       # {Username}_{Category}/
│   │   ├── LQA.xlsx      # 1 xlsx per folder
│   │   └── *.png         # Images with relative hyperlinks
│   ├── Alice_Quest/
│   │   ├── LQA.xlsx
│   │   └── *.png
│   └── ...
├── Masterfolder/         # OUTPUT GOES HERE
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   ├── ...
│   ├── LQA_UserProgress_Tracker.xlsx  # Progress tracker
│   └── Images/           # ALL images consolidated
│       ├── John_Quest_10034.png
│       └── Alice_Quest_10034.png
└── docs/
    ├── ROADMAP.md        # Project plan
    ├── WIP.md            # Technical details
    ├── DAILY_STATUS_PLAN.md   # Tracker implementation plan
    └── MANAGER_STATUS_PLAN.md # Manager status feature plan
```

---

## Features

### Comment + Screenshot Compilation

Each user gets **paired columns**: `COMMENT_John` + `SCREENSHOT_John`, etc.

```
... | COMMENT_John | SCREENSHOT_John | COMMENT_Alice | SCREENSHOT_Alice | ...
```

- Comment: QA feedback text (with timestamp)
- Screenshot: Hyperlink to `Images/{User}_{Category}_{filename}.png`

**Unified blue styling:**
- Both COMMENT and SCREENSHOT cells use light blue fill + blue border
- Headers: Light blue (`87CEEB`) with bold text
- Cells: Light blue fill (`E6F3FF`) when updated
- Only applies on NEW updates (preserves custom colors on re-runs)

**Comment format with timestamp:**
```
The translation is wrong
---
stringid:
10001
(updated: 251230 1445)
```

- Clean format: comment text, delimiter, metadata
- `---` delimiter separates comment from metadata
- Duplicate detection: splits on `---` to compare original text

### Status Tracking

Each master file gets a `STATUS` sheet as the **first tab** (yellow header):

| User  | Completion % | Total Rows | ISSUE # | NO ISSUE % | BLOCKED % |
|-------|--------------|------------|---------|------------|-----------|
| John  | 80.0%        | 5          | 1       | 40.0%      | 20.0%     |
| Mary  | 100.0%       | 5          | 1       | 80.0%      | 0.0%      |

**Columns explained:**
- **Completion %**: Rows with STATUS filled (ISSUE/NO ISSUE/BLOCKED) / Total rows
- **Total Rows**: Number of rows in all sheets combined
- **ISSUE #**: Raw count of ISSUE statuses
- **NO ISSUE %**: Percentage of NO ISSUE statuses
- **BLOCKED %**: Percentage of BLOCKED statuses

**Valid STATUS values:** ISSUE, NO ISSUE, BLOCKED

### Re-run Safe

- Running multiple times won't duplicate comments
- New comments from QA files are appended
- Existing comments preserved
- **Team's custom formatting preserved** (colors added to cells won't be overwritten)
- **Hidden columns stay hidden** (column visibility preserved on updates)
- **Manager status values preserved** (FIXED/REPORTED/CHECKING entries persist on re-compile)

### Manager Status Workflow

Managers can track issue resolution in Master files using `STATUS_{User}` columns:

```
| COMMENT_John | STATUS_John | SCREENSHOT_John | COMMENT_Alice | STATUS_Alice | ...
|--------------|-------------|-----------------|---------------|--------------|-----
| "Bug here"   | FIXED       | img.png         | "Typo found"  | REPORTED     |
| "Wrong text" |             |                 | "Missing"     | CHECKING     |
```

**Valid Manager STATUS values:**
- **FIXED**: Issue has been fixed
- **REPORTED**: Issue has been reported to dev team
- **CHECKING**: Issue is being investigated
- *(empty)*: No manager action yet

**Column styling:**
- `STATUS_{User}` headers: Light green (`90EE90`) background
- FIXED: Forest green text
- REPORTED: Orange text
- CHECKING: Blue text

**Workflow:**
1. Compiler creates Master files with empty `STATUS_{User}` columns
2. Manager opens Master file in Excel
3. Manager enters FIXED/REPORTED/CHECKING for each issue
4. On next compile, these values are **preserved automatically**
5. Manager stats appear in Progress Tracker (Fixed, Reported, Checking, Pending)

### Image Consolidation

All images from QA folders are copied to `Masterfolder/Images/` with unique names:

```
Images/
├── John_Quest_10034.png       # {User}_{Category}_{original}
├── Alice_Quest_10034.png      # No collision with John's file
├── John_Quest_screenshot.png
└── ...
```

**Features:**
- **Unique naming** - `{Username}_{Category}_{original}` prevents duplicates
- **Hyperlinks updated** - Automatically point to new `Images/` location
- **Click to open** - Hyperlinks work directly from master file

### User Progress Tracker

A separate `LQA_Tester_ProgressTracker.xlsx` file tracks progress across ALL categories:

**DAILY Tab** - Shows daily progress per user:
```
┌─────────────────────────────────────────────────────────────────┐
│                      DAILY PROGRESS                             │
├─────────┬───────────────┬───────────────┬───────────────────────┤
│         │     Alice     │     Bob       │      John             │
├─────────┼───────┬───────┼───────┬───────┼───────┬───────────────┤
│  Date   │ Done  │Issues │ Done  │Issues │ Done  │ Issues        │
├─────────┼───────┼───────┼───────┼───────┼───────┼───────────────┤
│  01/03  │  --   │  --   │  --   │  --   │  45   │   8           │
│  01/04  │  32   │   5   │  --   │  --   │  --   │  --           │
│  01/05  │  --   │  --   │  28   │   6   │  15   │   3           │
├─────────┼───────┼───────┼───────┼───────┼───────┼───────────────┤
│  TOTAL  │  32   │   5   │  28   │   6   │  60   │  11           │
└─────────┴───────┴───────┴───────┴───────┴───────┴───────────────┘
```

- **Date**: From file modification time (auto-detected)
- **Done**: Rows with STATUS filled (ISSUE + NO ISSUE + BLOCKED)
- **Issues**: Rows with STATUS = "ISSUE"
- **`--`**: No submission that day

**TOTAL Tab** - Cumulative stats per user (includes Manager Stats):

| User  | Completion % | Total | Issues | No Issue | Blocked | Fixed | Reported | Checking | Pending |
|-------|--------------|-------|--------|----------|---------|-------|----------|----------|---------|
| Alice | 100.0%       | 32    | 5      | 25       | 2       | 3     | 1        | 0        | 1       |
| Bob   | 95.0%        | 28    | 6      | 20       | 2       | 2     | 2        | 1        | 1       |
| John  | 98.0%        | 60    | 11     | 45       | 4       | 5     | 3        | 2        | 1       |
| TOTAL | 97.5%        | 120   | 22     | 90       | 8       | 10    | 6        | 3        | 3       |

**Manager Stats columns:**
- **Fixed**: Count of issues marked as FIXED by manager
- **Reported**: Count of issues marked as REPORTED by manager
- **Checking**: Count of issues marked as CHECKING by manager
- **Pending**: Issues with no manager action (Issues - Fixed - Reported - Checking)

**GRAPHS Tab** - Visual charts:
- **Daily Progress Chart**: Bar chart showing Done per user per day
- **User Completion Chart**: Horizontal bar chart showing Completion % per user
- **Issue Resolution Chart**: Pie chart showing Fixed vs Reported vs Checking vs Pending

**Key Features:**
- **File modification date** determines which day work is tracked
- **Combines all categories** (Quest, Knowledge, Item, etc.) per user
- **REPLACE mode**: Re-running updates existing entries (no duplicates)
- **Persistent data**: Hidden `_DAILY_DATA` sheet stores raw data
- **Beautiful styling**: Gold headers, alternating rows, borders
- **Manager stats tracking**: Fixed, Reported, Checking, Pending per user

---

## Input File Format

QA files should have these columns (detected dynamically by header name):

| Column | Description | Used |
|--------|-------------|------|
| Original | Korean source | NO |
| ENG | English translation | NO |
| StringKey | Identifier | NO |
| Command | Dev commands | NO |
| STATUS | QA status | **YES** (stats only, deleted from master) |
| COMMENT | QA feedback | **YES** (copied to COMMENT_{User}, deleted from master) |
| STRINGID | String identifier | **YES** (parsed into comment format, deleted from master) |
| SCREENSHOT | Hyperlink to image | **YES** (copied to SCREENSHOT_{User}, hyperlink updated) |

**Dynamic detection:** Column positions don't matter - the script finds columns by header name.

**Row matching:** By row index (all QA files for same category have identical structure)

**Columns deleted from master:** STATUS, COMMENT, SCREENSHOT, STRINGID are deleted when creating master files. Paired `COMMENT_{User}` + `SCREENSHOT_{User}` columns are added at the far right.

**Note:** STATUS values are read for statistics (shown in STATUS tab) but NOT copied per-user. COMMENT and SCREENSHOT get paired individual columns.

---

## Example

**Before (QA folders):**

`John_Quest/LQA.xlsx`:
| Original | ENG | COMMENT | SCREENSHOT |
|----------|-----|---------|------------|
| 기습 | Ambush | Looks good | |
| 낯선 땅 | Strange Lands | Typo here | typo.png |

`John_Quest/` also contains: `typo.png`

`Alice_Quest/LQA.xlsx`:
| Original | ENG | COMMENT | SCREENSHOT |
|----------|-----|---------|------------|
| 기습 | Ambush | | |
| 낯선 땅 | Strange Lands | Fixed now | fixed.png |

`Alice_Quest/` also contains: `fixed.png`

**After (Master file):**

`Master_Quest.xlsx`:
| Original | ENG | COMMENT_John | SCREENSHOT_John | COMMENT_Alice | SCREENSHOT_Alice |
|----------|-----|--------------|-----------------|---------------|------------------|
| 기습 | Ambush | Looks good\n---\nstringid:\n10001\n(updated: 251230 1500) | | | |
| 낯선 땅 | Strange Lands | Typo here\n---\nstringid:\n10002\n(updated: 251230 1500) | [John_Quest_typo.png] | Fixed now\n---\nstringid:\n10002\n(updated: 251230 1502) | [Alice_Quest_fixed.png] |

`Masterfolder/Images/` contains:
- `John_Quest_typo.png`
- `Alice_Quest_fixed.png`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No valid QA folders found" | Check folder format: `Username_Category/` |
| "No xlsx in folder" | Each folder needs exactly 1 `.xlsx` file |
| "Unknown category" | Use: Quest, Knowledge, Item, Node, System |
| ModuleNotFoundError | Run: `pip install -r requirements.txt` |
| Permission error | Close Excel files before running |
| Hyperlink not working | Check image exists in `Images/` folder |

---

## Technical Notes

- Uses `openpyxl` for Excel handling (preserves formatting)
- **Dynamic column detection** - finds columns by header name, not fixed positions
- **Folder-based input** - each user submits `{Username}_{Category}/` folder with xlsx + images
- Row matching by index (all QA files same structure per category)
- Paired `COMMENT_{User}` + `SCREENSHOT_{User}` columns added at far right
- Fallback row matching: 2+ cell values from non-editable columns
- STATUS sheet recreated on each run (always first tab)
- **Image unique naming** - `{Username}_{Category}_{original}` prevents collisions
- **Hyperlink transformation** - relative paths updated to point to `Images/` folder

---

*Created: 2025-12-30*
*Updated: 2026-01-05 - Added LQA User Progress Tracker with DAILY/TOTAL/GRAPHS tabs*
*Updated: 2026-01-05 - Added Manager Status feature (STATUS_{User} columns with FIXED/REPORTED/CHECKING)*
