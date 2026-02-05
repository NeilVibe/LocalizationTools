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

## EXPORT Folder Structure (CRITICAL REFERENCE)

**Full tree in:** `EXPORT PATH TREE.txt`

```
export__/
├── Dialog/
│   ├── AIDialog/           → AIDialog category
│   ├── NarrationDialog/    → NarrationDialog category
│   ├── QuestDialog/        → QuestDialog category
│   └── StageCloseDialog/   → QuestDialog category (maps to QuestDialog!)
│
├── Sequencer/              → Sequencer category (VRS-ordered)
│   ├── Faction/
│   ├── Main/
│   ├── Memory/
│   ├── Node/
│   └── ...
│
├── World/
│   ├── Character/          → Character category
│   ├── Faction/            → Faction category
│   ├── Item/               → Item category
│   ├── Knowledge/          → MIXED! See priority keywords below
│   ├── Npc/                → Character category
│   └── Region/             → Region category
│
├── System/
│   ├── Gimmick/            → Gimmick category
│   ├── LookAt/             → Item category (special rule)
│   ├── PatternDescription/ → Item category (special rule)
│   ├── Quest/              → Quest category
│   ├── Skill/              → Skill category
│   └── Ui/                 → UI category
│
├── None/
│   ├── Board/
│   ├── EquipType/
│   └── GameAdvice/
│
└── Platform/
    └── PlatformService/
```

---

## Two-Tier Clustering Algorithm (UPDATED)

### Tier 1: STORY Categories (VRS-Ordered)

| Category | Source Folder | Notes |
|----------|---------------|-------|
| **Sequencer** | Sequencer/ | All sequencer files, VRS-ordered |
| **AIDialog** | Dialog/AIDialog/ | Default for unknown dialog |
| **QuestDialog** | Dialog/QuestDialog/ + Dialog/StageCloseDialog/ | StageCloseDialog maps here! |
| **NarrationDialog** | Dialog/NarrationDialog/ | Tutorials, narration |

### Tier 2: GAME_DATA Categories (Priority Keywords!)

**CRITICAL: Priority keywords are checked FIRST, before folder matching!**

#### Priority Keywords (checked BEFORE folder)

| Keyword | → Category | Example |
|---------|------------|---------|
| `item` | Item | `KnowledgeInfo_Item.xml` → Item (not Knowledge) |
| `quest` | Quest | `KnowledgeInfo_Quest.xml` → Quest |
| `skill` | Skill | `KnowledgeInfo_Skill.xml` → Skill |
| `character` | Character | `characterinfo_monster.xml` → Character |
| `faction` | Faction | `KnowledgeInfo_Faction.xml` → Faction |
| `region` | Region | - |

#### Standard Folder Matching (if no priority keyword)

| Category | Folders | Fallback Keywords |
|----------|---------|-------------------|
| Item | LookAt/, PatternDescription/ | weapon, armor, itemequip |
| Quest | Quest/ | schedule_ |
| Character | Character/, Npc/ | monster, animal |
| Gimmick | Gimmick/ | - |
| Skill | Skill/ | - |
| Knowledge | Knowledge/ | (only if no priority keyword) |
| Faction | Faction/ | - |
| UI | Ui/ | localstringinfo, symboltext |
| Region | Region/ | - |
| System_Misc | (default) | - |

### Example: Knowledge Folder Categorization

Files in `World/Knowledge/`:
```
KnowledgeInfo_Item.xml        → Item (priority: "item")
KnowledgeInfo_Quest.xml       → Quest (priority: "quest")
KnowledgeInfo_Skill.xml       → Skill (priority: "skill")
KnowledgeInfo_Character.xml   → Character (priority: "character")
KnowledgeInfo_Faction.xml     → Faction (priority: "faction")
characterinfo_monster.xml     → Character (priority: "character")
item_food.xml                 → Item (priority: "item")
KnowledgeInfo_AbyssGate.xml   → Knowledge (no priority keyword)
KnowledgeInfo_Contents.xml    → Knowledge (no priority keyword)
KnowledgeInfo_Discover.xml    → Knowledge (no priority keyword)
```

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
├── EXPORT PATH TREE.txt           # Full EXPORT folder structure reference
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
│   └── excel_report.py           # Unified Excel report (2 sheets)
│
├── utils/                         # Shared utilities
│   ├── __init__.py               # Package exports
│   ├── language_utils.py         # Korean detection, language config
│   └── vrs_ordering.py           # VoiceRecordingSheet ordering
│
├── gui/                           # tkinter GUI (simplified v3.0)
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

## GUI v3.0 (Simplified)

**Changes in Build 014:**
- **Removed** language selection (always ALL languages except KOR)
- **Removed** folder path editing (fixed from settings.json)
- Shows paths as **read-only** with OK/NOT FOUND status
- Two main buttons: "Generate Word Count Report" + "Generate Language Excels"

**Excluded Language:** KOR (Korean is source, not target)

---

## Word Count Report Format (Build 014)

**ONE unified Excel file** with two sheets:

### Sheet 1: General Summary
One row per language showing totals:
| Language | Total Strings | Korean Words | Translation Count | Untranslated | Count Type |
|----------|---------------|--------------|-------------------|--------------|------------|
| English | 50,000 | 120,000 | 118,500 | 150 | Words |
| Japanese | 50,000 | 120,000 | 450,000 | 200 | Characters |

### Sheet 2: Detailed Summary
All language tables stacked vertically with nice titles:
```
┌─────────────────────────────────────────┐
│ English (Words)                         │
├─────────────────────────────────────────┤
│ Category | Strings | Korean | Trans | UT│
├─────────────────────────────────────────┤
│ Sequencer | 5,000 | 15,000 | 14,800| 20 │
│ AIDialog  | 8,000 | 24,000 | 23,500| 50 │
│ ...       |       |        |       |    │
│ TOTAL     |50,000 |120,000 |118,500|150 │
└─────────────────────────────────────────┘

(blank rows)

┌─────────────────────────────────────────┐
│ Japanese (Characters)                   │
├─────────────────────────────────────────┤
│ ...                                     │
└─────────────────────────────────────────┘
```

---

## XML Parsing (CRITICAL)

### Parser Selection
```python
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
1. Fix unescaped ampersands (`&` → `&amp;`)
2. Handle newlines in `<seg>` elements
3. Fix `<` and `&` in attribute values
4. **Tag stack repair** for malformed XML
5. Remove invalid control characters
6. **lxml recovery mode** for corrupted files

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

## Excel Column Structure

### Current Columns (Build 015+)

| Column | Editable? | Purpose |
|--------|-----------|---------|
| StrOrigin | LOCKED | Source Korean text |
| ENG | LOCKED | English reference (EU languages only) |
| Str | LOCKED | Current translation |
| Correction | EDITABLE | LQA correction field |
| Text State | LOCKED | Auto-filled: "KOREAN" or "TRANSLATED" |
| MEMO1 | EDITABLE | QA notes field 1 |
| MEMO2 | EDITABLE | QA notes field 2 |
| MEMO3 | EDITABLE | QA notes field 3 |
| Category | LOCKED | Category classification |
| StringID | LOCKED | Unique identifier |

### Text State Logic
- **KOREAN** = `Str` column contains Korean characters (untranslated)
- **TRANSLATED** = No Korean characters in `Str` column

Uses `contains_korean()` from `utils/language_utils.py` for detection.

---

## CI/CD Pipeline

### IMPORTANT: GitHub Actions (NOT Gitea!)

**LanguageDataExporter builds on GitHub Actions, NOT Gitea.**

| Project | CI Platform | Trigger File |
|---------|-------------|--------------|
| **LanguageDataExporter** | GitHub Actions | `LANGUAGEDATAEXPORTER_BUILD.txt` |
| LocaNext | Gitea Actions | `GITEA_TRIGGER.txt` |
| QACompilerNEW | GitHub Actions | `QACOMPILER_BUILD.txt` |

### Build Trigger
```bash
# Push to GitHub only (GitHub Actions)
echo "Build 025 - Description" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add LANGUAGEDATAEXPORTER_BUILD.txt
git commit -m "Build 025: Description"
git push origin main
```

### Workflow File
**Location:** `.github/workflows/languagedataexporter-build.yml`

**Jobs:**
1. **validate** - Check trigger, generate version (YY.MMDD.HHMM format)
2. **safety-checks** - Comprehensive validation:
   - `py_compile` - Syntax validation for ALL .py files
   - Import validation - Test all critical imports
   - **Direct module imports** - `python -c "import X"` for each module
   - Full app test - `python main.py --help`
   - **Flake8 critical errors** - NO `|| true` (fails build!)
   - **Comprehensive module validation** - Tests ALL exports
   - **Runtime function tests** - Actually runs key functions
   - pip-audit - Security vulnerability scan
3. **build-release** - PyInstaller + Inno Setup → GitHub Release

**Three Separate Artifacts:**
| Artifact | Description |
|----------|-------------|
| `*_Setup.exe` | Installer with drive selection wizard |
| `*_Portable.zip` | Standalone exe + working folders |
| `*_Source.zip` | Python source (excludes build artifacts) |

---

## Build History

### Build 014 - Simplified UI + Unified Report
- GUI v3.0: Removed language/folder selection
- ONE unified WordCountReport.xlsx with 2 sheets
- Always exports ALL languages except KOR

### Build 013 - Relative Import Fix
- Fixed `from ..utils` → `from utils` (absolute imports)
- Added direct `python -c "import X"` CI tests

### Build 012 - Lambda Bug + MEGA CI
- Fixed GUI lambda closure bug
- Removed `|| true` from Flake8 (now fails build)
- Added comprehensive validation tests

### Build 011 - CI/CD + PyInstaller Fix
- Full app test (`--help`)
- Modules in `hiddenimports`, NOT `datas`

### Build 010 - Case-Insensitive Everything
- ALL attribute/tag names case-insensitive

### Build 009 - lxml + Correct Attributes
- lxml with recovery mode
- Fixed `StringId` not `StringID`

### Build 008 - GUI Default
- GUI launches by default

---

## Key Files by Task

| Task | Primary File |
|------|--------------|
| XML parsing | `exporter/xml_parser.py` |
| Category assignment | `exporter/category_mapper.py` |
| **Priority keywords** | `clustering/gamedata_clusterer.py` |
| Excel generation | `exporter/excel_writer.py` |
| VRS ordering | `utils/vrs_ordering.py` |
| Word counting | `reports/word_counter.py` |
| Report generation | `reports/excel_report.py` |
| Korean detection | `utils/language_utils.py` |
| GUI | `gui/app.py` |
| Configuration | `config.py` |
| **EXPORT structure** | `EXPORT PATH TREE.txt` |

---

## Common Tasks

### Fix Category Assignment (Priority Keywords)
1. Edit `clustering/gamedata_clusterer.py`:
   - Add keyword to `PRIORITY_KEYWORDS` list
   - Or modify `GAMEDATA_PATTERNS` order
2. Edit `exporter/category_mapper.py` - Same changes
3. Test: `python main.py --list-categories`

### Add New Category
1. Edit `config.py` - Add to `STORY_CATEGORIES` or `GAMEDATA_CATEGORIES`
2. Edit `config.py` - Add color to `CATEGORY_COLORS`
3. Edit `category_mapper.py` - Add mapping logic
4. Edit `category_clusters.json` - Update configuration

### Debug VRS Ordering
```python
from utils.vrs_ordering import VRSOrderer
from config import VOICE_RECORDING_FOLDER
orderer = VRSOrderer(VOICE_RECORDING_FOLDER)
orderer.load()
print(f"Loaded {orderer.total_events} events")
```

---

## Dependencies

```
xlsxwriter>=3.1.0  # Excel file generation (PREFERRED - reliable, powerful!)
lxml>=4.9.0        # Fast XML parsing (optional)
```

Standard library: tkinter, xml.etree.ElementTree, json, logging, pathlib, re, dataclasses

---

## Excel Library Paradigm (IMPORTANT!)

**Use xlsxwriter, NOT openpyxl for writing Excel files:**

| | xlsxwriter | openpyxl |
|--|------------|----------|
| Writing | Excellent - just works | Buggy, unreliable |
| Install | `pip install` and done | Dependency issues |
| Sheet protection | Works perfectly | Hit or miss |
| Reading files | Cannot (write-only) | Can read |

**Sheet Protection Pattern (excel_writer.py):**
```python
# Lock all cells by default, unlock specific columns
cell_format_locked = wb.add_format({'locked': True})
cell_format_unlocked = wb.add_format({'locked': False})

# Apply unlocked format to editable cells (e.g., Correction column)
ws.write(row, correction_col, value, cell_format_unlocked)

# Activate protection (makes locked property effective)
ws.protect('')
```

**Only use openpyxl if you need to READ existing Excel files.**
