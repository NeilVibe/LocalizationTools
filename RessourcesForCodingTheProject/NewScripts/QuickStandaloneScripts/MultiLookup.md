# MultiLookup v1.1

**Excel-to-Excel lookup transfer with multi-file support, normalized key matching, and composite keys.**

Single-file QSS tool: `multi_lookup.py`. No dependencies on LocaNext or other QSS tools.

---

## What It Does

Build a **lookup dictionary** from one or more SOURCE Excel files, then write matched values into one or more TARGET Excel files.

```
SOURCE files                         TARGET files
┌──────────────────────┐             ┌──────────────────────────────┐
│ KEY col  │ VALUE col  │             │ KEY col  │ ... │ WRITE col   │
├──────────┼────────────┤             ├──────────┼─────┼─────────────┤
│ item_001 │ Sword      │  ────────→  │ item_001 │ ... │ Sword       │
│ item_002 │ Shield     │  (matched)  │ item_002 │ ... │ Shield      │
│ item_003 │ Potion     │             │ item_099 │ ... │ (no match)  │
└──────────┴────────────┘             └──────────┴─────┴─────────────┘
           ↓
    {normalized_key: value}
    one unified dictionary
    from ALL source files
```

Think of it as a **programmable VLOOKUP across multiple files** — but with normalized key matching that handles the messy reality of game localization data.

---

## How To Run

```bash
python multi_lookup.py
```

Dependencies: `pip install openpyxl`

Can be bundled with PyInstaller for standalone `.exe` distribution.

---

## Features

### Multi-File Source & Target

Add 1+ Excel files on each side. All source files compile into ONE unified dictionary. All target files are written in a single pass.

### Per-File Configuration

Each file gets its own:
- **Sheet** selection (auto-detected on file add)
- **KEY column** (combobox populated from row 1 headers)
- **KEY Col 2** (optional — for composite key matching on 2 columns)
- **VALUE column** (source) or **WRITE column** (target)

Click a file in the listbox → config panel updates. Switch between files freely — **selections persist**.

### Composite Key Matching (v1.1)

Match on **two columns** instead of just one. Set KEY Col 2 on both source and target to enable.

```
Single key:     KEY = normalize(StringID)
Composite key:  KEY = normalize(StringID) + "|||" + normalize(StrOrigin)
```

Example use case: When StringID alone has duplicates but StringID + StrOrigin is unique.

KEY Col 2 is optional per file. If not set, behaves as single-key mode. Use the [Clear] button to reset to single-key mode.

### Normalized Key Matching

Keys are normalized before comparison:

| Raw Cell Value | Normalized Key |
|----------------|----------------|
| `"  Hello World  "` | `hello world` |
| `"test_x000D_ value"` | `test value` |
| `"  CASE  insensitive  "` | `case insensitive` |
| `12345` (numeric) | `12345` |
| `""` or `None` | `""` (skipped) |

Normalization steps:
1. Convert to string
2. Strip leading/trailing whitespace
3. Remove `_x000D_` (Excel carriage return artifact)
4. Collapse multiple spaces to single space
5. Lowercase

**Values** are cleaned (strip + remove `_x000D_`) but **NOT lowercased** — original casing preserved.

### First-Wins Dedup

If multiple source rows have the same normalized key, the first one wins. Duplicate count is logged as a warning.

### Save Modes

| Mode | Behavior |
|------|----------|
| **Save as _lookup copy** (default) | `filename.xlsx` → `filename_lookup.xlsx` — original untouched |
| **Overwrite original** | Writes directly into the target file |

### Settings Persistence

`multi_lookup_settings.json` saved next to the script. Remembers:
- All source/target file paths
- Sheet + column selections per file (including KEY Col 2)
- Save mode

Files that no longer exist are silently skipped on reload. Switching between files preserves all config — no data loss.

### Error Handling

| Situation | Behavior |
|-----------|----------|
| openpyxl not installed | Warning at startup, TRANSFER button disabled |
| File locked by Excel | `PermissionError` → log "close file in Excel first", skip file |
| Empty source dictionary | Abort with error |
| 0 matches in target | Warning "check KEY columns" |
| Unconfigured files | Error dialog listing which files need config |

---

## GUI Layout

```
┌─ MultiLookup v1.1 ──────────────────────────────────────────────────────────────┐
│  Excel-to-Excel lookup transfer with normalized key matching                     │
│                                                                                  │
│  ┌─ Left Pane (60%) ─────────────────────────┬─ Right Pane (40%) ──────────────┐ │
│  │                                           │                                 │ │
│  │ ┌─ SOURCE Files (lookup dictionary) ────┐ │ ┌─ Log ───────────────────────┐ │ │
│  │ │ [Add Files...] [Remove] [Clear All]   │ │ │ ═══════════════════════════ │ │ │
│  │ │ ┌────────────────────────────────────┐│ │ │  MULTILOOKUP TRANSFER v1.1  │ │ │
│  │ │ │ data_ENG.xlsx [Sheet1]             ││ │ │ ═══════════════════════════ │ │ │
│  │ │ │ data_FRE.xlsx [Sheet1]             ││ │ │ BUILDING SOURCE DICTIONARY  │ │ │
│  │ │ │ corrections.xlsx [Batch2]          ││ │ │   Reading: data_ENG.xlsx    │ │ │
│  │ │ └────────────────────────────────────┘│ │ │     4200 rows, 4180 keys   │ │ │
│  │ │ Sheet [____] KEY Col [____] VAL [____]│ │ │   Dictionary: 12,450 keys  │ │ │
│  │ │              KEY Col 2 [____] [Clear] │ │ │ TRANSFERRING TO TARGETS...  │ │ │
│  │ └──────────────────────────────────────┘ │ │   3,891/4,200 rows matched  │ │ │
│  │                                           │ │   Saved: data_KOR_lookup    │ │ │
│  │ ┌─ TARGET Files (write into) ───────────┐ │ │                             │ │ │
│  │ │ [Add Files...] [Remove] [Clear All]   │ │ │                             │ │ │
│  │ │ ┌────────────────────────────────────┐│ │ │                             │ │ │
│  │ │ │ languagedata_KOR.xlsx [Main]       ││ │ │                             │ │ │
│  │ │ └────────────────────────────────────┘│ │ │                             │ │ │
│  │ │ Sheet [____] KEY Col [____] WRT [____]│ │ │                             │ │ │
│  │ │              KEY Col 2 [____] [Clear] │ │ │                             │ │ │
│  │ │ Save Mode: [Save as _lookup copy ▼]   │ │ │                             │ │ │
│  │ └──────────────────────────────────────┘ │ │                             │ │ │
│  │                                           │ │ [Clear Log]                 │ │ │
│  │      [===== TRANSFER =====]               │ └─────────────────────────────┘ │ │
│  └───────────────────────────────────────────┴─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
multi_lookup.py (single file)
├── normalize_key()             # Key normalization for matching
├── clean_value()               # Value cleaning (no lowercase)
├── _make_composite_key()       # Single or composite key from row
├── read_sheets()               # openpyxl introspection
├── read_headers()              # Row 1 header reading
├── build_source_dict()         # All sources → one {key: value} dict
├── transfer_to_targets()       # Row-by-row lookup + write
├── FileEntry                   # Per-file config (incl. col1b for KEY Col 2)
├── MultiLookupApp              # tkinter GUI
│   ├── _build_ui()                # PanedWindow: left controls, right log
│   ├── _build_file_section()      # Reused for SOURCE and TARGET
│   ├── _save_current_config()     # Save combobox state before file switch
│   ├── _on_listbox_select()       # Config panel sync (with persistence fix)
│   ├── _on_sheet_select()         # Header reload + targeted listbox update
│   ├── _on_col_select()           # KEY, VALUE/WRITE, and KEY Col 2
│   ├── _run_transfer()            # Validation + execute
│   └── _persist_settings()        # JSON save/restore (incl. col1b)
└── main()
```

---

## Changelog

### v1.1 (2026-03-11)

**Layout:**
- PanedWindow horizontal split — controls left (60%), log right (40%)
- Window: `850x780` → `1100x750`
- Listbox height: 4 → 10 rows, fill=both/expand=True for resizable sections

**Selection Persistence Fix:**
- `_save_current_config()` — saves combobox state back to FileEntry before switching files
- `_ignore_events` flag prevents event cascading during programmatic `.set()` calls
- `_current_src_idx` / `_current_tgt_idx` tracking for save-before-switch
- `_on_sheet_select()` — targeted single-item listbox update instead of full rebuild

**Composite Keys:**
- Optional KEY Col 2 combobox with [Clear] button per file section
- `FileEntry.col1b` / `col1b_idx` slots for second key column
- `_make_composite_key()` — builds `normalize(col1) + "|||" + normalize(col2)`
- Works in both `build_source_dict()` and `transfer_to_targets()`
- Backward compatible — missing col1b defaults to single-key mode
- Persisted in settings JSON

### v1.0 (2026-03-11)

Initial release.

---

## Use Cases

### 1. Batch Translation Transfer

Source: 5 Excel files from different translators, each with `StringID` + `Correction` columns.
Target: Master languagedata Excel. Match on `StringID`, write into `Correction` column.

### 2. Terminology Replacement

Source: Glossary Excel with `OldTerm` + `NewTerm`.
Target: Translation files. Match on old term column, overwrite with new term.

### 3. Cross-Language Sync

Source: English master with `StringID` + `ENG`.
Target: Korean working file. Match on `StringID`, write ENG text into a reference column.

### 4. Composite Key Transfer

Source: Corrections Excel with `StringID` + `StrOrigin` + `Correction`.
Target: Master file. Set KEY Col 2 to `StrOrigin` on both sides — matches only when both StringID AND StrOrigin match. Prevents wrong-row transfers when StringID has duplicates.

### 5. Data Migration

Source: Old system export.
Target: New system import template. Map by shared ID column.

---

## Future Roadmap

### v1.2 — Multi-Value Write

Write multiple columns at once instead of just one.

```
Source: StringID → Correction + Status + Comment
Target: StringID → (write all 3 columns)
```

**GUI:** VALUE/WRITE becomes a multi-select list. Transfer writes each matched column.

### v1.3 — Preview Mode

Before writing, show a preview table of what would change:

```
┌────────────┬──────────────┬──────────────┐
│ Key        │ Current      │ New Value    │
├────────────┼──────────────┼──────────────┤
│ item_001   │ (empty)      │ Sword        │
│ item_002   │ Old Shield   │ Shield       │  ← overwrite
│ item_003   │ Potion       │ Potion       │  ← same (skip?)
└────────────┴──────────────┴──────────────┘
```

Options: skip-if-same, skip-if-not-empty, overwrite-all.

### v1.4 — Conditional Transfer

Add filter rules: only transfer if a condition column matches.

```
Transfer Correction ONLY IF Status == "APPROVED"
```

### v1.5 — Report Output

Generate a transfer report Excel alongside the output:
- Matched rows (with before/after values)
- Unmatched source keys (orphans)
- Unmatched target keys (gaps)
- Duplicate key warnings with row numbers

---

## Grafting Into Larger Projects

MultiLookup is designed as a standalone QSS, but its architecture is graft-ready.

### Option A: Mega QSS Tab

The QSS roadmap (see `QSS.md`) plans a **Mega QSS** — all QSS tools combined into one tabbed window. MultiLookup slots in as a new tab. The `MultiLookupApp` class becomes a tab builder (receives parent `ttk.Frame` instead of creating `tk.Tk`). The log panel becomes shared.

### Option B: QuickTranslate Helper Tab

QuickTranslate already has Excel reading/writing infrastructure. MultiLookup could become a Helper Functions sub-tab, reusing QT's threaded worker and shared settings.

### Option C: Stay Standalone

Not everything needs to be integrated. MultiLookup is useful to people who don't use QuickTranslate — QA engineers, project managers, anyone working with Excel data. A standalone `.exe` via PyInstaller (< 30 MB) is easy to distribute.

**Recommended path:** Stay standalone for now. Graft into Mega QSS when that project starts.

---

## Technical Notes

| Detail | Value |
|--------|-------|
| **Python** | 3.8+ |
| **GUI** | tkinter + ttk (PanedWindow layout) |
| **Excel library** | openpyxl (read AND write — must modify existing files) |
| **Why not xlsxwriter?** | xlsxwriter can only create new files, can't open/modify existing ones |
| **Source read mode** | `data_only=True` — reads cached formula results, not formulas |
| **Target read mode** | Normal (not read_only) — must write back |
| **Threading** | None (QSS convention: synchronous with `update_idletasks()`) |
| **Settings** | `multi_lookup_settings.json` next to script, auto-saved after each transfer |
| **PyInstaller** | Compatible (`sys.frozen` check for `SCRIPT_DIR`) |

---

## Comparison with XLSTransfer

MultiLookup was inspired by XLSTransfer but addresses its limitations:

| | XLSTransfer | MultiLookup |
|---|---|---|
| **Files** | 1 source, 1 target | N sources, N targets |
| **Sheet selection** | Hardcoded or manual | Auto-detected, combobox |
| **Column selection** | Letter-based (A, B, C) | Header-based (clickable) |
| **Key matching** | `clean_text()` (strip `_x000D_`) | Full normalization (strip, collapse, lowercase) |
| **Composite keys** | No | Yes (KEY Col 2) |
| **Duplicate handling** | Undefined | First-wins with warning |
| **Save mode** | Overwrite only | Copy (default) or overwrite |
| **Settings** | None | Persistent JSON |
| **GUI** | Minimal | Full config per file |
| **Layout** | Vertical stack | PanedWindow (controls + log side by side) |

XLSTransfer remains a sacred script (never modified). MultiLookup is its spiritual successor for Excel-only workflows.

---

*Document updated: 2026-03-11 — MultiLookup v1.1*
