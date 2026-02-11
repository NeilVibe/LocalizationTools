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
├── generators/                # 9 datasheet generators
│   ├── base.py               # Shared utilities (XML, Excel, styles)
│   ├── quest.py              # Quest (largest, most complex)
│   ├── item.py               # Items
│   ├── region.py             # Regions/Factions
│   ├── knowledge.py          # Knowledge tree
│   ├── skill.py              # Skills
│   ├── character.py          # Characters
│   ├── help.py               # GameAdvice (simplest)
│   ├── gimmick.py            # Gimmicks
│   └── script.py             # Script template (Sequencer/Dialog)
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

## XML Newline Convention (CRITICAL!)

**Newlines in XML language data = `<br/>` tags. NOT `&#10;`, NOT `\n`.**

```xml
<!-- CORRECT -->
KR="첫 번째 줄<br/>두 번째 줄"

<!-- WRONG -->
KR="첫 번째 줄&#10;두 번째 줄"
```

All QACompiler modules (generators, base.py, xml parsing) MUST preserve `<br/>` tags when reading XML and writing to Excel. Never strip or convert them.

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
# Drive letter is NOW configurable via settings.json at runtime!
# Default F: paths in source, but settings.json overrides at runtime

# Categories (12 total)
CATEGORIES = ["Quest", "Knowledge", "Item", "Region", "System", "Character", "Skill", "Help", "Gimmick", "Contents", "Sequencer", "Dialog"]

# Category clustering (multiple categories → one master file)
CATEGORY_TO_MASTER = {
    "Skill": "System",       # Skill sheets → Master_System.xlsx
    "Help": "System",        # Help sheets → Master_System.xlsx
    "Gimmick": "Item",       # Gimmick sheets → Master_Item.xlsx
    "Sequencer": "Script",   # Sequencer sheets → Master_Script.xlsx
    "Dialog": "Script",      # Dialog sheets → Master_Script.xlsx
}

# Script-type categories use unique column structure
SCRIPT_TYPE_CATEGORIES = {"sequencer", "dialog"}  # Uses MEMO (not COMMENT), no SCREENSHOT
```

## Runtime Drive Configuration (settings.json)

**Problem solved:** PyInstaller compiles config.py at build time, so patching the .py file after install doesn't work - Python uses frozen bytecode.

**Solution:** config.py now reads `settings.json` at runtime.

### How It Works

```python
# config.py loads settings at import time
_SETTINGS = _load_settings()  # Reads settings.json
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')  # Default F:

# All paths use _apply_drive_letter()
RESOURCE_FOLDER = Path(_apply_drive_letter(r"F:\perforce\...", _DRIVE_LETTER))
```

### settings.json Format

```json
{"drive_letter": "D", "version": "1.0"}
```

**Location:** Same folder as QACompiler.exe

### Change Drive After Install

Just edit `settings.json`:
```json
{"drive_letter": "E", "version": "1.0"}
```

No reinstall needed!

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
| Script-type (Sequencer, Dialog) | Translation + EventName | EventName ONLY (not Translation!) |

**Key functions:**
- `build_master_index()` - O(1) lookup index for master worksheet
- `find_matching_row_in_master()` - 2-step cascade matching
- `extract_qa_row_data()` - Extract matching keys from QA row

## Script-Type Categories (Sequencer/Dialog)

**Unique structure for script/dialog LQA files:**

| Aspect | Script-Type | Standard |
|--------|-------------|----------|
| Comment column | MEMO | COMMENT |
| Screenshot | NO | Yes |
| Primary match | Translation + EventName | STRINGID + Translation |
| Fallback match | EventName ONLY | Translation only |
| Master output | Master_Script.xlsx | Master_{Category}.xlsx |

**Column layout:** ⚠️ **TO BE CONFIRMED** - Actual source files have different structure:
- Col 1: Group
- Col 2: SequenceName
- Col 3: Dialog Voice
- Col 4+: TBD

**Current TRANSLATION_COLS setting:** `{"eng": 2, "other": 3}` - **MAY NEED UPDATE** once actual structure confirmed.

**Folder naming:**
- `Username_Sequencer` → Master_Script.xlsx
- `Username_Dialog` → Master_Script.xlsx

## Column Detection: Name vs Position

**IMPORTANT:** QACompiler uses a MIX of column detection methods:

| Column | Detection Method | Notes |
|--------|------------------|-------|
| STATUS | **By header NAME** | `find_column_by_header("STATUS")` |
| COMMENT | **By header NAME** | `find_column_by_header("COMMENT")` |
| MEMO | **By header NAME** | Script-type only: `find_column_by_header("MEMO")` |
| SCREENSHOT | **By header NAME** | `find_column_by_header("SCREENSHOT")` |
| STRINGID | **By header NAME** | `find_column_by_header("STRINGID")` |
| EventName | **By header NAME** | Script-type only: `find_column_by_header("EventName")` |
| **Translation** | **HARDCODED POSITION** | Uses `TRANSLATION_COLS[category]["eng"/"other"]` |

**Why Translation uses position:**
- Translation column position varies by category (Item uses col 5/7, standard uses 2/3)
- Position is configured in `config.py` TRANSLATION_COLS
- Allows different layouts per category without changing header names

**Key functions:**
- `find_column_by_header(ws, name)` → Searches row 1 for matching header, returns column index
- `get_translation_column(category, is_english)` → Returns hardcoded position from TRANSLATION_COLS

**If column positions don't match TRANSLATION_COLS:** Matching will fail silently (wrong column data used)

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

## EXPORT-Aware Duplicate Resolution (base.py)

**Problem:** Same Korean text can have different translations depending on source file context.

```
Korean: "설명" (Description)
├── StringId 1001 (skillinfo_pc.xml) → "Skill Description"
├── StringId 1002 (iteminfo_pc.xml)  → "Item Description"
└── StringId 1003 (questinfo.xml)    → "Quest Description"
```

**Solution:** Use EXPORT folder to disambiguate by matching source filename to EXPORT StringIDs.

### Key Functions (base.py)

| Function | Purpose |
|----------|---------|
| `build_export_stringid_index()` | Scans EXPORT folder, builds `{filename: {stringids}}` map |
| `get_export_index()` | Lazy-loads and caches EXPORT index (module-level) |
| `get_export_key()` | Normalizes filenames for matching |
| `resolve_translation()` | Context-aware translation lookup with EXPORT matching |

### How It Works

```python
# All generators now track source_file through data pipeline:
# 1. Extraction: source_file = path.name
# 2. Data classes: source_file: str = ""
# 3. Row tuples: (depth, text, source_file)
# 4. Write: resolve_translation(text, lang_tbl, source_file, export_index)

# Resolution algorithm:
def resolve_translation(korean_text, lang_table, data_filename, export_index):
    candidates = lang_table.get(normalize(korean_text), [])
    if len(candidates) == 1:
        return candidates[0]  # Single match

    # Multiple matches - use EXPORT to disambiguate
    export_key = get_export_key(data_filename)  # "skillinfo_pc.staticinfo"
    export_stringids = export_index.get(export_key, set())

    for translation, stringid in candidates:
        if stringid in export_stringids:
            return (translation, stringid)  # EXPORT match!

    return first_good_translation(candidates)  # Fallback
```

### All 8 Generators Updated

| Generator | source_file tracking |
|-----------|---------------------|
| skill.py | SkillItem.source_file → RowItem tuple |
| character.py | CharacterItem.source_file |
| quest.py | Row builders track source_file |
| item.py | ItemData.source_file |
| region.py | All data classes have source_file |
| knowledge.py | KnowledgeItem.source_file |
| gimmick.py | GimmickEntry.source_file |
| help.py | AdviceItem/Group.source_file |

### Language Table Structure

```python
# Old: Single translation per Korean text
{normalized_korean: (translation, stringid)}

# New: List of ALL translations for duplicate handling
{normalized_korean: [(translation, stringid), ...]}
```

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

## CI/CD - Comprehensive Validation (5 Checks)

**IMPORTANT:** QACompiler has its OWN workflow with COMPREHENSIVE validation!

### CI Pipeline Structure (3 Jobs)

```
Job 1: validation (Ubuntu, ~30s)
  └─ Check trigger, generate version YY.MMDD.HHMM

Job 2: safety-checks (Ubuntu, ~2min)
  ├─ CHECK 1: Python Syntax (py_compile)
  ├─ CHECK 2: Module Imports (catches missing 'import sys')
  ├─ CHECK 3: Flake8 (undefined names, errors)
  ├─ CHECK 4: Security Audit (pip-audit)
  └─ CHECK 5: Pytest Tests

Job 3: build-and-release (Windows, ~10min)
  └─ Only runs if validation passes
```

### What CI Catches

| Bug Type | Check That Catches It |
|----------|----------------------|
| Missing `import sys` | CHECK 2: Module Import Validation |
| Undefined variable names | CHECK 3: Flake8 (F821/F822) |
| Syntax errors | CHECK 1: Python Syntax Validation |
| Unused imports | CHECK 3: Flake8 (F401) - warning only |
| Vulnerable dependencies | CHECK 4: pip-audit - warning only |

### Local Validation (BEFORE pushing!)

```bash
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW

# Full validation (mirrors CI)
python ci_validate.py

# Quick check (skip slow tests)
python ci_validate.py --quick

# Show fix suggestions
python ci_validate.py --fix
```

### FAIL FAST Philosophy

Validation errors stop build BEFORE PyInstaller runs (saves ~10 minutes).

## CI/CD - GitHub Actions Build

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

### Adding New Folders to Build

When adding new working folders, update **THREE places**:

1. **Workflow** (`.github/workflows/qacompiler-build.yml`):
   ```powershell
   $folders = @(
     "QAfolder",
     "TrackerUpdateFolder",
     "TrackerUpdateFolder\QAfolder",  # Subfolders too!
     ...
   )
   # Workflow creates .gitkeep files to preserve empty folders in ZIP
   ```

2. **Inno Setup** (`installer/QACompiler.iss`):
   ```ini
   ; [Files] section - copy from dist
   Source: "..\dist\QACompiler\TrackerUpdateFolder\*"; DestDir: "{app}\TrackerUpdateFolder"; Flags: ... skipifsourcedoesntexist

   ; [Dirs] section - create if not exists
   Name: "{app}\TrackerUpdateFolder"
   Name: "{app}\TrackerUpdateFolder\QAfolder"
   ```

3. **config.py** - `ensure_folders_exist()` for runtime creation

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
