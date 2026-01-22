# LanguageDataExporter - User Guide

**Language XML to Categorized Excel Converter with VRS-based Story Ordering**

> Converts game localization XML files into organized Excel spreadsheets, with chronological story ordering and word count reports for LQA scheduling.

---

## Table of Contents

1. [Quick Start](#-quick-start)
2. [Installation](#-installation)
3. [Features Overview](#-features-overview)
4. [GUI Mode](#-gui-mode)
5. [CLI Mode](#-cli-mode)
6. [Category System](#-category-system)
7. [VRS Ordering](#-vrs-ordering)
8. [Word Count Reports](#-word-count-reports)
9. [Output Files](#-output-files)
10. [Configuration](#-configuration)
11. [Troubleshooting](#-troubleshooting)
12. [Reference](#-reference)

---

## Quick Start

### 30-Second Workflow

```
1. Double-click LanguageDataExporter.exe
2. Click "Analyze Categories" to see distribution
3. Click "Generate Language Excels" to create files
4. Find output in GeneratedExcel/ folder
```

### Output Location

```
LanguageDataExporter/
└── GeneratedExcel/
    ├── LanguageData_ENG.xlsx      # English
    ├── LanguageData_FRE.xlsx      # French
    ├── LanguageData_GER.xlsx      # German
    ├── ...                        # Other languages
    ├── _Summary.xlsx              # Overview
    └── WordCountReport.xlsx       # LQA scheduling
```

---

## Installation

### Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | Windows 10/11 |
| **Disk Space** | ~50 MB |
| **Network** | Access to game data folders |
| **Drive** | Perforce sync on D:, E:, or F: |

### Step 1: Download

Download the latest `LanguageDataExporter-vX.X.X-Setup.exe` from GitHub Releases.

### Step 2: Install

1. Run the installer
2. Choose installation folder (default: `C:\Program Files\LanguageDataExporter`)
3. Click **Install**

### Step 3: Configure Drive Letter

On first launch, configure your Perforce drive:

```
┌─────────────────────────────────────────────┐
│  Drive Configuration                        │
├─────────────────────────────────────────────┤
│  Enter your Perforce drive letter: [F]      │
│                                             │
│  This will set paths to:                    │
│  • LOC: F:\perforce\cd\...\loc              │
│  • EXPORT: F:\perforce\cd\...\export__      │
│  • VRS: F:\perforce\cd\...\VoiceRecording   │
└─────────────────────────────────────────────┘
```

### Folder Structure After Install

```
LanguageDataExporter/
├── LanguageDataExporter.exe    # Main application
├── settings.json               # Your drive configuration
├── category_clusters.json      # Category colors/keywords
├── GeneratedExcel/             # Output folder (created on first run)
└── _internal/                  # Python runtime
```

---

## Features Overview

| Feature | Description | Output |
|---------|-------------|--------|
| **Language Export** | Convert XML to categorized Excel | `LanguageData_{LANG}.xlsx` |
| **Word Count Report** | LQA scheduling metrics | `WordCountReport.xlsx` |
| **Category Analysis** | View file distribution | GUI TreeView |
| **VRS Ordering** | Chronological story order | Sorted STORY rows |
| **Two-Tier Clustering** | STORY + GAME_DATA categories | Color-coded cells |

### Workflow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Language XML   │────▶│  LanguageData    │────▶│  Categorized    │
│  (loc folder)   │     │  Exporter        │     │  Excel Files    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌──────────────────┐
│  EXPORT XMLs    │────▶│  Category        │
│  (export__)     │     │  Assignment      │
└─────────────────┘     └──────────────────┘
                               │
                               ▼
┌─────────────────┐     ┌──────────────────┐
│  VRS Excel      │────▶│  Story Ordering  │
│  (EventName)    │     │  (Chronological) │
└─────────────────┘     └──────────────────┘
```

---

## GUI Mode

### Launching

```bash
# Double-click the executable
LanguageDataExporter.exe

# Or from command line
python main.py          # Default launches GUI
python main.py --gui    # Explicit GUI mode
```

### Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  LanguageDataExporter                                      [─][□][×]│
├─────────────────────────────────────────────────────────────────┤
│  CONFIGURED PATHS                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LOC Folder:    F:\perforce\cd\...\loc          [OK]       │  │
│  │ EXPORT Folder: F:\perforce\cd\...\export__     [OK]       │  │
│  │ Output Folder: GeneratedExcel                  [OK]       │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  CATEGORY ANALYSIS                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [Analyze Categories]                                      │  │
│  │                                                           │  │
│  │ Category          │ Files │ Tier                          │  │
│  │ ──────────────────┼───────┼────────                       │  │
│  │ Sequencer         │   340 │ STORY                         │  │
│  │ AIDialog          │   156 │ STORY                         │  │
│  │ Item              │   340 │ GAME_DATA                     │  │
│  │ System_Misc       │  1240 │ GAME_DATA                     │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  EXPORT ACTIONS                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [Generate Word Count Report]  [Generate Language Excels]  │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░  45%          │
│  Processing: LanguageData_FRE.xlsx                              │
└─────────────────────────────────────────────────────────────────┘
```

### GUI Actions

| Button | What It Does | Output | Required? |
|--------|--------------|--------|-----------|
| **Analyze Categories** | Shows category distribution (informational only) | TreeView updated | Optional |
| **Generate Word Count Report** | Creates LQA metrics report | `WordCountReport.xlsx` | Main action |
| **Generate Language Excels** | Creates all language files | `LanguageData_*.xlsx` | Main action |

> **Note:** "Analyze Categories" is **optional and informational only**. The export process automatically performs category clustering - you don't need to click Analyze first. It's just there to preview the category breakdown before exporting.

### Path Status Indicators

| Status | Meaning |
|--------|---------|
| `[OK]` | Path exists and is accessible |
| `[NOT FOUND]` | Path doesn't exist - check settings.json |

---

## CLI Mode

### Basic Commands

```bash
# Run with GUI (default)
python main.py

# Run in CLI mode
python main.py --cli

# Process specific languages
python main.py --cli --lang eng,fre,ger

# Generate word count report
python main.py --cli --word-count

# Word count report only (no language files)
python main.py --cli --word-count-only

# Preview without writing files
python main.py --cli --dry-run

# Show category distribution
python main.py --list-categories

# Custom output folder
python main.py --cli --output D:\Reports

# Verbose logging
python main.py --cli -v
```

### CLI Arguments Reference

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--cli` | | Run in command-line mode | `--cli` |
| `--lang` | | Process specific languages (comma-separated) | `--lang eng,fre` |
| `--word-count` | | Include word count report | `--word-count` |
| `--word-count-only` | | Only generate word count report | `--word-count-only` |
| `--dry-run` | | Preview without writing | `--dry-run` |
| `--list-categories` | | Show category distribution | `--list-categories` |
| `--output` | | Custom output folder | `--output D:\Out` |
| `--verbose` | `-v` | Enable debug logging | `-v` |
| `--gui` | | Force GUI mode | `--gui` |

### Example Workflows

**Daily Export (All Languages):**
```bash
python main.py --cli --word-count
```

**Quick French Check:**
```bash
python main.py --cli --lang fre --dry-run
```

**LQA Report Only:**
```bash
python main.py --cli --word-count-only
```

**Category Analysis:**
```bash
python main.py --list-categories
```

Output:
```
Two-Tier Category Distribution:

Tier 1: STORY (VRS-ordered, chronological)
  Sequencer                  :    340 files
  AIDialog                   :    156 files
  QuestDialog                :     89 files
  NarrationDialog            :     45 files
  ─────────────────────────────────────────
  SUBTOTAL                   :    630 files

Tier 2: GAME_DATA (Keyword-based)
  System_Misc                :   1240 files
  Item                       :    340 files
  Character                  :    215 files
  Quest                      :    180 files
  UI                         :    156 files
  Knowledge                  :    120 files
  Skill                      :     95 files
  Gimmick                    :     78 files
  Faction                    :     65 files
  Region                     :     42 files
  ─────────────────────────────────────────
  SUBTOTAL                   :   2531 files

TOTAL                        :   3161 files
```

---

## Category System (THE ALGORITHM)

This section explains the **complete category clustering algorithm** - the core logic that determines which category each string belongs to.

### Overview: Two-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CATEGORY CLUSTERING ALGORITHM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: File path from EXPORT folder (e.g., World/Knowledge/ItemInfo.xml)   │
│                                                                             │
│  STEP 1: DETERMINE TIER                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Is file in Dialog/ or Sequencer/ folder?                             │  │
│  │     YES → TIER 1 (STORY) → Use folder-based categorization            │  │
│  │     NO  → TIER 2 (GAME_DATA) → Use two-phase keyword matching         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STEP 2A: TIER 1 - STORY (Folder-Based)                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Sequencer/        → Sequencer                                        │  │
│  │  Dialog/AIDialog/  → AIDialog                                         │  │
│  │  Dialog/QuestDialog/ → QuestDialog                                    │  │
│  │  Dialog/NarrationDialog/ → NarrationDialog                            │  │
│  │  Dialog/StageCloseDialog/ → QuestDialog (mapped)                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  STEP 2B: TIER 2 - GAME_DATA (Two-Phase Matching)                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  PHASE 1: Check PRIORITY KEYWORDS in filename (checked FIRST!)        │  │
│  │     gimmick → Gimmick | item → Item | quest → Quest | skill → Skill   │  │
│  │     character → Character | faction → Faction | region → Region       │  │
│  │     IF MATCH FOUND → RETURN IMMEDIATELY (skip Phase 2)                │  │
│  │                                                                       │  │
│  │  PHASE 2: Check FOLDER PATTERNS + SECONDARY KEYWORDS                  │  │
│  │     LookAt/, PatternDescription/ → Item                               │  │
│  │     Quest/ → Quest | schedule_ keyword → Quest                        │  │
│  │     Character/, Npc/ → Character | monster, animal → Character        │  │
│  │     Skill/ → Skill | Knowledge/ → Knowledge | Faction/ → Faction      │  │
│  │     Ui/ → UI | localstringinfo, symboltext → UI                       │  │
│  │     Region/ → Region                                                  │  │
│  │     (no match) → System_Misc                                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  OUTPUT: Category name (e.g., "Item", "Quest", "Sequencer")                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Tier Classification

The algorithm first determines which tier a file belongs to based on its **top-level folder**:

| Top-Level Folder | Tier | Processing Method |
|------------------|------|-------------------|
| `Dialog/` | TIER 1 (STORY) | Subfolder determines category |
| `Sequencer/` | TIER 1 (STORY) | All files → Sequencer category |
| `System/` | TIER 2 (GAME_DATA) | Two-phase keyword matching |
| `World/` | TIER 2 (GAME_DATA) | Two-phase keyword matching |
| `None/` | TIER 2 (GAME_DATA) | Two-phase keyword matching |
| `Platform/` | TIER 2 (GAME_DATA) | Two-phase keyword matching |

### Step 2A: TIER 1 - STORY Categories

STORY content uses **simple folder-based categorization**:

| Folder Path | Category | Description | Ordering |
|-------------|----------|-------------|----------|
| `Sequencer/*.loc.xml` | **Sequencer** | Story cutscenes, major moments | VRS chronological |
| `Dialog/AIDialog/*.loc.xml` | **AIDialog** | NPC ambient conversation | VRS chronological |
| `Dialog/QuestDialog/*.loc.xml` | **QuestDialog** | Quest dialogue trees | VRS chronological |
| `Dialog/NarrationDialog/*.loc.xml` | **NarrationDialog** | Tutorial text, narration | VRS chronological |
| `Dialog/StageCloseDialog/*.loc.xml` | **QuestDialog** | Stage completion (mapped) | VRS chronological |

> **Key Point:** STORY categories are sorted **chronologically** using VoiceRecordingSheet (VRS) EventName ordering. This ensures LQA reviewers see content in the order players experience it.

### Step 2B: TIER 2 - GAME_DATA Two-Phase Matching

This is the **core algorithm** for non-story content. It uses two phases, checked in order:

#### PHASE 1: Priority Keywords (CHECKED FIRST!)

The algorithm extracts the **filename** (without extension) and checks if it contains any priority keyword. **First match wins and immediately returns.**

```
PRIORITY_KEYWORDS (checked in this exact order):
1. "gimmick"   → Gimmick
2. "item"      → Item
3. "quest"     → Quest
4. "skill"     → Skill
5. "character" → Character
6. "faction"   → Faction
7. "region"    → Region
```

**The matching is SUBSTRING-based and CASE-INSENSITIVE:**
- `gimmickinfo_item_book.xml` → Contains "gimmick" → **Gimmick**
- `KnowledgeInfo_Item.xml` → Contains "item" → **Item**
- `characterinfo_quest.xml` → Contains "quest" (checked before "character") → **Quest**

> **CRITICAL:** Priority keywords **completely override** folder location. A file named `KnowledgeInfo_Item.xml` in the `Knowledge/` folder will be categorized as **Item**, not Knowledge, because "item" is found in the filename.

#### PHASE 2: Standard Patterns (Only if Phase 1 didn't match)

If no priority keyword was found, the algorithm checks folder paths and secondary keywords:

| Match Type | Pattern | Category | Example |
|------------|---------|----------|---------|
| Folder | `lookat/` | Item | `System/LookAt/LookAtInfo.xml` |
| Folder | `patterndescription/` | Item | `World/PatternDescription/Pattern.xml` |
| Keyword | `weapon` | Item | `WeaponData.xml` |
| Keyword | `armor` | Item | `ArmorInfo.xml` |
| Folder | `quest/` | Quest | `System/Quest/QuestData.xml` |
| Keyword | `schedule_` | Quest | `schedule_daily.xml` |
| Folder | `character/` | Character | `World/Character/CharInfo.xml` |
| Folder | `npc/` | Character | `System/Npc/NpcData.xml` |
| Keyword | `monster` | Character | `MonsterInfo.xml` |
| Keyword | `animal` | Character | `AnimalData.xml` |
| Folder | `skill/` | Skill | `System/Skill/SkillInfo.xml` |
| Folder | `knowledge/` | Knowledge | `World/Knowledge/KnowledgeBase.xml` |
| Folder | `faction/` | Faction | `System/Faction/FactionInfo.xml` |
| Folder | `ui/` | UI | `System/Ui/UIStrings.xml` |
| Keyword | `localstringinfo` | UI | `LocalStringInfo.xml` |
| Keyword | `symboltext` | UI | `SymbolText.xml` |
| Folder | `region/` | Region | `System/Region/RegionInfo.xml` |
| (default) | (no match) | System_Misc | Everything else |

### Complete Algorithm Walkthrough Examples

**Example 1: File in Knowledge folder with "Item" in name**
```
Input:  World/Knowledge/KnowledgeInfo_Item.xml

Step 1: Tier Classification
  - Top folder is "World/" → TIER 2 (GAME_DATA)

Step 2B: Two-Phase Matching
  PHASE 1: Check priority keywords in filename "KnowledgeInfo_Item"
    - "gimmick" in "knowledgeinfo_item"? NO
    - "item" in "knowledgeinfo_item"? YES → RETURN "Item"

OUTPUT: Item (NOT Knowledge!)
```

**Example 2: Gimmick file with multiple keywords**
```
Input:  System/Gimmick/gimmickinfo_item_book.xml

Step 1: Tier Classification
  - Top folder is "System/" → TIER 2 (GAME_DATA)

Step 2B: Two-Phase Matching
  PHASE 1: Check priority keywords in filename "gimmickinfo_item_book"
    - "gimmick" in "gimmickinfo_item_book"? YES → RETURN "Gimmick"
    (Note: "item" is also present but "gimmick" is checked FIRST)

OUTPUT: Gimmick (gimmick has HIGHEST priority)
```

**Example 3: File with no priority keywords**
```
Input:  World/Knowledge/KnowledgeBase.xml

Step 1: Tier Classification
  - Top folder is "World/" → TIER 2 (GAME_DATA)

Step 2B: Two-Phase Matching
  PHASE 1: Check priority keywords in filename "KnowledgeBase"
    - "gimmick"? NO | "item"? NO | "quest"? NO | "skill"? NO
    - "character"? NO | "faction"? NO | "region"? NO
    - No match → Continue to Phase 2

  PHASE 2: Check folder patterns
    - "knowledge/" in path? YES → RETURN "Knowledge"

OUTPUT: Knowledge
```

**Example 4: Story content (Dialog)**
```
Input:  Dialog/AIDialog/AIDialogStringInfo.xml

Step 1: Tier Classification
  - Top folder is "Dialog/" → TIER 1 (STORY)

Step 2A: Folder-based categorization
  - Subfolder is "AIDialog/" → RETURN "AIDialog"

OUTPUT: AIDialog (will be VRS-ordered)
```

### Priority Keyword Conflict Resolution

When a filename contains **multiple** priority keywords, the **first match in priority order wins**:

| Filename | Contains | Winner | Why |
|----------|----------|--------|-----|
| `gimmickinfo_item_book` | gimmick, item | **Gimmick** | gimmick is priority 1 |
| `characterinfo_quest` | character, quest | **Quest** | quest is priority 3, character is 5 |
| `skillinfo_faction` | skill, faction | **Skill** | skill is priority 4, faction is 6 |
| `item_region_data` | item, region | **Item** | item is priority 2, region is 7 |

### Summary: Golden Rules

| Rule | Explanation |
|------|-------------|
| **Tier First** | Dialog/Sequencer → STORY, everything else → GAME_DATA |
| **Priority Keywords Win** | Phase 1 keywords override ALL folder matching |
| **Gimmick is #1** | "gimmick" in filename → always Gimmick category |
| **Order Matters** | Priority keywords checked in specific order (1-7) |
| **Substring Match** | Keywords match anywhere in filename (case-insensitive) |
| **STORY = VRS Order** | Dialog/Sequencer content sorted chronologically |
| **GAME_DATA = Alphabetical** | Other content sorted by category name |
| **Knowledge is Catch-All** | Only matches if NO priority keyword found |

---

## VRS Ordering

### What is VRS?

**VoiceRecordingSheet (VRS)** is the master Excel file containing all voiced lines in **chronological story order**. LanguageDataExporter uses VRS to sort STORY content so LQA reviewers see dialogue in the order players experience it.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    VRS ORDERING FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Load VoiceRecordingSheet.xlsx                               │
│     └── Read EventName from Column W                            │
│     └── Store: EventName → Row Position                         │
│                                                                 │
│  2. Scan EXPORT XMLs                                            │
│     └── Extract SoundEventName attribute from StringID          │
│     └── Store: StringID → SoundEventName                        │
│                                                                 │
│  3. Sort STORY Entries                                          │
│     └── For each entry: StringID → SoundEventName → VRS Row     │
│     └── Sort by VRS row position                                │
│                                                                 │
│  4. Result: Chronological Story Order!                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### VRS Column Reference

| Column | Index | Content |
|--------|-------|---------|
| **A** | 0 | Category (Sequencer, AIDialog, etc.) |
| **W** | 22 | EventName (SoundEventName) - **Ordering Key** |

### Example

**VoiceRecordingSheet Row Order:**
| Row | EventName |
|-----|-----------|
| 100 | cd_seq_quest_hernand_0100 |
| 101 | cd_seq_quest_hernand_0200 |
| 102 | cd_seq_quest_hernand_0300 |

**Result in Excel:**
STORY entries with these EventNames appear in rows 100, 101, 102 order.

---

## Word Count Reports

### Report Purpose

Word count reports help LQA teams:
- **Schedule work** based on word/character counts
- **Track progress** across languages
- **Identify untranslated** content (still contains Korean)

### Report Structure

**File:** `WordCountReport.xlsx`

**Sheets:**

1. **Summary** - All languages at a glance
2. **ENG** - English breakdown by category
3. **FRE** - French breakdown by category
4. **GER** - German breakdown by category
5. ... (one sheet per language)

### Columns Per Language Sheet

| Column | Description |
|--------|-------------|
| **Category** | Category name |
| **Korean Source** | Word count of Korean StrOrigin |
| **Translation** | Words (EU) or Characters (CJK) |
| **Total Strings** | Number of text entries |
| **Untranslated** | Strings still containing Korean |

### Counting Method

| Language Type | Method | Languages |
|---------------|--------|-----------|
| **European/SEA** | Word count | ENG, FRE, GER, SPA, POR, ITA, RUS, TUR, POL, THA, VIE, IND, MSA |
| **CJK** | Character count | JPN, ZHO-CN, ZHO-TW |

### Untranslated Detection

A string is marked **untranslated** if the translation still contains Korean characters (Unicode range U+AC00-U+D7A3).

| Translation | Untranslated? |
|-------------|---------------|
| `Hello World` | No |
| `Hello 안녕` | Yes (contains Korean) |
| `안녕하세요` | Yes (all Korean) |

---

## Output Files

### Language Excel Files

**Filename:** `LanguageData_{LANG}.xlsx`

**Example:** `LanguageData_FRE.xlsx` (French)

#### Columns (EU Languages)

| Column | Width | Description |
|--------|-------|-------------|
| **StrOrigin** | 45 | Korean source text |
| **Str** | 45 | Translated text |
| **StringID** | 15 | Unique identifier |
| **English** | 45 | English reference |
| **Category** | 20 | Color-coded category |

#### Columns (CJK Languages)

| Column | Width | Description |
|--------|-------|-------------|
| **StrOrigin** | 45 | Korean source text |
| **Str** | 45 | Translated text |
| **StringID** | 15 | Unique identifier |
| **Category** | 20 | Color-coded category |

> **Note:** CJK languages (JPN, ZHO-CN, ZHO-TW) don't include English column.

### Category Colors

| Category | Color | Hex |
|----------|-------|-----|
| Sequencer | Light Orange | `FFE599` |
| AIDialog | Light Green | `C6EFCE` |
| QuestDialog | Light Green | `C6EFCE` |
| NarrationDialog | Light Green | `C6EFCE` |
| Item | Light Purple | `D9D2E9` |
| Quest | Light Purple | `D9D2E9` |
| Character | Light Peach | `F8CBAD` |
| Gimmick | Light Purple | `D9D2E9` |
| Skill | Light Purple | `D9D2E9` |
| Knowledge | Light Purple | `D9D2E9` |
| Faction | Light Purple | `D9D2E9` |
| UI | Light Teal | `A9D08E` |
| Region | Light Peach | `F8CBAD` |
| System_Misc | Light Grey | `D9D9D9` |

### Summary File

**Filename:** `_Summary.xlsx`

| Column | Description |
|--------|-------------|
| **Language** | Language code (ENG, FRE, etc.) |
| **Row Count** | Number of entries |
| **File Generated** | Output filename |
| **Include English** | Yes/No |

---

## Configuration

### settings.json

**Location:** `LanguageDataExporter/settings.json`

**Created by:** Installer or `drive_replacer.py`

```json
{
  "drive_letter": "F",
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__"
}
```

### Changing Drive Letter

```bash
# Using drive_replacer.py
python drive_replacer.py D          # Set to D: drive
python drive_replacer.py F          # Set to F: drive
```

Or manually edit `settings.json`.

### category_clusters.json

**Location:** `LanguageDataExporter/category_clusters.json`

Defines:
- Priority keywords and categories
- Folder mappings
- Category colors
- Language configuration

**Rarely needs editing** - defaults work for standard game structure.

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Path NOT FOUND** | Wrong drive letter | Edit `settings.json` or run `drive_replacer.py` |
| **No language files** | LOC folder empty | Check Perforce sync status |
| **VRS not loaded** | Missing VRS folder | Verify VRS path in settings |
| **Empty output** | No .loc.xml files | Check EXPORT folder exists |
| **Wrong category** | Priority keyword conflict | Check filename for keywords |

### Error Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `LOC folder not found` | Path doesn't exist | Fix `settings.json` |
| `EXPORT folder not found` | Path doesn't exist | Fix `settings.json` |
| `No .loc.xml files found` | EXPORT empty | Sync Perforce |
| `VoiceRecordingSheet not loaded` | VRS missing | Check VRS folder |

### Debug Mode

```bash
python main.py --cli -v
```

Shows detailed logging:
- File discovery
- Category assignment decisions
- VRS ordering progress

---

## Reference

### Supported Languages

| Code | Language | Count Method | English Column |
|------|----------|--------------|----------------|
| ENG | English | Words | No |
| FRE | French | Words | Yes |
| GER | German | Words | Yes |
| SPA | Spanish | Words | Yes |
| POR | Portuguese | Words | Yes |
| ITA | Italian | Words | Yes |
| RUS | Russian | Words | Yes |
| TUR | Turkish | Words | Yes |
| POL | Polish | Words | Yes |
| KOR | Korean | Words | Yes |
| THA | Thai | Words | Yes |
| VIE | Vietnamese | Words | Yes |
| IND | Indonesian | Words | Yes |
| MSA | Malay | Words | Yes |
| JPN | Japanese | Characters | No |
| ZHO-CN | Chinese (Simplified) | Characters | No |
| ZHO-TW | Chinese (Traditional) | Characters | No |

### File Patterns

| Type | Pattern | Location |
|------|---------|----------|
| Language XML | `languagedata_*.xml` | LOC folder |
| Category XML | `*.loc.xml` | EXPORT folder |
| VRS Excel | `*.xlsx` (most recent) | VRS folder |

### Project Structure

```
LanguageDataExporter/
├── main.py                    # Entry point
├── config.py                  # Configuration
├── settings.json              # Runtime paths
├── category_clusters.json     # Category config
├── drive_replacer.py          # Drive configuration
├── exporter/
│   ├── xml_parser.py          # XML parsing
│   ├── category_mapper.py     # Two-tier clustering
│   └── excel_writer.py        # Excel output
├── reports/
│   ├── word_counter.py        # Word/char counting
│   └── excel_report.py        # Report generation
├── clustering/
│   ├── gamedata_clusterer.py  # GAME_DATA logic
│   ├── dialog_clusterer.py    # Dialog categories
│   └── sequencer_clusterer.py # Sequencer logic
├── gui/
│   └── app.py                 # tkinter GUI
└── utils/
    ├── language_utils.py      # Korean detection
    └── vrs_ordering.py        # VRS sorting
```

---

## Support

| Resource | Location |
|----------|----------|
| **GitHub Issues** | [Report bugs](https://github.com/NeilVibe/LocalizationTools/issues) |
| **README** | `README.md` in project folder |
| **This Guide** | `USER_GUIDE.md` |

---

*Last updated: January 2025*
*Version: 1.0.16*
