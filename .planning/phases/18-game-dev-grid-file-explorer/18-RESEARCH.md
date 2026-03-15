# Phase 18: Game Dev Grid + File Explorer - Research

**Researched:** 2026-03-15
**Domain:** File explorer tree, hierarchical XML grid, inline editing, virtual scrolling
**Confidence:** HIGH

## Summary

Phase 18 builds a VS Code-style file explorer for browsing gamedata folder structures and a hierarchical grid for viewing/editing XML entity attributes inline. The project already has extensive infrastructure to build on: VirtualGrid.svelte with variable-height virtual scrolling (tested with thousands of rows), TMExplorerTree.svelte with expand/collapse tree patterns, dual UI mode with `fileType === 'gamedev'` detection, and a `parse_gamedev_nodes()` backend function that converts XML into flat rows with depth/attribute metadata.

The core challenge is threefold: (1) creating a new backend endpoint to scan a folder on disk and return its tree structure, (2) extending the existing gamedev grid columns to support inline editing of Name/Desc/text attributes (currently blocked -- VirtualGrid explicitly skips inline edit for gamedev mode), and (3) ensuring edits persist back to the XML data model with proper br-tag encoding. The mock gamedata from Phase 15 provides 18 StaticInfo XML files across 6 entity types (352 entities) as the test dataset.

**Primary recommendation:** Build a new FileExplorerTree.svelte component (modeled on TMExplorerTree.svelte patterns) for the left panel, extend the existing VirtualGrid.svelte to enable inline editing for gamedev mode (rather than creating a separate GameDevGrid.svelte), and add a new backend service for folder scanning + XML attribute updates.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GDEV-01 | File explorer panel shows gamedata folder structure | New FileExplorerTree component + backend /api/ldm/gamedata/browse endpoint scanning disk folders |
| GDEV-02 | User clicks folder/file to load contents in grid | Navigation store integration -- clicking a file calls existing file upload/parse flow or new direct-parse endpoint |
| GDEV-03 | Grid displays XML entity hierarchy with parent-child nesting | parse_gamedev_nodes() already returns depth field; VirtualGrid needs indentation rendering per depth level |
| GDEV-04 | Inline editing of Name, Desc, text attributes | VirtualGrid currently blocks gamedev inline edit (line 2778); need to enable + extend RowUpdate schema for extra_data fields |
| GDEV-05 | Metadata columns appropriate to data type | gameDevColumns already defined (Node, Attributes, Values, Children); need dynamic columns based on XML file type (Key, StrKey, KnowledgeKey) |
| GDEV-06 | Changes saved with proper XML encoding (br-tag preservation) | lxml auto-escapes br-tags in attribute values; postprocess.py normalizes br variants; new save endpoint writes back to file |
| GDEV-07 | Virtual scroll for large files (1000+ entities) | VirtualGrid already implements variable-height virtual scrolling with row height cache, cumulative positions, and buffer rows |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | existing | Frontend components (Runes only) | Project standard |
| Carbon Components Svelte | existing | UI components (Tree, Tag, Button) | Project design system |
| carbon-icons-svelte | existing | File/folder icons | Consistent iconography |
| FastAPI | existing | Backend REST endpoints | Project standard |
| lxml | existing | XML parsing and writing | Already used by XMLParsingEngine |
| Pydantic | existing | Request/response schemas | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | existing | Logging (never print()) | All backend code |
| pathlib | stdlib | File system traversal | Folder scanning endpoint |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extend VirtualGrid for gamedev edit | New GameDevGrid.svelte | VirtualGrid already has 90% of what we need (virtual scroll, column system, dual mode detection). A new component would duplicate thousands of lines. Extend instead |
| Backend folder scan | Frontend filesystem API | Electron can access fs, but backend provides consistent API for both online/offline modes and keeps parsing logic server-side |
| Tree component from scratch | Carbon TreeView | Carbon TreeView exists but is Svelte 4 style and lacks the project's custom styling. TMExplorerTree patterns are better |

**Installation:**
No new dependencies required. All tools already in the project.

## Architecture Patterns

### Recommended Component Structure
```
locaNext/src/lib/components/
  ldm/
    FileExplorerTree.svelte      # NEW: Gamedata folder browser (left panel)
    VirtualGrid.svelte           # EXTEND: Enable inline edit for gamedev mode
  pages/
    GameDevPage.svelte           # NEW: Layout = FileExplorerTree + GridPage

server/tools/ldm/
  services/
    gamedata_browse_service.py   # NEW: Scan folders, return tree structure
    gamedata_edit_service.py     # NEW: Apply attribute edits to XML, save back
  routes/
    gamedata.py                  # NEW: /api/ldm/gamedata/browse, /api/ldm/gamedata/parse, /api/ldm/gamedata/save
  schemas/
    gamedata.py                  # NEW: FolderTreeResponse, GameDevRowUpdate, etc.
```

### Pattern 1: File Explorer Tree (Frontend)
**What:** Recursive tree component for folder/file browsing
**When to use:** Left panel of Game Dev mode
**Example (based on TMExplorerTree patterns):**
```svelte
<script>
  // Svelte 5 Runes
  let expandedNodes = $state(new Set());
  let selectedFile = $state(null);
  let treeData = $state({ folders: [] });

  function toggleNode(nodeId) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(nodeId)) newSet.delete(nodeId);
    else newSet.add(nodeId);
    expandedNodes = newSet;
  }
</script>

{#each treeData.folders as folder (folder.path)}
  <button class="tree-header" onclick={() => toggleNode(folder.path)}>
    {#if expandedNodes.has(folder.path)}
      <ChevronDown size={16} />
      <FolderOpen size={18} />
    {:else}
      <ChevronRight size={16} />
      <Folder size={18} />
    {/if}
    <span>{folder.name}</span>
    <span class="count">{folder.file_count}</span>
  </button>
  {#if expandedNodes.has(folder.path)}
    <div class="tree-children">
      {#each folder.files as file (file.path)}
        <button class="file-item" class:selected={selectedFile === file.path}
          onclick={() => selectFile(file)}>
          <Code size={16} />
          <span>{file.name}</span>
          <span class="entity-count">{file.entity_count}</span>
        </button>
      {/each}
    </div>
  {/if}
{/each}
```

### Pattern 2: Backend Folder Scanning
**What:** Service that scans a directory and returns tree structure with XML file metadata
**When to use:** /api/ldm/gamedata/browse endpoint
**Example:**
```python
from pathlib import Path
from lxml import etree

class GameDataBrowseService:
    def scan_folder(self, root_path: Path, max_depth: int = 4) -> dict:
        """Scan gamedata folder tree, returning structure with XML metadata."""
        result = {"name": root_path.name, "path": str(root_path), "folders": [], "files": []}
        for child in sorted(root_path.iterdir()):
            if child.is_dir():
                result["folders"].append(self.scan_folder(child, max_depth - 1))
            elif child.suffix.lower() == ".xml":
                result["files"].append({
                    "name": child.name,
                    "path": str(child),
                    "size": child.stat().st_size,
                    "entity_count": self._count_entities(child),
                })
        return result

    def _count_entities(self, xml_path: Path) -> int:
        """Quick count of child elements under root (no full parse)."""
        try:
            tree = etree.parse(str(xml_path))
            return len(list(tree.getroot()))
        except Exception:
            return 0
```

### Pattern 3: Inline Editing for Gamedev Mode
**What:** Extend VirtualGrid to allow editing specific attributes in gamedev mode
**When to use:** When user double-clicks a Name/Desc cell in the grid
**Key changes to VirtualGrid.svelte:**
```javascript
// Currently at line 2778:
// ondblclick={() => fileType !== 'gamedev' && !rowLock && startInlineEdit(row)}
// Change to:
// ondblclick={() => !rowLock && startInlineEdit(row)}

// For gamedev mode, editing needs to update specific attributes in extra_data
// rather than the "target" column. The save endpoint updates the XML attribute directly.
```

### Pattern 4: XML Attribute Save-Back
**What:** Service that modifies specific attributes in an XML file and saves
**When to use:** When user edits a Name/Desc value and confirms
**Critical:** Must preserve br-tags correctly
```python
def update_entity_attribute(self, xml_path: Path, entity_index: int,
                            attr_name: str, new_value: str) -> bool:
    """Update a specific attribute on an XML entity and save the file.

    br-tag handling:
    - User edits contain <br/> for newlines
    - lxml auto-escapes to &lt;br/&gt; in attribute values (correct on disk)
    - On re-parse, &lt;br/&gt; is read back as <br/> in attribute string
    """
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    elements = list(root)
    if 0 <= entity_index < len(elements):
        elements[entity_index].set(attr_name, new_value)
        tree.write(str(xml_path), encoding="UTF-8", xml_declaration=True)
        return True
    return False
```

### Pattern 5: Dynamic Column Configuration
**What:** Different metadata columns shown based on the entity type in the XML file
**When to use:** After loading an XML file, detect what attributes exist and configure columns
```javascript
// Detect columns from first entity's attributes
const entityAttrs = rows[0]?.extra_data?.attributes || {};
const dynamicColumns = [];
if ('Key' in entityAttrs) dynamicColumns.push({ key: 'key', label: 'Key', width: 100 });
if ('StrKey' in entityAttrs) dynamicColumns.push({ key: 'strkey', label: 'StrKey', width: 150 });
if ('KnowledgeKey' in entityAttrs) dynamicColumns.push({ key: 'knowledgekey', label: 'KnowledgeKey', width: 150 });
// ... entity-type-specific columns
```

### Anti-Patterns to Avoid
- **Creating a separate GameDevGrid.svelte from scratch:** VirtualGrid already has virtual scrolling, column system, search, filters. Duplicating all of that wastes code. Extend VirtualGrid instead.
- **Loading entire folder tree eagerly:** Large gamedata folders can have thousands of files. Lazy-load subfolder contents on expand, not all at once.
- **Saving edits to the database row only:** Gamedev mode edits must also save back to the XML file on disk. The database row is a cache; the XML file is the source of truth.
- **Using &#10; for newlines:** ALWAYS use `<br/>` tags. lxml correctly escapes these as `&lt;br/&gt;` in attributes on disk.
- **Editing source column in translator mode path:** Gamedev inline edit should target specific attributes (ItemName, ItemDesc, CharacterName, etc.), not the generic "target" column.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Virtual scrolling | New scroll engine | VirtualGrid.svelte existing implementation | Already handles variable heights, row caching, buffer rows for 1000+ rows |
| Tree component | Custom tree from scratch | TMExplorerTree.svelte patterns (expand/collapse, icons, selection) | Battle-tested patterns with Carbon icons, dark theme, keyboard support |
| XML parsing | Custom XML parser | lxml via XMLParsingEngine (get_xml_parsing_engine) | Handles encoding detection, attribute case variants, br-tag preservation |
| File type detection | Manual tag checking | parse_xml_file() in xml_handler.py | Already detects translator vs gamedev via LocStr presence |
| br-tag normalization | Manual regex | postprocess.py normalize_br_tags() | Handles all variants (br, BR, br/, br /) |

**Key insight:** This phase is 80% integration and extension of existing code, 20% new code. The virtual scrolling, XML parsing, tree patterns, and dual mode detection all exist. The new parts are folder scanning, inline edit enablement, and save-back.

## Common Pitfalls

### Pitfall 1: Losing br-tags on Edit Round-Trip
**What goes wrong:** User edits text containing `<br/>` newlines. On save, the br-tags get double-escaped, mangled, or lost.
**Why it happens:** lxml auto-escapes `<` and `>` in attribute values. If you pre-escape before passing to lxml, you get `&amp;lt;br/&amp;gt;` (double-escaped).
**How to avoid:** Store the user's edit as-is with `<br/>` tags. Pass directly to `element.set(attr, value)`. lxml will write `&lt;br/&gt;` on disk, which is correct. On re-read, lxml returns `<br/>` in the string.
**Warning signs:** Seeing `&amp;lt;` or `&#10;` in saved XML files.

### Pitfall 2: Folder Scan Performance on Large Gamedata
**What goes wrong:** Scanning a real gamedata folder with 500+ XML files takes seconds, blocking the UI.
**Why it happens:** Counting entities (parsing XML headers) for every file during scan is expensive.
**How to avoid:** Return the folder tree immediately (just file names and sizes). Count entities lazily when a file is selected, or use a lightweight XML element count (read first few KB, count closing tags).
**Warning signs:** Explorer taking >1 second to load.

### Pitfall 3: VirtualGrid State Confusion Between Modes
**What goes wrong:** Switching between translator and gamedev files leaves stale state (filters, search, column widths).
**Why it happens:** VirtualGrid state persists across file switches because it's the same component instance.
**How to avoid:** Key the VirtualGrid on `fileId + fileType` so it remounts cleanly on file switch. Or explicitly reset state in the `$effect` that watches `fileId`.
**Warning signs:** Seeing translator columns in gamedev mode or vice versa.

### Pitfall 4: Editing the Wrong Row After Virtual Scroll
**What goes wrong:** User scrolls, starts editing a cell, but the edit applies to a different row because virtual scroll recycled the DOM element.
**Why it happens:** Virtual scrolling reuses DOM elements for different data rows. If the edit handler captures a stale row reference, the wrong row gets updated.
**How to avoid:** Always reference the row by its stable ID (row_num or database ID), never by DOM index. The existing VirtualGrid already does this correctly -- maintain this pattern when extending gamedev edit.
**Warning signs:** Editing row 50 but row 42 changes.

### Pitfall 5: Security -- Path Traversal in Folder Browse
**What goes wrong:** Malicious folder path allows reading arbitrary files outside the gamedata directory.
**Why it happens:** Backend accepts a user-provided path and scans it without validation.
**How to avoid:** The browse endpoint must validate that the requested path is within an allowed base directory. Use `Path.resolve()` and check `is_relative_to()` against the configured gamedata root.
**Warning signs:** Ability to browse `/etc/` or `C:\Windows\`.

## Code Examples

### Existing: parse_gamedev_nodes (server/tools/ldm/file_handlers/xml_handler.py:65-117)
```python
# Already implemented -- each XML element becomes a row with:
extra_data = {
    "node_name": elem.tag,           # e.g., "ItemInfo"
    "attributes": dict(elem.attrib), # e.g., {"Key": "10001", "StrKey": "STR_ITEM_0001", ...}
    "values": elem.text,             # Text content (rare in this data)
    "children_count": len(list(elem)),# Direct child count
    "depth": depth,                  # Nesting level (1 = direct child of root)
}
```

### Existing: gameDevColumns (VirtualGrid.svelte:323-329)
```javascript
const gameDevColumns = {
    row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
    node_name: { key: "source", label: "Node", width: 200, always: true },
    attributes: { key: "target", label: "Attributes", width: 300, always: true },
    values: { key: "values", label: "Values", width: 250, always: true },
    children_count: { key: "children_count", label: "Children", width: 100, always: true }
};
```

### Existing: TMExplorerTree expand/collapse pattern
```javascript
// State
let expandedNodes = $state(new Set(['unassigned']));

function toggleNode(nodeId) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(nodeId)) newSet.delete(nodeId);
    else newSet.add(nodeId);
    expandedNodes = newSet;
}

function isExpanded(nodeId) {
    return expandedNodes.has(nodeId);
}
```

### Mock Gamedata XML Structure (from Phase 15)
```xml
<!-- StaticInfo/iteminfo/iteminfo_weapon.staticinfo.xml -->
<ItemInfoList>
  <ItemInfo Key="10001" StrKey="STR_ITEM_0001"
    ItemName="철 검"
    ItemDesc="전투에서 유용한 검.&lt;br/&gt;장인이 정성껏 제작했다."
    ItemType="Weapon" Grade="Common" KnowledgeKey="KNOW_ITEM_0001"/>
</ItemInfoList>

<!-- StaticInfo/skillinfo/SkillTreeInfo.staticinfo.xml (NESTED) -->
<SkillTreeInfoList>
  <SkillTreeInfo Key="1" StrKey="TREE_001" CharacterKey="CHAR_CLASS_001" UIPageName="전사 스킬">
    <SkillNode NodeId="1" SkillKey="Skill_0001_강타" ParentNodeId="0" UIPositionXY="0,0"/>
    <SkillNode NodeId="2" SkillKey="Skill_0002_회전_베기" ParentNodeId="1" UIPositionXY="100,0"/>
  </SkillTreeInfo>
</SkillTreeInfoList>
```

### Entity Type to Editable Attributes Map
```python
# Which attributes are editable per entity type
EDITABLE_ATTRS = {
    "ItemInfo": ["ItemName", "ItemDesc"],
    "CharacterInfo": ["CharacterName"],  # Desc is in knowledge
    "SkillInfo": ["SkillName", "SkillDesc"],
    "GimmickInfo": ["Name", "Desc"],
    "KnowledgeInfo": ["Name", "Desc"],
    "FactionNode": ["AliasName"],
    # SkillNode, SkillTreeInfo: read-only structural data
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate GameDevGrid component | Extend VirtualGrid with gamedev inline edit | Phase 18 (now) | Avoids code duplication; VirtualGrid already has virtual scroll + column system |
| Upload-only file access | Direct folder browsing from disk | Phase 18 (now) | Game devs work with folder structures, not uploaded files |
| Read-only gamedev mode | Inline editing of Name/Desc attributes | Phase 18 (now) | Enables actual game dev authoring workflow |

## Open Questions

1. **File access model: upload vs direct disk browse?**
   - What we know: The existing system uploads files to the server and stores rows in the DB. Game dev workflow expects browsing a local folder.
   - What's unclear: Should we reuse the upload-to-DB flow (parse XML, store rows, edit rows in DB, then export back), or add a new direct-edit flow (parse XML on demand, edit in memory, save directly to file)?
   - Recommendation: **Use the upload-to-DB flow** for consistency. The browse endpoint discovers files, clicking a file triggers the existing upload/parse pipeline, edits go through the existing row update endpoint, and a new "save to file" endpoint writes changes back to XML. This reuses all existing infrastructure.

2. **GameDevPage layout: separate page vs mode within LDM?**
   - What we know: LDM.svelte currently switches between FilesPage, GridPage, TMPage via navigation store.
   - What's unclear: Should the file explorer be a new page type, or integrated into GridPage as a left panel?
   - Recommendation: **New GameDevPage** that composes FileExplorerTree (left panel) + GridPage (right area). Add `'gamedev'` as a new page type in the navigation store. This keeps the file explorer visible while editing.

3. **Dynamic columns per entity type?**
   - What we know: Different XML files have different attributes (ItemInfo has Grade/ItemType, CharacterInfo has Gender/Age/Job/Race).
   - What's unclear: Should we show all attributes as individual columns, or keep the current "Attributes" summary column?
   - Recommendation: **Show key reference attributes as dedicated columns** (Key, StrKey, KnowledgeKey -- always present). Show editable text fields (Name, Desc) as separate editable columns. Keep remaining attributes in a collapsed "Attributes" summary column. Dynamic based on first row's extra_data.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x + vitest (frontend) |
| Config file | tests/conftest.py (backend), locaNext/vitest.config.ts (frontend) |
| Quick run command | `python -m pytest tests/unit/test_gamedata_browse.py -x` |
| Full suite command | `python -m pytest tests/unit/ tests/api/ -x --timeout=30` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GDEV-01 | Browse endpoint returns folder tree | unit | `pytest tests/unit/test_gamedata_browse.py::test_scan_folder -x` | Wave 0 |
| GDEV-02 | Click file loads entities in grid | integration | `pytest tests/api/test_gamedata_endpoints.py::test_load_file -x` | Wave 0 |
| GDEV-03 | Hierarchy depth rendering | unit | `pytest tests/unit/test_gamedata_browse.py::test_parse_depth -x` | Wave 0 |
| GDEV-04 | Inline edit updates attribute | unit | `pytest tests/unit/test_gamedata_edit.py::test_update_attribute -x` | Wave 0 |
| GDEV-05 | Dynamic columns per type | unit | `pytest tests/unit/test_gamedata_browse.py::test_column_detection -x` | Wave 0 |
| GDEV-06 | br-tag preservation on save | unit | `pytest tests/unit/test_gamedata_edit.py::test_br_tag_round_trip -x` | Wave 0 |
| GDEV-07 | Virtual scroll 1000+ rows | manual-only | Manual: load large XML, verify smooth scrolling | N/A (VirtualGrid already tested) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/test_gamedata_browse.py tests/unit/test_gamedata_edit.py -x`
- **Per wave merge:** `python -m pytest tests/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_gamedata_browse.py` -- covers GDEV-01, GDEV-03, GDEV-05
- [ ] `tests/unit/test_gamedata_edit.py` -- covers GDEV-04, GDEV-06
- [ ] `tests/api/test_gamedata_endpoints.py` -- covers GDEV-02 (integration)

## Sources

### Primary (HIGH confidence)
- Direct code reading: VirtualGrid.svelte (gameDevColumns, fileType handling, virtual scroll)
- Direct code reading: TMExplorerTree.svelte (tree expand/collapse patterns)
- Direct code reading: xml_handler.py (parse_gamedev_nodes, file_type detection)
- Direct code reading: GridPage.svelte (file loading, side panel integration)
- Direct code reading: Mock gamedata XML files (18 StaticInfo files, real attribute patterns)
- Architecture research: .planning/research/ARCHITECTURE.md (Game Dev Grid data flow)

### Secondary (MEDIUM confidence)
- Phase 15 research: .planning/phases/15-mock-gamedata-universe/15-RESEARCH.md (data generation patterns)
- Project memory: MEMORY.md (dual UI architecture, export/merge strategy, br-tag rules)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in the project, no new dependencies
- Architecture: HIGH - extension of existing VirtualGrid, TMExplorerTree, and xml_handler patterns verified via code reading
- Pitfalls: HIGH - br-tag handling is well-documented in project memory and existing postprocess.py; path traversal is standard security concern
- Inline edit: MEDIUM - extending VirtualGrid for gamedev mode requires careful state management; the exact edit-save flow needs implementation decisions

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- project-internal patterns, no external dependencies changing)
