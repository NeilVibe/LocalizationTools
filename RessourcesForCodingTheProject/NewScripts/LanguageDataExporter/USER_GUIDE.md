# LanguageDataExporter - Complete User Guide

**Language XML to Categorized Excel Converter with VRS-based Story Ordering**

> Converts game localization XML files into organized Excel spreadsheets, with chronological story ordering, word count reports, and full LQA correction workflow.

---

## Table of Contents

1. [Quick Start](#-quick-start)
2. [Installation](#-installation)
3. [Complete Workflow Overview](#-complete-workflow-overview)
4. [Features Overview](#-features-overview)
5. [GUI Mode](#-gui-mode)
6. [CLI Mode](#-cli-mode)
7. [Data Flow Architecture](#-data-flow-architecture)
8. [Category System (THE ALGORITHM)](#-category-system-the-algorithm)
9. [VRS Ordering](#-vrs-ordering)
10. [Word Count Reports](#-word-count-reports)
11. [Output Files](#-output-files)
12. [LQA Correction Workflow](#-lqa-correction-workflow)
13. [LOCDEV Merge](#-locdev-merge)
14. [ENG/ZHO-CN Exclusions](#-engzho-cn-exclusions)
15. [Code Pattern Analyzer (Removed)](#-code-pattern-analyzer-removed)
16. [Progress Tracker](#-progress-tracker)
17. [Configuration](#-configuration)
18. [Troubleshooting](#-troubleshooting)
19. [Reference](#-reference)

---

## Quick Start

### 30-Second Workflow

```
1. Double-click LanguageDataExporter.exe
2. Click "Generate Language Excels" to create files
3. Find output in GeneratedExcel/ folder
4. Copy files to ToSubmit/ folder for LQA review
5. After corrections, click "Merge to LOCDEV" to push corrections back
6. (Optional) Click "Prepare For Submit" to create clean 3-column archive files
```

### Output Location

```
LanguageDataExporter/
├── GeneratedExcel/                 # Generated files
│   ├── LanguageData_ENG.xlsx       # English (Dialog/Sequencer EXCLUDED)
│   ├── LanguageData_ZHO-CN.xlsx    # Chinese (Dialog/Sequencer EXCLUDED)
│   ├── LanguageData_FRE.xlsx       # French (ALL categories)
│   ├── ...                         # Other languages (ALL categories)
│   ├── _Summary.xlsx               # Overview
│   └── WordCountReport.xlsx        # LQA scheduling
│
├── ToSubmit/                       # LQA staging area
│   ├── LanguageData_ENG.xlsx       # Files being reviewed
│   ├── LanguageData_FRE.xlsx       # Fill Correction column here
│   └── backup_YYYYMMDD_HHMMSS/     # Auto-backup before submit
│
└── Correction_ProgressTracker.xlsx # Weekly/Total progress tracking
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
│  • LOCDEV: F:\perforce\cd\...\locdev__      │
└─────────────────────────────────────────────┘
```

### Folder Structure After Install

```
LanguageDataExporter/
├── LanguageDataExporter.exe          # Main application
├── settings.json                     # Your drive configuration
├── category_clusters.json            # Category colors/keywords
├── GeneratedExcel/                   # Generated Excel files
├── ToSubmit/                         # LQA staging folder
├── Correction_ProgressTracker.xlsx   # Progress tracking
└── _internal/                        # Python runtime
```

---

## Complete Workflow Overview

### The Big Picture

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    LANGUAGEDATAEXPORTER - COMPLETE WORKFLOW                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   ║
║   │   SOURCE    │    │   PROCESS   │    │   OUTPUT    │    │   SUBMIT    │   ║
║   │   DATA      │───▶│   ENGINE    │───▶│   FILES     │───▶│   WORKFLOW  │   ║
║   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────────┐ ║
║   │ SOURCE DATA (Read-Only, from Perforce)                                  │ ║
║   │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ ║
║   │ │ LOC Folder  │  │EXPORT Folder│  │ VRS Folder  │  │LOCDEV Folder│     │ ║
║   │ │ languagedata│  │  .loc.xml   │  │VoiceRecSheet│  │languagedata │     │ ║
║   │ │  _*.xml     │  │  (category  │  │  (story     │  │  _*.xml     │     │ ║
║   │ │ (ALL text)  │  │  structure) │  │   order)    │  │ (for merge) │     │ ║
║   │ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │ ║
║   └─────────────────────────────────────────────────────────────────────────┘ ║
║                                     │                                         ║
║                                     ▼                                         ║
║   ┌─────────────────────────────────────────────────────────────────────────┐ ║
║   │ PROCESS ENGINE                                                          │ ║
║   │                                                                         │ ║
║   │  1. Parse LOC XMLs ──────────────────────────────▶ All StringIDs       │ ║
║   │                                                                         │ ║
║   │  2. Scan EXPORT folder ──────────────────────────▶ StringID → Category │ ║
║   │     • Dialog/      → Tier 1 (STORY)                                    │ ║
║   │     • Sequencer/   → Tier 1 (STORY)                                    │ ║
║   │     • System/World/None/Platform/ → Tier 2 (GAME_DATA)                 │ ║
║   │                                                                         │ ║
║   │  3. Load VRS Excel ──────────────────────────────▶ EventName → Order   │ ║
║   │                                                                         │ ║
║   │  4. Sort STORY by VRS ───────────────────────────▶ Chronological order │ ║
║   │                                                                         │ ║
║   │  5. Apply ENG/ZHO-CN exclusions ─────────────────▶ Skip Dialog/Seq     │ ║
║   │                                                                         │ ║
║   └─────────────────────────────────────────────────────────────────────────┘ ║
║                                     │                                         ║
║                                     ▼                                         ║
║   ┌─────────────────────────────────────────────────────────────────────────┐ ║
║   │ OUTPUT FILES (GeneratedExcel/)                                          │ ║
║   │                                                                         │ ║
║   │  ┌─────────────────────────────────────────────────────────────────┐   │ ║
║   │  │ LanguageData_{LANG}.xlsx                                        │   │ ║
║   │  │ Columns (EU): StrOrigin | ENG | Str | Correction | Text State │   │ ║
║   │  │   | STATUS | COMMENT | MEMO1 | MEMO2 | Category | StringID   │   │ ║
║   │  │ (11 columns for EU, 10 for Asian - no ENG column)            │   │ ║
║   │  └─────────────────────────────────────────────────────────────────┘   │ ║
║   │                                                                         │ ║
║   │  + WordCountReport.xlsx (LQA scheduling metrics)                       │ ║
║   │  + _Summary.xlsx (overview)                                            │ ║
║   │                                                                         │ ║
║   └─────────────────────────────────────────────────────────────────────────┘ ║
║                                     │                                         ║
║                                     ▼                                         ║
║   ┌─────────────────────────────────────────────────────────────────────────┐ ║
║   │ SUBMIT WORKFLOW                                                         │ ║
║   │                                                                         │ ║
║   │  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐          │ ║
║   │  │ Copy to        │   │ LQA fills      │   │ Prepare For    │          │ ║
║   │  │ ToSubmit/      │──▶│ Correction     │──▶│ Submit         │          │ ║
║   │  │                │   │ column         │   │ (apply fixes)  │          │ ║
║   │  └────────────────┘   └────────────────┘   └────────────────┘          │ ║
║   │                                                    │                    │ ║
║   │                                                    ▼                    │ ║
║   │                                            ┌────────────────┐          │ ║
║   │                                            │ Merge to       │          │ ║
║   │                                            │ LOCDEV         │          │ ║
║   │                                            │ (push to XML)  │          │ ║
║   │                                            └────────────────┘          │ ║
║   │                                                                         │ ║
║   └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Features Overview

| Feature | Description | Output |
|---------|-------------|--------|
| **Language Export** | Convert XML to categorized Excel | `LanguageData_{LANG}.xlsx` |
| **Word Count Report** | LQA scheduling metrics | `WordCountReport.xlsx` |
| **Correction Column** | Empty column for LQA corrections | In each Excel file |
| **Prepare For Submit** | Extract corrections to clean 3-column file | Archive files |
| **Merge to LOCDEV (ALL)** | Push corrections back to source XML (StringID + StrOrigin match) | Updated LOCDEV XMLs + Tracker |
| **Merge to LOCDEV (SCRIPT)** | Push SCRIPT corrections (StringID-only match) | Updated LOCDEV XMLs |
| **Progress Tracker** | Track merge results (Success/Fail) weekly | `Correction_ProgressTracker.xlsx` |
| **VRS Ordering** | Chronological story order | Sorted STORY rows |
| **Two-Tier Clustering** | STORY + GAME_DATA categories | Color-coded cells |
| **ENG/ZHO-CN Exclusion** | Skip Dialog/Sequencer for voiced langs | Smaller Excel files |
| **StringID as TEXT** | Prevent scientific notation | Proper display in Excel |

### What's New in v3.0

| Feature | Description |
|---------|-------------|
| **STATUS Column** | New dropdown column (ISSUE / NO ISSUE) for QA tracking |
| **COMMENT Column** | Free-text QA notes column |
| **Merge Buttons** | Renamed for clarity: ALL (StringID + KR) and SCRIPT (StringID-only) |
| **USER GUIDE** | In-app scrollable guide window |
| **LOC Info** | Shows source folder info before generating Excel files |

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
│  LanguageDataExporter v3.0                                     │
├─────────────────────────────────────────────────────────────────┤
│  CONFIGURED PATHS                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LOC Folder:    F:\perforce\cd\...\loc          [OK]       │  │
│  │ EXPORT Folder: F:\perforce\cd\...\export__     [OK]       │  │
│  │ Output Folder: GeneratedExcel                  [OK]       │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  GENERATE & SUBMIT                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [Generate Word Count Report]  [Generate Language Excels]  │  │
│  │ [Prepare For Submit]          [Open ToSubmit Folder]      │  │
│  │ [Merge to LOCDEV (ALL)]       [Merge to LOCDEV (SCRIPT)]  │  │
│  │ [USER GUIDE]                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░  45%          │
│  Processing: LanguageData_FRE.xlsx                              │
└─────────────────────────────────────────────────────────────────┘
```

### GUI Actions

| Button | What It Does | Output |
|--------|--------------|--------|
| **Generate Word Count Report** | Creates LQA metrics report | `WordCountReport.xlsx` |
| **Generate Language Excels** | Creates files with Correction column | `LanguageData_*.xlsx` |
| **Prepare For Submit** | Extract corrections to 3-column archive | Clean archive files |
| **Open ToSubmit Folder** | Opens ToSubmit folder in explorer | - |
| **Merge to LOCDEV (ALL)** | Push corrections to LOCDEV (strict: StringID + StrOrigin) | Updated XML + Tracker |
| **Merge to LOCDEV (SCRIPT)** | Push SCRIPT corrections (StringID-only match) | Updated XML |
| **USER GUIDE** | Opens scrollable guide window | - |

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

---

## Data Flow Architecture

### Source Folders Explained

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         SOURCE DATA ARCHITECTURE                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │ LOC FOLDER (languagedata_*.xml)                                         │ ║
║  │ ═══════════════════════════════                                         │ ║
║  │ Contains: ALL game text strings                                         │ ║
║  │ Format: One file per language (languagedata_eng.xml, _fre.xml, etc.)    │ ║
║  │ Structure:                                                              │ ║
║  │   <LocStr StringId="12345" StrOrigin="몬스터" Str="Monster" />          │ ║
║  │                                                                         │ ║
║  │ Used for: Extracting all text to display in Excel                       │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │ EXPORT FOLDER (.loc.xml files)                                          │ ║
║  │ ══════════════════════════════                                          │ ║
║  │ Contains: Same StringIDs, but ORGANIZED BY CATEGORY                     │ ║
║  │ Structure:                                                              │ ║
║  │   export__/                                                             │ ║
║  │   ├── Dialog/                   ← TIER 1 (STORY)                       │ ║
║  │   │   ├── AIDialog/                                                     │ ║
║  │   │   ├── QuestDialog/                                                  │ ║
║  │   │   └── NarrationDialog/                                              │ ║
║  │   ├── Sequencer/                ← TIER 1 (STORY)                       │ ║
║  │   ├── System/                   ← TIER 2 (GAME_DATA)                   │ ║
║  │   ├── World/                    ← TIER 2 (GAME_DATA)                   │ ║
║  │   ├── None/                     ← TIER 2 (GAME_DATA)                   │ ║
║  │   └── Platform/                 ← TIER 2 (GAME_DATA)                   │ ║
║  │                                                                         │ ║
║  │ Used for: Determining which CATEGORY each StringID belongs to          │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │ VRS FOLDER (VoiceRecordingSheet Excel)                                  │ ║
║  │ ════════════════════════════════════                                    │ ║
║  │ Contains: Master list of voiced lines in CHRONOLOGICAL STORY ORDER     │ ║
║  │ Key Column: W (EventName / SoundEventName)                              │ ║
║  │                                                                         │ ║
║  │ Used for: Sorting STORY content (Dialog/Sequencer) chronologically     │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │ LOCDEV FOLDER (languagedata_*.xml)                                      │ ║
║  │ ══════════════════════════════════                                      │ ║
║  │ Contains: Development version of language files                         │ ║
║  │ Format: Same as LOC folder                                              │ ║
║  │                                                                         │ ║
║  │ Used for: MERGE TO LOCDEV - pushing corrections back to source         │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Why "Uncategorized" Can Happen

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      UNDERSTANDING "UNCATEGORIZED"                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   "Uncategorized" means: StringID exists in LOC but NOT in EXPORT             ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                                                                     │    ║
║   │   LOC Folder                    EXPORT Folder                       │    ║
║   │   ══════════                    ═════════════                       │    ║
║   │                                                                     │    ║
║   │   StringID: 1001  ──────────────▶  Found in Dialog/AI/  → AIDialog │    ║
║   │   StringID: 1002  ──────────────▶  Found in System/UI/  → UI       │    ║
║   │   StringID: 1003  ──────────────▶  Found in World/Item/ → Item     │    ║
║   │   StringID: 1004  ──────────────▶  NOT FOUND!           → Uncateg. │    ║
║   │                                          ↑                          │    ║
║   │                                          │                          │    ║
║   │                            This is a DATA ISSUE                    │    ║
║   │                            (not our code's fault)                  │    ║
║   │                                                                     │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
║   IMPORTANT: This is NOT a bug in LanguageDataExporter!                      ║
║                                                                               ║
║   If strings are "Uncategorized", it means the content team needs to:        ║
║   • Export those strings to the EXPORT folder structure                      ║
║   • Or check if they're deprecated/internal strings                          ║
║                                                                               ║
║   Everything IN EXPORT gets categorized properly.                            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Category System (THE ALGORITHM)

### Overview: Two-Tier Architecture

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     CATEGORY CLUSTERING ALGORITHM                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  INPUT: File path from EXPORT folder (e.g., World/Knowledge/ItemInfo.xml)    ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │  STEP 1: DETERMINE TIER                                                  │ ║
║  │  ════════════════════════                                                │ ║
║  │                                                                          │ ║
║  │    Is file in Dialog/ or Sequencer/ folder?                              │ ║
║  │       │                                                                  │ ║
║  │       ├── YES ──▶ TIER 1 (STORY)                                        │ ║
║  │       │           Folder-based categorization                            │ ║
║  │       │           Sorted by VRS (chronological)                          │ ║
║  │       │                                                                  │ ║
║  │       └── NO ───▶ TIER 2 (GAME_DATA)                                    │ ║
║  │                   Two-phase keyword matching                             │ ║
║  │                   Sorted alphabetically by category                      │ ║
║  │                                                                          │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │  STEP 2A: TIER 1 - STORY (Folder-Based)                                  │ ║
║  │  ═════════════════════════════════════                                   │ ║
║  │                                                                          │ ║
║  │    Sequencer/           ──────────────────────▶  "Sequencer"            │ ║
║  │    Dialog/AIDialog/     ──────────────────────▶  "AIDialog"             │ ║
║  │    Dialog/QuestDialog/  ──────────────────────▶  "QuestDialog"          │ ║
║  │    Dialog/NarrationDialog/ ───────────────────▶  "NarrationDialog"      │ ║
║  │    Dialog/StageCloseDialog/ ──────────────────▶  "QuestDialog" (mapped) │ ║
║  │    Dialog/(unknown)/    ──────────────────────▶  "AIDialog" (default)   │ ║
║  │                                                                          │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │  STEP 2B: TIER 2 - GAME_DATA (Two-Phase Matching)                        │ ║
║  │  ═════════════════════════════════════════════                           │ ║
║  │                                                                          │ ║
║  │    PHASE 1: Check PRIORITY KEYWORDS in filename (checked FIRST!)        │ ║
║  │    ──────────────────────────────────────────────────────────           │ ║
║  │       gimmick → Gimmick | item → Item | quest → Quest | skill → Skill   │ ║
║  │       character → Character | region → Region | faction → Faction       │ ║
║  │                                                                          │ ║
║  │       IF MATCH FOUND → RETURN IMMEDIATELY (skip Phase 2)                │ ║
║  │                                                                          │ ║
║  │    PHASE 2: Check FOLDER PATTERNS + SECONDARY KEYWORDS                  │ ║
║  │    ──────────────────────────────────────────────────────               │ ║
║  │       LookAt/, PatternDescription/ → Item                               │ ║
║  │       Quest/ → Quest | schedule_ keyword → Quest                        │ ║
║  │       Character/, Npc/ → Character | monster, animal → Character        │ ║
║  │       Skill/ → Skill | Knowledge/ → Knowledge | Faction/ → Faction      │ ║
║  │       Ui/ → UI | localstringinfo, symboltext → UI                       │ ║
║  │       Region/ → Region                                                  │ ║
║  │       (no match) → System_Misc                                          │ ║
║  │                                                                          │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                               ║
║  OUTPUT: Category name (e.g., "Item", "Quest", "Sequencer")                  ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Priority Keywords (CRITICAL!)

**Priority keywords are checked FIRST and override ALL folder matching:**

| Priority | Keyword | Category |
|----------|---------|----------|
| 1 | `gimmick` | Gimmick |
| 2 | `item` | Item |
| 3 | `quest` | Quest |
| 4 | `skill` | Skill |
| 5 | `character` | Character |
| 6 | `region` | Region |
| 7 | `faction` | Faction |

**Example:** `World/Knowledge/KnowledgeInfo_Item.xml`
- Folder says "Knowledge"
- But filename contains "item" (priority keyword)
- **Result: "Item" (NOT Knowledge!)**

### Category Summary

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         ALL CATEGORIES AT A GLANCE                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  TIER 1: STORY (VRS-ordered, chronological)                                  ║
║  ─────────────────────────────────────────                                   ║
║    │                                                                          ║
║    ├── Sequencer      │ Story cutscenes, major moments  │ FFE599 (orange)   ║
║    ├── AIDialog       │ NPC ambient conversation        │ C6EFCE (green)    ║
║    ├── QuestDialog    │ Quest dialogue trees            │ C6EFCE (green)    ║
║    └── NarrationDialog│ Tutorial text, narration        │ C6EFCE (green)    ║
║                                                                               ║
║  TIER 2: GAME_DATA (Keyword-based, alphabetical)                             ║
║  ───────────────────────────────────────────────                             ║
║    │                                                                          ║
║    ├── Item           │ Weapons, armor, consumables     │ D9D2E9 (purple)   ║
║    ├── Quest          │ Quest descriptions, objectives  │ D9D2E9 (purple)   ║
║    ├── Character      │ NPCs, monsters, animals         │ F8CBAD (peach)    ║
║    ├── Gimmick        │ Interactive objects             │ D9D2E9 (purple)   ║
║    ├── Skill          │ Abilities, spells               │ D9D2E9 (purple)   ║
║    ├── Knowledge      │ Lore, codex entries             │ D9D2E9 (purple)   ║
║    ├── Faction        │ Faction names, descriptions     │ D9D2E9 (purple)   ║
║    ├── UI             │ Interface text                  │ A9D08E (teal)     ║
║    ├── Region         │ Location names                  │ F8CBAD (peach)    ║
║    └── System_Misc    │ Everything else                 │ D9D9D9 (grey)     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## VRS Ordering

### What is VRS?

**VoiceRecordingSheet (VRS)** is the master Excel file containing all voiced lines in **chronological story order**. LanguageDataExporter uses VRS to sort STORY content so LQA reviewers see dialogue in the order players experience it.

### How It Works

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                            VRS ORDERING FLOW                                   ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   1. Load VoiceRecordingSheet.xlsx                                           ║
║      └── Read EventName from Column W                                        ║
║      └── Store: EventName → Row Position (e.g., "seq_quest_01" → row 100)   ║
║                                                                               ║
║   2. Scan EXPORT XMLs (Dialog/, Sequencer/)                                  ║
║      └── Extract SoundEventName attribute from each StringID                 ║
║      └── Store: StringID → SoundEventName                                    ║
║                                                                               ║
║   3. Sort STORY Entries                                                      ║
║      └── For each entry: StringID → SoundEventName → VRS Row                ║
║      └── Sort by VRS row position                                           ║
║                                                                               ║
║   4. Result: Chronological Story Order!                                      ║
║      └── LQA sees content in the order players experience it                ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Output Files

### Language Excel Files

**Filename:** `LanguageData_{LANG}.xlsx`

#### Columns (EU Languages - 11 columns)

| Column | Header | Description |
|--------|--------|-------------|
| A | **StrOrigin** | Korean source text |
| B | **ENG** | English reference |
| C | **Str** | Translated text |
| D | **Correction** | Empty - for LQA corrections |
| E | **Text State** | Auto-filled: KOREAN / TRANSLATED |
| F | **STATUS** | Dropdown: ISSUE / NO ISSUE |
| G | **COMMENT** | Free-text QA notes |
| H | **MEMO1** | General-purpose memo |
| I | **MEMO2** | General-purpose memo |
| J | **Category** | Color-coded category |
| K | **StringID** | Unique identifier (TEXT format) |

#### Columns (Asian Languages - 10 columns)

| Column | Header | Description |
|--------|--------|-------------|
| A | **StrOrigin** | Korean source text |
| B | **Str** | Translated text |
| C | **Correction** | Empty - for LQA corrections |
| D | **Text State** | Auto-filled: KOREAN / TRANSLATED |
| E | **STATUS** | Dropdown: ISSUE / NO ISSUE |
| F | **COMMENT** | Free-text QA notes |
| G | **MEMO1** | General-purpose memo |
| H | **MEMO2** | General-purpose memo |
| I | **Category** | Color-coded category |
| J | **StringID** | Unique identifier (TEXT format) |

### StringID as TEXT

StringID column is now formatted as TEXT to prevent Excel from displaying large numbers as scientific notation:

| Without TEXT format | With TEXT format |
|---------------------|------------------|
| `1.23457E+12` | `1234567890123` |

### Sheet Protection

Sheet protection is **disabled by default** (`protect_sheet=False`) to allow Ctrl+H (Find & Replace) across all columns.

When enabled (`protect_sheet=True`), the following columns are editable:
- **Correction** - LQA correction field
- **STATUS** - Issue tracking dropdown
- **COMMENT** - Free-text QA notes
- **MEMO1 / MEMO2** - General-purpose memo fields

All other columns (StrOrigin, ENG, Str, Text State, Category, StringID) are locked.

**No password required** - the protection prevents accidental edits, not malicious ones.

---

## LQA Correction Workflow

### Complete Workflow Diagram

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        LQA CORRECTION WORKFLOW                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  STEP 1: GENERATE                                                            ║
║  ════════════════                                                            ║
║    Click "Generate Language Excels"                                          ║
║    Output: GeneratedExcel/LanguageData_*.xlsx                                ║
║    Columns: StrOrigin | ENG | Str | Correction | Text State | STATUS | COMMENT | MEMO1 | MEMO2 | Category | StringID ║
║                                                                               ║
║                                    ↓                                          ║
║                                                                               ║
║  STEP 2: STAGE FOR REVIEW                                                    ║
║  ════════════════════════                                                    ║
║    Copy files from GeneratedExcel/ → ToSubmit/                               ║
║    (Or click "Open ToSubmit Folder" and drag files there)                    ║
║                                                                               ║
║                                    ↓                                          ║
║                                                                               ║
║  STEP 3: LQA REVIEW (Manual)                                                 ║
║  ═══════════════════════════                                                 ║
║    Open each file in ToSubmit/                                               ║
║    Review Str column (current translation)                                   ║
║    IF correction needed: Fill Correction column                              ║
║    IF no correction needed: Leave Correction empty                           ║
║    Save file                                                                 ║
║                                                                               ║
║                                    ↓                                          ║
║                                                                               ║
║  STEP 4: MERGE TO LOCDEV (MAIN STEP!)                                        ║
║  ════════════════════════════════════                                        ║
║    Click "Merge to LOCDEV" button                                            ║
║    Tool will:                                                                ║
║      1. Read corrections from ToSubmit Excel files                           ║
║      2. Match using STRICT criteria: StringID + StrOrigin must BOTH match   ║
║      3. Update Str attribute in LOCDEV XML files                             ║
║      4. Update Progress Tracker with SUCCESS/FAIL counts                     ║
║                                                                               ║
║                                    ↓                                          ║
║                                                                               ║
║  STEP 5: PREPARE FOR SUBMIT (Optional, for archival)                         ║
║  ═══════════════════════════════════════════════════                         ║
║    Click "Prepare For Submit" button                                         ║
║    Tool will:                                                                ║
║      1. Create backup in ToSubmit/backup_YYYYMMDD_HHMMSS/                    ║
║      2. Extract rows with Correction values only                             ║
║      3. Output only 3 columns: StrOrigin | Correction | StringID             ║
║    (Creates clean archive files for record-keeping)                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## LOCDEV Merge

### What It Does

Pushes corrections from Excel files back to LOCDEV XML files. This is the final step to integrate LQA corrections into the game.

### How It Works

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           LOCDEV MERGE PROCESS                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ToSubmit/LanguageData_FRE.xlsx          LOCDEV/languagedata_fre.xml        ║
║   ══════════════════════════════          ═══════════════════════════        ║
║                                                                               ║
║   ┌──────────┬───────────┬──────────┐    <LocStr                             ║
║   │StrOrigin │ Correction│ StringID │      StringId="1001"                   ║
║   ├──────────┼───────────┼──────────┤      StrOrigin="몬스터"                 ║
║   │ 몬스터   │ Créature  │   1001   │      Str="Monstre"                     ║
║   │ 철검     │           │   1002   │    />                                  ║
║   │ 안녕     │ Bonjour!  │   1003   │                                        ║
║   └──────────┴───────────┴──────────┘         │                              ║
║         │                                      │                              ║
║         │    STRICT MATCHING                   │                              ║
║         │    ═══════════════                   │                              ║
║         │                                      ▼                              ║
║         │    Both must match:          <LocStr                               ║
║         │    • StringID = "1001"         StringId="1001"                     ║
║         │    • StrOrigin = "몬스터"       StrOrigin="몬스터"                  ║
║         │                                Str="Créature"  ◀── UPDATED!        ║
║         └───────────────────────────▶  />                                    ║
║                                                                               ║
║   NOTE: Row with StringID 1002 has empty Correction → NOT processed          ║
║   NOTE: Only rows WITH Correction values are merged                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Why STRICT Matching?

The merge uses **STRICT matching** (StringID + StrOrigin must BOTH match) to prevent incorrect updates:

| Scenario | StringID Match | StrOrigin Match | Result |
|----------|---------------|-----------------|--------|
| Perfect match | ✓ | ✓ | **UPDATED** |
| Same ID, different source | ✓ | ✗ | No update (safety) |
| Same source, different ID | ✗ | ✓ | No update (safety) |
| Neither matches | ✗ | ✗ | No update |

### Text Normalization

Before matching, text is normalized to handle minor differences:

1. **HTML unescape**: `&lt;` → `<`, `&amp;` → `&`
2. **Strip whitespace**: Remove leading/trailing spaces
3. **Collapse internal whitespace**: Multiple spaces → single space

This ensures `"Hello   World"` matches `"Hello World"`.

---

## ENG/ZHO-CN Exclusions

### What It Does

For **ENG (English)** and **ZHO-CN (Simplified Chinese)**, the tool automatically **excludes Dialog and Sequencer categories** from the generated Excel files.

### Why?

These languages have **voiceover**. The Dialog/Sequencer content is handled separately through the voice recording pipeline, not through text-based LQA.

### Categories Excluded

| Category | Description |
|----------|-------------|
| Sequencer | Story cutscenes |
| AIDialog | NPC ambient dialog |
| QuestDialog | Quest dialog trees |
| NarrationDialog | Tutorial/narration |

### Result

| Language | Categories Included |
|----------|---------------------|
| **ENG** | Item, Quest, Character, Skill, UI, etc. (NO Dialog/Sequencer) |
| **ZHO-CN** | Item, Quest, Character, Skill, UI, etc. (NO Dialog/Sequencer) |
| **FRE, GER, SPA, etc.** | ALL categories (including Dialog/Sequencer) |

### Example

```
LanguageData_ENG.xlsx   →  ~50,000 rows (GAME_DATA only)
LanguageData_FRE.xlsx   →  ~80,000 rows (ALL categories)
LanguageData_GER.xlsx   →  ~80,000 rows (ALL categories)
LanguageData_ZHO-CN.xlsx → ~50,000 rows (GAME_DATA only)
```

---

## Code Pattern Analyzer (Removed)

The Code Pattern Analyzer feature has been removed from the GUI in v3.3. The underlying `pattern_analyzer.py` module remains available for CLI use if needed.

---

## Progress Tracker

### Overview

The **Correction Progress Tracker** (`Correction_ProgressTracker.xlsx`) tracks your LQA merge results over time. It's automatically updated when you click **"Merge to LOCDEV"**.

### What It Tracks

| Metric | Description |
|--------|-------------|
| **Corrections** | Total rows with Correction values in Excel |
| **Success** | Corrections that matched StringID + StrOrigin in LOCDEV |
| **Fail** | Corrections that did NOT match (possibly outdated or typo) |
| **Success %** | Success / Corrections × 100 |

### Tracker Structure

```
Correction_ProgressTracker.xlsx
├── WEEKLY          # Week-over-week merge results (visible)
│   └── Language | Week | Corrections | Success | Fail | Success %
├── TOTAL           # Summary per language (visible)
│   └── Language | Corrections | Success | Fail | Success %
└── _WEEKLY_DATA    # Raw data storage (hidden)
```

### Weekly Grouping

Data is grouped by **week** (Monday start) based on the **file modification time** of the Excel files in ToSubmit. This allows tracking corrections made in different weeks even if they're merged together.

---

## Configuration

### settings.json

**Location:** `LanguageDataExporter/settings.json`

```json
{
  "drive_letter": "F",
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__",
  "locdev_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\locdev__"
}
```

### Changing Drive Letter

```bash
# Using drive_replacer.py
python drive_replacer.py D          # Set to D: drive
python drive_replacer.py F          # Set to F: drive
```

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
| **Uncategorized strings** | StringID not in EXPORT | Content team needs to export those strings |
| **StringID shows as E+12** | Old version | Update to v3.0+ (TEXT format fix) |
| **LOCDEV merge no matches** | StrOrigin mismatch | Check text normalization, whitespace |

---

## Reference

### Supported Languages

| Code | Language | Count Method | English Column | Dialog/Seq Excluded |
|------|----------|--------------|----------------|---------------------|
| ENG | English | Words | No | **YES** |
| ZHO-CN | Chinese (Simplified) | Characters | No | **YES** |
| FRE | French | Words | Yes | No |
| GER | German | Words | Yes | No |
| SPA | Spanish | Words | Yes | No |
| POR | Portuguese | Words | Yes | No |
| ITA | Italian | Words | Yes | No |
| RUS | Russian | Words | Yes | No |
| TUR | Turkish | Words | Yes | No |
| POL | Polish | Words | Yes | No |
| THA | Thai | Words | Yes | No |
| VIE | Vietnamese | Words | Yes | No |
| IND | Indonesian | Words | Yes | No |
| MSA | Malay | Words | Yes | No |
| JPN | Japanese | Characters | No | No |
| ZHO-TW | Chinese (Traditional) | Characters | No | No |

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
│   ├── excel_writer.py        # Excel output
│   ├── submit_preparer.py     # LQA submission preparation
│   ├── locdev_merger.py       # LOCDEV merge
│   └── pattern_analyzer.py    # Code pattern analysis (CLI only)
├── tracker/                   # Progress tracking module
├── reports/                   # Word count reports
├── gui/
│   └── app.py                 # tkinter GUI
└── utils/
    ├── language_utils.py      # Korean detection, language config
    └── vrs_ordering.py        # VoiceRecordingSheet ordering
```

---

*Last updated: February 2026*
*Version: 3.3.0 - Column restructure (STATUS/COMMENT/MEMO1/MEMO2), USER GUIDE button, Code Pattern Analyzer removed from GUI*
