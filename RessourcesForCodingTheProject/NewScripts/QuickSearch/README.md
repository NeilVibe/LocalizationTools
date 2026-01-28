# QuickSearch v1.0.0 - Modular Rewrite

**Translation Search & QA Tool for Localization**

A complete modular rewrite of QuickSearch with clean architecture.

---

## New Features

### ENG BASE / KR BASE Selection

LINE CHECK and TERM CHECK now support two source modes:

| Mode | Description |
|------|-------------|
| **KR BASE** | Uses Korean StrOrigin as source (default) |
| **ENG BASE** | Uses English text matched via StringID |

**When to use ENG BASE:**
- Checking consistency against English source
- Finding inconsistent translations of same English text
- Validating terminology against English glossary

### Clean Output

Reports no longer include verbose filename printing:

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

---

## Project Structure

```
QuickSearch/
├── main.py                    # Entry point + GUI launcher
├── config.py                  # Configuration constants + settings
├── gui/
│   ├── __init__.py
│   ├── app.py                 # Main Tkinter GUI (tabs, buttons)
│   └── dialogs.py             # LINE/TERM CHECK config dialogs
├── core/
│   ├── __init__.py
│   ├── xml_parser.py          # XML parsing (LocStr extraction)
│   ├── dictionary.py          # Dictionary creation/loading
│   ├── search.py              # Search functionality
│   ├── line_check.py          # LINE CHECK logic
│   ├── term_check.py          # TERM CHECK logic
│   ├── glossary.py            # Glossary extraction & filtering
│   └── preprocessing.py       # ENG BASE preprocessing
├── utils/
│   ├── __init__.py
│   ├── filters.py             # Filter functions
│   └── language_utils.py      # Korean detection, normalization
└── tests/
    └── test_*.py
```

---

## Usage

### GUI Mode

```bash
python main.py
```

### Features

1. **Quick Search Tab**
   - Create/Load dictionaries
   - One-line and multi-line search
   - Reference dictionary support

2. **Glossary Checker Tab**
   - Extract Glossary
   - LINE CHECK (with ENG/KR BASE)
   - TERM CHECK (with ENG/KR BASE)

---

## ENG BASE Workflow

### LINE CHECK with ENG BASE

1. Open LINE CHECK dialog
2. Select **ENG BASE** in Source Base section
3. Select English XML file
4. Select target language files
5. Run check

Result: Finds cases where same English source has different translations.

### TERM CHECK with ENG BASE

1. Open TERM CHECK dialog
2. Select **ENG BASE** in Source Base section
3. Select English XML file
4. Select target language files
5. Run check

Result: Finds cases where English glossary term appears but expected translation is missing.

---

## Module Reference

### core/xml_parser.py

```python
from QuickSearch.core.xml_parser import parse_xml_file, parse_multiple_files

entries = parse_xml_file("languagedata_fre.xml")
# Returns List[LocStrEntry] with string_id, str_origin, str, file_path
```

### core/preprocessing.py

```python
from QuickSearch.core.preprocessing import preprocess_for_consistency_check
from QuickSearch.config import SOURCE_BASE_ENG

entries = preprocess_for_consistency_check(
    target_files=["languagedata_fre.xml"],
    eng_file="languagedata_eng.xml",
    source_base=SOURCE_BASE_ENG
)
# Returns List[PreprocessedEntry] with source matched via StringID
```

### core/line_check.py

```python
from QuickSearch.core.line_check import run_line_check, save_line_check_results

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

```python
from QuickSearch.core.term_check import run_term_check, save_term_check_results

results = run_term_check(
    target_files=["languagedata_fre.xml"],
    eng_file="languagedata_eng.xml",
    source_base="eng_base",
    filter_sentences=True,
    max_issues_per_term=6
)

save_term_check_results(results, "term_report.txt", include_filenames=False)
```

---

## Dependencies

- Python 3.8+
- lxml
- pandas
- ahocorasick (pyahocorasick)
- tkinter (for GUI)

---

## Original File

The original monolithic `QuickSearch0818.py` (3300+ lines) is preserved for reference.
This modular rewrite is approximately 2000 lines with better maintainability.

---

## Author

Neil | Version 1.0.0
