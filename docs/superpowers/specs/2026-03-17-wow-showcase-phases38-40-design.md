# WOW Showcase Design: Phases 38-40

**Date:** 2026-03-17
**Status:** Approved (auto-mode)
**Design Direction:** Fantasy Epic Cinema — maximalist dark theme, warm copper/gold, parchment textures, theatrical motion

## Overview

Three phases transforming LocaNext from functional to STUNNING for executive demo:
- **Phase 38:** Fantasy World Map (parchment, polygons, route animations)
- **Phase 39:** Codex Cards + Relationship Graph (glassmorphism, D3 force)
- **Phase 40:** Cross-cutting WOW Polish (transitions, shimmer, command palette)

## Design Principles

1. **Build on existing architecture** — MapCanvas.svelte, CodexPage.svelte, WorldMapService stay; add visual layers
2. **Warm copper palette** — `--warm: #d49a5c`, `--warm-bright: #f0b878`, sepia tones for fantasy
3. **Entity color system** — reuse Phase 37 semantic colors (purple=character, cyan=item, teal=region)
4. **GPU-only animations** — transform + opacity only, ease-out-quart easing
5. **Svelte 5 Runes** — $state, $derived, $effect everywhere
6. **No external images for backgrounds** — CSS gradients + SVG only (keeps bundle clean)

## Phase 38: Fantasy World Map

### 38-01: Mock Map Data + Parchment Aesthetic

**Backend:**
- Extend `worldmap_service.py` to support polygon boundaries per region
- Add showcase map data: 10 Korean-named fantasy regions with polygons
  - 안개의 숲 (Mist Forest), 봉인된 도서관 (Sealed Library), 흑성 마을 (Blackstar Village)
  - 용의 무덤 (Dragon's Tomb), 현자의 탑 (Sage Tower), 어둠의 교단 (Dark Cult HQ)
  - 바람의 협곡 (Wind Canyon), 잊힌 요새 (Forgotten Fortress), 달빛 호수 (Moonlight Lake), 화산 지대 (Volcanic Zone)
- Each region: `id`, `name_kr`, `name_en`, `region_type`, `polygon_points[]`, `center_x/y`, `danger_level`, `description_kr`
- 13 routes between regions with `danger_level` (1-3) and `travel_time`

**Frontend:**
- Parchment background: multi-layer CSS radial-gradient
  ```css
  background:
    radial-gradient(ellipse at 20% 30%, rgba(212,154,92,0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, rgba(139,105,20,0.1) 0%, transparent 50%),
    linear-gradient(180deg, #1a1408 0%, #2a1f0e 50%, #1a1408 100%);
  ```
- Ornamental SVG border: compass rose at corners, decorative line borders
- CSS filter for aged paper texture effect: `filter: url(#noise)` with SVG feTurbulence

**Files Modified:**
- `server/tools/ldm/services/worldmap_service.py` — add polygon data loading
- `server/tools/ldm/schemas/worldmap.py` — add polygon schema
- `tests/fixtures/mock_gamedata/` — add showcase map data XML
- `locaNext/src/lib/components/ldm/MapCanvas.svelte` — parchment background layer

### 38-02: Region Polygons + Terrain Icons + Node Markers

**Region Polygons:**
- SVG `<polygon>` elements with semi-transparent fill per region_type
- Fill: `rgba(entity_color, 0.15)` with `stroke: rgba(entity_color, 0.4)`
- Hover state: fill opacity → 0.3, stroke-width → 2, glow filter
- Korean region name rendered as `<text>` with text-shadow glow

**Terrain SVG Icons (inline, no external files):**
| Type | Icon | Size |
|------|------|------|
| Town | Castle turret | 24x24 |
| Dungeon | Skull | 24x24 |
| Fortress | Shield | 24x24 |
| Wilderness | Tent | 24x24 |
| Main | Compass rose | 28x28 |
| Sub | Tree | 20x20 |

**Files Modified:**
- `locaNext/src/lib/components/ldm/MapCanvas.svelte` — polygon rendering, icon system
- New: `locaNext/src/lib/components/ldm/MapIcons.svelte` — SVG icon components

### 38-03: Route Animations + Zoom + Mini-map

**Route Animations:**
- Animated stroke-dashoffset on hover (CSS animation, 2s linear infinite)
- Danger coloring: level 1 = `#24a148` (green), level 2 = `#f1c21b` (amber), level 3 = `#da1e28` (red)
- Route width: 2px default, 3px on hover
- Travel direction arrows along path (SVG marker-mid)

**Zoom Interactions:**
- Click region polygon → d3.transition().duration(500).call(zoom.transform, fitBounds)
- Smooth ease-out-quart: `cubic-bezier(0.25, 1, 0.5, 1)`
- Double-click to zoom in, scroll wheel for manual zoom

**Mini-map:**
- 150x150px fixed position bottom-right
- Shows all regions as simplified shapes
- Viewport rectangle shows current view area
- Click mini-map to pan main view

**Detail Panel:**
- Slides in from right (300ms ease-out) on region click
- Shows: region name (KR), type badge, danger level, description, connected entities
- Reuses warm glow border from Phase 37

**Files Modified:**
- `locaNext/src/lib/components/ldm/MapCanvas.svelte` — route animation, zoom, mini-map
- `locaNext/src/lib/components/ldm/MapDetailPanel.svelte` — enhanced panel
- `locaNext/src/lib/components/ldm/MapTooltip.svelte` — enhanced tooltip

## Phase 39: Codex Cards + Relationship Graph

### 39-01: Glassmorphism Entity Cards

**Card Design:**
```css
.codex-card {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(212, 154, 92, 0.2);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}
.codex-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(212, 154, 92, 0.15);
}
```

**Parallax Hover:**
- Track mouse position relative to card center
- Apply `transform: perspective(800px) rotateX(Ydeg) rotateY(Xdeg)` (max ±5deg)
- Image shifts slightly opposite direction (parallax depth)
- Use $effect for mousemove listener, cleanup on destroy

**Card Content:**
- Hero image: AI portrait (existing Gemini images) with shimmer-to-reveal
- Entity type badge (top-right, color-coded)
- Name in Korean + English
- Brief description (2 lines, ellipsis overflow)
- Stats row: related entities count, cross-ref count

**Entrance Animation:**
- Staggered slide-up + fade: `animation-delay: calc(var(--i) * 60ms)`
- Use CSS transition (NOT animation) to avoid replay on re-render (Phase 37 lesson)

**Files Modified:**
- `locaNext/src/lib/components/pages/CodexPage.svelte` — card layout
- New: `locaNext/src/lib/components/ldm/CodexCard.svelte` — glassmorphism card component
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — enhanced detail view

### 39-02: D3 Force-Directed Relationship Graph

**Architecture:**
- New "Relationships" tab in CodexPage alongside entity type tabs
- D3 force simulation rendered in SVG within a dedicated container
- Data: extract relationships from cross-refs in gamedata context service

**Graph Design:**
- Nodes: circles with entity-color fill, 20-40px radius based on connection count
- Node labels: entity name (Korean) below node
- Node images: AI portraits as SVG `<image>` clipped to circle

**Link Types:**
| Relationship | Style | Color |
|-------------|-------|-------|
| owns (character→item) | solid 2px | cyan |
| knows (character→knowledge) | dashed 2px | green |
| member_of (character→faction) | solid 1px | purple |
| located_in (character→region) | dotted 1px | teal |
| enemy_of (character→character) | solid 2px | red |

**Interactions:**
- Hover node → connected nodes full opacity, unconnected dim to 0.2 (200ms transition)
- Hover link → show relationship type label
- Click node → navigate to entity detail (existing CodexEntityDetail)
- Drag nodes to rearrange (d3-drag)
- Zoom + pan (d3-zoom, shared pattern with MapCanvas)

**Force Parameters:**
```javascript
forceSimulation(nodes)
  .force("link", forceLink(links).distance(120).strength(0.5))
  .force("charge", forceManyBody().strength(-300))
  .force("center", forceCenter(width/2, height/2))
  .force("collision", forceCollide(40))
```

**Backend:**
- New endpoint: `GET /api/ldm/codex/relationships`
- Extracts cross-refs from all entities, builds edge list
- Returns: `{ nodes: [...], links: [...] }`

**Files Modified:**
- `locaNext/src/lib/components/pages/CodexPage.svelte` — add Relationships tab
- New: `locaNext/src/lib/components/ldm/CodexRelationshipGraph.svelte` — D3 force graph
- `server/tools/ldm/routes/codex.py` — new relationships endpoint
- `server/tools/ldm/services/codex_service.py` — relationship extraction

## Phase 40: Cross-cutting WOW Polish

### 40-01: Page Transitions + Shimmer Loading

**Page Transitions:**
- CSS View Transitions API: `document.startViewTransition()` on navigation
- Crossfade: old page fades out (150ms), new page fades in (150ms)
- Fallback for browsers without View Transitions: simple opacity crossfade

**Shimmer Loading:**
- Replace ALL remaining spinners with shimmer skeletons
- Each page has shimmer matching its content layout:
  - GameData Tree: shimmer tree lines (8 rows)
  - Codex: shimmer cards (grid of 6)
  - World Map: shimmer rectangle with faded regions
  - Language Data Grid: shimmer table rows (10 rows)
  - TM Panel: shimmer match cards (3 items)

**Loading Choreography:**
- Skeleton appears immediately (0ms)
- Content fades in with stagger when data arrives
- No layout shift (skeleton dimensions match content)

**Files Modified:**
- `locaNext/src/lib/components/common/PageTransition.svelte` — new transition wrapper
- `locaNext/src/routes/+layout.svelte` — integrate page transitions
- Various page components — replace remaining spinners with shimmer

### 40-02: Ctrl+K Command Palette + Toast System

**Command Palette:**
- Global Ctrl+K listener (document keydown)
- Glassmorphism modal: backdrop-filter blur(20px), semi-transparent dark bg
- Search input at top, results below (max 8 visible, scrollable)
- Results: entity name + type badge + source page
- Arrow up/down to navigate, Enter to select, Escape to close
- Debounced search (150ms) hitting existing dictionary-lookup endpoint

**Toast System:**
- Fixed position top-right, stacked vertically (8px gap)
- Slide-in from right (200ms ease-out)
- Auto-dismiss after 3000ms with progress bar
- Types: success (green), error (red), info (warm copper)
- Warm accent left border (4px)
- Close button (X) for manual dismiss

**Files Modified:**
- New: `locaNext/src/lib/components/common/CommandPalette.svelte`
- New: `locaNext/src/lib/components/common/ToastContainer.svelte`
- New: `locaNext/src/lib/components/common/Toast.svelte`
- `locaNext/src/routes/+layout.svelte` — mount CommandPalette and ToastContainer

## Technical Constraints

1. **Svelte 5 Runes ONLY** — $state, $derived, $effect. No Svelte 4 patterns.
2. **CSS transitions over animations** — prevent replay stutter on re-render
3. **No {#key} for reactive updates** — only for truly fresh DOM needs
4. **SvelteSet/SvelteMap** for reactive collections
5. **GPU-only transforms** — transform + opacity, never animate layout properties
6. **ease-out-quart** — `cubic-bezier(0.25, 1, 0.5, 1)` for all motion
7. **prefers-reduced-motion** — respect user preference, disable animations
8. **Optimistic UI** — instant visual feedback, server sync in background
9. **Carbon Components** — use where appropriate, extend with custom components
10. **No external image files for backgrounds** — CSS gradients + inline SVG only

## Success Criteria (Composite Score)

Score 5 dimensions (0-10 each), target composite >= 9.5:
1. **Visual beauty** — screenshot comparison, no AI slop, distinctive
2. **Data interconnection** — click cross-refs, navigate between entities seamlessly
3. **Map immersion** — parchment feels real, regions glow, routes animate
4. **Codex wow** — glassmorphism cards + relationship graph impresses
5. **Micro-interactions** — transitions smooth, command palette responsive, toasts elegant

## Execution Strategy

- **Phase 38 + 39:** Partially parallelizable (independent components)
- **Phase 40:** Depends on 38+39 (cross-cutting requires all pages ready)
- **Agent Teams:** 1 teammate per plan (3 for Phase 38, 2 for Phase 39)
- **Ruflo Queen:** Validates commits for drift from this spec
- **Autoresearch Loop:** After execution, score and iterate until 9.5+
- **Review Chain:** code-reviewer + code-simplifier + critique skill after each phase
