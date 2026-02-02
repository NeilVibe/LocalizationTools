---
name: quicktranslate-specialist
description: QuickTranslate project specialist. Use when working on the QuickTranslate tool - translation LOOKUP, multi-language search, TRANSFER corrections to XML, match types (Substring/StringID-only/Strict/Special Key), or Excel/XML I/O functionality.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# QuickTranslate Specialist

## What Is QuickTranslate?

**QuickTranslate v3.0.0** - A dual-purpose localization tool:

1. **LOOKUP** - Find translations of Korean text across 17 languages
2. **TRANSFER** - Write corrections from Excel/XML to target XML files

**Location:** `RessourcesForCodingTheProject/NewScripts/QuickTranslate/`

## Two Core Functions

| Function | Button | Description | Operation |
|----------|--------|-------------|-----------|
| **LOOKUP** | Generate | Find translations, export to Excel | Read-only |
| **TRANSFER** | TRANSFER | Apply corrections to XML files | Writes files |

### LOOKUP Features
- **Substring Match** - Find Korean text in StrOrigin
- **StringID-Only Match** - For SCRIPT strings (Sequencer/Dialog)
- **Strict Match** - Match by StringID + StrOrigin tuple
- **StringID Lookup** - Direct lookup of any StringID
- **Reverse Lookup** - Find StringID from text in any language

### TRANSFER Features
- **File-to-File** - Single corrections file → single XML
- **Folder-to-Folder** - Batch corrections → all languagedata files
- **STRICT Mode** - Match by StringID AND StrOrigin
- **StringID-Only Mode** - Match by StringID for SCRIPT categories

## Project Structure

```
QuickTranslate/
├── main.py                    # Entry point + CLI args
├── config.py                  # Configuration (BRANCHES, SCRIPT_CATEGORIES)
├── requirements.txt           # Python dependencies
├── QuickTranslate.spec        # PyInstaller spec file
│
├── core/                      # Core functionality
│   ├── __init__.py            # Public exports
│   ├── text_utils.py          # Canonical text normalization (SINGLE SOURCE OF TRUTH)
│   ├── xml_parser.py          # XML sanitization & parsing
│   ├── korean_detection.py    # Korean text detection
│   ├── indexing.py            # StringID/StrOrigin indexing
│   ├── language_loader.py     # Language file discovery
│   ├── matching.py            # 4 matching algorithms (LOOKUP)
│   ├── excel_io.py            # Excel read/write
│   ├── xml_io.py              # XML input parsing
│   └── xml_transfer.py        # TRANSFER engine (writes to XML)
│
├── gui/                       # GUI components
│   ├── __init__.py
│   └── app.py                 # 900x850 Tkinter GUI
│
├── utils/                     # Utilities
│   ├── __init__.py
│   └── file_io.py             # File utilities
│
├── docs/                      # Documentation
│   ├── USER_GUIDE.md          # Full user guide (v3.0.0)
│   ├── QuickTranslate_UserGuide.pdf  # Generated PDF
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
| GUI | Tkinter (900x850) |
| XML Parsing | lxml (with fallback to ElementTree) |
| Excel I/O | openpyxl |
| Build | PyInstaller |
| Installer | Inno Setup |

## Key Modules

### core/text_utils.py (CANONICAL)

Single source of truth for text normalization:

```python
from core.text_utils import normalize_text, normalize_for_matching, normalize_nospace

# normalize_text: HTML unescape, whitespace collapse, &desc; removal
# normalize_for_matching: normalize_text + lowercase
# normalize_nospace: remove all whitespace
```

**CRITICAL:** All other modules import from here. Never duplicate!

### core/xml_transfer.py (TRANSFER ENGINE)

Core transfer functionality:

```python
from core.xml_transfer import (
    merge_corrections_to_xml,      # Core merge logic
    merge_corrections_stringid_only,  # SCRIPT-only merge
    transfer_folder_to_folder,     # Batch transfer
    transfer_file_to_file,         # Single file transfer
    format_transfer_report,        # Generate report
)
```

### core/matching.py (LOOKUP)

All matching algorithms:

```python
from core.matching import (
    find_matches,                  # Substring search
    find_matches_with_stats,       # Substring with statistics
    find_matches_stringid_only,    # SCRIPT filter
    find_matches_strict,           # Tuple match
    find_matches_special_key,      # Custom key
)

# SCRIPT_CATEGORIES imported from config.py
```

### core/excel_io.py

Excel operations:

```python
from core.excel_io import (
    read_korean_input,             # Column A Korean text
    read_corrections_from_excel,   # StringID/StrOrigin/Correction
    write_output_excel,            # Multi-language output
    write_stringid_lookup_excel,   # Single StringID lookup
    write_reverse_lookup_excel,    # Reverse lookup output
)
```

### core/xml_parser.py

XML sanitization and parsing (battle-tested from LanguageDataExporter):

```python
from core.xml_parser import sanitize_xml_content, parse_xml_file, iter_locstr_elements

# Handles: bad entities, control chars, newlines in seg elements
# Case-insensitive tag matching for LocStr
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

# SCRIPT categories - shared by matching.py and xml_transfer.py
SCRIPT_CATEGORIES = {"Sequencer", "AIDialog", "QuestDialog", "NarrationDialog"}

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
│ Log: [scrollable text area]                                  │
├─────────────────────────────────────────────────────────────┤
│ [████████████░░░░░░░░] 60%                                  │
│ [Generate]  [TRANSFER]  [Clear Log]  [Clear All]  [Exit]    │
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
python -c "from core.text_utils import normalize_text, normalize_for_matching; print('text_utils OK')"
python -c "from core.xml_transfer import transfer_file_to_file, format_transfer_report; print('xml_transfer OK')"
python -c "import config; print(config.SCRIPT_CATEGORIES)"

# Launch GUI (requires display)
python main.py

# Check all exports
python -c "
from core import (
    # LOOKUP
    find_matches, find_matches_stringid_only, find_matches_strict,
    # TRANSFER
    transfer_file_to_file, transfer_folder_to_folder, format_transfer_report,
    # Common
    parse_xml_file, read_corrections_from_excel,
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

## Common Tasks

### Add New Match Type

1. Add function to `core/matching.py`
2. Export in `core/__init__.py`
3. Add to `MATCHING_MODES` in `config.py`
4. Add UI option in `gui/app.py`
5. Add dispatch logic in `_generate()` method

### Modify TRANSFER Logic

1. Edit `core/xml_transfer.py`
2. Update `merge_corrections_to_xml()` or `merge_corrections_stringid_only()`
3. Update `transfer_file_to_file()` or `transfer_folder_to_folder()`
4. Test with sample corrections

### Fix Text Normalization

1. ONLY edit `core/text_utils.py` (single source of truth)
2. All other modules import from text_utils
3. Never duplicate normalization logic

### Add New Language

1. Add to `LANGUAGE_ORDER` in `config.py`
2. Add to `LANGUAGE_NAMES` in `config.py`
3. Test with `discover_language_files()`

## Key Files by Task

| Task | Primary File | Secondary |
|------|--------------|-----------|
| Text normalization | `core/text_utils.py` | - |
| XML parsing | `core/xml_parser.py` | - |
| TRANSFER logic | `core/xml_transfer.py` | `text_utils.py` |
| Matching algorithms | `core/matching.py` | `config.py` |
| Excel I/O | `core/excel_io.py` | `text_utils.py` |
| XML I/O | `core/xml_io.py` | `xml_parser.py` |
| Main GUI | `gui/app.py` | all core modules |
| Configuration | `config.py` | - |

## Output Format for Issues

```
## QuickTranslate Issue: [Description]

### Function
[LOOKUP/TRANSFER/Both]

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
```
```

## Reference Files

| File | Location | Purpose |
|------|----------|---------|
| **EXPORT PATH TREE** | `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/EXPORT PATH TREE.txt` | **COMPLETE** list of all export folder paths. Use this to verify path formats! |

### Export Folder Structure (from EXPORT PATH TREE.txt)

```
export__/
├── Dialog/
│   ├── AIDialog/
│   ├── NarrationDialog/
│   ├── QuestDialog/
│   └── StageCloseDialog/
├── None/
│   ├── Board/
│   ├── EquipType/
│   └── GameAdvice/
├── Platform/
│   └── PlatformService/
├── Sequencer/
│   └── Faction/...
├── System/                    ← GAME_DATA
│   ├── Gimmick/               ← NON-PRIORITY (filter out)
│   ├── Item/
│   ├── ItemGroup/
│   ├── LookAt/
│   ├── MultiChange/           ← NON-PRIORITY (filter out)
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

**NON-PRIORITY folders to filter:** `System/Gimmick`, `System/MultiChange`

## Documentation

| Document | Location |
|----------|----------|
| User Guide (MD) | `docs/USER_GUIDE.md` |
| User Guide (PDF) | `docs/QuickTranslate_UserGuide.pdf` |
| PDF Styling | `docs/style.css` |
| PDF Generator | `docs/generate_pdf.py` |
