# Phase 57: Transfer Service Adapter - Research

**Researched:** 2026-03-23
**Domain:** Python adapter layer wrapping QuickTranslate Sacred Scripts for LocaNext service use
**Confidence:** HIGH

## Summary

Phase 57 creates an adapter layer that imports QuickTranslate's core modules (`xml_transfer`, `postprocess`, `source_scanner`, `language_loader`) via `sys.path` injection, wrapping them as a LocaNext service without copying or modifying any Sacred Script code.

The critical challenge is the `config` module dependency. QuickTranslate modules (`xml_transfer.py`, `source_scanner.py`) import `config` at module level, and `config.py` reads from `settings.json` and has hardcoded `F:\perforce\` defaults. The adapter must inject a synthetic `config` module into `sys.modules` before importing QuickTranslate core modules, providing LocaNext-controlled paths (LOC_FOLDER, EXPORT_FOLDER, SCRIPT_CATEGORIES, LANGUAGE_NAMES).

LocaNext already has an in-memory `TranslatorMergeService` (v2.0) that operates on parsed DB rows. This phase creates a SEPARATE file-based transfer service that operates on XML files on disk -- the actual QuickTranslate workflow for the v6.0 offline showcase.

**Primary recommendation:** Create `server/services/transfer_adapter.py` that (1) injects a config shim into `sys.modules["config"]`, (2) adds QuickTranslate root to `sys.path`, (3) imports and wraps the 4 core modules with LocaNext-friendly function signatures, using loguru instead of stdlib logging.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XFER-01 | Adapter imports QuickTranslate core modules via sys.path | Config shim pattern + sys.path injection documented in Architecture Patterns |
| XFER-02 | StringID Only match type works (case-insensitive, SCRIPT/ALL category filter) | `merge_corrections_stringid_only()` + `_preprocess_stringid_only()` documented with signatures |
| XFER-03 | StringID+StrOrigin match type works (strict 2-key with nospace fallback) | `merge_corrections_to_xml()` with `_build_correction_lookups("strict")` documented |
| XFER-04 | StrOrigin+FileName 2PASS match type works (3-tuple then 2-tuple fallback) | `_build_correction_lookups("strorigin_filename")` PASS1/PASS2 pattern documented |
| XFER-05 | 8-step postprocess pipeline runs after merge | `run_all_postprocess()` and `run_all_postprocess_on_tree()` documented with all 8 steps |
| XFER-06 | Transfer scope works: "Transfer All" vs "Only Untranslated" | `only_untranslated` parameter threaded through all merge functions |
| XFER-07 | Multi-language folder merge with language auto-detection | `scan_source_for_languages()` + `transfer_folder_to_folder()` with language grouping documented |
</phase_requirements>

## Standard Stack

### Core (QuickTranslate modules imported via adapter)

| Module | Location | Purpose | Lines |
|--------|----------|---------|-------|
| `core/xml_transfer.py` | RFC/NewScripts/QuickTranslate/ | All merge functions: strict, stringid_only, strorigin_filename, folder-to-folder | 3064 |
| `core/postprocess.py` | RFC/NewScripts/QuickTranslate/ | 8-step XML cleanup pipeline | 1346 |
| `core/source_scanner.py` | RFC/NewScripts/QuickTranslate/ | Language auto-detection from folder/file structure | 944 |
| `core/language_loader.py` | RFC/NewScripts/QuickTranslate/ | languagedata_*.xml discovery and lookup building | 241 |

### Supporting (QuickTranslate internal dependencies)

| Module | Purpose | Imported By |
|--------|---------|-------------|
| `core/xml_parser.py` | XML sanitization, LocStr iteration, attribute constants | All core modules |
| `core/text_utils.py` | Text normalization (normalize_text, normalize_nospace, normalize_for_matching) | xml_transfer |
| `core/xml_io.py` | Parse corrections from XML source files | xml_transfer (via transfer_folder_to_folder) |
| `core/excel_io.py` | Parse corrections from Excel source files | xml_transfer (via transfer_folder_to_folder) |
| `core/korean_detection.py` | Korean text detection for skip guards | xml_transfer, xml_io |
| `core/eventname_resolver.py` | EventName-to-StringID resolution (StringID-Only mode) | xml_transfer |
| `core/category_mapper.py` | Category mapping | xml_transfer |
| `config.py` | Module-level config (LOC_FOLDER, EXPORT_FOLDER, etc.) | xml_transfer, source_scanner |

### LocaNext Side

| Component | Purpose |
|-----------|---------|
| `server/services/transfer_adapter.py` | NEW: Adapter wrapping QuickTranslate modules |
| `locaNext/src/lib/stores/projectSettings.js` | Per-project locPath/exportPath in localStorage |
| `server/tools/ldm/services/translator_merge.py` | EXISTING v2.0 in-memory merge (NOT replaced, separate concern) |

## Architecture Patterns

### Recommended Project Structure

```
server/services/
    transfer_adapter.py          # NEW: QuickTranslate adapter layer
    transfer_config_shim.py      # NEW: Synthetic config module for QT
    sync_service.py              # EXISTING
    __init__.py                  # EXISTING
```

### Pattern 1: Config Shim (CRITICAL)

**What:** QuickTranslate modules import `config` at module level. `config.py` reads `settings.json` from disk and defaults to `F:\perforce\` paths. We must provide a synthetic `config` module that LocaNext controls.

**When to use:** Before ANY import of QuickTranslate core modules.

**How it works:**
1. Create a `types.ModuleType` object named "config"
2. Set all attributes that QuickTranslate expects: `LOC_FOLDER`, `EXPORT_FOLDER`, `SCRIPT_CATEGORIES`, `SCRIPT_EXCLUDE_SUBFOLDERS`, `LANGUAGE_NAMES`, `FUZZY_THRESHOLD_DEFAULT`, `get_failed_report_dir`
3. Insert into `sys.modules["config"]` BEFORE importing QuickTranslate
4. Add QuickTranslate root to `sys.path[0]`

```python
import sys
import types
from pathlib import Path

def _create_config_shim(loc_path: str, export_path: str) -> types.ModuleType:
    """Create synthetic config module for QuickTranslate imports."""
    config = types.ModuleType("config")
    config.LOC_FOLDER = Path(loc_path)
    config.EXPORT_FOLDER = Path(export_path)
    config.SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}
    config.SCRIPT_EXCLUDE_SUBFOLDERS = set()
    config.LANGUAGE_NAMES = {}  # Will be populated from LOC folder
    config.FUZZY_THRESHOLD_DEFAULT = 0.85
    config.SEQUENCER_FOLDER = Path(export_path) / "Sequencer"
    config.SCRIPT_DIR = Path(loc_path).parent
    config.OUTPUT_FOLDER = Path("/tmp/quicktranslate_output")
    config.SOURCE_FOLDER = Path("/tmp/quicktranslate_source")

    # Auto-discover language names from LOC folder
    if config.LOC_FOLDER.exists():
        import re
        for f in config.LOC_FOLDER.glob("languagedata_*.xml"):
            m = re.match(r'languagedata_(.+)\.xml', f.name, re.IGNORECASE)
            if m:
                code = m.group(1)
                config.LANGUAGE_NAMES[code.upper()] = code.upper()

    return config

def init_quicktranslate(loc_path: str, export_path: str):
    """Initialize QuickTranslate module imports with LocaNext-controlled paths."""
    # Step 1: Create and inject config shim
    config_shim = _create_config_shim(loc_path, export_path)
    sys.modules["config"] = config_shim

    # Step 2: Add QuickTranslate root to sys.path
    qt_root = str(Path(__file__).parent.parent.parent /
                  "RessourcesForCodingTheProject" / "NewScripts" / "QuickTranslate")
    if qt_root not in sys.path:
        sys.path.insert(0, qt_root)

    # Step 3: Now safe to import core modules
    from core.xml_transfer import (
        transfer_folder_to_folder,
        merge_corrections_to_xml,
        merge_corrections_stringid_only,
    )
    from core.postprocess import run_all_postprocess
    from core.source_scanner import scan_source_for_languages
    from core.language_loader import (
        discover_language_files,
        build_translation_lookup,
        build_stringid_to_category,
        build_stringid_to_subfolder,
        build_stringid_to_filepath,
    )

    return {
        "transfer_folder_to_folder": transfer_folder_to_folder,
        "merge_corrections_to_xml": merge_corrections_to_xml,
        "merge_corrections_stringid_only": merge_corrections_stringid_only,
        "run_all_postprocess": run_all_postprocess,
        "scan_source_for_languages": scan_source_for_languages,
        "discover_language_files": discover_language_files,
        "build_translation_lookup": build_translation_lookup,
        "build_stringid_to_category": build_stringid_to_category,
        "build_stringid_to_subfolder": build_stringid_to_subfolder,
        "build_stringid_to_filepath": build_stringid_to_filepath,
    }
```

### Pattern 2: Lazy Loading with Path Reconfiguration

**What:** QuickTranslate paths may change per-project (different projects have different LOC/EXPORT paths). The config shim must be updateable.

**When to use:** When switching between projects or starting a new merge operation.

```python
def reconfigure_paths(loc_path: str, export_path: str):
    """Update QuickTranslate config paths for a different project."""
    config = sys.modules.get("config")
    if config is None:
        return init_quicktranslate(loc_path, export_path)

    config.LOC_FOLDER = Path(loc_path)
    config.EXPORT_FOLDER = Path(export_path)
    config.SEQUENCER_FOLDER = config.EXPORT_FOLDER / "Sequencer"

    # Clear source_scanner's cached language codes (stale after path change)
    from core.source_scanner import clear_language_code_cache
    clear_language_code_cache()
```

### Pattern 3: Match Mode Mapping

**What:** Map LocaNext's 3 user-facing match types to QuickTranslate's internal match_mode strings.

| LocaNext UI | QuickTranslate match_mode | Key Function |
|-------------|---------------------------|--------------|
| StringID Only | `"stringid_only"` | `merge_corrections_stringid_only()` or `transfer_folder_to_folder(match_mode="stringid_only")` |
| StringID+StrOrigin | `"strict"` | `merge_corrections_to_xml()` or `transfer_folder_to_folder(match_mode="strict")` |
| StrOrigin+FileName 2PASS | `"strorigin_filename"` | `transfer_folder_to_folder(match_mode="strorigin_filename")` |

### Pattern 4: Transfer Entry Point

**What:** The main adapter function wraps `transfer_folder_to_folder()` which is the single highest-level function that handles everything: source scanning, language detection, corrections parsing, match mode dispatch, postprocess, and result aggregation.

```python
def execute_transfer(
    source_path: str,
    target_path: str,    # LOC folder (languagedata_*.xml location)
    export_path: str,    # EXPORT folder (for category/filepath lookups)
    match_mode: str,     # "stringid_only" | "strict" | "strorigin_filename"
    only_untranslated: bool = False,
    stringid_all_categories: bool = False,
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
) -> dict:
    """Execute a transfer operation using QuickTranslate's engine."""
    # Ensure config is current
    reconfigure_paths(target_path, export_path)

    # Build category/subfolder maps if needed
    stringid_to_category = None
    stringid_to_subfolder = None
    stringid_to_filepath = None

    if match_mode == "stringid_only":
        stringid_to_category = build_stringid_to_category(Path(export_path))
        stringid_to_subfolder = build_stringid_to_subfolder(Path(export_path))
    elif match_mode == "strorigin_filename":
        stringid_to_filepath = build_stringid_to_filepath(Path(export_path))

    return transfer_folder_to_folder(
        source_folder=Path(source_path),
        target_folder=Path(target_path),
        stringid_to_category=stringid_to_category,
        stringid_to_subfolder=stringid_to_subfolder,
        stringid_to_filepath=stringid_to_filepath,
        match_mode=match_mode,
        dry_run=dry_run,
        progress_callback=progress_callback,
        log_callback=log_callback,
        only_untranslated=only_untranslated,
        stringid_all_categories=stringid_all_categories,
    )
```

### Anti-Patterns to Avoid

- **NEVER copy QuickTranslate code into LocaNext.** Sacred Scripts rule. Import via sys.path only.
- **NEVER modify QuickTranslate source files.** The adapter wraps, it does not patch.
- **NEVER import QuickTranslate modules before injecting the config shim.** Python caches imports -- if `config` is loaded once with wrong paths, all subsequent imports see stale data.
- **NEVER forget to call `clear_language_code_cache()` after changing paths.** `source_scanner.py` caches discovered language codes at module level.
- **NEVER use stdlib `logging` in the adapter.** LocaNext uses loguru. QuickTranslate's internal logging is fine (it uses stdlib), but the adapter layer must use loguru.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML merge matching | Custom match logic | `transfer_folder_to_folder()` | 3064 lines of battle-tested edge cases |
| Postprocess pipeline | Custom XML cleanup | `run_all_postprocess()` | 8 steps with CJK awareness, invisible char buckets |
| Language detection | regex on filenames | `scan_source_for_languages()` | Handles subfolders, suffixes, hyphenated codes (ZHO-CN) |
| Category mapping | DB query for categories | `build_stringid_to_category()` | Scans export folder structure, no DB needed |
| Correction parsing | Custom XML/Excel parser | QuickTranslate's `xml_io.py` + `excel_io.py` | Formula guards, integrity checks, Korean detection |
| Text normalization | Custom normalize | QuickTranslate's `text_utils.py` | HTML unescape, whitespace collapse, case handling |

**Key insight:** QuickTranslate's `transfer_folder_to_folder()` is the all-in-one orchestrator. It handles source scanning, language grouping, per-language target file resolution, match mode dispatch (including pre-building lookups once), postprocess, and result aggregation. The adapter should call THIS function, not the lower-level per-file functions.

## Common Pitfalls

### Pitfall 1: Config Module Import Order

**What goes wrong:** Importing any QuickTranslate `core.*` module before `sys.modules["config"]` is set causes an `ImportError` or loads the wrong `config.py` (LocaNext's `server/config.py` if that's on `sys.path`).

**Why it happens:** Python resolves `import config` at import time. QuickTranslate's `xml_transfer.py` and `source_scanner.py` have `import config` at the top level.

**How to avoid:** Always inject the config shim into `sys.modules["config"]` and add QuickTranslate root to `sys.path[0]` BEFORE any `from core.xxx import` statement.

**Warning signs:** `AttributeError: module 'config' has no attribute 'SCRIPT_CATEGORIES'` or paths pointing to F: drive.

### Pitfall 2: sys.path Pollution

**What goes wrong:** Adding QuickTranslate root to sys.path can cause name collisions (e.g., `config`, `core`, `utils` are generic names).

**Why it happens:** QuickTranslate uses bare `import config` and has a `core/` and `utils/` package that could shadow other modules.

**How to avoid:**
1. Insert at `sys.path[0]` (first position) to ensure QuickTranslate's `config` is found first
2. Do all QuickTranslate imports in a single initialization function
3. After imports are cached in `sys.modules`, the path position matters less
4. Consider removing the QuickTranslate root from `sys.path` after initial import (imports are cached)

### Pitfall 3: Language Code Cache Staleness

**What goes wrong:** `source_scanner.py` caches valid language codes at module level (`_cached_valid_codes`). If LOC_FOLDER changes between projects, stale codes cause wrong language detection.

**Why it happens:** Module-level cache populated on first call, never cleared automatically.

**How to avoid:** Call `clear_language_code_cache()` whenever `config.LOC_FOLDER` changes.

### Pitfall 4: lxml Dependency

**What goes wrong:** QuickTranslate modules try `from lxml import etree` with stdlib fallback. LocaNext's server environment may or may not have lxml installed.

**Why it happens:** QuickTranslate's xml_parser.py, postprocess.py, source_scanner.py, xml_transfer.py all have the try/except lxml import pattern.

**How to avoid:** Verify lxml is installed in LocaNext's Python environment. It should be (LocaNext's XML parsing engine uses lxml). If not, `pip install lxml`. The fallback to stdlib ElementTree works but is less robust (no `recover=True` parser).

### Pitfall 5: Existing LocaNext config.py Collision

**What goes wrong:** LocaNext has `server/config.py` which is a completely different module. If the wrong one loads, everything breaks silently.

**Why it happens:** Both LocaNext and QuickTranslate have a module named `config`. Python path resolution depends on `sys.path` order.

**How to avoid:** The config shim pattern (injecting into `sys.modules["config"]` directly) bypasses path resolution entirely. The key is to set `sys.modules["config"]` BEFORE any QuickTranslate import triggers `import config`.

### Pitfall 6: EventName Resolution in StringID-Only Mode

**What goes wrong:** StringID-Only mode uses `eventname_resolver.get_eventname_mapping(config.EXPORT_FOLDER)` to resolve EventName StringIDs to actual LocStr StringIDs. If EXPORT_FOLDER is wrong or doesn't exist, this fails silently (returns empty mapping).

**Why it happens:** EventName resolution is lazy-loaded in `_preprocess_stringid_only()`. It reads XML files from the export folder.

**How to avoid:** Ensure `config.EXPORT_FOLDER` points to a valid export folder with `.loc.xml` files. For testing with mock data, this may need to be populated or this feature gracefully degrades (EventNames just won't resolve, which is acceptable for demo).

### Pitfall 7: Only Untranslated Scope

**What goes wrong:** The "Only Untranslated" scope (`only_untranslated=True`) checks if target already has non-Korean text in Str attribute. If Str contains ANY non-Korean text, the entry is skipped even if the translation is "no translation".

**Why it happens:** The skip logic in QuickTranslate checks `is_korean_text()` on the existing Str value and skips non-Korean entries.

**How to avoid:** The `_is_no_translation()` guard runs separately and handles "no translation" entries correctly. No adapter-level workaround needed -- just pass `only_untranslated` through to `transfer_folder_to_folder()`.

## Code Examples

### QuickTranslate Function Signatures (Verified from source)

#### transfer_folder_to_folder (main orchestrator)
```python
# Source: RFC/NewScripts/QuickTranslate/core/xml_transfer.py:1709
def transfer_folder_to_folder(
    source_folder: Path,
    target_folder: Path,
    stringid_to_category: Optional[Dict[str, str]] = None,
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    stringid_to_filepath: Optional[Dict[str, str]] = None,
    match_mode: str = "strict",
    dry_run: bool = False,
    progress_callback=None,
    log_callback=None,
    threshold: float = None,
    only_untranslated: bool = False,
    # ... fuzzy params (not needed for Phase 57) ...
    stringid_all_categories: bool = False,
) -> Dict:
```

#### merge_corrections_to_xml (strict mode, per-file)
```python
# Source: RFC/NewScripts/QuickTranslate/core/xml_transfer.py:392
def merge_corrections_to_xml(
    xml_path: Path,
    corrections: List[Dict],
    dry_run: bool = False,
    only_untranslated: bool = False,
    _prebuilt_lookup=None,
) -> Dict:
    # Returns: {"matched", "updated", "not_found", "strorigin_mismatch",
    #           "skipped_translated", "errors", "by_category", "details"}
```

#### merge_corrections_stringid_only (stringid mode, per-file)
```python
# Source: RFC/NewScripts/QuickTranslate/core/xml_transfer.py:606
def merge_corrections_stringid_only(
    xml_path: Path,
    corrections: List[Dict],
    stringid_to_category: Dict[str, str],
    stringid_to_subfolder: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    only_untranslated: bool = False,
    _prebuilt_lookup=None,
) -> Dict:
    # Returns: {"matched", "updated", "skipped_non_script", "skipped_excluded",
    #           "skipped_translated", "skipped_empty_strorigin", "not_found", "errors"}
```

#### run_all_postprocess (8-step pipeline)
```python
# Source: RFC/NewScripts/QuickTranslate/core/postprocess.py:1024
def run_all_postprocess(xml_path: Path, dry_run: bool = False) -> dict:
    # Returns: {"newlines_fixed", "empty_strorigin_cleaned", "no_translation_replaced",
    #           "apostrophes_normalized", "hyphens_normalized", "ellipsis_normalized",
    #           "entities_decoded", "spaces_normalized", "invisibles_removed",
    #           "invisible_detail", "grey_zone_detected", "total_fixes"}
```

#### scan_source_for_languages (language detection)
```python
# Source: RFC/NewScripts/QuickTranslate/core/source_scanner.py:178
def scan_source_for_languages(source_path: Path) -> SourceScanResult:
    # Returns SourceScanResult with:
    #   .lang_files: Dict[str, List[Path]]  # {lang_code: [files]}
    #   .unrecognized: List[Path]
    #   .warnings: List[str]
    #   .total_files: int
    #   .language_count: int
    #   .get_languages(): List[str]
```

#### build_stringid_to_category (category mapping)
```python
# Source: RFC/NewScripts/QuickTranslate/core/language_loader.py:97
def build_stringid_to_category(
    export_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    # Scans export_folder subfolders, returns {StringID: category_name}
```

#### build_stringid_to_filepath (for strorigin_filename mode)
```python
# Source: RFC/NewScripts/QuickTranslate/core/language_loader.py:194
def build_stringid_to_filepath(
    export_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    # Scans export_folder, returns {StringID_lower: relative_filepath}
```

### 8-Step Postprocess Pipeline Detail

| Step | Function | What It Does | CJK Aware |
|------|----------|-------------|-----------|
| 1 | `cleanup_wrong_newlines` | ALL newline variants -> `<br/>` (20+ patterns) | No |
| 2 | `cleanup_empty_strorigin` | Clear Str/Desc when StrOrigin/DescOrigin is empty | No |
| 3 | `cleanup_no_translation` | Replace "no translation" Str with StrOrigin | No |
| 4 | `cleanup_apostrophes` | 6 curly/fancy apostrophe variants -> ASCII `'` | No |
| 5 | `cleanup_invisible_chars` | 3 buckets: Zs spaces->space, 19 safe invisible->delete, grey zone->warn | Yes (preserves U+3000 CJK space) |
| 6 | `cleanup_hyphens` | U+2010, U+2011 -> ASCII `-` | No |
| 7 | `cleanup_ellipsis` | U+2026 `...` -> `...` | Yes (skips KOR, JPN, ZHO) |
| 8 | `cleanup_double_escaped` | `&lt;`/`&gt;`/`&quot;`/`&apos;`/`&amp;ENTITY;` | No |

### 3 Match Types Detail

**StringID Only (`stringid_only`):**
- Key: `StringID.lower()`
- Pre-filter: Only SCRIPT categories (Dialog/Sequencer) unless `stringid_all_categories=True`
- Subfolder exclusion via `SCRIPT_EXCLUDE_SUBFOLDERS` (currently empty set)
- EventName resolution: tries to resolve EventName IDs to real LocStr StringIDs
- Case-insensitive StringID matching

**StringID+StrOrigin Strict (`strict`):**
- Key: `(StringID.lower(), normalize_text(StrOrigin))`
- Nospace fallback: `(StringID.lower(), normalize_nospace(StrOrigin))` for whitespace variations
- Both StringID AND StrOrigin must match
- Category tracking per match

**StrOrigin+FileName 2PASS (`strorigin_filename`):**
- PASS 1 (3-tuple): `(normalize_for_matching(StrOrigin), filepath, normalize_for_matching(DescOrigin))`
- PASS 2 (2-tuple fallback): `(normalize_for_matching(StrOrigin), filepath)`
- Requires `stringid_to_filepath` mapping from export folder
- `normalize_for_matching` = html.unescape + whitespace collapse + lowercase

### Multi-Language Folder Merge Flow

```
1. scan_source_for_languages(source_folder) -> SourceScanResult
   - Detects: FRE/, corrections_FRE/, file_GER.xml, languagedata_ENG.xml
   - Language suffix extraction: underscore-separated, standalone codes, hyphenated (ZHO-CN)
   - Returns {lang_code: [file_paths]} mapping

2. For each language group:
   - Find matching target files in LOC folder (languagedata_{LANG}.xml)
   - Parse all source corrections (XML or Excel)
   - Build match lookups ONCE per language group
   - Run fast_folder_merge on target files
   - Postprocess runs after every file merge

3. Aggregate results across all languages
```

## State of the Art

| Old Approach (v2.0) | New Approach (v6.0 Phase 57) | Impact |
|---------------------|------------------------------|--------|
| `TranslatorMergeService` operates on in-memory DB rows | Adapter wraps file-based QuickTranslate directly | Real offline workflow, identical to standalone QT |
| Separate `text_matching.py` with LocaNext-specific normalize | QuickTranslate's own `text_utils.py` normalization | Guaranteed parity with standalone results |
| No postprocess on DB rows | Full 8-step pipeline on XML files | Clean output files |
| No multi-language support | `scan_source_for_languages()` handles any folder structure | Batch processing |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in project) |
| Config file | None -- needs creation or use existing pattern |
| Quick run command | `python -m pytest tests/test_transfer_adapter.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XFER-01 | Adapter imports QT modules via sys.path | unit | `pytest tests/test_transfer_adapter.py::test_import_with_config_shim -x` | Wave 0 |
| XFER-02 | StringID Only match type works | integration | `pytest tests/test_transfer_adapter.py::test_stringid_only_transfer -x` | Wave 0 |
| XFER-03 | StringID+StrOrigin strict match works | integration | `pytest tests/test_transfer_adapter.py::test_strict_transfer -x` | Wave 0 |
| XFER-04 | StrOrigin+FileName 2PASS works | integration | `pytest tests/test_transfer_adapter.py::test_strorigin_filename_transfer -x` | Wave 0 |
| XFER-05 | 8-step postprocess runs after merge | integration | `pytest tests/test_transfer_adapter.py::test_postprocess_pipeline -x` | Wave 0 |
| XFER-06 | Transfer scope (all vs untranslated) | integration | `pytest tests/test_transfer_adapter.py::test_only_untranslated_scope -x` | Wave 0 |
| XFER-07 | Multi-language folder merge | integration | `pytest tests/test_transfer_adapter.py::test_multi_language_merge -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_transfer_adapter.py -x -q`
- **Per wave merge:** Full suite
- **Phase gate:** All 7 XFER tests green before verify

### Wave 0 Gaps
- [ ] `tests/test_transfer_adapter.py` -- covers XFER-01 through XFER-07
- [ ] Test fixtures: small XML files with known LocStr entries for deterministic merge results

## Open Questions

1. **Export folder for mock data**
   - What we know: Phase 56 created mock projects with languagedata files in LOC. Mock script uses real test data from `C:\Users\MYCOM\Desktop\oldoldVold\test123`.
   - What's unclear: Does the mock data include an export folder with `.loc.xml` files organized by category? StringID-Only and StrOrigin+FileName modes need `build_stringid_to_category()` and `build_stringid_to_filepath()` which scan the export folder.
   - Recommendation: For Plan 57-02, if no export folder exists in mock data, either (a) create a minimal export folder with category subfolders, or (b) make category/filepath maps optional with graceful degradation (StringID-Only falls back to ALL categories, StrOrigin+FileName falls back to StrOrigin-only matching).

2. **lxml availability**
   - What we know: LocaNext's server uses lxml (XMLParsingEngine). QuickTranslate has try/except fallback to stdlib.
   - What's unclear: Whether the exact same lxml version is available in the Python environment where the adapter runs.
   - Recommendation: Verify with `python -c "from lxml import etree; print(etree.LXML_VERSION)"`. This is LOW risk since LocaNext already uses lxml.

## Sources

### Primary (HIGH confidence)
- `RFC/NewScripts/QuickTranslate/core/xml_transfer.py` (3064 lines) -- read directly, all function signatures verified
- `RFC/NewScripts/QuickTranslate/core/postprocess.py` (1346 lines) -- read directly, 8-step pipeline verified
- `RFC/NewScripts/QuickTranslate/core/source_scanner.py` (944 lines) -- read directly, language detection logic verified
- `RFC/NewScripts/QuickTranslate/core/language_loader.py` (241 lines) -- read in full, all builder functions verified
- `RFC/NewScripts/QuickTranslate/config.py` -- read directly, dependency analysis complete
- `server/tools/ldm/services/translator_merge.py` -- read directly, confirmed separate concern
- `locaNext/src/lib/stores/projectSettings.js` -- read in full, per-project paths confirmed

### Secondary (MEDIUM confidence)
- Memory files: `quicktranslate_overview.md`, `quicktranslate_postprocess.md` -- cross-verified with source

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all modules read directly from source, function signatures verified
- Architecture: HIGH -- config shim pattern is well-understood, existing sys.path patterns in codebase (6 instances)
- Pitfalls: HIGH -- identified from direct code analysis of import chains and module-level state

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- QuickTranslate is Sacred Script, won't change)
