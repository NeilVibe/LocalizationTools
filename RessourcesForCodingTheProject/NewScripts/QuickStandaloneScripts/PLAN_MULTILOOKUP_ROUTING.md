# Plan: MultiLookup v1.2 — Source-to-Target Routing (PRXR Reviewed)

## Summary

Each target WRITE column picks WHICH source file to pull values from. Sources build individual named dicts. Routing uses stable `source_key = "path|sheet"` (not positional index).

---

## 1. Data Model

### WriteMapping (NEW class)

```python
class WriteMapping:
    __slots__ = ("col_name", "col_idx", "source_key")
    def __init__(self):
        self.col_name: str = ""     # "2: ENG_Text" (display string)
        self.col_idx: int = -1      # 2 (0-based column index)
        self.source_key: str = "ALL"  # "ALL" or "C:/path/to/file.xlsx|Sheet1"
```

**`source_key`:**
- `"ALL"` = use merged dict (all sources combined, first-wins — backward compat default)
- `"C:/path/to/file.xlsx|Sheet1"` = use per-source dict from that specific file+sheet

**Why path|sheet, not positional index:**
- Survives source add/remove/reorder without corruption
- Survives settings persistence across sessions (files skipped on load don't shift indices)
- Human-readable in settings JSON

### FileEntry changes

```python
class FileEntry:
    __slots__ = ("path", "sheets", "headers", "sheet", "col1", "col2",
                 "col1_idx", "col2_idx", "col1b", "col1b_idx",
                 "write_mappings")

    def __init__(self, path: str):
        # ... existing fields ...
        self.write_mappings: list = []  # List[WriteMapping], TARGET only

    @property
    def source_key(self) -> str:
        """Stable identity for this source entry: 'path|sheet'"""
        return f"{self.path}|{self.sheet}"

    @property
    def display(self) -> str:
        name = Path(self.path).name
        if self.sheet:
            return f"{name} [{self.sheet}]"
        return name
```

**Asymmetry (explicit contract):**
- Source entries: use `col2`/`col2_idx` for VALUE column. `write_mappings` empty.
- Target entries: use `write_mappings` for WRITE columns. `col2`/`col2_idx` unused (-1).

---

## 2. Core Logic

### `build_source_dicts()` — replaces `build_source_dict()`

```python
def build_source_dicts(
    entries: List[dict],
    log_fn=None,
) -> Tuple[Dict[str, Dict[str, str]], int]:
    """Build per-source lookup dicts keyed by source_key.

    Returns:
        (source_dicts: {source_key: {norm_key: clean_value}}, total_duplicates)
    """
```

- Each source entry produces one dict keyed by `entry["source_key"]`
- Composite keys (`key2_idx`) respected per source entry (same as v1.1)
- Dedup is per-source (first-wins within each file)
- NO merged dict built here — built lazily only if needed

### `_build_merged_dict()` — helper

```python
def _build_merged_dict(source_dicts: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Merge all per-source dicts into one. First-wins dedup across sources."""
    merged = {}
    for d in source_dicts.values():
        for k, v in d.items():
            if k not in merged:
                merged[k] = v
    return merged
```

Only called if any write mapping uses `source_key == "ALL"`.

### `transfer_to_targets()` — signature change

```python
def transfer_to_targets(
    source_dicts: Dict[str, Dict[str, str]],
    merged_dict: Optional[Dict[str, str]],  # None if not needed
    target_entries: List[dict],
    save_mode: str,
    log_fn=None,
) -> Tuple[int, int, int]:
```

Each target entry dict contains:
```python
{
    "path": str, "sheet": str,
    "key_col_idx": int, "key_col2_idx": int,
    "write_mappings": [
        {"col_idx": 2, "source_key": "ALL"},
        {"col_idx": 3, "source_key": "C:/data/ENG.xlsx|Sheet1"},
    ]
}
```

**Per-row logic:**
```python
for row in target_rows:
    nk = composite_key(row)
    for mapping in write_mappings:
        if mapping["source_key"] == "ALL":
            lookup = merged_dict
        else:
            lookup = source_dicts.get(mapping["source_key"])
            if lookup is None:
                # Source no longer exists — skip with warning (once)
                continue
        if nk in lookup:
            write_cell(row, mapping["col_idx"], lookup[nk])
```

**Per-mapping stats:**
```
Processing: master.xlsx [ENG tab]
  Col C (ENG_Text) <- ENG.xlsx [Sheet1]: 3,891/4,200 matched
  Col D (FRE_Text) <- FRE.xlsx [Sheet1]: 3,750/4,200 matched
```

---

## 3. GUI Layout

### Window: `1400x850`, PanedWindow `75/25` split

```
┌─ MultiLookup v1.2 ────────────────────────────────────────────────────────────────────────┐
│  Excel-to-Excel lookup transfer with source-to-target routing                              │
│                                                                                            │
│  ┌─ Left Pane (75%) ────────────────────────────────────────┬─ Log (25%) ────────────────┐ │
│  │                                                          │                            │ │
│  │ ┌─ SOURCE Files (lookup dictionary) ───────────────────┐ │ ┌─ Log ──────────────────┐ │ │
│  │ │ [Add Files...] [Remove] [Clear All]  3 files, 3 conf │ │ │ ══════════════════════ │ │ │
│  │ │ ┌──────────────────────────────────────────────────┐  │ │ │ MULTILOOKUP v1.2      │ │ │
│  │ │ │ [1] ENG.xlsx [Sheet1]                            │  │ │ │ ══════════════════════ │ │ │
│  │ │ │ [2] FRE.xlsx [Sheet1]                            │  │ │ │ Building dicts...     │ │ │
│  │ │ │ [3] KOR.xlsx [Sheet1]                            │  │ │ │   [1] 4200 rows       │ │ │
│  │ │ └──────────────────────────────────────────────────┘  │ │ │   [2] 4100 rows       │ │ │
│  │ │ Sheet [____]  KEY Col [____]  KEY Col 2 [____] [Clr]  │ │ │ Transferring...       │ │ │
│  │ │               VALUE Col [____]                         │ │ │   Col C <- [1]: 3891  │ │ │
│  │ └───────────────────────────────────────────────────────┘ │ │   Col D <- [2]: 3750  │ │ │
│  │                                                          │ │                        │ │ │
│  │ ┌─ TARGET Files (write into) ──────────────────────────┐ │ │                        │ │ │
│  │ │ [Add Files...] [Remove] [Clear All]  1 file, 1 conf  │ │ │                        │ │ │
│  │ │ ┌──────────────────────────────────────────────────┐  │ │ │                        │ │ │
│  │ │ │ master.xlsx [Main]                               │  │ │ │                        │ │ │
│  │ │ └──────────────────────────────────────────────────┘  │ │ │                        │ │ │
│  │ │ Sheet [____]  KEY Col [____]  KEY Col 2 [____] [Clr]  │ │ │                        │ │ │
│  │ │                                                        │ │ │                        │ │ │
│  │ │ Write Mappings:                                        │ │ │                        │ │ │
│  │ │ ┌─ # ─┬─ Write Into Column ─────┬─ From Source ─────┐ │ │ │                        │ │ │
│  │ │ │  1  │ [C: ENG_Text       ▼]   │ [1] ENG.xlsx  [X] │ │ │ │                        │ │ │
│  │ │ │  2  │ [D: FRE_Text       ▼]   │ [2] FRE.xlsx  [X] │ │ │ │                        │ │ │
│  │ │ │  3  │ [E: KOR_Text       ▼]   │ [3] KOR.xlsx  [X] │ │ │ │                        │ │ │
│  │ │ └─────┴─────────────────────────┴────────────────────┘ │ │ │ [Clear Log]           │ │ │
│  │ │ [+ Add Write Column]                                   │ │ └────────────────────────┘ │ │
│  │ │ Save Mode: [Save as _lookup copy ▼]                    │ │                            │ │
│  │ └────────────────────────────────────────────────────────┘ │                            │ │
│  │                                                          │                            │ │
│  │         [===== TRANSFER =====]                           │                            │ │
│  └──────────────────────────────────────────────────────────┴────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Source display: `[N]` prefix (not circled numbers)

Listbox: `[1] ENG.xlsx [Sheet1]`
Source selector dropdown values: `["ALL (merged)", "[1] ENG.xlsx [Sheet1]", "[2] FRE.xlsx [Sheet1]", ...]`

Numbers are display-only — routing uses `source_key` (path|sheet), not the number.

### Split `_build_file_section` → `_build_source_section` + `_build_target_section`

Shared helper `_build_file_list_and_keys(parent, title, is_source)` for:
- Button row (Add/Remove/Clear + status label)
- Listbox (height=8, fill=both, expand=True)
- Sheet + KEY + KEY Col 2 comboboxes

Then:
- `_build_source_section`: calls helper + adds VALUE Column combobox
- `_build_target_section`: calls helper + adds write mappings area + save mode

### Write Mapping Rows (dynamic)

Each mapping row is a `ttk.Frame` containing:
- Label `#N`
- Write-column combobox (readonly, width=25, populated from target headers)
- Source-selector combobox (readonly, width=30, populated from source list)
- `[X]` button to remove THIS specific row

Widget references stored directly on `WriteMapping` as transient attrs (not persisted, not in `__slots__`):
```python
# Set at GUI build time, never serialized:
mapping._col_widget = col_cb
mapping._src_widget = src_cb
mapping._frame = row_frame
```

Wait — `__slots__` prevents arbitrary attrs. Instead, store widget references in a parallel dict:
```python
self._mapping_widgets: Dict[int, Tuple[ttk.Frame, ttk.Combobox, ttk.Combobox]] = {}
# key = id(mapping), value = (frame, col_cb, src_cb)
```

### Source Selector Rebuild

`_rebuild_source_selectors()` — called when source list changes (add/remove/clear/sheet change):
1. Build values list: `["ALL (merged)"] + [f"[{i+1}] {e.display}" for i, e in enumerate(source_entries)]`
2. Build key map: `{display_string: source_key}` for resolving selection to source_key
3. For each target entry's write mappings, update source-selector combobox values
4. Preserve current selection if still valid; clear if source was removed

---

## 4. Persistence

### Target entry serialization:
```json
{
    "path": "C:/data/master.xlsx",
    "sheet": "Main",
    "col1": "0: StringID",
    "col1b": "",
    "write_mappings": [
        {"col_name": "2: ENG_Text", "source_key": "C:/data/ENG.xlsx|Sheet1"},
        {"col_name": "3: FRE_Text", "source_key": "C:/data/FRE.xlsx|Sheet1"}
    ]
}
```

### Source entry serialization (unchanged from v1.1):
```json
{
    "path": "C:/data/ENG.xlsx",
    "sheet": "Sheet1",
    "col1": "0: StringID",
    "col2": "1: Str",
    "col1b": ""
}
```

### Backward compat migration (in `_load_persisted_settings`):

```python
# For target entries:
if "write_mappings" in item:
    # v1.2+ format — load directly
    for wm_data in item["write_mappings"]:
        wm = WriteMapping()
        wm.col_name = wm_data.get("col_name", "")
        wm.source_key = wm_data.get("source_key", "ALL")
        if wm.col_name and wm.col_name in col_display:
            wm.col_idx = int(wm.col_name.split(":")[0])
            entry.write_mappings.append(wm)
elif "col2" in item and item["col2"]:
    # v1.1 format — migrate col2 → single WriteMapping with source_key="ALL"
    col2 = item["col2"]
    if col2 in col_display:
        wm = WriteMapping()
        wm.col_name = col2
        wm.col_idx = int(col2.split(":")[0])
        wm.source_key = "ALL"
        entry.write_mappings.append(wm)
```

### Stale source_key at load time:

If a write mapping references `source_key="C:/old/file.xlsx|Sheet1"` but that source no longer exists:
- Keep the mapping (source might be re-added later)
- At transfer time, skip with warning: "Source not found: file.xlsx [Sheet1]"

---

## 5. Event Handling

### `_save_current_config(is_source)`

**Source:** Same as v1.1 (save sheet, col1, col2, col1b from comboboxes).

**Target:** Save sheet, col1, col1b from comboboxes. Then iterate write mapping widgets:
```python
for mapping in entry.write_mappings:
    frame, col_cb, src_cb = self._mapping_widgets[id(mapping)]
    col_val = col_cb.get()
    if col_val:
        mapping.col_name = col_val
        mapping.col_idx = int(col_val.split(":")[0])
    src_val = src_cb.get()
    mapping.source_key = self._source_display_to_key.get(src_val, "ALL")
```

### `_on_listbox_select(is_source)`

**Source:** Same as v1.1 + update `[N]` prefix numbering.

**Target:** Save previous target's config → load new target's config. For write mappings:
1. Destroy all existing mapping row widgets
2. Clear `self._mapping_widgets`
3. For each mapping in `entry.write_mappings`:
   - Create row frame + comboboxes
   - Set values from mapping.col_name + mapping.source_key
   - Store in `self._mapping_widgets`
4. Wrap all `.set()` calls with `_ignore_events = True/False`

### `_on_sheet_select(is_source)` for target

When target sheet changes:
- Clear `entry.write_mappings` (headers changed → old column indices invalid)
- Destroy all mapping row widgets
- Clear `self._mapping_widgets`
- Targeted listbox single-item update (same as v1.1)

### Source list changes → `_rebuild_source_selectors()`

Called from: `_add_files(True)`, `_remove_selected(True)`, `_clear_files(True)`, `_on_sheet_select(True)`

For each target entry's write mappings:
- Update source combobox values list
- If current source_key still resolves to a source in the new list, preserve selection
- If source_key no longer resolves, set combobox to "ALL (merged)" and update mapping.source_key

---

## 6. Validation (`_run_transfer`)

### Source validation (unchanged):
- At least 1 source entry
- All sources have col1_idx >= 0 AND col2_idx >= 0

### Target validation (NEW):
- At least 1 target entry
- All targets have col1_idx >= 0
- All targets have len(write_mappings) >= 1
- All write mappings have col_idx >= 0
- All write mappings have source_key that resolves (source_key == "ALL" or source_key in source_dicts)
- WARNING (not error): duplicate col_idx across mappings in same target → log "Col X written by multiple mappings, last wins"

### `_update_status` for targets:
```python
configured = sum(1 for e in entries
    if e.col1_idx >= 0 and len(e.write_mappings) > 0
    and all(wm.col_idx >= 0 for wm in e.write_mappings))
```

---

## 7. Implementation Order

1. **WriteMapping class + FileEntry update** — data model
2. **`build_source_dicts()` + `_build_merged_dict()`** — core logic
3. **`transfer_to_targets()`** — new signature + per-mapping iteration
4. **Settings persistence** — serialize/deserialize write_mappings + backward compat migration
5. **GUI: Split builders** — `_build_source_section` + `_build_target_section` + shared helper
6. **GUI: Write mapping rows** — dynamic add/remove, [X] per row, source selector
7. **GUI: Source selector rebuild** — `_rebuild_source_selectors()` called on source changes
8. **GUI: Events** — `_save_current_config`, `_on_listbox_select`, `_on_sheet_select` for targets
9. **Validation update** — `_run_transfer` + `_update_status`
10. **Log output** — per-mapping stats
11. **Docs** — update MultiLookup.md

---

## 8. Review Findings Addressed

| Finding | Resolution |
|---------|------------|
| CRITICAL: source_idx positional instability | → `source_key = "path\|sheet"` stable identity |
| CRITICAL: empty write_mappings validation | → explicit validation in `_run_transfer` |
| CRITICAL: `__slots__` update | → `write_mappings` added to `__slots__` tuple |
| WARNING: source selector rebuild | → `_rebuild_source_selectors()` called on all source mutations |
| WARNING: `_save_current_config` redesign | → parallel `_mapping_widgets` dict, iterate on save |
| WARNING: `_on_sheet_select` clear mappings | → destroy widgets + clear list on target sheet change |
| WARNING: duplicate target columns | → warning in log, not error (last-wins documented) |
| WARNING: circled numbers cross-platform | → `[1]` `[2]` `[3]` plain text |
| WARNING: split builders | → `_build_source_section` + `_build_target_section` |
| WARNING: per-row remove | → `[X]` button per mapping row |
| WARNING: lazy merged dict | → only built if any mapping uses "ALL" |
| WARNING: composite keys per source | → each source uses its own key2_idx in per-source dict |

---

*Plan v2 — PRXR reviewed (5-agent) — 2026-03-11*
