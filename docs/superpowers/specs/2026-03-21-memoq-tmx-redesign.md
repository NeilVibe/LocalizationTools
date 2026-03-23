# MemoQ TMX Conversion Redesign — Auto Language Detection

**Date:** 2026-03-21
**Status:** Completed (2026-03-21)
**Scope:** Replace manual language dropdown + batch buttons with smart auto-detecting MemoQ TMX converter

---

## Goal

Redesign TMX Tools Tab Section 1 to auto-detect languages from folder/file suffixes (same as QuickTranslate's source scanner), eliminating the manual language dropdown and separate batch mode. One button converts everything.

---

## Changes Summary

| Before | After |
|--------|-------|
| Manual language dropdown (13 options) | Auto-detected from suffix |
| "Convert Single" + "Batch Convert" buttons | One "Convert to MemoQ-TMX" button |
| Folder-only input | File OR folder (radio toggle) |
| No language preview | Shows detected languages after browse |
| `creationid="CombinedConversion"` | `creationid="QT_YYYYMMDD_HHMM"` |

---

## Input Flow

Reuse `core.source_scanner.scan_source_for_languages()` — same function QuickTranslate Tab 1 uses.

**Supports:** XML, Excel, mixed, files with suffixes, folders with suffixes, nested structures.

**Example:**
```
Source/
├── FRE/              → all files inside tagged FRE
│   ├── file1.xml
│   └── file2.xml
├── corrections_GER.xml  → tagged GER
└── hotfix_ENG.xlsx      → tagged ENG
```

Result: 3 TMX files created (one per language).

---

## Language Mapping (Suffix → BCP-47)

MemoQ TMX `<tuv xml:lang="...">` needs BCP-47 codes. Map from QuickTranslate suffixes:

```python
SUFFIX_TO_BCP47 = {
    "ENG": "en-US",    "FRE": "fr-FR",    "GER": "de-DE",
    "ITA": "it-IT",    "JPN": "ja-JP",    "KOR": "ko",
    "POL": "pl-PL",    "POR-BR": "pt-BR", "RUS": "ru-RU",
    "SPA-ES": "es-ES", "SPA-MX": "es-MX", "TUR": "tr-TR",
    "ZHO-CN": "zh-CN", "ZHO-TW": "zh-TW",
}
```

Unknown suffixes → fallback to `suffix.lower()` (e.g. `THAI` → `thai`).

---

## Output

- **Location:** Same folder as input (no output folder picker)
- **Naming:** `<InputFolderName>_<LANG>.tmx` (e.g. `MyProject_FRE.tmx`)
- **File mode:** `<FileName>_<LANG>.tmx` next to the file
- **One TMX per detected language**

---

## TMX Creation ID

```python
from datetime import datetime
creation_id = f"QT_{datetime.now().strftime('%Y%m%d_%H%M')}"
# e.g. "QT_20260321_1730"
```

Used in `<tu creationid="QT_20260321_1730" changeid="QT_20260321_1730">`.

---

## GUI Design (Tab 3 Section 1 — replaces current)

```
┌─ MemoQ-TMX Conversion ────────────────────┐
│ ◉ Folder  ○ Single File                   │
│                                            │
│ Path: [________________________] [Browse]  │
│                                            │
│ [Convert to MemoQ-TMX]                     │
│                                            │
│ Detected: ENG (3 files), FRE (2 files)     │
└────────────────────────────────────────────┘
```

- Radio toggle (folder/file) — ExtractAnything pattern
- One Browse button, switches between `askdirectory` and `askopenfilename`
- One Convert button — scans, groups by language, creates one TMX per language
- Status label updates after browse showing detected languages + file counts

---

## Orchestrator Function

New function in `core/tmx_tools.py`:

```python
def convert_to_memoq_tmx(input_path: str) -> list[tuple[str, str, bool]]:
    """
    Auto-detect languages from input path, create one MemoQ TMX per language.

    Args:
        input_path: folder or single file path

    Returns:
        List of (language, output_file, success) tuples
    """
```

**Steps:**
1. Call `scan_source_for_languages(Path(input_path))` — **must wrap str as Path** since the function requires `Path` type
2. **Skip KOR** — KOR files would produce empty TMX because `is_korean_text()` discards all TUs when target=ko. Log a note and skip.
3. For each non-KOR language:
   a. Map suffix to BCP-47 via `SUFFIX_TO_BCP47`
   b. Call `combine_xmls_to_tmx()` with `file_list=files, postprocess=True, target_language=bcp47, creation_id="QT_YYYYMMDD_HHMM"`
   c. Output to `<input_folder>_<LANG>.tmx` (same folder as input)
4. Return results list

**API change to `combine_xmls_to_tmx()`:**
Add optional `file_list` parameter. When provided, use it directly instead of calling `get_all_xml_files(input_folder)`. Also add optional `creation_id` parameter (defaults to `"CombinedConversion"` for backwards compat).

```python
def combine_xmls_to_tmx(input_folder, output_file, target_language,
                         postprocess=True, file_list=None, creation_id=None):
```

**Single-file mode edge case:**
If user selects a single file with no language suffix (e.g. `strings.xml`), `scan_source_for_languages` puts it in `unrecognized`. In that case, show a warning: "No language detected in filename. Please put the file in a folder with a language suffix (e.g. FRE/) or rename it."

---

## Files to Modify

| File | Change |
|------|--------|
| `core/tmx_tools.py` | Add `SUFFIX_TO_BCP47`, `convert_to_memoq_tmx()` orchestrator, update `combine_xmls_to_tmx()` to accept `file_list` + `creation_id` params |
| `gui/tmx_tools_tab.py` | Rewrite Section 1 — radio toggle, auto-detect, single convert button, detected languages label |
| `core/__init__.py` | Export `convert_to_memoq_tmx` |

---

## What Stays the Same

- Section 2 (TMX Cleaner → Excel) — untouched
- `clean_segment()`, `postprocess_tmx_string()` — untouched
- `combine_xmls_to_tmx()` core logic — just add optional `creation_id` param
- All existing regex patterns — untouched
