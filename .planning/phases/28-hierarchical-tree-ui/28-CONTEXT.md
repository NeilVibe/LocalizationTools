# Phase 28: Hierarchical Tree UI - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the flat VirtualGrid on the Game Data page with a hierarchical tree UI for exploring XML gamedata. Users can expand/collapse nodes, view node details in a right panel, edit text attributes, and follow cross-reference links between entities. The tree loads from backend JSON (Phase 27 API) and supports full folder loading.

Requirements: TREE-01, TREE-02, TREE-03, TREE-04, TREE-06, TREE-08

</domain>

<decisions>
## Implementation Decisions

### Tree Component Layout
- Split layout: tree panel (left) + detail panel (right) — replaces current FileExplorerTree + VirtualGrid layout
- GameDevPage.svelte gets a new `GameDataTree.svelte` component that replaces VirtualGrid when in tree mode
- Folder loading reuses existing browse API flow, then lazy-fetches tree JSON per file when the file node is expanded (don't parse all files upfront — 5000+ entities would be slow)
- FileExplorerTree stays as the folder/file browser on the far left — clicking a file switches the main area to the tree view for that file
- "Load All" button to fetch folder tree via `POST /gamedata/tree/folder` when user wants the full picture

### Node Expand/Collapse Behavior
- Single click on a node: select it (shows detail in right panel)
- Click on chevron or double-click: expand/collapse children
- All nodes start collapsed except the first level
- Keyboard navigation: arrow keys to move, Enter to expand/collapse, space to select

### Dynamic Node Rendering
- Same `GameDataTree.svelte` component renders all entity types
- Entity type determines: icon, color accent, and which attributes to show inline in the tree row
- Inline tree row shows: icon + tag name + primary name attribute (e.g., ItemName, CharacterName, SkillName from EDITABLE_ATTRS first entry)
- If entity type has no EDITABLE_ATTRS (like NodeWaypointInfo), show the Key attribute as label

### Node Detail Panel
- Right panel shows all attributes of the selected node as key-value pairs
- Editable attributes (from EDITABLE_ATTRS mapping) render as text input fields
- Non-editable attributes render as read-only styled text
- Save on blur with optimistic UI — update locally, POST to `/gamedata/save` endpoint, revert on failure
- Direct children shown as compact clickable list at the bottom of the detail panel

### Cross-Reference Navigation
- Key attributes that match known cross-reference patterns (LearnKnowledgeKey, ParentNodeId, etc.) render as blue clickable links
- Clicking a cross-ref link: find target entity in tree, expand the path to it, select it, scroll into view
- Cross-ref resolution uses the tree data already in memory (no extra API call)
- If target not found (entity in a different file not yet loaded), show tooltip: "Entity in [filename] — click to load"

### Visual Design
- Color-coded node types: distinct muted color per entity type (consistent with Codex EntityCard colors)
- Entity type icons: folder-like icons for container nodes (SkillTreeInfo, GimmickGroupInfo), document icons for leaf entities
- Expand/collapse animation: 200ms CSS height transition + chevron rotation
- Proper indentation: 20px per nesting level with visible tree lines (vertical + horizontal connector lines)
- Hover preview: tooltip showing first 3 attributes on hover over any tree node
- Selected node highlight: subtle background color + left border accent

### Claude's Discretion
- Exact color palette for entity type coding (should complement existing Codex colors)
- Loading skeleton design during tree fetch
- Empty state design when no file is selected
- Exact tooltip positioning and styling
- Whether to show node count badges on expandable nodes
- Tree search/filter implementation details (if time permits — nice-to-have)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend Tree API (Phase 27 — built)
- `server/tools/ldm/services/gamedata_tree_service.py` — GameDataTreeService with lxml tree walking, reference resolution, TreeNode building
- `server/tools/ldm/schemas/gamedata.py` — TreeNode, TreeRequest, GameDataTreeResponse, FolderTreeDataRequest, FolderTreeDataResponse schemas
- `server/tools/ldm/routes/gamedata.py` — POST /gamedata/tree and POST /gamedata/tree/folder endpoints

### Existing GameDev UI (extend these)
- `locaNext/src/lib/components/pages/GameDevPage.svelte` — Current page layout with FileExplorerTree + VirtualGrid. Tree view replaces VirtualGrid section.
- `locaNext/src/lib/components/ldm/FileExplorerTree.svelte` — Folder/file browser with expand/collapse pattern. Reuse its Svelte 5 patterns.
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` — Current flat grid view. Keep available as fallback but tree is the primary view.

### Tree Pattern References
- `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` — Hierarchical tree with expand/collapse, selection, context menu. Closest UI pattern to follow.
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — Entity detail panel with attributes. Reuse detail panel patterns.
- `locaNext/src/lib/components/ldm/EntityCard.svelte` — Entity type icon and color mapping. Reuse for consistent type styling.

### Data References
- `server/tools/ldm/services/gamedata_browse_service.py` lines 24-38 — EDITABLE_ATTRS mapping per entity type
- `server/tools/ldm/services/gamedata_edit_service.py` — Entity attribute editing with br-tag preservation (reuse for save flow)

### Mock Fixtures
- `tests/fixtures/mock_gamedata/StaticInfo/` — All mock XML files for testing tree rendering

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FileExplorerTree.svelte`: Expand/collapse pattern with expandedNodes Set, Svelte 5 Runes, Carbon icons (ChevronDown/Right, Folder/FolderOpen)
- `TMExplorerTree.svelte`: Hierarchical tree with selection, context menu, multi-select — closest pattern for new GameDataTree
- `EntityCard.svelte`: Entity type icons and color styling — reuse for node type visual differentiation
- `CodexEntityDetail.svelte`: Attribute detail panel — reuse for node detail view
- `VirtualGrid.svelte`: Existing grid with gamedev mode fetch — keep as alternative view
- `api.js`: `getAuthHeaders()`, `getApiBase()` — standard API utilities
- `navigation.js`: `openFile`, `openFileInGrid`, `gamedevBasePath` stores — reuse for tree state management

### Established Patterns
- Svelte 5 Runes: `$state()`, `$derived()`, `$effect()`, `$props()` — mandatory
- Carbon Components: Button, TextInput, SkeletonText, icons — consistent UI
- Optimistic UI: update state immediately, revert on API failure
- Logger: `logger.info()`, `logger.apiCall()`, `logger.userAction()` — standard logging
- API calls: fetch with getAuthHeaders, JSON body, error handling via try-catch

### Integration Points
- GameDevPage.svelte: Replace VirtualGrid section with GameDataTree when tree mode active
- FileExplorerTree.svelte: `onFileSelect` callback triggers tree loading for selected file
- Backend: POST /gamedata/tree for single file, POST /gamedata/tree/folder for full folder
- Save: POST /gamedata/save for attribute edits (existing endpoint)

</code_context>

<specifics>
## Specific Ideas

- Tree should be "better than VS Code tree view" per TREE-08 — proper indentation with visible tree lines, not just indented text
- All 9+ entity types in mock_gamedata should render correctly (ItemInfo, CharacterInfo, SkillInfo, KnowledgeInfo, GimmickGroupInfo, RegionInfo, QuestInfo, SceneObjectData, SealDataInfo, SkillTreeInfo, NodeWaypointInfo, FactionGroup)
- Cross-reference links are a key differentiator — SkillInfo.LearnKnowledgeKey → KnowledgeInfo, KnowledgeList parent-child, ParentNodeId chains
- The tree must handle the triple-nesting from Phase 27 (SkillNode > SkillNode > SkillNode via ParentId)

</specifics>

<deferred>
## Deferred Ideas

- Tree search/filter (type to filter visible nodes) — nice-to-have, could be Phase 28 stretch or Phase 29
- Drag-drop reordering of tree nodes — out of scope (read + edit only, no CRUD)
- Tree diff view (compare two versions of same file) — future phase

</deferred>

---

*Phase: 28-hierarchical-tree-ui*
*Context gathered: 2026-03-16*
