<div align="center">

# QA Compiler Suite v2.0

### Complete User Guide

---

**Version 2.0.0** | **January 2025**

---

*Unified LQA Datasheet Generation & QA Compilation Tool*

</div>

---

<div style="page-break-after: always;"></div>

## Quick Reference Card

> **Keep this page handy for daily operations!**

### Essential Commands

```bash
python main.py                    # Launch GUI
python main.py --generate all     # Generate all datasheets
python main.py --transfer         # Transfer OLD → NEW
python main.py --build            # Build master files
python main.py --all              # Full pipeline (transfer + build)
```

### Folder Structure at a Glance

```
QACompilerNEW/
├── QAfolder/              ← Put tester work here
├── QAfolderOLD/           ← OLD files for transfer
├── QAfolderNEW/           ← NEW files for transfer
├── Masterfolder_EN/       ← English output
├── Masterfolder_CN/       ← Chinese output
├── GeneratedDatasheets/   ← Generated datasheets
└── languageTOtester_list.txt  ← Tester mapping
```

### QA Folder Naming (CRITICAL!)

```
✅  John_Quest       ✅  Mary_Item       ✅  Chen_Knowledge
❌  John Quest       ❌  Mary-Item       ❌  chen_knowledge
     (spaces!)           (hyphen!)           (inconsistent!)
```

### Status Values

| Tester Status | Manager Status |
|:-------------:|:--------------:|
| ISSUE | FIXED |
| NO ISSUE | REPORTED |
| BLOCKED | CHECKING |
| KOREAN | NON-ISSUE |

---

<div style="page-break-after: always;"></div>

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Installation & Setup](#3-installation--setup)
4. [The Four Functions](#4-the-four-functions)
5. [GUI Guide](#5-gui-guide)
6. [CLI Reference](#6-cli-reference)
7. [Tester Configuration](#7-tester-configuration)
8. [Categories Explained](#8-categories-explained)
9. [Workflow Recipes](#9-workflow-recipes)
10. [Troubleshooting](#10-troubleshooting)

---

<div style="page-break-after: always;"></div>

## 1. Overview

### What is QA Compiler Suite?

The QA Compiler Suite is your all-in-one tool for managing Language Quality Assurance workflows. It handles everything from generating test datasheets to compiling final master files.

### The Four Core Functions

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   1. GENERATE          2. TRANSFER         3. BUILD            │
│   ───────────          ──────────          ─────               │
│   XML Sources    →     OLD + NEW     →     QAfolder    →       │
│   to Datasheets        Merge Work          to Masters          │
│                                                                 │
│                        4. COVERAGE                              │
│                        ────────                                 │
│                        Analyze coverage & word counts           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | What It Does |
|---------|--------------|
| **EN/CN Separation** | Routes testers to correct language Master file |
| **Manager Workflow** | FIXED/REPORTED/CHECKING/NON-ISSUE tracking |
| **Progress Tracker** | Daily stats, totals, and rankings |
| **Category Clustering** | Skill+Help→System, Gimmick→Item |
| **Image Management** | Auto-copy with hyperlink preservation |
| **Two-Pass Matching** | STRINGID+Trans first, then Trans fallback |

---

<div style="page-break-after: always;"></div>

## 2. Quick Start

### 5-Minute Setup

**Step 1: Install Dependencies**
```bash
pip install openpyxl lxml
```

**Step 2: Configure Paths**

Edit `config.py` and update these paths:
```python
RESOURCE_FOLDER = Path(r"F:\your\path\to\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\your\path\to\stringtable\loc")
```

**Step 3: Set Up Tester Mapping**

Create `languageTOtester_list.txt`:
```
ENG
John
Mary

ZHO-CN
Chen
Wei
```

**Step 4: Run!**
```bash
python main.py
```

---

### First-Time Workflow

```
   START
     │
     ▼
┌─────────────────┐
│ Generate        │    python main.py --generate all
│ Datasheets      │
└────────┬────────┘
         │
         ▼
   Distribute to
     Testers
         │
         ▼
    Testers work
    on datasheets
         │
         ▼
┌─────────────────┐
│ Collect work    │    Copy to QAfolder/{User}_{Category}/
│ in QAfolder     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build Masters   │    python main.py --build
└────────┬────────┘
         │
         ▼
    Check outputs:
    • Masterfolder_EN/
    • Masterfolder_CN/
    • Progress Tracker
```

---

<div style="page-break-after: always;"></div>

## 3. Installation & Setup

### System Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.8 or higher |
| Disk Space | ~100MB + generated files |
| RAM | 4GB minimum (8GB recommended for large datasets) |
| Network | Access to game resource paths |

### Step-by-Step Installation

#### 1. Extract Package

```
C:\Tools\QACompilerNEW\
```

#### 2. Install Python Packages

```bash
pip install openpyxl lxml
```

#### 3. Verify Installation

```bash
python main.py --version
# Output: QA Compiler Suite v2.0.0

python main.py --list
# Shows all available categories
```

### Configuration File (config.py)

#### Critical Paths to Configure

```python
# Main game data paths
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")

# Quest-specific paths
SCENARIO_FOLDER = Path(r"...\staticinfo_quest\scenario")
FACTION_QUEST_FOLDER = Path(r"...\staticinfo_quest\quest\faction")
FACTIONINFO_FOLDER = Path(r"...\StaticInfo\factioninfo")
```

#### Category Clustering (Pre-configured)

```python
# These categories merge into others:
CATEGORY_TO_MASTER = {
    "Skill": "System",   # Skill → Master_System.xlsx
    "Help": "System",    # Help → Master_System.xlsx
    "Gimmick": "Item",   # Gimmick → Master_Item.xlsx
}
```

---

<div style="page-break-after: always;"></div>

## 4. The Four Functions

### Function 1: Generate Datasheets

> **Purpose:** Create Excel datasheets from game XML sources for QA testers

#### What It Does

```
Game XML Files                    Excel Datasheets
(StaticInfo)     ──────────────►  (Per Language)

• questgroupinfo.xml              • Quest_LQA_ENG.xlsx
• knowledgeinfo.xml               • Quest_LQA_FRE.xlsx
• iteminfo.xml                    • Quest_LQA_ZHO.xlsx
• etc.                            • etc.
```

#### Columns Generated

| Column | Purpose |
|--------|---------|
| Original | Korean source text |
| ENG | English translation |
| {Language} | Target language (hidden for ENG) |
| StringKey | For /complete commands |
| Command | /complete and /teleport |
| STATUS | Dropdown: ISSUE, NO ISSUE, BLOCKED, KOREAN |
| COMMENT | Tester notes |
| STRINGID | Unique identifier |
| SCREENSHOT | Image reference |

#### Usage

```bash
# Generate specific categories
python main.py --generate quest knowledge item

# Generate ALL categories (9 total)
python main.py --generate all
```

---

### Function 2: Transfer QA Files

> **Purpose:** Preserve tester work when datasheets are updated

#### When to Use

- New datasheets generated (content changed)
- Need to migrate existing work to new version
- Updating mid-project

#### How It Works

```
QAfolderOLD/           QAfolderNEW/           QAfolder/
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ STATUS: ISSUE│  +   │ STATUS: ___  │  =   │ STATUS: ISSUE│
│ COMMENT: Bug │      │ COMMENT: ___ │      │ COMMENT: Bug │
│ SCREENSHOT:X │      │ SCREENSHOT:_ │      │ SCREENSHOT:X │
└──────────────┘      └──────────────┘      └──────────────┘
   (Old work)           (New empty)           (Merged!)
```

#### Matching Algorithm

| Pass | Standard Categories | Item Category |
|------|---------------------|---------------|
| **Pass 1** (Exact) | STRINGID + Translation | ItemName + ItemDesc + STRINGID |
| **Pass 2** (Fallback) | Translation only | ItemName + ItemDesc |

#### Usage

```bash
python main.py --transfer
```

---

### Function 3: Build Master Files

> **Purpose:** Compile individual QA files into centralized Masters

#### What It Does

```
QAfolder/                         Masterfolder_EN/
├── John_Quest/     ─────────►   ├── Master_Quest.xlsx
├── Mary_Quest/                  │   (John + Mary combined)
├── Chen_Item/                   └── Master_Item.xlsx
└── Wei_Item/
                                  Masterfolder_CN/
                    ─────────►   ├── Master_Quest.xlsx
                                 └── Master_Item.xlsx
                                     (Chen + Wei)

                    ─────────►   LQA_Tester_ProgressTracker.xlsx
```

#### Per-User Columns Added

- `STATUS_{Username}` - Manager status (FIXED, REPORTED, etc.)
- `COMMENT_{Username}` - Notes with metadata
- `SCREENSHOT_{Username}` - Image links

#### Usage

```bash
python main.py --build
```

---

### Function 4: Coverage Analysis

> **Purpose:** Calculate coverage and word counts

#### Metrics

- **String Coverage:** % of language data covered by datasheets
- **Word Count:** Total words (EN) or characters (CN) per category

#### Output

- Terminal report
- Excel file: `Coverage_Report_YYYYMMDD_HHMMSS.xlsx`

#### Usage

```bash
# Via GUI: Click "Run Coverage Analysis"
# Or after generating datasheets, it runs automatically
```

---

<div style="page-break-after: always;"></div>

## 5. GUI Guide

### Launching

```bash
python main.py
# or
python main.py --gui
```

### Interface Overview

```
╔════════════════════════════════════════════════════════════╗
║              QA Compiler Suite v2.0                        ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  ┌─ 1. Generate Datasheets ─────────────────────────────┐  ║
║  │                                                       │  ║
║  │   ☑ Quest      ☑ Knowledge   ☑ Item                  │  ║
║  │   ☑ Region     ☑ System      ☑ Character             │  ║
║  │   ☑ Skill      ☑ Help        ☑ Gimmick               │  ║
║  │                                                       │  ║
║  │   [Select All]  [Deselect All]  [Generate Selected]  │  ║
║  └───────────────────────────────────────────────────────┘  ║
║                                                            ║
║  ┌─ 2. Transfer QA Files ───────────────────────────────┐  ║
║  │   QAfolderOLD + QAfolderNEW → QAfolder               │  ║
║  │                                                       │  ║
║  │              [Transfer QA Files]                      │  ║
║  └───────────────────────────────────────────────────────┘  ║
║                                                            ║
║  ┌─ 3. Build Master Files ──────────────────────────────┐  ║
║  │   QAfolder → Masterfolder_EN / Masterfolder_CN       │  ║
║  │                                                       │  ║
║  │              [Build Master Files]                     │  ║
║  └───────────────────────────────────────────────────────┘  ║
║                                                            ║
║  ┌─ 4. Coverage Analysis ───────────────────────────────┐  ║
║  │   Calculate coverage + word counts                    │  ║
║  │                                                       │  ║
║  │              [Run Coverage Analysis]                  │  ║
║  └───────────────────────────────────────────────────────┘  ║
║                                                            ║
║  Status: Ready                                             ║
║  [═══════════════════════════════════════════════════════] ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### Using Each Section

| Section | Action | Result |
|---------|--------|--------|
| **1. Generate** | Check categories, click Generate | Datasheets in GeneratedDatasheets/ |
| **2. Transfer** | Click Transfer | Merged files in QAfolder/ |
| **3. Build** | Click Build | Master files + Tracker |
| **4. Coverage** | Click Coverage | Report in console + Excel |

---

<div style="page-break-after: always;"></div>

## 6. CLI Reference

### Complete Command Reference

| Command | Short | Description |
|---------|-------|-------------|
| `--help` | `-h` | Show help message |
| `--version` | `-v` | Show version |
| `--list` | `-l` | List available categories |
| `--generate CATS` | `-g CATS` | Generate datasheets |
| `--transfer` | `-t` | Transfer QA files |
| `--build` | `-b` | Build master files |
| `--all` | `-a` | Full pipeline (transfer + build) |
| `--gui` | | Force GUI mode |

### Examples

```bash
# Show help
python main.py --help

# Generate Quest and Item only
python main.py --generate quest item

# Generate ALL categories
python main.py --generate all

# Full daily workflow
python main.py --all

# Multiple operations
python main.py --generate quest --build
```

---

<div style="page-break-after: always;"></div>

## 7. Tester Configuration

### The Mapping File

File: `languageTOtester_list.txt`

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

### Rules

| Rule | Description |
|------|-------------|
| Section headers | `ENG` or `ZHO-CN` only |
| One name per line | Exact match with folder names |
| Empty lines | Ignored |
| Default | Unmapped testers → EN |

### Effect on Routing

| Tester | Mapping | Output |
|--------|---------|--------|
| John | ENG | Masterfolder_EN/ |
| Mary | ENG | Masterfolder_EN/ |
| Chen | ZHO-CN | Masterfolder_CN/ |
| Unknown | (default) | Masterfolder_EN/ |

---

<div style="page-break-after: always;"></div>

## 8. Categories Explained

### All 9 Categories

| # | Category | Source | Description |
|---|----------|--------|-------------|
| 1 | **Quest** | scenario/, faction/, challenge/ | All quest types |
| 2 | **Knowledge** | knowledgeinfo/, knowledgegroupinfo/ | Knowledge entries |
| 3 | **Item** | iteminfo/, itemgroupinfo/ | Items with descriptions |
| 4 | **Region** | factiongroupinfo/ | Faction/Region data |
| 5 | **System** | *(Skill + Help)* | Combined category |
| 6 | **Character** | characterinfo_*.xml | NPC/Monster info |
| 7 | **Skill** | skillinfo_pc.xml | Player skills |
| 8 | **Help** | gameadviceinfo.xml | GameAdvice entries |
| 9 | **Gimmick** | gimmickinfo/ | Gimmick objects |

### Quest Tab Organization

```
Quest_LQA_ENG.xlsx
│
├── Main Quest           ← From scenario/ folder
├── Faction 1           ← OrderByString from factioninfo
├── Faction 2
├── ...
├── Region Quest         ← *_Request StrKey pattern
├── Daily                ← *_Daily + Group="daily"
├── Politics             ← *_Situation StrKey pattern
├── Challenge Quest      ← From challenge/ folder
├── Minigame Quest       ← From contents_minigame.xml
└── Others               ← Leftover factions
```

### Category Clustering

```
Input                    Output
─────                    ──────
Skill   ─────┐
             ├────────►  Master_System.xlsx
Help    ─────┘

Gimmick ─────────────►  Master_Item.xlsx
                        (merged with Item)
```

---

<div style="page-break-after: always;"></div>

## 9. Workflow Recipes

### Recipe A: New Project

```bash
# 1. Generate datasheets
python main.py --generate all

# 2. Distribute to testers
# Copy from GeneratedDatasheets/

# 3. Collect completed work
# Testers put files in QAfolder/{Name}_{Category}/

# 4. Build masters
python main.py --build

# 5. Check outputs
ls Masterfolder_EN/
ls Masterfolder_CN/
cat LQA_Tester_ProgressTracker.xlsx
```

### Recipe B: Update Mid-Project

```bash
# 1. Backup current work
mv QAfolder/* QAfolderOLD/

# 2. Generate new datasheets
python main.py --generate quest

# 3. Copy new datasheets to QAfolderNEW
# (same structure as QAfolderOLD)

# 4. Transfer work
python main.py --transfer

# 5. Build updated masters
python main.py --build
```

### Recipe C: Daily Compilation

```bash
# One command does it all
python main.py --all
```

---

<div style="page-break-after: always;"></div>

## 10. Troubleshooting

### Common Issues & Solutions

---

#### ❌ "No valid QA folders found"

**Cause:** Folder naming is incorrect

**Solution:** Check naming format
```bash
# Check folders
ls QAfolder/

# Should see:
John_Quest/    ✅
Mary_Item/     ✅

# NOT:
John Quest/    ❌ (space)
Mary-Item/     ❌ (hyphen)
```

---

#### ❌ "Language folder not found"

**Cause:** Path in config.py is incorrect or not accessible

**Solution:**
1. Check Perforce workspace is synced
2. Verify path in config.py
3. Ensure network drive is connected

---

#### ❌ "No matching NEW folder for transfer"

**Cause:** OLD folder has no corresponding NEW folder

**Solution:** Ensure both exist with same name
```
QAfolderOLD/John_Quest/   ✅
QAfolderNEW/John_Quest/   ✅ (must exist!)
```

---

#### ❌ Low transfer success rate

**Cause:** Content changed significantly

**Solution:** This is expected. Unmatched rows mean strings were removed or modified. Check the duplicate translation report if generated.

---

#### ❌ Images not appearing

**Cause:** Hyperlinks broken

**Solution:**
1. Check `Images/` folder in Master output
2. Verify filenames match SCREENSHOT column
3. Avoid special characters in filenames

---

### Debug Mode

```bash
# Save all output to log file
python main.py --build 2>&1 | tee build.log
```

---

<div style="page-break-after: always;"></div>

## Quick Update Protocol

### Updating Individual Files (Instead of Full Zip)

When updates are made, you don't need to re-download the entire zip. Just replace the specific file(s) that changed.

#### File-to-Function Mapping

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

#### Update Steps

1. Download only the changed file(s) from the repository
2. Replace in your local installation:
   ```
   QACompilerNEW/
   └── generators/
       └── quest.py  ← Replace this file
   ```
3. Run to verify: `python main.py --list`

---

<div style="page-break-after: always;"></div>

## Appendix

### A. All Status Values

#### Tester Status (STATUS column)

| Value | Meaning |
|-------|---------|
| `ISSUE` | Translation issue found |
| `NO ISSUE` | Checked, no issue |
| `BLOCKED` | Cannot test |
| `KOREAN` | Korean text remaining |

#### Manager Status (STATUS_{User} column)

| Value | Meaning |
|-------|---------|
| `FIXED` | Issue resolved |
| `REPORTED` | Sent to development |
| `CHECKING` | Under review |
| `NON-ISSUE` | Not a real issue |

### B. File Limits

| Limit | Value |
|-------|-------|
| Max rows per Excel sheet | 1,048,576 |
| Recommended images per folder | 1,000 |
| Progress tracker entries | Unlimited |

### C. Supported Languages

ENG, FRE, DEU, SPA, ITA, JPN, ZHO, KOR, POR, RUS, and more...

### D. Progress Tracker Sheets

| Sheet | Content |
|-------|---------|
| **DAILY** | Daily deltas by user (EN/CN sections) |
| **TOTAL** | Cumulative totals, category breakdown, rankings |
| **_DAILY_DATA** | Hidden raw data storage |

### E. Ranking Formula

```
Score = 80% × Done + 20% × Actual Issues
```

Higher score = Better (rewards both productivity and issue finding)

---

<div align="center">

---

**QA Compiler Suite v2.0**

*Document Version: 1.0 | January 2025*

---

</div>
