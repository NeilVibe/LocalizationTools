# MultiLookup v1.0

**Excel-to-Excel lookup transfer with multi-file support and normalized key matching.**

Single-file QSS tool: `multi_lookup.py` (929 lines). No dependencies on LocaNext or other QSS tools.

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

## Features (v1.0)

### Multi-File Source & Target

Add 1+ Excel files on each side. All source files compile into ONE unified dictionary. All target files are written in a single pass.

### Per-File Configuration

Each file gets its own:
- **Sheet** selection (auto-detected on file add)
- **KEY column** (combobox populated from row 1 headers)
- **VALUE column** (source) or **WRITE column** (target)

Click a file in the listbox → config panel updates. Same file can be added twice for different sheets.

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
- Sheet + column selections per file
- Save mode

Files that no longer exist are silently skipped on reload.

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
┌─ MultiLookup v1.0 ──────────────────────────────────────────┐
│  Excel-to-Excel lookup transfer with normalized key matching │
│                                                              │
│  ┌─ SOURCE Files (lookup dictionary) ──────────────────────┐ │
│  │ [Add Files...] [Remove] [Clear All]     3 files, 3 conf │ │
│  │ ┌──────────────────────────────────────────────────────┐ │ │
│  │ │ data_ENG.xlsx [Sheet1]                               │ │ │
│  │ │ data_FRE.xlsx [Sheet1]                               │ │ │
│  │ │ corrections.xlsx [Batch2]                            │ │ │
│  │ └──────────────────────────────────────────────────────┘ │ │
│  │ Sheet: [Sheet1 ▼]  KEY: [0: StringID ▼]  VALUE: [2: Str]│ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ TARGET Files (write into) ─────────────────────────────┐ │
│  │ [Add Files...] [Remove] [Clear All]     1 file, 1 conf  │ │
│  │ ┌──────────────────────────────────────────────────────┐ │ │
│  │ │ languagedata_KOR.xlsx [Main]                         │ │ │
│  │ └──────────────────────────────────────────────────────┘ │ │
│  │ Sheet: [Main ▼]  KEY: [0: StringID ▼]  WRITE: [3: Corr] │ │
│  │ Save Mode: [Save as _lookup copy ▼]                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  [===== TRANSFER =====]  [Clear Log]                         │
│                                                              │
│  ┌─ Log ───────────────────────────────────────────────────┐ │
│  │ ════════════════════════════════════════════════════════ │ │
│  │   MULTILOOKUP TRANSFER v1.0                             │ │
│  │ ════════════════════════════════════════════════════════ │ │
│  │ BUILDING SOURCE DICTIONARY...                           │ │
│  │   Reading: data_ENG.xlsx [Sheet1]                       │ │
│  │     4200 rows scanned, 4180 keys added                  │ │
│  │   Dictionary: 12,450 unique keys                        │ │
│  │ TRANSFERRING TO TARGETS (Save as _lookup copy)...       │ │
│  │   Processing: languagedata_KOR.xlsx [Main]              │ │
│  │     3,891/4,200 rows matched                            │ │
│  │     Saved: languagedata_KOR_lookup.xlsx                 │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
multi_lookup.py (single file, ~930 lines)
├── normalize_key()          # Key normalization for matching
├── clean_value()            # Value cleaning (no lowercase)
├── read_sheets()            # openpyxl introspection
├── read_headers()           # Row 1 header reading
├── build_source_dict()      # All sources → one {key: value} dict
├── transfer_to_targets()    # Row-by-row lookup + write
├── FileEntry                # Per-file config data model
├── MultiLookupApp           # tkinter GUI
│   ├── _build_file_section()   # Reused for SOURCE and TARGET
│   ├── _on_listbox_select()    # Config panel sync
│   ├── _on_sheet_select()      # Header reload on sheet change
│   ├── _run_transfer()         # Validation + execute
│   └── _persist_settings()     # JSON save/restore
└── main()
```

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

### 4. Data Migration

Source: Old system export.
Target: New system import template. Map by shared ID column.

---

## Future Roadmap

### v1.1 — Multi-Column Key (Composite Key)

**The big evolution.** Instead of matching on a single column, match on 2+ columns concatenated.

```
Current (v1.0):  KEY = Column A
Future (v1.1):   KEY = Column A + Column B  (or A + B + C)

Example:
  Source: StringID + StrOrigin → Correction
  Target: StringID + StrOrigin → (write Correction here)

  Normalized key = normalize(A) + "║" + normalize(B)
```

**GUI change:** Replace single KEY combobox with a multi-select or "Add Key Column" button:

```
KEY Columns: [0: StringID ▼] [+]        ← click [+] to add more
             [1: StrOrigin ▼] [×]       ← click [×] to remove
```

**Code change:** Minimal — `normalize_key()` becomes `normalize_keys(values: list)` that joins with a separator. `FileEntry` stores `key_col_indices: List[int]` instead of single `col1_idx`. Everything else (dict lookup, dedup, transfer) works identically.

This is the killer feature that makes MultiLookup more powerful than any VLOOKUP — composite keys are painful in Excel but trivial here.

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

The QSS roadmap (see `QSS.md`) plans a **Mega QSS** — all QSS tools combined into one tabbed window. MultiLookup slots in as a new tab:

```
Mega QSS
├── [Diff]          ← XML Diff Extractor
├── [Long Strings]  ← Script Long String Extractor
├── [No-Voice]      ← Script No-Voice Extractor
├── [Blacklist]     ← BlacklistExtractor
├── [String Eraser] ← String Eraser XML
├── [File Eraser]   ← File Eraser By Name
└── [MultiLookup]   ← NEW — Excel-to-Excel transfer
```

**What changes:** The `MultiLookupApp` class becomes a tab builder (receives parent `ttk.Frame` instead of creating `tk.Tk`). The log panel becomes shared. Settings merge into `mega_qss_settings.json`.

**What stays:** All core logic (`normalize_key`, `build_source_dict`, `transfer_to_targets`) is pure functions with no GUI dependency — they graft as-is.

### Option B: QuickTranslate Helper Tab

QuickTranslate already has Excel reading/writing infrastructure. MultiLookup could become a Helper Functions sub-tab:

```
QuickTranslate
├── [Transfer]         ← Main XML transfer workflow
├── [Other Tools]      ← Pre-submission check, search, etc.
└── [Helper Functions]
    ├── Quick Actions
    ├── Substring Search
    └── MultiLookup    ← Excel-to-Excel (no XML)
```

**Advantages of QT integration:**
- Reuses QT's threaded worker (no GUI freeze on large files)
- Shared settings (source/target folder paths)
- Output feeds into QT's Transfer workflow (MultiLookup → produce Excel → QT transfers to XML)

**What changes:** Replace tkinter log with QT's `log_callback`. Replace synchronous loop with QT's thread pattern. Column config moves into QT's settings panel style.

### Option C: Stay Standalone

Not everything needs to be integrated. MultiLookup is useful to people who don't use QuickTranslate — QA engineers, project managers, anyone working with Excel data. A standalone `.exe` via PyInstaller (< 30 MB) is easy to distribute.

**Recommended path:** Stay standalone for now. Graft into Mega QSS when that project starts. Consider QT integration only if the Excel-to-Excel workflow becomes a frequent step in the translation pipeline.

---

## Technical Notes

| Detail | Value |
|--------|-------|
| **Python** | 3.8+ |
| **GUI** | tkinter + ttk |
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
| **Duplicate handling** | Undefined | First-wins with warning |
| **Save mode** | Overwrite only | Copy (default) or overwrite |
| **Settings** | None | Persistent JSON |
| **GUI** | Minimal | Full config per file |
| **Future: composite keys** | No | Planned (v1.1) |

XLSTransfer remains a sacred script (never modified). MultiLookup is its spiritual successor for Excel-only workflows.

---

*Document created: 2026-03-11 — MultiLookup v1.0*
