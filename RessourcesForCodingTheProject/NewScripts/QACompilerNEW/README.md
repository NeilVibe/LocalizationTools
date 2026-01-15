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
│   ├── processing.py        # Sheet processing
│   ├── transfer.py          # File transfer (OLD + NEW → QAfolder)
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
    "Skill": "System",   # Skill → Master_System.xlsx
    "Help": "System",    # Help → Master_System.xlsx
}
```

### Transfer Column Mapping
System category has a unique column layout (CONTENT in col 1):
```python
TRANSLATION_COLS = {
    "Quest": {"eng": 2, "other": 3},      # Standard layout
    "Knowledge": {"eng": 2, "other": 3},
    "Item": {"eng": 5, "other": 7},       # ItemName column
    "System": {"eng": 1, "other": 1},     # CONTENT column (single)
    # ... other categories use standard 2/3
}
```
System Excel layout: `CONTENT | STATUS | COMMENT | STRINGID | SCREENSHOT`

## GUI Layout

```
┌──────────────────────────────────────────────────┐
│           QA Compiler Suite v2.0                 │
├──────────────────────────────────────────────────┤
│  1. Generate Datasheets                          │
│     ☑ Quest      ☑ Knowledge   ☑ Item            │
│     ☑ Region     ☑ System      ☑ Character       │
│     ☑ Skill      ☑ Help        ☑ Gimmick         │
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
│  Status: Ready                                   │
│  [═══════════════════════════════════════]       │
└──────────────────────────────────────────────────┘
```

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

## Notes

- Generators require access to game resource paths (Perforce)
- Output format matches original scripts exactly
- STATUS dropdown validation on all sheets
- STRINGID formatted as text (prevents scientific notation)
- ENG column hidden for non-English workbooks
