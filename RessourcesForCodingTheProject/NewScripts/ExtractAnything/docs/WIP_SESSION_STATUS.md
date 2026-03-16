# ExtractAnything — Session Status

> **Purpose:** Recovery doc so we never lose context when sessions get cut off.
> **Last updated:** 2026-03-16

---

## What Was Done (Previous Session)

Ported all QuickTranslate safeguards to ExtractAnything — 7 files modified:

| Safeguard | File | Status |
|-----------|------|--------|
| Control char stripping | xml_parser.py | IMPROVED (precompiled regex) |
| `<seg>` newline preprocessing | xml_parser.py | IMPROVED (precompiled regex) |
| Tag stack repair | xml_parser.py | IDENTICAL to QT |
| `huge_tree=True` on all parsers | xml_parser.py | IMPROVED (all 4 sites vs QT's 2/9) |
| File permission handling | xml_parser.py | IMPROVED (centralized) |
| 7-step `normalize_newlines()` | text_utils.py | IDENTICAL to QT |
| `has_wrong_newlines()` | text_utils.py | IDENTICAL to QT |
| `convert_linebreaks_for_xml()` | text_utils.py | IDENTICAL to QT |
| `br_to_newline()` | text_utils.py | New (QT doesn't need) |
| `~$` temp file filtering | excel_reader.py, input_parser.py | All entry points covered |
| Excel `\n` → `<br/>` on read | excel_reader.py | Applied to StrOrigin + Str |
| `<br/>` → `\n` on Excel write | excel_writer.py | With text_wrap format |
| Backup before destructive write | string_eraser_engine.py | shutil.copy2 |
| Backup before revert write | diff_engine.py | shutil.copy2 |

## 4-Agent Review Results (Current Session)

### Agent 1 — XML Safeguards: ALL PASS
- 8/8 checks: IDENTICAL or IMPROVED vs QT
- Bad ampersand regex is stricter/more correct
- `_escape_attr_lt` preserves `<br/>` (QT destroys them)
- XXE prevention flags consistent on all parsers

### Agent 2 — Text/Newline Safeguards: 2 CRITICAL ISSUES FOUND
- **CRITICAL:** `normalize_newlines()` defined but NEVER CALLED (dead code)
- **CRITICAL:** `has_wrong_newlines()` defined but NEVER CALLED (dead code)
- **CRITICAL:** XML→XML path passes raw `\n` without `<br/>` conversion
- **FIX:** Call `normalize_newlines()` on StrOrigin and Str in `input_parser.parse_xml_entries()`

### Agent 3 — Excel/Backup Safeguards: 1 CRITICAL ISSUE
- **CRITICAL:** Backup failure doesn't abort destructive write
- **FIX:** Add `backup_ok` flag, skip write if backup fails
- Minor: `~$` filter missing in `string_eraser_engine.load_source_keys()` loop level

### Agent 4 — StrOrigin/Data Integrity: MOSTLY GOOD
- All attribute variants identical to QT (STRINGID_ATTRS, STRORIGIN_ATTRS, LOCSTR_TAGS)
- Empty StrOrigin/translation cleanup is NOT APPLICABLE (EA is extraction, not transfer)
- Warning: Silent file drops on encoding failure (logger only, no GUI notification)
- Warning: `_MULTILINE_KEYS` missing `"correction"` column

## Issues Fixed (Current Session)

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | `normalize_newlines()` never called | input_parser.py | Call on so/sv after get_attr() |
| 2 | `has_wrong_newlines()` never called | (exported but used by normalize path) | Exported from __init__.py |
| 3 | Backup failure doesn't abort write | string_eraser_engine.py, diff_engine.py | backup_ok flag |
| 4 | `~$` filter missing in eraser loop | string_eraser_engine.py | Added at loop level |
| 5 | `_MULTILINE_KEYS` incomplete | excel_writer.py | Added "correction" |

## Diff Tab Enhancements (2026-03-16, Builds 027-029)

Three builds adding smart diff filtering and visualization:

### Build 027 — Non-Letter Filter Checkbox

Added `☑ Filter non-letter-only changes` checkbox to both File Diff and Folder Diff sub-tabs. When enabled, entries where the Str diff consists only of punctuation, quotes, special unicode spaces, or symbols are filtered out. At least one letter change (`str.isalpha()`) or `<br/>` count change required to keep an entry.

**Core function:** `has_letter_change(old_str, new_str)` in `text_utils.py` — character-level `SequenceMatcher`, None-safe, handles `<br/>` as structural change.

**Files:** `text_utils.py`, `diff_engine.py` (`_filter_nonletter_changes` post-filter), `diff_tab.py` (checkbox UI).

### Build 028 — Str Diff Mode (6th Compare Mode)

New dedicated "Str Diff" mode — matches by StringID (must exist in both source and target), compares `str_value`, shows word-level diff visualization.

**Output columns:** `StringID | StrOrigin | Old Str | New Str | Str Diff`

Mirrors existing "StrOrigin Diff" pattern but for translated text. Composes with the non-letter filter checkbox.

**Files:** `diff_engine.py` (`_diff_str`), `config.py` (COMPARE_MODES), `diff_tab.py` (columns), `validators.py` (`_DIFF_MODE_COLUMNS`), `excel_writer.py` (`_MULTILINE_KEYS`).

### Build 029 — Universal Word-Level Diff Enrichment

Added `_enrich_with_diffs()` post-step that runs on ALL diff modes. For any entry with a matching StringID in source, computes:

- `_old_str` / `_str_diff` — when Str changed
- `_old_strorigin` / `_strorigin_diff` — when StrOrigin changed

Uses `extract_differences()` (same word-level difflib from QuickTranslate failure reports). Dedicated Str Diff / StrOrigin Diff modes skip re-enrichment via key-existence guards.

**Key fixes from review:** Case-sensitive enrichment (so case-only changes get visualization), empty-to-text transitions enriched, Excel `_MULTILINE_KEYS` updated for `<br/>` rendering.

### Current Diff Tab Capabilities

| Mode | Match Key | Diff Visualization |
|------|-----------|-------------------|
| Full (all attributes) | StringID | ADD/EDIT tag + Old Str/StrOrigin + word-level diff |
| StrOrigin + StringID | (StrOrigin, SID) | Old Str/StrOrigin + word-level diff |
| StrOrigin + StringID + Str | (StrOrigin, SID, Str) | Old Str/StrOrigin + word-level diff |
| StringID + Str | (SID, Str) | Old Str/StrOrigin + word-level diff |
| StrOrigin Diff | StringID (both must exist) | Old StrOrigin + StrOrigin Diff + cross-enriched Str diff |
| Str Diff | StringID (both must exist) | Old Str + Str Diff + cross-enriched StrOrigin diff |

**Filters:** Category filter (All / SCRIPT / NON-SCRIPT) + Non-letter filter checkbox.

---

## New Feature: Path-Based String Extraction (Planned)

**Concept:** Allow users to SELECT specific export paths (e.g., `Dialog/Sequencer`, `System/Item`) and only extract strings from those paths. Everything outside selected paths is ignored.

**Approach:** Reuse QuickTranslate's EXCLUDE path GUI (the sub-window popup from Find Missing Translation) but as an INCLUDE/SELECT mode. The GUI component should be reusable for future tools.

**Status:** Planning phase (PRXR protocol)
