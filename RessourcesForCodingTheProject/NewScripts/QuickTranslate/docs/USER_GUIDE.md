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

This is the first part. I'll continue with the remaining sections in the next response.