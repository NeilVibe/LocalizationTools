# Phase 20: Interactive World Map - Research

**Researched:** 2026-03-15
**Domain:** SVG interactive map visualization with pan/zoom, Svelte 5, D3-zoom, FastAPI backend
**Confidence:** HIGH

## Summary

Phase 20 builds an interactive SVG world map showing 14 region nodes from mock FactionNode data with WorldPosition coordinates (X,Z plane, range 500-5000), connected by NodeWaypointInfo route paths. The map requires pan/zoom interaction, hover tooltips with region metadata, click-through to Codex entity pages, and route visualization between connected nodes.

The technical stack is well-defined: D3-zoom for pan/zoom behavior on an SVG canvas (the only mature pan/zoom library for SVG in the npm ecosystem), a lightweight backend endpoint to serve pre-parsed map data (nodes + routes + Codex cross-refs), and a Svelte 5 page component following the exact pattern established by CodexPage (Phase 19). The 14-node dataset is trivially small -- no virtualization or tiling needed.

**Primary recommendation:** Use `d3-zoom` (standalone, ~12KB) for pan/zoom on a Svelte 5 `<svg>` element. Backend serves a single `/api/ldm/worldmap/data` endpoint returning nodes with positions + routes + entity cross-refs from the existing CodexService. Frontend is a single `WorldMapPage.svelte` with inline SVG rendering.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MAP-01 | Interactive map renders region nodes at correct WorldPosition coordinates (X, Z from XML) | Backend parses FactionNode XML, extracts X/Z from "X,0,Z" format. Frontend maps to SVG viewBox coordinates via linear scale. |
| MAP-02 | Hover over a map node shows tooltip with name, description, and key NPCs | Backend enriches nodes with Codex entity data (name, description, related characters). Frontend renders tooltip via absolute-positioned div on mouseover. |
| MAP-03 | Click a map node opens detail panel linking to Codex pages (characters, items, quests in that region) | Backend cross-refs region entities via CodexService. Frontend panel lists related entities with click-through to Codex navigation (goToCodex + entity selection). |
| MAP-04 | Route connections between nodes are visualized (from NodeWaypointInfo waypoints) | Backend parses NodeWaypointInfo XML, returns waypoint position arrays. Frontend renders as SVG `<path>` elements using waypoint coordinates. |
| MAP-05 | Map supports pan and zoom interaction (d3-zoom or equivalent) | d3-zoom library applied to SVG `<g>` transform. Handles wheel zoom, drag pan, double-click reset. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| d3-zoom | ^3.0.0 | Pan/zoom transform management | Industry standard for SVG pan/zoom. Used by every major SVG map/graph visualization. Only ~12KB standalone. |
| d3-selection | ^3.0.0 | DOM selection for d3-zoom binding | Required peer dependency for d3-zoom event handling. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| carbon-icons-svelte | ^13.0.0 | Map control icons (zoom in/out, reset) | Already installed. Use for toolbar buttons. |
| carbon-components-svelte | ^0.95.0 | Tag, Tooltip, InlineLoading components | Already installed. Reuse for region type badges and loading states. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| d3-zoom | panzoom (npm) | Simpler API but no SVG transform support -- d3-zoom is purpose-built for SVG |
| d3-zoom | Leaflet/MapLibre | Massive overkill for 14 nodes on a simple coordinate plane. Adds 200KB+ and tile-based paradigm we don't need |
| SVG rendering | Canvas/WebGL | Canvas loses DOM events (hover, click). SVG is perfect for <100 elements |

**Installation:**
```bash
cd locaNext && npm install d3-zoom d3-selection
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  schemas/worldmap.py          # Pydantic models (MapNode, MapRoute, WorldMapData)
  services/worldmap_service.py # Parse FactionNode + NodeWaypointInfo + Codex cross-ref
  routes/worldmap.py           # GET /api/ldm/worldmap/data endpoint

locaNext/src/lib/
  components/pages/WorldMapPage.svelte    # Main page (follows CodexPage pattern)
  components/ldm/MapCanvas.svelte         # SVG + d3-zoom canvas
  components/ldm/MapTooltip.svelte        # Hover tooltip overlay
  components/ldm/MapDetailPanel.svelte    # Click detail panel with Codex links

tests/unit/
  test_worldmap_service.py     # Backend service unit tests
  ldm/test_worldmap_routes.py  # API endpoint tests
```

### Pattern 1: Navigation Integration
**What:** Add 'worldmap' to the currentPage store and wire into LDM.svelte + layout header
**When to use:** Always -- follows exact Phase 18/19 pattern
**Example:**
```javascript
// navigation.js -- add goToWorldMap()
export function goToWorldMap() {
  currentPage.set('worldmap');
  openFile.set(null);
}

// LDM.svelte -- add page case
{:else if $currentPage === 'worldmap'}
  <WorldMapPage />

// +layout.svelte -- add nav tab with Map icon
```

### Pattern 2: SVG + d3-zoom in Svelte 5
**What:** Bind d3-zoom to an SVG `<g>` element via $effect for clean lifecycle management
**When to use:** MAP-05 pan/zoom requirement
**Example:**
```svelte
<script>
  import { zoom, zoomIdentity } from 'd3-zoom';
  import { select } from 'd3-selection';
  import { onMount } from 'svelte';

  let svgEl = $state(null);
  let transform = $state(zoomIdentity);

  onMount(() => {
    const zoomBehavior = zoom()
      .scaleExtent([0.5, 4])
      .on('zoom', (event) => {
        transform = event.transform;
      });

    select(svgEl).call(zoomBehavior);

    // Double-click to reset
    select(svgEl).on('dblclick.zoom', () => {
      select(svgEl).transition().duration(300).call(zoomBehavior.transform, zoomIdentity);
    });
  });
</script>

<svg bind:this={svgEl} viewBox="0 0 1000 1000" class="map-svg">
  <g transform="translate({transform.x},{transform.y}) scale({transform.k})">
    <!-- nodes, routes, labels rendered here -->
  </g>
</svg>
```

### Pattern 3: Backend WorldMapService (Singleton Pattern)
**What:** Module-level singleton parsing FactionNode + NodeWaypointInfo XML, enriched with CodexService cross-refs
**When to use:** Same pattern as CodexService, MapDataService, GameDataBrowseService
**Example:**
```python
class WorldMapService:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._nodes: list[MapNode] = []
        self._routes: list[MapRoute] = []
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        self._parse_faction_nodes()
        self._parse_waypoints()
        self._enrich_with_codex()
        self._initialized = True

    def get_map_data(self) -> WorldMapData:
        if not self._initialized:
            self.initialize()
        return WorldMapData(nodes=self._nodes, routes=self._routes)
```

### Pattern 4: Coordinate Mapping
**What:** Map XML WorldPosition (X: 500-5000, Z: 500-5000) to SVG viewBox coordinates
**When to use:** MAP-01 rendering
**Example:**
```javascript
// XML coordinates: X=500..5000, Z=500..5000
// SVG viewBox: 0 0 1000 1000
// Linear mapping: svgX = (worldX - 500) / 4500 * 1000
// svgY = (worldZ - 500) / 4500 * 1000  (Z maps to Y in 2D)
function worldToSvg(worldX, worldZ) {
  const padding = 50; // leave margin
  const range = 1000 - 2 * padding;
  return {
    x: padding + ((worldX - 500) / 4500) * range,
    y: padding + ((worldZ - 500) / 4500) * range
  };
}
```

### Pattern 5: Tooltip Positioning (Hover)
**What:** Position tooltip div relative to SVG node using getBoundingClientRect + transform offset
**When to use:** MAP-02 hover tooltip
**Example:**
```svelte
<!-- Use position:fixed tooltip outside SVG, positioned via mouse event -->
<script>
  let tooltipNode = $state(null);
  let tooltipPos = $state({ x: 0, y: 0 });

  function handleNodeHover(node, event) {
    tooltipNode = node;
    tooltipPos = { x: event.clientX + 12, y: event.clientY - 12 };
  }

  function handleNodeLeave() {
    tooltipNode = null;
  }
</script>

{#if tooltipNode}
  <div class="map-tooltip" style="left:{tooltipPos.x}px; top:{tooltipPos.y}px;">
    <strong>{tooltipNode.name}</strong>
    <p>{tooltipNode.description}</p>
    {#if tooltipNode.npcs?.length}
      <span>NPCs: {tooltipNode.npcs.join(', ')}</span>
    {/if}
  </div>
{/if}
```

### Anti-Patterns to Avoid
- **Canvas for <100 elements:** SVG is simpler, faster to develop, and has native DOM events. Canvas only needed for 1000+ elements.
- **Full D3 import:** Never `npm install d3` (500KB+). Only install `d3-zoom` + `d3-selection` (~25KB total).
- **Svelte 4 reactive declarations:** No `$:` syntax. Use `$state`, `$derived`, `$effect`.
- **Leaflet/tile maps:** This is a coordinate-space visualization of game world positions, not a geographic map. No tiles needed.
- **Rebuilding d3-zoom from scratch:** Pan/zoom with proper inertia, wheel handling, touch support, and transform math is deceptively complex.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pan/zoom interaction | Custom mouse/wheel handlers | d3-zoom | Touch support, inertia, scale limits, transform matrix -- 500+ lines of edge cases |
| SVG path interpolation | Manual control point calculation | SVG polyline with waypoint coordinates | Waypoints are already intermediate positions -- just connect them |
| Entity cross-referencing | Re-parse XML for Codex data | Reuse CodexService singleton | Already has entity registry with knowledge key resolution |
| Tooltip positioning | Custom portal/position code | Fixed-position div with clientX/clientY | Mouse-following tooltip is simpler and works with zoom transforms |

**Key insight:** The map is a visualization layer on top of existing data services. The CodexService already has the entity registry, cross-refs, and knowledge resolution. WorldMapService only needs to parse the spatial data (FactionNode positions + NodeWaypointInfo routes) and merge with Codex data.

## Common Pitfalls

### Pitfall 1: d3-zoom Event Interference with Svelte
**What goes wrong:** d3-zoom attaches wheel/mousedown handlers that conflict with Svelte's event delegation
**Why it happens:** d3 uses direct DOM manipulation, Svelte uses delegated events
**How to avoid:** Apply d3-zoom in onMount after SVG is in DOM. Use $effect cleanup to remove zoom behavior on unmount. Never mix Svelte event handlers on the same SVG element where d3-zoom is applied.
**Warning signs:** Double-firing events, zoom not working, page scrolling instead of zooming

### Pitfall 2: SVG Tooltip Clipping
**What goes wrong:** Tooltip renders inside SVG and gets clipped by viewBox/overflow
**Why it happens:** SVG overflow:hidden is default behavior
**How to avoid:** Render tooltip as HTML `<div>` with `position:fixed` outside the SVG element. Use mouse clientX/clientY for positioning, not SVG coordinates.
**Warning signs:** Tooltip cut off at SVG edges, disappearing on zoom

### Pitfall 3: Coordinate System Confusion (Y-axis)
**What goes wrong:** Map appears vertically flipped
**Why it happens:** Game world Z-axis increases "forward" but SVG Y-axis increases downward
**How to avoid:** Verify with mock data visual inspection. If flipped, invert Z mapping: `svgY = range - ((worldZ - min) / span) * range`
**Warning signs:** Regions appear in wrong relative positions

### Pitfall 4: Zoom Transform Not Applied to Click Handlers
**What goes wrong:** Click coordinates don't match node positions after zooming
**Why it happens:** Click event gives screen coordinates but nodes are transformed by zoom
**How to avoid:** Use d3-zoom's `transform.invert()` to convert screen coordinates to SVG space, OR attach click handlers directly to SVG node elements (preferred -- no coordinate conversion needed)
**Warning signs:** Clicking on a node after zoom/pan opens wrong region

### Pitfall 5: Route Paths Not Scaling with Zoom
**What goes wrong:** Routes render at wrong positions or don't zoom with nodes
**Why it happens:** Routes rendered outside the zoom transform group
**How to avoid:** Render both nodes AND routes inside the same `<g>` element that receives the d3-zoom transform
**Warning signs:** Routes stay static while nodes move during pan/zoom

## Code Examples

### Backend: WorldMapService Data Model
```python
# schemas/worldmap.py
from pydantic import BaseModel
from typing import List, Optional

class MapNode(BaseModel):
    strkey: str               # FNODE_0001
    knowledge_key: str        # KNOW_REGION_0001
    name: str                 # Region name from Codex
    description: Optional[str] = None
    region_type: str          # Main, Sub, Dungeon, Town, Fortress, Wilderness
    x: float                  # WorldPosition X
    z: float                  # WorldPosition Z
    npcs: List[str] = []      # Character names in this region (from Codex related_entities)
    entity_type_counts: dict = {}  # {"character": 3, "item": 5, "skill": 2}

class MapRoute(BaseModel):
    from_node: str            # FNODE_0001
    to_node: str              # FNODE_0002
    waypoints: List[dict]     # [{"x": 2921.3, "z": 4439.2}, ...]

class WorldMapData(BaseModel):
    nodes: List[MapNode]
    routes: List[MapRoute]
    bounds: dict = {}         # {"min_x": 500, "max_x": 5000, "min_z": 500, "max_z": 5000}
```

### Backend: Parsing FactionNode XML
```python
# Follows exact same lxml pattern as codex_service.py
def _parse_faction_nodes(self):
    faction_path = self.base_dir / "factioninfo" / "FactionInfo.staticinfo.xml"
    tree = etree.parse(str(faction_path))
    for el in tree.getroot().iter("FactionNode"):
        strkey = el.get("StrKey", "")
        wp = el.get("WorldPosition", "")
        parts = wp.split(",")
        x, z = float(parts[0]), float(parts[2])
        knowledge_key = el.get("KnowledgeKey", "")
        region_type = el.get("Type", "")
        # Enrich with Codex name/description later
        self._nodes.append(MapNode(
            strkey=strkey, knowledge_key=knowledge_key,
            name=strkey,  # placeholder until Codex enrichment
            region_type=region_type, x=x, z=z
        ))
```

### Frontend: Route Path Rendering
```svelte
<!-- SVG polyline for waypoint routes -->
{#each routes as route (route.from_node + '-' + route.to_node)}
  {@const fromNode = nodeMap.get(route.from_node)}
  {@const toNode = nodeMap.get(route.to_node)}
  {#if fromNode && toNode}
    {@const points = [
      worldToSvg(fromNode.x, fromNode.z),
      ...route.waypoints.map(wp => worldToSvg(wp.x, wp.z)),
      worldToSvg(toNode.x, toNode.z)
    ]}
    <polyline
      points={points.map(p => `${p.x},${p.y}`).join(' ')}
      fill="none"
      stroke="var(--cds-border-subtle-01)"
      stroke-width="1.5"
      stroke-dasharray="4,4"
      opacity="0.6"
    />
  {/if}
{/each}
```

### Frontend: Region Node Rendering
```svelte
{#each nodes as node (node.strkey)}
  {@const pos = worldToSvg(node.x, node.z)}
  <g
    class="map-node"
    transform="translate({pos.x},{pos.y})"
    onmouseenter={(e) => handleNodeHover(node, e)}
    onmouseleave={handleNodeLeave}
    onclick={() => handleNodeClick(node)}
    role="button"
    tabindex="0"
  >
    <circle
      r={NODE_RADIUS[node.region_type] || 8}
      fill={NODE_COLORS[node.region_type] || '#0f62fe'}
      stroke="var(--cds-text-01)"
      stroke-width="1.5"
    />
    <text
      y={-12}
      text-anchor="middle"
      class="node-label"
      fill="var(--cds-text-01)"
      font-size="10"
    >{node.name}</text>
  </g>
{/each}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full D3 bundle (d3@7, 500KB) | Tree-shakeable d3-zoom + d3-selection (~25KB) | D3 v7+ (2021) | 95% smaller bundle for pan/zoom only use case |
| Canvas-based maps | SVG for small datasets (<500 elements) | Ongoing | Better accessibility, DOM events, CSS styling |
| Leaflet for all maps | Plain SVG for coordinate visualizations | N/A | Leaflet is for geographic tiles, not game coordinate spaces |

**Deprecated/outdated:**
- d3-zoom v1/v2: Use v3 (current). API is stable and backward-compatible.

## Open Questions

1. **Background texture or plain background?**
   - What we know: Map is a coordinate visualization, not a geographic map. No tile source exists.
   - What's unclear: Should it have a subtle parchment/grid background or plain Carbon dark background?
   - Recommendation: Use plain Carbon background (var(--cds-background)) with subtle grid lines for spatial reference. Matches project dark theme.

2. **Region detail panel: overlay or side panel?**
   - What we know: Codex uses full-page navigation. Game Dev Grid uses inline editing.
   - What's unclear: Should clicking a node open an inline side panel or navigate to Codex?
   - Recommendation: Inline side panel (right side, similar to RightPanel pattern) showing region summary with "Open in Codex" links. Avoids losing map context on navigation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Playwright (frontend) |
| Config file | tests/conftest.py (backend), locaNext/playwright.config.ts (frontend) |
| Quick run command | `python -m pytest tests/unit/ldm/test_worldmap_service.py -x` |
| Full suite command | `python -m pytest tests/unit/ldm/ tests/unit/test_mock_map_data.py -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-01 | Nodes render at WorldPosition coordinates | unit | `pytest tests/unit/ldm/test_worldmap_service.py::test_node_positions -x` | No -- Wave 0 |
| MAP-02 | Tooltip shows name, description, NPCs | unit + integration | `pytest tests/unit/ldm/test_worldmap_service.py::test_node_enrichment -x` | No -- Wave 0 |
| MAP-03 | Click opens detail with Codex links | unit | `pytest tests/unit/ldm/test_worldmap_service.py::test_codex_crossrefs -x` | No -- Wave 0 |
| MAP-04 | Route connections from waypoints | unit | `pytest tests/unit/ldm/test_worldmap_service.py::test_route_parsing -x` | No -- Wave 0 |
| MAP-05 | Pan/zoom interaction | manual-only | Visual verification in browser | N/A -- d3-zoom is trusted library |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_worldmap_service.py -x`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ tests/unit/test_mock_map_data.py -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_worldmap_service.py` -- covers MAP-01 through MAP-04
- [ ] `tests/unit/ldm/test_worldmap_routes.py` -- covers API endpoint validation
- [ ] `npm install d3-zoom d3-selection` -- frontend dependency

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: FactionInfo.staticinfo.xml (14 nodes, X/Z range 500-5000)
- Direct codebase inspection: NodeWaypointInfo.staticinfo.xml (13 routes with 2-4 waypoints each)
- Direct codebase inspection: codex_service.py (entity registry, FactionNode -> region entity type)
- Direct codebase inspection: navigation.js (currentPage store, goToCodex/goToGameDev pattern)
- Direct codebase inspection: LDM.svelte (page routing pattern with {#if $currentPage === 'x'})
- Direct codebase inspection: CodexPage.svelte (page component pattern, Carbon Components, API fetch pattern)
- Direct codebase inspection: generate_mock_universe.py (coordinate generation, region types)
- Direct codebase inspection: test_mock_map_data.py (existing map data tests)

### Secondary (MEDIUM confidence)
- d3-zoom API: Well-documented, stable since v3, widely used in production SVG applications
- Package sizes: d3-zoom ~12KB, d3-selection ~12KB (from bundlephobia, verified pattern)

### Tertiary (LOW confidence)
- None. All findings based on direct codebase inspection and well-known library capabilities.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- d3-zoom is the only serious SVG pan/zoom library; project patterns are well-established
- Architecture: HIGH -- follows exact patterns from Phase 18/19 (singleton service, page component, API route)
- Pitfalls: HIGH -- based on common d3+framework integration patterns and SVG rendering known issues

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no fast-moving dependencies)
