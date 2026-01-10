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

This launches a GUI with two buttons:

```
┌─────────────────────────────────────────────────────────────────┐
│                    QA Excel Compiler                             │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────────────────┐   ┌─────────────────────────┐     │
│   │   Transfer QA Files     │   │   Build Masterfiles     │     │
│   └─────────────────────────┘   └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Transfer QA Files** - Use when QA file structure changes:
1. Place OLD QA files in `QAfolderOLD/`
2. Place NEW QA files (empty) in `QAfolderNEW/`
3. Click "Transfer QA Files"
4. Tester work (COMMENT/STATUS/SCREENSHOT) transfers to `QAfolder/`

**Transfer Matching Logic:**

For **Quest, Knowledge, Character, Region**:
- **Step 1:** STRINGID + Translation (exact match)
- **Step 2:** Translation only (fallback)

For **System** (manually created sheets):
- **Column structure:** Col1=Translation, Col2=STATUS, Col3=COMMENT, Col4=STRINGID, Col5=SCREENSHOT
- **Step 1:** STRINGID + Translation (exact match)
- **Step 2:** Translation only (fallback)

For **Item** (stricter matching using ItemName + ItemDesc):
- **Step 1:** ItemName + ItemDesc + STRINGID (all 3 must match)
- **Step 2:** ItemName + ItemDesc only (fallback)
- **No fallback to ItemName only** - requires both name and description to match

**Duplicate Translation Report:**
If same translation appears multiple times with different comments, a report is generated:
- `QAfolder/{Username}_{Category}/DUPLICATE_TRANSLATION_REPORT.txt`
- Lists translations where only the first comment was kept
- Review to ensure no important feedback was lost

**Build Masterfiles** - Normal compilation:
1. Place QA files in `QAfolder/`
2. Click "Build Masterfiles"
3. Master files created in `Masterfolder_EN/` and `Masterfolder_CN/`

### 3. Check `Masterfolder_EN/` and `Masterfolder_CN/` for results

Output structure:
```
QAExcelCompiler/
├── Masterfolder_EN/               # EN testers
│   ├── Master_Quest.xlsx          # QA data + STATUS per category
│   ├── Master_Knowledge.xlsx
│   ├── Master_Item.xlsx
│   └── Images/                    # EN images consolidated
│
├── Masterfolder_CN/               # CN testers
│   ├── Master_Quest.xlsx
│   └── Images/                    # CN images consolidated
│
└── LQA_Tester_ProgressTracker.xlsx  # Combined progress tracker
    ├── DAILY                      # Daily progress per user
    ├── TOTAL                      # Cumulative stats (EN + CN sections)
    └── GRAPHS                     # Visual charts
```

---

## Folder Structure

```
QAExcelCompiler/
├── compile_qa.py         # Main script with GUI
├── requirements.txt      # Dependencies (openpyxl)
├── README.md             # This file
│
├── QAfolderOLD/          # OLD structure QA files (for migration)
│   └── {Username}_{Category}/
│
├── QAfolderNEW/          # NEW structure QA files (for migration)
│   └── {Username}_{Category}/
│
├── QAfolder/             # WORKING folder (input for Build)
│   ├── John_Quest/       # {Username}_{Category}/
│   │   ├── LQA.xlsx      # 1 xlsx per folder
│   │   └── *.png         # Images with relative hyperlinks
│   ├── Alice_Quest/
│   │   ├── LQA.xlsx
│   │   └── *.png
│   └── ...
│
├── Masterfolder_EN/      # EN tester output
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   └── Images/
│
├── Masterfolder_CN/      # CN tester output
│   ├── Master_Quest.xlsx
│   └── Images/
│
├── LQA_Tester_ProgressTracker.xlsx  # Combined progress tracker
│
├── datasheet_generators/  # Scripts that create QA source files
│   ├── fullquest15.py       # Quest data extractor
│   ├── fullknowledge14.py   # Knowledge data extractor
│   ├── fullitem25.py        # Item data extractor
│   ├── fullregion7.py       # Region data extractor
│   ├── fullcharacter1.py    # Character data extractor
│   ├── fullgimmick1.py      # Gimmick data extractor
│   └── README.md
│
└── docs/
    ├── ROADMAP.md        # Project plan
    ├── WIP.md            # Technical details
    ├── MIGRATION_PLAN.md # Migration feature plan
    └── ...
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

**Valid STATUS values:** ISSUE, NO ISSUE, BLOCKED, KOREAN

### Re-run Safe

- Running multiple times won't duplicate comments
- New comments from QA files are appended
- Existing comments preserved
- **Team's custom formatting preserved** (colors added to cells won't be overwritten)
- **Hidden columns stay hidden** (column visibility preserved on updates)
- **Manager status values preserved** (FIXED/REPORTED/CHECKING entries persist on re-compile)

### Two-Status System (Tester + Manager)

Master files have **two status columns per user**:

```
| COMMENT_John | TESTER_STATUS_John | STATUS_John | SCREENSHOT_John |
|--------------|-------------------|-------------|-----------------|
| "Bug here"   | ISSUE             | FIXED       | img.png         |
| "Wrong text" | BLOCKED           |             |                 |
| "Looks OK"   | NO ISSUE          |             |                 |
```

**Column structure per user:**
1. `COMMENT_{User}` - QA feedback (visible)
2. `TESTER_STATUS_{User}` - Original QA status (**HIDDEN** - for filtering)
3. `STATUS_{User}` - Manager status (visible, dropdown)
4. `SCREENSHOT_{User}` - Image hyperlink (visible)

**Tester STATUS values** (from QA file):
- **ISSUE**: Problem found (rows visible by default)
- **NO ISSUE**: No problem (rows hidden)
- **BLOCKED**: Cannot test (rows hidden)
- **KOREAN**: Korean-only issue (rows hidden)

**Manager STATUS values** (set in Master file):
- **FIXED**: Issue has been fixed (rows hidden)
- **REPORTED**: Issue reported to dev team (rows visible)
- **CHECKING**: Issue being investigated (rows visible)
- **NON-ISSUE**: Not actually an issue (rows hidden)
- *(empty)*: Pending manager review (rows visible)

### Row Visibility Rules

| Tester Status | Manager Status | Row Visible? |
|---------------|----------------|--------------|
| ISSUE | (empty) | ✅ YES |
| ISSUE | REPORTED | ✅ YES |
| ISSUE | CHECKING | ✅ YES |
| ISSUE | FIXED | ❌ NO |
| ISSUE | NON-ISSUE | ❌ NO |
| BLOCKED | (any) | ❌ NO |
| KOREAN | (any) | ❌ NO |
| NO ISSUE | (any) | ❌ NO |

**Key points:**
- Comments are compiled for **ALL** tester statuses (not just ISSUE)
- Only ISSUE rows are shown by default
- Manager can resolve ISSUE rows → they become hidden
- TESTER_STATUS column always stays hidden (internal use)
- If ANY user has ISSUE status on a row, row is visible

### Sheet Hiding Rules

Sheets are hidden when:
- Sheet has NO comments at all
- Sheet has comments but NO visible ISSUE rows after filtering

### Manager Workflow

1. Compiler creates Master files with empty `STATUS_{User}` columns
2. Manager opens Master file in Excel
3. Manager enters FIXED/REPORTED/CHECKING/NON-ISSUE for each issue
4. On next compile, these values are **preserved automatically** (matched by comment text)
5. Manager stats appear in Progress Tracker (Fixed, Reported, Checking, Pending)

**Column styling:**
- `STATUS_{User}` headers: Light green (`90EE90`) background
- FIXED: Forest green text
- REPORTED: Orange text
- CHECKING: Blue text
- NON-ISSUE: Gray text

### EN Item A-Z Sorting

For the **EN Item** category specifically, both input and output are sorted A-Z:

- **Input QA files**: Sorted A-Z by `ItemName(ENG)` column before processing
- **Master output**: Sorted A-Z by `ItemName(ENG)` column

**Why:** Ensures consistent row alignment regardless of how testers submit their files. Both files are in the same order before any matching happens.

**Note:** CN Item and other categories (Quest, Knowledge, etc.) are NOT sorted - they preserve original row order.

### Word Wrap + Autofit Row Heights

All master files get automatic formatting:

- **Word wrap enabled** on all cells
- **Row heights auto-calculated** based on content (multi-line comments expand rows)
- **Max height capped** at 300 points (prevents extreme rows)

This applies to ALL categories, not just EN Item.

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

**DAILY Tab** - Shows daily progress per user with clear separation:
```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              DAILY PROGRESS                                              │
├─────────┬────────────────────╫────────────────────╫────────────────────╫─────────────────┤
│         │       Alice        ║        Bob         ║       John         ║  Manager Stats  │
├─────────┼──────┬─────────────╫──────┬─────────────╫──────┬─────────────╫─────┬─────┬─────┤
│  Date   │ Done │   Issues    ║ Done │   Issues    ║ Done │   Issues    ║Fixed│Rept │Pend │
├─────────┼──────┼─────────────╫──────┼─────────────╫──────┼─────────────╫─────┼─────┼─────┤
│  01/03  │  --  │     --      ║  --  │     --      ║  45  │     8       ║  2  │  1  │  5  │
│  01/04  │  32  │      5      ║  --  │     --      ║  --  │    --       ║  3  │  2  │  0  │
│  01/05  │  --  │     --      ║  28  │      6      ║  15  │     3       ║  1  │  4  │  4  │
├─────────┼──────┼─────────────╫──────┼─────────────╫──────┼─────────────╫─────┼─────┼─────┤
│  TOTAL  │  32  │      5      ║  28  │      6      ║  60  │    11       ║  6  │  7  │  9  │
└─────────┴──────┴─────────────╫──────┴─────────────╫──────┴─────────────╫─────┴─────┴─────┘
                    ║ = THICK BORDER separating users
```

- **Date**: From file modification time (auto-detected)
- **Done**: Rows with STATUS filled (ISSUE + NO ISSUE + BLOCKED)
- **Issues**: Rows with STATUS = "ISSUE"
- **`--`**: No submission that day
- **Thick borders (║)**: Visually separate each tester and Manager Stats section
- **Chart**: Uses main table data directly (no separate data table)

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

**Cross-Category Progress:**

When a tester completes one category and gets assigned a new one:

| Scenario | Total Rows | Done | Completion |
|----------|------------|------|------------|
| Quest only (100%) | 1000 | 1000 | 100% |
| Quest + Knowledge (new) | 1500 | 1000 | 66.7% |

- TOTAL tab aggregates **latest data** per (user, category)
- Adding new category increases total rows → completion % drops
- This correctly reflects overall progress across all assignments

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
| Excel repair dialog on open | Regenerate with latest code (fixed in v2026-01-07) |
| Hidden content not showing on re-run | Fixed: sheets/columns now reset to visible before processing |

---

## Known Warnings (Safe to Ignore)

```
UserWarning: Unknown type for MediaServiceImageTags
```

**What it means:** openpyxl found a Microsoft-specific property it doesn't understand (for image handling).

**Is it a problem?** NO. The warning is harmless - openpyxl continues and works correctly. This happens when Excel adds its own internal properties to files.

**Do I need to fix it?** No. Just ignore it. Your data is 100% safe.

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
- **EN Item A-Z sorting** - both input and master sorted by `ItemName(ENG)` for consistent alignment
- **Excel formula sanitization** - prevents `=`, `+`, `@` chars from being interpreted as formulas
- **DAILY delta calculation** - shows daily work (today - yesterday), not cumulative totals
- **Actual Issues % clamping** - prevents negative percentages (clamped to 0-100%)
- **Smart data validation** - uses actual row count + buffer instead of hardcoded 1000 rows
- **Word wrap + autofit** - all master files get word wrap and auto row heights

---

---

## GRAPHS Tab (Dashboard)

**Status:** ✅ IMPLEMENTED | **Docs:** [docs/GRAPHS_REDESIGN_PLAN.md](docs/GRAPHS_REDESIGN_PLAN.md)

ONE big spacious line chart showing cumulative progress:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LQA PROGRESS TRACKER                             │
│                                                                          │
│  Rows ▲                                                  ●──── TOTAL     │
│       │                                                ╱                 │
│  100  │                                  ●────────────●   ●──── Alice    │
│       │                                ╱                                 │
│   50  │                    ●──────────●                   ●──── Bob      │
│       │                  ╱                                               │
│    0  ├──●──────────────●──────────────────────────────→  ●──── Fixed    │
│          01/03         01/04         01/05      Date                     │
│                                                                          │
│   ● Alice    ● Bob    ● John    ● TOTAL    ● Fixed                      │
│                    ↑ click legend to toggle                              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Dots connected by lines (clean, agreeable UIUX)
- Cumulative data (lines go UP)
- Click legend to show/hide any series (Excel built-in)
- Data tables hidden (not cluttered)

---

*Created: 2025-12-30*
*Updated: 2026-01-05 - Added LQA User Progress Tracker with DAILY/TOTAL/GRAPHS tabs*
*Updated: 2026-01-05 - Added Manager Status feature (STATUS_{User} columns with FIXED/REPORTED/CHECKING)*
*Updated: 2026-01-05 - Added Comp % column to DAILY tab (shows completion per user per day)*
*Updated: 2026-01-08 - DAILY tab simplified: removed Comp%, Actual Issues columns (keep in TOTAL only); added thick borders between users; chart uses main table directly*
*Updated: 2026-01-08 - Added safe_load_workbook() to handle corrupted Excel filter errors; clear error message with fix instructions*
*Updated: 2026-01-05 - Redesigned GRAPHS tab: ONE big line chart with dots, cumulative data, toggleable legend*
*Updated: 2026-01-07 - EN Item: Sort both input and master A-Z by ItemName(ENG) for consistent alignment*
*Updated: 2026-01-07 - Excel safety: sanitization for formula chars, fixed data validation range*
*Updated: 2026-01-07 - UNHIDE fix: sheets/columns reset to visible before re-processing*
*Updated: 2026-01-07 - DAILY delta: shows daily work instead of cumulative totals*
*Updated: 2026-01-07 - Actual Issues %: clamped to 0-100% to prevent negative values*
*Updated: 2026-01-08 - Manager row hiding: rows with FIXED/REPORTED/NON-ISSUE status are auto-hidden in Master files*
*Updated: 2026-01-08 - Pending formula fix: now correctly subtracts NON-ISSUE (Pending = Issues - Fixed - Reported - Checking - NonIssue)*
*Updated: 2026-01-08 - DAILY tab: removed confusing TOTAL row; added NonIssue column to manager stats*
*Updated: 2026-01-08 - TOTAL tab charts: fixed Actual Issues % chart (now uses numeric values instead of strings)*
*Updated: 2026-01-08 - CRITICAL FIX: TOTAL tab was double-counting due to summing cumulative data across dates; now uses latest date only*
*Updated: 2026-01-08 - ROBUST auto-repair for corrupted Excel filters (strips autoFilter XML from corrupted files)*
*Updated: 2026-01-10 - fullitem25.py v3.13: ItemDesc from KnowledgeKey->KnowledgeInfo.Desc*
*Updated: 2026-01-10 - fullitem25.py v3.14: KnowledgeKey priority, fallback to ItemInfo.ItemDesc if no KnowledgeKey*
*Updated: 2026-01-10 - Item transfer: stricter matching using ItemName+ItemDesc+STRINGID (requires both name and description)*
*Updated: 2026-01-10 - System category: supports manually created sheets with Translation in Column 1*
*Updated: 2026-01-10 - KOREAN status: added as valid tester status (rows hidden like BLOCKED)*
*Updated: 2026-01-10 - Two-status system: TESTER_STATUS (hidden) + STATUS (manager) columns per user*
*Updated: 2026-01-10 - Compile ALL statuses: comments compiled for ISSUE/BLOCKED/KOREAN/NO ISSUE (not just ISSUE)*
*Updated: 2026-01-10 - Row visibility: show if ANY user has ISSUE, hide if manager marks FIXED/NON-ISSUE*
*Updated: 2026-01-10 - Sheet hiding: hide sheets with no visible ISSUE rows after filtering*
*Updated: 2026-01-10 - REPORTED status: now stays VISIBLE (was incorrectly hidden before)*
