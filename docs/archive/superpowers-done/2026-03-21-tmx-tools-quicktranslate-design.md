# TMX Tools Tab — QuickTranslate Integration

**Date:** 2026-03-21
**Status:** Completed (2026-03-21)
**Scope:** Add TMX Tools as Tab 3 in QuickTranslate with 3 functions + fix postprocessor gaps

---

## Goal

Integrate TMX conversion and cleaning into QuickTranslate as a new "TMX Tools" tab (Tab 3). Three functions:

1. **MemoQ-TMX Conversion** (single file) — XML folder → MemoQ-formatted TMX
2. **MemoQ-TMX Batch** (multi-folder) — Multiple XML folders → multiple MemoQ TMX files
3. **TMX Cleaner → Excel** — TMX file → clean + dedup → Excel

Also fix critical gaps in `postprocess_tmx_string` discovered during TMX cleaner development.

---

## Files to Create

| File | Purpose |
|------|---------|
| `QuickTranslate/core/tmx_tools.py` | All TMX business logic (clean, postprocess, convert, export) |
| `QuickTranslate/gui/tmx_tools_tab.py` | Tab 3 GUI (buttons, dialogs, threading) |

## Files to Modify

| File | Change |
|------|--------|
| `QuickTranslate/gui/app.py` | Add Tab 3 to notebook, import tmx_tools_tab |
| `QuickTranslate/core/__init__.py` | Export tmx_tools public API |

---

## Module Design: `core/tmx_tools.py`

### Section 1: TMX Cleaning (ported from tmx_cleaner.py)

All compiled regex patterns + `clean_segment()` + `clean_tmx_string()`.

Handles: MemoQ bpt/ept (all categories, both quote styles), ph with/without val, self-closing ph, fmt ph, Trados bpt/ept/it, Phrase ph, generic x/g tags, zero-width chars, br normalization.

### Section 2: MemoQ Postprocessing (FIXED)

`postprocess_tmx_string()` — ported from tmxconvert41.py with these fixes:

**Fix 1 — Generalize StaticInfo pattern:**
```python
# OLD (broken): only Knowledge
sk_pattern = re.compile(r'\{Staticinfo:Knowledge:([^#}]+)#([^}]+)\}')

# NEW: any category (Knowledge, Item, Character, etc.)
sk_pattern = re.compile(r'\{Static[Ii]nfo:(\w+):([^#}]+)#([^}]+)\}')
```

**Fix 2 — Use mq:rxt-req (not mq:rxt) for BOTH bpt AND ept StaticInfo tags:**
```python
# OLD: mq:rxt (non-required) in bpt
bpt = f"<bpt i='{i}'>&lt;mq:rxt displaytext=&quot;..."
# OLD: mq:rxt in ept
ept = f"<ept i='{i}'>&lt;/mq:rxt displaytext=&quot;..."

# NEW: mq:rxt-req in BOTH (matches real MemoQ exports)
bpt = f"<bpt i='{i}'>&lt;mq:rxt-req displaytext=&quot;..."
ept = f"<ept i='{i}'>&lt;/mq:rxt-req displaytext=&quot;..."
```

**Fix 3 — Dynamic category in val + normalize casing to `StaticInfo`:**
```python
# OLD: hardcoded Staticinfo:Knowledge
val=&quot;{Staticinfo:Knowledge:{ident}#&quot;

# NEW: uses captured category, normalizes to StaticInfo (capital I)
# This matches tmx_cleaner.py's output which also normalizes to StaticInfo
val=&quot;{StaticInfo:{category}:{ident}#&quot;
```

**Fix 4 — Update exclusion regex for generic {…}:**
```python
# OLD: only excludes Staticinfo:Knowledge
r'\{(?!Staticinfo:Knowledge:)([^}]+)\}'

# NEW: excludes any StaticInfo category
r'\{(?!Static[Ii]nfo:\w+:)([^}]+)\}'
```

**Fix 5 — Strip trailing whitespace (keep rstrip, not lstrip):**
```python
# KEEP: rstrip() only — some game strings have intentional leading spaces
# MemoQ's 99% match issue is caused by trailing whitespace, not leading
content.rstrip()
```
Note: Leading whitespace is preserved because game dialogue strings may use intentional indentation.

### Section 3: Conversion Pipeline

Ported from tmxconvert41.py:
- `combine_xmls_to_tmx(folder, output, lang, postprocess)` — core conversion
- `batch_tmx_from_folders(folders, output_dir, lang, postprocess)` — batch wrapper

### Section 4: TMX → Excel

Ported from tmx_cleaner.py:
- `parse_tmx_to_rows(fpath)` — parse + clean + extract metadata
- `dedup_rows(rows)` — dedup by (x-context, ko_seg), keep latest changedate
- `write_excel(rows, output_path)` — xlsxwriter with autofilter
- `clean_and_convert_to_excel(fpath)` — full pipeline

**Excel column names (merge-ready):**

| TMX field | Excel column | Why |
|-----------|-------------|-----|
| KO seg (source) | `StrOrigin` | Matches LocStr attribute name — directly mergeable |
| EN seg (target) | `Correction` | Standard correction column for transfer tools |
| x-context | `StringID` | Matches LocStr StringID attribute |
| Other metadata | `changedate`, `x-document`, etc. | Kept for reference but not required for merge |

---

## GUI Design: `gui/tmx_tools_tab.py`

```
┌─────────────────────────────────────────────┐
│  TMX Tools                                  │
├─────────────────────────────────────────────┤
│  ▸ MemoQ-TMX Conversion                    │
│    Source Folder: [Select Folder]           │
│    Target Language: [dropdown ▼]            │
│    [Convert Single File]  [Batch Convert]   │
├─────────────────────────────────────────────┤
│  ▸ TMX Cleaner → Excel                     │
│    [Select TMX File → Clean & Export]       │
├─────────────────────────────────────────────┤
│  (space for future tools)                   │
└─────────────────────────────────────────────┘
```

- All operations run in threads (same pattern as existing tabs)
- Log output goes to shared right-side log pane
- Language dropdown uses `config.LANGUAGE_ORDER` + `config.LANGUAGE_NAMES` (same as app.py's existing language selection)
- All new files must include `from __future__ import annotations` per project rules

---

## Dependencies

No new dependencies. QuickTranslate already has: lxml, openpyxl, xlsxwriter.

---

## What We Don't Touch

- Tab 1 (Transfer) — unchanged
- Tab 2 (Other Tools) — unchanged
- tmxconvert41.py — stays as standalone, we PORT logic not import it
- tmx_cleaner.py — stays as standalone, we PORT logic not import it

---

## Implementation Order

1. Create `core/tmx_tools.py` with all 4 sections (clean, postprocess-fixed, convert, excel)
2. Write tests for the postprocessor fixes (StaticInfo:Item, Character, trailing spaces)
3. Create `gui/tmx_tools_tab.py` with 3 GUI sections
4. Wire Tab 3 into `gui/app.py`
5. Update `core/__init__.py` exports
6. Test end-to-end
