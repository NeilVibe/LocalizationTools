# Translation Bank v1.0 - User Guide

**Translation Recovery Tool for XML Localization Files**

> Recovers translations when StringId or StrOrigin changes in XML files. Uses a 3-level unique key system for reliable matching even when IDs change.

---

## Table of Contents

1. [Quick Start](#-quick-start)
2. [Installation](#-installation)
3. [Complete Workflow Overview](#-complete-workflow-overview)
4. [The Three-Level Key System](#-the-three-level-key-system)
5. [GUI Mode](#-gui-mode)
6. [Creating a Translation Bank](#-creating-a-translation-bank)
7. [Transferring Translations](#-transferring-translations)
8. [Understanding the Transfer Report](#-understanding-the-transfer-report)
9. [Configuration](#-configuration)
10. [Troubleshooting](#-troubleshooting)
11. [Reference](#-reference)

---

## Quick Start

### 30-Second Workflow

```
1. Double-click TranslationBank.exe
2. Select SOURCE folder (translated XML files)
3. Click "Generate Bank" → Creates .pkl file
4. Select TARGET folder (new XML files needing translations)
5. Click "Transfer" → Translations applied!
6. Review the transfer report for HIT/MISS statistics
```

### Output Files

```
TranslationBank/
├── TranslationBank.exe           # Main application
├── config.py                     # Drive configuration
└── [your_bank_name].pkl          # Generated bank file (fast, binary)
    └── [your_bank_name].json     # Optional: human-readable (for debugging)
```

---

## Installation

### Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | Windows 10/11 |
| **Disk Space** | ~30 MB |
| **RAM** | 4 GB minimum (8 GB for 150k+ entries) |
| **Python** | Not required (bundled in .exe) |

### Step 1: Download

Download the latest `TranslationBank_vX.X.X_Setup.exe` from GitHub Releases.

### Step 2: Install

1. Run the installer
2. Choose installation folder (default: Desktop)
3. Click **Install**

### Step 3: Launch

Double-click `TranslationBank.exe` to start.

---

## Complete Workflow Overview

### The Big Picture

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     TRANSLATION BANK - COMPLETE WORKFLOW                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐║
║   │  OLD TRANSLATED │         │  TRANSLATION    │         │  NEW XML FILES  │║
║   │  XML FILES      │────────▶│  BANK (.pkl)    │────────▶│  WITH MISSING   │║
║   │                 │ CREATE  │                 │ TRANSFER│  TRANSLATIONS   │║
║   │  (Has Str attr) │ BANK    │  150k+ entries  │         │                 │║
║   └─────────────────┘         └─────────────────┘         └─────────────────┘║
║                                                                               ║
║   ═══════════════════════════════════════════════════════════════════════════ ║
║                                                                               ║
║   STEP 1: CREATE BANK                    STEP 2: TRANSFER                     ║
║   ┌─────────────────────────────┐       ┌─────────────────────────────┐      ║
║   │ Input:  Translated XMLs     │       │ Input:  Bank + Target XMLs  │      ║
║   │ Output: translation_bank.pkl│       │ Output: Updated XMLs        │      ║
║   │                             │       │         + Transfer Report   │      ║
║   │ Extracts:                   │       │                             │      ║
║   │ • StringId                  │       │ Matches using 3 levels:     │      ║
║   │ • StrOrigin (Korean)        │       │ 1. StrOrigin + StringId     │      ║
║   │ • Str (Translation)         │       │ 2. StringId only            │      ║
║   │ • Adjacent context          │       │ 3. Context-aware (neighbors)│      ║
║   └─────────────────────────────┘       └─────────────────────────────┘      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### When to Use Translation Bank

| Scenario | Use Translation Bank? |
|----------|----------------------|
| StringId changed in new XML | **YES** - Level 2 or 3 will match |
| StrOrigin (Korean) was edited | **YES** - Level 2 will match by ID |
| Both StringId AND StrOrigin changed | **YES** - Level 3 uses context |
| Completely new string added | **NO** - Nothing to transfer |
| File structure reorganized | **YES** - Still matches by content |

---

## The Three-Level Key System

### Why Three Levels?

Traditional translation transfer breaks when IDs change. Translation Bank solves this with fallback matching:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         THREE-LEVEL KEY SYSTEM                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   LEVEL 1: StrOrigin + StringId (Most Reliable)                              ║
║   ═══════════════════════════════════════════════                             ║
║   Key = SHA256( "Korean text here" + "12345" )                               ║
║                                                                               ║
║   ✓ Use when: Both Korean text AND ID match exactly                          ║
║   ✓ Reliability: 100% - definitely the same string                           ║
║                                                                               ║
║   ─────────────────────────────────────────────────────────────────────────── ║
║                                                                               ║
║   LEVEL 2: StringId Only (Fallback)                                          ║
║   ══════════════════════════════════                                          ║
║   Key = "12345" (normalized)                                                  ║
║                                                                               ║
║   ✓ Use when: Korean text changed but StringId still exists                  ║
║   ✓ Reliability: High - same ID usually means same string                    ║
║   ⚠ Caution: May return multiple matches if ID reused                        ║
║                                                                               ║
║   ─────────────────────────────────────────────────────────────────────────── ║
║                                                                               ║
║   LEVEL 3: Context-Aware (Last Resort)                                       ║
║   ═════════════════════════════════════                                       ║
║   Key = SHA256( StrOrigin + Filename + Prev_Context + Next_Context )         ║
║                                                                               ║
║   ✓ Use when: Both ID and Korean text changed                                ║
║   ✓ Reliability: Good - neighbors confirm position                           ║
║   ✓ How it works:                                                            ║
║                                                                               ║
║     Position N-1:  ┌─────────────┐                                           ║
║     (Previous)     │ String A    │──┐                                        ║
║                    │ ID: 111     │  │                                        ║
║                    └─────────────┘  │                                        ║
║                                     │  Context                               ║
║     Position N:    ┌─────────────┐  │  includes                              ║
║     (Target)       │ String B    │◀─┤  neighbors                             ║
║                    │ ID: ???     │  │                                        ║
║                    └─────────────┘  │                                        ║
║                                     │                                        ║
║     Position N+1:  ┌─────────────┐  │                                        ║
║     (Next)         │ String C    │──┘                                        ║
║                    │ ID: 333     │                                           ║
║                    └─────────────┘                                           ║
║                                                                               ║
║   If neighbors A and C match, B is confirmed even with changed ID!           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Fallback Chain

```
Target Entry → Try Level 1 → HIT? → Use translation
                    │
                    ↓ MISS
              Try Level 2 → HIT? → Use translation
                    │
                    ↓ MISS
              Try Level 3 → HIT? → Use translation
                    │
                    ↓ MISS
              Report as MISS (new string, needs translation)
```

---

## GUI Mode

### Main Window Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         Translation Bank v1.0                               │
├────────────────────────────────────────────────────────────────────────────┤
│  Mode                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  (○) File    (●) Folder (Recursive)                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────────────┤
│  1. Create Bank                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Source:  [D:\LanguageData_Translated________________] [Browse]     │   │
│  │                                                                      │   │
│  │  [ ] Export as JSON (slower, for debugging)                         │   │
│  │                                                                      │   │
│  │                    [  Generate Bank  ]                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────────────┤
│  2. Transfer Translations                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Bank:    [D:\TranslationBanks\my_bank.pkl____________] [Browse]    │   │
│  │  Target:  [D:\LanguageData_New________________________] [Browse]    │   │
│  │                                                                      │   │
│  │                    [    Transfer    ]                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────────────┤
│  Console Output                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Building bank from: D:\LanguageData_Translated                     │   │
│  │  Processing: LanguageData_eng.xml                                   │   │
│  │  Processing: LanguageData_fre.xml                                   │   │
│  │  ...                                                                │   │
│  │  Bank built: 152,347 entries from 24 files                          │   │
│  │    Level 1 keys: 152,347                                            │   │
│  │    Level 2 keys: 148,920                                            │   │
│  │    Level 3 keys: 152,347                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────────────┤
│  [████████████████████████████████████████████] 100%        Status: Ready  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Mode Selection

| Mode | Description |
|------|-------------|
| **File** | Process single XML file |
| **Folder (Recursive)** | Process all XML files in folder and subfolders |

---

## Creating a Translation Bank

### Step-by-Step Guide

#### Step 1: Select Source

Click **Browse** next to Source and select:
- **File mode**: Single translated XML file
- **Folder mode**: Folder containing translated XML files

#### Step 2: Choose Format

| Format | When to Use |
|--------|-------------|
| **PKL (default)** | Normal usage - fast load/save for 150k+ entries |
| **JSON (checkbox)** | Debugging - human-readable, can inspect contents |

#### Step 3: Generate

1. Click **Generate Bank**
2. Choose save location
3. Wait for processing (progress bar shows status)
4. Bank file is created!

### What Gets Extracted

For each `<LocStr>` element with a translation:

```xml
<LocStr StringId="12345" StrOrigin="한국어 텍스트" Str="English translation"/>
```

Extracted data:
- `string_id`: "12345"
- `str_origin`: "한국어 텍스트"
- `str_translated`: "English translation"
- `filename`: "LanguageData_eng.xml"
- `position`: Element position in file
- `prev_context`: Previous entry's Korean + ID
- `next_context`: Next entry's Korean + ID

---

## Transferring Translations

### Step-by-Step Guide

#### Step 1: Load Bank

Click **Browse** next to Bank and select your `.pkl` or `.json` bank file.

#### Step 2: Select Target

Click **Browse** next to Target and select:
- **File mode**: Single XML file needing translations
- **Folder mode**: Folder containing XML files

#### Step 3: Transfer

1. Click **Transfer**
2. Choose output location
3. Wait for processing
4. Review transfer report in console

### Transfer Logic

For each target entry with empty `Str=""`:

1. Generate Level 1 key from StrOrigin + StringId
2. Look up in bank → Found? Use translation
3. If not found, try Level 2 (StringId only)
4. If not found, try Level 3 (context-aware)
5. If still not found, mark as MISS

---

## Understanding the Transfer Report

### Sample Report

```
══════════════════════════════════════════════════════════════════════════
                  TRANSLATION BANK TRANSFER REPORT
══════════════════════════════════════════════════════════════════════════

Bank:   D:\TranslationBanks\my_bank.pkl
Target: D:\LanguageData_New\

──────────────────────────────────────────────────────────────────────────
                         MATCH SUMMARY
──────────────────────────────────────────────────────────────────────────
Total Target Entries:         10,234
──────────────────────────────────────────────────────────────────────────
HIT  (Total):                  9,567    ( 93.5%)
  Level 1 (StrOrigin+ID):      7,890    ( 77.1%)  ← Most reliable matches
  Level 2 (ID only):           1,432    ( 14.0%)  ← ID matched, Korean changed
  Level 3 (Context):             245    (  2.4%)  ← Both changed, neighbors matched
──────────────────────────────────────────────────────────────────────────
MISS:                            667    (  6.5%)  ← New strings, need translation
══════════════════════════════════════════════════════════════════════════

Files processed: 24
Files modified:  18
```

### Interpreting Results

| Metric | Meaning | Action |
|--------|---------|--------|
| **Level 1 HIT** | Perfect match | None needed |
| **Level 2 HIT** | Korean text was edited | Review translation still fits |
| **Level 3 HIT** | Both ID and Korean changed | Double-check match is correct |
| **MISS** | No match found | Needs manual translation |

### Expected Hit Rates

| Scenario | Expected Rate |
|----------|---------------|
| Minor XML update | 95-99% |
| ID regeneration | 85-95% |
| Major restructure | 70-90% |
| New content batch | 50-80% |

---

## Configuration

### config.py Settings

```python
# Drive letters
DATA_DRIVE = "D:"

# Default paths
DEFAULT_SOURCE_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_Translated")
DEFAULT_BANK_OUTPUT = Path(f"{DATA_DRIVE}/TranslationBanks")
DEFAULT_TARGET_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_New")

# Bank format (.pkl for speed, .json for debugging)
BANK_EXTENSION = ".pkl"

# XML element configuration
LOCSTR_ELEMENT = "LocStr"
ATTR_STRING_ID = "StringId"
ATTR_STR_ORIGIN = "StrOrigin"
ATTR_STR = "Str"
```

### Customizing for Your Project

If your XML uses different attribute names:

```python
# Example: Different attribute names
ATTR_STRING_ID = "ID"           # Instead of "StringId"
ATTR_STR_ORIGIN = "Source"      # Instead of "StrOrigin"
ATTR_STR = "Translation"        # Instead of "Str"
```

---

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Low hit rate (<70%) | Bank doesn't contain source translations | Recreate bank with correct source files |
| XML parse error | Malformed XML file | Check file encoding (UTF-8), fix invalid characters |
| Slow bank loading | Using JSON format | Use PKL format (default) for 150k+ entries |
| Level 3 mismatches | File structure changed significantly | Review Level 3 hits manually |
| Out of memory | Bank too large | Process in batches, increase RAM |

### Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| "Failed to load bank" | Bank file corrupted or wrong format | Regenerate bank |
| "Could not parse: X.xml" | XML syntax error in file | Fix XML syntax |
| "No entries needed translation" | All Str attributes already filled | Check target files |

### Performance Tips

| Tip | Impact |
|-----|--------|
| Use PKL format | 10x faster load for large banks |
| Process by folder | Better context matching |
| Close other apps | More RAM for large banks |

---

## Reference

### Supported XML Format

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="12345" StrOrigin="한국어" Str="English"/>
  <LocStr StringId="12346" StrOrigin="테스트" Str="Test"/>
</LanguageData>
```

### Bank File Structure

```json
{
  "metadata": {
    "created": "2026-01-30T12:00:00",
    "source_path": "D:/LanguageData_Translated",
    "entry_count": 152347
  },
  "entries": [
    {
      "string_id": "12345",
      "str_origin": "한국어",
      "str_translated": "English",
      "filename": "LanguageData_eng.xml",
      "position": 0,
      "prev_context": "|",
      "next_context": "테스트|12346"
    }
  ],
  "indices": {
    "level1": {"sha256_hash": 0},
    "level2": {"12345": [0]},
    "level3": {"sha256_hash": 0}
  }
}
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Execute current action |
| `Ctrl+O` | Open/Browse |
| `Ctrl+Q` | Quit |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-30 | Initial release with 3-level key system |

---

*Translation Bank - Never lose translations again!*
