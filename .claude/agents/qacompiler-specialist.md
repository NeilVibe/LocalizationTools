---
name: qacompiler-specialist
description: QACompilerNEW project specialist. Use when working on the QA Compiler Suite - generators, tracker, transfer workflow, or datasheet operations.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# QACompilerNEW Specialist

## What Is QACompilerNEW?

**QA Compiler Suite v2.0** - A localization QA workflow automation tool for game translation testing.

**Location:** `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/`

**Core Functions:**
1. **Generate** datasheets from game XML (Perforce)
2. **Transfer** merge OLD tester work with NEW sheets
3. **Build** master files from tester folders
4. **Track** coverage % and progress

## Project Structure

```
QACompilerNEW/
├── main.py                    # Entry point (CLI + GUI)
├── config.py                  # ALL paths & constants (THE source of truth)
├── system_localizer.py        # Standalone System sheet tool
│
├── core/                      # Compiler pipeline
│   ├── discovery.py          # Find valid tester folders
│   ├── excel_ops.py          # Workbook operations
│   ├── matching.py           # Content-based row matching (shared logic)
│   ├── processing.py         # Sheet processing, user columns
│   ├── transfer.py           # OLD+NEW merge logic
│   ├── populate_new.py       # Auto-populate QAfolderNEW
│   ├── tracker_update.py     # Tracker-only update (no master rebuild)
│   └── compiler.py           # Main orchestration
│
├── generators/                # 8 datasheet generators
│   ├── base.py               # Shared utilities (XML, Excel, styles)
│   ├── quest.py              # Quest (largest, most complex)
│   ├── item.py               # Items
│   ├── region.py             # Regions/Factions
│   ├── knowledge.py          # Knowledge tree
│   ├── skill.py              # Skills
│   ├── character.py          # Characters
│   ├── help.py               # GameAdvice (simplest)
│   └── gimmick.py            # Gimmicks
│
├── tracker/                   # Progress tracking
│   ├── coverage.py           # Coverage % + word counts (largest)
│   ├── data.py               # _DAILY_DATA operations
│   ├── daily.py              # DAILY sheet builder
│   └── total.py              # TOTAL sheet + rankings
│
├── gui/app.py                 # Tkinter GUI
├── docs/                      # Documentation
├── QAfolder/                  # Active tester work
├── QAfolderOLD/               # Previous round
├── QAfolderNEW/               # Current round (for merging)
├── TrackerUpdateFolder/       # Retroactive tracker updates
│   ├── QAfolder/              # Tester QA files (for tester stats)
│   ├── Masterfolder_EN/       # English masters (for manager stats)
│   └── Masterfolder_CN/       # Chinese masters (for manager stats)
├── Masterfolder_EN/           # English output
└── Masterfolder_CN/           # Chinese output
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| GUI | Tkinter |
| Excel | openpyxl |
| XML | lxml |
| Build | PyInstaller |

## Workflow Pipeline

```
1. GENERATE    Game XML → GeneratedDatasheets/*.xlsx
2. TRANSFER    QAfolderOLD + GeneratedDatasheets → QAfolderNEW
3. BUILD       QAfolder → Masterfolder_EN/CN (content-based matching)
4. TRACK       Master files → _TRACKER.xlsx (DAILY + TOTAL)
5. TRACKER-ONLY (optional)  QAFolderForTracker → _TRACKER.xlsx (no master rebuild)
```

## GUI Sections

```
1. Generate Datasheets       - Select categories, generate from XML
2. Transfer QA Files         - Merge OLD + NEW
3. Build Master Files        - Compile to Masterfolder_EN/CN
4. Coverage Analysis         - Calculate coverage %
5. System Sheet Localizer    - Create localized System versions
6. Update Tracker Only       - Retroactive tracker updates + Set File Dates
```

## Key Config (config.py)

```python
# Perforce paths - MUST match user's drive
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# Categories (10 total)
CATEGORIES = ["Quest", "Knowledge", "Item", "Region", "System", "Character", "Skill", "Help", "Gimmick", "Contents"]

# Category clustering (multiple categories → one master file)
CATEGORY_TO_MASTER = {
    "Skill": "System",   # Skill sheets → Master_System.xlsx
    "Help": "System",    # Help sheets → Master_System.xlsx
    "Gimmick": "Item",   # Gimmick sheets → Master_Item.xlsx
}
```

## Critical Naming Convention

**Tester folders MUST be:** `{TesterName}_{Category}`

```
✅ 김민영_Quest
✅ John_Item
✅ Chen_System

❌ 김민영 Quest     (space)
❌ quest_김민영     (wrong order)
❌ 김민영_quest     (lowercase)
```

## Content-Based Matching (core/matching.py)

**Robust row matching for master build - handles mixed old/new structure files.**

| Category | Primary Match | Fallback |
|----------|---------------|----------|
| Standard (Quest, Knowledge, etc.) | STRINGID + Translation | Translation only |
| Item | ItemName + ItemDesc + STRINGID | ItemName + ItemDesc |
| Contents | INSTRUCTIONS (col 2) | none |

**Key functions:**
- `build_master_index()` - O(1) lookup index for master worksheet
- `find_matching_row_in_master()` - 2-step cascade matching
- `extract_qa_row_data()` - Extract matching keys from QA row

## Tracker-Only Update (core/tracker_update.py)

**Retroactively add missing days to tracker WITHOUT rebuilding master files.**

```
TrackerUpdateFolder/
├── QAfolder/           # Tester stats (ISSUE, NO ISSUE, BLOCKED, KOREAN)
│   └── Username_Category/
│       └── file.xlsx
├── Masterfolder_EN/    # Manager stats (FIXED, REPORTED, CHECKING, NON-ISSUE)
│   └── Master_Quest.xlsx
└── Masterfolder_CN/    # Manager stats (Chinese masters)
    └── Master_Item.xlsx
```

```bash
# CLI
python main.py --update-tracker

# Workflow
1. Copy QA files to TrackerUpdateFolder/QAfolder/
2. Copy Master files to TrackerUpdateFolder/Masterfolder_EN/ or CN/
3. (Optional) Set file dates via GUI "Set File Dates..." button (select folder)
4. Run "Update Tracker" - uses file mtime as tracker date
```

**File date = tracker date.** Uses `os.utime()` (cross-platform).

**Stats tracked:**
- Tester: ISSUE, NO ISSUE, BLOCKED, KOREAN, word count
- Manager: FIXED, REPORTED, CHECKING, NON-ISSUE (from STATUS_{Username} columns)

## Common Tasks

### Add New Generator

1. Create `generators/newcat.py` copying from `help.py` (simplest)
2. Add category to `config.CATEGORIES`
3. Register in `generators/__init__.py`
4. Add column config to `config.py`

### Fix Generator Bug

1. Identify which generator: `generators/{category}.py`
2. Check `base.py` for shared utilities
3. Test: `python main.py --generate {category}`

### Fix Tracker Bug

1. Check `tracker/coverage.py` for coverage calculations
2. Check `tracker/total.py` for TOTAL sheet formatting
3. Check `tracker/daily.py` for DAILY sheet

### Modify Column Layout

Edit `config.py`:
```python
TRANSLATION_COLS = {
    "Quest": {"KR": 3, "EN": 4, "Trans": 5, "Status": 6},
    ...
}
```

## Debugging

```bash
# Navigate to project
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW

# Syntax check all
python -m py_compile config.py main.py core/*.py generators/*.py tracker/*.py

# Import test
python -c "from generators import generate_datasheets; print('OK')"
python -c "from core.matching import build_master_index; print('OK')"
python -c "from core.tracker_update import update_tracker_only; print('OK')"

# Run specific generator
python main.py --generate quest

# Full pipeline
python main.py --all

# Tracker-only update (no master rebuild)
python main.py --update-tracker

# List categories
python main.py --list

# Launch GUI
python main.py
```

## GDP Logging for QACompiler

```python
from loguru import logger

# Add to any module
logger.warning(f"GDP-001: Processing file {filename}")
logger.warning(f"GDP-002: Found {len(rows)} rows")
logger.warning(f"GDP-003: Matched {matched} / {total}")
```

## Key Files by Task

| Task | Primary File | Secondary |
|------|--------------|-----------|
| Datasheet generation | `generators/*.py` | `base.py` |
| Transfer/merge | `core/transfer.py` | `matching.py` |
| Master building | `core/compiler.py` | `matching.py`, `processing.py` |
| Content-based matching | `core/matching.py` | `config.py` (TRANSLATION_COLS) |
| Tracker-only update | `core/tracker_update.py` | `tracker/data.py` |
| Coverage tracking | `tracker/coverage.py` | `total.py` |
| Config/paths | `config.py` | - |
| GUI | `gui/app.py` | - |

## Recent Features (Session 56)

| Feature | Description | Files |
|---------|-------------|-------|
| Unified TrackerUpdateFolder | QAfolder + Masterfolder_EN/CN subfolders | `config.py` |
| Manager stats tracking | FIXED/REPORTED/CHECKING/NON-ISSUE from masters | `core/tracker_update.py` |
| Folder picker for dates | GUI folder selection for Set File Dates | `gui/app.py` |

## Session 55 Features

| Feature | Description | Files |
|---------|-------------|-------|
| Content-based matching | Robust row matching by content, not index | `core/matching.py` |
| Tracker-only update | Add missing days without master rebuild | `core/tracker_update.py` |
| Set File Dates (GUI) | Set mtime for retroactive entries | `gui/app.py` Section 6 |
| Contents category | INSTRUCTIONS-based matching | `config.py`, `matching.py` |
| GUI 1000x1000 | Larger window to fit Section 6 | `gui/app.py` |

## Previous Fixes (Session 49)

| Issue | Fix | File |
|-------|-----|------|
| Workload data lost on rebuild | Stop at "CATEGORY BREAKDOWN" | `tracker/total.py:168` |
| System output path wrong | Use `DATASHEET_OUTPUT` | `gui/app.py:463` |
| System not in pipeline | Added to `DATASHEET_LOCATIONS` | `core/populate_new.py` |

## Mapping Files

| File | Purpose |
|------|---------|
| `languageTOtester_list.txt` | Tester → Language code |
| `TesterType.txt` | Tester → Type (Text/Gameplay) |

## CI/CD - GitHub Actions Build

**IMPORTANT:** QACompiler has its OWN workflow, separate from LocaNext!

### Two Workflows in This Repo

| Workflow | Trigger File | What It Builds |
|----------|--------------|----------------|
| **LocaNext** | `BUILD_TRIGGER.txt` | Electron app (.exe installer) |
| **QACompiler** | `QACOMPILER_BUILD.txt` | PyInstaller exe + Inno Setup installer |

### Trigger QACompiler Build

```bash
# Add "Build" to trigger file and push
echo "Build" >> QACOMPILER_BUILD.txt
git add QACOMPILER_BUILD.txt
git commit -m "Trigger QACompiler build"
git push origin main
```

### Workflow Details

**File:** `.github/workflows/qacompiler-build.yml`

**Triggers:**
- Push to `QACOMPILER_BUILD.txt` with "Build" line
- Manual dispatch via GitHub Actions UI

**Outputs (GitHub Releases):**
- `QACompiler_vX.X.X_Setup.exe` - Inno Setup installer
- `QACompiler_vX.X.X_Portable.zip` - Portable ZIP
- `QACompiler_vX.X.X_Source.zip` - Source code

**Version Format:** `YY.MMDD.HHMM` (auto-generated, Korean time)

### Local Build (Alternative)

```bash
# On Windows, in QACompilerNEW folder
build_exe.bat

# Output: dist/QACompiler/QACompiler.exe
```

## Output Format for Issues

```
## QACompiler Issue: [Description]

### Category
[Generator/Tracker/Transfer/Config]

### File
`{path/to/file.py}:{line}`

### Problem
[What's wrong]

### Fix
```python
# Code fix
```

### Test
```bash
python main.py --generate {category}
# or
python main.py --all
```
```
