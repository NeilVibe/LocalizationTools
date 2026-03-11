# MultiLookup v1.2

**Excel-to-Excel lookup transfer with source-to-target routing, normalized key matching, and composite keys.**

Single-file QSS tool: `multi_lookup.py`. No dependencies on LocaNext or other QSS tools.

---

## What It Does

Build **per-source lookup dictionaries** from SOURCE Excel files, then write matched values into TARGET Excel files — with **per-column control** over which source provides the value.

```
SOURCE files                         TARGET file
┌─────────────────────┐
│ [1] ENG.xlsx        │              ┌──────────────────────────────────────┐
│  KEY=A  VALUE=B     │──────────┐   │ master.xlsx [Main]                   │
├─────────────────────┤          │   │                                      │
│ [2] FRE.xlsx        │          ├──→│ KEY=A  Write Col C ← [1] ENG.xlsx   │
│  KEY=A  VALUE=B     │──────────┤   │         Write Col D ← [2] FRE.xlsx   │
├─────────────────────┤          │   │         Write Col E ← [3] KOR.xlsx   │
│ [3] KOR.xlsx        │          │   │                                      │
│  KEY=A  VALUE=B     │──────────┘   └──────────────────────────────────────┘
└─────────────────────┘
Each source → its own named dict
Each target column picks its source
```

Think of it as a **programmable VLOOKUP across multiple files** — with source routing, normalized key matching, and composite keys.

---

## How To Run

```bash
python multi_lookup.py
```

Dependencies: `pip install openpyxl`

Can be bundled with PyInstaller for standalone `.exe` distribution.

---

## Features

### Source-to-Target Routing (v1.2)

The killer feature. Each target WRITE column picks **which source** to pull values from:

| Target Column | Value From Source |
|---------------|-------------------|
| C: ENG_Text | [1] ENG.xlsx [Sheet1] |
| D: FRE_Text | [2] FRE.xlsx [Sheet1] |
| E: KOR_Text | [3] KOR.xlsx [Sheet1] |

Sources are numbered `[1]`, `[2]`, `[3]` in the listbox. Target write mappings reference them by name via a dropdown. The `"ALL (merged)"` option combines all sources into one dictionary (backward compatible with v1.1 behavior).

**Routing uses stable `path|sheet` identity** — not positional indices. Removing or reordering sources won't silently corrupt your mappings.

### Multi-File Source & Target

Add 1+ Excel files on each side. Each source builds its own lookup dictionary. Multiple write mappings per target file.

### Per-File Configuration

Each file gets:
- **Sheet** selection (auto-detected on file add)
- **KEY column** + optional **KEY Col 2** (composite key matching)
- Source: **VALUE column**
- Target: **N write mappings**, each with column + source selector

### Dynamic Write Mappings

Target files have a **Write Mappings** area with:
- `[+ Add Write Column]` to add a new mapping row
- `[X]` button per row to remove a specific mapping
- Each row: Write-column combobox + Source-selector combobox

### Composite Key Matching

Match on **two columns** instead of just one. Set KEY Col 2 on both source and target.

```
Single key:     KEY = normalize(StringID)
Composite key:  KEY = normalize(StringID) + "|||" + normalize(StrOrigin)
```

### Normalized Key Matching

Keys are normalized before comparison:

| Raw Cell Value | Normalized Key |
|----------------|----------------|
| `"  Hello World  "` | `hello world` |
| `"test_x000D_ value"` | `test value` |
| `"  CASE  insensitive  "` | `case insensitive` |
| `12345` (numeric) | `12345` |

**Values** are cleaned but **NOT lowercased** — original casing preserved.

### Save Modes

| Mode | Behavior |
|------|----------|
| **Save as _lookup copy** (default) | `filename.xlsx` → `filename_lookup.xlsx` |
| **Overwrite original** | Writes directly into the target file |

### Settings Persistence

`multi_lookup_settings.json` remembers everything:
- All source/target file paths and sheet/column selections
- Write mappings per target file (including source routing)
- Save mode

Backward compatible — v1.1 settings with `col2` auto-migrate to write mappings.

### Error Handling

| Situation | Behavior |
|-----------|----------|
| openpyxl not installed | Warning, TRANSFER disabled |
| File locked by Excel | Skip with error message |
| Empty source dictionary | Abort |
| 0 matches in target | Warning |
| Unconfigured files/mappings | Error dialog with details |
| Duplicate write columns | Warning in log (last mapping wins) |
| Source not found at transfer | Skip column with warning |

---

## GUI Layout

```
┌─ MultiLookup v1.2 ─────────────────────────────────────────────────────────────────┐
│  Excel-to-Excel lookup transfer with source-to-target routing                       │
│                                                                                     │
│  ┌─ Left Pane (75%) ──────────────────────────────────┬─ Log (25%) ───────────────┐ │
│  │                                                    │                           │ │
│  │ ┌─ SOURCE Files ────────────────────────────────┐  │ ┌─ Log ────────────────┐  │ │
│  │ │ [Add] [Remove] [Clear All]  3 files, 3 conf  │  │ │ ════════════════════ │  │ │
│  │ │ [1] ENG.xlsx [Sheet1]                         │  │ │ MULTILOOKUP v1.2    │  │ │
│  │ │ [2] FRE.xlsx [Sheet1]                         │  │ │ ════════════════════ │  │ │
│  │ │ [3] KOR.xlsx [Sheet1]                         │  │ │ Building dicts...   │  │ │
│  │ │ Sheet [__] KEY [__] KEY2 [__] [Clr]           │  │ │  [1] 4200 rows     │  │ │
│  │ │ VALUE Column [__________]                     │  │ │  [2] 4100 rows     │  │ │
│  │ └──────────────────────────────────────────────┘  │ │ Transferring...     │  │ │
│  │                                                    │ │  C <- ENG: 3891    │  │ │
│  │ ┌─ TARGET Files ───────────────────────────────┐  │ │  D <- FRE: 3750    │  │ │
│  │ │ [Add] [Remove] [Clear All]  1 file, 1 conf  │  │ │  E <- KOR: 3600    │  │ │
│  │ │ master.xlsx [Main]                           │  │ │                     │  │ │
│  │ │ Sheet [__] KEY [__] KEY2 [__] [Clr]          │  │ │                     │  │ │
│  │ │ Write Mappings:                              │  │ │                     │  │ │
│  │ │  # │ Write Into Column │ From Source         │  │ │                     │  │ │
│  │ │  1 │ [C: ENG_Text  ▼]  │ [1] ENG.xlsx  [X]  │  │ │                     │  │ │
│  │ │  2 │ [D: FRE_Text  ▼]  │ [2] FRE.xlsx  [X]  │  │ │                     │  │ │
│  │ │  3 │ [E: KOR_Text  ▼]  │ [3] KOR.xlsx  [X]  │  │ │                     │  │ │
│  │ │ [+ Add Write Column]                         │  │ │ [Clear Log]        │  │ │
│  │ │ Save Mode: [Save as _lookup copy ▼]          │  │ └─────────────────────┘  │ │
│  │ └──────────────────────────────────────────────┘  │                           │ │
│  │        [===== TRANSFER =====]                     │                           │ │
│  └────────────────────────────────────────────────────┴───────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
multi_lookup.py (single file, ~1560 lines)
├── normalize_key()               # Key normalization for matching
├── clean_value()                 # Value cleaning (no lowercase)
├── _make_composite_key()         # Single or composite key from row
├── read_sheets() / read_headers() # openpyxl introspection
├── build_source_dicts()          # Per-source dicts {source_key: {key: value}}
├── build_merged_dict()           # Lazy merge of all per-source dicts
├── transfer_to_targets()         # Per-row, per-mapping lookup + write
├── WriteMapping                  # Target write column + source routing
├── FileEntry                     # Per-file config (source: col2, target: write_mappings)
├── MultiLookupApp                # tkinter GUI
│   ├── _build_file_list_and_keys()  # Shared: buttons + listbox + key combos
│   ├── _build_source_section()      # Source-specific: VALUE column
│   ├── _build_target_section()      # Target-specific: write mappings area
│   ├── _rebuild_source_selectors()  # Update target dropdowns on source changes
│   ├── _add_write_mapping()         # Dynamic mapping row creation
│   ├── _remove_write_mapping()      # Per-row [X] removal
│   ├── _save_current_config()       # Persist combos + write mappings to entry
│   ├── _on_listbox_select()         # File switch with config persistence
│   ├── _run_transfer()              # Validation + execute
│   └── _persist_settings()          # JSON save/restore with backward compat
└── main()
```

---

## Changelog

### v1.2 (2026-03-11)

**Source-to-Target Routing:**
- Each source builds its own named dict keyed by `source_key = "path|sheet"` (stable identity)
- Target write mappings reference sources by key, not positional index
- "ALL (merged)" mode combines all sources (backward compat default)
- Merged dict built lazily — only if needed
- Per-mapping transfer stats in log output

**GUI:**
- Window: `1100x750` → `1400x850`
- PanedWindow split: 60/40 → 75/25 (log compressed right)
- Split builders: `_build_source_section` + `_build_target_section` + shared helper
- Source display: `[N]` prefix in listbox for reference
- Target: dynamic write mappings area with [+ Add] / [X] per-row buttons
- Source selector dropdown rebuilt on all source mutations

**Data Model:**
- `WriteMapping` class: `col_name`, `col_idx`, `source_key`
- `FileEntry.write_mappings` list for target entries
- `FileEntry.source_key` property for stable identity
- `to_source_dict()` / `to_target_dict()` replace `to_transfer_dict()`

**Validation:**
- Target: KEY + at least 1 write mapping with valid column
- Duplicate write-column warning (last mapping wins)
- Stale source_key at transfer time: skip column with warning

**Settings:**
- Write mappings persisted per target entry
- Backward compat: v1.1 `col2` auto-migrates to single WriteMapping with source_key="ALL"

### v1.1 (2026-03-11)

- PanedWindow horizontal split layout
- Selection persistence fix (save-before-switch, event guards)
- Composite keys (optional KEY Col 2)

### v1.0 (2026-03-11)

Initial release.

---

## Use Cases

### 1. Multi-Language Transfer (the v1.2 killer use case)

Source: 10 language Excel files (ENG.xlsx, FRE.xlsx, KOR.xlsx, ...), each with StringID + translation.
Target: Master file with 10 tabs or 10 columns. Each write mapping routes a specific language to its column.

### 2. Batch Translation Transfer

Source: 5 files from translators. Target: Master file. All sources use "ALL (merged)" mode.

### 3. Composite Key Transfer

Source: Corrections with StringID + StrOrigin + Correction.
Target: Master file. KEY Col 2 = StrOrigin — matches only when both columns match.

### 4. Cross-Language Sync

Source: English master. Target: Korean working file. Route ENG values to a reference column.

---

## Future Roadmap

### v1.3 — Multi-Value Write

Write multiple source columns at once per mapping (Correction + Status + Comment).

### v1.4 — Preview Mode

Show a preview table before writing. Options: skip-if-same, skip-if-not-empty, overwrite-all.

### v1.5 — Conditional Transfer

Transfer only if a condition column matches (e.g., `Status == "APPROVED"`).

---

## Technical Notes

| Detail | Value |
|--------|-------|
| **Python** | 3.8+ |
| **GUI** | tkinter + ttk (PanedWindow, dynamic widget creation) |
| **Excel library** | openpyxl (read AND write) |
| **Source read mode** | `data_only=True` — cached formula results |
| **Target read mode** | Normal (must write back) |
| **Routing identity** | `source_key = "path\|sheet"` — stable across add/remove |
| **Threading** | None (QSS convention: synchronous with `update_idletasks()`) |
| **Settings** | `multi_lookup_settings.json` — auto-saved after each transfer |
| **PyInstaller** | Compatible (`sys.frozen` check for `SCRIPT_DIR`) |

---

*Document updated: 2026-03-11 — MultiLookup v1.2*
