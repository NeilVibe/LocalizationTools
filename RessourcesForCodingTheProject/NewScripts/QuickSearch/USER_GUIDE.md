# QuickSearch XML v0818 - User Guide

**Translation Search & QA Tool for CD Platform**

Version: 0818 | Author: Neil

---

## Table of Contents

1. [Quick Start - CD Platform XML Search](#1-quick-start---cd-platform-xml-search)
2. [LINE CHECK - Translation Consistency QA](#2-line-check---translation-consistency-qa)
3. [Additional Features](#3-additional-features)
4. [Configuration Options](#4-configuration-options)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Quick Start - CD Platform XML Search

This section covers the most common use case: creating a searchable dictionary from a single CD platform XML file.

### Step-by-Step Workflow

#### Step 1: Launch QuickSearch

Double-click `QuickSearch0818.exe` (or run `QuickSearch0818.py`).

The main window opens with two tabs:
- **Quick Search** - Search functionality (default)
- **Glossary Checker** - QA tools (LINE CHECK, Term Check)

#### Step 2: Create Dictionary

1. Click the **"Create Dictionary"** button in the top-left area

2. The "Create New Dictionary" dialog appears with three sections:

   **Select Game:**
   - BDO
   - BDM
   - BDC
   - **CD** ← Select this for CD platform

   **Select Language:**
   - DE (German)
   - EN (English)
   - FR (French)
   - IT (Italian)
   - PL (Polish)
   - ES/SP (Spanish)
   - PT (Portuguese)
   - RU (Russian)
   - And more...

   **Source Selection Mode:**
   - **Select Files (XML/TXT)** ← Recommended for single file
   - Select Folder (recursive)

3. Select **CD** as the game platform

4. Select your target language (e.g., **DE** for German)

5. Ensure **"Select Files (XML/TXT)"** is selected

6. Click **"Create"**

#### Step 3: Select Your XML File

A file dialog opens. Navigate to your XML file location and select it.

**Supported formats:**
- `.xml` - LocStr XML format
- `.txt` / `.tsv` - Tab-delimited text files

The progress bar shows dictionary creation status.

#### Step 4: Load and Search

1. Once creation completes, click **"Load Dictionary"**

2. Select the dictionary you just created (CD-DE, etc.)

3. Type your search term in the search box

4. Click **"Search"** or press Enter

5. Results display with:
   - Korean source text
   - Translated text
   - StringID (if available)

### Search Options

| Option | Description |
|--------|-------------|
| **Contains** | Find partial matches (default) |
| **Exact Match** | Find exact string matches only |
| **One Line** | Standard single-term search |
| **Multi Line** | Search multiple terms at once |

---

## 2. LINE CHECK - Translation Consistency QA

LINE CHECK identifies inconsistent translations where the same Korean source text has been translated differently in different locations.

### What LINE CHECK Does

- Scans all translation entries in your files
- Groups entries by Korean source text
- Flags entries where the same source has multiple different translations
- Generates a report showing all inconsistencies with file locations

### When to Use LINE CHECK

- Before delivery to find translation inconsistencies
- After merging multiple translators' work
- For quality assurance on large XML files
- To maintain glossary/terminology consistency

### Two Check Modes

| Mode | Description |
|------|-------------|
| **Source against Self** | Check selected files against themselves. Use when you want to find inconsistencies within your own translation files. |
| **Source against External Glossary** | Check selected files against a reference glossary. Use when you have an approved glossary to validate against. |

### Filter Configuration Options

These options control which entries are checked:

| Setting | Default | Purpose |
|---------|---------|---------|
| **Filter sentences** | ON (checked) | Skip entries where source ends with `.` `?` `!` - focuses on terms, not sentences |
| **Max source length** | 15 | Ignore source text longer than this (characters). Reduces noise from long sentences |
| **Min occurrence** | 2 | Only flag if the same source appears 2+ times. Must have multiple instances to detect inconsistency |

### How to Use LINE CHECK

#### Step 1: Open Glossary Checker Tab

Click the **"Glossary Checker"** tab at the top of the window.

#### Step 2: Configure Options (Optional)

In the Options panel on the left:

1. **Filter sentences** - Keep checked to focus on terminology
2. **Max source length** - Adjust if needed (default 15 is good for terms)
3. **Minimum occurrence count** - Keep at 2 (needs at least 2 to compare)

#### Step 3: Click Line Check

Click the **"Line Check"** button in the Buttons panel.

#### Step 4: Configure Check Mode

The "Line Check Configuration" dialog opens:

**Check Mode:**
- Select **"Source against Self"** for internal consistency check
- Select **"Source against External Glossary"** to check against a reference

**Source Data:**
- Click **"Select Files"** to choose XML/TXT files to check
- Or click **"Select Folder"** to check all files in a directory

**External Glossary Data:** (only for External mode)
- Click **"Select Files"** to choose glossary files
- Or click **"Select Folder"** for glossary directory

#### Step 5: Start Check

Click **"Start Check"** button.

You'll be prompted to choose where to save the report file.

#### Step 6: Review Report

The report is saved as a `.txt` file with this format:

```
Korean_source_text_1
  Translation_A    [file1.xml]
  Translation_B    [file2.xml]

Korean_source_text_2
  TranslationX    [main.xml]
  TranslationY    [update.xml]
  TranslationZ    [patch.xml]
```

**How to read the report:**
- Each Korean source text that has inconsistent translations is listed
- Below it, each different translation variant is shown
- The file(s) where each translation appears are listed in brackets

### LINE CHECK Example

**Scenario:** You have a CD platform German translation file. You want to check if any terms were translated inconsistently.

1. Go to **Glossary Checker** tab
2. Click **"Line Check"**
3. Select **"Source against Self"**
4. Click **"Select Files"** → choose your CD German XML file
5. Click **"Start Check"**
6. Save report as `CD_DE_consistency_check.txt`
7. Open report to review inconsistencies

---

## 3. Additional Features

### Reference Dictionary

Load a second dictionary for side-by-side comparison:

1. Click **"REFERENCE OFF"** button
2. Select a reference dictionary
3. Button changes to show reference (e.g., "REFERENCE: CD-EN")
4. Search results now show both main and reference translations

### Term Check

Similar to LINE CHECK but uses Aho-Corasick algorithm for faster term detection:

1. Go to **Glossary Checker** tab
2. Click **"Term Check"**
3. Configure similarly to LINE CHECK
4. Detects terms that appear in source but may have inconsistent translations

### Extract Glossary

Extract a glossary from translation files:

1. Go to **Glossary Checker** tab
2. Click **"Extract Glossary"**
3. Select source files
4. Save extracted glossary as Excel or text file

### Settings

Click **"Settings"** to customize:

- **Font Family** - Change display font
- **Font Size** - Adjust text size
- **Colors** - Set colors for Korean, Translation, and Reference text
- **Styles** - Bold/Italic options
- **UI Language** - English or Korean interface

---

## 4. Configuration Options

### Dictionary Storage

Dictionaries are saved in the application directory:
```
QuickSearch/
├── QuickSearch0818.py
├── BDO/
│   ├── DE/dictionary.pkl
│   └── EN/dictionary.pkl
├── CD/
│   ├── DE/dictionary.pkl
│   └── FR/dictionary.pkl
└── qs_settings.json
```

### Settings File

`qs_settings.json` stores your preferences:
- Font family and size
- Color settings
- Style preferences
- UI language selection

---

## 5. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "No files selected" warning | Make sure to select at least one XML or TXT file |
| Dictionary creation fails | Check that XML files are valid LocStr format |
| No search results | Verify dictionary is loaded (button shows "LOADED: CD-DE") |
| LINE CHECK finds nothing | Try reducing "Max source length" or lowering "Min occurrence" to 1 |

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

**For CD Platform Single XML File Workflow:**

1. Create Dictionary → Select CD → Select Language → Select Files → Choose your XML
2. Load Dictionary → Select CD-[Language]
3. Search as needed

**For Translation Consistency QA:**

1. Glossary Checker tab → Line Check
2. Source against Self → Select Files → Choose XML(s)
3. Start Check → Save report → Review inconsistencies

---

*QuickSearch XML v0818 - Translation Search & QA Tool*
