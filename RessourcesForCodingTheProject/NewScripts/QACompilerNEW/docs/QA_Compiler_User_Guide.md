# QA Compiler Suite v2.0 - Complete User Guide

---

## Table of Contents

1. [Overview](#1-overview)
2. [Requirements](#2-requirements)
3. [Installation & Setup](#3-installation--setup)
4. [Folder Structure](#4-folder-structure)
5. [Configuration](#5-configuration)
6. [Functionalities](#6-functionalities)
   - [6.1 Generate Datasheets](#61-generate-datasheets)
   - [6.2 Transfer QA Files](#62-transfer-qa-files)
   - [6.3 Build Master Files](#63-build-master-files)
   - [6.4 Coverage Analysis](#64-coverage-analysis)
7. [GUI Usage](#7-gui-usage)
8. [CLI Usage](#8-cli-usage)
9. [Tester Mapping](#9-tester-mapping)
10. [Categories & Generators](#10-categories--generators)
11. [Output Files](#11-output-files)
12. [Workflow Examples](#12-workflow-examples)
13. [Best Practices](#13-best-practices)
14. [Troubleshooting](#14-troubleshooting)
15. [Appendix](#15-appendix)

---

## 1. Overview

The **QA Compiler Suite v2.0** is a unified tool for managing Language Quality Assurance (LQA) workflows. It provides:

- **Datasheet Generation**: Create Excel datasheets from game XML sources for QA testers
- **File Transfer**: Transfer tester work between folder structures while preserving STATUS/COMMENT/SCREENSHOT data
- **Master File Building**: Compile individual QA files into centralized Master files with progress tracking
- **Coverage Analysis**: Calculate and report coverage statistics and word counts

### Key Features

| Feature | Description |
|---------|-------------|
| EN/CN Separation | Automatic routing of testers to English or Chinese master files |
| Manager Workflow | STATUS columns for FIXED/REPORTED/CHECKING/NON-ISSUE tracking |
| Progress Tracker | Automatic daily/total statistics with rankings |
| Category Clustering | Skill and Help merge into System; Gimmick merges into Item |
| Image Handling | Automatic image copying with hyperlink preservation |

---

## 2. Requirements

### Software Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Required |
| openpyxl | Latest | Excel file handling |
| lxml | Latest | XML parsing |
| tkinter | Built-in | GUI (included with Python) |

### Installation

```bash
pip install openpyxl lxml
```

### Access Requirements

- Read access to game resource paths (Perforce workspace)
- Write access to output folders
- Network access to `F:\perforce\cd\mainline\` (or configured paths)

---

## 3. Installation & Setup

### Step 1: Extract the Package

Extract `QACompilerNEW.zip` to your desired location:

```
C:\Tools\QACompilerNEW\
```

### Step 2: Configure Paths

Edit `config.py` to match your environment:

```python
# Game resource paths (MUST be accessible)
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
```

### Step 3: Set Up Tester Mapping

Create or edit `languageTOtester_list.txt`:

```
ENG
TesterName1
TesterName2

ZHO-CN
TesterName3
TesterName4
```

### Step 4: Create Required Folders

Run the tool once to auto-create folders, or create manually:

```
QACompilerNEW/
├── QAfolder/           # Compiled QA files (auto-created)
├── QAfolderOLD/        # OLD QA files for transfer
├── QAfolderNEW/        # NEW datasheets for transfer
├── Masterfolder_EN/    # English master output
├── Masterfolder_CN/    # Chinese master output
└── GeneratedDatasheets/ # Generated datasheets output
```

### Step 5: Verify Setup

```bash
python main.py --version
python main.py --list
```

---

## 4. Folder Structure

### Complete Directory Layout

```
QACompilerNEW/
│
├── main.py                      # Entry point (GUI + CLI)
├── config.py                    # All configuration
├── languageTOtester_list.txt    # Tester -> Language mapping
│
├── core/                        # Compiler core modules
│   ├── compiler.py              # Main orchestration
│   ├── transfer.py              # File transfer logic
│   ├── discovery.py             # QA folder detection
│   ├── processing.py            # Sheet processing
│   └── excel_ops.py             # Excel operations
│
├── generators/                  # Datasheet generators
│   ├── base.py                  # Shared utilities
│   ├── quest.py                 # Quest datasheets
│   ├── knowledge.py             # Knowledge datasheets
│   ├── item.py                  # Item datasheets
│   ├── region.py                # Region datasheets
│   ├── skill.py                 # Skill datasheets
│   ├── character.py             # Character datasheets
│   ├── help.py                  # Help datasheets
│   └── gimmick.py               # Gimmick datasheets
│
├── tracker/                     # Progress tracker
│   ├── data.py                  # Data operations
│   ├── daily.py                 # DAILY sheet builder
│   ├── total.py                 # TOTAL sheet + rankings
│   └── coverage.py              # Coverage analysis
│
├── gui/                         # GUI module
│   └── app.py                   # Tkinter application
│
├── QAfolder/                    # Working QA files
│   └── {Username}_{Category}/   # Per-tester folders
│       ├── *.xlsx               # QA workbook
│       └── *.png/*.jpg          # Screenshots
│
├── QAfolderOLD/                 # OLD QA files (for transfer)
├── QAfolderNEW/                 # NEW datasheets (for transfer)
│
├── Masterfolder_EN/             # English output
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   ├── Master_Item.xlsx
│   ├── Master_Region.xlsx
│   ├── Master_System.xlsx       # Skill + Help combined
│   ├── Master_Character.xlsx
│   └── Images/                  # Copied screenshots
│
├── Masterfolder_CN/             # Chinese output
│   └── (same structure as EN)
│
├── GeneratedDatasheets/         # Generated datasheets
│   ├── QuestData_Map_All/
│   ├── Knowledge_LQA_All/
│   ├── ItemData_Map_All/
│   └── (other category folders)
│
└── LQA_Tester_ProgressTracker.xlsx  # Progress tracker
```

### QA Folder Naming Convention

**CRITICAL**: QA folders MUST follow this exact naming:

```
{TesterName}_{Category}
```

Examples:
- `John_Quest/`
- `Mary_Item/`
- `Chen_Knowledge/`

**Valid Categories**: Quest, Knowledge, Item, Region, System, Character, Skill, Help, Gimmick

---

## 5. Configuration

### config.py - Key Settings

#### Path Configuration

```python
# Game resource paths
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# Quest-specific paths
QUESTGROUPINFO_FILE = Path(r"...\questgroupinfo.staticinfo.xml")
SCENARIO_FOLDER = Path(r"...\scenario")
FACTION_QUEST_FOLDER = Path(r"...\quest\faction")
CHALLENGE_FOLDER = Path(r"...\Challenge")
MINIGAME_FILE = Path(r"...\contents_minigame.staticinfo.xml")
SEQUENCER_FOLDER = Path(r"...\sequencer\stageseq")
FACTIONINFO_FOLDER = Path(r"...\StaticInfo\factioninfo")

# Teleport reference (optional)
TELEPORT_SOURCE_FILE = SCRIPT_DIR / "Quest_LQA_ENG_1231_seon_final_final.xlsx"
```

#### Category Clustering

```python
CATEGORY_TO_MASTER = {
    "Skill": "System",   # Skill -> Master_System.xlsx
    "Help": "System",    # Help -> Master_System.xlsx
    "Gimmick": "Item",   # Gimmick -> Master_Item.xlsx
}
```

#### Translation Column Mapping

```python
TRANSLATION_COLS = {
    "Quest": {"eng": 2, "other": 3},
    "Knowledge": {"eng": 2, "other": 3},
    "Character": {"eng": 2, "other": 3},
    "Region": {"eng": 2, "other": 3},
    "Item": {"eng": 5, "other": 7},      # ItemName column
    "System": {"eng": 1, "other": 1},    # CONTENT column (single)
    "Skill": {"eng": 2, "other": 3},
    "Help": {"eng": 2, "other": 3},
    "Gimmick": {"eng": 2, "other": 3},
}
```

---

## 6. Functionalities

### 6.1 Generate Datasheets

**Purpose**: Create Excel datasheets from game XML files for QA testers.

#### What It Does

1. Reads game XML source files (StaticInfo)
2. Loads language translation tables
3. Builds structured Excel workbooks with:
   - Original Korean text
   - English translation
   - Target language translation
   - StringKey for commands
   - STATUS dropdown
   - COMMENT field
   - STRINGID
   - SCREENSHOT field

#### Sources by Category

| Category | Source Files |
|----------|-------------|
| Quest | scenario/, faction/, challenge/, minigame, factioninfo/ |
| Knowledge | knowledgegroupinfo/, knowledgeinfo/, characterinfo/ |
| Item | itemgroupinfo/, iteminfo/ |
| Region | factiongroupinfo/ |
| Character | characterinfo_*.xml |
| Skill | skillinfo_pc.staticinfo.xml |
| Help | gameadviceinfo.staticinfo.xml |
| Gimmick | gimmickinfo/, iteminfo/ |

#### Output Location

```
GeneratedDatasheets/
├── QuestData_Map_All/
│   ├── Quest_LQA_ENG.xlsx
│   ├── Quest_LQA_FRE.xlsx
│   └── ...
├── Knowledge_LQA_All/
├── ItemData_Map_All/
└── ...
```

---

### 6.2 Transfer QA Files

**Purpose**: Transfer tester work from OLD datasheets to NEW datasheets while preserving all QA data.

#### When to Use

- When new datasheets are generated (content changed)
- When testers have existing work to preserve
- When migrating between datasheet versions

#### How It Works

```
QAfolderOLD/          QAfolderNEW/          QAfolder/
(Tester's work)  +    (New empty)     =    (Merged result)
   STATUS                Empty               STATUS preserved
   COMMENT               Empty               COMMENT preserved
   SCREENSHOT            Empty               SCREENSHOT preserved
```

#### Matching Algorithm

**Two-Pass Global Matching** (across ALL sheets):

1. **Pass 1 - Exact Match**:
   - Standard: STRINGID + Translation
   - Item: ItemName + ItemDesc + STRINGID

2. **Pass 2 - Fallback Match**:
   - Standard: Translation only
   - Item: ItemName + ItemDesc only

#### Folder Setup

```
QAfolderOLD/
└── John_Quest/
    ├── Quest_LQA_ENG.xlsx    # Has STATUS/COMMENT/SCREENSHOT
    └── screenshot1.png

QAfolderNEW/
└── John_Quest/
    ├── Quest_LQA_ENG.xlsx    # New empty datasheet
    └── (no images)
```

#### Output

```
QAfolder/
└── John_Quest/
    ├── Quest_LQA_ENG.xlsx    # Merged file
    ├── screenshot1.png       # Copied from OLD
    └── DUPLICATE_TRANSLATION_REPORT.txt  # If duplicates found
```

---

### 6.3 Build Master Files

**Purpose**: Compile individual QA files into centralized Master files with manager workflow support.

#### What It Does

1. Discovers all QA folders in `QAfolder/`
2. Routes testers to EN or CN based on mapping
3. Creates/updates Master files per category
4. Adds per-user columns: `STATUS_{User}`, `COMMENT_{User}`, `SCREENSHOT_{User}`
5. Copies images with unique names
6. Preserves manager status (FIXED/REPORTED/CHECKING/NON-ISSUE)
7. Updates Progress Tracker

#### Input Structure

```
QAfolder/
├── John_Quest/
│   ├── Quest_LQA_ENG.xlsx
│   └── screenshot1.png
├── Mary_Quest/
│   ├── Quest_LQA_ENG.xlsx
│   └── image1.png
└── Chen_Knowledge/
    └── Knowledge_LQA_ZHO.xlsx
```

#### Output Structure

```
Masterfolder_EN/
├── Master_Quest.xlsx         # John + Mary's work combined
├── Master_Knowledge.xlsx
└── Images/
    ├── John_screenshot1.png  # Prefixed with username
    └── Mary_image1.png

Masterfolder_CN/
├── Master_Knowledge.xlsx     # Chen's work
└── Images/

LQA_Tester_ProgressTracker.xlsx  # Updated stats
```

#### Master File Structure

Each Master file contains:
- **Data Sheets**: One per tab from source (Main Quest, Faction tabs, etc.)
- **STATUS Sheet**: Summary statistics per user

Per-user columns added:
- `STATUS_{Username}` - ISSUE, NO ISSUE, BLOCKED, KOREAN
- `COMMENT_{Username}` - Tester notes with metadata
- `SCREENSHOT_{Username}` - Image references with hyperlinks

---

### 6.4 Coverage Analysis

**Purpose**: Calculate how much of the language data is covered by generated datasheets.

#### What It Measures

1. **String Coverage**: Unique Korean strings in datasheets vs. language master
2. **Word/Character Count**: Total words (EN) or characters (CN) per category
3. **Additional Sources**: Quest includes voice recording sheets

#### Output

- Terminal report with coverage percentages
- Excel file: `Coverage_Report_YYYYMMDD_HHMMSS.xlsx`
  - Sheet 1: Coverage Report (per category)
  - Sheet 2: Word Count by Category

---

## 7. GUI Usage

### Launching the GUI

```bash
python main.py
# or
python main.py --gui
```

### GUI Layout

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

### Using Each Section

#### 1. Generate Datasheets
1. Check the categories you want to generate
2. Click **[Generate Selected]**
3. Wait for completion (progress bar animates)
4. Check `GeneratedDatasheets/` folder

#### 2. Transfer QA Files
1. Place OLD files in `QAfolderOLD/{User}_{Category}/`
2. Place NEW files in `QAfolderNEW/{User}_{Category}/`
3. Click **[Transfer QA Files]**
4. Check `QAfolder/` for merged results

#### 3. Build Master Files
1. Ensure QA files are in `QAfolder/{User}_{Category}/`
2. Click **[Build Master Files]**
3. Check `Masterfolder_EN/` and `Masterfolder_CN/`
4. Check `LQA_Tester_ProgressTracker.xlsx`

#### 4. Coverage Analysis
1. Ensure datasheets exist in `GeneratedDatasheets/`
2. Click **[Run Coverage Analysis]**
3. View report in console and Excel file

---

## 8. CLI Usage

### Basic Commands

```bash
# Show help
python main.py --help

# Show version
python main.py --version

# List available categories
python main.py --list
```

### Generate Datasheets

```bash
# Generate specific categories
python main.py --generate quest knowledge item

# Generate all categories
python main.py --generate all

# Multiple -g flags
python main.py -g quest -g item -g region
```

### Transfer Files

```bash
python main.py --transfer
# or
python main.py -t
```

### Build Master Files

```bash
python main.py --build
# or
python main.py -b
```

### Full Pipeline

```bash
# Transfer + Build in one command
python main.py --all
# or
python main.py -a
```

### Combined Operations

```bash
# Generate, then transfer, then build
python main.py --generate all --all
```

---

## 9. Tester Mapping

### File Format

Create `languageTOtester_list.txt`:

```
ENG
TesterName1
TesterName2
TesterName3

ZHO-CN
TesterName4
TesterName5
```

### Rules

- Section headers: `ENG` or `ZHO-CN`
- One tester name per line (exact match with folder names)
- Empty lines are ignored
- Testers NOT in the mapping default to EN

### Example

```
ENG
John
Mary
David

ZHO-CN
Chen
Wei
Liu
```

### Effect

| Tester | Language | Output Folder |
|--------|----------|---------------|
| John | EN | Masterfolder_EN/ |
| Mary | EN | Masterfolder_EN/ |
| Chen | CN | Masterfolder_CN/ |
| Unknown | EN (default) | Masterfolder_EN/ |

---

## 10. Categories & Generators

### Category Overview

| # | Category | Generator | Description | Output Tabs |
|---|----------|-----------|-------------|-------------|
| 1 | Quest | quest.py | All quest types | Main, Factions, Region Quest, Daily, Politics, Challenge, Minigame, Others |
| 2 | Knowledge | knowledge.py | Knowledge entries | Per mega-root group |
| 3 | Item | item.py | Items with groups | Merged groups |
| 4 | Region | region.py | Faction/Region data | Per faction group |
| 5 | System | (Skill+Help) | Combined category | Skill + Help tabs |
| 6 | Character | character.py | NPC/Monster info | Per character type |
| 7 | Skill | skill.py | Player skills | Knowledge-linked |
| 8 | Help | help.py | GameAdvice entries | Single sheet |
| 9 | Gimmick | gimmick.py | Gimmick objects | Hierarchical |

### Quest Tab Organization

```
Quest_LQA_ENG.xlsx
├── Main Quest           (scenario-based)
├── Faction 1           (OrderByString from factioninfo)
├── Faction 2
├── ...
├── Region Quest         (*_Request StrKey)
├── Daily                (*_Daily StrKey + Group="daily")
├── Politics             (*_Situation StrKey)
├── Challenge Quest
├── Minigame Quest
└── Others               (leftover factions)
```

### Category Clustering

Some categories merge into others for Master files:

| Input Category | Target Master |
|----------------|---------------|
| Skill | Master_System.xlsx |
| Help | Master_System.xlsx |
| Gimmick | Master_Item.xlsx |

---

## 11. Output Files

### Generated Datasheet Columns

| Column | Description |
|--------|-------------|
| Original | Korean source text |
| ENG | English translation |
| {Language} | Target language (hidden for ENG files) |
| StringKey | Identifier for /complete commands |
| Command | Cheat commands (see Quest Command Structure below) |
| STATUS | Dropdown: ISSUE, NO ISSUE, BLOCKED, KOREAN |
| COMMENT | Tester notes |
| STRINGID | Unique string identifier |
| SCREENSHOT | Image filename |

### Quest Command Structure

The Command column in Quest datasheets contains cheat commands in this order:

1. **Prerequisite Commands** (Daily, Politics, Region Quest tabs only):
   - `/complete mission Mission_A && Mission_B` - Complete prerequisite missions
   - `/complete quest Quest_A && Quest_B` - Complete prerequisite quests

2. **Progress Command**:
   - `/complete prevquest {StringKey}` - Complete previous quest
   - `/complete prevmission {StrKey}` - Complete previous mission

3. **Teleport Command**:
   - `/teleport X Y Z` - Teleport to quest location

**Example multi-line Command:**
```
/complete mission Mission_IcemoorCastleRuins_Block_DeerKing_Boss && Mission_BluemontManor_Rupert_Normal_Trust
/complete prevmission Mission_HernandCastle_Finale_IcemoorCastleRuins
/teleport 1234 567 89
```

**Note**: Prerequisite commands are auto-generated from:
- Factioninfo `<Quest Condition="...">` attributes
- Quest XML `<Branch Condition="..." Execute="...">` elements

### Master File Columns

Same as datasheet, plus per-user columns:
- `STATUS_{Username}`
- `COMMENT_{Username}` - Format: `{comment}\n---\nstringid:\n{id}\n(updated: {date})`
- `SCREENSHOT_{Username}` - With hyperlink to Images/ folder

### Progress Tracker Sheets

**DAILY Sheet**:
- EN/CN sections with daily deltas
- Columns: Date, Done, Issues, NoIssue, Blocked, Korean, Words/Chars per user

**TOTAL Sheet**:
- Cumulative totals per user
- Category breakdown
- Rankings (80% Done + 20% Actual Issues)

**_DAILY_DATA Sheet** (hidden):
- Raw data storage for calculations

---

## 12. Workflow Examples

### Workflow A: New Project Setup

```bash
# 1. Generate all datasheets
python main.py --generate all

# 2. Distribute datasheets to testers
# Copy from GeneratedDatasheets/ to testers

# 3. Wait for testers to complete work...

# 4. Collect tester work into QAfolder/
# QAfolder/{TesterName}_{Category}/

# 5. Build master files
python main.py --build

# 6. Review Master files and tracker
```

### Workflow B: Update Existing Project

```bash
# 1. Testers' current work -> QAfolderOLD/
mv QAfolder/* QAfolderOLD/

# 2. Generate new datasheets -> QAfolderNEW/
python main.py --generate quest
cp GeneratedDatasheets/QuestData_Map_All/* QAfolderNEW/{TesterName}_Quest/

# 3. Transfer work to preserve STATUS/COMMENT
python main.py --transfer

# 4. Build updated masters
python main.py --build
```

### Workflow C: Daily Compilation

```bash
# One command for daily updates
python main.py --all

# This does:
# - Transfer (if OLD/NEW exist)
# - Build master files
# - Update progress tracker
```

---

## 13. Best Practices

### Folder Naming

| Do | Don't |
|----|-------|
| `John_Quest` | `John Quest` (spaces) |
| `Mary_Item` | `Mary-Item` (hyphens) |
| `Chen_Knowledge` | `chen_knowledge` (inconsistent case may work but avoid) |

### Before Transfer

1. **Backup QAfolderOLD** - Transfer modifies files
2. **Verify folder names match** - OLD and NEW must have same `{User}_{Category}` names
3. **Check duplicate translation report** - Review if multiple comments exist for same text

### Before Build

1. **Verify tester mapping** - Check `languageTOtester_list.txt`
2. **One Excel per folder** - Each QA folder should have exactly ONE .xlsx file
3. **Image formats** - Supported: .png, .jpg, .jpeg, .gif, .bmp

### Manager Status

| Status | Meaning |
|--------|---------|
| FIXED | Issue has been fixed |
| REPORTED | Issue reported to devs |
| CHECKING | Under investigation |
| NON-ISSUE | Marked as not an issue |

**How Manager Status is Preserved:**

Manager status (STATUS_{User}, MANAGER_COMMENT_{User}) is preserved across rebuilds using a two-stage matching system:

1. **Stage 1 (QA -> Master Row):** Match QA rows to Master rows by STRINGID + Translation content
2. **Stage 2 (Manager Lookup):** Use MASTER row's STRINGID + Tester comment to find manager status

This ensures manager work is never lost, even when QA files have empty STRINGIDs.

See `docs/TECHNICAL_MATCHING_SYSTEM.md` for technical details.

---

## 14. Troubleshooting

### Common Issues

#### "No valid QA folders found"

**Cause**: Folder naming incorrect
**Solution**: Ensure format is `{TesterName}_{Category}` with valid category

```bash
# Check your folders
ls QAfolder/

# Should see:
# John_Quest/
# Mary_Item/
```

#### "Language folder not found"

**Cause**: Path in config.py incorrect or not accessible
**Solution**:
1. Check Perforce workspace is synced
2. Verify path in `config.py`
3. Ensure network drive is connected

#### "No matching NEW folder for transfer"

**Cause**: OLD folder has no corresponding NEW folder
**Solution**: Ensure both folders exist with same name:
```
QAfolderOLD/John_Quest/
QAfolderNEW/John_Quest/
```

#### "Transfer success is low"

**Cause**: Content changed significantly between OLD and NEW
**Solution**: This is expected when many strings changed. Unmatched rows are logged.

#### Images not appearing

**Cause**: Hyperlinks broken or images not copied
**Solution**:
1. Check Images/ folder in Master output
2. Verify image filenames match SCREENSHOT values
3. Check for special characters in filenames

### Debug Mode

Check console output for detailed logs:
```bash
python main.py --build 2>&1 | tee build.log
```

---

## 15. Quick Update Protocol

### Updating Individual Files (Instead of Full Zip)

When updates are made, you don't need to re-download the entire zip. Just replace the specific file(s) that changed.

### File-to-Function Mapping

| If this changes... | Replace this file |
|--------------------|-------------------|
| Quest datasheets | `generators/quest.py` |
| Knowledge datasheets | `generators/knowledge.py` |
| Item datasheets | `generators/item.py` |
| Region datasheets | `generators/region.py` |
| Skill datasheets | `generators/skill.py` |
| Character datasheets | `generators/character.py` |
| Help datasheets | `generators/help.py` |
| Gimmick datasheets | `generators/gimmick.py` |
| Transfer logic | `core/transfer.py` |
| Build/Compile logic | `core/compiler.py` |
| Progress Tracker | `tracker/total.py`, `tracker/daily.py`, `tracker/data.py` |
| Configuration | `config.py` |
| GUI | `gui/app.py` |

### Update Steps

1. Download only the changed file(s) from the repository
2. Replace in your local installation
3. Run to verify: `python main.py --list`

---

## 16. Appendix

### Status Values

**Tester Status (STATUS column)**:
- ISSUE - Translation issue found
- NO ISSUE - Checked, no issue
- BLOCKED - Cannot test
- KOREAN - Korean text remaining

**Manager Status (STATUS_{User} column)**:
- FIXED - Issue resolved
- REPORTED - Sent to development
- CHECKING - Under review
- NON-ISSUE - Not a real issue

### Supported Languages

The system generates datasheets for all languages found in `LANGUAGE_FOLDER`, including:
- ENG (English)
- FRE (French)
- DEU (German)
- SPA (Spanish)
- ITA (Italian)
- JPN (Japanese)
- ZHO (Chinese)
- KOR (Korean)
- And more...

### File Size Limits

- Maximum rows per sheet: 1,048,576 (Excel limit)
- Recommended max images per folder: 1,000
- Progress tracker handles unlimited daily entries

### Keyboard Shortcuts (GUI)

Currently none - use buttons or CLI for faster operation.

---

## Document Information

| Field | Value |
|-------|-------|
| Version | 2.0.0 |
| Last Updated | 2025-01-15 |
| Author | QA Compiler Team |

---

*End of User Guide*
