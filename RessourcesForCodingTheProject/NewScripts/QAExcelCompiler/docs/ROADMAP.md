# QA Excel Compiler - Roadmap

**Created:** 2025-12-30 | **Status:** ✅ IMPLEMENTED | **Updated:** 2026-01-06

---

## Overview

Compile QA tester Excel files into master sheets with automatic STATUS tracking, COMMENT aggregation, and IMAGE compilation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  QA Excel Compiler (v2 - with Images)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  QAfolder/                         Masterfolder/                  │
│  ├── John_Quest/             ──→   ├── Master_Quest.xlsx         │
│  │   ├── LQA.xlsx                  │   ├── STATUS (first tab)    │
│  │   ├── bug1.png                  │   └── Sheet1 (data +        │
│  │   └── typo.png                  │        COMMENT_{User} +     │
│  ├── Alice_Quest/            ──→   │        SCREENSHOT_{User})   │
│  │   ├── LQA.xlsx                  ├── Master_Knowledge.xlsx     │
│  │   └── font.png                  ├── Master_Item.xlsx          │
│  └── Bob_Knowledge/          ──→   ├── Master_Node.xlsx          │
│      ├── LQA.xlsx                  ├── Master_System.xlsx        │
│      └── term.png                  └── Images/                   │
│                                        ├── John_Quest_bug1.png   │
│                                        ├── John_Quest_typo.png   │
│                                        ├── Alice_Quest_font.png  │
│                                        └── Bob_Knowledge_term.png│
└─────────────────────────────────────────────────────────────────┘
```

---

## Phases

### Phase 1: Core Infrastructure ✅
| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Folder detection logic (`discover_qa_folders()`) | ✅ DONE |
| 1.2 | Parse folder name: `{Username}_{Category}` | ✅ DONE |
| 1.3 | Load Excel files with openpyxl (preserve formatting) | ✅ DONE |
| 1.4 | Create/load Master file structure | ✅ DONE |

### Phase 2: Comment Compilation ✅
| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Add COMMENT_{Username} columns to master | ✅ DONE |
| 2.2 | Match rows by index (identical structure) | ✅ DONE |
| 2.3 | Copy comments to corresponding column | ✅ DONE |
| 2.4 | Handle comment updates (append with datetime) | ✅ DONE |

### Phase 3: Status Tracking ✅
| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Create STATUS sheet in each master file (first tab) | ✅ DONE |
| 3.2 | Calculate completion % per user | ✅ DONE |
| 3.3 | Build status summary table (ISSUE #, NO ISSUE %, BLOCKED %) | ✅ DONE |
| 3.4 | Update status on each compile run | ✅ DONE |

### Phase 4: Polish & Error Handling ✅
| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Handle new users (auto-create columns) | ✅ DONE |
| 4.2 | Handle missing files/folders gracefully | ✅ DONE |
| 4.3 | Logging and progress output | ✅ DONE |
| 4.4 | Backup before overwrite | ⏸️ SKIPPED |

### Phase 5: Image Compilation ✅ (NEW)
| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Folder-based input: `{Username}_{Category}/` | ✅ DONE |
| 5.2 | Copy images to `Images/` with unique names | ✅ DONE |
| 5.3 | Add SCREENSHOT_{Username} columns (paired with COMMENT) | ✅ DONE |
| 5.4 | Hyperlink transformation to new paths | ✅ DONE |
| 5.5 | Remove MasterUI (no longer needed) | ✅ DONE |

### Phase 6: Progress Tracker ✅ (NEW)
| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Create `LQA_Tester_ProgressTracker.xlsx` | ✅ DONE |
| 6.2 | DAILY sheet with table + 2 clustered bar charts | ✅ DONE |
| 6.3 | TOTAL sheet with table + 2 clustered bar charts | ✅ DONE |
| 6.4 | Hidden `_DAILY_DATA` sheet for raw data | ✅ DONE |
| 6.5 | Manager stats integration (Fixed, Reported, Checking) | ✅ DONE |
| 6.6 | Chart standardization (DAILY/TOTAL identical style) | ✅ DONE |

**Chart Details:** See [GRAPHS_REDESIGN_PLAN.md](GRAPHS_REDESIGN_PLAN.md)

### Phase 7: UX Improvements ✅ (NEW)
| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Auto-hide rows with no comments (focus on issues) | ✅ DONE |
| 7.2 | Adjacent row context (keep rows near comments visible) | ✅ DONE |
| 7.3 | Auto-hide sheets with no comments (entire tab hidden) | ✅ DONE |

### Phase 8: EN/CN Language Separation ✅ (NEW)
| Task | Description | Status |
|------|-------------|--------|
| 8.1 | Load tester→language mapping from `languageTOtester_list.txt` | ✅ DONE |
| 8.2 | Create `Masterfolder_EN/` and `Masterfolder_CN/` | ✅ DONE |
| 8.3 | Auto-route testers to correct folder based on language | ✅ DONE |
| 8.4 | Progress Tracker at root level (combines all languages) | ✅ DONE |
| 8.5 | TOTAL sheet EN/CN separation with colored headers | ✅ DONE |

---

## Categories (Fixed)

| Category | Master File | Description |
|----------|-------------|-------------|
| Quest | Master_Quest.xlsx | Quest-related strings |
| Knowledge | Master_Knowledge.xlsx | Knowledge/lore strings |
| Item | Master_Item.xlsx | Item descriptions |
| Node | Master_Node.xlsx | Node/location strings |
| System | Master_System.xlsx | System/UI strings |

---

## Input/Output Specifications

### Input: QA Folders

**Folder Format:** `QAfolder/{Username}_{Category}/`

**Contents:**
- One `.xlsx` file (any name)
- Images referenced in SCREENSHOT column

**Examples:**
```
QAfolder/
├── John_Quest/
│   ├── LQA_Quest.xlsx
│   ├── bug1.png
│   └── typo.png
├── Alice_Quest/
│   ├── LQA.xlsx
│   └── font_issue.png
└── Bob_Knowledge/
    ├── LQA_Knowledge.xlsx
    └── term.png
```

**Expected Columns in xlsx:**
| Column | Description | Compiled To |
|--------|-------------|-------------|
| Original | Korean source text | (kept) |
| ENG | English translation | (kept) |
| StringKey | Optional identifier | (kept) |
| Command | Dev commands | (kept) |
| STATUS | QA status (ISSUE/NO ISSUE/BLOCKED) | Stats only |
| COMMENT | QA feedback/notes | COMMENT_{User} |
| SCREENSHOT | Hyperlink to image | SCREENSHOT_{User} |
| STRINGID | String identifier | Embedded in comment |

**Row Matching:** By row index (all QA testers have identical structure per category)

### Output: Master Files + Images (EN/CN Separated)

**Structure:**
```
QAExcelCompiler/
├── LQA_Tester_ProgressTracker.xlsx  # Combined progress (root level)
├── languageTOtester_list.txt        # Tester→Language mapping
├── Masterfolder_EN/                 # EN testers output
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   ├── Master_Item.xlsx
│   ├── Master_Node.xlsx
│   ├── Master_System.xlsx
│   └── Images/
│       ├── bug1.png
│       └── typo.png
└── Masterfolder_CN/                 # CN testers output
    ├── Master_Quest.xlsx
    ├── Master_Knowledge.xlsx
    └── Images/
        └── screenshot.png
```

**Master File Structure:**
```
Master_Quest.xlsx
├── STATUS               # First tab - completion tracking
└── Sheet1               # Data + paired user columns
```

**Data Sheet Columns:**
| Column | Description |
|--------|-------------|
| Original | Korean source |
| ENG | English translation |
| StringKey | Identifier |
| Command | Dev commands |
| COMMENT_John | John's comments (with timestamps) |
| SCREENSHOT_John | John's screenshots (hyperlinks to Images/) |
| COMMENT_Alice | Alice's comments |
| SCREENSHOT_Alice | Alice's screenshots |

**STATUS Sheet:**
| User | Completion % | Total Rows | ISSUE # | NO ISSUE % | BLOCKED % |
|------|--------------|------------|---------|------------|-----------|
| John | 80.0% | 5 | 2 | 20.0% | 20.0% |
| Alice | 100.0% | 5 | 1 | 80.0% | 0.0% |

---

## Comment Format

**Format (with stringid):**
```
COMMENT_John:
Translation issue
---
stringid:
10001
(updated: 251204 1030)
```

**Format (without stringid):**
```
COMMENT_John:
Translation issue
---
(updated: 251204 1030)
```

**Key points:**
- Clean format: comment text, `---` delimiter, metadata
- REPLACE mode: New comments replace old entirely (no append)
- Duplicate detection: Splits on `---` to compare original text

---

## Status Calculation

```python
def calculate_completion(df, status_column='STATUS'):
    """
    Calculate completion percentage.

    Completion = rows with non-empty STATUS / total rows * 100
    """
    total_rows = len(df)
    completed_rows = df[status_column].notna().sum()
    return round(completed_rows / total_rows * 100, 1)
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| New user (no column exists) | Create COMMENT_{User} column |
| New user (no STATUS row) | Add row to STATUS sheet |
| Empty QAfolder | Skip with warning |
| Invalid filename format | Skip with warning |
| Missing StringKey | Use row index as fallback |
| Master file doesn't exist | Create from first QA file |
| Sheet mismatch | Only process matching sheets |

---

## Dependencies

```
openpyxl>=3.1.0    # Excel read/write with formatting
```

---

## Usage

```bash
# Run the compiler
python3 compile_qa.py
```

**What it does:**
1. Scans `QAfolder/` for `{Username}_{Category}/` folders
2. Copies images to `Masterfolder/Images/` with unique names
3. Compiles xlsx data into `Master_{Category}.xlsx`
4. Creates paired `COMMENT_{User}` + `SCREENSHOT_{User}` columns
5. Updates hyperlinks to point to `Images/` folder
6. Generates STATUS sheet with completion stats

---

*Roadmap created 2025-12-30*
*Implemented 2026-01-02*
