# QuickSearch v1.0.0 - User Guide

**Translation Search & QA Tool for Localization**

Version: 1.0.0 | Author: Neil

---

## Table of Contents

1. [Quick Start - Dictionary Search](#1-quick-start---dictionary-search)
2. [LINE CHECK - Translation Consistency QA](#2-line-check---translation-consistency-qa)
3. [TERM CHECK - Glossary Term Validation](#3-term-check---glossary-term-validation)
4. [ENG BASE vs KR BASE (NEW!)](#4-eng-base-vs-kr-base-new)
5. [Additional Features](#5-additional-features)
6. [Configuration Options](#6-configuration-options)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start - Dictionary Search

This section covers creating a searchable dictionary from XML/TXT files.

### Step-by-Step Workflow

#### Step 1: Launch QuickSearch

Double-click `QuickSearch.exe` (or run `python main.py`).

The main window opens with two tabs:
- **Quick Search** - Search functionality (default)
- **Glossary Checker** - QA tools (LINE CHECK, TERM CHECK)

#### Step 2: Create Dictionary

1. Click the **"Create Dictionary"** button
2. Select **Game** (BDO, BDM, BDC, CD)
3. Select **Language** (DE, EN, FR, IT, etc.)
4. Click **"Create"**
5. Select your XML/TXT files

#### Step 3: Load and Search

1. Click **"Load Dictionary"**
2. Select the dictionary you created
3. Type your search term
4. Click **"Search"** or press Enter

### Search Options

| Option | Description |
|--------|-------------|
| **Contains** | Find partial matches (default) |
| **Exact Match** | Find exact string matches only |
| **One Line** | Standard single-term search |
| **Multi Line** | Search multiple terms at once (one per line) |

---

## 2. LINE CHECK - Translation Consistency QA

LINE CHECK identifies inconsistent translations where the same source text has been translated differently.

### What LINE CHECK Does

- Scans all translation entries in your files
- Groups entries by source text
- Flags entries where the same source has multiple different translations
- Generates a **clean report** (no filename clutter)

### New Clean Output Format

```
source_text_1
  translation_A
  translation_B

source_text_2
  translation_X
  translation_Y
  translation_Z
```

### How to Use LINE CHECK

#### Step 1: Open Glossary Checker Tab

Click the **"Glossary Checker"** tab.

#### Step 2: Click LINE CHECK

Click the **"LINE CHECK"** button.

#### Step 3: Configure Source Base (NEW!)

Select your source base mode:

| Mode | Description |
|------|-------------|
| **KR BASE** | Use Korean StrOrigin as source (default) |
| **ENG BASE** | Use English text matched via StringID |

See [Section 4](#4-eng-base-vs-kr-base-new) for details.

#### Step 4: Select Files

- **Source Data**: Select target language XML/TXT files to check
- **English XML** (ENG BASE only): Select English XML for StringID matching

#### Step 5: Configure Options

| Setting | Default | Purpose |
|---------|---------|---------|
| Filter sentences | ON | Skip entries ending with . ? ! |
| Max source length | 15 | Ignore long source text |
| Min occurrence | 2 | Only flag if source appears 2+ times |

#### Step 6: Start Check

Click **"Start Check"** → Save report → Review results.

---

## 3. TERM CHECK - Glossary Term Validation

TERM CHECK finds instances where a glossary term appears in source text but the expected translation is missing.

### What TERM CHECK Does

- Builds glossary from your files (or external glossary)
- Uses **Aho-Corasick algorithm** for fast multi-pattern matching
- Detects terms that appear in source but may have wrong/missing translations
- Generates a **clean report**

### Clean Output Format

```
korean_term // reference_translation
  Source: "full source text containing the term"
  Trans: "translation that's missing the expected term"

another_term // expected_translation
  Source: "another source text"
  Trans: "translation without expected term"
```

### How to Use TERM CHECK

#### Step 1: Click TERM CHECK

In Glossary Checker tab, click **"TERM CHECK"**.

#### Step 2: Configure Source Base

Same as LINE CHECK - choose **KR BASE** or **ENG BASE**.

#### Step 3: Select Check Mode

| Mode | Description |
|------|-------------|
| Source against Self | Build glossary from same files being checked |
| Source against External | Use separate glossary files |

#### Step 4: Start Check

Configure options → Click **"Start Check"** → Review report.

---

## 4. ENG BASE vs KR BASE (NEW!)

**This is the key new feature in v1.0.0.**

### The Problem

By default, consistency checks use Korean StrOrigin as the source. But sometimes you want to check if the **same English text** was translated consistently.

### The Solution

**ENG BASE mode** matches entries by StringID to get English source text.

### How It Works

```
Target XML (e.g., French):
  StringID="1001", StrOrigin="한국어", Str="French translation"

English XML:
  StringID="1001", StrOrigin="한국어", Str="English text"

KR BASE: Groups by "한국어" (Korean)
ENG BASE: Groups by "English text" (matched via StringID)
```

### When to Use Each Mode

| Mode | Use When |
|------|----------|
| **KR BASE** | Checking Korean source consistency (default) |
| **ENG BASE** | Checking English source consistency across languages |

### ENG BASE Workflow

1. Select **ENG BASE** in Source Base section
2. Select **English XML file** (required)
3. Select **Target XML files** (e.g., French, German)
4. Run check

Result: Finds cases where same English source has different translations.

---

## 5. Additional Features

### Reference Dictionary

Load a second dictionary for side-by-side comparison:

1. Click **"REFERENCE OFF"** button
2. Select a reference dictionary
3. Search results now show both translations

### Extract Glossary

Create a glossary from translation files:

1. Go to **Glossary Checker** tab
2. Click **"Extract Glossary"**
3. Select source files
4. Save glossary

### Settings

Click **"Settings"** to customize:

- **Font Family** - Change display font
- **Font Size** - Adjust text size
- **Colors** - Set colors for Korean, Translation, Reference text
- **UI Language** - English or Korean interface

---

## 6. Configuration Options

### Filter Options

| Setting | Default | Purpose |
|---------|---------|---------|
| **Filter sentences** | ON | Skip entries ending with . ? ! |
| **Max source length** | 15 | Ignore source text longer than this |
| **Min occurrence** | 2 | Only include terms appearing 2+ times |
| **Sort method** | Alphabetical | How to sort glossary output |

### Dictionary Storage

Dictionaries are saved in the `dictionaries/` folder:

```
QuickSearch/
├── QuickSearch.exe
├── dictionaries/
│   ├── BDO_DE.pkl
│   ├── CD_FR.pkl
│   └── ...
├── output/
│   └── (reports saved here)
└── qs_settings.json
```

---

## 7. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "No files selected" | Select at least one XML or TXT file |
| Dictionary creation fails | Check XML files are valid LocStr format |
| No search results | Verify dictionary is loaded |
| LINE CHECK finds nothing | Try reducing max length or min occurrence |
| ENG BASE shows no matches | Ensure English XML has matching StringIDs |

### Supported File Formats

**XML Files (LocStr format):**
```xml
<LocStr StringID="12345" StrOrigin="Korean text" Str="Translated text"/>
```

**Tab-delimited TXT/TSV files:**
- Column 6 (index 5): Korean source
- Column 7 (index 6): Translation

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Execute search |
| Ctrl+C | Copy selected text |

---

## Summary

### For Dictionary Search:
1. Create Dictionary → Select Game → Select Language → Choose files
2. Load Dictionary → Search as needed

### For Consistency QA:
1. Glossary Checker tab → LINE CHECK or TERM CHECK
2. Choose **KR BASE** or **ENG BASE**
3. Select files → Start Check → Review report

### New in v1.0.0:
- **ENG BASE / KR BASE** selection for consistency checks
- **Clean output** without filename clutter
- **Modular architecture** for better maintainability

---

*QuickSearch v1.0.0 - Translation Search & QA Tool*
