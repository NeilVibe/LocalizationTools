---
name: quicktranslate-specialist
description: QuickTranslate project specialist. Use when working on the QuickTranslate tool - translation lookup, multi-language search, match types (Substring/StringID-only/Strict/Special Key), or XML/Excel I/O functionality.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# QuickTranslate Specialist

## What Is QuickTranslate?

**QuickTranslate v2.0.0** - A translation lookup tool for finding Korean text translations across 17 languages.

**Location:** `RessourcesForCodingTheProject/NewScripts/QuickTranslate/`

**Core Functions:**
1. **Substring Match** - Find Korean text in StrOrigin
2. **StringID-Only Match** - For SCRIPT strings (Sequencer/Dialog)
3. **Strict Match** - Match by StringID + StrOrigin tuple
4. **StringID Lookup** - Direct lookup of any StringID
5. **Reverse Lookup** - Find StringID from text in any language

**Key Feature:** Multiple match types for different localization workflows

## Project Structure

```
QuickTranslate/
├── main.py                    # Entry point + CLI args
├── config.py                  # Configuration (BRANCHES, MATCHING_MODES)
├── requirements.txt           # Python dependencies
├── QuickTranslate.spec        # PyInstaller spec file
│
├── core/                      # Core functionality
│   ├── __init__.py            # Public exports (21 functions)
│   ├── xml_parser.py          # XML sanitization & parsing
│   ├── korean_detection.py    # Korean text detection
│   ├── indexing.py            # StringID/StrOrigin indexing
│   ├── language_loader.py     # Language file discovery
│   ├── matching.py            # All 4 matching algorithms
│   ├── excel_io.py            # Excel read/write
│   └── xml_io.py              # XML input parsing
│
├── gui/                       # GUI components
│   ├── __init__.py
│   └── app.py                 # 850x750 Tkinter GUI
│
├── utils/                     # Utilities
│   ├── __init__.py
│   └── file_io.py             # File utilities
│
├── docs/                      # Documentation
│   ├── USER_GUIDE.md          # 851-line user guide
│   ├── QuickTranslate_UserGuide.pdf  # Generated PDF (8 pages)
│   ├── style.css              # PDF styling
│   └── generate_pdf.py        # PDF generator
│
└── installer/                 # Inno Setup
    └── QuickTranslate.iss     # Installer script
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| GUI | Tkinter (850x750) |
| XML Parsing | lxml (with fallback to ElementTree) |
| Excel I/O | openpyxl |
| Build | PyInstaller |
| Installer | Inno Setup |

## Match Types

| Mode | Function | Use Case |
|------|----------|----------|
| **Substring** | `find_matches()` | Find Korean text in StrOrigin |
| **StringID-Only** | `find_matches_stringid_only()` | SCRIPT strings (Sequencer/Dialog) |
| **Strict** | `find_matches_strict()` | Match both StringID AND StrOrigin |
| **Special Key** | `find_matches_special_key()` | Custom composite key patterns |

### How StringID-Only Works

```python
# core/matching.py
SCRIPT_CATEGORIES = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

def find_matches_stringid_only(corrections, stringid_to_category):
    """Filter to SCRIPT categories only, match by StringID."""
    script_corrections = []
    for c in corrections:
        category = stringid_to_category.get(c["string_id"], "")
        if category in SCRIPT_CATEGORIES:
            script_corrections.append(c)
    return script_corrections, skipped_count
```

### How Strict Match Works

```python
# core/matching.py
def find_matches_strict(corrections, xml_entries):
    """Match by (StringID, normalized_StrOrigin) tuple."""
    matched = []
    for c in corrections:
        key = (c["string_id"], normalize_text(c["str_origin"]))
        if key in xml_entries:
            matched.append(c)
    return matched, not_found_count
```

## Input/Output Modes

### Format Modes
| Format | Extensions | Read Function |
|--------|------------|---------------|
| **Excel** | .xlsx, .xls | `read_korean_input()`, `read_corrections_from_excel()` |
| **XML** | .xml, .loc.xml | `parse_corrections_from_xml()`, `parse_folder_xml_files()` |

### Input Modes
| Mode | Description |
|------|-------------|
| **File** | Single file processing |
| **Folder** | Recursive folder scanning |

## Key Modules

### core/xml_parser.py

XML sanitization and parsing (battle-tested from LanguageDataExporter):

```python
from core.xml_parser import sanitize_xml_content, parse_xml_file

# Handles: bad entities, control chars, newlines in seg elements
content = sanitize_xml_content(raw_xml)
root = parse_xml_file(xml_path)  # Returns lxml Element
```

### core/matching.py

All matching algorithms:

```python
from core.matching import (
    find_matches,              # Substring search
    find_matches_stringid_only, # SCRIPT filter
    find_matches_strict,       # Tuple match
    find_matches_special_key,  # Custom key
    normalize_text,            # Text normalization
    SCRIPT_CATEGORIES,         # {"Sequencer", "AIDialog", ...}
)
```

### core/language_loader.py

Language file discovery and lookup building:

```python
from core.language_loader import (
    discover_language_files,    # Find languagedata_*.xml
    build_translation_lookup,   # {lang: {sid: translation}}
    build_reverse_lookup,       # {lang: {text: sid}}
    build_stringid_to_category, # {sid: category}
)
```

### core/excel_io.py

Excel operations:

```python
from core.excel_io import (
    read_korean_input,           # Column A Korean text
    read_corrections_from_excel, # StringID/StrOrigin/Correction
    write_output_excel,          # Multi-language output
    write_stringid_lookup_excel, # Single StringID lookup
    write_reverse_lookup_excel,  # Reverse lookup output
)
```

### core/indexing.py

Index building:

```python
from core.indexing import (
    build_sequencer_strorigin_index,  # {StringID: StrOrigin}
    scan_folder_for_strings,          # Recursive XML scan
    scan_folder_for_entries,          # Full entry data
)
```

## Configuration (config.py)

```python
# Match types
MATCHING_MODES = {
    "substring": "Substring Match (original)",
    "stringid_only": "StringID-Only (SCRIPT strings)",
    "strict": "StringID + StrOrigin (Strict)",
    "special_key": "Special Key Match",
}

# SCRIPT categories
SCRIPT_CATEGORIES = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

# Branches
BRANCHES = {
    "mainline": {
        "loc": Path(r"F:\perforce\cd\mainline\...\loc"),
        "export": Path(r"F:\perforce\cd\mainline\...\export__"),
    },
    "cd_lambda": {...},
}

# Languages (17 total)
LANGUAGE_ORDER = ["kor", "eng", "fre", "ger", "spa", "por", "ita", "rus",
                  "tur", "pol", "zho-cn", "zho-tw", "jpn", "tha", "vie", "ind", "msa"]
```

## GUI Structure (gui/app.py)

```
┌─────────────────────────────────────────────────────────────┐
│ Format:    ○ Excel (.xlsx)    ○ XML (.xml)                  │
├─────────────────────────────────────────────────────────────┤
│ Mode:      ○ File (single)    ○ Folder (recursive)          │
├─────────────────────────────────────────────────────────────┤
│ Match Type:                                                  │
│   ○ Substring Match (Original)                               │
│   ○ StringID-Only (SCRIPT)                                   │
│   ○ StringID + StrOrigin (STRICT)                           │
│   ○ Special Key Match                                        │
├─────────────────────────────────────────────────────────────┤
│ Source: [________________] [Browse]                          │
│ Target: [________________] [Browse]                          │
│ Branch: [mainline ▼] → [mainline ▼]                         │
├─────────────────────────────────────────────────────────────┤
│ Quick Actions: StringID Lookup | Reverse Lookup              │
├─────────────────────────────────────────────────────────────┤
│ [████████████░░░░░░░░] 60%                                  │
│ [Generate]  [Clear]  [Exit]                                 │
└─────────────────────────────────────────────────────────────┘
```

## Debugging

```bash
# Navigate to project
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate

# Syntax check all
python -m py_compile main.py config.py core/*.py gui/*.py utils/*.py

# Import test
python -c "from core import *; print('core OK')"
python -c "from utils import *; print('utils OK')"
python -c "import config; print(list(config.MATCHING_MODES.keys()))"

# Launch GUI (requires display)
python main.py

# Check all exports
python -c "
from core import (
    sanitize_xml_content, parse_xml_file,
    is_korean_text, find_matches,
    find_matches_stringid_only, find_matches_strict,
    build_sequencer_strorigin_index, discover_language_files,
)
print('All exports OK')
"
```

## CI/CD - GitHub Actions Build

### Trigger File

**Location:** `/home/neil1988/LocalizationTools/QUICKTRANSLATE_BUILD.txt`

### Trigger Build

```bash
echo "Build 001 - Description" >> QUICKTRANSLATE_BUILD.txt
git add QUICKTRANSLATE_BUILD.txt
git commit -m "Build 001: Description"
git push origin main
```

### Workflow

**File:** `.github/workflows/quicktranslate-build.yml`

**Pipeline:**
1. **Validation** (Ubuntu) - Check trigger, generate version
2. **Safety Checks** (Ubuntu) - Syntax, imports, flake8, security
3. **Build** (Windows) - PyInstaller → Inno Setup → Release

**Outputs:**
- `QuickTranslate_vX.X.X_Setup.exe` - Installer with drive selection
- `QuickTranslate_vX.X.X_Portable.zip` - Portable executable
- `QuickTranslate_vX.X.X_Source.zip` - Python source

**Version Format:** `YY.MMDD.HHMM` (auto-generated, Korean time)

### Check Build Status

```bash
gh run list --workflow=quicktranslate-build.yml --limit 5
```

## Common Tasks

### Add New Match Type

1. Add function to `core/matching.py`
2. Export in `core/__init__.py`
3. Add to `MATCHING_MODES` in `config.py`
4. Add UI option in `gui/app.py`
5. Add dispatch logic in `_generate()` method

### Add New Language

1. Add to `LANGUAGE_ORDER` in `config.py`
2. Add to `LANGUAGE_NAMES` in `config.py`
3. Test with `discover_language_files()`

### Modify XML Parsing

1. Edit `core/xml_parser.py`
2. Update `sanitize_xml_content()` for new edge cases
3. Test with problematic XML files

### Add New Output Format

1. Add write function to `core/excel_io.py`
2. Export in `core/__init__.py`
3. Add UI option and call in `gui/app.py`

## Key Files by Task

| Task | Primary File | Secondary |
|------|--------------|-----------|
| XML parsing | `core/xml_parser.py` | - |
| Korean detection | `core/korean_detection.py` | - |
| Index building | `core/indexing.py` | `xml_parser.py` |
| Language loading | `core/language_loader.py` | `xml_parser.py` |
| Matching algorithms | `core/matching.py` | `config.py` |
| Excel I/O | `core/excel_io.py` | `matching.py` |
| XML I/O | `core/xml_io.py` | `xml_parser.py` |
| Main GUI | `gui/app.py` | all core modules |
| Configuration | `config.py` | - |
| Entry point | `main.py` | `gui/app.py` |

## Output Format for Issues

```
## QuickTranslate Issue: [Description]

### Module
[core/gui/utils]

### File
`{path/to/file.py}:{line}`

### Problem
[What's wrong]

### Fix
```python
# Code fix
```

### Test
```bash
python -c "from core.{module} import {function}; print('OK')"
# or
python main.py
```
```

## Documentation

| Document | Location |
|----------|----------|
| User Guide (MD) | `docs/USER_GUIDE.md` |
| User Guide (PDF) | `docs/QuickTranslate_UserGuide.pdf` |
| PDF Styling | `docs/style.css` |
| PDF Generator | `docs/generate_pdf.py` |
