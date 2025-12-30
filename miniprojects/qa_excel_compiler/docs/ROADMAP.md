# QA Excel Compiler - Roadmap

**Created:** 2025-12-30 | **Status:** PLANNING

---

## Overview

Compile QA tester Excel files into master sheets with automatic STATUS tracking and COMMENT aggregation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        QA Excel Compiler                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  QAfolder/                         Masterfolder/                  │
│  ├── John_Quest.xlsx      ──→      ├── Master_Quest.xlsx         │
│  ├── Alice_Quest.xlsx     ──→      │   ├── Sheet1 (data)         │
│  ├── John_Knowledge.xlsx  ──→      │   ├── Sheet3 (data)         │
│  └── ...                           │   └── STATUS (tracking)     │
│                                    ├── Master_Knowledge.xlsx     │
│                                    ├── Master_Item.xlsx          │
│                                    ├── Master_Node.xlsx          │
│                                    └── Master_System.xlsx        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phases

### Phase 1: Core Infrastructure
| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Create folder detection logic | HIGH |
| 1.2 | Parse filename to extract Username + Category | HIGH |
| 1.3 | Load Excel files with openpyxl (preserve formatting) | HIGH |
| 1.4 | Create/load Master file structure | HIGH |

### Phase 2: Comment Compilation
| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Add COMMENT_{Username} columns to master | HIGH |
| 2.2 | Match rows by index (identical structure) | HIGH |
| 2.3 | Copy comments to corresponding column | HIGH |
| 2.4 | Handle comment updates (append with datetime) | HIGH |

### Phase 3: Status Tracking
| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Create STATUS sheet in each master file | HIGH |
| 3.2 | Calculate completion % per user per sheet | HIGH |
| 3.3 | Build status summary table | HIGH |
| 3.4 | Update status on each compile run | HIGH |

### Phase 4: Polish & Error Handling
| Task | Description | Priority |
|------|-------------|----------|
| 4.1 | Handle new users (auto-create columns/rows) | MEDIUM |
| 4.2 | Handle missing files gracefully | MEDIUM |
| 4.3 | Logging and progress output | MEDIUM |
| 4.4 | Backup before overwrite | LOW |

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

### Input: QA Files

**Filename Format:** `{Username}_{Category}.xlsx`

**Examples:**
- `John_Quest.xlsx`
- `Alice_Knowledge.xlsx`
- `Bob_Item.xlsx`

**Expected Columns:**
| Column | Description | Editable |
|--------|-------------|----------|
| Original | Korean source text | NO |
| ENG | English translation | NO |
| StringKey | Optional identifier | NO |
| Command | Dev commands | NO |
| STATUS | QA status (e.g., OK, ERROR, PENDING) | YES |
| COMMENT | QA feedback/notes | YES |
| SCREENSHOT | Hyperlink to screenshot | (IGNORED) |

**Row Matching:** By row index (within each category, all QA testers have identical structure)

### Output: Master Files

**Filename Format:** `Master_{Category}.xlsx`

**Structure:**
```
Master_Quest.xlsx
├── Sheet1               # Original data + COMMENT_{User} columns
├── Sheet3               # Original data + COMMENT_{User} columns
├── ...                  # Other sheets from source
└── STATUS               # Completion tracking per user
```

**Data Sheet Columns:**
| Column | Description |
|--------|-------------|
| Original | Korean source (from first file) |
| ENG | English translation (from first file) |
| StringKey | Unique identifier (matching key) |
| Command | Dev commands |
| COMMENT_John | John's comments |
| COMMENT_Alice | Alice's comments |
| COMMENT_Bob | Bob's comments |
| ... | More users as needed |

**STATUS Sheet:**
| User | Sheet1 | Sheet3 | ... | Total |
|------|--------|--------|-----|-------|
| John | 85% | 100% | ... | 92% |
| Alice | 50% | 75% | ... | 62% |
| Bob | 100% | 100% | ... | 100% |

---

## Comment Update Logic

### Scenario: User updates an existing comment

**Before:**
```
COMMENT_John: "Translation issue" (date: 251204 1030)
```

**After (user adds new comment):**
```
COMMENT_John: "Fixed now" (date: 251230 1445)

"Translation issue" (date: 251204 1030)
```

**Format:** Latest comment on top, older below, separated by blank line.

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
pandas>=2.0.0      # Data manipulation
```

---

## Usage

```bash
# Basic usage
python3 compile_qa.py

# With options (future)
python3 compile_qa.py --qa-folder ./QAfolder --master-folder ./Masterfolder
python3 compile_qa.py --dry-run  # Preview without writing
python3 compile_qa.py --backup   # Create backups before overwrite
```

---

*Roadmap created 2025-12-30*
