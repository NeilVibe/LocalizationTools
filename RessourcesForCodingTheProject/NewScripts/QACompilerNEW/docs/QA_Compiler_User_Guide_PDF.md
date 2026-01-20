<div align="center">

# QA Compiler Suite v2.0

## Complete User Guide

---

**Version 2.0.0** | **January 2025**

---

*Your Complete Guide to LQA Datasheet Generation & QA Compilation*

---

**What's Inside:**

| Part | Content | Page |
|:----:|---------|:----:|
| **Quick Ref** | Essential commands at a glance | 2 |
| **Part 1** | Quick Start (New Users) | 3 |
| **Part 2** | Everyday Operations | 6 |
| **Part 3** | The OLD→NEW Update Process | 12 |
| **Part 4** | Detailed Reference | 17 |
| **Part 5** | Troubleshooting | 25 |
| **Appendix** | Status Values, CLI, Rules | 28 |

---

</div>

<div style="page-break-after: always;"></div>

---

# Quick Reference Card

> **📋 Keep this page handy for daily operations!**

---

## Essential Commands

```bash
python main.py                    # Launch GUI
python main.py --generate all     # Generate all datasheets
python main.py --transfer         # Transfer OLD → NEW
python main.py --build            # Build master files
python main.py --all              # Full pipeline (transfer + build)
```

---

## Folder Structure

```
QACompilerNEW/
├── 📁 QAfolder/              ← CURRENT tester work goes here
├── 📁 QAfolderOLD/           ← Backup during weekly refresh
├── 📁 QAfolderNEW/           ← Auto-created during Transfer
├── 📁 Masterfolder_EN/       ← English output
├── 📁 Masterfolder_CN/       ← Chinese output
├── 📁 GeneratedDatasheets/   ← Fresh datasheets here
└── 📄 languageTOtester_list.txt  ← Tester language mapping
```

---

## Folder Naming Rules (CRITICAL!)

```
✅ CORRECT              ❌ WRONG
─────────────────────────────────────────────
John_Quest              John Quest     (space!)
Mary_Item               Mary-Item      (hyphen!)
Chen_Knowledge          chen_knowledge (case mismatch!)
```

**Format:** `{TesterName}_{Category}` — underscore only, exact case match

---

## Status Values

| **Tester** (STATUS column) | **Manager** (STATUS_{User} column) |
|:--------------------------:|:----------------------------------:|
| ISSUE | FIXED |
| NO ISSUE | REPORTED |
| BLOCKED | CHECKING |
| KOREAN | NON-ISSUE |

---

<div style="page-break-after: always;"></div>

---

# Part 1: Quick Start

## For New Users — Start Here!

---

## What is QA Compiler Suite?

QA Compiler Suite is your all-in-one tool for managing Language Quality Assurance. It handles the entire workflow from generating test datasheets to compiling final master files.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QA COMPILER SUITE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐         │
│    │ GENERATE │ ──► │ TRANSFER │ ──► │  BUILD   │ ──► │ COVERAGE │         │
│    └──────────┘     └──────────┘     └──────────┘     └──────────┘         │
│         │                │                │                │                │
│         ▼                ▼                ▼                ▼                │
│    Create fresh     Preserve        Compile into      Analyze %           │
│    datasheets       tester work      Master files     complete            │
│    from XML         when updating                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5-Minute First Run

### Step 1: Install Dependencies

```bash
pip install openpyxl lxml
```

### Step 2: Configure Paths

Edit `config.py` and update these paths to match your environment:

```python
RESOURCE_FOLDER = Path(r"F:\your\path\to\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\your\path\to\stringtable\loc")
```

### Step 3: Set Up Tester Mapping

Create `languageTOtester_list.txt`:

```
ENG
John
Mary

ZHO-CN
Chen
Wei
```

### Step 4: Launch!

```bash
python main.py
```

> ✅ **SUCCESS**
> You should see the GUI window with four sections: Generate, Transfer, Build, Coverage.

---

<div style="page-break-after: always;"></div>

## Decision Tree: Which Workflow Do I Use?

```
                    ┌─────────────────────────────┐
                    │   Is this your FIRST TIME   │
                    │   using QA Compiler?        │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
            YES                                        NO
              │                                         │
              ▼                                         ▼
    ┌─────────────────┐               ┌─────────────────────────────┐
    │  Recipe A       │               │  Did the game data change?  │
    │  NEW PROJECT    │               │  (new translations, etc.)   │
    │  (see below)    │               └──────────────┬──────────────┘
    └─────────────────┘                              │
                                    ┌────────────────┴────────────────┐
                                    ▼                                 ▼
                                   YES                               NO
                                    │                                 │
                                    ▼                                 ▼
                          ┌─────────────────┐             ┌─────────────────┐
                          │  Recipe B       │             │  Recipe C       │
                          │  UPDATE         │             │  DAILY          │
                          │  (preserves     │             │  (just build)   │
                          │  tester work)   │             │                 │
                          └─────────────────┘             └─────────────────┘
```

---

## Recipe A: New Project (First Time)

Use this when starting fresh with no existing tester work.

```bash
# Step 1: Generate all datasheets
python main.py --generate all

# Step 2: Distribute files to testers
# Copy from GeneratedDatasheets/ to your shared drive

# Step 3: Testers complete their work
# They put finished files in QAfolder/{Name}_{Category}/

# Step 4: Build master files
python main.py --build
```

> ✅ **SUCCESS**
> Check: `Masterfolder_EN/Master_Quest.xlsx` should exist

---

## Recipe B: Update (Preserve Tester Work)

Use this when game data changes but you want to keep existing QA work.

```bash
# Step 1: Backup current work
mv QAfolder/* QAfolderOLD/

# Step 2: Generate fresh datasheets
python main.py --generate all

# Step 3: Transfer merges OLD work into NEW datasheets
python main.py --transfer

# Step 4: Build updated masters
python main.py --build
```

> 💡 **TIP**
> Transfer automatically preserves STATUS, COMMENT, and SCREENSHOT from OLD.

---

## Recipe C: Daily Compilation

Use this for normal daily work — no data changes, just building.

```bash
# One command does it all!
python main.py --all
```

Or in GUI: Click **[Build Master Files]**

---

<div style="page-break-after: always;"></div>

---

# Part 2: Everyday Operations

## Your Weekly QA Workflow

---

## The Complete Weekly Cycle

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      THE QA COMPILER WEEKLY CYCLE                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ╔═══════════════════════════════════════════════════════════════════════╗  │
│   ║  🗓️ FRIDAY — THE WEEKLY REFRESH                                       ║  │
│   ╠═══════════════════════════════════════════════════════════════════════╣  │
│   ║                                                                        ║  │
│   ║   1. BACKUP    →    Move QAfolder/* to QAfolderOLD/                   ║  │
│   ║   2. GENERATE  →    Create fresh datasheets from latest XML           ║  │
│   ║   3. TRANSFER  →    Merge OLD work into NEW datasheets                ║  │
│   ║   4. BUILD     →    Compile Master files + Progress Tracker           ║  │
│   ║                                                                        ║  │
│   ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                        │                                      │
│                                        ▼                                      │
│   ╔═══════════════════════════════════════════════════════════════════════╗  │
│   ║  📅 MONDAY — PREPARE FOR THE WEEK                                     ║  │
│   ╠═══════════════════════════════════════════════════════════════════════╣  │
│   ║                                                                        ║  │
│   ║   • Verify fresh datasheets in GeneratedDatasheets/                   ║  │
│   ║   • Distribute files to testers                                        ║  │
│   ║   • Assign categories: "John: Quest, Mary: Item, Chen: Knowledge"     ║  │
│   ║                                                                        ║  │
│   ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                        │                                      │
│                                        ▼                                      │
│   ╔═══════════════════════════════════════════════════════════════════════╗  │
│   ║  📥 TUESDAY–THURSDAY — DAILY COLLECTION                               ║  │
│   ╠═══════════════════════════════════════════════════════════════════════╣  │
│   ║                                                                        ║  │
│   ║   • Testers work on datasheets, report issues                         ║  │
│   ║   • Collect completed files → QAfolder/{Name}_{Category}/             ║  │
│   ║   • Run BUILD as needed to update Master files                        ║  │
│   ║   • Check Progress Tracker for status                                  ║  │
│   ║                                                                        ║  │
│   ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                        │                                      │
│                                        └─────────────► (back to FRIDAY)       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

<div style="page-break-after: always;"></div>

## 🗓️ MONDAY: Prepare for the Week

After Friday's refresh, you have fresh datasheets ready to distribute.

---

### Your Monday Checklist

| # | Task | How | Verify |
|:-:|------|-----|--------|
| 1 | Verify datasheets | Check `GeneratedDatasheets/` | All 9 categories present |
| 2 | Distribute to testers | Copy files to shared drive | Testers confirm receipt |
| 3 | Assign categories | Email or meeting | Everyone knows their tasks |

---

### What Testers Receive

Each tester gets ONE Excel file per assigned category:

```
GeneratedDatasheets/
├── QuestData_Map_All/
│   ├── Quest_LQA_ENG.xlsx    ← English tester (John)
│   ├── Quest_LQA_ZHO.xlsx    ← Chinese tester (Chen)
│   └── Quest_LQA_FRE.xlsx    ← French tester (Pierre)
├── ItemData_Map_All/
│   ├── Item_LQA_ENG.xlsx
│   └── ...
└── ...
```

---

### What Testers Do With Their Files

Testers fill in these columns for each row they test:

| Column | What to Enter | Example |
|--------|---------------|---------|
| **STATUS** | Dropdown value | `ISSUE`, `NO ISSUE`, `BLOCKED`, `KOREAN` |
| **COMMENT** | Description of issue | "Missing word in sentence" |
| **SCREENSHOT** | Reference to screenshot | `quest_bug_001.png` |

> ⚠️ **WARNING**
> Testers should NOT modify columns like STRINGID, Original, or translations. Only STATUS, COMMENT, and SCREENSHOT!

---

### Datasheet Columns Explained

| Column | Purpose | Editable? |
|--------|---------|:---------:|
| Original | Korean source text | ❌ |
| ENG | English translation | ❌ |
| {Language} | Target language | ❌ |
| StringKey | For /complete commands | ❌ |
| Command | Cheat commands | ❌ |
| **STATUS** | Issue status | ✅ |
| **COMMENT** | Tester notes | ✅ |
| STRINGID | Unique identifier | ❌ |
| **SCREENSHOT** | Image reference | ✅ |

---

<div style="page-break-after: always;"></div>

## 📥 DAILY: Collect Tester Work (Tue–Thu)

---

### Collection Workflow

```
TESTER                             MANAGER
──────                             ───────
  │                                   │
  │   1. Complete work                │
  │   2. Upload to Redmine            │
  │───────────────────────────────────►│
  │      or shared drive              │
  │                                   │
  │                                   │   3. Download file
  │                                   │   4. Copy to QAfolder/
  │                                   │
  │                                   ▼
  │                            ┌─────────────────┐
  │                            │  QAfolder/      │
  │                            │  ├─ John_Quest/ │
  │                            │  ├─ Mary_Item/  │
  │                            │  └─ Chen_Quest/ │
  │                            └─────────────────┘
  │                                   │
  │                                   │   5. Run BUILD
  │                                   │
  │                                   ▼
  │                            Master files +
  │                            Tracker updated
```

---

### Folder Structure Rules

> 🚨 **CRITICAL**
> Folder names MUST follow this exact format: `{TesterName}_{Category}`

**Examples:**

```
QAfolder/
├── John_Quest/           ✅ Correct
│   └── Quest_LQA_ENG.xlsx
├── Mary_Item/            ✅ Correct
│   └── Item_LQA_ENG.xlsx
├── Chen_Knowledge/       ✅ Correct
│   └── Knowledge_LQA_ZHO.xlsx
└── Wei_System/           ✅ Correct
    └── System_LQA_ZHO.xlsx
```

**Invalid names (will be ignored!):**

```
John Quest/     ❌ Space in name
Mary-Item/      ❌ Hyphen instead of underscore
chen_knowledge/ ❌ Case must match exactly!
quest/          ❌ Missing tester name
```

---

### Run BUILD After Collection

```bash
python main.py --build
```

Or in GUI: Click **[Build Master Files]**

> ✅ **SUCCESS**
> Check these outputs:
> - `Masterfolder_EN/Master_Quest.xlsx`
> - `Masterfolder_CN/Master_Quest.xlsx`
> - `LQA_Tester_ProgressTracker.xlsx`

---

<div style="page-break-after: always;"></div>

## 📅 FRIDAY: Weekly Compilation

**This is the MAIN event.** Refresh everything for the new week.

---

### Friday Checklist (Print This!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    📋 FRIDAY REFRESH CHECKLIST                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   □ Step 1: BACKUP                                                       │
│     └─ Move QAfolder/* → QAfolderOLD/                                   │
│                                                                          │
│   □ Step 2: GENERATE                                                     │
│     └─ Click [Generate All] or: python main.py --generate all           │
│                                                                          │
│   □ Step 3: TRANSFER                                                     │
│     └─ Click [Transfer QA Files] or: python main.py --transfer          │
│                                                                          │
│   □ Step 4: BUILD                                                        │
│     └─ Click [Build Master Files] or: python main.py --build            │
│                                                                          │
│   □ Step 5: VERIFY                                                       │
│     └─ Check: Masterfolder_EN/, Masterfolder_CN/, Tracker               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Step-by-Step with Expected Results

---

#### Step 1: BACKUP

```bash
mv QAfolder/* QAfolderOLD/
```

**What happens:** All current tester work moves to backup folder.

**Verify:** `QAfolder/` should be **EMPTY**.

> 💡 **TIP**
> Keep QAfolderOLD for at least one week as a safety backup.

---

#### Step 2: GENERATE

```bash
python main.py --generate all
```

**What happens:** Fresh datasheets created from latest game XML.

**Verify:** Check `GeneratedDatasheets/` has all 9 categories:

```
GeneratedDatasheets/
├── QuestData_Map_All/       ✅
├── KnowledgeData_Map_All/   ✅
├── ItemData_Map_All/        ✅
├── RegionData_Map_All/      ✅
├── SystemData_Map_All/      ✅
├── CharacterData_Map_All/   ✅
├── SkillData_Map_All/       ✅
├── HelpData_Map_All/        ✅
└── GimmickData_Map_All/     ✅
```

---

#### Step 3: TRANSFER

```bash
python main.py --transfer
```

**What happens:** Transfer reads OLD and NEW, merges tester work into fresh datasheets.

**Verify:** `QAfolder/` now has same structure as `QAfolderOLD/`, but with updated content.

> ✅ **SUCCESS CHECK**
> Open a merged file and verify:
> - STATUS values preserved from OLD
> - COMMENT preserved from OLD
> - New rows have empty STATUS/COMMENT

---

#### Step 4: BUILD

```bash
python main.py --build
```

**What happens:** Compiles all QAfolder data into Master files and Progress Tracker.

**Verify:**
- `Masterfolder_EN/Master_Quest.xlsx` exists
- `Masterfolder_CN/Master_Quest.xlsx` exists
- `LQA_Tester_ProgressTracker.xlsx` exists and has data

---

#### Step 5: VERIFY

Open the Progress Tracker and check:

| Sheet | What to Check |
|-------|---------------|
| **DAILY** | Today's date appears, deltas recorded |
| **TOTAL** | Cumulative totals updated |

---

<div style="page-break-after: always;"></div>

## Progress Tracker Deep Dive

The Progress Tracker automatically generates when you BUILD.

---

### Tracker Sheets

| Sheet | Purpose |
|-------|---------|
| **DAILY** | Day-by-day deltas per tester (EN and CN sections) |
| **TOTAL** | Cumulative totals, category breakdown, rankings |
| **_DAILY_DATA** | Hidden raw data (don't edit!) |

---

### TOTAL Sheet Columns

| Column | Meaning |
|--------|---------|
| **User** | Tester name |
| **Quest** | Count for Quest category |
| **Knowledge** | Count for Knowledge category |
| **Item** | Count for Item category |
| ... | Other categories |
| **Total** | Sum of all categories |
| **Issues** | Rows marked ISSUE |
| **Score** | Ranking score (see formula below) |

---

### Ranking Formula

```
Score = (80% × Done) + (20% × Actual Issues)
```

- **Done** = Total rows with any status (ISSUE, NO ISSUE, BLOCKED, KOREAN)
- **Actual Issues** = Rows specifically marked ISSUE

> 💡 **TIP**
> This rewards both productivity (getting work done) AND finding real issues.

---

### Manager Workflow Columns

When managers review tester work, they use these columns:

| Column | Values | Purpose |
|--------|--------|---------|
| **STATUS_{User}** | FIXED, REPORTED, CHECKING, NON-ISSUE | Manager's resolution |
| **COMMENT_{User}** | Free text | Manager's notes |
| **SCREENSHOT_{User}** | Image reference | Supporting evidence |

**Example:** If John reports an issue, manager sees:

```
STATUS_John: ISSUE          (tester's finding)
COMMENT_John: "Wrong word"  (tester's note)
│
▼ Manager adds:
STATUS_John: FIXED          (manager's resolution)
COMMENT_John: "Fixed in build 123"
```

---

<div style="page-break-after: always;"></div>

---

# Part 3: The OLD→NEW Update Process

## Understanding Transfer — The Key to Preserving Work

---

## When to Use Transfer

```
┌─────────────────────────────────────────────────────────────┐
│                 WHEN TO USE TRANSFER                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ USE TRANSFER when:                                       │
│     • Game data changed (new translations, fixed strings)    │
│     • Weekly refresh (Friday cycle)                          │
│     • Testers have existing work to preserve                 │
│                                                              │
│  ❌ DON'T USE TRANSFER when:                                 │
│     • Starting fresh (no existing work)                      │
│     • Just doing daily compilation                           │
│     • QAfolderOLD is empty                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Understanding the Three QA Folders

> 🚨 **CRITICAL**
> This is the #1 source of confusion. Read this section carefully!

### The Three Folders Explained

| Folder | Purpose | When Used |
|--------|---------|-----------|
| **QAfolder/** | CURRENT work | Always — this is your main working folder |
| **QAfolderOLD/** | BACKUP of previous work | Only during weekly refresh |
| **QAfolderNEW/** | Fresh datasheets (auto-created) | Only during Transfer |

---

### Visual: How They Work Together

```
NORMAL WEEK (Monday–Thursday):
═══════════════════════════════════════════════════════════════════════════

    Only QAfolder/ is used. Testers add their completed files here.

    ┌─────────────────────┐
    │     QAfolder/       │  ← All tester work goes here
    │  ├─ John_Quest/     │
    │  ├─ Mary_Item/      │
    │  └─ Chen_Knowledge/ │
    └─────────────────────┘


FRIDAY REFRESH:
═══════════════════════════════════════════════════════════════════════════

    Step 1: Move current work to backup
    ────────────────────────────────────────────────────

    QAfolder/              ──────────►    QAfolderOLD/
    (has work)              mv *         (backup)

    Result: QAfolder/ is now EMPTY


    Step 2: Generate creates fresh datasheets
    ────────────────────────────────────────────────────

    XML Sources  ──────────►  GeneratedDatasheets/
                  generate     (fresh files)


    Step 3: Transfer merges OLD + NEW
    ────────────────────────────────────────────────────

    QAfolderOLD/           QAfolderNEW/           QAfolder/
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │ STATUS: ISSUE│  +   │ Fresh data   │  =   │ STATUS: ISSUE│
    │ COMMENT: Bug │      │ STATUS: ___  │      │ COMMENT: Bug │
    │ SCREENSHOT:X │      │ COMMENT: ___ │      │ + New rows   │
    └──────────────┘      └──────────────┘      └──────────────┘
       (Old work)         (Auto-populated)         (Merged!)
```

---

<div style="page-break-after: always;"></div>

## Step-by-Step Transfer Process

---

### Before You Start

Make sure you have:
- [ ] Tester work in `QAfolder/` (to become OLD)
- [ ] Latest game XML files (for GENERATE)

---

### Step 1: Create QAfolderOLD

```bash
# Move all current work to OLD
mv QAfolder/* QAfolderOLD/
```

**Verify:** `ls QAfolderOLD/` shows your tester folders

```
QAfolderOLD/
├── John_Quest/
│   └── Quest_LQA_ENG.xlsx    ← Has STATUS, COMMENT data
├── Mary_Item/
│   └── Item_LQA_ENG.xlsx
└── Chen_Knowledge/
    └── Knowledge_LQA_ZHO.xlsx
```

---

### Step 2: Generate Fresh Datasheets

```bash
python main.py --generate all
```

**Verify:** `ls GeneratedDatasheets/` shows fresh files

---

### Step 3: Run Transfer

```bash
python main.py --transfer
```

**What Transfer Does:**

1. For each folder in `QAfolderOLD/`, finds matching folder structure
2. Copies fresh datasheets from `GeneratedDatasheets/` to `QAfolderNEW/`
3. Matches rows between OLD and NEW using STRINGID + Translation
4. Copies STATUS, COMMENT, SCREENSHOT from OLD to NEW
5. Outputs merged files to `QAfolder/`

---

### Step 4: Verify Merged Files

Open a merged file in `QAfolder/` and check:

| Check | Expected |
|-------|----------|
| Row count | May differ from OLD (new content!) |
| STATUS values | Preserved where rows matched |
| COMMENT text | Preserved where rows matched |
| SCREENSHOT refs | Preserved where rows matched |
| New rows | Have empty STATUS/COMMENT |

---

<div style="page-break-after: always;"></div>

## Transfer Matching Algorithm

Transfer uses a two-pass matching algorithm to preserve as much work as possible.

---

### For Standard Categories (Quest, Knowledge, etc.)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STANDARD MATCHING ALGORITHM                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   PASS 1: Exact Match (STRINGID + Translation)                          │
│   ─────────────────────────────────────────────                         │
│   OLD Row: STRINGID="12345" + Translation="Hello World"                 │
│   NEW Row: STRINGID="12345" + Translation="Hello World"                 │
│   Result: ✅ MATCH — copy STATUS, COMMENT, SCREENSHOT                   │
│                                                                          │
│   PASS 2: Fallback Match (Translation only)                             │
│   ─────────────────────────────────────────                             │
│   For rows that didn't match in Pass 1:                                 │
│   OLD Row: Translation="Hello World"                                    │
│   NEW Row: Translation="Hello World"                                    │
│   Result: ✅ MATCH — copy data (STRINGID may have changed)              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### For Item Category (Special Handling)

Items have additional matching because of duplicate item names:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ITEM MATCHING ALGORITHM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   PASS 1: Exact Match (ItemName + ItemDesc + STRINGID)                  │
│   ─────────────────────────────────────────────────────                 │
│   OLD: Name="Sword" + Desc="A sharp blade" + STRINGID="W001"            │
│   NEW: Name="Sword" + Desc="A sharp blade" + STRINGID="W001"            │
│   Result: ✅ MATCH                                                       │
│                                                                          │
│   PASS 2: Fallback Match (ItemName + ItemDesc)                          │
│   ─────────────────────────────────────────────────                     │
│   OLD: Name="Sword" + Desc="A sharp blade"                              │
│   NEW: Name="Sword" + Desc="A sharp blade"                              │
│   Result: ✅ MATCH (STRINGID may have changed)                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Duplicate Translation Handling (EXPORT-aware)

When multiple rows have the same translation, Transfer uses intelligent resolution:

```
SCENARIO: Two rows with identical translation

OLD File:
┌─────────────────────────────────────────────────────────────────┐
│ Row 1: "Hello" | STATUS: ISSUE   | COMMENT: "Bug A"            │
│ Row 2: "Hello" | STATUS: NO ISSUE | COMMENT: ""                │
└─────────────────────────────────────────────────────────────────┘

Transfer Resolution Priority:
1. EXPORT rows (in-game visible) > non-EXPORT rows
2. Rows with STATUS data > rows without
3. First occurrence wins for equal priority

Result: The most important work is preserved!
```

> 💡 **TIP**
> If you see a "Duplicate Translation Report" after transfer, review it to ensure important work wasn't lost.

---

<div style="page-break-after: always;"></div>

## Before/After Transfer Diagram

```
═══════════════════════════════════════════════════════════════════════════
BEFORE TRANSFER
═══════════════════════════════════════════════════════════════════════════

QAfolderOLD/John_Quest/Quest_LQA_ENG.xlsx:
┌─────────────────────────────────────────────────────────────────────────┐
│ STRINGID │ Translation    │ STATUS   │ COMMENT          │ SCREENSHOT   │
├──────────┼────────────────┼──────────┼──────────────────┼──────────────┤
│ Q001     │ Accept Quest   │ ISSUE    │ "Typo in text"   │ bug_001.png  │
│ Q002     │ Complete Quest │ NO ISSUE │ ""               │ ""           │
│ Q003     │ Old text       │ KOREAN   │ "Still Korean"   │ ""           │
└─────────────────────────────────────────────────────────────────────────┘

GeneratedDatasheets/ (NEW - from latest XML):
┌─────────────────────────────────────────────────────────────────────────┐
│ STRINGID │ Translation    │ STATUS   │ COMMENT          │ SCREENSHOT   │
├──────────┼────────────────┼──────────┼──────────────────┼──────────────┤
│ Q001     │ Accept Quest   │ ___      │ ___              │ ___          │
│ Q002     │ Complete Quest │ ___      │ ___              │ ___          │
│ Q004     │ NEW quest text │ ___      │ ___              │ ___          │  ← NEW row!
└─────────────────────────────────────────────────────────────────────────┘
                                                            (Q003 REMOVED)


═══════════════════════════════════════════════════════════════════════════
AFTER TRANSFER
═══════════════════════════════════════════════════════════════════════════

QAfolder/John_Quest/Quest_LQA_ENG.xlsx:
┌─────────────────────────────────────────────────────────────────────────┐
│ STRINGID │ Translation    │ STATUS   │ COMMENT          │ SCREENSHOT   │
├──────────┼────────────────┼──────────┼──────────────────┼──────────────┤
│ Q001     │ Accept Quest   │ ISSUE    │ "Typo in text"   │ bug_001.png  │  ← PRESERVED!
│ Q002     │ Complete Quest │ NO ISSUE │ ""               │ ""           │  ← PRESERVED!
│ Q004     │ NEW quest text │ ___      │ ___              │ ___          │  ← NEW (needs testing)
└─────────────────────────────────────────────────────────────────────────┘

RESULT:
 ✅ Q001: Work preserved (matched by STRINGID + Translation)
 ✅ Q002: Work preserved (matched)
 ❌ Q003: Lost (row no longer exists in game data)
 🆕 Q004: New row added (needs testing)
```

---

<div style="page-break-after: always;"></div>

## Troubleshooting Transfer Issues

---

### Issue: "No matching NEW folder"

**Error:** `No matching NEW folder for: John_Quest`

**Cause:** QAfolderNEW doesn't have a folder with that exact name.

**Solution:**
1. Check folder naming matches exactly (case-sensitive!)
2. Ensure GENERATE was run before TRANSFER
3. Verify the category still exists in game data

---

### Issue: Low Transfer Success Rate

**Symptom:** Transfer reports many unmatched rows.

**This is often NORMAL.** Common reasons:

| Reason | Explanation |
|--------|-------------|
| Content changed | Translations were updated — old text doesn't match |
| Rows removed | Strings were deleted from game data |
| STRINGID changed | Internal ID changed (fallback match should catch) |

> 💡 **TIP**
> Check the duplicate translation report if generated. It shows why some rows didn't match.

---

### Issue: Work Not Preserved

**Symptom:** STATUS/COMMENT empty after transfer for rows that had data.

**Debug steps:**

1. **Check OLD file:** Does it actually have STATUS data?
   ```
   Open QAfolderOLD/John_Quest/Quest_LQA_ENG.xlsx
   Verify STATUS column has values
   ```

2. **Check matching:** Does the translation match exactly?
   - Whitespace differences break matching
   - Case differences break matching
   - Special character differences break matching

3. **Check STRINGID:** Did it change?
   - If only STRINGID changed, Pass 2 fallback should catch it
   - If both changed, no match is possible

---

### Issue: Images Not Copied

**Symptom:** SCREENSHOT references exist but images missing.

**Solution:**
1. Check `Images/` folder in OLD location
2. Ensure filenames match exactly (including extension)
3. Avoid special characters in image filenames

---

<div style="page-break-after: always;"></div>

---

# Part 4: Detailed Reference

## The Four Functions in Depth

---

## Function 1: Generate Datasheets

> **Purpose:** Create Excel datasheets from game XML sources for QA testers

---

### What It Creates

```
Game XML Files                         Excel Datasheets
(StaticInfo, etc.)                     (Per Language Per Category)
─────────────────                      ───────────────────────────

questgroupinfo.xml     ──────────►     Quest_LQA_ENG.xlsx
knowledgeinfo.xml      ──────────►     Quest_LQA_FRE.xlsx
iteminfo.xml           ──────────►     Quest_LQA_ZHO.xlsx
characterinfo.xml      ──────────►     Item_LQA_ENG.xlsx
skillinfo.xml          ──────────►     Knowledge_LQA_JPN.xlsx
etc.                   ──────────►     etc.
```

---

### Generated Columns

| Column | Purpose | Generated From |
|--------|---------|----------------|
| Original | Korean source text | XML Source attribute |
| ENG | English translation | stringtable/loc/ENG/ |
| {Language} | Target language | stringtable/loc/{LANG}/ |
| StringKey | For /complete commands | XML StrKey attribute |
| Command | Cheat commands | Generated from factioninfo |
| STATUS | Issue status | Empty (tester fills) |
| COMMENT | Tester notes | Empty (tester fills) |
| STRINGID | Unique identifier | XML internal ID |
| SCREENSHOT | Image reference | Empty (tester fills) |

---

### Quest Command Structure

For Daily/Politics/Region quests, commands are auto-generated:

```
/complete mission Mission_A && Mission_B    ← Prerequisites first
/complete prevmission Mission_X             ← Progress command
/teleport 1234 567 89                       ← Teleport last
```

*Extracted automatically from factioninfo Condition + Branch Execute*

---

### Usage

```bash
# Generate specific categories
python main.py --generate quest knowledge item

# Generate ALL categories (all 9)
python main.py --generate all

# GUI: Check boxes and click [Generate Selected]
```

---

<div style="page-break-after: always;"></div>

## Function 2: Transfer QA Files

> **Purpose:** Preserve tester work when datasheets are updated

See **Part 3** for detailed Transfer documentation.

---

### Quick Reference

```bash
# Before transfer: Backup current work
mv QAfolder/* QAfolderOLD/

# Generate fresh datasheets
python main.py --generate all

# Run transfer
python main.py --transfer
```

---

## Function 3: Build Master Files

> **Purpose:** Compile individual QA files into centralized Master files

---

### What It Creates

```
QAfolder/                              Output
─────────────────                      ───────────────────────────

├── John_Quest/        ──────────►     Masterfolder_EN/
│   └── Quest_LQA_ENG.xlsx              └── Master_Quest.xlsx
├── Mary_Quest/        ──────────►         (John + Mary combined)
│   └── Quest_LQA_ENG.xlsx
│                                      Masterfolder_CN/
├── Chen_Quest/        ──────────►     └── Master_Quest.xlsx
│   └── Quest_LQA_ZHO.xlsx                 (Chen + Wei combined)
├── Wei_Quest/
│   └── Quest_LQA_ZHO.xlsx
│
└── (all folders)      ──────────►     LQA_Tester_ProgressTracker.xlsx
```

---

### Per-User Columns in Master Files

When files are merged, per-user columns are added:

| Column | Purpose |
|--------|---------|
| `STATUS_{Username}` | Manager's resolution status |
| `COMMENT_{Username}` | Manager's notes (includes metadata) |
| `SCREENSHOT_{Username}` | Manager's image references |

---

### Usage

```bash
python main.py --build

# GUI: Click [Build Master Files]
```

---

<div style="page-break-after: always;"></div>

## Function 4: Coverage Analysis

> **Purpose:** Calculate coverage and word counts for reporting

---

### Metrics Calculated

| Metric | Description |
|--------|-------------|
| **String Coverage** | % of language strings covered by datasheets |
| **Word Count** | Total words (EN) or characters (CN) per category |
| **Category Breakdown** | Coverage per category |

---

### Output

- **Terminal:** Summary report printed to console
- **Excel:** `Coverage_Report_YYYYMMDD_HHMMSS.xlsx`

---

### Usage

```bash
# Via GUI: Click [Run Coverage Analysis]
# Also runs automatically after generating datasheets
```

---

<div style="page-break-after: always;"></div>

## All 9 Categories Explained

---

### Category Overview

| # | Category | Source Files | Description |
|:-:|----------|--------------|-------------|
| 1 | **Quest** | scenario/, faction/, challenge/ | All quest types |
| 2 | **Knowledge** | knowledgeinfo/, knowledgegroupinfo/ | Knowledge entries |
| 3 | **Item** | iteminfo/, itemgroupinfo/ | Items with descriptions |
| 4 | **Region** | factiongroupinfo/ | Faction/Region data |
| 5 | **System** | *(Skill + Help combined)* | Combined category |
| 6 | **Character** | characterinfo_*.xml | NPC/Monster info |
| 7 | **Skill** | skillinfo_pc.xml | Player skills |
| 8 | **Help** | gameadviceinfo.xml | GameAdvice entries |
| 9 | **Gimmick** | gimmickinfo/ | Gimmick objects |

---

### Category Clustering

Some categories merge into others in the Master files:

```
Input Category           Output Master
──────────────           ─────────────

Skill    ───────┐
                ├─────►  Master_System.xlsx
Help     ───────┘

Gimmick  ──────────────►  Master_Item.xlsx
                          (merged with Item)
```

---

### Quest Tab Organization

Quest datasheets are organized by tabs:

```
Quest_LQA_ENG.xlsx
│
├── Main Quest           ← From scenario/ folder
├── Faction 1            ← OrderByString from factioninfo
├── Faction 2
├── ...
├── Region Quest         ← *_Request StrKey pattern
├── Daily                ← *_Daily + Group="daily"
├── Politics             ← *_Situation StrKey pattern
├── Challenge Quest      ← From challenge/ folder
├── Minigame Quest       ← From contents_minigame.xml
└── Others               ← Leftover factions
```

---

<div style="page-break-after: always;"></div>

## GUI Guide

---

### Launching the GUI

```bash
python main.py
# or explicitly
python main.py --gui
```

---

### Interface Overview

```
╔════════════════════════════════════════════════════════════════════════════╗
║                        QA Compiler Suite v2.0                               ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║  ┌─ 1. Generate Datasheets ───────────────────────────────────────────────┐ ║
║  │                                                                         │ ║
║  │   ☑ Quest      ☑ Knowledge   ☑ Item                                    │ ║
║  │   ☑ Region     ☑ System      ☑ Character                               │ ║
║  │   ☑ Skill      ☑ Help        ☑ Gimmick                                 │ ║
║  │                                                                         │ ║
║  │   [Select All]  [Deselect All]  [Generate Selected]                    │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                             ║
║  ┌─ 2. Transfer QA Files ─────────────────────────────────────────────────┐ ║
║  │   QAfolderOLD + QAfolderNEW → QAfolder                                 │ ║
║  │                                                                         │ ║
║  │                    [Transfer QA Files]                                  │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                             ║
║  ┌─ 3. Build Master Files ────────────────────────────────────────────────┐ ║
║  │   QAfolder → Masterfolder_EN / Masterfolder_CN                         │ ║
║  │                                                                         │ ║
║  │                    [Build Master Files]                                 │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                             ║
║  ┌─ 4. Coverage Analysis ─────────────────────────────────────────────────┐ ║
║  │   Calculate coverage + word counts                                      │ ║
║  │                                                                         │ ║
║  │                    [Run Coverage Analysis]                              │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                             ║
║  Status: Ready                                                              ║
║  [════════════════════════════════════════════════════════════════════════] ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### GUI Section Guide

| Section | Action | Output |
|---------|--------|--------|
| **1. Generate** | Check categories, click Generate | Files in GeneratedDatasheets/ |
| **2. Transfer** | Click Transfer | Merged files in QAfolder/ |
| **3. Build** | Click Build | Master files + Tracker |
| **4. Coverage** | Click Coverage | Report in console + Excel |

---

<div style="page-break-after: always;"></div>

## Tester Configuration

---

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

---

### Format Rules

| Rule | Description |
|------|-------------|
| Section headers | `ENG` or `ZHO-CN` only (no other values) |
| One name per line | Must match folder names exactly |
| Empty lines | Ignored |
| Case-sensitive | `John` ≠ `john` |
| Default | Unmapped testers → EN |

---

### Effect on Routing

| Tester | Mapping | Master Output |
|--------|---------|---------------|
| John | ENG | Masterfolder_EN/ |
| Mary | ENG | Masterfolder_EN/ |
| Chen | ZHO-CN | Masterfolder_CN/ |
| Unknown | (default) | Masterfolder_EN/ |

> ⚠️ **WARNING**
> If a tester name doesn't match exactly, they'll be routed to English by default!

---

<div style="page-break-after: always;"></div>

---

# Part 5: Troubleshooting

## Common Issues and Solutions

---

### ❌ "No valid QA folders found"

**Cause:** Folder naming doesn't follow the required format.

**Solution:**

```bash
# Check folder names
ls QAfolder/

# Correct format:
John_Quest/    ✅
Mary_Item/     ✅

# Wrong formats:
John Quest/    ❌ (space)
Mary-Item/     ❌ (hyphen)
John/          ❌ (no category)
quest/         ❌ (no tester name)
```

> 🚨 **CRITICAL**
> Format must be: `{TesterName}_{Category}` with underscore, exact case match!

---

### ❌ "Language folder not found"

**Cause:** Path in config.py doesn't exist or isn't accessible.

**Solution:**

1. Check Perforce workspace is synced
2. Verify path in `config.py`:
   ```python
   LANGUAGE_FOLDER = Path(r"F:\perforce\...\stringtable\loc")
   ```
3. Ensure network drive is connected
4. Test path exists: `dir F:\perforce\...\stringtable\loc`

---

### ❌ "No matching NEW folder for transfer"

**Cause:** QAfolderNEW doesn't have a folder with that exact name.

**Solution:**

```bash
# Ensure both exist with EXACT same name:
QAfolderOLD/John_Quest/   ✅
QAfolderNEW/John_Quest/   ✅ (must exist!)

# Check for typos or case differences:
QAfolderOLD/John_Quest/
QAfolderNEW/john_quest/   ❌ (case mismatch!)
```

---

### ❌ Low Transfer Success Rate

**Cause:** Content changed significantly between OLD and NEW.

**This is often NORMAL.** Reasons include:
- Translations were updated
- Strings were removed from game
- STRINGIDs changed

**What to do:**
1. Check the duplicate translation report (if generated)
2. Review unmatched rows — were they important?
3. If critical work lost, restore from QAfolderOLD manually

---

<div style="page-break-after: always;"></div>

### ❌ Images Not Appearing in Master

**Cause:** Hyperlinks broken or images not found.

**Solution:**

1. Check `Images/` folder exists in Master output
2. Verify filenames match SCREENSHOT column exactly
3. Avoid special characters in image filenames
4. Check file extensions match (`.png` vs `.PNG`)

---

### ❌ Tester Routed to Wrong Master

**Cause:** Tester name not in `languageTOtester_list.txt` or misspelled.

**Solution:**

```bash
# Check mapping file
cat languageTOtester_list.txt

# Ensure tester name matches EXACTLY:
ENG
John      ← Must match folder: John_Quest/
john      ← WRONG! Won't match John_Quest/
```

---

### ❌ Progress Tracker Empty

**Cause:** No valid QA folders found, or no STATUS data.

**Solution:**

1. Check `QAfolder/` has properly named folders
2. Check Excel files have STATUS column with data
3. Verify file format is `.xlsx` (not `.xls`)

---

### ❌ Build Takes Too Long

**Cause:** Large datasets or slow disk.

**Tips:**

- Process fewer categories at once
- Close other programs using Excel
- Use SSD if available
- Large images slow down the process

---

## Debug Mode

For detailed logging, redirect output to a file:

```bash
python main.py --build 2>&1 | tee build.log
```

Then review `build.log` for detailed error messages.

---

<div style="page-break-after: always;"></div>

---

# Appendix

---

## A. All Status Values

### Tester Status (STATUS column)

| Value | Meaning | When to Use |
|-------|---------|-------------|
| `ISSUE` | Translation issue found | Text is wrong, missing, or problematic |
| `NO ISSUE` | Checked, no issue | Text is correct |
| `BLOCKED` | Cannot test | Can't access content in-game |
| `KOREAN` | Korean text remaining | Untranslated text found |

### Manager Status (STATUS_{User} column)

| Value | Meaning | When to Use |
|-------|---------|-------------|
| `FIXED` | Issue resolved | Dev fixed the issue |
| `REPORTED` | Sent to development | Issue forwarded to dev team |
| `CHECKING` | Under review | Still investigating |
| `NON-ISSUE` | Not a real issue | False positive |

---

## B. CLI Command Reference

| Command | Short | Description |
|---------|:-----:|-------------|
| `--help` | `-h` | Show help message |
| `--version` | `-v` | Show version |
| `--list` | `-l` | List available categories |
| `--generate CATS` | `-g` | Generate datasheets for categories |
| `--transfer` | `-t` | Transfer OLD → NEW |
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

# Full pipeline
python main.py --all

# Multiple operations
python main.py --generate quest --build
```

---

<div style="page-break-after: always;"></div>

## C. Folder Naming Rules

### Format

```
{TesterName}_{Category}
```

### Valid Characters

| Allowed | Not Allowed |
|---------|-------------|
| Letters (A-Z, a-z) | Spaces |
| Numbers (0-9) | Hyphens |
| Underscore (between name/category only) | Special characters |

### Valid Category Names

```
Quest, Knowledge, Item, Region, System, Character, Skill, Help, Gimmick
```

### Examples

| Folder Name | Valid? | Reason |
|-------------|:------:|--------|
| `John_Quest` | ✅ | Correct format |
| `Mary_Item` | ✅ | Correct format |
| `Chen_Knowledge` | ✅ | Correct format |
| `John Quest` | ❌ | Space not allowed |
| `Mary-Item` | ❌ | Hyphen not allowed |
| `chen_knowledge` | ❌ | Case mismatch with tester list |
| `Quest` | ❌ | Missing tester name |
| `John` | ❌ | Missing category |

---

## D. File-to-Function Mapping

When updates are released, you may only need to replace specific files:

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
| Progress Tracker | `tracker/total.py`, `tracker/daily.py` |
| Configuration | `config.py` |
| GUI | `gui/app.py` |

---

## E. File Limits

| Limit | Value |
|-------|-------|
| Max rows per Excel sheet | 1,048,576 |
| Recommended images per folder | 1,000 |
| Progress tracker entries | Unlimited |

---

## F. Supported Languages

Standard codes: ENG, FRE, DEU, SPA, ITA, JPN, ZHO, KOR, POR, RUS, and more...

For tester routing, only `ENG` and `ZHO-CN` are supported in the mapping file.

---

<div align="center">

---

**QA Compiler Suite v2.0**

*User Guide Version 2.0 | January 2025*

*Questions? Check the troubleshooting section or contact your QA lead.*

---

</div>
