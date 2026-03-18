# Header-Name Column Matching — Kill Position Fallback

**Date:** 2026-03-17
**Status:** Approved
**Scope:** QA Compiler matching layer (`core/matching.py`, `core/compiler.py`, `core/tracker_update.py`, `core/excel_ops.py`, `config.py`)

## Problem

`TRANSLATION_COLS` in `config.py` hardcodes column positions per category for row matching during compilation. Every generator already writes explicit, unique header names. The position numbers are fragile and already wrong for Gimmick (`{"eng": 2, "other": 3}` points to GroupInfo/Original KR instead of actual translation columns 4/5).

## Solution

Replace all position-based column lookups with header-name matching. The system already has `find_column_by_header()` and uses it for Script categories. Extend this to ALL categories.

### Translation Column Detection Logic

New function `find_translation_column(ws_or_col_idx, is_english)`:

1. Scan headers for prefix match (case-insensitive):
   - **ENG workbooks:** Match header starting with `"ENGLISH"` or exactly `"TRANSLATION (ENG)"`
   - **OTHER workbooks:** Match header starting with `"TRANSLATION"` (but NOT `"TRANSLATION (ENG)"`)
2. If no prefix match found, try existing `find_column_by_header(ws, "Text")` (Script compatibility)
3. **No position fallback.** If header not found, return None and log warning.

### Files Modified

1. **`core/matching.py`** — Add `find_translation_column()`. Update `build_master_index()`, `extract_qa_row_data()`, `extract_qa_row_data_fast()`, `get_translation_column()` to use header-name detection. Remove position-based `get_translation_column()`.
2. **`core/compiler.py`** — Replace `TRANSLATION_COLS.get()` with header-name lookup.
3. **`core/tracker_update.py`** — Replace `TRANSLATION_COLS.get()` with header-name lookup.
4. **`core/excel_ops.py`** — Replace `TRANSLATION_COLS.get()` with header-name lookup.
5. **`config.py`** — Delete `TRANSLATION_COLS` dict entirely.

### What Does NOT Change

- No generator files touched
- No Excel output format changes
- No existing QA file compatibility broken
- Script categories already work by header name — no change needed

### Risk

Low. Replacing fragile position system with robust header-name system already proven on Script categories. All 10 generators verified to write consistent headers.
