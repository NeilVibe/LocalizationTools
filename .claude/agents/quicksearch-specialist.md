---
name: quicksearch-specialist
description: QuickSearch project specialist. Use when working on the QuickSearch tool - LINE CHECK, TERM CHECK, dictionary creation, ENG/KR BASE modes, or XML search functionality.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# QuickSearch Specialist

## What Is QuickSearch?

**QuickSearch v1.0.0** - A translation search and QA tool for localization workflows.

**Location:** `RessourcesForCodingTheProject/NewScripts/QuickSearch/`

**Core Functions:**
1. **Quick Search** - Dictionary-based search with reference support
2. **LINE CHECK** - Find inconsistent translations (same source, different translations)
3. **TERM CHECK** - Find missing glossary terms using Aho-Corasick
4. **Glossary Extract** - Create glossaries from localization files

**Key Feature:** ENG BASE / KR BASE selection for LINE CHECK and TERM CHECK

## Project Structure

```
QuickSearch/
├── main.py                    # Entry point + GUI launcher
├── config.py                  # Configuration constants + settings
├── requirements.txt           # Python dependencies
├── QuickSearch.spec           # PyInstaller spec file
├── README.md                  # Documentation
├── USER_GUIDE.md              # User documentation
│
├── gui/                       # GUI components
│   ├── __init__.py
│   ├── app.py                 # Main Tkinter GUI (tabs, buttons)
│   └── dialogs.py             # LINE/TERM CHECK config dialogs
│
├── core/                      # Core functionality
│   ├── __init__.py
│   ├── xml_parser.py          # XML parsing (LocStr extraction)
│   ├── preprocessing.py       # ENG BASE StringID matching (NEW!)
│   ├── line_check.py          # LINE CHECK logic
│   ├── term_check.py          # TERM CHECK with Aho-Corasick
│   ├── glossary.py            # Glossary extraction & filtering
│   ├── dictionary.py          # Dictionary creation/loading
│   └── search.py              # Search functionality
│
├── utils/                     # Utilities
│   ├── __init__.py
│   ├── filters.py             # Filter functions
│   └── language_utils.py      # Korean detection, normalization
│
├── installer/                 # Inno Setup
│   └── QuickSearch.iss        # Installer script
│
└── tests/                     # Tests
    └── __init__.py
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| GUI | Tkinter |
| XML Parsing | lxml |
| Data Processing | pandas |
| Fast String Matching | pyahocorasick |
| Build | PyInstaller |
| Installer | Inno Setup |

## ENG BASE vs KR BASE

**The key new feature in v1.0.0:**

| Mode | Source | Use Case |
|------|--------|----------|
| **KR BASE** | Korean StrOrigin | Default - check Korean source consistency |
| **ENG BASE** | English via StringID | Check against English source text |

### How ENG BASE Works

```python
# core/preprocessing.py
def preprocess_for_consistency_check(target_files, eng_file, source_base):
    target_entries = parse_multiple_files(target_files)

    if source_base == "kr_base" or eng_file is None:
        # KR BASE: Use StrOrigin directly
        return [{"source": e["str_origin"], ...} for e in target_entries]
    else:
        # ENG BASE: Match StringIDs to get English source
        eng_lookup = {e["string_id"]: e["str"] for e in parse_multiple_files([eng_file])}
        return [{"source": eng_lookup.get(e["string_id"], e["str_origin"]), ...}
                for e in target_entries]
```

### GUI Selection

LINE CHECK and TERM CHECK dialogs have a "Source Base" section:
```
┌─ Source Base ─────────────────────────────────────────┐
│  ( ) KR BASE - Korean StrOrigin as source (default)   │
│  ( ) ENG BASE - English via StringID matching         │
└───────────────────────────────────────────────────────┘
```

## Clean Output

**No filename clutter in reports:**

```
# OLD (verbose):
source_text
  translation_A    [file1.xml]
  translation_B    [file2.xml]

# NEW (clean):
source_text
  translation_A
  translation_B
```

## Key Modules

### core/xml_parser.py

Parses XML and TXT/TSV files:

```python
from core.xml_parser import parse_xml_file, parse_multiple_files, LocStrEntry

entries = parse_xml_file("languagedata_fre.xml")
# Returns List[LocStrEntry] with string_id, str_origin, str, file_path
```

### core/preprocessing.py

Handles ENG BASE StringID matching:

```python
from core.preprocessing import preprocess_for_consistency_check
from config import SOURCE_BASE_ENG

entries = preprocess_for_consistency_check(
    target_files=["languagedata_fre.xml"],
    eng_file="languagedata_eng.xml",
    source_base=SOURCE_BASE_ENG
)
# Returns List[PreprocessedEntry] with source matched via StringID
```

### core/line_check.py

LINE CHECK algorithm:

```python
from core.line_check import run_line_check, save_line_check_results

results = run_line_check(
    target_files=["languagedata_fre.xml"],
    eng_file="languagedata_eng.xml",
    source_base="eng_base",
    filter_sentences=True,
    length_threshold=15
)

save_line_check_results(results, "line_report.txt", include_filenames=False)
```

### core/term_check.py

TERM CHECK with Aho-Corasick:

```python
from core.term_check import run_term_check, save_term_check_results

results = run_term_check(
    target_files=["languagedata_fre.xml"],
    eng_file="languagedata_eng.xml",
    source_base="eng_base",
    filter_sentences=True,
    max_issues_per_term=6
)

save_term_check_results(results, "term_report.txt", include_filenames=False)
```

### utils/language_utils.py

Korean detection and text processing:

```python
from utils.language_utils import is_korean, normalize_text, tokenize

is_korean("안녕하세요")  # True
is_korean("Hello")       # False

normalized = normalize_text("Text with   spaces")  # "Text with spaces"
```

### utils/filters.py

Glossary filtering:

```python
from utils.filters import glossary_filter

filtered = glossary_filter(
    pairs,
    length_threshold=15,
    filter_sentences=True,
    min_occurrence=2
)
```

## Data Structures

### LocStrEntry (core/xml_parser.py)

```python
@dataclass
class LocStrEntry:
    string_id: str      # StringID for matching
    str_origin: str     # Korean/source text
    str: str            # Translation
    file_path: str      # Source file
```

### PreprocessedEntry (core/preprocessing.py)

```python
@dataclass
class PreprocessedEntry:
    source: str               # Source for comparison (KR or ENG)
    translation: str          # Translation
    string_id: str            # StringID
    file_path: str            # Source file
    original_str_origin: str  # Original Korean (for reference)
```

### LineCheckResult (core/line_check.py)

```python
@dataclass
class LineCheckResult:
    source: str              # The source text
    translations: List[str]  # Multiple different translations found
```

### TermCheckResult (core/term_check.py)

```python
@dataclass
class TermCheckResult:
    term: str                    # The glossary term
    reference_translation: str   # Expected translation
    issues: List[TermIssue]      # List of violations
```

## Configuration (config.py)

```python
# Source base modes
SOURCE_BASE_KR = "kr_base"
SOURCE_BASE_ENG = "eng_base"

# Settings dataclass with defaults
@dataclass
class Settings:
    font_family: str = 'Arial'
    font_size: int = 10
    ui_language: str = 'English'
    glossary_length: int = 15
    min_occurrence: int = 2
    filter_sentences: bool = True
```

## Debugging

```bash
# Navigate to project
cd RessourcesForCodingTheProject/NewScripts/QuickSearch

# Syntax check all
python -m py_compile config.py main.py core/*.py gui/*.py utils/*.py

# Import test
python -c "from core.xml_parser import parse_xml_file; print('OK')"
python -c "from core.preprocessing import preprocess_for_consistency_check; print('OK')"
python -c "from core.line_check import run_line_check; print('OK')"
python -c "from core.term_check import run_term_check; print('OK')"

# Launch GUI
python main.py
```

## CI/CD - GitHub Actions Build

### Trigger File

**Location:** `/home/neil1988/LocalizationTools/QUICKSEARCH_BUILD.txt`

### Trigger Build

```bash
echo "Build 001 - Description" >> QUICKSEARCH_BUILD.txt
git add QUICKSEARCH_BUILD.txt
git commit -m "Build 001: Description"
git push origin main
```

### Workflow

**File:** `.github/workflows/quicksearch-build.yml`

**Pipeline:**
1. **Validation** (Ubuntu) - Check trigger, generate version
2. **Safety Checks** (Ubuntu) - Syntax, imports, flake8, security
3. **Build** (Windows) - PyInstaller → Inno Setup → Release

**Outputs:**
- `QuickSearch_vX.X.X_Setup.exe` - Installer
- `QuickSearch_vX.X.X_Portable.zip` - Portable
- `QuickSearch_vX.X.X_Source.zip` - Source

**Version Format:** `YY.MMDD.HHMM` (auto-generated, Korean time)

## Common Tasks

### Add New Filter

1. Add function to `utils/filters.py`
2. Export in `utils/__init__.py`
3. Use in `core/glossary.py` or `core/line_check.py`

### Modify LINE CHECK Logic

1. Edit `core/line_check.py`
2. Update `run_line_check()` function
3. Test with sample XML files

### Modify TERM CHECK Logic

1. Edit `core/term_check.py`
2. Update `run_term_check()` function
3. Ensure Aho-Corasick automaton is rebuilt correctly

### Add New GUI Dialog

1. Create dialog class in `gui/dialogs.py`
2. Add button in `gui/app.py`
3. Connect to core function

## Key Files by Task

| Task | Primary File | Secondary |
|------|--------------|-----------|
| XML/TXT parsing | `core/xml_parser.py` | - |
| ENG BASE matching | `core/preprocessing.py` | `config.py` |
| LINE CHECK | `core/line_check.py` | `preprocessing.py` |
| TERM CHECK | `core/term_check.py` | `preprocessing.py` |
| Glossary extraction | `core/glossary.py` | `utils/filters.py` |
| Dictionary management | `core/dictionary.py` | - |
| Search | `core/search.py` | `dictionary.py` |
| Korean detection | `utils/language_utils.py` | - |
| Filters | `utils/filters.py` | - |
| Main GUI | `gui/app.py` | - |
| Dialogs | `gui/dialogs.py` | - |
| Config | `config.py` | - |

## Output Format for Issues

```
## QuickSearch Issue: [Description]

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
