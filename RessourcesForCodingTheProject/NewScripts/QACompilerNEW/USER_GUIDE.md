# QA Compiler Suite - User Guide

<div align="center">

![Version](https://img.shields.io/badge/Version-2.0-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production-success?style=for-the-badge)

**Your Complete Guide to QA Localization Workflow**

---

</div>

## Table of Contents

| Section | Description |
|---------|-------------|
| [Installation](#-installation) | Build and setup |
| [Workflows Overview](#-workflows-overview) | Weekly vs Daily tasks |
| [Weekly Workflow](#-weekly-workflow-friday-refresh) | Generate → Transfer → Build |
| [Daily Workflow](#-daily-workflow) | Download and organize tester files |
| [Main Interface](#-main-interface) | Understanding the GUI |
| [1. Generate Datasheets](#-1-generate-datasheets) | Create LQA worksheets |
| [2. Transfer QA Files](#-2-transfer-qa-files) | Merge tester work |
| [3. Build Master Files](#-3-build-master-files) | Compile master documents |
| [4. Coverage Analysis](#-4-coverage-analysis) | Check translation coverage |
| [5. System Localizer](#-5-system-localizer) | Localize System sheets |
| [6. Update Tracker](#-6-update-tracker-retroactive) | **Backfill missing days** |
| [Category Reference](#-category-reference) | Category clustering and column layouts |
| [Folder Structure](#-folder-structure) | Where files go |
| [Folder Naming Convention](#folder-naming-convention) | How to name tester folders |
| [Troubleshooting](#-troubleshooting) | Common issues |

---

## 🚀 Installation

### Simple Portable Install

Download, extract, and run. No admin rights needed!

| Step | Action |
|------|--------|
| 1 | **Download** `QACompiler_Setup.exe` |
| 2 | **Run** the installer |
| 3 | **Select your Perforce drive** (F:, D:, E:, etc.) |
| 4 | **Choose folder** (default: same folder as installer) |
| 5 | **Done!** Double-click `QACompiler.exe` to run |

### During Installation

The installer will ask for your Perforce drive letter:

```
Select your Perforce drive:
  ○ F: drive (default)
  ○ D: drive
  ○ E: drive
  ○ Other...
```

### Requirements

| Requirement | Details |
|-------------|---------|
| Windows | 10 or higher |
| Perforce | Must be synced to your machine |

> **Note:** No admin rights needed. No Python required. Portable install.

### Installation Folder

Installs in the same folder (portable):

```
C:\MyTools\QACompiler\       ← Your chosen folder
├── QACompiler.exe           ← Main application
├── QAfolder\
├── QAfolderOLD\
├── QAfolderNEW\
├── GeneratedDatasheets\
├── Masterfolder_EN\
└── Masterfolder_CN\
```

---

## 📋 Workflows Overview

The QA Compiler supports two main workflows:

| Workflow | Frequency | Purpose |
|----------|-----------|---------|
| **Daily** | Every day | Collect tester submissions into QAfolder |
| **Weekly (Friday Refresh)** | Every Friday | Refresh datasheets and compile masters |

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY WORKFLOW (Simple)                       │
│         Download from Redmine → Put into QAfolder/              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    WEEKLY WORKFLOW (Friday)                      │
│  Move QAfolder→OLD → Generate → Transfer → Build Master Files   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📆 Daily Workflow

Every day, collect tester submissions. Simple!

### Step 1: Download from Redmine

Testers upload their completed QA files to Redmine.

| Source | What to Download |
|--------|------------------|
| Redmine | Tester-submitted QA folders |
| Format | `이름_Category` folders |

### Step 2: Put into QAfolder

Put downloaded folders **directly into `QAfolder/`**. That's it!

| Action | Details |
|--------|---------|
| Download | Get tester folders from Redmine |
| Place | Put directly into `QAfolder/` |
| Done | Files accumulate throughout the week |

> **Note:** Daily workflow does NOT use QAfolderOLD or QAfolderNEW. Those are only for the weekly refresh.

---

## 📅 Weekly Workflow (Friday Refresh)

Every Friday, refresh the QA files with latest game data.

### Step 1: Move QAfolder to OLD

Move ALL contents from `QAfolder/` to `QAfolderOLD/`.

| Action | Details |
|--------|---------|
| Move | Everything in `QAfolder/` → `QAfolderOLD/` |
| Result | `QAfolder/` is now empty |
| Purpose | Preserve tester work for merging |

### Step 2: Generate Fresh Datasheets

Creates fresh LQA worksheets from game XML data.

| Action | Details |
|--------|---------|
| Click | **[Generate Selected]** (or select all) |
| Output | `GeneratedDatasheets/` folder |
| Important | Sheets must be freshly generated (< 10 hours old) |

### Step 3: Transfer QA Files

The Transfer process will:
1. Check that generated sheets are fresh
2. Auto-create folders in `QAfolderNEW/` matching `QAfolderOLD/`
3. Auto-copy the correct generated sheet for each tester's language
4. Merge OLD tester work with NEW sheets
5. Output combined files to `QAfolder/`

| Action | Details |
|--------|---------|
| Click | **[Transfer QA Files]** |
| Auto-does | Creates QAfolderNEW folders + copies sheets |
| Output | `QAfolder/` (merged OLD work + NEW sheets) |

### Step 4: Build Master Files

Compiles everything into final master documents.

| Action | Details |
|--------|---------|
| Click | **[Build Master Files]** |
| Output | `Masterfolder_EN/` and `Masterfolder_CN/` |
| Includes | Progress tracker (`_TRACKER.xlsx`) |

### Weekly Workflow Summary

```
1. Move QAfolder → OLD    →  Preserve all tester work
2. Generate Datasheets    →  Fresh sheets from game XML
3. Transfer QA Files      →  Auto-populate NEW + merge with OLD
4. Build Master Files     →  Compile into Master files + Tracker
```

---

## 📁 QAfolder Behavior (Important!)

The `QAfolder/` is the **master collection** of all QA work.

### Tester Languages

Each tester is assigned a language in `languageTOtester_list.txt`:

| Language Code | Language | Example |
|---------------|----------|---------|
| `ENG` | English | Most testers |
| `ZHO-CN` | Chinese (Simplified) | Chinese team |

The Transfer process uses this mapping to copy the correct generated datasheet.

### Golden Rules

| Rule | Explanation |
|------|-------------|
| **Never delete manually** | Files are managed by Transfer process |
| **Only add/edit** | New categories get added, existing ones get updated |
| **Auto-updated** | Transfer process handles all merging |
| **Keeps history** | Completed categories stay until next refresh |

### How It Works

```
Before Transfer:
QAfolder/
├── 김민영_Quest/      ← Completed last week, KEEP IT
├── 박지훈_Knowledge/  ← Completed last week, KEEP IT
└── (empty for new categories)

After Transfer:
QAfolder/
├── 김민영_Quest/      ← Still there (untouched)
├── 박지훈_Knowledge/  ← Still there (untouched)
├── 이수진_Item/       ← NEW - just transferred
└── 최영희_Region/     ← NEW - just transferred
```

### Why This Matters

- **Completed work is preserved** until weekly refresh
- **No accidental deletions** - Transfer only adds/updates
- **Incremental updates** - Add new categories as testers finish

---

## 🖥️ Main Interface

```
┌────────────────────────────────────────────────────────────┐
│              QA Compiler Suite v2.0                        │
├────────────────────────────────────────────────────────────┤
│  📋 1. Generate Datasheets                                 │
│     ☑ Quest    ☑ Knowledge   ☑ Item      ☑ Region           │
│     ☑ System   ☑ Character   ☑ Skill     ☑ Help            │
│     ☑ Gimmick  ☑ Contents    ☑ Sequencer ☑ Dialog  ☑ Face  │
│     [Select All] [Deselect All] [Generate Selected]        │
├────────────────────────────────────────────────────────────┤
│  📁 2. Transfer QA Files                                   │
│     [Transfer QA Files]                                    │
├────────────────────────────────────────────────────────────┤
│  🔨 3. Build Master Files                                  │
│     [Build Master Files]                                   │
├────────────────────────────────────────────────────────────┤
│  📊 4. Coverage Analysis                                   │
│     [Run Coverage Analysis]                                │
├────────────────────────────────────────────────────────────┤
│  🌐 5. System Sheet Localizer                              │
│     [Localize System Sheet]                                │
├────────────────────────────────────────────────────────────┤
│  🔄 6. Update Tracker Only                                 │
│     Date: [2025-01-16    ] [Set File Dates...]             │
│     [Update Tracker]                                       │
├────────────────────────────────────────────────────────────┤
│  Status: Ready                                             │
│  [════════════════════════════════════════]                │
└────────────────────────────────────────────────────────────┘
```

---

## 📋 1. Generate Datasheets

**Purpose:** Create fresh LQA worksheets from game XML data.

### Category Guide

| Category | Contains | Generation | Output |
|----------|----------|------------|--------|
| **Quest** | Main story, faction, daily quests | ✅ Auto | `QuestData_Map_All/` |
| **Knowledge** | Encyclopedia entries | ✅ Auto | `Knowledge_LQA_All/` |
| **Item** | Items, equipment, consumables | ✅ Auto | `ItemData_Map_All/` |
| **Region** | Areas, locations, POIs | ✅ Auto | `Region_LQA_v3/` |
| **Character** | NPCs, monsters | ✅ Auto | `Character_LQA_All/` |
| **Skill** | Player abilities | ✅ Auto | `Skill_LQA_All/` |
| **Help** | Tutorial, tips | ✅ Auto | `GameAdvice_LQA_All/` |
| **Gimmick** | Interactive objects | ✅ Auto | `Gimmick_LQA_Output/` |
| **System** | UI text, menus | 🔧 Manual | Use System Localizer (Section 5) |
| **Contents** | Content instructions | 🔧 Manual | Prepared externally |
| **Sequencer** | Cutscene/event scripts | 🔧 Manual | Script-type (see below) |
| **Dialog** | NPC dialogue scripts | 🔧 Manual | Script-type (see below) |
| **Face** | Facial animation QA | 🔧 Manual | Face-type (see below) |

> **Note:** System, Contents, Sequencer, Dialog, and Face sheets are NOT auto-generated. System sheets are created via the System Localizer. The others are prepared manually/externally.

### Quest Datasheet Features

The Quest generator produces the most complex datasheets with multiple tabs and special features.

#### Quest Tab Organization

```
Quest_LQA_ENG.xlsx
├── Main Quest           (scenario-based main story)
├── Faction 1            (primary faction with OrderByString)
├── Faction 2            (primary faction with OrderByString)
├── ...
├── Region Quest         (*_Request StrKey)
├── Daily                (*_Daily StrKey + Group="daily")
├── Politics             (*_Situation StrKey)
├── Challenge Quest
├── Minigame Quest
└── Others               (leftover factions without OrderByString)
```

#### Faction Unlock Commands

Primary faction sheets include **unlock commands** in the Command column to help testers quickly unlock faction content for testing.

**How It Works:**

| Faction Type | Command Source | Example |
|--------------|----------------|---------|
| **Primary Factions** (with OrderByString) | `EndQuestKey` from `<EventData>` elements | `/complete quest Quest_BloodCoronation_WitchDukeAndDream` |
| **Leftover Factions** (Daily, Request, Situation) | `Condition` attributes from child `<Quest>` elements | `/complete quest Quest_A && Quest_B` |

**Output Format:**

The faction header row (depth 0, yellow background) includes the unlock command:

| Scenario | Command Output |
|----------|---------------|
| Single unlock quest | `/complete quest Quest_BloodCoronation_WitchDukeAndDream` |
| Multiple unlock quests | `/complete quest Quest_A && Quest_B && Quest_C` |
| No unlock quest found | (empty) |

**XML Source Example:**

Primary factions extract `EndQuestKey` from `<EventData>` elements inside `<Faction>`:

```xml
<Faction StrKey="Faction_BloodCoronation" Name="Blood Coronation">
  <EventData EndQuestKey="Quest_BloodCoronation_WitchDukeAndDream" />
  <EventData EndQuestKey="Quest_BloodCoronation_SecondArc" />
</Faction>
```

This generates: `/complete quest Quest_BloodCoronation_WitchDukeAndDream && Quest_BloodCoronation_SecondArc`

**Use Case:**

Testers can copy-paste the unlock command directly into the game console to:
1. Unlock the faction content
2. Skip prerequisite quests
3. Access faction-specific quests for testing

### Script-Type Categories (Sequencer & Dialog)

Sequencer and Dialog are special **Script-type** categories with different column layouts:

| Feature | Standard Categories | Script-Type (Sequencer/Dialog) |
|---------|--------------------|---------------------------------|
| **Master Output** | Various (Quest, Item, etc.) | `Master_Script.xlsx` |
| **Comment Column** | COMMENT | MEMO |
| **Row Matching** | STRINGID | EventName |
| **SCREENSHOT** | ✅ Yes | ❌ No |
| **Typical Size** | 1,000-5,000 rows | 10,000+ rows |

**Key Differences:**
- Uses `MEMO` column instead of `COMMENT`
- Uses `EventName` for matching (acts as the identifier like STRINGID does for other categories)
- NO SCREENSHOT column
- Both Sequencer and Dialog merge into `Master_Script.xlsx`
- Testers commonly use "NON-ISSUE" (with hyphen) - the code accepts both "NON-ISSUE" and "NO ISSUE"

### Face Category (Special Processing)

Face is a special category for **facial animation QA**. Unlike standard categories, Face does NOT build a traditional Master file. Instead it produces separate output files per language:

| Output File | Contents |
|-------------|----------|
| `MasterMismatch_EN.xlsx` | EventNames with MISMATCH status (EN) |
| `MasterMismatch_CN.xlsx` | EventNames with MISMATCH status (CN) |
| `MasterMissing_EN.xlsx` | EventNames with MISSING status (EN) |
| `MasterMissing_CN.xlsx` | EventNames with MISSING status (CN) |
| `MasterConflict_EN.xlsx` | EventNames in BOTH mismatch and missing (EN) |
| `MasterConflict_CN.xlsx` | EventNames in BOTH mismatch and missing (CN) |

**Face Tester STATUS Options:**

| Status | Meaning |
|--------|---------|
| `NO ISSUE` | Animation checked, looks good |
| `MISMATCH` | Animation doesn't match audio/text |
| `MISSING` | Animation is missing entirely |

**Key Differences from Standard Categories:**

| Feature | Standard Categories | Face |
|---------|--------------------|----|
| **Master Output** | `Master_*.xlsx` (combined per-tester) | `MasterMismatch_*.xlsx` + `MasterMissing_*.xlsx` |
| **Row Matching** | STRINGID | EventName |
| **STATUS values** | ISSUE / NO ISSUE / BLOCKED / KOREAN | NO ISSUE / MISMATCH / MISSING |
| **Per-tester columns** | Yes (COMMENT, STATUS per user) | No (deduped EventName lists) |
| **Date-tab history** | No | Yes (each run adds MMDD tab) |

**Cross-Tab Deduplication:**

Each compilation adds a new date tab (e.g., "0204" for Feb 4th). EventNames that already exist in previous tabs are automatically skipped — only NEW EventNames are written to the latest tab. This prevents duplicates across runs while preserving history.

**Conflict Resolution:**

If the same EventName appears as both MISMATCH and MISSING across different testers, it is placed in MISMATCH (the more actionable status) and logged in the Conflict file.

### Tester Sheet Columns (Generated Datasheets)

| Column | Description | Editable? |
|--------|-------------|-----------|
| **Original (KR)** | Korean source text | ❌ No |
| **English (ENG)** | English translation | ❌ No |
| **Translation** | Target language text | ❌ No |
| **STATUS** | Issue status dropdown | ✅ Yes |
| **COMMENT** | Tester notes | ✅ Yes |
| **STRINGID** | Unique identifier | ❌ No |
| **SCREENSHOT** | Screenshot reference | ✅ Yes |

### Master File Columns (After Build)

Master files include additional columns per tester:

| Column | Description | Editable? |
|--------|-------------|-----------|
| **COMMENT_{User}** | Tester's comment (from QA) | ❌ Preserved |
| **TESTER_STATUS_{User}** | Original tester status | ❌ Hidden |
| **STATUS_{User}** | Manager review status | ✅ Yes |
| **MANAGER_COMMENT_{User}** | Manager's notes | ✅ Yes |
| **SCREENSHOT_{User}** | Screenshot reference | ❌ Preserved |

### Tester STATUS Options

| Status | Meaning | Color |
|--------|---------|-------|
| `ISSUE` | Problem found - needs fix | 🔴 Red |
| `NO ISSUE` | Checked, looks good | 🟢 Green |
| `BLOCKED` | Cannot test | 🟡 Yellow |
| `KOREAN` | Still in Korean | 🟠 Orange |

> **Note on "NO ISSUE" vs "NON-ISSUE":** The code accepts BOTH formats:
> - `NO ISSUE` (with space) - standard format used by most categories
> - `NON-ISSUE` (with hyphen) - also accepted, commonly used in Script-type categories
>
> Both are treated identically by the system - use whichever your testers prefer.

### How Duplicate Text Gets the Correct StringID

The same Korean text can appear in multiple game files with **different StringIDs**. The generator automatically finds the correct StringID for each occurrence using **EXPORT folder matching**.

#### The Problem

```
Korean text "무기를 장착합니다" appears in:
  - skillinfo_pc.xml      → Should get StringID_A
  - iteminfo_weapon.xml   → Should get StringID_B

Without smart matching, the system might assign the wrong StringID!
```

#### The Solution: EXPORT Folder Matching

The generator matches each data file to its corresponding EXPORT file:

```
┌─────────────────────────────────────────────────────────────┐
│  SOURCE FILE              →    EXPORT FILE    →   STRINGID  │
├─────────────────────────────────────────────────────────────┤
│  skillinfo_pc.xml         →    EXPORT/skillinfo_pc.xml      │
│  Korean "무기를 장착합니다"  →    Found StringID_A here!      │
├─────────────────────────────────────────────────────────────┤
│  iteminfo_weapon.xml      →    EXPORT/iteminfo_weapon.xml   │
│  Korean "무기를 장착합니다"  →    Found StringID_B here!      │
└─────────────────────────────────────────────────────────────┘
```

#### How It Works

1. **Track Source File** - Each text entry remembers which XML file it came from
2. **Load All Translations** - Language tables store ALL (translation, stringid) pairs for each Korean text
3. **Match via EXPORT** - When multiple StringIDs exist for the same Korean text:
   - Look up the EXPORT file matching the source data file
   - Find which StringID exists in that EXPORT file
   - Return the correct (translation, stringid) pair
4. **Fallback** - If no EXPORT match found, use the first valid translation

#### Result

Each generated datasheet has the **correct StringID** for each row, even when the same Korean text appears in multiple game files with different identifiers.

> **Technical Note:** This matching is automatic and invisible to users. The EXPORT folder must be synced from Perforce for accurate StringID resolution.

---

## 📁 2. Transfer QA Files

**Purpose:** Merge tester work from OLD/NEW folders into QAfolder.

### The Flow

```
┌─────────────────┐     ┌─────────────────┐
│  QAfolderOLD    │     │  QAfolderNEW    │
│  (Previous QA)  │     │  (Current QA)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌─────────────────┐
            │    QAfolder     │
            │  (Combined)     │
            └─────────────────┘
```

### How to Use

| Step | Action |
|------|--------|
| 1 | Place OLD tester folders in `QAfolderOLD/` |
| 2 | Place NEW tester folders in `QAfolderNEW/` |
| 3 | Click **[Transfer QA Files]** |
| 4 | Combined output appears in `QAfolder/` |

---

## 🔨 3. Build Master Files

**Purpose:** Compile all QA files into master documents with progress tracking.

### How Master Build Works (Technical)

The master build process uses **content-based matching** to preserve all tester work:

#### Step 1: Template Selection (Most Recent File)

```
Multiple QA files for same category:
├── 김민영_Quest/file.xlsx  (modified Jan 15)
├── 박지훈_Quest/file.xlsx  (modified Jan 16)  ← MOST RECENT = TEMPLATE
└── 이수진_Quest/file.xlsx  (modified Jan 14)
```

The **most recent file** (by modification date) is used as the template structure.
This ensures the master has the freshest column layout.

> **Multiple XLSX in Same Folder:** When a tester folder contains multiple xlsx files, the **most recently modified** file is used. This is useful when testers save multiple versions - only the latest matters.

#### Step 2: Content-Based Row Matching (2-Step Cascade)

Each tester's data is matched to master rows using a 2-step cascade:

| Category | Step 1 (Primary Match) | Step 2 (Fallback) |
|----------|------------------------|-------------------|
| **Standard** (Quest, Knowledge, etc.) | STRINGID + Translation | Translation only |
| **Item** | ItemName + ItemDesc + STRINGID | ItemName + ItemDesc |
| **Contents** | INSTRUCTIONS column | (unique, no fallback) |

This prevents data loss even when row order changes between builds.

#### Step 3: Data Preservation

For each matched row, these columns are preserved:

| From Tester QA | From Previous Master |
|----------------|---------------------|
| COMMENT_{User} | STATUS_{User} (manager status) |
| TESTER_STATUS_{User} | MANAGER_COMMENT_{User} |
| SCREENSHOT_{User} | |

> **Key Benefit:** Manager work (status + comments) survives master rebuilds because matching is content-based, not row-index-based.

### Category Merging

Some categories are **merged** into combined master files:

| Input Category | Output Master File |
|----------------|-------------------|
| Quest | `Master_Quest.xlsx` |
| Knowledge | `Master_Knowledge.xlsx` |
| Item | `Master_Item.xlsx` |
| Region | `Master_Region.xlsx` |
| Character | `Master_Character.xlsx` |
| Contents | `Master_Contents.xlsx` |
| **Skill** | `Master_System.xlsx` ← *merged* |
| **Help** | `Master_System.xlsx` ← *merged* |
| **Gimmick** | `Master_Item.xlsx` ← *merged* |
| **Sequencer** | `Master_Script.xlsx` ← *merged* |
| **Dialog** | `Master_Script.xlsx` ← *merged* |
| **Face** | `MasterMismatch_*.xlsx` + `MasterMissing_*.xlsx` + `MasterConflict_*.xlsx` ← *special* |

### Output Structure

```
Masterfolder_EN/
├── Master_Quest.xlsx
├── Master_Knowledge.xlsx
├── Master_Item.xlsx        ← includes Gimmick
├── Master_Region.xlsx
├── Master_System.xlsx      ← includes Skill + Help
├── Master_Character.xlsx
├── Master_Contents.xlsx
├── Master_Script.xlsx      ← includes Sequencer + Dialog
├── MasterMismatch_EN.xlsx  ← Face: mismatched animations
├── MasterMissing_EN.xlsx   ← Face: missing animations
├── MasterConflict_EN.xlsx  ← Face: in both mismatch+missing (if any)
├── _TRACKER.xlsx           ← Progress tracking
└── Images/
```

### Progress Tracker

The `_TRACKER.xlsx` contains:

| Sheet | Shows |
|-------|-------|
| **DAILY** | Day-by-day progress per tester |
| **TOTAL** | Overall statistics and rankings |
| **Facial** | Face category progress (separate from standard) |
| **_DAILY_DATA** | Raw data for standard categories (hidden) |
| **_FACIAL_DATA** | Raw data for Face category (hidden) |

#### TOTAL Tab Structure

The TOTAL tab displays per-tester statistics in three color-coded sections:

| Section | Color | Columns |
|---------|-------|---------|
| **Tester Stats** | 🔵 Blue | Done, Issues, No Issue, Blocked, Korean |
| **Manager Stats** | 🟢 Green | Fixed, Reported, NonIssue, Checking, Pending |
| **Workload Analysis** | 🟠 Light Orange | Actual Done, Daily Avg, Type, Days Worked, Tester Assessment |

##### Workload Analysis Columns

| Column | Formula/Source | Description |
|--------|----------------|-------------|
| **Actual Done** | `Done - Blocked - Korean` | Real completed work count |
| **Daily Avg** | `Actual Done / Days Worked` | Daily productivity metric |
| **Type** | From `TesterType.txt` | "Text" or "Gameplay" |
| **Days Worked** | Manual entry | Manager fills in days |
| **Tester Assessment** | Manual entry | Manager's quality notes |

> **Note:** Configure tester types in `TesterType.txt` (same format as `languageTOtester_list.txt`)

#### Facial Tab Structure

The Facial tab tracks Face category QA progress. There are 2 QA files (one for EN, one for CN). Each file is shared with multiple testers. Each tester is assigned specific groups to check — testers generally don't overlap. The goal is to collectively cover 100% of the file.

The tab has 5 sections:

| Section | Shows |
|---------|-------|
| **FACIAL DAILY TABLE** | Per-user daily Done/Mismatch/Missing counts (all users) |
| **EN FACIAL TOTAL TABLE** | EN testers with TOTAL row showing cumulative coverage |
| **CN FACIAL TOTAL TABLE** | CN testers with TOTAL row showing cumulative coverage |
| **EN FACIAL CATEGORY TABLE** | EN groups — per-group coverage breakdown |
| **CN FACIAL CATEGORY TABLE** | CN groups — per-group coverage breakdown |

**How Done% works:**

- **TOTAL tables (per tester):** Each tester's Done% = their items done / total items. The TOTAL row is a **SUM** of all testers' Done% — it shows collective coverage toward 100%.
- **CATEGORY tables (per group):** Total = actual group size (not summed across testers). Done% = items done by all testers / group size. Shows how much of that group is covered.

```
EN FACIAL TOTAL TABLE
| User    | Total | Done | NoIssue | Mismatch | Missing | Done%  |
| Alice   | 5000  | 1500 | 1400    | 70       | 30      | 30.0%  |
| Bob     | 5000  | 2500 | 2400    | 80       | 20      | 50.0%  |
| Charlie | 5000  | 1000 | 950     | 30       | 20      | 20.0%  |
| TOTAL   |       | 5000 | 4750    | 180      | 70      | 100.0% |

EN FACIAL CATEGORY TABLE
| Group       | Total | Done | NoIssue | Mismatch | Missing | Done%  |
| NPC_Human   | 3000  | 3000 | 2850    | 100      | 50      | 100.0% |
| NPC_Monster | 2000  | 2000 | 1900    | 80       | 20      | 100.0% |
```

> **Key rules:** Total column = actual group/file size (never summed across testers). Done% is never averaged. EN and CN data are always separate — never mixed.

### Automatic Row Hiding

Rows are automatically hidden based on two status columns:

#### TESTER STATUS (`TESTER_STATUS_{User}` - hidden column)

This is the **tester's original status** (from their QA work):

| Status | Hidden? | Reason |
|--------|---------|--------|
| `ISSUE` | ❌ No | Active issue - needs attention |
| `BLOCKED` | ✅ Yes | Tester couldn't test |
| `KOREAN` | ✅ Yes | Still in Korean |
| `NO ISSUE` | ✅ Yes | No problem found |

#### MANAGER STATUS (`STATUS_{User}` - visible column)

This is the **manager's review status** (dropdown in Master file):

| Status | Hidden? | Reason |
|--------|---------|--------|
| `FIXED` | ✅ Yes | Issue resolved |
| `NON-ISSUE` | ✅ Yes | Not actually an issue |
| `REPORTED` | ❌ No | Reported to dev team |
| `CHECKING` | ❌ No | Under investigation |
| *(empty)* | ❌ No | Pending manager review |

#### MANAGER COMMENT (`MANAGER_COMMENT_{User}` - visible column)

Manager notes paired with manager status. Both are preserved when master files are rebuilt.

| Feature | Description |
|---------|-------------|
| **Paired with** | `STATUS_{User}` |
| **Preserved on rebuild** | ✅ Yes - keyed by tester comment |
| **Use case** | Track why status was set, additional notes |

**Summary:** Only `ISSUE` rows that haven't been resolved by manager are visible.

#### SCREENSHOT Column Auto-Hide

`SCREENSHOT_{User}` columns are automatically hidden if ALL cells in the column are empty.

---

## 📊 4. Coverage Analysis

**Purpose:** Calculate translation coverage.

Creates `Coverage_Report_YYYYMMDD_HHMMSS.xlsx` with:

| Sheet | Contents |
|-------|----------|
| **Coverage Report** | Strings covered per category |
| **Word Count** | Korean + Translation word counts |

---

## 🔄 6. Update Tracker (Retroactive)

**Purpose:** Add missing days to the Progress Tracker WITHOUT rebuilding master files.

### When to Use

| Scenario | Use This Feature? |
|----------|-------------------|
| Forgot to run Build Master on a specific day | ✅ Yes |
| Need to backfill tracker data for missed days | ✅ Yes |
| Normal daily workflow | ❌ No - use Build Master Files |

### Folder Structure

```
TrackerUpdateFolder/
├── QAfolder/              ← Tester QA files (for tester stats)
│   └── 김민영_Quest/
│       └── file.xlsx
├── Masterfolder_EN/       ← English master files (for manager stats)
│   └── Master_Quest.xlsx
└── Masterfolder_CN/       ← Chinese master files (for manager stats)
    └── Master_Quest.xlsx
```

### Step-by-Step Process

| Step | Action | Details |
|------|--------|---------|
| 1 | **Copy files** | Copy QA files and/or Master files to `TrackerUpdateFolder/` |
| 2 | **Set date** | Enter target date (YYYY-MM-DD) in the date field |
| 3 | **Click "Set File Dates"** | Select the folder containing your files |
| 4 | **Click "Update Tracker"** | Updates tracker with the file date, not today |

### Critical: File Date = Tracker Date

The tracker uses the **file's Last Modified date** to determine which day to record:

| File Modified Date | Tracker Entry Date |
|-------------------|-------------------|
| 2025-01-16 | 2025-01-16 |
| 2025-01-18 | 2025-01-18 |

**The "Set File Dates" button changes BOTH:**
- ✅ xlsx files
- ✅ Parent folders
- ✅ Root selected folder

### What Gets Updated

| Source | Updates |
|--------|---------|
| **QAfolder/** files | Tester stats (Done, Issues, No Issue, Blocked, Korean) |
| **Masterfolder_EN/** files | Manager stats (Fixed, Reported, Checking, Non-Issue) |
| **Masterfolder_CN/** files | Manager stats (Fixed, Reported, Checking, Non-Issue) |

### Example: Backfill January 16th

```
1. Copy your QA files from Jan 16th backup to:
   TrackerUpdateFolder/QAfolder/

2. Copy your Master files from Jan 16th backup to:
   TrackerUpdateFolder/Masterfolder_EN/
   TrackerUpdateFolder/Masterfolder_CN/

3. Enter date: 2025-01-16

4. Click "Set File Dates" → Select TrackerUpdateFolder

5. Click "Update Tracker"

Result: Tracker now has data for 2025-01-16!
```

---

## 🌐 5. System Localizer

**Purpose:** Create localized System sheets for all languages.

### Output

```
System_LQA_All/
├── System_ENG.xlsx
├── System_DEU.xlsx
├── System_FRA.xlsx
├── System_JPN.xlsx
└── ... (all languages)
```

### Matching Process

```
Step 1: StringID → Korean → Target Language (most accurate)
Step 2: English Text → Korean → Target Language (fallback)
```

---

## 📚 Category Reference

This section provides detailed reference information about category clustering, column layouts, and special processing.

### Category Clustering Diagram

Categories are **clustered** into master files. Some categories share a master file:

```
┌─────────────────────────────────────────────────────────────┐
│  CATEGORY CLUSTERING (What merges where)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Quest ────────────────────► Master_Quest.xlsx              │
│  Knowledge ────────────────► Master_Knowledge.xlsx          │
│  Item ─────────┬───────────► Master_Item.xlsx               │
│  Gimmick ──────┘                                            │
│  Region ───────────────────► Master_Region.xlsx             │
│  System ───────┬───────────► Master_System.xlsx             │
│  Skill ────────┤                                            │
│  Help ─────────┘                                            │
│  Character ────────────────► Master_Character.xlsx          │
│  Contents ─────────────────► Master_Contents.xlsx           │
│  Sequencer ────┬───────────► Master_Script.xlsx             │
│  Dialog ───────┘                                            │
│  Face ───────────────────► MasterMismatch/Missing_*.xlsx    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Column Layout by Category Type

Different category types have different column structures:

| Type | Categories | Key Columns |
|------|------------|-------------|
| **Standard** | Quest, Knowledge, Region, Character | STRINGID \| Translation \| STATUS \| COMMENT \| SCREENSHOT |
| **Item** | Item, Gimmick | ItemName \| ItemDesc \| STRINGID \| STATUS \| COMMENT \| SCREENSHOT |
| **System** | System, Skill, Help | CONTENT \| STATUS \| COMMENT \| STRINGID \| SCREENSHOT |
| **Contents** | Contents | CONTENT \| INSTRUCTIONS \| STATUS \| COMMENT \| SCREENSHOT |
| **Script** | Sequencer, Dialog | EventName \| Text \| Translation \| STATUS \| MEMO (no SCREENSHOT) |
| **Face** | Face | EventName \| Group \| STATUS (NO ISSUE / MISMATCH / MISSING) |

#### Detailed Column Reference

<details>
<summary><b>Standard Categories (Quest, Knowledge, Region, Character)</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| Original (KR) | Korean source text | ❌ |
| English (ENG) | English translation | ❌ |
| Translation | Target language | ❌ |
| **STATUS** | Issue status dropdown | ✅ |
| **COMMENT** | Tester notes | ✅ |
| STRINGID | Unique identifier (for matching) | ❌ |
| **SCREENSHOT** | Screenshot reference | ✅ |

</details>

<details>
<summary><b>Item Categories (Item, Gimmick)</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| ItemName | Item name | ❌ |
| ItemDesc | Item description | ❌ |
| STRINGID | Unique identifier | ❌ |
| **STATUS** | Issue status dropdown | ✅ |
| **COMMENT** | Tester notes | ✅ |
| **SCREENSHOT** | Screenshot reference | ✅ |

</details>

<details>
<summary><b>System Categories (System, Skill, Help)</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| CONTENT | System text content | ❌ |
| **STATUS** | Issue status dropdown | ✅ |
| **COMMENT** | Tester notes | ✅ |
| STRINGID | Unique identifier | ❌ |
| **SCREENSHOT** | Screenshot reference | ✅ |

</details>

<details>
<summary><b>Contents Category</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| CONTENT | Content text | ❌ |
| INSTRUCTIONS | Context instructions | ❌ |
| **STATUS** | Issue status dropdown | ✅ |
| **COMMENT** | Tester notes | ✅ |
| **SCREENSHOT** | Screenshot reference | ✅ |

</details>

<details>
<summary><b>Script Categories (Sequencer, Dialog)</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| EventName | Event identifier (used for matching) | ❌ |
| Text | Original text | ❌ |
| Translation | Target language | ❌ |
| **STATUS** | Issue status dropdown | ✅ |
| **MEMO** | Tester notes (NOT "COMMENT") | ✅ |

> **Note:** Script categories do NOT have a SCREENSHOT column.

</details>

<details>
<summary><b>Face Category</b></summary>

| Column | Description | Editable? |
|--------|-------------|-----------|
| EventName | Animation event identifier | No |
| Group | Animation group/scene | No |
| **STATUS** | Review status (NO ISSUE / MISMATCH / MISSING) | Yes |

> **Note:** Face does NOT produce per-tester columns in a master file. Instead, all testers' findings are deduplicated by EventName into MasterMismatch and MasterMissing output files.

</details>

### Script-Type Optimization (Clean Slate Processing)

Script files (Sequencer/Dialog) can have **10,000+ rows**, making full processing slow. The system uses "clean slate" preprocessing:

```
┌─────────────────────────────────────────────────────────────┐
│  SCRIPT-TYPE OPTIMIZATION                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Original Script File (10,000+ rows)                        │
│  ├── Row 1: (no status)     ← SKIPPED                       │
│  ├── Row 2: (no status)     ← SKIPPED                       │
│  ├── Row 3: STATUS=ISSUE    ← PROCESSED                     │
│  ├── Row 4: (no status)     ← SKIPPED                       │
│  ├── Row 5: STATUS=NO ISSUE ← PROCESSED                     │
│  └── ... (10,000 more)                                      │
│                                                             │
│  Filtered Template: Only rows WITH STATUS are processed     │
│  Result: Much faster than processing all 10,000+ rows       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**How it works:**
1. Script files are scanned for rows that have a STATUS value
2. Only rows WITH STATUS (ISSUE, NO ISSUE, BLOCKED, etc.) are included
3. Creates a "clean slate" template with only the checked rows
4. This dramatically speeds up processing for large script files

---

## 📂 Folder Structure

```
QACompiler/
├── QACompiler.exe           ← Main application
│
├── QAfolderOLD/             ← Previous round tester files
│   ├── 김민영_Quest/
│   └── 박지훈_Item/
│
├── QAfolderNEW/             ← Current round tester files
│   ├── 김민영_Quest/
│   └── 박지훈_Item/
│
├── QAfolder/                ← Combined (auto-generated)
│   ├── 김민영_Quest/
│   └── 박지훈_Item/
│
├── GeneratedDatasheets/     ← From "Generate Datasheets"
│
├── Masterfolder_EN/         ← English master output
│   ├── Master_Quest.xlsx
│   ├── _TRACKER.xlsx
│   └── Images/
│
├── Masterfolder_CN/         ← Chinese master output
│
└── TrackerUpdateFolder/     ← For retroactive tracker updates (Section 6)
    ├── QAfolder/            ← Tester files for backfill
    ├── Masterfolder_EN/     ← Master files for manager stats
    └── Masterfolder_CN/     ← Master files for manager stats
```

### Folder Naming Convention

Tester folders must follow this format: **`이름_Category`**

| Format | Example | Explanation |
|--------|---------|-------------|
| `이름_Category` | `김민영_Quest` | Name + underscore + Category |

#### Valid Examples

| Folder Name | Tester | Category |
|-------------|--------|----------|
| `김민영_Quest` | 김민영 | Quest |
| `박지훈_Item` | 박지훈 | Item |
| `이수진_Knowledge` | 이수진 | Knowledge |
| `최영희_Region` | 최영희 | Region |
| `John_Quest` | John | Quest |

#### Valid Categories

| Category | Type | Master Output |
|----------|------|---------------|
| Quest | Standard | Master_Quest.xlsx |
| Knowledge | Standard | Master_Knowledge.xlsx |
| Item | Item | Master_Item.xlsx |
| Region | Standard | Master_Region.xlsx |
| System | System | Master_System.xlsx |
| Character | Standard | Master_Character.xlsx |
| Skill | System | Master_System.xlsx |
| Help | System | Master_System.xlsx |
| Gimmick | Item | Master_Item.xlsx |
| Contents | Contents | Master_Contents.xlsx |
| Sequencer | Script | Master_Script.xlsx |
| Dialog | Script | Master_Script.xlsx |
| Face | Face | MasterMismatch_*.xlsx + MasterMissing_*.xlsx |

#### Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| Single underscore | `김민영_Quest` | `김_민_영_Quest` |
| Category at end | `김민영_Quest` | `Quest_김민영` |
| Exact category name | `김민영_Quest` | `김민영_quest` |

---

## 🔧 Troubleshooting

<details>
<summary><b>❌ "Generator modules not yet implemented"</b></summary>

**Cause:** Generator files missing or import failed.

**Solution:**
1. Verify all files present
2. Check `generators/` folder exists
3. Re-extract from package

</details>

<details>
<summary><b>❌ "No datasheets found in GeneratedDatasheets"</b></summary>

**Cause:** Coverage analysis needs datasheets first.

**Solution:**
1. Run "Generate Datasheets" first
2. Verify files in `GeneratedDatasheets/`
3. Then run Coverage Analysis

</details>

<details>
<summary><b>❌ Path errors mentioning wrong drive</b></summary>

**Cause:** Executable built for different drive.

**Solution:**
1. Re-run `build_exe.bat`
2. Enter YOUR drive letter when prompted
3. Use the new executable

</details>

<details>
<summary><b>❌ Excel file corrupted</b></summary>

**Cause:** Process interrupted during write.

**Solution:**
1. Delete corrupted file
2. Run operation again
3. Don't close app while progress bar active

</details>

<details>
<summary><b>❌ Folder not recognized</b></summary>

**Cause:** Folder name doesn't match `이름_Category` format.

**Solution:**
1. Check folder name format: `김민영_Quest`
2. Verify category is valid (Quest, Item, etc.)
3. Use single underscore only

</details>

---

## 📞 Support

| Need | Contact |
|------|---------|
| Bug reports | Your QA Lead |
| Feature requests | Development Team |
| Access issues | IT Department |

---

<div align="center">

**QA Compiler Suite v2.0**

*Making localization QA easier, one datasheet at a time.*

---

![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue?style=flat-square&logo=python)
![Excel Support](https://img.shields.io/badge/Excel-Supported-green?style=flat-square&logo=microsoft-excel)

</div>
