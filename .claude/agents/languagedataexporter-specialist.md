---
name: languagedataexporter-specialist
description: LanguageDataExporter project specialist. Use when working on language data export, category clustering, VRS ordering, word count reports, or GUI operations.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# LanguageDataExporter Specialist

## Project Overview

**LanguageDataExporter** converts `languagedata_*.xml` files into categorized Excel sheets with VoiceRecordingSheet-based story ordering.

**Location:** `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/`

**Key Purpose:**
- Export language strings to Excel for LQA review
- Categorize strings using two-tier clustering (STORY + GAME_DATA)
- Order STORY strings chronologically using VoiceRecordingSheet
- Generate word count reports for LQA scheduling
- Support 17 languages with proper word/character counting

---

## Complete File Structure

```
LanguageDataExporter/
├── main.py                        # CLI entry point, argument parsing
├── config.py                      # Configuration constants (paths, categories, colors)
├── category_clusters.json         # Category clustering configuration
├── settings.json                  # Runtime config (created by installer)
├── requirements.txt               # Python dependencies (openpyxl, lxml)
├── drive_replacer.py              # Drive letter configuration utility
├── LanguageDataExporter.spec      # PyInstaller build configuration
├── README.md                      # Project documentation
│
├── exporter/                      # Core export logic
│   ├── __init__.py               # Package exports
│   ├── xml_parser.py             # XML parsing + SoundEventName extraction
│   ├── category_mapper.py        # Two-tier clustering algorithm
│   └── excel_writer.py           # Excel output with VRS ordering
│
├── reports/                       # Word count reporting
│   ├── __init__.py               # Package exports
│   ├── word_counter.py           # Word/character counting logic
│   ├── report_generator.py       # Report data structures
│   └── excel_report.py           # Styled Excel report output
│
├── utils/                         # Shared utilities
│   ├── __init__.py               # Package exports
│   ├── language_utils.py         # Korean detection, language config
│   └── vrs_ordering.py           # VoiceRecordingSheet ordering
│
├── gui/                           # tkinter GUI
│   ├── __init__.py               # Package exports
│   └── app.py                    # Main GUI application
│
├── clustering/                    # Category clustering modules
│   ├── __init__.py               # Package exports
│   ├── tier_classifier.py        # STORY vs GAME_DATA classification
│   ├── dialog_clusterer.py       # Dialog category assignment
│   ├── sequencer_clusterer.py    # Sequencer category assignment
│   └── gamedata_clusterer.py     # Game data keyword matching
│
├── installer/                     # Inno Setup installer
│   └── LanguageDataExporter.iss  # Installer script with drive selection
│
└── GeneratedExcel/                # Output folder (created at runtime)
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Excel Generation | openpyxl |
| XML Parsing | lxml (primary) with ElementTree fallback |
| GUI | tkinter |
| Packaging | PyInstaller |
| Installer | Inno Setup |
| CI/CD | GitHub Actions |

---

## XML Parsing (CRITICAL)

### Parser Selection
```python
# Uses lxml if available, falls back to ElementTree
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False
```

### Case-Insensitive Attribute Matching
**ALL attribute lookups try multiple case variations:**

| Attribute | Variations Checked |
|-----------|-------------------|
| StringId | `StringId`, `StringID`, `stringid`, `STRINGID` |
| StrOrigin | `StrOrigin`, `Strorigin`, `strorigin`, `STRORIGIN` |
| Str | `Str`, `str`, `STR` |
| SoundEventName | `SoundEventName`, `soundeventname`, `SOUNDEVENTNAME`, `EventName`, `eventname` |
| LocStr (tag) | `LocStr`, `locstr`, `LOCSTR` |

### XML Sanitization (from QACompiler)
The parser includes battle-tested sanitization:
1. Fix unescaped ampersands (`&` → `&amp;`)
2. Handle newlines in `<seg>` elements
3. Fix `<` and `&` in attribute values
4. **Tag stack repair** for malformed XML
5. Remove invalid control characters
6. **lxml recovery mode** for corrupted files

### Key Functions
| Function | Purpose |
|----------|---------|
| `sanitize_xml_content()` | Clean malformed XML |
| `parse_language_file()` | Parse languagedata_*.xml |
| `parse_export_file()` | Extract StringIds from .loc.xml |
| `parse_export_with_soundevent()` | Extract StringId + SoundEventName |
| `build_stringid_soundevent_map()` | Build StringId→SoundEventName mapping |
| `_find_folder_case_insensitive()` | Cross-platform folder matching |

---

## Data Flow Pipeline

```
1. INPUT
   ├── languagedata_*.xml (LOC_FOLDER) → Source strings
   ├── *.loc.xml (EXPORT_FOLDER) → Category + SoundEventName
   └── VoiceRecordingSheet.xlsx → EventName ordering

2. PROCESSING
   ├── xml_parser.py → Extract LocStr elements
   ├── category_mapper.py → Assign categories (two-tier)
   ├── vrs_ordering.py → Load VRS EventName order
   └── word_counter.py → Count words/characters

3. OUTPUT
   ├── LanguageData_{LANG}.xlsx → Per-language Excel
   ├── WordCountReport.xlsx → Word count summary
   └── _Summary.xlsx → Export statistics
```

---

## Two-Tier Clustering Algorithm

### Tier 1: STORY Categories (VRS-Ordered)

| Category | Source | Assignment |
|----------|--------|------------|
| Sequencer | Sequencer/ folder | All sequencer files |
| AIDialog | Dialog/AIDialog/ | AI/ambient dialog (DEFAULT for unknown dialog) |
| QuestDialog | Dialog/QuestDialog/ + Dialog/StageCloseDialog/ | Quest-related |
| NarrationDialog | Dialog/NarrationDialog/ | Narration/tutorials |

**Dialog Folder Mapping (case-insensitive):**
```python
DIALOG_CATEGORIES = {
    "aidialog": "AIDialog",
    "narrationdialog": "NarrationDialog",
    "questdialog": "QuestDialog",
    "stageclosedialog": "QuestDialog",  # Maps to QuestDialog!
}
# Default: AIDialog (for unknown dialog subfolders)
```

**VRS Ordering:** STORY strings sorted by VoiceRecordingSheet EventName (Column W) for chronological story order.

### Tier 2: GAME_DATA Categories (Keyword-Based)

| Category | Folders | Keywords |
|----------|---------|----------|
| Item | LookAt/, PatternDescription/ | item, weapon, armor, itemequip |
| Quest | Quest/ | quest, schedule_ |
| Character | Character/, Npc/ | monster, animal |
| Gimmick | Gimmick/ | - |
| Skill | Skill/ | - |
| Knowledge | Knowledge/ | - |
| Faction | Faction/ | - |
| UI | Ui/ | localstringinfo, symboltext |
| Region | Region/ | - |
| System_Misc | (default) | - |

---

## VRS Ordering System

**Purpose:** Sort STORY strings in chronological story order for LQA review.

**How it works:**
1. Find most recent `.xlsx` in `VOICE_RECORDING_FOLDER`
2. Extract EventName from Column W (index 22)
3. Build `{EventName: position}` mapping
4. Parse EXPORT XML for SoundEventName attribute
5. Build `{StringID: SoundEventName}` mapping
6. Sort entries by VRS position

**Key Files:**
- `utils/vrs_ordering.py` - VRSOrderer class
- `exporter/xml_parser.py` - `build_stringid_soundevent_map()`
- `exporter/excel_writer.py` - `_sort_entries_for_output()`

---

## Language Configuration

### Word Count Languages (space-separated)
```python
WORD_COUNT_LANGUAGES = {
    "eng", "fre", "ger", "spa", "por", "ita", "rus", "tur", "pol",
    "kor", "tha", "vie", "ind", "msa"
}
```

### Character Count Languages (CJK)
```python
CHAR_COUNT_LANGUAGES = {"jpn", "zho-cn", "zho-tw"}
```

### English Column Inclusion
- **Include:** fre, ger, spa, por, ita, rus, tur, pol, kor, tha, vie, ind, msa
- **Exclude:** eng, jpn, zho-cn, zho-tw

---

## Category Colors (wordcount6.py style)

| Category | Color | Hex |
|----------|-------|-----|
| Sequencer | Light Orange | FFE599 |
| AIDialog | Light Green | C6EFCE |
| QuestDialog | Light Green | C6EFCE |
| NarrationDialog | Light Green | C6EFCE |
| Item | Light Purple | D9D2E9 |
| Quest | Light Purple | D9D2E9 |
| Character | Light Peach | F8CBAD |
| Gimmick | Light Purple | D9D2E9 |
| Skill | Light Purple | D9D2E9 |
| Knowledge | Light Purple | D9D2E9 |
| Faction | Light Purple | D9D2E9 |
| UI | Light Teal | A9D08E |
| Region | Light Peach | F8CBAD |
| System_Misc | Light Grey | D9D9D9 |
| Uncategorized | Light Brown | DDD9C4 |

---

## Configuration Paths (config.py)

```python
# Perforce paths (default F: drive)
LOC_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")
VOICE_RECORDING_FOLDER = Path(r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__")

# Output
OUTPUT_FOLDER = SCRIPT_DIR / "GeneratedExcel"
```

---

## GUI Sections

### Main Window (gui/app.py)
1. **Folder Selection** - LOC, EXPORT, VRS, Output paths
2. **Language Selection** - Checkboxes with Select All/Deselect All
3. **Action Buttons**:
   - Analyze Categories - Show distribution
   - Generate Language Excels - Per-language output
   - Generate Word Count Report - Summary report
   - Generate All - Both outputs
4. **Progress Bar** - Visual feedback
5. **Status Display** - Current operation
6. **VRS Status** - Shows if VRS ordering is available

---

## CLI Commands

```bash
# Default (GUI)
python main.py                      # Launch GUI (default!)

# CLI mode
python main.py --cli                # Convert all languages (CLI)
python main.py --lang eng           # Single language (CLI)
python main.py --lang eng,fre,ger   # Multiple languages (CLI)

# Reports (CLI)
python main.py --word-count         # Include word count report
python main.py --word-count-only    # Only word count report

# Analysis (CLI)
python main.py --list-categories    # Show category distribution
python main.py --dry-run            # Preview without writing

# Debug
python main.py -v                   # Verbose logging
```

---

## Common Tasks

### Add New Category
1. Edit `config.py` - Add to `STORY_CATEGORIES` or `GAMEDATA_CATEGORIES`
2. Edit `config.py` - Add color to `CATEGORY_COLORS`
3. Edit `category_mapper.py` - Add mapping logic in `TwoTierCategoryMapper`
4. Edit `category_clusters.json` - Update configuration

### Fix Category Assignment
1. Check `exporter/category_mapper.py` - `TwoTierCategoryMapper` class
2. Review `DIALOG_CATEGORIES` dict for dialog mapping
3. Review `GAMEDATA_PATTERNS` list for keyword matching

### Add New Language
1. Edit `utils/language_utils.py` - Add to appropriate set:
   - `WORD_COUNT_LANGUAGES` or `CHAR_COUNT_LANGUAGES`
   - `ENGLISH_COLUMN_LANGUAGES` or `NO_ENGLISH_COLUMN_LANGUAGES`
2. Edit `config.py` - Add to `LANGUAGE_NAMES` dict

### Debug VRS Ordering
1. Check VRS folder path: `config.py` → `VOICE_RECORDING_FOLDER`
2. Test VRS loading:
   ```python
   from utils.vrs_ordering import VRSOrderer
   from config import VOICE_RECORDING_FOLDER
   orderer = VRSOrderer(VOICE_RECORDING_FOLDER)
   orderer.load()
   print(f"Loaded {orderer.total_events} events")
   ```
3. Check SoundEventName extraction:
   ```python
   from exporter.xml_parser import build_stringid_soundevent_map
   from config import EXPORT_FOLDER
   mapping = build_stringid_soundevent_map(EXPORT_FOLDER)
   print(f"Found {len(mapping)} StringID → SoundEventName mappings")
   ```

---

## Key Files by Task

| Task | Primary File |
|------|--------------|
| XML parsing | `exporter/xml_parser.py` |
| Category assignment | `exporter/category_mapper.py` |
| Excel generation | `exporter/excel_writer.py` |
| VRS ordering | `utils/vrs_ordering.py` |
| Word counting | `reports/word_counter.py` |
| Report generation | `reports/excel_report.py` |
| Korean detection | `utils/language_utils.py` |
| GUI | `gui/app.py` |
| Configuration | `config.py` |

---

## CI/CD Pipeline

### Build Trigger
```bash
echo "Build 011" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add -A && git commit -m "Build: LanguageDataExporter" && git push
```

### GitHub Actions Workflow
File: `.github/workflows/languagedataexporter-build.yml`

**Jobs:**
1. **validate** - Check trigger, generate version (YY.MMDD.HHMM format)
2. **safety-checks** - Comprehensive validation (see below)
3. **build-release** - PyInstaller + Inno Setup → GitHub Release

### Safety Checks (Build 011+)
| Check | Purpose |
|-------|---------|
| `py_compile` | Syntax validation for ALL .py files |
| Import validation | Test all critical imports work |
| GUI import test | Verify `from gui import launch_gui` works |
| Full app test | Run `python main.py --help` |
| flake8 | Critical errors only (E9,F63,F7,F82) |
| pip-audit | Security vulnerability scan |
| pytest | Run tests (continue-on-error for Windows-specific) |

**Artifact Creation (QACompiler-style):**
- All artifacts centralized in `installer_output/` folder
- Working folders include `.gitkeep` for structure preservation
- Source ZIP uses temp directory for clean packaging

**Three Separate Artifacts:**
| Artifact | Description |
|----------|-------------|
| `*_Setup.exe` | Installer with drive selection wizard |
| `*_Portable.zip` | Standalone exe + working folders |
| `*_Source.zip` | Python source (excludes build artifacts) |

### PyInstaller Spec (CRITICAL)
**DO NOT copy Python packages as data files!**
```python
# WRONG - breaks relative imports
datas=[('exporter', 'exporter')]

# CORRECT - let PyInstaller analyze imports
hiddenimports=['exporter', 'exporter.xml_parser', ...]
```

---

## Testing Commands

```bash
# Syntax check
cd RessourcesForCodingTheProject/NewScripts/LanguageDataExporter
python -m py_compile main.py config.py

# Import validation
python -c "
from config import STORY_CATEGORIES, CATEGORY_COLORS
from utils import VRSOrderer, contains_korean
from exporter import parse_language_file, build_stringid_category_index
print('All imports OK')
"

# List categories (quick test)
python main.py --list-categories

# Dry run (no output files)
python main.py --dry-run --lang eng
```

---

## Runtime Configuration (settings.json)

The installer creates `settings.json` with user-selected paths. This file is **loaded at runtime** by `config.py`.

**Format:**
```json
{
  "drive_letter": "F",
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__"
}
```

**How it works:**
1. Installer prompts for drive letter during installation
2. Creates `settings.json` with full paths using selected drive
3. `config.py` loads settings.json at module import time
4. Falls back to F: drive defaults if file missing/invalid

**To change paths after install:** Edit `settings.json` directly.

---

## Recent Features / Build History

### Build 011 - CI/CD + PyInstaller Fix
- Improved CI with full app test (`--help`)
- Fixed PyInstaller spec (modules as hiddenimports, NOT datas)
- Fixes "ValueError: attempted relative import beyond top-level package"

### Build 010 - Case-Insensitive Everything
- ALL attribute/tag names case-insensitive
- StringId, StrOrigin, Str, SoundEventName, LocStr variations

### Build 009 - lxml + Correct Attributes
- Use lxml with recovery mode (like QACompiler)
- Fixed attribute name: `StringId` not `StringID`
- Battle-tested XML sanitization

### Build 008 - GUI Default
- GUI launches by default (just double-click)
- Use `--cli` flag for command-line mode

### Build 007 - Debug Logging
- Comprehensive debug output for troubleshooting
- Shows path resolution, folder discovery, XML parsing

### Build 006 - Settings.json Loading
- settings.json properly loaded at runtime
- Case-insensitive folder matching
- Fixes "No StringID to Category mapping found"

### Build 005 - VRS Ordering + Triple Artifacts
- VoiceRecordingSheet-based story ordering
- QACompiler-style Setup/Portable/Source artifacts

### Core Features
- Two-tier clustering (4 STORY + 10 GAME_DATA categories)
- Word/character counting (17 languages)
- Korean detection for untranslated text

---

## Debugging Tips

### Interpreting Debug Output
The app prints extensive debug info with `[DEBUG ...]` prefixes:

```
[DEBUG CONFIG] settings.json exists? True/False
[DEBUG CONFIG] LOC_FOLDER = ... exists? True/False
[DEBUG XML_PARSER] Using lxml for XML parsing
[DEBUG XML_PARSER] Found X LocStr elements
[DEBUG CATEGORY_MAPPER] Files processed: X, StringIDs found: Y
```

**Key things to check:**
1. `settings.json exists?` - Is runtime config loaded?
2. `LOC_FOLDER exists?` - Are paths correct?
3. `Using lxml` - Is lxml available?
4. `Found X LocStr elements` - Are entries being parsed?
5. `StringIDs found: Y` - Are mappings being built?

### VRS Not Loading
1. Check path exists: `ls -la F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__`
2. Check for `.xlsx` files in folder
3. Enable verbose logging: `python main.py -v`

### Categories Wrong
1. Run `python main.py --list-categories` to see distribution
2. Check `exporter/category_mapper.py` mapping logic
3. Verify EXPORT folder structure matches expected paths

### Excel Output Issues
1. Check `GeneratedExcel/` folder permissions
2. Verify openpyxl installed: `pip show openpyxl`
3. Test with single language: `python main.py --lang eng`

### No StringIDs Found
1. Check debug output: `[DEBUG XML_PARSER] Found X LocStr elements`
2. Verify attribute names match (case variations are tried)
3. Check if EXPORT folder has .loc.xml files
4. Ensure lxml is installed: `pip show lxml`

### Import Errors (ValueError)
1. Check PyInstaller spec doesn't copy modules as datas
2. Modules must be in `hiddenimports`, NOT `datas`
3. Run `python main.py --help` to test import chain

---

## Dependencies

```
openpyxl>=3.1.0    # Excel file generation
lxml>=4.9.0        # Fast XML parsing (optional)
```

Standard library: tkinter, xml.etree.ElementTree, json, logging, pathlib, re, dataclasses
