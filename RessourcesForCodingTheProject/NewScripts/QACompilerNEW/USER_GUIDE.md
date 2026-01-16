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
| [Getting Started](#-getting-started) | Installation and first launch |
| [Main Interface](#-main-interface) | Understanding the GUI |
| [Generate Datasheets](#-1-generate-datasheets) | Create LQA worksheets from game data |
| [Transfer QA Files](#-2-transfer-qa-files) | Merge tester work into QAfolder |
| [Build Master Files](#-3-build-master-files) | Compile final master documents |
| [Coverage Analysis](#-4-coverage-analysis) | Check translation coverage |
| [System Localizer](#-5-system-localizer) | Create localized System sheets |
| [Folder Structure](#-folder-structure) | Where files go |
| [Troubleshooting](#-troubleshooting) | Common issues and solutions |

---

## 🚀 Getting Started

### Installation

1. **Download** the latest `QACompiler.exe` package
2. **Extract** to your preferred location (e.g., `C:\Tools\QACompiler\`)
3. **Double-click** `QACompiler.exe` to launch

> 💡 **Tip:** Keep the folder structure intact - don't move files around!

### First Launch Checklist

Before using the tool, verify these paths exist on your system:

| Path | Purpose |
|------|---------|
| `F:\perforce\cd\mainline\resource\GameData\StaticInfo\` | Game XML data |
| `F:\perforce\cd\mainline\resource\GameData\stringtable\loc\` | Language files |

> ⚠️ **Different Drive?** If your Perforce is on D: or E: drive, see [Building for Different Drives](#building-for-different-drives).

---

## 🖥️ Main Interface

When you launch QA Compiler Suite, you'll see this interface:

```
┌────────────────────────────────────────────────────────────┐
│              QA Compiler Suite v2.0                        │
├────────────────────────────────────────────────────────────┤
│  📋 1. Generate Datasheets                                 │
│     ☑ Quest    ☑ Knowledge   ☑ Item                        │
│     ☑ Region   ☑ System      ☑ Character                   │
│     ☑ Skill    ☑ Help        ☑ Gimmick                     │
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
│  Status: Ready                                             │
│  [════════════════════════════════════════]                │
└────────────────────────────────────────────────────────────┘
```

---

## 📋 1. Generate Datasheets

**Purpose:** Create fresh LQA worksheets from game XML data for testers to work on.

### When to Use
- Starting a new QA cycle
- Game data has been updated
- Need worksheets for specific categories

### How to Use

| Step | Action |
|------|--------|
| 1 | **Select categories** by checking the boxes |
| 2 | Click **[Generate Selected]** |
| 3 | Wait for progress bar to complete |
| 4 | Find files in `GeneratedDatasheets/` folder |

### Category Guide

| Category | Contains | Output Folder |
|----------|----------|---------------|
| **Quest** | Main story, faction, daily quests | `QuestData_Map_All/` |
| **Knowledge** | Encyclopedia entries | `Knowledge_LQA_All/` |
| **Item** | Items, equipment, consumables | `ItemData_Map_All/` |
| **Region** | Areas, locations, POIs | `Region_LQA_v3/` |
| **System** | UI text, menus | *(via Skill+Help)* |
| **Character** | NPCs, monsters | `Character_LQA_All/` |
| **Skill** | Player abilities | `Skill_LQA_All/` |
| **Help** | Tutorial, tips | `GameAdvice_LQA_All/` |
| **Gimmick** | Interactive objects | `Gimmick_LQA_Output/` |

### Output Excel Structure

Each generated file contains these columns:

| Column | Description | Editable? |
|--------|-------------|-----------|
| **Original (KR)** | Korean source text | ❌ No |
| **English (ENG)** | English translation | ❌ No |
| **Translation** | Target language text | ❌ No |
| **STATUS** | Issue status dropdown | ✅ Yes |
| **COMMENT** | Tester notes | ✅ Yes |
| **STRINGID** | Unique identifier | ❌ No |
| **SCREENSHOT** | Screenshot reference | ✅ Yes |

### STATUS Options

| Status | Meaning | Color |
|--------|---------|-------|
| `ISSUE` | Problem found - needs fix | 🔴 Red |
| `NO ISSUE` | Checked, looks good | 🟢 Green |
| `BLOCKED` | Cannot test | 🟡 Yellow |
| `KOREAN` | Still in Korean | 🟠 Orange |

> 💡 **Tip:** Use `Select All` then uncheck what you don't need - faster than selecting one by one!

---

## 📁 2. Transfer QA Files

**Purpose:** Merge completed tester work from OLD and NEW folders into the main QAfolder.

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

### When to Use
- Testers have submitted their completed files
- Need to combine work from multiple rounds

### How to Use

| Step | Action |
|------|--------|
| 1 | Place OLD tester files in `QAfolderOLD/` |
| 2 | Place NEW tester files in `QAfolderNEW/` |
| 3 | Click **[Transfer QA Files]** |
| 4 | Combined files appear in `QAfolder/` |

> ⚠️ **Important:** Files in QAfolder will be overwritten! Backup if needed.

---

## 🔨 3. Build Master Files

**Purpose:** Compile all QA files into final master documents with progress tracking.

### The Flow

```
┌─────────────────┐
│    QAfolder     │
│  (All QA work)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           BUILD PROCESS                  │
│  • Merge all tester sheets              │
│  • Calculate progress                    │
│  • Generate DAILY/TOTAL trackers        │
│  • Hide completed rows (NON ISSUE)      │
│  • Auto-fit columns                      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Masterfolder_EN │     │ Masterfolder_CN │
│  (English)      │     │  (Chinese)      │
└─────────────────┘     └─────────────────┘
```

### Output Contents

Each Master folder contains:

| File | Description |
|------|-------------|
| `Master_Quest.xlsx` | All quest QA combined |
| `Master_Knowledge.xlsx` | All knowledge QA combined |
| `Master_Item.xlsx` | All item QA combined |
| `Master_Region.xlsx` | All region QA combined |
| `Master_System.xlsx` | Combined Skill + Help |
| `Master_Character.xlsx` | All character QA combined |
| `Master_Gimmick.xlsx` | All gimmick QA combined |
| `_TRACKER.xlsx` | Progress tracking sheets |

### Progress Tracker Sheets

The `_TRACKER.xlsx` contains:

| Sheet | Shows |
|-------|-------|
| **DAILY** | Day-by-day progress per tester |
| **TOTAL** | Overall statistics and rankings |
| **_DAILY_DATA** | Raw data (hidden) |

### Automatic Row Hiding

Rows marked as these statuses are **automatically hidden** in master files:

| Status | Hidden? |
|--------|---------|
| `FIXED` | ✅ Yes |
| `NON ISSUE` | ✅ Yes |
| `NON-ISSUE` | ✅ Yes |
| `ISSUE` | ❌ No (needs attention) |
| `BLOCKED` | ❌ No (needs attention) |

> 💡 **Tip:** This helps managers focus on remaining issues!

---

## 📊 4. Coverage Analysis

**Purpose:** Calculate how much of the game's text is covered by your datasheets.

### When to Use
- After generating datasheets
- To verify translation coverage
- For reporting to stakeholders

### How to Use

| Step | Action |
|------|--------|
| 1 | Generate datasheets first (Section 1) |
| 2 | Click **[Run Coverage Analysis]** |
| 3 | View summary popup |
| 4 | Check `GeneratedDatasheets/` for detailed Excel report |

### Output Report

Creates `Coverage_Report_YYYYMMDD_HHMMSS.xlsx` with:

| Sheet | Contents |
|-------|----------|
| **Coverage Report** | Strings covered per category |
| **Word Count** | Korean + Translation word counts |

### Understanding Coverage

```
Coverage = (Strings in Datasheets / Total Strings in Game) × 100%

Example:
  Quest:     12,500 / 15,000 = 83.3%
  Knowledge:  8,200 /  8,500 = 96.5%
  Item:       5,100 /  6,000 = 85.0%
  ─────────────────────────────────
  Total:     25,800 / 29,500 = 87.5%
```

---

## 🌐 5. System Localizer

**Purpose:** Create localized versions of System datasheets for ALL languages automatically.

### When to Use
- You have a manually-created System Excel file
- Need to generate versions for all languages
- System UI text needs QA across languages

### How to Use

| Step | Action |
|------|--------|
| 1 | Click **[Localize System Sheet]** |
| 2 | Select your System Excel file |
| 3 | Wait for processing |
| 4 | Find output in `System_LQA_All/` folder |

### Output Structure

```
System_LQA_All/
├── System_ENG.xlsx    (English)
├── System_DEU.xlsx    (German)
├── System_FRA.xlsx    (French)
├── System_JPN.xlsx    (Japanese)
├── System_CHT.xlsx    (Chinese Traditional)
└── ... (all supported languages)
```

### How Matching Works

The localizer uses a **2-step matching process**:

```
Step 1: StringID Match
  StringID → Korean → Target Language
  (Most accurate)

Step 2: Text Match (Fallback)
  English Text → Korean → Target Language
  (When no StringID available)
```

---

## 📂 Folder Structure

### Application Folders

```
QACompiler/
├── QACompiler.exe           ← Main application
│
├── QAfolderOLD/             ← Put OLD tester files here
├── QAfolderNEW/             ← Put NEW tester files here
├── QAfolder/                ← Combined files (auto-generated)
│
├── GeneratedDatasheets/     ← Output from "Generate Datasheets"
│   ├── QuestData_Map_All/
│   ├── Knowledge_LQA_All/
│   ├── ItemData_Map_All/
│   └── ...
│
├── Masterfolder_EN/         ← Output from "Build Master Files"
│   ├── Master_Quest.xlsx
│   ├── Master_Knowledge.xlsx
│   ├── _TRACKER.xlsx
│   └── Images/
│
└── Masterfolder_CN/         ← Chinese master output
    └── ...
```

### File Naming Convention

| Pattern | Meaning |
|---------|---------|
| `Quest_LQA_ENG.xlsx` | Quest datasheet, English |
| `Item_LQA_DEU.xlsx` | Item datasheet, German |
| `Master_Quest.xlsx` | Combined quest master |
| `_TRACKER.xlsx` | Progress tracking |

---

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><b>❌ "Generator modules not yet implemented"</b></summary>

**Cause:** Generator files are missing or import failed.

**Solution:**
1. Verify all files are present in the installation
2. Check the `generators/` folder exists
3. Re-extract from the original package

</details>

<details>
<summary><b>❌ "No datasheets found in GeneratedDatasheets"</b></summary>

**Cause:** Coverage analysis needs datasheets first.

**Solution:**
1. Run "Generate Datasheets" first (Section 1)
2. Verify files exist in `GeneratedDatasheets/` folder
3. Then run Coverage Analysis

</details>

<details>
<summary><b>❌ Path errors mentioning F: drive</b></summary>

**Cause:** Your Perforce is on a different drive.

**Solution:**
See [Building for Different Drives](#building-for-different-drives) below.

</details>

<details>
<summary><b>❌ Excel file is corrupted or won't open</b></summary>

**Cause:** Process was interrupted during write.

**Solution:**
1. Delete the corrupted file
2. Run the operation again
3. Don't close the app while progress bar is active

</details>

<details>
<summary><b>❌ STATUS dropdown not appearing</b></summary>

**Cause:** Data validation may not have applied.

**Solution:**
1. Click on the STATUS cell
2. Look for small dropdown arrow
3. If missing, the file may need regeneration

</details>

---

## 🔨 Building for Different Drives

If your Perforce is on **D:** or **E:** drive instead of **F:**:

### Option 1: Use Build Script (Recommended)

1. Run `build_exe.bat`
2. When prompted, enter your drive letter:
   ```
   Enter drive letter (F/D/E/etc.) [F]: D
   ```
3. The executable will be built with correct paths

### Option 2: Manual Path Update

Edit `config.py` and change all paths:
```python
# Change FROM:
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\...")

# Change TO:
RESOURCE_FOLDER = Path(r"D:\perforce\cd\mainline\...")
```

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
