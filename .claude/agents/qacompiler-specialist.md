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
│   ├── processing.py         # Row matching, string normalization
│   ├── transfer.py           # OLD+NEW merge logic
│   ├── populate_new.py       # Auto-populate QAfolderNEW
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
3. BUILD       QAfolder → Masterfolder_EN/CN
4. TRACK       Master files → _TRACKER.xlsx (DAILY + TOTAL)
```

## Key Config (config.py)

```python
# Perforce paths - MUST match user's drive
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# Categories
CATEGORIES = ["Quest", "Knowledge", "Item", "Region", "System", "Character", "Skill", "Help", "Gimmick"]

# Category clustering
CLUSTERING = {
    "Skill": "System",
    "Gimmick": "Item",
    "Help": "Knowledge"
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

# Run specific generator
python main.py --generate quest

# Full pipeline
python main.py --all

# List categories
python main.py --list
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
| Transfer/merge | `core/transfer.py` | `processing.py` |
| Master building | `core/compiler.py` | `excel_ops.py` |
| Coverage tracking | `tracker/coverage.py` | `total.py` |
| Config/paths | `config.py` | - |
| GUI | `gui/app.py` | - |

## Recent Fixes (Session 49)

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

## Build Executable

```bash
# Use build script (prompts for drive letter)
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
