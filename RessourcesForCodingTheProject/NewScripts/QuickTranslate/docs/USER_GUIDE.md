# QuickTranslate User Guide

**Version 3.1.0** | February 2026 | LocaNext Project

---

> *"Lookup & Transfer - Two Tools in One"*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Core Concepts](#4-core-concepts)
5. [LOOKUP Features](#5-lookup-features)
6. [TRANSFER Features](#6-transfer-features)
7. [Match Types](#7-match-types)
8. [Workflows](#8-workflows)
9. [Output Files](#9-output-files)
10. [Troubleshooting](#10-troubleshooting)
11. [Reference](#11-reference)
12. [Appendix](#12-appendix)

---

# 1. Introduction

## 1.1 What is QuickTranslate?

**QuickTranslate** is a dual-purpose desktop application for localization teams:

| Function | Description |
|----------|-------------|
| **LOOKUP** | Find translations of Korean text across 17 languages |
| **TRANSFER** | Write corrections from Excel/XML to target XML files |

### Two Buttons, Two Workflows

```
┌─────────────────────────────────────────────────────────────┐
│                      QuickTranslate                         │
├─────────────────────────────────────────────────────────────┤
│ [Generate]                    │ [TRANSFER]                  │
│   ↓                           │    ↓                        │
│ Read source → Find matches    │ Read source → Match →       │
│   → Export to Excel           │   → WRITE to target XMLs    │
│   (READ-ONLY operation)       │   (MODIFIES target files!)  │
└─────────────────────────────────────────────────────────────┘
```

### LOOKUP (Generate Button)
- Find translations for Korean text
- Look up any StringID to see all languages
- Reverse-lookup: find StringID from text in any language
- **Output:** Excel file with all translations
- **Safe:** Read-only, never modifies source files

### TRANSFER (TRANSFER Button)
- Read corrections from Excel or XML
- Match corrections to target XML files
- **Write** corrections to target languagedata_*.xml files
- **Output:** Modified XML files in LOC folder
- **Careful:** Modifies target files!

## 1.2 Who is it for?

| Role | LOOKUP Use Case | TRANSFER Use Case |
|------|-----------------|-------------------|
| **Localization Coordinators** | Find existing translations | Apply batch corrections |
| **QA Testers** | Verify translation consistency | Fix verified issues |
| **Translators** | Look up reference translations | Submit corrections |
| **Developers** | Find StringIDs from text | Update localization files |

## 1.3 Key Benefits

| Feature | LOOKUP | TRANSFER |
|---------|--------|----------|
| **Speed** | Process hundreds of strings in seconds | Update multiple files at once |
| **Accuracy** | Multiple matching strategies | Strict and StringID-only modes |
| **Completeness** | Access all 17 languages | Target all languagedata files |
| **Flexibility** | Excel and XML input/output | Excel and XML corrections |
| **Safety** | Read-only operation | Confirmation before write |

---

# 2. Installation

## 2.1 System Requirements

| Requirement | Specification |
|-------------|---------------|
| **Operating System** | Windows 10 / Windows 11 |
| **Perforce Access** | Sync access to stringtable folders |
| **Drive** | F: drive mapped (or custom path configured) |
| **Python** | 3.11+ (portable version only) |

## 2.2 Installation Methods

### 2.2.1 Setup Installer (Recommended)

1. Download `QuickTranslate_vX.X.X_Setup.exe` from releases
2. Run the installer
3. Select installation drive (C:, D:, F:, etc.)
4. Click **Install**
5. Application launches automatically

### 2.2.2 Portable Version

1. Download `QuickTranslate_vX.X.X_Portable.zip`
2. Extract to any folder
3. Run `QuickTranslate.exe`

## 2.3 First-Time Configuration

On first launch, QuickTranslate creates `settings.json`:

```json
{
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__"
}
```

**To change paths:**
1. Close QuickTranslate
2. Edit `settings.json` in the application folder
3. Update paths to match your Perforce workspace
4. Restart QuickTranslate

---

# 3. Quick Start

## 3.1 Your First LOOKUP (Translation Search)

**Goal:** Find translations for Korean strings

### Step 1: Prepare Input Excel

| Column A |
|----------|
| 안녕하세요 |
| 감사합니다 |
| 시작하기 |

Save as `input.xlsx`

### Step 2: Configure

1. Launch QuickTranslate
2. Set **Format**: Excel
3. Set **Mode**: File
4. Set **Match Type**: Substring Match

### Step 3: Select & Generate

1. Click **Browse** → select `input.xlsx`
2. Click **Generate**

### Step 4: View Results

Output: `Output/QuickTranslate_YYYYMMDD_HHMMSS.xlsx`

| KOR (Input) | ENG | FRE | GER | ... |
|-------------|-----|-----|-----|-----|
| 안녕하세요 | Hello | Bonjour | Hallo | ... |

---

## 3.2 Your First TRANSFER (Apply Corrections)

**Goal:** Apply corrections from Excel to LOC XML files

### Step 1: Prepare Corrections Excel

| StringID | StrOrigin | Correction |
|----------|-----------|------------|
| UI_001 | 확인 버튼 | OK Button (fixed) |
| UI_002 | 취소 버튼 | Cancel Button (fixed) |

Columns can be in any order - QuickTranslate auto-detects them.

### Step 2: Configure

1. Set **Format**: Excel
2. Set **Mode**: File
3. Set **Match Type**: StringID + StrOrigin (STRICT)

### Step 3: Select Files

1. **Source**: Browse → select your corrections Excel
2. **Target**: Browse → select LOC folder (or leave default)

### Step 4: Transfer

1. Click **TRANSFER** (red button)
2. Confirm the operation in dialog
3. View results in log

### Step 5: Verify

Check the modified `languagedata_*.xml` files in target folder.

---

## 3.3 Quick StringID Lookup

**Goal:** Find all translations for a specific StringID

1. Enter StringID in Quick Actions section (e.g., `UI_MainMenu_Title`)
2. Click **Lookup**
3. Output: Excel with all 17 language translations

---

## 3.4 Reverse Lookup

**Goal:** Find StringID from English (or any language) text

1. Create text file:
   ```
   Start Game
   Options
   Exit
   ```
2. In Quick Actions → Reverse, click **Browse**
3. Select your text file
4. Click **Find All**
5. Output: Excel with StringID and all translations

---

# 4. Core Concepts

## 4.1 StringID, StrOrigin, and Translations

### StringID
Unique identifier for each localized string:
```
UI_MainMenu_Title_001
Quest_Chapter1_Dialog_042
Item_Weapon_Sword_Name
```

### StrOrigin
Original Korean source text:
```xml
<LocStr StringId="UI_Button_OK" StrOrigin="확인" Str="OK" />
```

### Translations
Stored in `languagedata_*.xml` files (17 languages).

## 4.2 SCRIPT Categories

**SCRIPT** categories have StrOrigin = raw Korean text:

| Category | Content Type |
|----------|--------------|
| **Sequencer** | Cutscene dialogue |
| **AIDialog** | NPC AI dialogue |
| **QuestDialog** | Quest conversations |
| **NarrationDialog** | Narrator/voiceover |

**Important:** For SCRIPT strings, use **StringID-Only** match mode.

## 4.3 LOOKUP vs TRANSFER

| Aspect | LOOKUP (Generate) | TRANSFER |
|--------|-------------------|----------|
| **Purpose** | Find translations | Apply corrections |
| **Output** | Excel file | Modified XML files |
| **Operation** | Read-only | Writes to files |
| **Confirmation** | None needed | Required before write |
| **Undo** | N/A | Use Perforce revert |

## 4.4 File Structure

### LOC Folder (Target for TRANSFER)
```
loc/
├── languagedata_eng.xml
├── languagedata_fre.xml
├── languagedata_ger.xml
└── ... (17 files)
```

### Export Folder (Source for LOOKUP)
```
export__/
├── Sequencer/
├── UI/
├── Items/
└── Quest/
```

---

# 5. LOOKUP Features

## 5.1 Generate Button

The **Generate** button performs read-only translation lookup:

```
Input (Korean text) → Match against stringtables → Output Excel
```

### Input Modes

| Mode | Description |
|------|-------------|
| **File** | Single Excel or XML file |
| **Folder** | All files in folder (recursive) |

### Format Modes

| Format | Extensions | Use Case |
|--------|------------|----------|
| **Excel** | .xlsx, .xls | Korean text in Column A |
| **XML** | .xml, .loc.xml | LocStr elements with StringId |

### Mixed File Support (Folder Mode)

When using Folder mode, QuickTranslate automatically detects and processes:
- All `.xlsx` and `.xls` files
- All `.xml` files

Files are combined into a single output.

## 5.2 StringID Lookup

Direct lookup of any StringID:

1. Enter StringID in the text field
2. Click **Lookup**
3. Get Excel with all 17 translations

**Output columns:** StringID | ENG | FRE | GER | SPA | ...

## 5.3 Reverse Lookup

Find StringID from text in ANY language:

1. Create text file with strings (one per line)
2. Click **Browse** → select file
3. Click **Find All**

**Auto-detection:** Identifies which language each input string is in.

**Output columns:** Input | KOR | ENG | FRE | GER | ...

## 5.4 ToSubmit Integration

Enable the checkbox to include files from `ToSubmit/` folder:

- Automatically loads correction files staged for submission
- Combines with selected source file/folder
- Useful for batch processing pending corrections

---

# 6. TRANSFER Features

## 6.1 TRANSFER Button

The **TRANSFER** button writes corrections to target XML files:

```
Corrections (Excel/XML) → Match in target → WRITE to languagedata_*.xml
```

### Important Notes

1. **Confirmation Required:** Dialog asks for confirmation before writing
2. **Backup Recommended:** Use Perforce or manual backup before transfer
3. **Target Default:** LOC folder from settings.json

## 6.2 Source Formats

### Excel Corrections

Required columns (auto-detected, case-insensitive):
- **StringID** (or StringId, string_id)
- **StrOrigin** (or Str_Origin, str_origin)
- **Correction** (or correction)

Example:
| StringID | StrOrigin | Correction |
|----------|-----------|------------|
| UI_001 | 확인 버튼 | OK Button |

### XML Corrections

Standard LocStr format:
```xml
<LocStr StringId="UI_001" StrOrigin="확인 버튼" Str="OK Button" />
```

**Case-insensitive attributes:** StringId, StringID, stringid, STRINGID all work.

## 6.3 Transfer Modes

### File Mode
- Source: Single Excel or XML file
- Target: LOC folder or specific languagedata_*.xml

**Language Detection:** Extracts language code from filename:
- `corrections_ENG.xlsx` → `languagedata_eng.xml`
- `languagedata_FRE.xml` → `languagedata_fre.xml`

### Folder Mode
- Source: Folder with multiple Excel/XML files
- Target: LOC folder

**Batch Processing:** All corrections applied to matching language files.

## 6.4 Match Modes for TRANSFER

### STRICT Mode (Recommended)
Matches by **both** StringID AND StrOrigin:
- Most precise - no false positives
- Requires StrOrigin in corrections
- Use for: General corrections

### StringID-Only Mode
Matches by StringID only:
- For SCRIPT categories (Sequencer, Dialog)
- StrOrigin not required for matching
- Use for: Dialogue corrections

## 6.5 Transfer Report

After transfer, the log shows:

```
═══════════════════════════════════════════
     TRANSFER REPORT
═══════════════════════════════════════════
● languagedata_eng.xml: 45 updated
● languagedata_fre.xml: 42 updated
○ languagedata_ger.xml: 0 updated (no matches)

Summary:
  Matched: 150
  Updated: 87
  Not Found: 12
═══════════════════════════════════════════
```

**Symbols:**
- ● = Updates applied
- ○ = No matches found
- × = Error during processing

## 6.6 Folder Analysis

When you browse a **Source** or **Target** folder, QuickTranslate automatically analyzes the folder contents and prints a detailed summary to both the terminal and the GUI log.

### What It Shows

| Information | Description |
|-------------|-------------|
| **File count** | Total items, XML files, Excel files, other files, subdirectories |
| **Languagedata index** | Numbered table of all `languagedata_*.xml` files found |
| **Language codes** | Detected language code for each file (ENG, FRE, GER, etc.) |
| **File sizes** | Human-readable size for each file |
| **Eligibility check** | Whether the folder is eligible for TRANSFER operations |

### Terminal Output Example

```
============================================================
  SOURCE FOLDER ANALYSIS
============================================================
  Path: D:\locmerge\source
  Total items: 14 (12 XML, 0 Excel, 2 other, 0 subdirs)
------------------------------------------------------------

  LANGUAGEDATA FILES (12 found):
  #    Filename                            Lang     Size
  ---- ----------------------------------- -------- ----------
  1    languagedata_ENG.xml                ENG      4.2 MB
  2    languagedata_FRE.xml                FRE      3.8 MB
  3    languagedata_GER.xml                GER      3.9 MB
  ...

  VALIDATION:
  [OK] Eligible for TRANSFER (12 language files)
  [OK] Languages: ENG, FRE, GER, ...
============================================================
```

### GUI Log Summary

The GUI log area shows a condensed version:
- Folder path
- Number of languagedata files found
- List of detected languages
- Eligibility status

### Error Handling

If the folder cannot be fully analyzed (e.g., permission errors, unreadable files), the analysis gracefully reports the issue without blocking the operation.

## 6.7 Cross-Match Analysis

Before a **TRANSFER** executes in **Folder mode**, QuickTranslate performs a cross-match analysis. This prints a detailed pairing report to the terminal showing which source correction files will be applied to which target languagedata files.

### What It Shows

| Information | Description |
|-------------|-------------|
| **Source count** | Number of languagedata files in the source folder |
| **Target count** | Number of languagedata files in the target folder |
| **Matched pairs** | Source-to-target file pairings by language code |
| **Unmatched files** | Any files that could not be paired |

### Terminal Output Example

```
============================================================
  TRANSFER CROSS-MATCH ANALYSIS
============================================================
  Source: 12 languagedata files
  Target: 12 languagedata files
  Matched: 12 pairs
------------------------------------------------------------

  MATCHED PAIRS (12):
    languagedata_eng.xml                --> languagedata_ENG.xml
    languagedata_fre.xml                --> languagedata_FRE.xml
    languagedata_ger.xml                --> languagedata_GER.xml
    languagedata_spa.xml                --> languagedata_SPA.xml
    languagedata_por.xml                --> languagedata_POR.xml
    languagedata_ita.xml                --> languagedata_ITA.xml
    languagedata_rus.xml                --> languagedata_RUS.xml
    languagedata_tur.xml                --> languagedata_TUR.xml
    languagedata_pol.xml                --> languagedata_POL.xml
    languagedata_jpn.xml                --> languagedata_JPN.xml
    languagedata_zho-cn.xml             --> languagedata_ZHO-CN.xml
    languagedata_zho-tw.xml             --> languagedata_ZHO-TW.xml
============================================================
```

### Why This Matters

The cross-match analysis helps verify that:
1. All expected language files are present in both source and target
2. File naming is consistent so pairings are correct
3. No corrections will be silently skipped due to missing target files

If any source files have no matching target, or vice versa, they are listed under an **UNMATCHED** section so you can investigate before the transfer proceeds.

---

# 7. Match Types

## 7.1 Substring Match (Original)

**How it works:**
```
Input: "시작"
Finds: Any string containing "시작"
  - "게임 시작하기" ✓
  - "시작 버튼" ✓
  - "새로 시작" ✓
```

| Pros | Cons |
|------|------|
| Flexible | May return multiple matches |
| Finds partial matches | Less precise |

**Best for:** Finding strings when you only have partial Korean text

**Button:** Generate (LOOKUP only)

## 7.2 StringID-Only (SCRIPT)

**How it works:**
1. Reads StringIDs from input
2. Filters to SCRIPT categories ONLY (Sequencer, AIDialog, QuestDialog, NarrationDialog)
3. Returns/applies translations for matching StringIDs

**Status output:** "SCRIPT filter: 150 kept, 23 skipped"

**Best for:** Processing Sequencer/Dialog corrections

**Buttons:** Generate (LOOKUP) and TRANSFER

## 7.3 StringID + StrOrigin (STRICT)

**How it works:**
```
Input: StringID="UI_001", StrOrigin="확인"
Matches: ONLY if both StringID AND StrOrigin match exactly
```

| Pros | Cons |
|------|------|
| Most precise | Requires both fields |
| No false positives | More input data needed |
| Handles reused StringIDs | - |

**Best for:** Verifying corrections with 100% certainty

**Buttons:** Generate (LOOKUP) and TRANSFER

## 7.4 Special Key Match

**How it works:**
- Custom composite key from multiple fields
- Configure key fields in the UI (comma-separated)
- Default: `string_id,category`

**Best for:** Advanced matching scenarios

**Buttons:** Generate (LOOKUP) only

---

# 8. Workflows

## 8.1 LOOKUP: Find Translations

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Create    │───→│   Generate  │───→│   Review    │
│   Excel     │    │   (LOOKUP)  │    │   Output    │
└─────────────┘    └─────────────┘    └─────────────┘
```

1. Create Excel with Korean text in Column A
2. Set Format: Excel, Mode: File, Match Type: Substring
3. Browse to file → Click **Generate**
4. Open output Excel

## 8.2 LOOKUP: Process SCRIPT Corrections

1. Set Format: XML
2. Set Match Type: StringID-Only (SCRIPT)
3. Browse to XML file
4. Click **Generate**

**Output:** Only SCRIPT categories included

## 8.3 LOOKUP: Verify with Strict Matching

1. Set Format: XML
2. Set Match Type: StringID + StrOrigin (STRICT)
3. Browse to Source XML
4. Browse to Target folder
5. Click **Generate**

**Output:** Only verified matches

## 8.4 TRANSFER: Apply Excel Corrections

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Corrections│───→│  TRANSFER   │───→│   Verify    │
│   Excel     │    │   Button    │    │   XML Files │
└─────────────┘    └─────────────┘    └─────────────┘
```

1. Prepare corrections Excel (StringID, StrOrigin, Correction)
2. Set Format: Excel, Mode: File
3. Set Match Type: STRICT (recommended)
4. Source: Browse to corrections file
5. Target: Browse to LOC folder
6. Click **TRANSFER** → Confirm
7. Check log for results

## 8.5 TRANSFER: Batch Apply from Folder

1. Set Mode: Folder
2. Set Match Type: STRICT or StringID-Only
3. Source: Browse to folder with corrections
4. Target: LOC folder
5. Click **TRANSFER** → Confirm
6. View transfer report

## 8.6 TRANSFER: SCRIPT Dialogue Corrections

For Sequencer/Dialog corrections:

1. Set Match Type: StringID-Only (SCRIPT)
2. Source: Corrections file
3. Target: LOC folder
4. Click **TRANSFER**

**Note:** Only SCRIPT categories are processed; others skipped.

---

# 9. Output Files

## 9.1 LOOKUP Outputs

All saved to: `<app_folder>/Output/`

### Translation Output
**Filename:** `QuickTranslate_YYYYMMDD_HHMMSS.xlsx`

| Column | Content |
|--------|---------|
| A | KOR (Input) |
| B | ENG |
| C-Q | Other languages... |

**Multiple matches:** Formatted as numbered list
```
1. Translation option 1
2. Translation option 2
```

### StringID Lookup Output
**Filename:** `StringID_<ID>_YYYYMMDD_HHMMSS.xlsx`

Single row with StringID and all translations.

### Reverse Lookup Output
**Filename:** `ReverseLookup_YYYYMMDD_HHMMSS.xlsx`

| Input | KOR | ENG | FRE | GER |
|-------|-----|-----|-----|-----|
| Start Game | 게임 시작 | Start Game | Démarrer | Spiel starten |

**Special values:**
- `NOT FOUND` - No matching StringID
- `NO TRANSLATION` - Translation empty

## 9.2 TRANSFER Outputs

**Output:** Modified `languagedata_*.xml` files in target folder

**Log Report:** Shown in application log area with:
- Files processed
- Matches found
- Updates applied
- Errors encountered

---

# 10. Troubleshooting

## 10.1 LOOKUP Issues

### "LOC folder not found"
**Cause:** Perforce not synced or path incorrect
**Solution:**
1. Run `p4 sync` on stringtable folder
2. Or update `settings.json` with correct path

### "Sequencer folder not found"
**Cause:** Export folder not synced
**Solution:**
```
p4 sync //depot/cd/mainline/resource/GameData/stringtable/export__/...
```

### "No input data found"
**Cause:** Empty file or wrong format
**Solution:**
- Excel: Ensure data is in Column A
- XML: Ensure file has `<LocStr>` elements

### "StringID not found"
**Cause:** StringID doesn't exist in current branch
**Solution:**
1. Check spelling (case-sensitive)
2. Try different branch

## 10.2 TRANSFER Issues

### "Source not found"
**Cause:** File path incorrect
**Solution:** Use Browse button to select file

### "Target folder not found"
**Cause:** LOC folder path incorrect
**Solution:** Update `settings.json` or browse to correct folder

### "0 matches found"
**Causes:**
1. StringID not in target files
2. StrOrigin doesn't match (STRICT mode)
3. Category not in SCRIPT set (StringID-Only mode)

**Solutions:**
1. Verify StringIDs exist in target
2. Check StrOrigin text matches exactly
3. Use STRICT mode for non-SCRIPT strings

### "Transfer completed but file unchanged"
**Cause:** Corrections already applied or no differences
**Solution:** This is normal if translations are identical

## 10.3 Performance Tips

| Scenario | Tip |
|----------|-----|
| First run slow | Building index. Subsequent runs faster |
| Large corrections file | Use Folder mode for batching |
| Memory usage | Close other apps for 1000+ corrections |

---

# 11. Reference

## 11.1 Supported Languages

| Code | Display | Language |
|------|---------|----------|
| `kor` | KOR | Korean (Source) |
| `eng` | ENG | English |
| `fre` | FRE | French |
| `ger` | GER | German |
| `spa` | SPA | Spanish |
| `por` | POR | Portuguese |
| `ita` | ITA | Italian |
| `rus` | RUS | Russian |
| `tur` | TUR | Turkish |
| `pol` | POL | Polish |
| `zho-cn` | ZHO-CN | Chinese (Simplified) |
| `zho-tw` | ZHO-TW | Chinese (Traditional) |
| `jpn` | JPN | Japanese |
| `tha` | THA | Thai |
| `vie` | VIE | Vietnamese |
| `ind` | IND | Indonesian |
| `msa` | MSA | Malay |

## 11.2 Supported File Formats

| Format | Extensions | Library |
|--------|------------|---------|
| Excel | `.xlsx`, `.xls` | openpyxl |
| XML | `.xml`, `.loc.xml` | lxml |
| Text | `.txt` | built-in |

## 11.3 SCRIPT Categories

| Category | Description |
|----------|-------------|
| Sequencer | Cutscene/cinematic dialogue |
| AIDialog | NPC AI-triggered dialogue |
| QuestDialog | Quest conversation text |
| NarrationDialog | Narrator/voiceover text |

## 11.4 Default Paths

| Path | Default Value |
|------|---------------|
| LOC Folder | `F:\perforce\cd\mainline\resource\GameData\stringtable\loc` |
| Export Folder | `F:\perforce\cd\mainline\resource\GameData\stringtable\export__` |
| Output Folder | `<app_folder>\Output` |
| ToSubmit Folder | `<app_folder>\ToSubmit` |
| Settings File | `<app_folder>\settings.json` |

## 11.5 Excel Column Detection

QuickTranslate auto-detects these column names (case-insensitive):

| Column Purpose | Accepted Names |
|----------------|----------------|
| StringID | StringID, StringId, string_id, STRINGID |
| StrOrigin | StrOrigin, Str_Origin, str_origin, STRORIGIN |
| Correction | Correction, correction, Str, str |

## 11.6 Command Line Options

```bash
python main.py              # Launch GUI
python main.py --verbose    # Launch with debug logging
python main.py --version    # Show version
python main.py --help       # Show help
```

## 11.7 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt+G` | Generate |
| `Alt+T` | Transfer |
| `Alt+C` | Clear fields |
| `Alt+X` | Exit |

---

# 12. Appendix

## 12.1 Glossary

| Term | Definition |
|------|------------|
| **StringID** | Unique identifier for a localized string |
| **StrOrigin** | Original Korean source text |
| **Str** | Translated text for a language |
| **LocStr** | XML element containing string data |
| **SCRIPT** | Categories with raw Korean StrOrigin |
| **LOC folder** | Contains `languagedata_*.xml` files |
| **LOOKUP** | Read-only translation search (Generate button) |
| **TRANSFER** | Write corrections to XML files (TRANSFER button) |

## 12.2 XML Element Structure

```xml
<LocStr
    StringId="UI_Button_001"
    StrOrigin="확인 버튼"
    Str="OK Button"
    Category="UI"
/>
```

| Attribute | Required | Description |
|-----------|----------|-------------|
| StringId | Yes | Unique identifier |
| StrOrigin | No | Korean source text |
| Str | Yes | Translation text |
| Category | No | String category |

## 12.3 Changelog

### Version 3.1.0 (February 2026)

**New Features:**
- Folder analysis on browse: detailed terminal output with file indexing, language identification, eligibility check
- Cross-match analysis before TRANSFER: shows source-to-target file pairing
- Window now vertically resizable (900x1000, min 900x900)

**Bug Fixes:**
- Fixed TRANSFER button being invisible due to window too small (900x850)
- Added error handling for folder analysis (permission errors, unreadable files)

### Version 3.0.0 (February 2026)

**New Features:**
- Added TRANSFER functionality - write corrections to XML files
- Added transfer_file_to_file and transfer_folder_to_folder
- Added transfer report with detailed statistics
- Added mixed Excel/XML support in Folder mode
- Added canonical text normalization (text_utils.py)

**Improvements:**
- Unified normalization across all modules
- Case-insensitive XML attribute reading
- Better column detection in Excel files
- Resource leak fixes in Excel operations
- Improved error handling and logging

**Technical:**
- Created core/text_utils.py as single source of truth
- Created core/xml_transfer.py for transfer operations
- Fixed newline order bug in XML parsing
- Imported SCRIPT_CATEGORIES from config.py

### Version 2.0.0 (February 2026)

**New Features:**
- Added StringID-Only match type for SCRIPT strings
- Added Strict match type (StringID + StrOrigin)
- Added Special Key match type
- Added Folder mode (recursive processing)
- Added XML format input support
- Added Reverse Lookup feature
- Added branch selection (mainline/cd_lambda)
- Added ToSubmit folder integration

**Improvements:**
- Modular codebase (main.py + core/ + gui/ + utils/)
- Better XML parsing with lxml recovery mode
- Progress bar and detailed status updates

### Version 1.0.0 (Initial Release)

- Basic substring matching
- Excel input/output
- StringID lookup
- Multi-language support (17 languages)

---

## 12.4 Support

**Issues & Feedback:**
- GitHub Issues: [LocalizationTools Repository](https://github.com/NeilVibe/LocalizationTools/issues)

**Documentation:**
- This User Guide: `docs/USER_GUIDE.md`

---

<div align="center">

**QuickTranslate** | Version 3.1.0 | LocaNext Project

*Lookup & Transfer - Two Tools in One*

</div>
