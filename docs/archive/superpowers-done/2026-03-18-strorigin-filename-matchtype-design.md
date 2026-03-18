# Design: `strorigin_filename` Match Mode for QuickTranslate

**Date:** 2026-03-18
**Status:** Approved
**Scope:** New 2-pass match type using export filepath as matching key component

---

## Problem

Current match modes (strict, strorigin_only, strorigin_descorigin, stringid_only) lack file-context awareness. When the same StrOrigin text appears in multiple files (e.g., a shared label like "Name" in both `characterinfo.loc.xml` and `iteminfo.loc.xml`), strorigin_only mode cannot disambiguate — it fills ALL occurrences. The user needs a mode that matches by text content AND file location.

## Solution

A new `strorigin_filename` match mode with 2 passes:

- **PASS 1 (Precise):** Key = `(normalized_StrOrigin, export_filepath, normalized_DescOrigin)`
- **PASS 2 (Relaxed):** Key = `(normalized_StrOrigin, export_filepath)`

PASS 2 only runs on corrections that PASS 1 didn't match, catching cases where DescOrigin changed or is empty.

## Key Component: Export Filepath Index

The existing `build_export_stringid_index()` in `core/missing_translation_finder.py:318-360` already builds `{StringID: relative_filepath}` from the export folder. Example:

```
"STR_CHARACTER_NAME_001" → "UI/characterinfo.loc.xml"
"STR_DIALOG_INTRO_042"  → "Dialog/NarrationDialog/intro.loc.xml"
```

Both source corrections and target LocStr elements resolve their filepath via the same export index (by StringID lookup). Same source of truth = clean, consistent matching.

## Architecture

### Data Flow

```
Export Folder (export__)
    ↓ build_stringid_to_filepath()
StringID (lowercased) → filepath index (cached on self)
    ↓ passed into transfer pipeline
_build_correction_lookups(corrections, match_mode, stringid_to_filepath):
    For each correction:
        filepath = stringid_to_filepath.get(correction["string_id"].lower(), "")
        PASS1 key = (norm_strorigin, filepath, norm_descorigin)
        PASS2 key = (norm_strorigin, filepath)
    ↓
_fast_folder_merge(target_files, ..., stringid_to_filepath):
    For each target LocStr:
        filepath = stringid_to_filepath.get(target_sid.lower(), "")
        Try PASS1 key → miss → Try PASS2 key
        If match: apply correction
```

### Lookup Dict Structure

Reuses the existing `(correction_lookup, correction_lookup_nospace)` return contract:

- `correction_lookup` = **PASS 1 dict** with 3-tuple keys `(norm_strorigin, filepath, norm_descorigin)`
- `correction_lookup_nospace` = **PASS 2 dict** with 2-tuple keys `(norm_strorigin, filepath)`

Values: `[(corrected_text, category, index), ...]` — same as `strict` and `strorigin_descorigin` modes.

This keeps the return shape identical to all other modes — zero impact on callers.

### Normalization

- **StrOrigin:** `normalize_for_matching()` (lowercase + whitespace collapse) — same as `strorigin_descorigin` mode
- **DescOrigin:** `normalize_for_matching()` — same as `strorigin_descorigin` mode
- **Filepath:** Used as-is from the export index (already normalized with forward slashes)
- **StringID for index lookup:** `.lower()` on BOTH insert (in `build_stringid_to_filepath`) AND lookup — case-insensitive throughout

### Missing StringIDs

If a StringID is not in the export index (stale export, unreleased content):
- `filepath` resolves to `""` (empty string)
- Correction with `filepath=""` can only match target with `filepath=""` — safe, no false matches
- Log a warning if >10% of StringIDs are missing from the export index

### Error Handling

- `_build_correction_lookups()`: Add `raise ValueError(f"Unknown match_mode: {match_mode}")` instead of silent `return None, None` fallthrough — prevents silent crash if mode string is mistyped
- `_fast_folder_merge()`: Same — explicit error for unknown mode

## Files to Modify

| # | File | Change | Lines |
|---|------|--------|-------|
| 1 | `core/language_loader.py` | Add `build_stringid_to_filepath()` — adapt logic from `missing_translation_finder.build_export_stringid_index`, store as `{sid.lower(): filepath}` | ~25 new lines |
| 2 | `config.py` | Add `"strorigin_filename"` to `MATCHING_MODES` dict | 1 line |
| 3 | `core/xml_transfer.py` `_build_correction_lookups()` | Add `stringid_to_filepath` param + new `elif strorigin_filename` branch building PASS1 + PASS2 dicts | ~30 new lines |
| 4 | `core/xml_transfer.py` `_fast_folder_merge()` | Add `stringid_to_filepath` param + new `elif strorigin_filename` branch with 2-pass matching | ~35 new lines |
| 5 | `core/xml_transfer.py` `transfer_folder_to_folder()` | Add `stringid_to_filepath` param, pass through to `_build_correction_lookups` and `_fast_folder_merge` | ~15 new lines |
| 6 | `gui/app.py` `_load_data_if_needed()` | Add `self.stringid_to_filepath`, build with `build_stringid_to_filepath()` | ~8 new lines |
| 7 | `gui/app.py` `_run_transfer_thread()` | Add to transfer mode mapping block (line ~3205), add to `transfer_kwargs`, extend load condition | ~10 new lines |
| 8 | `gui/app.py` `_on_match_type_changed()` | Add `elif "strorigin_filename"` — show `precision_options_frame` (no fuzzy), hide `stringid_all_frame`, hide `strict_non_script_frame` | ~8 new lines |
| 9 | `gui/app.py` `_update_match_type_availability()` | Add prerequisite: requires StrOrigin + Correction columns AND export folder set | ~8 new lines |
| 10 | `gui/app.py` `_validate_columns_for_mode()` | Add validation entry for `strorigin_filename` — requires StrOrigin column | ~5 new lines |
| 11 | `gui/app.py` | Add radio button for `strorigin_filename` in Transfer tab | ~5 new lines |

**Total: ~150 new lines across 4 files. No structural changes.**

## GUI Integration

The new mode appears as a radio button option in the Transfer tab match type selector, alongside the existing modes (Strict, StrOrigin Only, StrOrigin+DescOrigin, StringID Only).

### Sub-frame visibility (in `_on_match_type_changed`)
- `precision_options_frame`: **HIDDEN** (no fuzzy variant for this mode)
- `transfer_scope_frame`: **SHOWN** (all strings / untranslated only)
- `unique_only_frame`: **HIDDEN** (filepath disambiguates — no need for unique filter)
- `strict_non_script_frame`: **HIDDEN** (not relevant)
- `stringid_all_frame`: **HIDDEN** (not StringID mode)

### Prerequisites (in `_update_match_type_availability`)
- Source must have StrOrigin + Correction columns
- Export folder must be set (same gate as StringID-Only mode)
- Radio button disabled with tooltip if prerequisites not met

## Edge Cases

| Case | Behavior |
|------|----------|
| StringID not in export index | filepath = "", matches only other missing strings — effectively NOT_FOUND |
| Empty StrOrigin | Skipped (golden rule — same as all modes) |
| Empty DescOrigin in source | PASS 1 miss (descorigin part of key), PASS 2 catches it |
| Empty DescOrigin in target | Same — PASS 1 miss, PASS 2 catches it |
| Duplicate StrOrigin across files | Correctly disambiguated by filepath — this is the whole point |
| Source from Excel (no StringID) | Cannot resolve filepath → NOT_FOUND. Excel mode needs FileName column OR StringID column |
| Unknown match_mode string | `ValueError` raised immediately — no silent fallthrough |

## Testing Strategy

1. Unit test `build_stringid_to_filepath()` with mock export folder — verify `{sid.lower(): relpath}` output
2. Unit test `_build_correction_lookups()` for `strorigin_filename` mode — verify PASS1 (3-tuple) and PASS2 (2-tuple) dicts
3. Integration test: source with duplicate StrOrigin in different files → verify only correct file gets the correction
4. Integration test: PASS1 miss (DescOrigin mismatch) → verify PASS2 catches it
5. Edge case: StringID not in export index → verify NOT_FOUND, no crash
6. Edge case: unknown match_mode → verify ValueError raised
