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
| XML Parsing | xml.etree.ElementTree, lxml |
| GUI | tkinter |
| Packaging | PyInstaller |
| Installer | Inno Setup |
| CI/CD | GitHub Actions |

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
| AIDialog | Dialog/AIDialog/ | AI/ambient dialog |
| QuestDialog | Dialog/QuestDialog/ + StageCloseDialog | Quest-related |
| NarrationDialog | Dialog/NarrationDialog/ | Narration/tutorials |

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
# Basic usage
python main.py                      # Convert all languages
python main.py --lang eng           # Single language
python main.py --lang eng,fre,ger   # Multiple languages

# Reports
python main.py --word-count         # Include word count report
python main.py --word-count-only    # Only word count report

# Analysis
python main.py --list-categories    # Show category distribution
python main.py --dry-run            # Preview without writing

# GUI
python main.py --gui                # Launch GUI

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
echo "Build 005" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add -A && git commit -m "Build: LanguageDataExporter" && git push
```

### GitHub Actions Workflow
File: `.github/workflows/languagedataexporter-build.yml`

**Jobs:**
1. **validate** - Check trigger, generate version (YY.MMDD.HHMM format)
2. **safety-checks** - Syntax, imports, flake8, pip-audit security
3. **build-release** - PyInstaller + Inno Setup → GitHub Release

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

**Separate Upload Artifacts:**
- `LanguageDataExporter-Setup`
- `LanguageDataExporter-Portable`
- `LanguageDataExporter-Source`

**Artifacts:**
- `LanguageDataExporter_v{VERSION}_Setup.exe`
- `LanguageDataExporter_v{VERSION}_Portable.zip`
- `LanguageDataExporter_v{VERSION}_Source.zip`

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

## Recent Features

### VRS Ordering (Latest)
- Chronological story ordering via VoiceRecordingSheet
- EventName → SoundEventName mapping
- STORY categories sorted by VRS position

### Two-Tier Clustering
- Simplified to 4 STORY categories
- GAME_DATA keyword-based clustering
- Color-coded Excel output

### Word Count Reports
- Per-language word/character counting
- Korean detection for untranslated text
- Summary sheet across all languages

---

## Debugging Tips

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

---

## Dependencies

```
openpyxl>=3.1.0    # Excel file generation
lxml>=4.9.0        # Fast XML parsing (optional)
```

Standard library: tkinter, xml.etree.ElementTree, json, logging, pathlib, re, dataclasses
