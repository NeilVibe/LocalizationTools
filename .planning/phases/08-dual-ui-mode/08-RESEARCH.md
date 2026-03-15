# Phase 08: Dual UI Mode - Research

**Researched:** 2026-03-15
**Domain:** Svelte 5 component architecture, column-config-driven rendering, file type detection
**Confidence:** HIGH

## Summary

Phase 08 adds automatic UI mode switching based on XML file type. When a user opens a file containing `<LocStr>` elements, they see Translator columns (Source, Target, Status, Match%, TM Source). When they open any other XML file, they see Game Dev columns (NodeName, Attributes, Values, Children count). A mode indicator badge in the editor header shows which mode is active.

The critical architectural constraint is that VirtualGrid.svelte (4048 lines) MUST NOT be duplicated. The existing `allColumns` object and `getVisibleColumns()` function already demonstrate the column-config pattern -- adding a second set of columns keyed by file type is a natural extension. The backend already stores `file_metadata` (including `element_tag`, `root_element`) per file via `extra_data` on LDMFile. File type detection can leverage the existing `iter_locstr_elements()` helper from Phase 07's XMLParsingEngine.

The main risk is state leakage between modes: if a user opens a Translator file, then switches to a Game Dev file, Svelte 5's proxy-based reactivity preserves stale `rows`, `searchTerm`, `editingRowId`, etc. The fix is either `{#key fileType}` for full remount or explicit state reset in the `$effect` that watches `fileId` changes (the latter is preferred since VirtualGrid already has this effect at line 2298).

**Primary recommendation:** Add `fileType` prop to VirtualGrid, use it in a `$derived` to select column configs, add mode badge to header, and reset all transient state in the existing fileId-change effect. Backend adds `file_type` field to file response schema and detects it during upload via LocStr element scan.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DUAL-01 | System detects file type (LocStr = Translator, other = Game Dev) and switches UI automatically | Backend: `iter_locstr_elements()` from XMLParsingEngine (Phase 07). Detect at upload time, store in `file_metadata.file_type`. Frontend: `fileType` prop on VirtualGrid drives column selection via `$derived`. |
| DUAL-02 | Translator mode shows translation-specific columns (Source, Target, Status, Match%, TM Source) | Extend existing `allColumns` in VirtualGrid with `translatorColumns` config. Source/Target already exist. Add Match% and TM Source as optional columns. |
| DUAL-03 | Game Dev mode shows XML-structure columns (NodeName, Attributes, Values, Children count) | New `gameDevColumns` config in VirtualGrid. Requires new row data shape from backend (`node_name`, `attributes`, `values`, `children_count`). New `parse_gamedev_file()` in xml_handler. |
| DUAL-04 | Mode indicator visible in editor header showing current file type | Add Carbon `Tag` component to `.grid-header .header-left` in VirtualGrid. Blue for Translator, teal for Game Dev. |
| DUAL-05 | Both modes share the same virtual grid infrastructure with different column configs | Single VirtualGrid with `$derived` activeColumns based on `fileType` prop. No component duplication. Cell rendering uses column key to select render logic. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | 5.x (Runes) | UI framework | Already in use, `$state`/`$derived`/`$effect` |
| Carbon Components Svelte | 0.x | UI components (Tag, icons) | Already in use for all UI elements |
| lxml | >=4.9.0 | XML parsing for file type detection | Already used by XMLParsingEngine (Phase 07) |
| FastAPI | 0.115.x | Backend API | Already in use |
| Pydantic | 2.x | Schema validation | Already in use for FileResponse/RowResponse |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| carbon-icons-svelte | 12.x | Mode indicator icons (Translate, DataStructured) | Mode badge in header |
| loguru | 0.7.x | Backend logging | All backend changes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `$derived` column switching | `{#key fileType}` full remount | Remount destroys scroll position, loses editing state. `$derived` is cheaper and preserves grid state where appropriate. |
| Storing file_type in DB | Detecting on every file open | DB storage is one-time cost at upload; re-detection on every open wastes CPU on large files. |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Changes

```
Backend (server/tools/ldm/):
  file_handlers/
    xml_handler.py           # MODIFY: add file_type to metadata, add parse_gamedev_nodes()
  services/
    xml_parsing.py           # EXISTING: iter_locstr_elements() already available
  schemas/
    file.py                  # MODIFY: add file_type field to FileResponse
    row.py                   # MODIFY: add optional Game Dev fields (or use extra_data)
  routes/
    files.py                 # MODIFY: include file_type in response
    rows.py                  # MODIFY: serve Game Dev row shape when file_type=gamedev

Frontend (locaNext/src/lib/):
  components/ldm/
    VirtualGrid.svelte       # MODIFY: column configs, mode badge, cell rendering
  stores/
    ldm.js                   # NO CHANGE needed (fileType comes as prop, not store)

Tests:
  tests/unit/ldm/
    test_filetype_detection.py   # NEW: file type detection tests
    test_gamedev_parsing.py      # NEW: Game Dev XML parsing tests
```

### Pattern 1: Column Config Selection via $derived

**What:** Use a `$derived` reactive declaration to select active columns based on file type.
**When to use:** Whenever the VirtualGrid needs to render different column layouts.
**Example:**
```svelte
// VirtualGrid.svelte -- additions to existing code
let { fileId = $bindable(null), fileName = "", fileType = "translator", ... } = $props();

const translatorColumns = {
  row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
  string_id: { key: "string_id", label: "StringID", width: 150, prefKey: "showStringId" },
  source: { key: "source", label: "Source (KR)", width: 350, always: true },
  target: { key: "target", label: "Target", width: 350, always: true },
  reference: { key: "reference", label: "Reference", width: 300, prefKey: "showReference" },
  tm_result: { key: "tm_result", label: "TM Match", width: 300, prefKey: "showTmResults" }
};

const gameDevColumns = {
  row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
  node_name: { key: "node_name", label: "Node", width: 200, always: true },
  attributes: { key: "attributes", label: "Attributes", width: 300, always: true },
  values: { key: "values", label: "Values", width: 300, always: true },
  children_count: { key: "children_count", label: "Children", width: 100, always: true }
};

// Replace existing allColumns with mode-aware selection
let allColumns = $derived(fileType === 'gamedev' ? gameDevColumns : translatorColumns);
```

### Pattern 2: File Type Detection at Upload Time

**What:** Detect file type during XML upload, store in file metadata.
**When to use:** When a new XML file is uploaded or re-uploaded.
**Example:**
```python
# xml_handler.py -- add to parse_xml_file()
from server.tools.ldm.services.xml_parsing import iter_locstr_elements

# After parsing root element:
loc_elements = list(iter_locstr_elements(root))
file_type = "translator" if loc_elements else "gamedev"

metadata = {
    "encoding": detected_encoding,
    "file_type": file_type,   # NEW
    # ... existing fields
}
```

### Pattern 3: Mode Badge in Header

**What:** Carbon Tag component showing current mode.
**When to use:** Always visible in the grid header when a file is open.
**Example:**
```svelte
<!-- In .grid-header .header-left, after row-count -->
<Tag type={fileType === 'gamedev' ? 'teal' : 'blue'} size="sm">
  {fileType === 'gamedev' ? 'Game Dev' : 'Translator'}
</Tag>
```

### Pattern 4: Game Dev Row Data Shape

**What:** Backend parses non-LocStr XML into a flat row structure for the grid.
**When to use:** When file_type is "gamedev".
**Example:**
```python
def parse_gamedev_nodes(root, max_depth=3):
    """Parse XML nodes into flat rows for Game Dev grid display."""
    rows = []
    for i, elem in enumerate(root.iter()):
        if elem.tag is etree.Comment:
            continue
        rows.append({
            "row_num": i + 1,
            "string_id": None,
            "source": elem.tag,                    # node_name goes in source
            "target": _format_attributes(elem),    # attributes summary in target
            "status": "pending",
            "extra_data": {
                "node_name": elem.tag,
                "attributes": dict(elem.attrib),
                "values": (elem.text or "").strip(),
                "children_count": len(list(elem)),
                "depth": _get_depth(elem, root)
            }
        })
    return rows
```

### Anti-Patterns to Avoid
- **Separate Grid Components:** Do NOT create `TranslatorGrid.svelte` and `GameDevGrid.svelte`. VirtualGrid is 4048 lines -- duplicating ANY of it is unacceptable.
- **Storing fileType in Svelte store:** fileType should flow as a prop from GridPage to VirtualGrid, not as global state. Each open file has its own type.
- **Re-detecting file type on every open:** Detect once at upload, store in `extra_data.file_type`. The `get_file` response includes it.
- **Hardcoded column rendering in HTML:** Cell rendering should branch on `col.key`, not on file type. The column config drives what renders.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LocStr detection | Custom XML regex scanner | `iter_locstr_elements()` from XMLParsingEngine | Already handles all case variants (LocStr, locstr, LOCSTR, LOCStr, Locstr) |
| Mode indicator UI | Custom div with styling | Carbon `Tag` component | Consistent with design system, accessible, themed |
| Column visibility logic | New visibility system | Extend existing `getVisibleColumns()` | Already handles preferences, just needs mode awareness |
| File metadata storage | New DB column | `extra_data` JSON field on LDMFile | Already exists, already used for encoding/root_element/element_tag |

## Common Pitfalls

### Pitfall 1: State Leakage Between Modes
**What goes wrong:** User opens Translator file, edits row 5, switches to Game Dev file. Row 5 editing state, search term, selected row, etc. persist from Translator mode.
**Why it happens:** Svelte 5 proxy-based reactivity preserves component state across prop changes. VirtualGrid is not destroyed/recreated when `fileId` changes.
**How to avoid:** The existing `$effect` at line 2298 already resets `searchTerm` and re-loads rows when `fileId` changes. Extend this to also reset: `inlineEditingRowId`, `selectedRowId`, `hoveredRowId`, `tmResults`, `referenceData`, `semanticResults`, `activeFilter`.
**Warning signs:** Old column data appearing briefly, editing state from previous file carrying over, search results from wrong file.

### Pitfall 2: Cell Rendering Mismatch
**What goes wrong:** VirtualGrid's HTML template has hardcoded cell rendering for `source`, `target`, `string_id` -- Game Dev mode needs different rendering for `node_name`, `attributes`, `values`, `children_count`.
**Why it happens:** Current template at lines 2570-2700+ directly references `row.source`, `row.target` with specialized rendering (ColorText, inline editing, QA badges, TM badges).
**How to avoid:** For Game Dev mode, map Game Dev data into existing row fields (`source` = node_name, `target` = values/attributes summary) OR add conditional rendering blocks keyed on `fileType`. The former is simpler for v2.0.
**Warning signs:** Empty cells, undefined values, broken inline editing in Game Dev mode.

### Pitfall 3: Inline Editing in Game Dev Mode
**What goes wrong:** Game Dev mode rows should NOT be editable via inline editing (they're structural XML data, not translation text). But VirtualGrid has inline editing hardwired for the `target` column.
**Why it happens:** `startInlineEdit()` and the `ondblclick` handler don't know about file type.
**How to avoid:** Guard inline editing with `fileType !== 'gamedev'` check. Game Dev editing is deferred to v3.0 (GDEV-01/02/03).
**Warning signs:** User accidentally editing XML node names or attribute values.

### Pitfall 4: API Response Shape Mismatch
**What goes wrong:** Frontend expects `RowResponse` with `source`/`target` fields. Game Dev rows have fundamentally different data (node names, attributes).
**Why it happens:** The existing schema is Translator-centric.
**How to avoid:** Reuse `source`/`target` fields for Game Dev data (source=node_name display, target=primary value), store full Game Dev data in `extra_data`. Frontend reads from `extra_data` when in Game Dev mode for additional columns.
**Warning signs:** Missing columns, null values in required fields.

### Pitfall 5: getVisibleColumns Ignores File Type
**What goes wrong:** `getVisibleColumns()` currently only checks preferences (`showIndex`, `showStringId`, `showReference`). Without file type awareness, it returns Translator columns for Game Dev files.
**Why it happens:** The function was written before dual mode existed.
**How to avoid:** Pass `fileType` into `getVisibleColumns()` or make `allColumns` a `$derived` that changes based on `fileType`.
**Warning signs:** Game Dev files showing "Source (KR)" and "Target" headers.

## Code Examples

### Example 1: Extended FileResponse Schema
```python
# server/tools/ldm/schemas/file.py
class FileResponse(BaseModel):
    id: int
    project_id: Optional[int]
    folder_id: Optional[int]
    name: str
    original_filename: str
    format: str
    file_type: str = "translator"  # NEW: "translator" or "gamedev"
    row_count: int
    source_language: str
    target_language: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

### Example 2: File Type in Upload Response
```python
# In files.py upload_file route, after parsing:
file_type = "translator"  # default
if file_metadata and file_metadata.get("file_type"):
    file_type = file_metadata["file_type"]

return {
    # ... existing fields ...
    "file_type": file_type,
}
```

### Example 3: GridPage Passes fileType to VirtualGrid
```svelte
<!-- GridPage.svelte -->
<VirtualGrid
  bind:this={virtualGrid}
  bind:fileId={fileId}
  fileName={fileName}
  fileType={fileType}
  activeTMs={activeTMs}
  isLocalFile={isLocalFile}
  on:selectRow={handleRowSelect}
  ...
/>
```

### Example 4: State Reset on File Switch
```svelte
// VirtualGrid.svelte - extend existing $effect at line 2298
$effect(() => {
  if (fileId && fileId !== previousFileId) {
    previousFileId = fileId;

    // Reset ALL transient state
    searchTerm = "";
    inlineEditingRowId = null;
    selectedRowId = null;
    hoveredRowId = null;
    tmResults = new Map();
    referenceData = new Map();
    semanticResults = [];
    activeFilter = "all";
    tmAppliedRows = new Map();

    joinFile(fileId);
    if (cellUpdateUnsubscribe) cellUpdateUnsubscribe();
    cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);

    loadRows();
  }
});
```

### Example 5: Conditional Cell Rendering
```svelte
<!-- For Game Dev mode, disable inline editing -->
{#if fileType === 'gamedev'}
  <div class="cell target" style="flex: {100 - sourceWidthPercent} 1 0;">
    <span class="cell-content">{row.target || ""}</span>
  </div>
{:else}
  <!-- Existing Translator target cell with inline editing, QA flags, etc. -->
  <div class="cell target" ondblclick={() => !rowLock && startInlineEdit(row)} ...>
    ...
  </div>
{/if}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate grid per mode | Single grid with column configs | v2.0 Phase 08 | Eliminates 4000+ lines of duplication |
| File type detection on open | Detection at upload, stored in metadata | v2.0 Phase 08 | O(1) type lookup vs O(n) LocStr scan per open |
| Svelte 4 `$:` reactivity | Svelte 5 `$derived` for column selection | v1.0 baseline | Fine-grained reactivity, better performance |

## Open Questions

1. **Game Dev Row Data: Reuse `source`/`target` or Add New Fields?**
   - What we know: RowResponse has `source`, `target`, `string_id` fields. Game Dev needs `node_name`, `attributes`, `values`, `children_count`.
   - What's unclear: Whether to map Game Dev data into existing fields (simpler API, less work) or add new optional fields to RowResponse (cleaner semantics).
   - Recommendation: Reuse `source`/`target` for display, store full Game Dev data in `extra_data`. This avoids schema changes and works with existing pagination/search infrastructure. Phase 12 (Game Dev Merge) can revisit if needed.

2. **Search Behavior in Game Dev Mode**
   - What we know: Search currently searches `source` and `target` fields. In Game Dev mode, these map to node names and attribute summaries.
   - What's unclear: Whether users expect to search by attribute name, attribute value, node path, etc.
   - Recommendation: Keep search working on `source`/`target` mapping for now. This searches node names and values, which covers the basic use case. Defer advanced Game Dev search to v3.0.

3. **Game Dev Column Resizing**
   - What we know: VirtualGrid has complex resize logic with `sourceWidthPercent` and fixed-width columns.
   - What's unclear: Whether the same resize model works for 4 Game Dev columns vs 2-3 Translator columns.
   - Recommendation: Use same flex-grow pattern. `node_name` gets fixed width, `attributes` and `values` share remaining space, `children_count` gets fixed width. Mimics existing `string_id` (fixed) + `source`/`target` (flex) + `reference` (fixed) pattern.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` (root) |
| Quick run command | `pytest tests/unit/ldm/ -x -q --no-header` |
| Full suite command | `pytest tests/ -x --ignore=tests/archive --ignore=tests/api --ignore=tests/cdp --ignore=tests/e2e` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DUAL-01 | File type detection (LocStr = translator, other = gamedev) | unit | `pytest tests/unit/ldm/test_filetype_detection.py -x` | Wave 0 |
| DUAL-02 | Translator columns returned for translator files | unit | `pytest tests/unit/ldm/test_filetype_detection.py::test_translator_columns -x` | Wave 0 |
| DUAL-03 | Game Dev columns returned for non-LocStr files | unit | `pytest tests/unit/ldm/test_filetype_detection.py::test_gamedev_columns -x` | Wave 0 |
| DUAL-04 | Mode indicator in response matches file type | unit | `pytest tests/unit/ldm/test_filetype_detection.py::test_mode_indicator -x` | Wave 0 |
| DUAL-05 | Shared grid infrastructure (no separate grid) | manual-only | Visual verification: single VirtualGrid.svelte used | N/A |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/ldm/ -x -q --no-header`
- **Per wave merge:** `pytest tests/ -x --ignore=tests/archive --ignore=tests/api --ignore=tests/cdp --ignore=tests/e2e`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_filetype_detection.py` -- covers DUAL-01 through DUAL-04
- [ ] `tests/fixtures/xml/gamedev_sample.xml` -- non-LocStr XML fixture for Game Dev mode testing

## Sources

### Primary (HIGH confidence)
- Inspected: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 290-348 (allColumns, getVisibleColumns, column rendering)
- Inspected: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 2390-2400 (grid-header with fileName and row count)
- Inspected: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 2555-2700 (cell rendering per column)
- Inspected: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 2298-2316 (fileId change effect -- state reset point)
- Inspected: `locaNext/src/lib/components/pages/GridPage.svelte` (VirtualGrid wrapper, prop passing)
- Inspected: `server/tools/ldm/services/xml_parsing.py` (iter_locstr_elements, LOCSTR_TAGS, get_attr)
- Inspected: `server/tools/ldm/file_handlers/xml_handler.py` (parse_xml_file, metadata structure)
- Inspected: `server/tools/ldm/schemas/file.py` (FileResponse, PaginatedRows)
- Inspected: `server/tools/ldm/schemas/row.py` (RowResponse with source/target/extra_data)
- Inspected: `server/tools/ldm/routes/files.py` lines 155-370 (get_file, upload_file, file_metadata storage)

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` Pattern 3 (Column Config Objects for Dual UI)
- `.planning/research/SUMMARY.md` Phase 2 rationale and pitfalls

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and verified in codebase
- Architecture: HIGH - based on direct inspection of VirtualGrid column system, XMLParsingEngine, and route structure
- Pitfalls: HIGH - state leakage, cell rendering mismatch, and inline editing guard identified from actual code inspection

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- Svelte 5 and existing architecture won't change)
