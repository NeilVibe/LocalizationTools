# QA Compiler Suite v2.0 (Modular)

Modular rewrite of the QA Excel Compiler with integrated datasheet generators.

## Status: 100% COMPLETE

All modules migrated from monolith to clean modular architecture.

## Quick Start

```bash
# GUI mode (default)
python main.py

# CLI - Generate datasheets
python main.py --generate quest knowledge item
python main.py --generate all                    # All 9 categories
python main.py -g quest -g item                  # Multiple flags

# CLI - Compile QA files
python main.py --transfer                        # Transfer QA files
python main.py --build                           # Build master files
python main.py --all                             # Full pipeline

# Utilities
python main.py --list                            # List categories
python main.py --version                         # Version info
python main.py --help                            # Full help
```

## Structure

```
QACompilerNEW/
├── main.py                   # Entry point (CLI + GUI launcher)
├── config.py                 # All paths, categories, constants
├── README.md                 # This file
│
├── core/                     # Compiler core modules
│   ├── __init__.py          # Package exports
│   ├── discovery.py         # QA folder detection
│   ├── excel_ops.py         # Workbook operations
│   ├── matching.py          # Content-based row matching (shared)
│   ├── processing.py        # Sheet processing
│   ├── transfer.py          # File transfer (OLD + NEW → QAfolder)
│   ├── tracker_update.py    # Tracker-only update (no master rebuild)
│   └── compiler.py          # Main orchestration
│
├── tracker/                  # Progress tracker modules
│   ├── __init__.py          # Package exports
│   ├── data.py              # _DAILY_DATA operations
│   ├── daily.py             # DAILY sheet builder
│   └── total.py             # TOTAL sheet + rankings
│
├── generators/               # Datasheet generators (8 total)
│   ├── __init__.py          # Dispatcher + exports
│   ├── base.py              # Shared utilities (XML, Excel, styles)
│   ├── quest.py             # Quest datasheets (1286 lines)
│   ├── knowledge.py         # Knowledge datasheets (627 lines)
│   ├── item.py              # Item datasheets (565 lines)
│   ├── region.py            # Region datasheets (866 lines)
│   ├── skill.py             # Skill datasheets (528 lines)
│   ├── character.py         # Character datasheets (422 lines)
│   ├── help.py              # Help/GameAdvice datasheets (413 lines)
│   └── gimmick.py           # Gimmick datasheets (466 lines)
│
└── gui/                      # GUI module
    ├── __init__.py          # Package exports
    └── app.py               # Unified Tkinter GUI
```

## Standalone Tools

### System Sheet Localizer (`system_localizer.py`)

**Purpose:** Creates localized versions of manually-created System datasheets.

**System Datasheet Structure:**
The System category is special - it's created **manually** (not auto-generated) and contains:
- **Translation** column - The localized text
- **English** column - English reference text
- **StringID** column - Unique identifier for lookup

**2-Step Matching Process:**
1. **StringID Match** - First tries to find translation by StringID → Korean → Target Language
2. **Text Match (Fallback)** - If no StringID match: English → Korean → Target Language

**Usage:**
```bash
# GUI mode (file dialogs)
python system_localizer.py

# CLI mode
python system_localizer.py --cli <input.xlsx> <language_folder>
```

**Output:** Creates `System_LQA_All/` folder with `System_{LANG}.xlsx` for each language.

---

## Available Categories

| # | Category | Generator | Description |
|---|----------|-----------|-------------|
| 1 | Quest | `quest.py` | Main/Faction/Daily/Challenge/Minigame quests |
| 2 | Knowledge | `knowledge.py` | Knowledge entries with hierarchical groups |
| 3 | Item | `item.py` | Items with descriptions and group organization |
| 4 | Region | `region.py` | Faction/Region exploration data |
| 5 | System | (Skill+Help) | Combined category (clustering) |
| 6 | Character | `character.py` | NPC/Monster character info |
| 7 | Skill | `skill.py` | Player skills with knowledge linking |
| 8 | Help | `help.py` | GameAdvice/Help system entries |
| 9 | Gimmick | `gimmick.py` | Interactive gimmick objects |
| 10 | Contents | (manual) | Manual content review sheets, no localization |
| 11 | Sequencer | `script.py` | Script data → Master_Script.xlsx (EventName matching) |
| 12 | Dialog | `script.py` | Dialog data → Master_Script.xlsx (EventName matching) |

## Generator Details

### Quest Generator (`quest.py`)
**Source:** `fullquest15.py` (most complex)
- Multiple quest sources: Main, Faction, Daily, Challenge, Minigame
- Stage→Sequencer→Position mapping for teleport commands
- FactionKeyList/FactionNodeKeyList for faction assignment
- Teleport post-processor from reference Excel file
- Sheets: Main Quest, Faction tabs (ordered), Daily, Challenge, Minigame

### Knowledge Generator (`knowledge.py`)
**Source:** `fullknowledge14.py`
- KnowledgeGroupInfo hierarchy parsing
- One sheet per "mega root" (top-level group)
- Handles KnowledgeInfo inside CharacterInfo via KnowledgeGroupKey
- Depth-based styling for hierarchical display

### Item Generator (`item.py`)
**Source:** `fullitem25.py`
- ItemGroupInfo → ItemInfo hierarchy
- ItemDesc from KnowledgeKey lookup with fallback
- Group merging for small groups (<50 items)
- Depth-based clustering for organization

### Region Generator (`region.py`)
**Source:** `fullregion7.py`
- FactionGroup → Faction → FactionNode hierarchy
- FactionNode.Name from KnowledgeInfo lookup
- Deduplication based on (Korean, Translation, STRINGID)
- Shop data parsing

### Skill Generator (`skill.py`)
**Source:** `fullskill1.py`
- SkillInfo extraction from skillinfo_pc.staticinfo.xml
- KnowledgeKey linking with priority rule (highest MaxLevel wins)
- Nested skill/knowledge hierarchy display

### Character Generator (`character.py`)
**Source:** `fullcharacter1.py`
- CharacterInfo extraction from characterinfo_*.staticinfo.xml
- Grouped by filename pattern (NPC, Monster, etc.)
- One sheet per character group

### Help Generator (`help.py`)
**Source:** `fullgameadvice1.py` (simplest)
- GameAdviceGroupInfo/GameAdviceInfo extraction
- Single sheet with depth-based indentation

### Gimmick Generator (`gimmick.py`)
**Source:** `fullgimmick1.py`
- GimmickAttributeGroup → GimmickInfo → DropItem
- ItemInfo index for item names/descriptions
- Hierarchical sheet output

### Contents Category (Manual)
**No generator** - Manual content review sheets.

**Column Structure:**
| Col | Header | Description |
|-----|--------|-------------|
| 1 | CONTENT | Text being reviewed |
| 2 | INSTRUCTIONS | Unique identifier for row matching |
| 3 | STATUS | Tester status (ISSUE, NO ISSUE, etc.) |
| 4 | COMMENT | Tester notes |
| 5 | SCREENSHOT | Screenshot reference |

**Key Differences from Other Categories:**
- No localization (single language)
- INSTRUCTIONS used for row matching (like STRINGID in others)
- No generator - testers create sheets manually
- Outputs to `Master_Contents.xlsx` (standalone, no clustering)

## Shared Utilities (`generators/base.py`)

All generators share these utilities:

```python
# XML Processing
parse_xml_file(path)           # Parse with sanitization
iter_xml_files(folder)         # Recursive XML iteration
sanitize_xml(raw)              # Fix entities, escape newlines

# Language Tables
load_language_tables(folder)   # Load all non-Korean translations
normalize_placeholders(text)   # Normalize for matching

# Korean Detection
contains_korean(text)          # Check for Korean chars
is_good_translation(text)      # Valid = non-empty + no Korean

# Excel Styling
THIN_BORDER                    # Standard border
HEADER_FILL, HEADER_FONT       # Header styling
get_depth_fill(depth)          # Depth-based colors
autofit_worksheet(ws)          # Auto-size columns/rows

# Helpers
create_header_row(ws, headers) # Create styled header
add_status_dropdown(ws, col)   # STATUS validation dropdown
```

## Configuration (`config.py`)

### Path Configuration
```python
# Game resource paths
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# Quest-specific paths
QUESTGROUPINFO_FILE = Path(r"...\questgroupinfo.staticinfo.xml")
SCENARIO_FOLDER = Path(r"...\scenario")
FACTION_QUEST_FOLDER = Path(r"...\quest\faction")
# ... and more

# Output
DATASHEET_OUTPUT = SCRIPT_DIR / "GeneratedDatasheets"
```

### Category Clustering
```python
CATEGORY_TO_MASTER = {
    "Skill": "System",       # Skill → Master_System.xlsx
    "Help": "System",        # Help → Master_System.xlsx
    "Sequencer": "Script",   # Sequencer → Master_Script.xlsx
    "Dialog": "Script",      # Dialog → Master_Script.xlsx
}
```

### Transfer Column Mapping
System, Contents, and Script categories have unique column layouts:
```python
TRANSLATION_COLS = {
    "Quest": {"eng": 2, "other": 3},      # Standard layout
    "Knowledge": {"eng": 2, "other": 3},
    "Item": {"eng": 5, "other": 7},       # ItemName column
    "System": {"eng": 1, "other": 1},     # CONTENT column (single)
    "Contents": {"eng": 2, "other": 2},   # INSTRUCTIONS column (matching key)
    "Sequencer": {"eng": 2, "other": 3},  # Text column → Script
    "Dialog": {"eng": 2, "other": 3},     # Text column → Script
    # ... other categories use standard 2/3
}
```
System Excel layout: `CONTENT | STATUS | COMMENT | STRINGID | SCREENSHOT`
Contents Excel layout: `CONTENT | INSTRUCTIONS | STATUS | COMMENT | SCREENSHOT`
Script Excel layout: `EventName | Text | Translation | STATUS | MEMO` (no SCREENSHOT, MEMO=COMMENT)

**Script Matching Logic (Sequencer/Dialog):**
- Primary: Translation (Text) + EventName (both must match)
- Fallback: EventName ONLY (not Translation only like other categories)

## Script-Type Optimization (Sequencer/Dialog)

Sequencer and Dialog files can have **thousands of rows** (10,000+), but only a fraction have been checked (have STATUS). The compiler includes a **preprocessing optimization** that dramatically speeds up master file creation.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│  PREPROCESSING PHASE (Script-type only)                             │
├─────────────────────────────────────────────────────────────────────┤
│  1. Scan ALL QA files for the category (all testers)                │
│  2. Build GLOBAL UNIVERSE of rows WITH STATUS                       │
│     - Key: (EventName, Text)                                        │
│     - Any row with non-empty STATUS (ISSUE/NON-ISSUE/NO ISSUE/etc)  │
│  3. Create FILTERED TEMPLATE containing only active rows            │
│     - Full row data preserved (all columns)                         │
│     - Fetches from source files when needed                         │
│  4. Master built from filtered template (clean, no empty rows)      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  PROCESSING PHASE (also optimized)                                  │
├─────────────────────────────────────────────────────────────────────┤
│  - For each QA file, SKIP rows without STATUS before matching       │
│  - Only rows with STATUS are processed                              │
│  - Prints: "[OPTIMIZATION] 100 rows with STATUS (skipping 9900)"    │
└─────────────────────────────────────────────────────────────────────┘
```

### Column Detection (Script-type)

**ALL columns are detected BY NAME, not position:**

| Column | Config Key | Header Name | Purpose |
|--------|------------|-------------|---------|
| Translation | `translation` | `Text` | Text content for matching |
| StringID | `stringid` | `EventName` | Unique identifier (EventName = STRINGID) |
| Status | `status` | `STATUS` | Tester status |
| Comment | `comment` | `MEMO` | Tester notes (MEMO maps to COMMENT) |

**No SCREENSHOT column** for Script-type categories.

### Category Clustering

Both Sequencer and Dialog merge into `Master_Script.xlsx`:

```
Sequencer QA files  ─┐                    ┌─ Sequencer sheet(s)
                     ├──► Master_Script.xlsx ─┤
Dialog QA files     ─┘                    └─ Dialog sheet(s)
```

Processing order:
1. **Sequencer**: Preprocessed → filtered template → creates Master_Script.xlsx
2. **Dialog**: Preprocessed → filtered template → appends to Master_Script.xlsx

### Performance Impact

| Scenario | Without Optimization | With Optimization |
|----------|---------------------|-------------------|
| 10,000 rows, 100 with STATUS | Process all 10,000 | Process only 100 |
| Template creation | Full 10,000 row template | 100 row filtered template |
| Matching operations | 10,000 lookups | 100 lookups |

### Config (`config.py`)

```python
# Script-type categories (use preprocessing + name-based columns)
SCRIPT_TYPE_CATEGORIES = {"sequencer", "dialog"}

# Column name mapping for Script-type
SCRIPT_COLS = {
    "translation": "Text",       # Column header for text content
    "stringid": "EventName",     # EventName acts as STRINGID
    "status": "STATUS",
    "comment": "MEMO",           # MEMO maps to COMMENT
    # NO SCREENSHOT for Script-type
}
```

### Robustness (Build 016+)

The preprocessing is designed to be **fault-tolerant**:

| Feature | Behavior |
|---------|----------|
| **Any STATUS value** | If STATUS has ANY non-empty value, row is included |
| **NON-ISSUE support** | Both "NON-ISSUE" (hyphen) and "NO ISSUE" (space) accepted |
| **Safe color handling** | Handles indexed colors, None, alpha channels without crashing |
| **Error recovery** | Continues processing if one file/sheet/row fails |
| **Full tracebacks** | All errors print full traceback to terminal (not messageboxes) |
| **Edge case handling** | Empty sheets, missing columns, non-existent files handled gracefully |

### Testing

```bash
# Run Script-type preprocessing tests
cd QACompilerNEW
python3 tests/test_script_preprocessing.py

# Tests include:
# - Color handling (5 tests)
# - Preprocessing (7 tests)
# - Filtered template creation (8 tests)
# - Edge cases (5 tests)
```

## GUI Layout (1000x1000 window)

```
┌──────────────────────────────────────────────────┐
│           QA Compiler Suite v2.0                 │
├──────────────────────────────────────────────────┤
│  1. Generate Datasheets                          │
│     ☑ Quest      ☑ Knowledge   ☑ Item            │
│     ☑ Region     ☑ System      ☑ Character       │
│     ☑ Skill      ☑ Help        ☑ Gimmick         │
│     ☑ Contents                                   │
│     [Select All] [Deselect] [Generate Selected]  │
├──────────────────────────────────────────────────┤
│  2. Transfer QA Files                            │
│     QAfolderOLD + QAfolderNEW → QAfolder         │
│     [Transfer QA Files]                          │
├──────────────────────────────────────────────────┤
│  3. Build Master Files                           │
│     QAfolder → Masterfolder_EN / Masterfolder_CN │
│     [Build Master Files]                         │
├──────────────────────────────────────────────────┤
│  4. Coverage Analysis                            │
│     Calculate coverage + word counts             │
│     [Run Coverage Analysis]                      │
├──────────────────────────────────────────────────┤
│  5. System Sheet Localizer                       │
│     Create localized System versions             │
│     [Localize System Sheet]                      │
├──────────────────────────────────────────────────┤
│  6. Update Tracker Only                          │
│     Retroactive tracker updates from             │
│     TrackerUpdateFolder (no master rebuild)      │
│     Set Date: [YYYY-MM-DD] [Set File Dates...]   │
│     [Update Tracker]                             │
├──────────────────────────────────────────────────┤
│  Status: Ready                                   │
│  [═══════════════════════════════════════]       │
└──────────────────────────────────────────────────┘
```

## TrackerUpdateFolder (Retroactive Tracker Updates)

Update tracker without rebuilding master files. Useful for adding missing days.

### Folder Structure
```
TrackerUpdateFolder/
├── QAfolder/              # Tester QA files (for tester stats)
│   └── Username_Category/
│       └── file.xlsx
├── Masterfolder_EN/       # English masters (for manager stats)
│   └── Master_Quest.xlsx
└── Masterfolder_CN/       # Chinese masters (for manager stats)
    └── Master_Item.xlsx
```

### Stats Tracked
| Source | Stats |
|--------|-------|
| QAfolder | ISSUE, NO ISSUE, BLOCKED, KOREAN, word count |
| Masterfolder_EN/CN | FIXED, REPORTED, CHECKING, NON-ISSUE |

### Workflow
1. Copy QA files to `TrackerUpdateFolder/QAfolder/`
2. Copy Master files to `TrackerUpdateFolder/Masterfolder_EN/` or `Masterfolder_CN/`
3. (Optional) Set file dates via GUI → `Set File Dates...` button (select folder)
4. Click `Update Tracker` → uses file mtime as tracker date

**File date = tracker date.** Uses `os.utime()` (cross-platform).

### CLI
```bash
python main.py --update-tracker
```

---

## Output Structure

### Generated Datasheets
```
GeneratedDatasheets/
├── Character_LQA_All/
│   ├── Character_LQA_ENG.xlsx
│   └── Character_LQA_*.xlsx
├── QuestData_Map_All/
│   ├── Quest_LQA_ENG.xlsx
│   └── Quest_LQA_*.xlsx
├── ItemData_Map_All/
│   ├── Item_Full_LQA/           ← ENG files here (nested!)
│   │   ├── Item_LQA_ENG.xlsx
│   │   └── Item_LQA_*.xlsx
│   └── Item_Sorted_LQA/
├── Knowledge_LQA_All/
│   └── Knowledge_LQA_ENG.xlsx
├── Skill_LQA_All/
│   └── LQA_Skill_ENG.xlsx
├── Region_LQA_v3/
│   └── Region_LQA_ENG.xlsx
├── Gimmick_LQA_Output/
│   └── Gimmick_LQA_ENG.xlsx
└── GameAdvice_LQA_All/
    └── LQA_GameAdvice_ENG.xlsx
```

### Excel Columns (per sheet)
| Column | Description |
|--------|-------------|
| Original (KR) | Korean source text |
| English (ENG) | English translation |
| Translation (LOC) | Target language (hidden for ENG) |
| StringKey | Identifier for commands |
| Command | /complete, /teleport commands |
| STATUS | Dropdown: ISSUE, NO ISSUE, BLOCKED, KOREAN |
| COMMENT | Tester notes |
| STRINGID | Unique string identifier |
| SCREENSHOT | Screenshot reference |

## Migration from Monolith

### Original (Preserved)
```
QAExcelCompiler/
├── compile_qa.py              # 4000+ lines monolith
└── datasheet_generators/
    ├── fullquest15.py         # 1247 lines
    ├── fullknowledge14.py     # 1000+ lines
    ├── fullitem25.py          # 1400+ lines
    ├── fullregion7.py         # 1300+ lines
    ├── fullskill1.py          # 900+ lines
    ├── fullcharacter1.py      # 700+ lines
    ├── fullgameadvice1.py     # 700+ lines
    └── fullgimmick1.py        # 900+ lines
    (Total: ~40,000+ lines with duplication)
```

### New Modular (This Project)
```
QACompilerNEW/
├── Shared utilities: ~425 lines (base.py)
├── 8 generators: ~5,275 lines
├── Core modules: ~2,000 lines
├── Config: ~200 lines
(Total: ~8,000 lines - no duplication)
```

### Key Improvements
1. **No code duplication** - XML parsing, styling, language loading shared
2. **Centralized config** - All paths in one file
3. **Clean separation** - Each generator is independent
4. **CLI support** - Can run without GUI
5. **Fallback support** - Uses original scripts if needed

## Requirements

```
Python 3.8+
openpyxl
lxml
tkinter (for GUI)
```

## Testing

```bash
# Syntax check all modules
python -m py_compile generators/*.py config.py main.py

# Import test
python -c "from generators import generate_datasheets; print('OK')"

# CLI test
python main.py --list
python main.py --version
```

## Coverage Analysis (`tracker/coverage.py`)

Calculates coverage of language data by generated datasheets and produces word count reports.

### Features
1. **Coverage Report** - Match Excel Korean strings against LOC master using consume technique
2. **Word Count Table** - Count Korean + Translation words from Excel columns
3. **Additional Coverage** - Quest includes System/Quest, Item includes System/LookAt
4. **Excel Export** - Formatted word count report with colors

### Column Configuration

Coverage and word count read from these columns (1-based):

| Category | Korean Columns | Translation Columns |
|----------|----------------|---------------------|
| Character | 1 | 2 |
| Quest | 1 | 2 |
| Knowledge | 1 | 2 |
| Skill | 1 | 2 |
| Region | 1 | 2 |
| Help | 1 | 2 |
| Item | 6, 8 (Name, Desc) | 7, 9 |
| Gimmick | 6, 9, 11 (GimmickName, ItemName, ItemDesc) | 7, 10, 12 |

### Additional Sources (for Coverage)

| Category | Additional Source | Description |
|----------|-------------------|-------------|
| Quest | System/Quest | Quest system strings from export folder |
| Quest | VoiceRecordingSheet | Voice recording strings |
| Item | System/LookAt | LookAt strings from export folder |

### Output
- Terminal: Coverage report + Word count table
- Excel: `Coverage_Report_YYYYMMDD_HHMMSS.xlsx` in GeneratedDatasheets folder
  - Sheet 1: **Coverage Report** (unique strings, words covered, % coverage per category)
  - Sheet 2: **Word Count by Category** (Korean words, Translation words per category)

### Usage
```bash
# Via GUI: Click "Run Coverage Analysis" button

# Standalone (from tracker folder):
python coverage.py
```

## CI/CD - GitHub Actions Build

### ⚠️ GitHub Actions (NOT Gitea!)

**IMPORTANT:** QACompiler uses **GitHub Actions**, NOT Gitea!

| Aspect | Value |
|--------|-------|
| CI System | GitHub Actions |
| Trigger File | `QACOMPILER_BUILD.txt` |
| Push To | **GitHub only** (NOT Gitea) |
| Check Status | [GitHub Actions](https://github.com/NeilVibe/LocalizationTools/actions) |

### Two Workflows in LocalizationTools Repo

| Workflow | Trigger File | What It Builds | Output |
|----------|--------------|----------------|--------|
| **LocaNext** | `BUILD_TRIGGER.txt` | Electron desktop app | `.exe` installer |
| **QACompiler** | `QACOMPILER_BUILD.txt` | PyInstaller exe + Inno Setup | Setup + Portable + Source |

### How to Trigger QACompiler Build

```bash
# From repo root (trigger file is at ROOT, not in project folder!):
echo "Build: <description>" >> QACOMPILER_BUILD.txt
git add -A && git commit -m "Trigger QAC build" && git push origin main

# Check build progress at:
# https://github.com/NeilVibe/LocalizationTools/actions
```

### Workflow File

**Location:** `.github/workflows/qacompiler-build.yml`

**Triggers:**
- Push to `QACOMPILER_BUILD.txt` containing "Build" line
- Manual dispatch via GitHub Actions UI (workflow_dispatch)

**Build Steps:**
1. Setup Python 3.10 on Windows
2. Install dependencies from `requirements.txt`
3. Inject auto-generated version (YY.MMDD.HHMM format)
4. Build with PyInstaller
5. Create working folders (QAfolder, Masterfolder_EN, etc.)
6. Build Inno Setup installer
7. Create portable ZIP
8. Create source ZIP
9. Upload to GitHub Releases

**Output Artifacts (GitHub Releases):**
- `QACompiler_vX.X.X_Setup.exe` - Inno Setup installer (recommended)
- `QACompiler_vX.X.X_Portable.zip` - Portable version (no install needed)
- `QACompiler_vX.X.X_Source.zip` - Source code snapshot

**Version Format:** `YY.MMDD.HHMM` (auto-generated, Korean Standard Time)

Example: `26.0119.1430` = January 19, 2026 at 14:30 KST

---

## Building Executable (Local)

### Using `build_exe.bat`

The build script creates a standalone Windows executable that doesn't require Python.

```batch
# Double-click build_exe.bat or run from command line:
build_exe.bat
```

### Drive Selection Feature

**Problem:** The default LOC path uses F: drive (`F:\perforce\cd\mainline\...`), but some users have Perforce on a different drive (D:, E:, etc.).

**Solution:** The build script prompts for drive selection before building:

```
========================================
  QA Compiler Suite - Build Executable
========================================

Current default LOC path uses F: drive
(F:\perforce\cd\mainline\resource\GameData\stringtable\loc)

If your Perforce is on a different drive, enter the drive letter.
Otherwise, just press Enter to keep F: drive.

Enter drive letter (F/D/E/etc.) [F]: D

Selected drive: D:
```

**What happens:**
1. If you enter a different drive (e.g., `D`), the script automatically:
   - Backs up `config.py` and `system_localizer.py`
   - Replaces all `F:\` paths with `D:\`
   - Builds the executable with the new paths
   - Restores the original source files (keeps your repo clean)

2. If you press Enter (keep F:), no path changes are made.

**Output:**
```
dist\QACompiler\
├── QACompiler.exe          # Main executable
├── QAfolder\               # Input folder for QA files
├── Masterfolder_EN\        # Output for EN masters
├── Masterfolder_CN\        # Output for CN masters
└── ...
```

### Requirements
- Python 3.8+ with pip
- PyInstaller (auto-installed by script)

---

## Troubleshooting & Debug Logs

### Debug Log Files

| File | Purpose | When Generated |
|------|---------|----------------|
| `MATCHING_DEBUG.log` | Row matching failures (STRINGID, Translation mismatches) | During Build |
| `MANAGER_STATS_DEBUG.log` | Manager stats collection + tracker lookup phase | During Build |

### Known Issues

See `docs/ISSUE_TRACKER_MATCHING.md` and `docs/ISSUE_TRACKER_INVESTIGATION_SESSION.md` for details.

#### Issue: Tracker Shows Low or Zero Stats

**Symptoms:**
- Tester stats (Issues, No Issue, etc.) are 0 or lower than expected
- Manager stats (Fixed, Reported, etc.) show MISS in debug log

**Potential Causes:**
1. **Row matching failing** - Check `MATCHING_DEBUG.log` for `UNMATCHED` entries
2. **Script categories (Sequencer/Dialog) with no STATUS** - Pre-filter skips empty rows
3. **Master files missing** - Check `Masterfolder_EN/` and `Masterfolder_CN/`
4. **STATUS_{User} columns missing** - Check Master file headers

**Debug Steps:**
1. Run Build and check console for `[WARN] ... UNMATCHED` messages
2. Open `MATCHING_DEBUG.log` to see which rows failed and why
3. Open `MANAGER_STATS_DEBUG.log` to see lookup hits/misses

---

## Notes

- Generators require access to game resource paths (Perforce)
- Output format matches original scripts exactly
- STATUS dropdown validation on all sheets
- STRINGID formatted as text (prevents scientific notation)
- ENG column hidden for non-English workbooks
