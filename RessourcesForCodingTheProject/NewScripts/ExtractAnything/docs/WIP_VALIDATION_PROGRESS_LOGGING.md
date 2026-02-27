# ExtractAnything: Validation, Progress & Logging Overhaul

**Date:** 2026-02-27
**Status:** IMPLEMENTED — awaiting review

---

## Summary

Added three major features to ExtractAnything, inspired by QuickTranslate's patterns:

1. **Modular folder/file validation** — per-tab, runs on browse
2. **Progress bar wiring** — all 6 tabs now report 0-100% during operations
3. **Rich GUI logging** — timestamps, operation headers, per-file feedback, summaries

---

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| `core/validators.py` | 9 modular validation functions |

### Modified Files
| File | Changes |
|------|---------|
| `core/language_utils.py` | Added cached `get_valid_codes()`, `invalidate_code_cache()`, `count_*` helpers, hardcoded fallback codes, standalone folder name detection |
| `core/input_parser.py` | `parse_input_folder()` now accepts `log_fn` + `progress_fn`, logs per-file entry counts and summary |
| `core/diff_engine.py` | `diff_folder()` accepts `progress_fn`, reports progress during source/target/compare phases |
| `core/long_string_engine.py` | `extract_long_strings_folder()` accepts `progress_fn`, passes through to parser |
| `core/novoice_engine.py` | `extract_novoice_folder()` accepts `progress_fn`, passes through to parser |
| `core/blacklist_engine.py` | `search_blacklist_folder()` accepts `progress_fn`, passes through to parser |
| `gui/app.py` | LOC/EXPORT browse now validates + logs results; `_browse_loc`/`_browse_export` replace generic `_browse_setting`; code cache invalidation on LOC change; log messages include timestamps; auto-truncation at 5000 lines |
| `gui/base_tab.py` | Added `set_progress()` shortcut, `on_selected` callback for `browse_file`/`browse_folder`, `_log_header()` for operation headers |
| `gui/diff_tab.py` | All 3 sub-tabs validate on browse; progress wired to file diff + folder diff + revert; operation headers |
| `gui/long_string_tab.py` | Source folder validates on browse; progress bar wired; operation header |
| `gui/novoice_tab.py` | Source folder validates on browse; progress bar wired; operation header; EXPORT stats logged |
| `gui/blacklist_tab.py` | Blacklist Excel/folder validates on browse; Target folder validates on browse; per-language term counts logged; progress wired |
| `gui/string_eraser_tab.py` | Source keys folder validates on browse; Target folder validates on browse; progress wired; operation header |
| `gui/file_eraser_tab.py` | Both folders validate on browse; preview count logged; progress wired; operation header |

---

## Validation System (`core/validators.py`)

### Design Principle
Each tab has different input requirements. Instead of one monolithic validator, we have **modular validators** that tabs compose.

### Validators Available

| Validator | What it checks | Used by |
|-----------|---------------|---------|
| `validate_loc_folder()` | Has `languagedata_*.xml`, reports language codes | Global LOC browse |
| `validate_export_folder()` | Has `*.loc.xml`, reports categories | Global EXPORT browse |
| `validate_xml_source_folder()` | XML files with LocStr entries; detects languages via suffix; dry-run counts per file | Long String, No-Voice, Blacklist (target), Str Erase (target), Diff (folder) |
| `validate_excel_source()` | Excel has StringID/StrOrigin/Str columns | (Available for future use) |
| `validate_source_keys_folder()` | Has XML or Excel files for erase keys | Str Erase (source) |
| `validate_blacklist_excel()` | Header row = language codes; counts data rows; reports matched/unknown columns | Blacklist (file) |
| `validate_blacklist_folder()` | Multiple Excel files, aggregates language detection | Blacklist (folder) |
| `validate_generic_folder()` | Folder exists, has files, reports count | File Erase (source + target) |
| `validate_diff_file()` | Single file: XML has LocStr entries, or Excel has correct columns | Diff (file mode) |
| `validate_diff_excel_columns()` | **BLOCKING** — Excel has columns required by compare mode (XML always passes) | Diff (file + revert) |
| `validate_diff_folder_excel_columns()` | **BLOCKING** — all Excel files in folder pass column check | Diff (folder) |

### ValidationResult
```python
@dataclass
class ValidationResult:
    ok: bool = True
    languages: list[str]       # Detected language codes
    file_count: int             # Number of files
    entry_count: int            # Total LocStr entries (if applicable)
    messages: list[(str, tag)]  # Log messages to replay
    file_details: dict          # Per-file counts/errors
```

### Suffix Detection
Uses `language_utils.get_valid_codes()` which:
1. Auto-discovers from LOC folder (`languagedata_*.xml`)
2. Merges with hardcoded fallback set (ENG, KR, FRE, GER, etc.)
3. Caches result (invalidated on LOC folder change)

---

## Progress Bar Wiring

### Before
- Progress bar existed but was only wired to EXPORT index building
- All other operations: bar sat at 0 until 100

### After
Every tab reports progress. Ranges vary per tab (some use EXPORT, some don't).

**Typical ranges (Long String, No-Voice, Blacklist):**

| Phase | Progress Range | Who Reports |
|-------|---------------|-------------|
| EXPORT index build | 5-25% | Tab wraps `build_export_index(cur, tot)` |
| File parsing | 25-64% | Engine wraps `parse_input_folder` to 0-60% of range |
| Filtering | 64-90% | Engine per-language loop (60-100% of range) |
| Writing output | 92-100% | Tab + `signal_done` |

**Note:** `build_export_index` uses `progress_fn(current, total)` (2 args).
All other engines use `progress_fn(float_0_to_100)` (1 arg). Tabs convert via lambdas.

### Engine Progress Pattern
Engines split 60/40 between parsing and filtering with wrapper lambdas:
```python
parse_prog = (lambda v: progress_fn(v * 0.6)) if progress_fn else None
by_lang = input_parser.parse_input_folder(folder, progress_fn=parse_prog)

for i, lang in enumerate(langs, 1):
    progress_fn(60 + (i * 40 / len(langs)))
```

---

## Rich Logging

### Before
- No timestamps
- Basic "Processing KR..." + final count
- No per-file feedback during parsing
- No operation headers

### After

**Timestamps:** Every log line prefixed with `[HH:MM:SS]`

**Operation Headers:** Separator + title before each operation
```
[14:32:01] ──────────────────────────────────────────────────
[14:32:01]   Long String Extraction (>= 200 chars)
[14:32:01] ──────────────────────────────────────────────────
```

**Per-file parsing feedback:**
```
[14:32:01] Parsing 3 *.xml files...
[14:32:01]   languagedata_KR.xml: 12,345 entries (KR)
[14:32:01]   languagedata_ENG.xml: 12,345 entries (ENG)
[14:32:01]   languagedata_FRE.xml: 8,901 entries (FRE)
[14:32:02] Parsed 3 files -> 33,591 entries across 3 languages
```

**Validation feedback on browse:**
```
[14:31:55] LOC: 15 languages detected: ARA, BRA, CHI, CZE, ...
[14:31:56] EXPORT: 8,234 .loc.xml files, 12 categories (Dialog, ...)
[14:31:57] Source: 3 XML files, 33,591 LocStr entries, 3 languages
[14:31:57]   KR: 1 file, 12,345 entries
[14:31:57]   ENG: 1 file, 12,345 entries
[14:31:57]   FRE: 1 file, 8,901 entries
```

**Auto-truncation:** Log panel capped at 5,000 lines (prevents memory growth).

---

## Per-Tab Validation on Browse

| Tab | Source Browse | Target Browse |
|-----|-------------|---------------|
| **Diff (File)** | `validate_diff_file(label="Source")` + **`validate_diff_excel_columns()` BLOCKING** | `validate_diff_file(label="Target")` + **`validate_diff_excel_columns()` BLOCKING** |
| **Diff (Folder)** | `validate_xml_source_folder(label="Source")` + **`validate_diff_folder_excel_columns()` BLOCKING** | `validate_xml_source_folder(label="Target")` + **`validate_diff_folder_excel_columns()` BLOCKING** |
| **Diff (Revert)** | `validate_diff_file()` per file + **`validate_diff_excel_columns()` BLOCKING** (Before + After) | N/A |
| **Long String** | `validate_xml_source_folder(label="Source")` | N/A (uses global LOC) |
| **No-Voice** | `validate_xml_source_folder(label="Source")` | N/A (uses global LOC) |
| **Blacklist** | `validate_blacklist_excel()` or `validate_blacklist_folder()` | `validate_xml_source_folder(label="Target")` |
| **Str Erase** | `validate_source_keys_folder()` | `validate_xml_source_folder(label="Target")` |
| **File Erase** | `validate_generic_folder(label="Source")` | `validate_generic_folder(label="Target")` |

---

## Global Folder Dependencies (unchanged)

| Tab | LOC Folder | EXPORT Folder |
|-----|-----------|----------------|
| **Diff (File)** | No | Conditional (category filter) |
| **Diff (Folder)** | Yes (suffix detection) | Conditional (category filter) |
| **Diff (Revert)** | No | No |
| **Long String** | No (auto-detect) | Yes (category + subfolder) |
| **No-Voice** | No (auto-detect) | Yes (category + voiced) |
| **Blacklist** | Yes (validate lang columns) | No |
| **Str Erase** | No | No |
| **File Erase** | No | No |

---

## Excel Folder Support (2026-02-27)

All 4 folder-level engines (Diff folder, Long String, No-Voice, Blacklist target) now support Excel input alongside XML. Previously only single-file operations (Diff file, Str Erase source) handled Excel.

**Changes:**
- `parse_input_folder()` default pattern: `"*.xml"` → `("*.xml", "*.xlsx")` with multi-glob dedup
- `validate_xml_source_folder()` counts both XML and Excel files, reports type breakdown
- GUI labels updated: "languagedata XMLs" → "XML / Excel" (Long String, No-Voice, Blacklist target)
- Engine docstrings updated to reflect XML/Excel support

**Key insight:** The architecture was already Excel-ready at per-file level (`parse_input_file()` auto-detects format). The only bottleneck was the `"*.xml"` default glob in `parse_input_folder()`.

---

## Diff Column Validation (BLOCKING — 2026-02-27)

When an Excel file is missing columns required by the selected compare mode, the diff operation is **blocked before any work starts**. No automatic fallback — the user gets a clear error and must fix the input or change mode.

**Column requirements per mode:**

| Compare Mode | StringID | StrOrigin | Str |
|---|---|---|---|
| Full (all attributes) | REQUIRED | REQUIRED | REQUIRED |
| StrOrigin + StringID | REQUIRED | REQUIRED | — |
| StrOrigin + StringID + Str | REQUIRED | REQUIRED | REQUIRED |
| StringID + Str | REQUIRED | — | REQUIRED |

XML files always pass (they carry `raw_attribs`).

**Defense-in-depth:** `_diff_full()` and `_compute_revert_changes()` in `diff_engine.py` also skip entries where both `str_origin` and `str_value` are empty (catches edge cases where validation was bypassed).

---

## Testing Checklist

- [ ] Launch GUI: `python -m ExtractAnything.main`
- [ ] Browse LOC folder -> log shows language count
- [ ] Browse EXPORT folder -> log shows .loc.xml count + categories
- [ ] Each tab: browse source/target -> validation logged
- [ ] Each tab: run operation -> progress bar moves 0-100
- [ ] Each tab: operation headers visible in log
- [ ] Each tab: per-file parsing feedback in log
- [ ] Each tab: final summary with totals
- [ ] Blacklist: browse Excel -> detects language columns
- [ ] Blacklist: browse folder -> aggregates from multiple files
- [ ] Str Erase: browse source -> counts XML + Excel files
- [ ] File Erase: preview count before confirmation
- [ ] Diff File: Excel missing StrOrigin + "StrOrigin + StringID" mode → BLOCKED
- [ ] Diff File: Excel missing Str + "StringID + Str" mode → BLOCKED
- [ ] Diff File: Excel with all columns + any mode → proceeds
- [ ] Diff File: XML in any mode → proceeds (validation skipped)
- [ ] Diff Folder: folder with bad Excel → BLOCKED, lists the file
- [ ] Diff Folder: all XML → proceeds
- [ ] Revert: Excel Before missing StrOrigin → BLOCKED
- [ ] Revert: both XML → proceeds

---

*Last updated: 2026-02-27*
