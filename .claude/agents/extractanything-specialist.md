---
name: extractanything-specialist
description: ExtractAnything project specialist. Use when working on extraction, diff, long string, no-voice, blacklist, string eraser, string add, file eraser tabs, or XML/Excel I/O operations.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# ExtractAnything Specialist

## Project Overview

**ExtractAnything** is a multi-tab tkinter tool for extracting, comparing, and manipulating LocStr entries from XML language data files.

**Location:** `RessourcesForCodingTheProject/NewScripts/ExtractAnything/`

**Key Purpose:**
- Extract LocStr entries from XML to Excel/XML
- Diff source vs target language data
- Find long strings, no-voice entries, blacklisted terms
- Erase or add LocStr entries by StringID + StrOrigin matching
- Erase files by filename matching

---

## RAW LOCSTR PRESERVATION (CRITICAL!)

**NEVER modify original LocStr attributes. EVER.**

- `raw_attribs = dict(elem.attrib)` — captured from lxml elements, untouched
- `xml_writer.py` uses `etree.SubElement(root, "LocStr", **raw_attribs)` — pure raw output
- `normalize_newlines()` only modifies convenience fields (`str_origin`, `str_value`) — NOT `raw_attribs`
- When writing back to XML, always use `raw_attribs`, never the normalized fields

---

## 8 Tabs

| Tab | Engine | Purpose |
|-----|--------|---------|
| Extract | `extract_tab.py` | Extract all LocStr entries to Excel + XML per language |
| Diff | `diff_tab.py` + `diff_engine.py` | Compare source vs target, output differences |
| Long String | `long_string_tab.py` + `long_string_engine.py` | Find strings exceeding visible char limit |
| No-Voice | `novoice_tab.py` + `novoice_engine.py` | Find voiced entries missing SoundEventName |
| Blacklist | `blacklist_tab.py` + `blacklist_engine.py` | Find blacklisted terms in translations |
| Str Erase | `string_eraser_tab.py` + `string_eraser_engine.py` | Remove LocStr by StringID+StrOrigin match |
| Str Add | `string_add_tab.py` + `string_add_engine.py` | Add missing LocStr by StringID+StrOrigin diff |
| File Erase | `file_eraser_tab.py` + `file_eraser_engine.py` | Move files matching source stems to backup |

---

## File Structure

```
ExtractAnything/
├── main.py                     # Entry point
├── config.py                   # Constants, settings, paths
├── requirements.txt            # Dependencies (lxml, openpyxl, xlsxwriter)
├── ExtractAnything.spec         # PyInstaller config
│
├── core/                       # Engines and utilities
│   ├── xml_parser.py           # Sanitize, parse, read/write XML
│   ├── xml_writer.py           # Raw LocStr XML output (etree.SubElement)
│   ├── input_parser.py         # Unified XML/Excel → common entry format
│   ├── excel_reader.py         # Read entries from Excel
│   ├── excel_writer.py         # Write entries to Excel (xlsxwriter)
│   ├── text_utils.py           # Normalization, char counting, newline handling
│   ├── language_utils.py       # Language code detection
│   ├── export_index.py         # EXPORT folder index (categories, voiced SIDs)
│   ├── path_filter.py          # Path-based entry filtering
│   ├── validators.py           # Input validation for all tabs
│   ├── diff_engine.py          # Diff + revert logic
│   ├── long_string_engine.py   # Visible char counting
│   ├── novoice_engine.py       # Missing SoundEventName detection
│   ├── blacklist_engine.py     # Blacklist term matching
│   ├── string_eraser_engine.py # LocStr removal by key match
│   ├── string_add_engine.py    # LocStr addition by key diff
│   └── file_eraser_engine.py   # File stem matching + move
│
├── gui/                        # tkinter GUI
│   ├── app.py                  # Main window, notebook, log, settings bar
│   ├── base_tab.py             # Abstract base class for tabs
│   ├── extract_tab.py          # Extract tab
│   ├── diff_tab.py             # Diff tab
│   ├── long_string_tab.py      # Long String tab
│   ├── novoice_tab.py          # No-Voice tab
│   ├── blacklist_tab.py        # Blacklist tab
│   ├── string_eraser_tab.py    # String Eraser tab
│   ├── string_add_tab.py       # String Add tab
│   ├── file_eraser_tab.py      # File Eraser tab
│   └── path_filter_dialog.py   # Path filter selection dialog
│
└── installer/
    └── ExtractAnything.iss      # Inno Setup installer
```

---

## Key Patterns

### Entry Format (Common Dict)
```python
{
    "string_id": "SID_001",
    "str_origin": "한국어 텍스트",      # normalized (for display/comparison)
    "str_value": "Translation text",    # normalized (for display/comparison)
    "raw_attribs": {"StringId": "SID_001", "StrOrigin": "...", "Str": "..."},  # UNTOUCHED
    "language": "KR",
    "source_file": "/path/to/file.xml",
}
```

### Key Matching (String Eraser / String Add)
2-step cascade: exact normalized → nospace normalized.
```python
key = (sid.lower(), normalize_text(str_origin))
nospace_key = (sid.lower(), normalize_nospace(normalize_text(str_origin)))
```

### Thread Safety
All tabs use `self.run_in_thread(work_fn)` → daemon thread → queue-based logging.

### XML Parse Paths
- `parse_root_from_string(sanitize_xml(raw))` — for reading entries (sanitized)
- `parse_tree_from_file(path)` — for in-place modification (no sanitization)
- **NEVER mix these for the same file** in key collection + modification

---

## XML Newline Convention

**Newlines in XML = `<br/>` tags. The ONLY correct format.**
- `normalize_newlines()` converts all variants to `<br/>` (for convenience fields only)
- `raw_attribs` preserves whatever the original file had (lxml handles escaping)

---

## CI/CD Pipeline

### GitHub Actions (NOT Gitea!)

```bash
echo "Build N: description" >> /home/neil1988/LocalizationTools/EXTRACTANYTHING_BUILD.txt
git add EXTRACTANYTHING_BUILD.txt && git commit -m "Trigger ExtractAnything Build N" && git push origin main
```

### Workflow: `.github/workflows/extractanything-build.yml`

**Jobs:** validate → safety-checks → build-release
**Artifacts:** Setup.exe, Portable.zip, Source.zip

---

## Config Constants

```python
LOCSTR_TAGS = ("LocStr", "locstr", "LOCSTR", "LOCStr", "Locstr")
STRINGID_ATTRS = ("StringId", "StringID", "stringid", "STRINGID", "Stringid", "stringId")
STRORIGIN_ATTRS = ("StrOrigin", "Strorigin", "strorigin", "STRORIGIN")
STR_ATTRS = ("Str", "str", "STR")
```

---

## Python Compatibility Protocol

1. `from __future__ import annotations` — EVERY `.py` file
2. Direct imports only — `import config`, `from core.X import Y`. Never `from .. import`.
