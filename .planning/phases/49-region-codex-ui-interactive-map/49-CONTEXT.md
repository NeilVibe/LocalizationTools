# Phase 49: Region Codex UI + Interactive Map - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Svelte 5 Region Codex page with FactionGroup→Faction→FactionNode tree navigation AND an interactive map with real WorldPosition coordinates via d3-zoom. All data from MegaIndex. Extends existing WorldMap page pattern.

</domain>

<decisions>
## Implementation Decisions

### UI Layout
- Split view: tree navigation on left, interactive map on right
- FactionGroup→Faction→FactionNode tree — collapsible hierarchy
- Map renders real WorldPosition coordinates using d3-zoom (existing pattern in WorldMapPage)
- Click tree node → highlight on map + show detail panel
- Click map node → select in tree + show detail panel

### Map
- Use existing d3-zoom + SVG pattern from WorldMapPage.svelte
- Nodes positioned using WorldPosition (x, z) from MegaIndex D4 region_by_strkey
- Node styling: different icons per node_type (Town, Dungeon, Fortress, etc.)
- Region display names from MegaIndex D16 region_display_names
- Parchment background aesthetic (already built in v3.5 Phase 38)

### Detail Panel
- Region name (DisplayName), WorldPosition coordinates, node type badge
- Knowledge cross-references
- DDS image if available via strkey_to_image_path

### FactionGroup Tabs
- Top-level tabs for FactionGroups (World, Underground, etc.)
- Each tab shows its faction tree

### Claude's Discretion
- Map zoom limits and default viewport
- Node size and spacing
- Detail panel layout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `locaNext/src/lib/components/pages/WorldMapPage.svelte` — d3-zoom + SVG map, parchment aesthetic, node markers
- MegaIndex D4 (region_by_strkey), D5 (faction_by_strkey), D6 (faction_group_by_strkey), D16 (region_display_names), C1 (strkey_to_image_path)
- All previous Codex patterns (ItemCodex, CharacterCodex, AudioCodex)

### Integration Points
- API: GET /api/ldm/codex/regions (list), /regions/tree (hierarchy), /regions/{strkey} (detail)
- Navigation: "Regions" tab in sidebar

</code_context>

<specifics>
## Specific Ideas

- Map and tree should be synchronized — selecting in one updates the other
- WorldPosition uses (x, z) for 2D map display (y is elevation, ignored for top-down view)

</specifics>

<deferred>
## Deferred Ideas

- Shop positions on map (v6.0)
- 3-hop Knowledge_Contents position chain (v6.0)

</deferred>
