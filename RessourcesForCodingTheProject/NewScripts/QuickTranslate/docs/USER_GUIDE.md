# QuickTranslate User Guide

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ██████╗ ██╗   ██╗██╗ ██████╗██╗  ██╗████████╗██████╗  █████╗ ███╗   ██╗║
║  ██╔═══██╗██║   ██║██║██╔════╝██║ ██╔╝╚══██╔══╝██╔══██╗██╔══██╗████╗  ██║║
║  ██║   ██║██║   ██║██║██║     █████╔╝    ██║   ██████╔╝███████║██╔██╗ ██║║
║  ██║▄▄ ██║██║   ██║██║██║     ██╔═██╗    ██║   ██╔══██╗██╔══██║██║╚██╗██║║
║  ╚██████╔╝╚██████╔╝██║╚██████╗██║  ██╗   ██║   ██║  ██║██║  ██║██║ ╚████║║
║   ╚══▀▀═╝  ╚═════╝ ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝║
║                                                                           ║
║                    LOOKUP & TRANSFER - TWO TOOLS IN ONE                   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

**Version 4.0.0** | February 2026 | LocaNext Project

---

## 🎯 What Can QuickTranslate Do?

<div align="center">

| Feature | What It Does | Speed |
|---------|--------------|-------|
| ✅ **LOOKUP** | Find translations across 17 languages | ⚡ Instant |
| 📊 **TRANSFER** | Apply corrections to XML files | ⚡ Seconds |
| 🔍 **StringID Lookup** | Get all translations for any ID | ⚡ Instant |
| 🔄 **Reverse Lookup** | Find StringID from text | ⚡ Fast |
| 📝 **Find Missing** | Identify untranslated strings | ⚡ Fast-Slow* |
| ⚠️ **4 Match Types** | Flexible matching strategies | Various |

*\*Depends on match mode (Strict = instant, Fuzzy = minutes)*

</div>

---

## 🚀 Quick Navigation for Newbies

```
┌─────────────────────────────────────────────────────────────────────┐
│  NEW USER? START HERE                                               │
├─────────────────────────────────────────────────────────────────────┤
│  📖 Section 1: Introduction ────────────► What is QuickTranslate?   │
│  💾 Section 2: Installation ────────────► Get it running            │
│  🎓 Section 3: Quick Start ─────────────► First 5 minutes           │
│  🧠 Section 4: Core Concepts ───────────► Key terminology           │
│                                                                     │
│  READY TO USE? GO HERE                                              │
├─────────────────────────────────────────────────────────────────────┤
│  🔍 Section 5: LOOKUP Features ─────────► Find translations         │
│  📝 Section 6: TRANSFER Features ───────► Apply corrections         │
│  🎯 Section 7: Find Missing ────────────► Identify gaps             │
│  ⚙️  Section 8: Match Types ────────────► Choose strategy           │
│                                                                     │
│  NEED HELP? CHECK HERE                                              │
├─────────────────────────────────────────────────────────────────────┤
│  🔧 Section 11: Troubleshooting ────────► Fix problems              │
│  📚 Section 12: Reference ──────────────► All details               │
│  📋 Section 13: Quick Reference Card ───► One-page cheat sheet      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📖 Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Core Concepts](#4-core-concepts)
5. [LOOKUP Features](#5-lookup-features)
6. [TRANSFER Features](#6-transfer-features)
7. [Find Missing Translations](#7-find-missing-translations)
8. [Match Types](#8-match-types)
9. [Workflows](#9-workflows)
10. [Output Files](#10-output-files)
11. [Troubleshooting](#11-troubleshooting)
12. [Reference](#12-reference)
13. [Quick Reference Card](#13-quick-reference-card)
14. [Appendix](#14-appendix)

---

# 1. Introduction

## 1.1 What is QuickTranslate?

**QuickTranslate** is a dual-purpose desktop application for localization teams:

```
┌───────────────────────────────────────────────────────────────────┐
│                     TWO CORE FUNCTIONS                            │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🔍 LOOKUP (Generate Button)                                     │
│  ────────────────────────────────────────────────────────────    │
│  ✅ Find translations of Korean text                             │
│  ✅ Search across 17 languages                                   │
│  ✅ Look up any StringID                                         │
│  ✅ Reverse lookup: text → StringID                              │
│  ✅ Export results to Excel                                      │
│  ✅ 100% SAFE - Read-only operation                              │
│                                                                   │
│  📝 TRANSFER (TRANSFER Button)                                   │
│  ────────────────────────────────────────────────────────────    │
│  ✅ Apply corrections to XML files                               │
│  ✅ Batch update multiple languages                              │
│  ✅ Strict matching for safety                                   │
│  ✅ Detailed success/failure reports                             │
│  ⚠️  CAUTION - Modifies target files!                            │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Two Buttons, Two Workflows

```
┌─────────────────────────────────────────────────────────────────────┐
│                      QuickTranslate GUI                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [  GENERATE  ]                       [  TRANSFER  ]                │
│        │                                     │                      │
│        ↓                                     ↓                      │
│  Read source                           Read source                  │
│        ↓                                     ↓                      │
│  Find matches                          Match corrections            │
│        ↓                                     ↓                      │
│  Export to Excel                       WRITE to target XMLs         │
│        ↓                                     ↓                      │
│  📊 OUTPUT: Excel file              📝 OUTPUT: Modified XML files   │
│  ✅ Safe (read-only)                 ⚠️  Careful (writes files!)    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** If you're unsure which to use, start with **LOOKUP (Generate)**. It's completely safe and helps you understand your data before making changes with TRANSFER.

---

## 1.2 Who Should Use QuickTranslate?

| Role | LOOKUP Use Case | TRANSFER Use Case |
|------|-----------------|-------------------|
| **🎯 Localization Coordinators** | Find existing translations quickly | Apply batch corrections efficiently |
| **✅ QA Testers** | Verify translation consistency | Fix verified issues in bulk |
| **📝 Translators** | Look up reference translations | Submit corrections for review |
| **💻 Developers** | Find StringIDs from in-game text | Update localization files directly |
| **📊 Project Managers** | Analyze translation coverage | Track correction progress |

---

## 1.3 Key Benefits

```
┌────────────────────────────────────────────────────────────────────┐
│  WHY QUICKTRANSLATE?                                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ⚡ SPEED        Process hundreds of strings in seconds            │
│  🎯 ACCURACY    Multiple matching strategies for precision         │
│  🌍 COMPLETE    Access all 17 languages at once                    │
│  🔀 FLEXIBLE    Excel AND XML input/output                         │
│  ✅ SAFE        Confirmation dialogs + detailed reports            │
│  📊 SMART       4 match types for different scenarios              │
│  🔍 POWERFUL    Fuzzy matching with Korean semantic search         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Feature Comparison

| Feature | LOOKUP | TRANSFER |
|---------|:------:|:--------:|
| **Speed** | ⚡⚡⚡ Instant | ⚡⚡ Seconds |
| **Accuracy** | 🎯 Multiple strategies | 🎯 Strict + StringID-only |
| **Languages** | 🌍 All 17 | 🌍 All 17 |
| **Safety** | ✅ Read-only | ⚠️ Confirmation required |
| **Undo** | N/A | Perforce revert |
| **Output** | 📊 Excel | 📝 Modified XML |

---

# 2. Installation

## 2.1 System Requirements

```
┌────────────────────────────────────────────────────────────────┐
│  MINIMUM REQUIREMENTS                                          │
├────────────────────────────────────────────────────────────────┤
│  🖥️  OS:        Windows 10 / Windows 11                        │
│  💾 Disk:      500 MB free space                               │
│  🔐 Access:    Perforce sync to stringtable folders            │
│  📁 Drive:     F: drive mapped (or custom path)                │
│  🐍 Python:    3.11+ (portable version only)                   │
└────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** The installer version includes everything you need. No Python installation required!

---

## 2.2 Installation Methods

### 2.2.1 Setup Installer (✅ Recommended for Most Users)

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP-BY-STEP INSTALLATION                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1:  Download QuickTranslate_vX.X.X_Setup.exe             │
│           ↓                                                     │
│  Step 2:  Run the installer (double-click)                     │
│           ↓                                                     │
│  Step 3:  Select installation drive (C:, D:, F:, etc.)         │
│           ↓                                                     │
│  Step 4:  Click [Install]                                      │
│           ↓                                                     │
│  Step 5:  ✅ Done! Application launches automatically           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **🔥 IMPORTANT:** The installer creates a Start Menu shortcut and desktop icon. Find it under **QuickTranslate** in your Start Menu.

---

### 2.2.2 Portable Version (For Advanced Users)

```
┌─────────────────────────────────────────────────────────────────┐
│  PORTABLE INSTALLATION                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1:  Download QuickTranslate_vX.X.X_Portable.zip          │
│           ↓                                                     │
│  Step 2:  Extract to any folder (e.g., D:\Tools\)              │
│           ↓                                                     │
│  Step 3:  Run QuickTranslate.exe                               │
│           ↓                                                     │
│  Step 4:  ✅ Ready to use!                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** Portable version is great for USB drives or network shares. No installation needed!

---

## 2.3 First-Time Configuration

On first launch, QuickTranslate creates `settings.json` with default paths:

```json
{
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__"
}
```

### Changing Default Paths

```
┌─────────────────────────────────────────────────────────────────┐
│  HOW TO UPDATE PATHS                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1:  Close QuickTranslate                                 │
│           ↓                                                     │
│  Step 2:  Open settings.json in text editor                    │
│           (Located in application folder)                      │
│           ↓                                                     │
│  Step 3:  Update paths to match your Perforce workspace        │
│           ↓                                                     │
│  Step 4:  Save and restart QuickTranslate                      │
│           ↓                                                     │
│  Step 5:  ✅ New paths applied!                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **⚠️ WARNING:** Use double backslashes (`\\`) in JSON paths! Single backslash will cause errors.

**Example Custom Path:**
```json
{
  "loc_folder": "D:\\MyProject\\loc",
  "export_folder": "D:\\MyProject\\export__"
}
```

---

## 2.4 Folder Structure After Installation

```
QuickTranslate/
├── QuickTranslate.exe          ← Main application
├── settings.json               ← Configuration file
├── Source/                     ← 📁 Default source folder (auto-created)
│   └── (place your files here)
├── Output/                     ← 📊 Results go here (auto-created)
├── Failed Reports/             ← ⚠️ Failure reports (auto-created on failures)
└── ToSubmit/                   ← 📝 Optional corrections staging
```

> **💡 TIP:** The `Source/` folder is pre-populated in the GUI for easy file drop. Just put your files there and click Generate or TRANSFER!

---

# 3. Quick Start

## 3.1 Your First LOOKUP (Translation Search)

**Goal:** Find translations for Korean strings

### Visual Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────→│   Place in  │────→│  Configure  │────→│  Generate   │
│   Excel     │     │   Source/   │     │   Settings  │     │  & Review   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Step 1: Prepare Input Excel

Create `input.xlsx` with Korean text in Column A:

| Column A (Korean Text) |
|------------------------|
| 안녕하세요 |
| 감사합니다 |
| 시작하기 |

> **💡 TIP:** You can also use Column A header like "Korean" or "KOR" - QuickTranslate auto-detects!

---

### Step 2: Place File in Source Folder

```
QuickTranslate/
└── Source/
    └── input.xlsx    ← Place your file here
```

> **💡 TIP:** The Source path is pre-populated in the GUI. Just drop files and go!

---

### Step 3: Configure & Generate

```
┌─────────────────────────────────────────────────────────────────┐
│  QuickTranslate GUI                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Match Type:  ( ) Substring Match (Original)    ← Select this  │
│               ( ) StringID-Only (SCRIPT)                        │
│               ( ) StringID + StrOrigin (STRICT)                 │
│               ( ) StrOrigin Only                                │
│                                                                 │
│  Source: [Source/                    ] [Browse]                 │
│                                                                 │
│  [ Generate ]  ← Click here                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 4: View Results

**Output:** `Output/QuickTranslate_YYYYMMDD_HHMMSS.xlsx`

**Before (Input):**
| Korean |
|--------|
| 안녕하세요 |

**After (Output):**
| KOR | ENG | FRE | GER | SPA | ... |
|-----|-----|-----|-----|-----|-----|
| 안녕하세요 | Hello | Bonjour | Hallo | Hola | ... |

> **✨ MAGIC:** One Korean string → 17 language translations instantly!

---

## 3.2 Your First TRANSFER (Apply Corrections)

**Goal:** Apply corrections from Excel to LOC XML files

> **⚠️ WARNING:** TRANSFER modifies target files! Always back up or use Perforce!

### Visual Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────→│   Place in  │────→│  Configure  │────→│  TRANSFER   │
│ Corrections │     │   Source/   │     │   & Select  │     │  & Verify   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Step 1: Prepare Corrections Excel

Create `corrections.xlsx` with three columns:

| StringID | StrOrigin | Correction |
|----------|-----------|------------|
| UI_001 | 확인 버튼 | OK Button (fixed) |
| UI_002 | 취소 버튼 | Cancel Button (fixed) |

> **💡 TIP:** Column order doesn't matter - QuickTranslate auto-detects column names (case-insensitive)!

**Accepted column names:**
- **StringID:** StringID, StringId, string_id, STRINGID
- **StrOrigin:** StrOrigin, Str_Origin, str_origin, STRORIGIN
- **Correction:** Correction, correction, Str, str

---

### Step 2: Place File & Configure

```
QuickTranslate/
└── Source/
    └── corrections.xlsx    ← Place here
```

```
┌─────────────────────────────────────────────────────────────────┐
│  QuickTranslate GUI                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Match Type:  ( ) Substring Match (Original)                   │
│               ( ) StringID-Only (SCRIPT)                        │
│               (●) StringID + StrOrigin (STRICT)    ← Select    │
│               ( ) StrOrigin Only                                │
│                                                                 │
│  Source: [Source/                    ] [Browse]                 │
│  Target: [F:\...\loc                 ] [Browse]                 │
│                                                                 │
│  Transfer Scope:  (●) ALL    ( ) Untranslated only             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** Start with **STRICT mode** - it's the safest! Requires both StringID AND StrOrigin to match.

---

### Step 3: Transfer & Confirm

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 3.1: Click [TRANSFER]                                     │
│            ↓                                                     │
│  Step 3.2: Review transfer plan in terminal/log                 │
│            ↓                                                     │
│  Step 3.3: Confirm in popup dialog                              │
│            ↓                                                     │
│  Step 3.4: Watch progress in log                                │
│            ↓                                                     │
│  Step 3.5: ✅ Review transfer report                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Transfer Report Example:**
```
═══════════════════════════════════════════
     TRANSFER REPORT
═══════════════════════════════════════════
● languagedata_eng.xml: 2 updated
● languagedata_fre.xml: 2 updated

Summary:
  Matched: 2
  Updated: 4 (2 files × 2 languages)
  Not Found: 0
═══════════════════════════════════════════
```

> **✅ SUCCESS:** Your corrections are now in the target XML files!

---

### Step 4: Verify Changes

Check the modified files in your LOC folder:

**Before TRANSFER:**
```xml
<LocStr StringId="UI_001" StrOrigin="확인 버튼" Str="OK Button" />
```

**After TRANSFER:**
```xml
<LocStr StringId="UI_001" StrOrigin="확인 버튼" Str="OK Button (fixed)" />
```

> **💡 TIP:** Use Perforce diff to see exactly what changed!

---

## 3.3 Quick StringID Lookup

**Goal:** Find all translations for a specific StringID

### Visual Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Enter     │────→│   Click     │────→│   Review    │
│  StringID   │     │   Lookup    │     │   Excel     │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│  Quick Actions: StringID Lookup                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  StringID: [UI_MainMenu_Title_001      ]  [Lookup]             │
│                                                                 │
│  Step 1: Type or paste StringID                                │
│  Step 2: Click [Lookup]                                        │
│  Step 3: Excel opens with all 17 translations                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Output:** `Output/StringID_UI_MainMenu_Title_001_YYYYMMDD_HHMMSS.xlsx`

| StringID | ENG | FRE | GER | SPA | ... |
|----------|-----|-----|-----|-----|-----|
| UI_MainMenu_Title_001 | Main Menu | Menu Principal | Hauptmenü | Menú Principal | ... |

> **⚡ SPEED:** Instant lookup across all languages!

---

## 3.4 Reverse Lookup

**Goal:** Find StringID from English (or any language) text

### Visual Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────→│   Browse    │────→│  Click      │────→│   Review    │
│  Text File  │     │   to File   │     │  Find All   │     │   Excel     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Step 1: Create Text File

Create `search.txt` with one string per line:

```
Start Game
Options
Exit
```

> **💡 TIP:** Works with ANY language, not just English! QuickTranslate auto-detects the language.

---

### Step 2: Browse & Search

```
┌─────────────────────────────────────────────────────────────────┐
│  Quick Actions: Reverse Lookup                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Reverse: [                          ]  [Browse]  [Find All]   │
│                                                                 │
│  Step 1: Click [Browse]                                        │
│  Step 2: Select your text file                                 │
│  Step 3: Click [Find All]                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 3: Review Output

**Output:** `Output/ReverseLookup_YYYYMMDD_HHMMSS.xlsx`

| Input | KOR | ENG | FRE | GER |
|-------|-----|-----|-----|-----|
| Start Game | 게임 시작 | Start Game | Démarrer le jeu | Spiel starten |
| Options | 옵션 | Options | Options | Optionen |
| Exit | 종료 | Exit | Quitter | Beenden |

> **✨ MAGIC:** Text → StringID → All translations!

---

## 3.5 Find Missing Translations

**Goal:** Find Korean strings in TARGET that are MISSING from SOURCE

> **💡 NEW IN v3.7.0:** 4 match modes, fuzzy matching, category clustering, and Close folder output!

### Visual Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Select    │────→│   Click     │────→│   Choose    │────→│   Review    │
│Source/Target│     │Find Missing │     │  Parameters │     │   Reports   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Step 1: Set Paths

```
Source: Reference/corrections folder (keys you expect)
Target: LOC folder with languagedata_*.xml files
```

---

### Step 2: Click Find Missing

```
┌─────────────────────────────────────────────────────────────────┐
│  Quick Actions                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Find Missing Translations]  ← Click here                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

A parameter popup appears:

```
┌─────────────────────────────────────────────────────────────────┐
│  Find Missing Translations - Parameters                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Match Type:                                                    │
│    (●) StringID + KR (Strict)       ← Fastest, recommended     │
│    ( ) StringID + KR (Fuzzy)        ← For text rewording       │
│    ( ) KR only (Strict)             ← Ignore StringID changes  │
│    ( ) KR only (Fuzzy)              ← Maximum coverage (slow)  │
│                                                                 │
│  Fuzzy Threshold: [====|====] 0.85                              │
│  (only enabled when Fuzzy is selected)                          │
│                                                                 │
│  [  Run  ]                          [  Cancel  ]                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** Start with **StringID + KR (Strict)** - it's instant and catches 95% of cases!

---

### Step 3: Select Output & Watch Progress

```
┌─────────────────────────────────────────────────────────────────┐
│  PROGRESS TRACKING                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Step 1] EXPORT indexes built: 45,293 categories              │
│  [Step 2] SOURCE keys collected: 147,293                       │
│  [Step 3] TARGET scan: 14 languages, 312,456 Korean entries    │
│  [Step 4] Matching per language...                             │
│    [1/14] ENG: 2,456 MISSING                                   │
│    [2/14] FRE: 2,890 MISSING                                   │
│    ...                                                          │
│  [Step 5] ✅ Complete! Reports generated                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 4: Review Output

**Two types of output:**

```
Output/
├── MISSING_ENG_20260206_120000.xlsx    ← Excel report (category-clustered)
├── MISSING_FRE_20260206_120000.xlsx
├── MISSING_GER_20260206_120000.xlsx
├── ...
├── Close_ENG/                          ← EXPORT-mirrored XML structure
│   ├── Dialog/
│   │   ├── AIDialog/
│   │   │   └── npc_greetings.loc.xml
│   │   └── QuestDialog/
│   │       └── quest_chapter1.loc.xml
│   └── UI/
│       └── menu_strings.loc.xml
├── Close_FRE/
└── ...
```

**Excel Report Columns:**

| Column | Content | Example |
|--------|---------|---------|
| **StrOrigin** | Korean source text | 확인 버튼을 누르세요 |
| **Translation** | Current (untranslated) | 확인 버튼을 누르세요 |
| **StringID** | String identifier | UI_Button_Confirm_001 |
| **Category** | EXPORT-based category | UI |

> **💡 TIP:** Close folders can be used directly as TRANSFER source for the next correction batch!

---

# 4. Core Concepts

## 4.1 The Three Key Fields

Every localized string has three essential components:

```
┌────────────────────────────────────────────────────────────────┐
│  THE ANATOMY OF A LOCALIZED STRING                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  <LocStr                                                       │
│      StringId="UI_Button_OK"          ← 🔑 Unique ID          │
│      StrOrigin="확인"                 ← 📝 Korean source       │
│      Str="OK"                         ← 🌍 Translation         │
│  />                                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 🔑 StringID - The Unique Identifier

**What it is:** A unique code that identifies each localized string

**Examples:**
```
UI_MainMenu_Title_001
Quest_Chapter1_Dialog_042
Item_Weapon_Sword_Name
Character_NPC_Greeting_Hello
```

**Rules:**
- Must be unique across the entire project
- Case-sensitive
- Usually follows naming conventions

> **💡 TIP:** StringIDs are your "address" for finding strings. Think of them like house addresses!

---

### 📝 StrOrigin - The Korean Source

**What it is:** The original Korean text that needs translation

**Examples:**
```
"확인"           (OK)
"게임 시작하기"  (Start Game)
"무기를 장착하세요" (Equip weapon)
```

**Important notes:**
- Not always present (especially in SCRIPT categories)
- Used for matching in STRICT mode
- Source of truth for what needs translation

> **⚠️ WARNING:** StrOrigin may change during development! This can cause STRICT mode to fail matching.

---

### 🌍 Str - The Translation

**What it is:** The translated text in the target language

**Examples:**
```
ENG: "OK"
FRE: "D'accord"
GER: "OK"
```

**Special cases:**
- **Empty:** Translation not yet provided
- **Korean text:** Untranslated (needs work!)
- **Same as English:** May indicate missing translation

> **💡 TIP:** If `Str` contains Korean characters, it means the string is untranslated!

---

## 4.2 SCRIPT Categories - Special Case

**SCRIPT categories** have special behavior:

```
┌────────────────────────────────────────────────────────────────┐
│  SCRIPT CATEGORIES (Dialogue/Cutscenes)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Category            Content Type                              │
│  ─────────────────   ─────────────────────────────────────    │
│  🎬 Sequencer        Cutscene dialogue                         │
│  💬 AIDialog         NPC AI dialogue                           │
│  📖 QuestDialog      Quest conversations                       │
│  📢 NarrationDialog  Narrator/voiceover                        │
│                                                                │
│  ⚠️ SPECIAL BEHAVIOR:                                          │
│  • StrOrigin = full dialogue text (very long!)                │
│  • Use StringID-Only match mode for corrections               │
│  • Strict mode usually won't work (StrOrigin too long)        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Example SCRIPT entry:**
```xml
<LocStr
    StringId="Quest_MainStory_Ch1_Dialog_001"
    StrOrigin="안녕하세요, 용사님. 마을에 오신 것을 환영합니다. 최근 몬스터들이..."
    Str="Hello, hero. Welcome to the village. Recently, monsters have..."
/>
```

> **💡 TIP:** For SCRIPT categories, always use **StringID-Only match mode**!

---

## 4.3 LOOKUP vs TRANSFER - The Two Modes

```
┌─────────────────────────────────────────────────────────────────┐
│  LOOKUP (Generate) vs TRANSFER                                  │
├──────────────────────────────┬──────────────────────────────────┤
│         🔍 LOOKUP            │        📝 TRANSFER               │
├──────────────────────────────┼──────────────────────────────────┤
│ Purpose:                     │ Purpose:                         │
│  Find translations           │  Apply corrections               │
│                              │                                  │
│ Input:                       │ Input:                           │
│  Korean text or StringIDs    │  Corrections (Excel/XML)         │
│                              │                                  │
│ Output:                      │ Output:                          │
│  Excel with all languages    │  Modified XML files              │
│                              │                                  │
│ Operation:                   │ Operation:                       │
│  ✅ Read-only                │  ⚠️ WRITES to files              │
│                              │                                  │
│ Safety:                      │ Safety:                          │
│  ✅ 100% safe                │  ⚠️ Requires confirmation        │
│  ✅ No confirmation needed   │  ⚠️ Use Perforce for undo        │
│                              │                                  │
│ Speed:                       │ Speed:                           │
│  ⚡ Instant                  │  ⚡ Seconds to minutes           │
│                              │                                  │
│ Undo:                        │ Undo:                            │
│  N/A (no changes made)       │  Perforce revert                 │
└──────────────────────────────┴──────────────────────────────────┘
```

### When to Use Each

```
┌─────────────────────────────────────────────────────────────────┐
│  DECISION TREE: LOOKUP OR TRANSFER?                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Do you want to MODIFY files?                                  │
│    │                                                            │
│    ├─ NO  ────► Use LOOKUP (Generate)                          │
│    │            • Find translations                             │
│    │            • Look up StringIDs                             │
│    │            • Explore data                                  │
│    │            • Verify before applying                        │
│    │                                                            │
│    └─ YES ────► Use TRANSFER                                   │
│                 • Apply corrections                             │
│                 • Update XML files                              │
│                 • Batch fixes                                   │
│                 • ⚠️ Make sure you have backups!               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **🔥 IMPORTANT:** Always test with LOOKUP first! Use TRANSFER only when you're confident your corrections are correct.

---

## 4.4 File Structure Overview

### LOC Folder (Target for TRANSFER)

```
F:\perforce\cd\mainline\resource\GameData\stringtable\loc/
├── languagedata_eng.xml        ← English
├── languagedata_fre.xml        ← French
├── languagedata_ger.xml        ← German
├── languagedata_spa.xml        ← Spanish
├── languagedata_por.xml        ← Portuguese
├── languagedata_ita.xml        ← Italian
├── languagedata_rus.xml        ← Russian
├── languagedata_tur.xml        ← Turkish
├── languagedata_pol.xml        ← Polish
├── languagedata_jpn.xml        ← Japanese
├── languagedata_zho-cn.xml     ← Chinese Simplified
├── languagedata_zho-tw.xml     ← Chinese Traditional
├── languagedata_tha.xml        ← Thai
├── languagedata_vie.xml        ← Vietnamese
├── languagedata_ind.xml        ← Indonesian
├── languagedata_msa.xml        ← Malay
└── languagedata_kor.xml        ← Korean (source)
```

> **💡 TIP:** These are the "master" files that contain ALL translations for the game!

---

### Export Folder (Source for LOOKUP)

```
F:\perforce\cd\mainline\resource\GameData\stringtable\export__/
├── Dialog/
│   ├── AIDialog/
│   ├── NarrationDialog/
│   ├── QuestDialog/
│   └── StageCloseDialog/
├── Sequencer/
│   └── Faction/
│       └── ...
├── System/
│   ├── Item/
│   ├── Quest/
│   ├── Skill/
│   └── Ui/
└── World/
    ├── Character/
    ├── Faction/
    ├── Knowledge/
    ├── Npc/
    └── Region/
```

> **💡 TIP:** Export folder is organized by category for easy navigation!

---

# 5. LOOKUP Features

## 5.1 Generate Button - The Safe Explorer

```
┌─────────────────────────────────────────────────────────────────┐
│  WHAT GENERATE DOES                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input (Korean text)                                            │
│         ↓                                                       │
│  Match against stringtables                                     │
│         ↓                                                       │
│  Export to Excel with all 17 languages                          │
│         ↓                                                       │
│  📊 OUTPUT: Excel file in Output/ folder                        │
│  ✅ SAFETY: Read-only, no files modified                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Source Folder Auto-Detection

QuickTranslate operates in **folder mode** and automatically detects file types:

```
┌────────────────────────────────────────────────────────────────┐
│  AUTO-DETECTION MAGIC                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  File Extension          Detection                             │
│  ───────────────────     ─────────────────────────────────    │
│  .xlsx, .xls             Excel corrections (auto-detected)     │
│  .xml, .loc.xml          XML corrections (auto-detected)       │
│                                                                │
│  ✨ MIXED FILES: Place both Excel AND XML in same folder!     │
│     QuickTranslate processes ALL and combines into one output. │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Default Source folder:** `Source/` is created alongside the app and pre-populated in the GUI.

> **💡 TIP:** Just drop files in `Source/` and click Generate. Or browse to any other folder!

---

## 5.2 StringID Lookup - Direct Access

```
┌─────────────────────────────────────────────────────────────────┐
│  STRINGID LOOKUP WORKFLOW                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Enter StringID                                        │
│          [UI_MainMenu_Title_001        ]                        │
│          ↓                                                      │
│  Step 2: Click [Lookup]                                        │
│          ↓                                                      │
│  Step 3: Get Excel with ALL 17 translations                    │
│          ↓                                                      │
│  📊 OUTPUT: StringID_<ID>_YYYYMMDD_HHMMSS.xlsx                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Output columns:** StringID | ENG | FRE | GER | SPA | POR | ITA | RUS | ...

**Example output:**

| StringID | ENG | FRE | GER |
|----------|-----|-----|-----|
| UI_MainMenu_Title_001 | Main Menu | Menu Principal | Hauptmenü |

> **⚡ SPEED:** Instant lookup across all 17 languages!

---

## 5.3 Reverse Lookup - Find the ID

```
┌─────────────────────────────────────────────────────────────────┐
│  REVERSE LOOKUP WORKFLOW                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Create text file with strings (one per line)         │
│          Start Game                                             │
│          Options                                                │
│          Exit                                                   │
│          ↓                                                      │
│  Step 2: Click [Browse] → Select file                          │
│          ↓                                                      │
│  Step 3: Click [Find All]                                      │
│          ↓                                                      │
│  Step 4: Get Excel with StringID + all translations            │
│          ↓                                                      │
│  📊 OUTPUT: ReverseLookup_YYYYMMDD_HHMMSS.xlsx                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Auto-detection:** QuickTranslate identifies which language each input string is in!

**Output columns:** Input | KOR | ENG | FRE | GER | ...

**Special values:**
- `NOT FOUND` - No matching StringID
- `NO TRANSLATION` - Translation is empty

> **✨ MAGIC:** Works with ANY language! English, French, German, Korean - all auto-detected!

---

## 5.4 ToSubmit Integration

```
┌─────────────────────────────────────────────────────────────────┐
│  TOSUBMIT CHECKBOX                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [✓] Include files from ToSubmit/ folder                       │
│                                                                 │
│  When checked:                                                  │
│  • Automatically loads correction files from ToSubmit/         │
│  • Combines with selected source folder                         │
│  • Useful for batch processing pending corrections             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Folder structure:**
```
QuickTranslate/
├── Source/              ← Your current files
└── ToSubmit/            ← Staged corrections
    ├── batch1.xml
    ├── batch2.xlsx
    └── ...
```

> **💡 TIP:** Use ToSubmit/ to organize corrections awaiting approval!

---

# 6. TRANSFER Features

## 6.1 Overview - What TRANSFER Does

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  TRANSFER MODIFIES FILES!                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRANSFER writes correction text into languagedata_*.xml files. │
│  It replaces the "Str" attribute in matching LocStr elements.   │
│                                                                 │
│  Before TRANSFER:                                               │
│  <LocStr StringId="UI_001" StrOrigin="확인" Str="OK" />         │
│                                                                 │
│  After TRANSFER (correction = "Confirm"):                       │
│  <LocStr StringId="UI_001" StrOrigin="확인" Str="Confirm" />    │
│                                                                 │
│  ✅ Corrections applied directly to the XML                     │
│  ⚠️  Original "Str" value is OVERWRITTEN                        │
│  ⚠️  Always ensure Perforce backup before running!              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **🔥 IMPORTANT:** TRANSFER is available for **StringID-Only**, **Strict**, and **StrOrigin Only** match types. It is NOT available for **Substring Match** (which is lookup-only).

---

## 6.2 The TRANSFER Pipeline

When you click the TRANSFER button, the following steps happen in order:

```
┌─────────────────────────────────────────────────────────────────┐
│  TRANSFER PIPELINE (Step by Step)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: PARSE SOURCE                                           │
│          Read all correction files (Excel + XML)                │
│          ↓                                                      │
│  Step 2: DETECT LANGUAGES                                       │
│          Match source files to target languagedata_*.xml        │
│          ↓                                                      │
│  Step 3: RESOLVE EVENTNAMES (if applicable)                     │
│          Convert EventName → StringID via 3-step waterfall      │
│          ↓                                                      │
│  Step 4: SHOW TRANSFER PLAN                                     │
│          Display tree table with full file mappings              │
│          ↓                                                      │
│  Step 5: CONFIRM                                                │
│          User must click "Yes" in confirmation dialog            │
│          ↓                                                      │
│  Step 6: EXECUTE                                                │
│          Apply corrections to target XML files                  │
│          ↓                                                      │
│  Step 7: CLEANUP                                                │
│          Enforce golden rule (empty StrOrigin = empty Str)       │
│          ↓                                                      │
│  Step 8: GENERATE REPORTS                                       │
│          Transfer report + failure reports (if any)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6.3 Transfer Plan

Before any files are modified, QuickTranslate generates a **Transfer Plan** and displays it in the terminal log. The Transfer Plan is a tree table showing exactly which source files will transfer to which target files.

```
┌─────────────────────────────────────────────────────────────────┐
│  TRANSFER PLAN (Example)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ═══════════════════════════════════════════════════════        │
│        TRANSFER PLAN                                            │
│  ═══════════════════════════════════════════════════════        │
│                                                                 │
│  Source: D:\Corrections\Batch_42\                               │
│  Target: F:\perforce\...\stringtable\loc\                       │
│                                                                 │
│  ┌─ ENG (3 files) ─────────────────────────────────┐           │
│  │  corrections_eng.xlsx ──→ languagedata_eng.xml  │           │
│  │  patch_eng.xml        ──→ languagedata_eng.xml  │           │
│  │  fixes_eng.xlsx       ──→ languagedata_eng.xml  │           │
│  └──────────────────────────────────────────────────┘           │
│  ┌─ FRE (1 file) ──────────────────────────────────┐           │
│  │  corrections_fre.xlsx ──→ languagedata_fre.xml  │           │
│  └──────────────────────────────────────────────────┘           │
│  ┌─ JPN (1 file) ──── SKIPPED (no target) ─────────┐           │
│  │  corrections_jpn.xlsx ──→ ??? (not found)       │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  Summary: 4 files READY, 1 file SKIPPED                        │
│  Languages: ENG, FRE ready | JPN skipped                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** The full tree table is always printed to the terminal/log so you can review it before confirming. The confirmation dialog shows a condensed summary.

---

## 6.4 Confirmation Dialog

After the Transfer Plan is shown, a confirmation dialog appears:

```
┌─────────────────────────────────────────────────────────────────┐
│  Confirm Transfer - Review Tree in Terminal                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRANSFER will modify target XML files.                         │
│                                                                 │
│  Mode: STRICT                                                   │
│  Scope: ALL matches (overwrite)                                 │
│                                                                 │
│  Languages: 2 ready, 1 skipped                                  │
│  Files: 4 will transfer, 1 skipped (no target)                  │
│                                                                 │
│  Ready: ENG, FRE                                                │
│  Skipped: JPN                                                   │
│                                                                 │
│              [  Yes  ]        [  No  ]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **⚠️ WARNING:** Clicking "Yes" starts writing to files immediately. There is no undo within QuickTranslate. Use Perforce revert if you need to undo changes!

---

## 6.5 Transfer Scope

Transfer Scope controls **which entries** get updated:

```
┌─────────────────────────────────────────────────────────────────┐
│  TRANSFER SCOPE                                                  │
├──────────────────────────────┬──────────────────────────────────┤
│    Transfer ALL               │    Only Untranslated              │
├──────────────────────────────┼──────────────────────────────────┤
│                              │                                  │
│  Overwrite EVERY match,      │  Only overwrite entries where    │
│  even if a translation       │  the target "Str" contains      │
│  already exists.             │  Korean text or is empty.        │
│                              │                                  │
│  Use when:                   │  Use when:                       │
│  • Corrections fix known     │  • Filling in missing            │
│    wrong translations        │    translations                  │
│  • You are sure ALL          │  • StrOrigin Only mode           │
│    corrections are correct   │    (fan-out behavior)            │
│  • Small targeted batches    │  • Large batch updates           │
│                              │                                  │
│  ⚠️ Risky for large batches  │  ✅ Safe for large batches       │
│                              │                                  │
└──────────────────────────────┴──────────────────────────────────┘
```

### Default Scope by Match Type

| Match Type | Default Scope | Why |
|------------|---------------|-----|
| **Strict** | Transfer ALL | Strict match is precise, overwrite is usually intended |
| **StringID-Only** | Transfer ALL | SCRIPT corrections are targeted by definition |
| **StrOrigin Only** | Only untranslated | Fan-out is dangerous: one StrOrigin can match many entries |

> **⚠️ WARNING:** Switching StrOrigin Only to "Transfer ALL" triggers a safety warning dialog. This is because one correction can fan out to hundreds of matching entries and overwrite existing translations.

---

## 6.6 The Golden Rule (Cleanup Pass)

After every TRANSFER, QuickTranslate runs a **cleanup pass** that enforces this rule:

```
┌─────────────────────────────────────────────────────────────────┐
│  THE GOLDEN RULE                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  If StrOrigin is EMPTY → Str MUST be EMPTY                      │
│                                                                 │
│  ✅ StrOrigin="확인"     Str="OK"          (Valid: both set)     │
│  ✅ StrOrigin=""         Str=""             (Valid: both empty)   │
│  ❌ StrOrigin=""         Str="OK"          (INVALID: cleared!)   │
│                                                                 │
│  Why? Entries with empty StrOrigin are placeholders or deleted  │
│  strings. Writing a translation to them would create orphan     │
│  text that appears nowhere in the game.                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

The cleanup runs automatically. If any entries are cleaned, you will see a log message:

```
Post-process: cleared Str on 3 entries with empty StrOrigin in languagedata_eng.xml
```

> **💡 TIP:** You never need to worry about the golden rule. QuickTranslate enforces it automatically after every transfer.

---

## 6.7 Failure Reports

When corrections fail to match (NOT_FOUND, STRORIGIN_MISMATCH, etc.), QuickTranslate generates **failure reports** so you can investigate.

### Where Failure Reports Go

```
Failed Reports/
└── 260209/                        ← Date (YYMMDD)
    └── Corrections_Batch_42/      ← Source folder name
        ├── failed_eng.xml         ← Unmerged corrections (XML)
        ├── failed_fre.xml
        └── FailureReport_260209_143022.xlsx   ← Detailed Excel report
```

### Excel Failure Report Structure

The Excel failure report contains **three sheets:**

```
┌─────────────────────────────────────────────────────────────────┐
│  FAILURE REPORT EXCEL                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Sheet 1: Summary                                            │
│  ─────────────────────────────────────                         │
│  Total corrections, matched, updated, failed                   │
│  Per-language breakdown with match rates                       │
│                                                                 │
│  📊 Sheet 2: Breakdown                                          │
│  ─────────────────────────────────────                         │
│  Per-language, per-status counts                               │
│  NOT_FOUND | STRORIGIN_MISMATCH | SKIPPED_TRANSLATED | ...     │
│                                                                 │
│  📊 Sheet 3: Details                                            │
│  ─────────────────────────────────────                         │
│  Every single failed entry with:                               │
│  StringID | StrOrigin | Correction | Status | Language          │
│  + all original attributes from the source file                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Failure Status Codes

| Status Code | Meaning | Common Cause |
|-------------|---------|--------------|
| **NOT_FOUND** | StringID does not exist in the target file | Wrong StringID, or string was removed |
| **STRORIGIN_MISMATCH** | StringID exists but StrOrigin text differs | Korean source text was updated |
| **SKIPPED_TRANSLATED** | Entry already has a non-Korean translation | "Only untranslated" scope was selected |
| **SKIPPED_NON_SCRIPT** | StringID is not in a SCRIPT category | StringID-Only mode skips non-Dialog/Sequencer |
| **SKIPPED_EXCLUDED** | StringID is in an excluded subfolder | NarrationDialog is excluded by default |

> **💡 TIP:** The XML failure files preserve all original attributes, so you can re-use them as source files after fixing the issues.

---

# 7. Find Missing Translations

## 7.1 What "Find Missing" Does

**Find Missing Translations** compares a **Source folder** (your corrections/reference data) against a **Target LOC folder** (the languagedata_*.xml files) to identify Korean strings that are still untranslated.

```
┌─────────────────────────────────────────────────────────────────┐
│  FIND MISSING - CONCEPT                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Source (reference keys)          Target (LOC folder)           │
│  ┌──────────────────┐           ┌──────────────────────┐       │
│  │ StringID: UI_001  │           │ UI_001: "확인" → "OK"│       │
│  │ StringID: UI_002  │   vs.     │ UI_002: "취소" → ""  │ ← !!  │
│  │ StringID: UI_003  │           │ UI_003: "확인" → "확인"│ ← !!  │
│  └──────────────────┘           └──────────────────────────┘   │
│                                                                 │
│  Result:                                                       │
│  • UI_001: ✅ Translated (has English)                          │
│  • UI_002: ❌ MISSING (Str is empty)                            │
│  • UI_003: ❌ MISSING (Str still Korean = untranslated)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.2 Match Modes for Find Missing

When you click **Find Missing Translations**, a parameter dialog appears with **4 match modes:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Find Missing Translations - Parameters                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Match Mode:                                                    │
│    (●) StringID + KR (Strict)      ← Fastest, recommended      │
│    ( ) StringID + KR (Fuzzy)       ← For text rewording         │
│    ( ) KR only (Strict)            ← Ignore StringID changes    │
│    ( ) KR only (Fuzzy)             ← Maximum coverage (slow)    │
│                                                                 │
│  Fuzzy Threshold: [====|====] 0.85                              │
│  (only enabled when Fuzzy is selected)                          │
│                                                                 │
│  [ Exclude Folders... ]            [ Run ]  [ Cancel ]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Match Mode Comparison

| Mode | Speed | Accuracy | Best For |
|------|-------|----------|----------|
| **StringID + KR (Strict)** | ⚡⚡⚡ Instant | 🎯🎯🎯 Highest | Default choice for most cases |
| **StringID + KR (Fuzzy)** | ⚡ Minutes | 🎯🎯 High | Korean text was slightly reworded |
| **KR only (Strict)** | ⚡⚡ Fast | 🎯🎯 High | StringID changed but Korean text is same |
| **KR only (Fuzzy)** | 🐌 Slow | 🎯 Good | Maximum coverage, catches everything |

> **💡 TIP:** Start with **StringID + KR (Strict)** for the first run. It catches 95% of missing translations instantly. Use Fuzzy modes only if you suspect Korean text was reworded.

---

## 7.3 Exclude Dialog

The **Exclude Dialog** lets you filter out specific folders from the Missing Translation results. This is useful when certain categories (like Gimmick or MultiChange) are not a priority.

```
┌─────────────────────────────────────────────────────────────────┐
│  Exclude Folders                                                 │
├──────────────────────────────┬──────────────────────────────────┤
│  EXPORT Folder Tree          │  Excluded Paths                  │
│  ─────────────────────       │  ─────────────────               │
│  ▼ export__/                 │  System/Gimmick                  │
│    ▼ Dialog/                 │  System/MultiChange              │
│      ▸ AIDialog/             │                                  │
│      ▸ QuestDialog/          │  [Remove Selected]               │
│    ▼ System/                 │                                  │
│      ▸ Gimmick/ ← excluded  │                                  │
│      ▸ Item/                 │                                  │
│      ▸ MultiChange/ ← excl. │                                  │
│    ▸ World/                  │                                  │
│                              │                                  │
│  [Add Selected →]            │                                  │
│                              │                                  │
├──────────────────────────────┴──────────────────────────────────┤
│                     [  OK  ]     [  Cancel  ]                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key features:**
- **Left panel:** Browse the EXPORT folder tree
- **Right panel:** View currently excluded paths
- **Add Selected:** Move folder from tree to exclusion list
- **Remove Selected:** Remove folder from exclusion list
- **Persistence:** Exclude rules are saved to `exclude_rules.json` and remembered between sessions

> **💡 TIP:** System/Gimmick and System/MultiChange are commonly excluded as non-priority folders.

---

## 7.4 Output Files

Find Missing generates two types of output:

### Per-Language Excel Reports

```
Output/
├── MISSING_ENG_20260206_120000.xlsx
├── MISSING_FRE_20260206_120000.xlsx
├── MISSING_GER_20260206_120000.xlsx
└── ...
```

Each Excel report is clustered by EXPORT category:

| StrOrigin | Translation | StringID | Category |
|-----------|-------------|----------|----------|
| 확인 버튼을 누르세요 | 확인 버튼을 누르세요 | UI_Button_001 | UI |
| 무기를 장착하세요 | | Item_Equip_003 | Item |

### Per-Language Close Folders (XML)

```
Output/
├── Close_ENG/                  ← Mirrors EXPORT folder structure
│   ├── Dialog/
│   │   └── AIDialog/
│   │       └── npc_greetings.loc.xml
│   └── System/
│       └── Item/
│           └── weapon_names.loc.xml
├── Close_FRE/
└── ...
```

> **💡 TIP:** Close folders mirror the EXPORT structure and can be used directly as TRANSFER source files for the next correction batch!

---

# 8. Match Types

## 8.1 Overview - The Four Match Types

```
┌─────────────────────────────────────────────────────────────────┐
│  MATCH TYPE DECISION TREE                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What do you have?                                              │
│    │                                                            │
│    ├─ Just Korean text ────────► Substring Match (Lookup only)  │
│    │                                                            │
│    ├─ StringID + Correction ──► StringID-Only (SCRIPT strings)  │
│    │                                                            │
│    ├─ StringID + StrOrigin ───► Strict (safest for non-SCRIPT)  │
│    │   + Correction                                             │
│    │                                                            │
│    └─ StrOrigin + Correction ─► StrOrigin Only (fills dupes)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Comparison Table

| Feature | Substring | StringID-Only | Strict | StrOrigin Only |
|---------|:---------:|:-------------:|:------:|:--------------:|
| **LOOKUP** | ✅ | ✅ | ✅ | ✅ |
| **TRANSFER** | ❌ | ✅ | ✅ | ✅ |
| **Required: StringID** | ❌ | ✅ | ✅ | ❌ |
| **Required: StrOrigin** | ❌ | ❌ | ✅ | ✅ |
| **Required: Correction** | ❌ | ✅ | ✅ | ✅ |
| **Precision** | Low | Medium | Highest | Medium |
| **Supports Fuzzy** | ❌ | ❌ | ✅ | ✅ |
| **Fan-out** | N/A | No | No | Yes |

---

## 8.2 Substring Match (Lookup Only)

```
┌─────────────────────────────────────────────────────────────────┐
│  SUBSTRING MATCH                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How it works:                                                  │
│  Searches for your Korean text INSIDE the StrOrigin field       │
│  of every .loc.xml file in the EXPORT folder.                   │
│                                                                 │
│  Input:  "확인"                                                 │
│  Match:  StrOrigin="확인 버튼을 누르세요"  ← Contains "확인"     │
│  Match:  StrOrigin="확인"                  ← Contains "확인"     │
│  Match:  StrOrigin="주문 확인하기"         ← Contains "확인"     │
│                                                                 │
│  ✅ Good for: "What is this Korean text in English?"            │
│  ✅ Good for: Exploring translations across all languages        │
│  ❌ TRANSFER is NOT available (too imprecise for writing)       │
│                                                                 │
│  Output: Excel with all matching translations                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**When to use:**
- You see Korean text in the game and want to know what it means
- You want to find all strings containing a specific Korean phrase
- You want to explore the translation database before making corrections

**Required columns:** Just Korean text in Column A (no headers needed).

> **⚠️ WARNING:** Short Korean strings (1-2 characters) may return hundreds of matches. Be specific!

---

## 8.3 StringID-Only (SCRIPT Strings)

```
┌─────────────────────────────────────────────────────────────────┐
│  STRINGID-ONLY MATCH                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How it works:                                                  │
│  Matches by StringID ONLY, ignores StrOrigin completely.        │
│  ONLY processes SCRIPT categories (Dialog/ and Sequencer/).     │
│  Excludes NarrationDialog subfolder.                            │
│                                                                 │
│  Input:  StringID = "Quest_Ch1_Dialog_042"                      │
│  Match:  Target has StringId="Quest_Ch1_Dialog_042"  ← Match!   │
│          (StrOrigin is ignored, even if it changed)             │
│                                                                 │
│  ✅ Good for: Dialogue and cutscene corrections                 │
│  ✅ Handles Korean text changes (only StringID matters)         │
│  ⚠️ Only works for Dialog/ and Sequencer/ categories           │
│  ❌ Non-SCRIPT strings are SKIPPED (status: SKIPPED_NON_SCRIPT)│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Required columns:**

| Column | Required | Description |
|--------|:--------:|-------------|
| **StringID** | ✅ | The unique string identifier |
| **Correction** | ✅ | The corrected translation text |
| **StrOrigin** | Optional | Not used for matching, but preserved in reports |

**SCRIPT categories processed:**

| Category | Folder | Content |
|----------|--------|---------|
| 🎬 Sequencer | `export__/Sequencer/` | Cutscene dialogue |
| 💬 Dialog | `export__/Dialog/` | All dialogue types |

**Excluded subfolders:**

| Subfolder | Why Excluded |
|-----------|--------------|
| NarrationDialog | Narrator/voiceover handled separately |

> **💡 TIP:** SCRIPT categories have very long StrOrigin values (entire dialogue lines), which makes Strict matching unreliable. StringID-Only is the correct choice for these.

---

## 8.4 Strict (StringID + StrOrigin)

```
┌─────────────────────────────────────────────────────────────────┐
│  STRICT MATCH                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How it works:                                                  │
│  Requires BOTH StringID AND StrOrigin to match.                 │
│  This is the SAFEST mode for non-SCRIPT categories.             │
│                                                                 │
│  Input:  StringID="UI_001"  +  StrOrigin="확인"                  │
│  Match:  Target has StringId="UI_001" AND StrOrigin="확인"       │
│          → ✅ MATCH (both match)                                │
│                                                                 │
│  Input:  StringID="UI_001"  +  StrOrigin="확인"                  │
│  Target: StringId="UI_001"  +  StrOrigin="확인하기"              │
│          → ❌ STRORIGIN_MISMATCH (StringID found, text differs) │
│                                                                 │
│  Input:  StringID="UI_999"  +  StrOrigin="확인"                  │
│  Target: (no UI_999 exists)                                     │
│          → ❌ NOT_FOUND (StringID does not exist)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Required columns:**

| Column | Required | Description |
|--------|:--------:|-------------|
| **StringID** | ✅ | The unique string identifier |
| **StrOrigin** | ✅ | The Korean source text (must match target) |
| **Correction** | ✅ | The corrected translation text |

### 4-Step Matching Cascade

Strict mode tries multiple normalization levels before declaring "not found":

```
┌─────────────────────────────────────────────────────────────────┐
│  STRICT MATCHING CASCADE                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: EXACT match                                            │
│          StringID (case-insensitive) + normalized StrOrigin     │
│          ↓ (if no match)                                        │
│  Step 2: LOWERCASE match                                        │
│          Both sides lowercased                                  │
│          ↓ (if no match)                                        │
│  Step 3: NORMALIZED match                                       │
│          HTML unescape + whitespace collapse + &desc; removal   │
│          ↓ (if no match)                                        │
│  Step 4: NOSPACE FALLBACK                                       │
│          Remove ALL whitespace and compare                      │
│          ↓ (if still no match)                                  │
│  Result: NOT_FOUND or STRORIGIN_MISMATCH                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Perfect vs Fuzzy Precision

Strict mode supports two precision levels:

| Precision | Speed | How It Works |
|-----------|-------|--------------|
| **Perfect** | ⚡ Instant | Exact match only (4-step cascade above) |
| **Fuzzy** | 🐌 Minutes | Perfect first, then SBERT semantic search on unmatched |

> **💡 TIP:** Use Perfect precision for most workflows. Switch to Fuzzy only when you know Korean text was significantly reworded and the 4-step cascade cannot handle it.

---

## 8.5 StrOrigin Only (Fills Duplicates)

```
┌─────────────────────────────────────────────────────────────────┐
│  STRORIGIN ONLY MATCH                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How it works:                                                  │
│  Matches by StrOrigin text ONLY, ignores StringID.              │
│  ONE correction fills ALL entries with the same StrOrigin.      │
│  This is called "fan-out" behavior.                             │
│                                                                 │
│  Input:  StrOrigin="확인"  Correction="Confirm"                  │
│                                                                 │
│  Target file has 5 entries with StrOrigin="확인":                │
│  • UI_001:    StrOrigin="확인" → Str updated to "Confirm"        │
│  • UI_042:    StrOrigin="확인" → Str updated to "Confirm"        │
│  • Menu_007:  StrOrigin="확인" → Str updated to "Confirm"        │
│  • Shop_003:  StrOrigin="확인" → Str updated to "Confirm"        │
│  • Quest_001: StrOrigin="확인" → Str updated to "Confirm"        │
│                                                                 │
│  ✅ Good for: Filling untranslated strings across many entries  │
│  ⚠️ CAUTION: Fan-out means one row can update MANY entries     │
│  ⚠️ Defaults to "Only untranslated" scope for safety           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Required columns:**

| Column | Required | Description |
|--------|:--------:|-------------|
| **StrOrigin** | ✅ | The Korean source text to match |
| **Correction** | ✅ | The corrected translation text |
| **StringID** | Optional | Not used for matching, but preserved in reports |

### Fan-Out Behavior Explained

```
┌─────────────────────────────────────────────────────────────────┐
│  FAN-OUT: ONE Correction → MANY Entries                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Source (1 row):                                                │
│  ┌──────────────────────────────────────────┐                   │
│  │ StrOrigin: "확인"   Correction: "Confirm" │                   │
│  └──────────────────────────────────────────┘                   │
│                      │                                          │
│                      ↓ (fans out to ALL matches)                │
│                                                                 │
│  Target entries updated:                                        │
│  ┌──────────────────────────────────────────┐                   │
│  │ UI_001:    "확인" → "Confirm"             │                   │
│  │ UI_042:    "확인" → "Confirm"             │                   │
│  │ Menu_007:  "확인" → "Confirm"             │                   │
│  │ Shop_003:  "확인" → "Confirm"             │                   │
│  │ Quest_001: "확인" → "Confirm"             │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                 │
│  ⚠️ 1 source row updated 5 target entries!                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why "Only Untranslated" is the Default

Because of fan-out, StrOrigin Only defaults to **"Only untranslated"** scope:

| Scope | Behavior | Risk |
|-------|----------|------|
| **Only untranslated** (default) | Only fills entries where Str is empty or Korean | ✅ Safe: never overwrites existing translations |
| **Transfer ALL** | Overwrites ALL matching entries | ⚠️ Dangerous: could overwrite good translations |

> **⚠️ WARNING:** Switching to "Transfer ALL" in StrOrigin Only mode triggers a warning dialog. Think carefully before confirming - you could be overwriting hundreds of already-correct translations!

---

# 9. Workflows

## 9.1 Typical Correction Workflow (End to End)

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPLETE CORRECTION WORKFLOW                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: DISCOVER                                               │
│          Use LOOKUP (Substring) to find the string              │
│          → Get StringID, current translations, category          │
│          ↓                                                      │
│  Step 2: PREPARE                                                │
│          Create correction Excel with correct columns           │
│          → StringID, StrOrigin, Correction (or EventName)       │
│          ↓                                                      │
│  Step 3: ORGANIZE                                               │
│          Place files in Source/ folder with language naming      │
│          → corrections_eng.xlsx, corrections_fre.xlsx, etc.     │
│          ↓                                                      │
│  Step 4: TEST (Optional but recommended)                        │
│          Use LOOKUP (Strict) to verify matches before transfer  │
│          → Check that corrections match target entries          │
│          ↓                                                      │
│  Step 5: TRANSFER                                               │
│          Click TRANSFER, review plan, confirm                   │
│          → Corrections written to languagedata_*.xml files      │
│          ↓                                                      │
│  Step 6: VERIFY                                                 │
│          Check failure reports, review modified files            │
│          → Use Perforce diff to confirm changes                 │
│          ↓                                                      │
│  Step 7: SUBMIT                                                 │
│          Submit changes via Perforce                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.2 Organizing Source Files by Language

QuickTranslate auto-detects which language each source file belongs to. You can organize files using **folder names** or **file names.**

### Method 1: Language Folders (Recommended)

```
Source/
├── Corrections_ENG/           ← Language from folder name
│   ├── batch1.xlsx
│   ├── batch2.xml
│   └── fixes.xlsx
├── FRE/                       ← Language from folder name
│   └── corrections.xlsx
├── ZHO-CN/                    ← Hyphenated codes work too
│   └── corrections.xlsx
└── GER/
    └── patch.xlsx
```

### Method 2: File Names

```
Source/
├── corrections_eng.xlsx       ← Language from filename suffix
├── corrections_fre.xlsx
├── patch_ger.xlsx
├── languagedata_spa-es.xml    ← Standard languagedata naming
└── fixes_zho-cn.xlsx
```

### Language Detection Rules

QuickTranslate detects language codes using these rules (in priority order):

```
┌─────────────────────────────────────────────────────────────────┐
│  LANGUAGE DETECTION PRIORITY                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Folder name:    Corrections_ENG/ → "eng"                    │
│     • Underscore separator: Corrections_ENG → takes "eng"       │
│     • Direct name: ENG/ → "eng"                                 │
│     • Case-insensitive: eng/, ENG/, Eng/ all work              │
│                                                                 │
│  2. File name:      corrections_eng.xlsx → "eng"                │
│     • Last part after underscore: corrections_fre → "fre"       │
│     • Standard prefix: languagedata_ger.xml → "ger"            │
│                                                                 │
│  3. Hyphenated codes: zho-cn, zho-tw, spa-es, spa-mx, por-br  │
│     • Case-insensitive: ZHO-CN, zho-cn, Zho-CN all work       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** Folder-based organization is the most reliable. If you have corrections for 5 languages, create 5 subfolders in Source/.

---

## 9.3 EventName Resolution (3-Step Waterfall)

When your source file has an **EventName** column instead of StringID, QuickTranslate resolves it through a 3-step waterfall:

```
┌─────────────────────────────────────────────────────────────────┐
│  EVENTNAME → STRINGID RESOLUTION                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: DIALOGVOICE GENERATION                                 │
│  ─────────────────────────────                                 │
│  If DialogVoice column exists:                                  │
│    Remove DialogVoice prefix from EventName                     │
│    Example: EventName = "John_Conversation_Greeting_001"        │
│             DialogVoice = "John_Conversation"                   │
│             Result: StringID = "Greeting_001"                   │
│                                                                 │
│         ↓ (if Step 1 fails)                                     │
│                                                                 │
│  Step 2: KEYWORD EXTRACTION                                     │
│  ─────────────────────────────                                 │
│  Look for aidialog/questdialog keywords in EventName:           │
│    Example: EventName = "VO_AIDialog_NPC_Hello_001"             │
│             Keyword found: "aidialog"                           │
│             Result: StringID = "NPC_Hello_001"                  │
│                                                                 │
│         ↓ (if Step 2 fails)                                     │
│                                                                 │
│  Step 3: EXPORT FOLDER LOOKUP                                   │
│  ─────────────────────────────                                 │
│  Search EXPORT .loc.xml files for SoundEventName attribute:     │
│    Example: EventName = "VO_Custom_Event_123"                   │
│             Found in: export__/Dialog/AIDialog/npc.loc.xml      │
│             Result: StringID from matching LocStr element       │
│                                                                 │
│         ↓ (if all 3 steps fail)                                 │
│                                                                 │
│  Result: MISSING EVENTNAME (appears in failure report)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **💡 TIP:** If your Excel has both StringID and EventName columns, QuickTranslate uses per-row priority: StringID wins when present, EventName is the fallback for rows where StringID is empty.

---

## 9.4 Excel Column Headers (Recognized Names)

QuickTranslate recognizes the following column header names (all **case-insensitive**):

| Logical Column | Recognized Headers |
|----------------|--------------------|
| **StringID** | `StringID`, `StringId`, `string_id`, `STRINGID`, `id` |
| **StrOrigin** | `StrOrigin`, `Str_Origin`, `str_origin`, `STRORIGIN`, `origin`, `korean`, `kor` |
| **Correction** | `Correction`, `correction`, `corrected`, `translated`, `translation`, `Str`, `str` |
| **EventName** | `EventName`, `event_name`, `SoundEventName`, `soundeventname` |
| **DialogVoice** | `DialogVoice`, `dialog_voice` |

> **💡 TIP:** Column ORDER does not matter! QuickTranslate detects columns by header name, not position. Put them in any order you like.

> **⚠️ WARNING:** If required columns are missing, you will see a clear error message listing what was found and what is needed.

---

# 10. Output Files

## 10.1 Output Folder Structure

```
QuickTranslate/
├── Output/                                  ← 📊 LOOKUP results
│   ├── QuickTranslate_20260211_143022.xlsx  ← Generate results
│   ├── StringID_UI_001_20260211_143025.xlsx ← StringID lookup
│   └── ReverseLookup_20260211_143030.xlsx   ← Reverse lookup
│
├── Presubmission Checks/                    ← ⚠️ Quality checks
│   ├── Korean/                              ← Check Korean results
│   │   ├── korean_eng_20260211.xml
│   │   └── korean_fre_20260211.xml
│   ├── PatternErrors/                       ← Check Patterns results
│   │   ├── pattern_eng_20260211.xml
│   │   └── pattern_fre_20260211.xml
│   └── QualityCheck/                        ← Check Quality results
│       ├── quality_eng_20260211.xlsx
│       └── quality_fre_20260211.xlsx
│
└── Failed Reports/                          ← ❌ TRANSFER failures
    └── 260211/                              ← Date (YYMMDD)
        └── Corrections_Batch_42/            ← Source folder name
            ├── failed_eng.xml               ← Unmerged corrections
            ├── failed_fre.xml
            └── FailureReport_260211_143022.xlsx
```

---

## 10.2 Output File Details

### Generate Results (LOOKUP)

**File:** `Output/QuickTranslate_YYYYMMDD_HHMMSS.xlsx`

**Sheets:**
- **Summary:** Match statistics (total, matched, not found, multi-match)
- **Translations:** Full results with columns: KOR (Input) | Status | StringID | ENG | FRE | GER | ...

**Status values:**
| Status | Color | Meaning |
|--------|-------|---------|
| MATCHED | 🟢 Green | Exactly 1 StringID found |
| MULTI (N) | 🟠 Orange | N StringIDs found (listed in StringID column) |
| NOT FOUND | 🔴 Red | No matching string found |

---

### StringID Lookup

**File:** `Output/StringID_<ID>_YYYYMMDD_HHMMSS.xlsx`

**Columns:** StringID | ENG | FRE | GER | ITA | JPN | KOR | ...

One row with translations in all available languages.

---

### Reverse Lookup

**File:** `Output/ReverseLookup_YYYYMMDD_HHMMSS.xlsx`

**Columns:** Input | KOR | ENG | FRE | GER | ...

One row per input text, with the auto-detected StringID and all translations.

**Special values:**
- `NOT FOUND` - No matching StringID for this text
- `NO TRANSLATION` - StringID exists but translation is empty

---

### Failed Merge XML

**File:** `Failed Reports/YYMMDD/source_name/failed_<lang>.xml`

Contains all LocStr elements that failed to merge, preserving ALL original attributes. This file can be used as a new source file after fixing the issues.

---

### Failure Report Excel

**File:** `Failed Reports/YYMMDD/source_name/FailureReport_YYYYMMDD_HHMMSS.xlsx`

| Sheet | Content |
|-------|---------|
| **Summary** | Total corrections, matched, updated, failed; per-language match rates |
| **Breakdown** | Per-language, per-status counts (NOT_FOUND, STRORIGIN_MISMATCH, etc.) |
| **Details** | Every single failed entry: StringID, StrOrigin, Correction, Status, Language |

---

# 11. Troubleshooting

## 11.1 Common Problems & Solutions

### "Match type is greyed out"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: Match type radio buttons are disabled                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cause:                                                         │
│  The source files do not contain the required columns for       │
│  that match type. QuickTranslate scans your source files and    │
│  disables match types whose required columns are missing.       │
│                                                                 │
│  Solutions:                                                     │
│  • Check that your Excel has the correct column headers          │
│  • StringID-Only needs: StringID + Correction                   │
│  • Strict needs: StringID + StrOrigin + Correction              │
│  • StrOrigin Only needs: StrOrigin + Correction                 │
│  • Make sure headers are in the FIRST ROW                       │
│                                                                 │
│  Quick diagnostic:                                              │
│  Look at the log area - it shows which columns were detected    │
│  when you browse to a source folder.                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### "TRANSFER button does nothing" / "TRANSFER not available"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: TRANSFER button is disabled or does nothing            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cause:                                                         │
│  Substring Match mode is selected. Substring is lookup-only     │
│  and does not support TRANSFER.                                 │
│                                                                 │
│  Solution:                                                      │
│  Switch to one of these match types:                            │
│  • StringID-Only (for SCRIPT strings)                           │
│  • Strict (for precise matching)                                │
│  • StrOrigin Only (for filling duplicates)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### "Korean corrections skipped"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: Rows in source file are being skipped                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cause:                                                         │
│  QuickTranslate skips rows where the "Correction" column        │
│  contains Korean text. This means the correction has not been   │
│  translated yet and should not be written to target files.      │
│                                                                 │
│  How it works:                                                  │
│  • Correction = "Confirm"     → ✅ Applied (non-Korean)         │
│  • Correction = "확인"        → ❌ Skipped (still Korean)       │
│  • Correction = "확인 Button" → ❌ Skipped (contains Korean)    │
│  • Correction = ""            → ❌ Skipped (empty)              │
│                                                                 │
│  Solution:                                                      │
│  Ensure all corrections are actually translated before          │
│  running TRANSFER.                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### "EventName not resolved"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: EventNames fail to resolve to StringIDs               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cause:                                                         │
│  The 3-step waterfall (DialogVoice → Keyword → Export lookup)   │
│  could not find a matching StringID for the EventName.          │
│                                                                 │
│  Solutions:                                                     │
│  1. Check if the EventName exists in the EXPORT folder          │
│     (search for SoundEventName attributes)                      │
│  2. Verify the DialogVoice column is correct (if present)       │
│  3. Check the Missing EventName report in Failed Reports/       │
│  4. Consider using StringID directly instead of EventName       │
│                                                                 │
│  💡 The Missing EventName report lists all unresolved           │
│     EventNames so you can fix them in your source file.         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### "0 matches found"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: No matches found at all                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Checklist:                                                     │
│                                                                 │
│  □ Is the correct match type selected?                          │
│    • Strict requires StringID + StrOrigin                       │
│    • StringID-Only requires Dialog/Sequencer categories          │
│                                                                 │
│  □ Are the source file columns correct?                         │
│    • Check column headers match expected names                  │
│    • Check column detection in the log                          │
│                                                                 │
│  □ Are the paths correct?                                       │
│    • Source: Points to your correction files                    │
│    • Target: Points to the LOC folder with languagedata_*.xml  │
│                                                                 │
│  □ Did you sync from Perforce recently?                         │
│    • Target files may be outdated                               │
│                                                                 │
│  □ For Strict mode: has the Korean source text changed?         │
│    • Use Fuzzy precision to handle text rewording               │
│                                                                 │
│  □ For StringID-Only: are your strings in SCRIPT categories?    │
│    • Only Dialog/ and Sequencer/ categories are processed       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### "settings.json issues"

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEM: Paths not loading or saving correctly                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  settings.json location:                                        │
│  Same folder as QuickTranslate.exe (or main.py)                │
│                                                                 │
│  Common issues:                                                 │
│  • Single backslash: "C:\path" → Use "C:\\path" (double!)       │
│  • Trailing backslash: "C:\\path\\" → Remove trailing \\       │
│  • Missing quotes: C:\path → Must be "C:\\path"                │
│  • Invalid JSON: Check for missing commas or brackets           │
│                                                                 │
│  Reset to defaults:                                             │
│  Delete settings.json and restart QuickTranslate.               │
│  A fresh settings.json with F: drive defaults will be created.  │
│                                                                 │
│  Correct format:                                                │
│  {                                                              │
│    "loc_folder": "F:\\perforce\\cd\\mainline\\...\\loc",        │
│    "export_folder": "F:\\perforce\\cd\\mainline\\...\\export__" │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 12. Reference

## 12.1 Pre-Submission Checks

QuickTranslate includes three quality checks that can be run on Source files before submission:

### Check Korean (Untranslated Detection)

```
┌─────────────────────────────────────────────────────────────────┐
│  CHECK KOREAN                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What it does:                                                  │
│  Scans non-KOR languagedata files in Source/ for entries where  │
│  the "Str" field still contains Korean text.                    │
│                                                                 │
│  If "Str" has Korean in a non-Korean file, it means the        │
│  string was never translated (or was copy-pasted from Korean).  │
│                                                                 │
│  Output: XML files in Presubmission Checks/Korean/              │
│  Example: korean_eng_20260211.xml                               │
│                                                                 │
│  Each file contains the LocStr elements that still have         │
│  Korean text in their Str attribute.                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Check Patterns (Placeholder Validation)

```
┌─────────────────────────────────────────────────────────────────┐
│  CHECK PATTERNS                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What it does:                                                  │
│  Validates that {code} placeholders in translations match the   │
│  placeholders in the Korean source (StrOrigin).                 │
│                                                                 │
│  Example mismatch:                                              │
│  StrOrigin: "{Name}이(가) {Item}을(를) 획득했습니다."           │
│  Str:       "{Name} obtained {Weapon}."                         │
│  Error:     {Item} in source but {Weapon} in translation!       │
│                                                                 │
│  This catches:                                                  │
│  • Missing placeholders (translator forgot to include {code})   │
│  • Extra placeholders (translator added wrong {code})           │
│  • Renamed placeholders (translator changed {Item} to {Weapon}) │
│                                                                 │
│  Output: XML files in Presubmission Checks/PatternErrors/       │
│  Example: pattern_eng_20260211.xml                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Check Quality (Script + Hallucination Detection)

```
┌─────────────────────────────────────────────────────────────────┐
│  CHECK QUALITY                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What it does:                                                  │
│  Two-part quality scan:                                         │
│                                                                 │
│  Part 1: WRONG SCRIPT DETECTION                                 │
│  Finds characters from the wrong writing system.                │
│  Example: Cyrillic characters in a French translation,          │
│  or Latin characters where Japanese is expected.                │
│                                                                 │
│  Part 2: AI HALLUCINATION DETECTION                             │
│  Finds signs of machine translation errors:                     │
│  • Common AI phrases ("I'd be happy to help")                   │
│  • Extreme length ratios (translation 5x longer than source)    │
│  • Forward slashes in non-code text (common LLM artifact)       │
│                                                                 │
│  Output: Excel files in Presubmission Checks/QualityCheck/      │
│  Example: quality_eng_20260211.xlsx                             │
│                                                                 │
│  Excel has two tabs:                                            │
│  • "Language Issues" - Wrong script characters                  │
│  • "AI Hallucination" - Potential machine translation errors    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12.2 Fuzzy Matching Details

### How Fuzzy Matching Works

```
┌─────────────────────────────────────────────────────────────────┐
│  FUZZY MATCHING UNDER THE HOOD                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Technology: KR-SBERT (Korean Sentence-BERT)                    │
│  Index:      FAISS IndexFlatIP (Inner Product = Cosine)         │
│                                                                 │
│  How it works:                                                  │
│  1. Load KR-SBERT model (first time: ~30 seconds)              │
│  2. Encode all Korean source texts as vectors                   │
│  3. Build FAISS index for fast similarity search                │
│  4. For each correction, encode and find best match             │
│  5. If similarity score >= threshold → MATCH                    │
│                                                                 │
│  Threshold range: 0.70 to 1.00 (default: 0.85)                 │
│                                                                 │
│  Score interpretation:                                          │
│  • 1.00 = Identical text                                        │
│  • 0.95+ = Minor wording change                                │
│  • 0.85-0.95 = Moderate rewording                              │
│  • 0.70-0.85 = Significant differences                         │
│  • Below 0.70 = Probably not the same string                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Fuzzy Threshold Guidance

| Threshold | Strictness | Use Case |
|-----------|------------|----------|
| **0.95** | Very strict | Only minor spelling/whitespace changes |
| **0.85** (default) | Balanced | General-purpose rewording detection |
| **0.80** | Relaxed | Significant Korean text changes |
| **0.70** | Very relaxed | Maximum coverage (may have false positives) |

> **💡 TIP:** Lower threshold = more matches but higher risk of wrong matches. Start with the default 0.85 and only lower it if you see too many NOT_FOUND results.

---

## 12.3 Settings Configuration

### settings.json

**Location:** Same folder as `QuickTranslate.exe` or `main.py`

**Format:**
```json
{
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__"
}
```

| Setting | Description | Default |
|---------|-------------|---------|
| **loc_folder** | Path to LOC folder with languagedata_*.xml files | F:\perforce\...\loc |
| **export_folder** | Path to EXPORT folder with categorized .loc.xml files | F:\perforce\...\export__ |

### exclude_rules.json

**Location:** Same folder as `QuickTranslate.exe` or `main.py`

**Format:**
```json
{
  "excluded_paths": [
    "System/Gimmick",
    "System/MultiChange"
  ]
}
```

Used by **Find Missing Translations** to filter out non-priority folders from results.

> **💡 TIP:** You can edit exclude_rules.json manually, or use the Exclude Dialog in the GUI (much easier).

---

# 13. Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════════╗
║                  QUICKTRANSLATE QUICK REFERENCE                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  BUTTONS                                                          ║
║  ────────────────────────────────────────────────────             ║
║  [Generate]           Find translations → Export to Excel         ║
║  [TRANSFER]           Apply corrections → Write to XML files      ║
║  [StringID Lookup]    Look up one StringID → All languages        ║
║  [Reverse Lookup]     Text file → Find StringIDs                  ║
║  [Find Missing]       Compare source vs target → Gap report       ║
║  [Check Korean]       Find untranslated Korean in target files    ║
║  [Check Patterns]     Validate {code} placeholders match          ║
║  [Check Quality]      Wrong script + AI hallucination detection   ║
║  [Exclude Folders]    Configure excluded paths for Find Missing   ║
║  [Settings]           Configure LOC and EXPORT folder paths       ║
║  [Clear Log]          Clear the log area                          ║
║  [Clear All]          Reset all fields                            ║
║  [Exit]               Close the application                       ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  MATCH TYPES                                                      ║
║  ────────────────────────────────────────────────────             ║
║  Substring     Korean text search, lookup only, no TRANSFER       ║
║  StringID-Only StringID match, SCRIPT only, ignores StrOrigin     ║
║  Strict        StringID + StrOrigin, safest, 4-step cascade       ║
║  StrOrigin Only  StrOrigin match, fan-out, fills duplicates       ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  MATCH PRECISION (Strict & StrOrigin Only)                        ║
║  ────────────────────────────────────────────────────             ║
║  Perfect       Exact match only (instant)                         ║
║  Fuzzy         Perfect first, then SBERT semantic search (slow)   ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  TRANSFER SCOPE                                                   ║
║  ────────────────────────────────────────────────────             ║
║  Transfer ALL          Overwrite all matches                      ║
║  Only untranslated     Only fill Korean/empty entries             ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  REQUIRED COLUMNS BY MATCH TYPE                                   ║
║  ────────────────────────────────────────────────────             ║
║  Substring:      Column A with Korean text (no headers needed)    ║
║  StringID-Only:  StringID + Correction                            ║
║  Strict:         StringID + StrOrigin + Correction                ║
║  StrOrigin Only: StrOrigin + Correction                           ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  OUTPUT LOCATIONS                                                 ║
║  ────────────────────────────────────────────────────             ║
║  Output/                  LOOKUP results (Excel)                  ║
║  Presubmission Checks/    Quality check results (XML + Excel)     ║
║  Failed Reports/          TRANSFER failure reports (XML + Excel)  ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  SAFETY TIPS                                                      ║
║  ────────────────────────────────────────────────────             ║
║  ✅ Always LOOKUP first, TRANSFER second                          ║
║  ✅ Keep Perforce up to date (for undo via revert)                ║
║  ✅ Check failure reports after every TRANSFER                    ║
║  ✅ Use "Only untranslated" scope for large batches               ║
║  ⚠️ TRANSFER modifies files! No built-in undo!                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

# 14. Appendix

## 14.1 Supported Languages

QuickTranslate auto-discovers languages from the LOC folder. The following is the standard production language set:

| Code | Language | Script |
|------|----------|--------|
| `eng` | English | Latin |
| `fre` | French | Latin |
| `ger` | German | Latin |
| `ita` | Italian | Latin |
| `jpn` | Japanese | CJK + Kana |
| `kor` | Korean (Source) | Hangul |
| `pol` | Polish | Latin |
| `por-br` | Portuguese (Brazil) | Latin |
| `rus` | Russian | Cyrillic |
| `spa-es` | Spanish (Spain) | Latin |
| `spa-mx` | Spanish (Mexico) | Latin |
| `tur` | Turkish | Latin |
| `zho-cn` | Chinese Simplified | CJK |
| `zho-tw` | Chinese Traditional | CJK |

> **💡 TIP:** If your project has additional languages (e.g., `tha`, `vie`, `ind`, `msa`), QuickTranslate will auto-discover them from the LOC folder. No configuration needed.

---

## 14.2 Column Header Mapping

Complete list of recognized column header names (all case-insensitive):

| Logical Column | Recognized Names |
|----------------|------------------|
| **StringID** | `StringID`, `StringId`, `string_id`, `STRINGID`, `id` |
| **StrOrigin** | `StrOrigin`, `Str_Origin`, `str_origin`, `STRORIGIN`, `origin`, `korean`, `kor` |
| **Correction** | `Correction`, `correction`, `corrected`, `translated`, `translation`, `Str`, `str` |
| **EventName** | `EventName`, `event_name`, `SoundEventName`, `soundeventname` |
| **DialogVoice** | `DialogVoice`, `dialog_voice` |

**Column combination requirements:**

| Match Type | Minimum Required | Optional |
|------------|------------------|----------|
| Substring | Column A (any text) | None |
| StringID-Only | StringID + Correction | StrOrigin, EventName, DialogVoice |
| Strict | StringID + StrOrigin + Correction | EventName, DialogVoice |
| StrOrigin Only | StrOrigin + Correction | StringID, EventName, DialogVoice |

---

## 14.3 Failure Reason Codes

Complete list of status codes that appear in TRANSFER results and failure reports:

| Code | Meaning | When It Happens |
|------|---------|-----------------|
| `UPDATED` | Correction applied successfully | Target entry found and Str was changed |
| `UNCHANGED` | Entry matched but value is already correct | New value equals existing value |
| `NOT_FOUND` | StringID does not exist in target file | Wrong StringID or string was removed from game |
| `STRORIGIN_MISMATCH` | StringID exists but StrOrigin differs | Korean source text was updated (use Fuzzy) |
| `SKIPPED_TRANSLATED` | Entry already has non-Korean translation | "Only untranslated" scope is active |
| `SKIPPED_NON_SCRIPT` | StringID not in Dialog/Sequencer category | StringID-Only mode skips non-SCRIPT strings |
| `SKIPPED_EXCLUDED` | StringID is in an excluded subfolder | NarrationDialog or user-excluded path |

---

## 14.4 File Format Reference

### Source File Formats

| Format | Extensions | Used For |
|--------|-----------|----------|
| **Excel** | `.xlsx`, `.xls` | Corrections with column headers |
| **XML** | `.xml`, `.loc.xml` | Correction LocStr elements |

### Target File Format

```xml
<!-- languagedata_eng.xml (target) -->
<root>
  <LocStr StringId="UI_001" StrOrigin="확인" Str="OK" />
  <LocStr StringId="UI_002" StrOrigin="취소" Str="Cancel" />
  ...
</root>
```

### Export File Format

```xml
<!-- export__/System/Ui/menu.loc.xml (reference) -->
<root>
  <LocStr StringId="UI_001" StrOrigin="확인" Str="확인" />
  <LocStr StringId="UI_002" StrOrigin="취소" Str="취소" />
  ...
</root>
```

> **💡 TIP:** Export files always have the Korean text in Str (they are the Korean reference). LOC files have the translated text in Str.

---

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                     END OF USER GUIDE                             ║
║                                                                   ║
║              QuickTranslate v4.0.0 | February 2026                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```