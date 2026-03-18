# LocaNext v3.5 WOW Showcase — Complete Design Spec

**Date:** 2026-03-17
**Status:** Design Phase
**Predecessor:** v3.4 GameData Showcase (9.5/10 shipped)
**Goal:** Transform every LocaNext surface into a demo-worthy showcase that makes viewers say "WOW" within the first 60 seconds.

---

## Table of Contents

1. [Area 1: XML Viewer WOW Polish](#area-1-xml-viewer-wow-polish)
2. [Area 2: Interactive World Map](#area-2-interactive-world-map)
3. [Area 3: Codex Enhancement](#area-3-codex-enhancement)
4. [Area 4: Cross-Cutting WOW Effects](#area-4-cross-cutting-wow-effects)
5. [Implementation Phases](#implementation-phases)
6. [Technical Constraints](#technical-constraints)
7. [Mock Data Requirements](#mock-data-requirements)
8. [Success Criteria](#success-criteria)

---

## Area 1: XML Viewer WOW Polish

### Current State (v3.4)

Files: `GameDataTree.svelte`, `GameDataContextPanel.svelte`

- Chrome DevTools-style XML viewer with One Dark Pro theme
- Line numbers, fold gutters, indent guides, collapsed node badges
- Cross-reference links (blue, clickable) and inline editable attributes
- Right panel with 4 tabs (Dictionary | Context | Media | Info)
- AttributeEditModal for double-click editing
- Search bar with cascade index
- Keyboard navigation (arrows, enter, space)

**What's lacking:** Whole-line highlighting is visually flat. No hover previews. No animation on transitions. No micro-feedback on user actions.

---

### 1.1 Smart Attribute Highlighting

**Problem:** Clicking a node highlights the entire line with a flat background color. Every attribute looks the same. Users cannot visually distinguish cross-refs from editable fields from identity keys.

**Solution:** Classify each attribute into a semantic category and apply distinct color styling per category. The attribute VALUE gets the color treatment, not the attribute name (which stays `#d19a66` per One Dark Pro).

#### Attribute Categories and Colors

| Category | Attributes (examples) | Value Color | Extra Effect |
|----------|----------------------|-------------|-------------|
| **Identity** | `Key`, `StrKey`, `Id`, `StringID` | `#e5c07b` (gold/amber) | Bold weight, `1px` bottom border |
| **Cross-Reference** | `KnowledgeKey`, `FactionKey`, `SkillKey`, `ItemKey`, `CharacterKey`, `RegionKey`, `LinkedQuestKey`, `RequireSkillKey`, `ParentNodeId`, `TargetKey` | `#61afef` (blue) | Underline, `cursor: pointer`, hover glow `0 0 6px rgba(97,175,239,0.4)` |
| **Editable** | `CharacterName`, `CharacterDesc`, `ItemName`, `ItemDesc`, `SkillName` | `#98c379` (green) | Dashed underline `1px`, subtle green glow `0 0 4px rgba(152,195,121,0.15)` on hover |
| **Stat/Numeric** | `Level`, `HP`, `CooldownSec`, `Damage`, `Defense`, `Weight`, `Price` | `#56b6c2` (cyan) | Monospace font, tabular-nums |
| **Media** | `UITextureName`, `VoicePath`, `IconPath`, `TexturePath` | `#c678dd` (purple) | Italic, hover shows media type icon inline |
| **Default** | Everything else | `#e06c75` (One Dark Pro string red) | No extra effect |

#### Implementation Details

**Classification function** in `GameDataTree.svelte`:

```javascript
const ATTR_CATEGORIES = {
  identity: new Set(['Key', 'StrKey', 'Id', 'StringID', 'NodeId']),
  crossref: new Set([
    'KnowledgeKey', 'FactionKey', 'SkillKey', 'ItemKey', 'CharacterKey',
    'RegionKey', 'LinkedQuestKey', 'RequireSkillKey', 'ParentNodeId',
    'ParentId', 'TargetKey', 'LearnKnowledgeKey'
  ]),
  editable: new Set([
    'CharacterName', 'CharacterDesc', 'ItemName', 'ItemDesc',
    'SkillName', 'SkillDesc', 'QuestName', 'QuestDesc',
    'RegionName', 'AliasName', 'Desc', 'Name'
  ]),
  stat: new Set([
    'Level', 'HP', 'MP', 'CooldownSec', 'Damage', 'Defense',
    'Weight', 'Price', 'DropRate', 'SpawnRate', 'Radius',
    'MinLevel', 'MaxLevel', 'RequireLevel', 'SkillLevel'
  ]),
  media: new Set([
    'UITextureName', 'VoicePath', 'IconPath', 'TexturePath',
    'SoundPath', 'AnimationPath', 'ModelPath'
  ])
};

function classifyAttr(attrName) {
  for (const [category, names] of Object.entries(ATTR_CATEGORIES)) {
    if (names.has(attrName)) return category;
  }
  // Heuristic fallback: ends with 'Key' or 'Id' → cross-ref
  if (attrName.endsWith('Key') || attrName.endsWith('Id')) return 'crossref';
  return 'default';
}
```

**CSS classes** (One Dark Pro integrated):

```css
.attr-val-identity   { color: #e5c07b; font-weight: 600; border-bottom: 1px solid #e5c07b40; }
.attr-val-crossref   { color: #61afef; text-decoration: underline; cursor: pointer;
                       transition: text-shadow 0.15s ease; }
.attr-val-crossref:hover { text-shadow: 0 0 6px rgba(97,175,239,0.4); }
.attr-val-editable   { color: #98c379; border-bottom: 1px dashed #98c37960;
                       transition: text-shadow 0.15s ease; }
.attr-val-editable:hover { text-shadow: 0 0 4px rgba(152,195,121,0.15); cursor: text; }
.attr-val-stat       { color: #56b6c2; font-family: 'JetBrains Mono', monospace;
                       font-variant-numeric: tabular-nums; }
.attr-val-media      { color: #c678dd; font-style: italic; }
.attr-val-default    { color: #e06c75; }
```

**Merge strategy:** The existing `renderAttrValue()` function in `GameDataTree.svelte` currently returns a `<span>` for cross-refs and a `<span>` for editables. Extend it to call `classifyAttr()` and apply the appropriate CSS class to ALL attribute values.

---

### 1.2 Hover Preview Tooltips

**Problem:** Cross-reference attribute values (e.g., `KnowledgeKey="Knowledge_SealedLibrary"`) are clickable but the user has no idea what they link to without clicking. Clicking navigates away, breaking flow.

**Solution:** On hover over any cross-ref attribute value, show a floating preview card with entity summary data.

#### Preview Card Design

```
┌────────────────────────────────┐
│ ┌────┐  Knowledge_SealedLib... │
│ │ img│  KnowledgeInfo          │  ← entity type tag
│ │    │  봉인된 도서관의 비밀      │  ← localized name (from dict)
│ └────┘  3 cross-refs           │
│         5 children             │
└────────────────────────────────┘
```

**Dimensions:** 280px wide, auto-height (max 120px). 48x48 thumbnail on left. Dark background (`#1e1e2e`) with `1px` border matching entity type color.

#### Data Fetching

Use the existing `/api/ldm/gamedata/context` endpoint. Cache responses in an LRU map (max 100 entries) keyed by `{file_path}:{node_id}`.

```javascript
let previewCache = $state(new Map());
let hoveredRef = $state(null);
let hoverTimer = null;
let tooltipPos = $state({ x: 0, y: 0 });

function onRefMouseEnter(event, attrValue, filePath) {
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(async () => {
    const cacheKey = `${filePath}:${attrValue}`;
    if (!previewCache.has(cacheKey)) {
      const resp = await fetch(`${API_BASE}/api/ldm/gamedata/search?q=${attrValue}`, {
        headers: getAuthHeaders()
      });
      const data = await resp.json();
      if (data.results?.length > 0) {
        previewCache.set(cacheKey, data.results[0]);
        // LRU eviction
        if (previewCache.size > 100) {
          const firstKey = previewCache.keys().next().value;
          previewCache.delete(firstKey);
        }
      }
    }
    hoveredRef = previewCache.get(cacheKey) ?? null;
    tooltipPos = { x: event.clientX + 12, y: event.clientY - 8 };
  }, 300); // 300ms delay to avoid flash on quick mouse-through
}

function onRefMouseLeave() {
  clearTimeout(hoverTimer);
  hoveredRef = null;
}
```

#### Tooltip Component

Render as a `<div>` with `position: fixed` using `tooltipPos`. Use `{#if hoveredRef}` conditional. Include:
- Thumbnail from `/api/ldm/gamedata/media/thumbnail/{entity_key}` (48x48, fallback to type icon)
- Entity key (truncated at 24 chars with ellipsis)
- Entity type as Carbon `<Tag>` with entity color from `ENTITY_TYPE_COLORS`
- Localized name from dictionary lookup (if available)
- Child count and cross-ref count badges

**Animation:** Fade in with `opacity 0→1` over 150ms, `transform: translateY(4px) → 0`.

**Edge detection:** If tooltip would overflow viewport right/bottom, flip to left/above the cursor.

---

### 1.3 Smooth Animations

All animations use CSS transitions and Svelte `transition:` directives. No external animation libraries. Performance budget: every animation must run at 60fps.

#### Panel Entrance Animation

When a node is selected and the context panel appears (or content changes):

```css
/* Panel slide-in from right */
.context-panel-content {
  animation: panelSlideIn 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes panelSlideIn {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}
```

#### Tab Content Crossfade

When switching tabs in `GameDataContextPanel.svelte`:

```svelte
{#key activeTab}
  <div class="tab-content" in:fade={{ duration: 150 }}>
    <!-- tab content -->
  </div>
{/key}
```

Use Svelte's built-in `fade` transition. The `{#key}` block ensures the old content is destroyed and new content fades in.

#### Image Loading: Shimmer to Reveal

Replace the current image loading with a shimmer skeleton that crossfades to the actual image:

```css
.image-shimmer {
  background: linear-gradient(90deg, #2d2d3d 25%, #3d3d4d 50%, #2d2d3d 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.image-reveal {
  animation: imageReveal 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes imageReveal {
  from { opacity: 0; filter: blur(8px); }
  to   { opacity: 1; filter: blur(0); }
}
```

State machine: `loading → shimmer visible` → `onload → shimmer hidden, image with reveal animation`.

#### Dictionary Results Staggered Fade-In

When dictionary results load, each result card appears with a staggered delay:

```css
.dict-result {
  animation: staggerFadeIn 0.2s cubic-bezier(0.4, 0, 0.2, 1) both;
}
.dict-result:nth-child(1) { animation-delay: 0ms; }
.dict-result:nth-child(2) { animation-delay: 50ms; }
.dict-result:nth-child(3) { animation-delay: 100ms; }
.dict-result:nth-child(4) { animation-delay: 150ms; }
.dict-result:nth-child(5) { animation-delay: 200ms; }

@keyframes staggerFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Limit to first 5 children. Beyond 5, all appear at 250ms delay (no infinite stagger).

---

### 1.4 Micro-interactions

#### Copy-on-Click with Ripple

Clicking any non-crossref, non-editable attribute value copies it to clipboard and shows a ripple:

```javascript
async function copyAttrValue(event, value) {
  await navigator.clipboard.writeText(value);
  // Create ripple element at click position
  const ripple = document.createElement('span');
  ripple.className = 'copy-ripple';
  ripple.style.left = `${event.offsetX}px`;
  ripple.style.top = `${event.offsetY}px`;
  event.target.appendChild(ripple);
  // Show "Copied!" toast (see Area 4)
  showToast('Copied to clipboard', 'success');
  setTimeout(() => ripple.remove(), 400);
}
```

```css
.copy-ripple {
  position: absolute;
  width: 20px; height: 20px;
  border-radius: 50%;
  background: rgba(152, 195, 121, 0.3);
  animation: rippleExpand 0.4s ease-out;
  pointer-events: none;
}
@keyframes rippleExpand {
  from { transform: scale(0); opacity: 1; }
  to   { transform: scale(4); opacity: 0; }
}
```

#### Node Expand/Collapse Accordion

Currently, expanding/collapsing a node instantly shows/hides children. Add smooth height animation:

- Use `max-height` transition on the children container
- Fold arrow rotates 0deg → 90deg with `transition: transform 0.15s ease`
- Already partially implemented (ChevronRight rotation). Extend with height animation.

```css
.node-children {
  overflow: hidden;
  transition: max-height 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.15s ease;
}
.node-children.collapsed {
  max-height: 0;
  opacity: 0;
}
.node-children.expanded {
  max-height: 5000px; /* Large enough for any subtree */
  opacity: 1;
}
```

Note: `max-height` transition with a large value has a known quirk where collapse is fast but expand appears to have a delay. Mitigate by using `requestAnimationFrame` to measure actual height and set `max-height` to the measured value.

#### Search Result Highlight Pulse

When search results are shown and the user clicks one to navigate, the target line gets a brief pulse:

```css
.search-highlight-pulse {
  animation: highlightPulse 1s ease-out;
}
@keyframes highlightPulse {
  0%   { background-color: rgba(97, 175, 239, 0.3); }
  50%  { background-color: rgba(97, 175, 239, 0.1); }
  100% { background-color: transparent; }
}
```

---

## Area 2: Interactive World Map

### Current State (v3.4)

Files: `MapCanvas.svelte`, `MapTooltip.svelte`, `MapDetailPanel.svelte`

- SVG canvas with `d3-zoom` for pan/zoom
- Colored circles for region nodes, sized by type
- Dashed polyline routes between connected nodes
- `onNodeHover` → tooltip, `onNodeClick` → detail panel
- Coordinate mapping: world space → SVG space with bounds normalization

**What's lacking:** Looks like a technical debug view, not a game world map. No visual storytelling. No terrain, no aesthetic, no fantasy feel.

---

### 2.1 Fantasy Map Aesthetic

**Design philosophy:** The map should look like a hand-drawn cartographic document from a fantasy RPG — aged parchment, ornamental borders, stylized typography. All achieved with CSS and SVG (no external image assets per constraints).

#### Parchment Background

Apply to the SVG container element:

```css
.map-container {
  background:
    /* Noise texture via radial gradients */
    radial-gradient(ellipse at 20% 50%, rgba(139,90,43,0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(139,90,43,0.06) 0%, transparent 40%),
    radial-gradient(ellipse at 50% 80%, rgba(101,67,33,0.05) 0%, transparent 45%),
    /* Base parchment gradient */
    linear-gradient(135deg,
      #2a2318 0%,    /* Dark brown edge */
      #3d3426 15%,   /* Warm dark */
      #4a3c2a 40%,   /* Parchment dark */
      #3d3426 60%,   /* Return */
      #2a2318 100%   /* Dark brown edge */
    );
  border: 2px solid #5a4a32;
  border-radius: 4px;
  box-shadow: inset 0 0 60px rgba(0,0,0,0.3);
}
```

This creates a dark-mode parchment effect that fits the One Dark Pro theme while feeling like aged paper.

#### Ornamental Border Frame

SVG `<defs>` pattern for decorative border inside the map:

```svg
<defs>
  <pattern id="borderPattern" width="20" height="20" patternUnits="userSpaceOnUse">
    <path d="M0,10 Q5,0 10,10 Q15,20 20,10" fill="none" stroke="#5a4a32" stroke-width="0.5" opacity="0.6"/>
  </pattern>
  <filter id="roughEdge">
    <feTurbulence type="turbulence" baseFrequency="0.05" numOctaves="3" result="noise"/>
    <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
</defs>

<!-- Decorative border rectangle -->
<rect x="20" y="20" width="960" height="960" fill="none"
      stroke="url(#borderPattern)" stroke-width="8" rx="4"
      filter="url(#roughEdge)" opacity="0.5"/>
```

#### Compass Rose

An SVG group positioned in the bottom-right corner (`x=880, y=880`), rendered as a simplified compass:

```svg
<g class="compass-rose" transform="translate(900, 900) scale(0.6)">
  <!-- Outer ring -->
  <circle r="40" fill="none" stroke="#8b7355" stroke-width="1.5" opacity="0.6"/>
  <!-- Cardinal points -->
  <polygon points="0,-35 -4,-8 4,-8" fill="#8b7355" opacity="0.8"/> <!-- N -->
  <polygon points="0,35 -4,8 4,8" fill="#6b5540" opacity="0.5"/>   <!-- S -->
  <polygon points="35,0 8,-4 8,4" fill="#6b5540" opacity="0.5"/>   <!-- E -->
  <polygon points="-35,0 -8,-4 -8,4" fill="#6b5540" opacity="0.5"/> <!-- W -->
  <!-- N label -->
  <text y="-42" text-anchor="middle" fill="#8b7355"
        font-family="serif" font-size="12" opacity="0.7">N</text>
</g>
```

#### Title Cartouche

Decorative title banner at top center:

```svg
<g class="title-cartouche" transform="translate(500, 35)">
  <!-- Scroll shape -->
  <path d="M-120,-15 Q-130,-15 -130,0 Q-130,15 -120,15 L120,15 Q130,15 130,0 Q130,-15 120,-15 Z"
        fill="#2a231880" stroke="#5a4a32" stroke-width="1"/>
  <!-- Scroll curls -->
  <circle cx="-130" cy="0" r="6" fill="none" stroke="#5a4a32" stroke-width="1" opacity="0.5"/>
  <circle cx="130" cy="0" r="6" fill="none" stroke="#5a4a32" stroke-width="1" opacity="0.5"/>
  <text text-anchor="middle" y="5" fill="#c8b88a"
        font-family="'Cinzel', 'Palatino', serif" font-size="14" letter-spacing="3">
    WORLD MAP
  </text>
</g>
```

---

### 2.2 Region Visualization

#### Voronoi/Polygon Regions

Replace plain circles with semi-transparent polygon regions. Each region is defined by a `boundary` array of `[x, y]` points.

**Rendering approach:**

```svg
{#each regions as region}
  <polygon
    points={region.boundary.map(([x,y]) => `${worldToSvg(x,y).join(',')}`).join(' ')}
    fill={region.color}
    fill-opacity="0.12"
    stroke={region.color}
    stroke-width="1.5"
    stroke-opacity="0.4"
    filter="url(#roughEdge)"
    class="region-polygon"
    class:hovered={hoveredRegion === region.id}
  />
{/each}
```

```css
.region-polygon {
  transition: fill-opacity 0.3s ease, stroke-opacity 0.3s ease;
  cursor: pointer;
}
.region-polygon.hovered {
  fill-opacity: 0.25;
  stroke-opacity: 0.8;
  filter: url(#roughEdge) drop-shadow(0 0 8px var(--region-color));
}
```

**Glow effect on hover:** Use CSS `filter: drop-shadow()` with the region's color. Set `--region-color` as a CSS custom property per region element.

#### Region Names

Render region names at the centroid of each boundary polygon, using fantasy-style typography:

```css
.region-label {
  font-family: 'Cinzel', 'Palatino Linotype', 'Garamond', serif;
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  fill: #c8b88a;
  opacity: 0.7;
  text-anchor: middle;
  pointer-events: none;
  text-shadow: 0 0 4px rgba(0,0,0,0.8);
  transition: opacity 0.2s ease;
}
```

For Korean names (e.g., "봉인된 도서관"), use `font-family: 'Noto Serif KR', serif` and drop the `text-transform: uppercase`.

#### Terrain Indicators

Small SVG icon groups placed inside or near regions to suggest terrain type:

| Terrain | Icon | SVG |
|---------|------|-----|
| Mountains/Highland | Triangle peaks | `<path d="M0,0 L-5,10 L5,10 Z"/>` repeated 2-3x offset |
| Forest | Tree shapes | `<circle r="3"/>` on top of `<rect width="2" height="5"/>` |
| Water/Coast | Wave lines | `<path d="M0,0 Q5,-3 10,0 Q15,3 20,0"/>` |
| Desert/Plains | Dot scatter | 5-7 small `<circle r="1"/>` scattered |
| Ruins/Dungeon | Broken column | `<rect>` with jagged top edge |

Render at 30-40% opacity, colored `#5a4a3280`. These are atmospheric, not data-carrying.

---

### 2.3 Node Visualization

#### Custom SVG Icons by Type

Replace uniform circles with type-specific SVG icon groups:

| Node Type | Icon Design | Size | Color |
|-----------|-------------|------|-------|
| Town | Castle turrets (3 rectangles with triangles) | 16x16 | `#24a148` (green) |
| Dungeon | Skull shape (circle + jaw) | 14x14 | `#da1e28` (red) |
| Camp | Tent shape (triangle) | 12x12 | `#f1c21b` (yellow) |
| Fortress | Shield shape (pointed bottom rect) | 16x16 | `#8a3ffc` (purple) |
| Wilderness | Tree silhouette | 12x12 | `#007d79` (teal) |
| Main | Star/diamond shape | 18x18 | `#0f62fe` (blue) |

Each icon is an SVG `<g>` element rendered at the node's mapped position.

#### Animated Pulse for Quest Nodes

Nodes with associated quests get a pulsing ring:

```svg
<circle cx={x} cy={y} r={radius + 4}
        fill="none" stroke={color} stroke-width="1.5"
        opacity="0.6" class="quest-pulse"/>
```

```css
.quest-pulse {
  animation: questPulse 2s ease-in-out infinite;
}
@keyframes questPulse {
  0%, 100% { r: calc(var(--base-r) + 4); opacity: 0.6; }
  50%      { r: calc(var(--base-r) + 10); opacity: 0; }
}
```

Note: SVG `r` cannot be animated with CSS in all browsers. Use SMIL `<animate>` as fallback:

```svg
<animate attributeName="r" values="14;20;14" dur="2s" repeatCount="indefinite"/>
<animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite"/>
```

#### Size Scaled by Importance

Node icon scale factor based on entity count:

```javascript
function nodeScale(region) {
  const entityCount = Object.values(region.entities || {}).reduce((a, b) => a + b, 0);
  if (entityCount >= 10) return 1.4;
  if (entityCount >= 5)  return 1.2;
  return 1.0;
}
```

---

### 2.4 Map Interaction

#### Smooth Pan/Zoom with Momentum

The existing `d3-zoom` already handles this. Enhance with:

```javascript
const zoomBehavior = zoom()
  .scaleExtent([0.5, 8])
  .on('zoom', (event) => {
    transform = event.transform;
  });
```

Add smooth transition when programmatically zooming (e.g., click-to-zoom):

```javascript
function zoomToRegion(region) {
  const [cx, cy] = worldToSvg(region.x, region.z);
  const targetScale = 3;
  const svg = select(svgElement);
  svg.transition()
    .duration(750)
    .call(
      zoomBehavior.transform,
      zoomIdentity
        .translate(SVG_SIZE / 2, SVG_SIZE / 2)
        .scale(targetScale)
        .translate(-cx, -cy)
    );
}
```

#### Click Region to Zoom + Detail Panel

Clicking a region polygon or node:
1. Smooth zoom to fit the region boundary (750ms transition)
2. Open `MapDetailPanel` with region info
3. Highlight connected routes

```javascript
function onRegionClick(region) {
  zoomToRegion(region);
  selectedRegion = region;
  // Highlight connected routes
  highlightedRoutes = new Set(
    routes.filter(r => r.from === region.id || r.to === region.id).map(r => r.id)
  );
}
```

#### Route Animation on Hover

Connection routes animate with a traveling dash effect on hover:

```css
.route-path {
  stroke-dasharray: 8 4;
  stroke-dashoffset: 0;
  transition: stroke-width 0.2s ease, stroke-opacity 0.2s ease;
}
.route-path.hovered {
  stroke-width: 3;
  stroke-opacity: 0.9;
  animation: routeTravel 1s linear infinite;
}
@keyframes routeTravel {
  to { stroke-dashoffset: -24; }
}
```

**Danger level styling:**

| Danger | Stroke Color | Dash Pattern |
|--------|-------------|-------------|
| `low` | `#24a148` (green) | `12 4` |
| `medium` | `#f1c21b` (yellow) | `8 4` |
| `high` | `#da1e28` (red) | `4 4` |

#### Mini-Map

An inset overview map in the top-left corner showing the full map with a viewport rectangle:

```svelte
<svg class="mini-map" width="120" height="120" viewBox="0 0 1000 1000">
  <!-- All nodes as tiny dots -->
  {#each nodes as node}
    <circle cx={worldToSvg(node.x, node.z)[0]}
            cy={worldToSvg(node.x, node.z)[1]}
            r="3" fill={NODE_COLORS[node.type] ?? '#666'}/>
  {/each}
  <!-- Viewport rectangle -->
  <rect x={viewportRect.x} y={viewportRect.y}
        width={viewportRect.w} height={viewportRect.h}
        fill="none" stroke="#61afef" stroke-width="2" opacity="0.8"/>
</svg>
```

```css
.mini-map {
  position: absolute;
  top: 12px; left: 12px;
  background: #1e1e2e80;
  border: 1px solid #3d3d4d;
  border-radius: 4px;
  backdrop-filter: blur(4px);
  pointer-events: none; /* Or make it interactive for click-to-pan */
}
```

Compute `viewportRect` from the inverse of the current d3-zoom transform:

```javascript
let viewportRect = $derived(() => {
  const k = transform.k;
  const x = -transform.x / k;
  const y = -transform.y / k;
  const w = SVG_SIZE / k;
  const h = SVG_SIZE / k;
  return { x, y, w, h };
});
```

---

### 2.5 Mock Data Structure

Extend the existing map data endpoint or create `/api/ldm/mapdata/enhanced` to serve enriched region data:

```json
{
  "regions": [
    {
      "id": "Region_SealedLibrary",
      "name": "봉인된 도서관",
      "name_en": "Sealed Library",
      "type": "Dungeon",
      "terrain": "ruins",
      "x": 450, "z": 300,
      "boundary": [[400,250],[500,250],[520,350],[380,350]],
      "color": "#8b5cf6",
      "entities": {
        "characters": 3,
        "items": 5,
        "quests": 2,
        "knowledge": 4
      },
      "connections": ["Region_DarkForest", "Region_SageTemple"],
      "has_quests": true,
      "importance": "major"
    },
    {
      "id": "Region_DarkForest",
      "name": "어둠의 숲",
      "name_en": "Dark Forest",
      "type": "Wilderness",
      "terrain": "forest",
      "x": 250, "z": 400,
      "boundary": [[180,350],[320,340],[340,460],[200,470]],
      "color": "#007d79",
      "entities": {
        "characters": 2,
        "items": 3,
        "quests": 1,
        "knowledge": 2
      },
      "connections": ["Region_SealedLibrary", "Region_BlackstarVillage"],
      "has_quests": true,
      "importance": "minor"
    },
    {
      "id": "Region_BlackstarVillage",
      "name": "흑성 마을",
      "name_en": "Blackstar Village",
      "type": "Town",
      "terrain": "plains",
      "x": 600, "z": 500,
      "boundary": [[550,450],[670,440],[680,560],[540,570]],
      "color": "#24a148",
      "entities": {
        "characters": 5,
        "items": 8,
        "quests": 3,
        "knowledge": 3
      },
      "connections": ["Region_DarkForest", "Region_ForgeFortress", "Region_SageTemple"],
      "has_quests": true,
      "importance": "major"
    },
    {
      "id": "Region_ForgeFortress",
      "name": "대장간 요새",
      "name_en": "Forge Fortress",
      "type": "Fortress",
      "terrain": "mountain",
      "x": 780, "z": 350,
      "boundary": [[730,290],[840,300],[850,410],[720,400]],
      "color": "#8a3ffc",
      "entities": {
        "characters": 2,
        "items": 6,
        "quests": 1,
        "knowledge": 1
      },
      "connections": ["Region_BlackstarVillage"],
      "has_quests": false,
      "importance": "minor"
    },
    {
      "id": "Region_SageTemple",
      "name": "현자의 신전",
      "name_en": "Sage Temple",
      "type": "Main",
      "terrain": "plains",
      "x": 500, "z": 650,
      "boundary": [[430,590],[570,580],[590,710],[420,720]],
      "color": "#0f62fe",
      "entities": {
        "characters": 4,
        "items": 4,
        "quests": 4,
        "knowledge": 6
      },
      "connections": ["Region_SealedLibrary", "Region_BlackstarVillage"],
      "has_quests": true,
      "importance": "major"
    }
  ],
  "routes": [
    { "id": "route_1", "from": "Region_SealedLibrary", "to": "Region_DarkForest", "type": "path", "danger": "high" },
    { "id": "route_2", "from": "Region_DarkForest", "to": "Region_BlackstarVillage", "type": "road", "danger": "medium" },
    { "id": "route_3", "from": "Region_BlackstarVillage", "to": "Region_ForgeFortress", "type": "road", "danger": "low" },
    { "id": "route_4", "from": "Region_BlackstarVillage", "to": "Region_SageTemple", "type": "road", "danger": "low" },
    { "id": "route_5", "from": "Region_SealedLibrary", "to": "Region_SageTemple", "type": "path", "danger": "medium" }
  ]
}
```

---

## Area 3: Codex Enhancement

### Current State (v3.4)

Files: `CodexEntityDetail.svelte`, `CodexSearchBar.svelte`, `CodexPage.svelte`

- Entity detail card with image (AI-generated portrait), metadata, audio, similar items
- Semantic search via CodexSearchBar
- PlaceholderImage and PlaceholderAudio components
- AI image generation integration (Gemini nano-banana)

**What's lacking:** No grid overview of all entities. No visual relationship graph. Detail view is functional but not visually stunning.

---

### 3.1 Entity Cards Grid

A browseable grid of all indexed entities displayed as visually rich cards.

#### Card Design

```
┌──────────────────────┐
│                      │  ← AI portrait as background
│    [parallax image]  │     (parallax shift on hover)
│                      │
│  ┌──────────────────┐│  ← Glassmorphism overlay at bottom
│  │ 🏰 CharacterInfo ││  ← Type badge with icon
│  │ 엘더 바론         ││  ← Entity name
│  │ Elder Varon       ││  ← English name (smaller)
│  └──────────────────┘│
└──────────────────────┘
```

**Dimensions:** 220px x 280px per card. Responsive grid: `grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`.

#### Glassmorphism Effect

```css
.entity-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: #1e1e2e;
  border: 1px solid #3d3d4d;
}
.entity-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.entity-card-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px;
  background: rgba(30, 30, 46, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(255,255,255,0.08);
}
```

#### Parallax on Hover

Subtle image shift based on mouse position within the card:

```javascript
function onCardMouseMove(event, card) {
  const rect = card.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width - 0.5;  // -0.5 to 0.5
  const y = (event.clientY - rect.top) / rect.height - 0.5;
  card.style.setProperty('--parallax-x', `${x * -8}px`);
  card.style.setProperty('--parallax-y', `${y * -8}px`);
}
```

```css
.entity-card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: translate(var(--parallax-x, 0), var(--parallax-y, 0)) scale(1.05);
  transition: transform 0.1s ease-out;
}
```

The `scale(1.05)` ensures no gaps appear at edges during parallax shift.

#### Type Badge Icons

Map entity types to Carbon icons:

| Type | Icon | Badge Color |
|------|------|-------------|
| CharacterInfo | `UserAvatar` | `#8b5cf6` |
| ItemInfo | `ShoppingCatalog` | `#06b6d4` |
| SkillInfo | `Flash` | `#a855f7` |
| QuestInfo | `TaskComplete` | `#f97316` |
| RegionInfo | `Map` (as `MapIcon`) | `#14b8a6` |
| KnowledgeInfo | `Book` | `#10b981` |

#### Staggered Entrance Animation

When the grid loads or search results change:

```css
.entity-card {
  animation: cardEntrance 0.3s cubic-bezier(0.4, 0, 0.2, 1) both;
}

@keyframes cardEntrance {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

Apply stagger via inline `animation-delay` computed from card index:

```svelte
{#each entities as entity, i (entity.key)}
  <div class="entity-card" style="animation-delay: {Math.min(i * 40, 400)}ms">
    ...
  </div>
{/each}
```

Cap delay at 400ms (10 cards) so the grid doesn't take forever on large result sets.

#### Data Source

Use `/api/ldm/codex/entities` (existing endpoint) to fetch all indexed entities. Display as card grid by default, switch to detail view on card click.

---

### 3.2 Relationship Graph

A D3 force-directed graph showing connections between entities.

#### Graph Layout

```
     [CharacterInfo: 키라] ──uses──→ [ItemInfo: 흑성검]
            │                              │
         belongs_to                   found_in
            │                              │
            v                              v
     [FactionInfo: 현자회]        [RegionInfo: 흑성 마을]
            │
        knows
            │
            v
     [SkillInfo: 신성한 보호]
```

#### Nodes

Each entity is a circle node sized by connection count:

```javascript
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d => d.id).distance(120))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(d => d.radius + 8));
```

Node rendering:

```svg
<circle r={node.radius} fill={ENTITY_TYPE_COLORS[node.type]}
        opacity={highlightedNode ? (isConnected(node) ? 1 : 0.2) : 0.8}
        stroke={highlightedNode === node.id ? '#fff' : 'none'}
        stroke-width="2"/>
<text dy="4" text-anchor="middle" fill="#c8ccd0" font-size="10">
  {truncate(node.name, 12)}
</text>
```

#### Links

Connections typed by relationship:

| Relationship | Stroke Style | Color |
|-------------|-------------|-------|
| `uses` (char→item) | Solid | `#06b6d4` |
| `knows` (char→skill) | Dashed `4 2` | `#a855f7` |
| `belongs_to` (char→faction) | Dotted `2 2` | `#ec4899` |
| `found_in` (item→region) | Solid | `#14b8a6` |
| `triggers` (quest→quest) | Dashed `6 3` | `#f97316` |

#### Hover Highlight

When hovering a node:
1. Connected nodes and links go to full opacity
2. Unconnected nodes and links fade to `opacity: 0.15`
3. Hovered node gets a white stroke ring
4. Transition: `opacity 0.2s ease`

```javascript
function onNodeHover(nodeId) {
  highlightedNode = nodeId;
  connectedIds = new Set();
  links.forEach(l => {
    if (l.source.id === nodeId) connectedIds.add(l.target.id);
    if (l.target.id === nodeId) connectedIds.add(l.source.id);
  });
  connectedIds.add(nodeId);
}
```

#### Click Navigation

Clicking a node in the graph navigates to the Codex entity detail view for that entity:

```javascript
function onNodeClick(nodeId) {
  const entity = entityMap.get(nodeId);
  if (entity) navigateToEntity(entity);
}
```

#### Data Source

Build the graph from cross-reference data. Use existing `/api/ldm/gamedata/context` responses to extract relationships. Cache the full relationship graph on first load.

Backend endpoint (new): `GET /api/ldm/codex/relationships`

Response:
```json
{
  "nodes": [
    { "id": "Character_Kira", "name": "키라", "type": "CharacterInfo", "connections": 4 }
  ],
  "links": [
    { "source": "Character_Kira", "target": "Item_BlackstarSword", "relationship": "uses" }
  ]
}
```

The service extracts relationships by scanning cross-reference attributes across all indexed entities.

---

## Area 4: Cross-Cutting WOW Effects

### 4.1 Loading States: Shimmer Skeletons

Replace all spinners (`InlineLoading`) with shimmer skeleton placeholders that match the shape of the content they're replacing.

#### Skeleton Components

**Text skeleton:**
```css
.skeleton-text {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, #2d2d3d 25%, #3d3d4d 50%, #2d2d3d 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-text.short { width: 40%; }
.skeleton-text.medium { width: 70%; }
.skeleton-text.full { width: 100%; }
```

**Image skeleton:**
```css
.skeleton-image {
  border-radius: 8px;
  background: linear-gradient(90deg, #2d2d3d 25%, #3d3d4d 50%, #2d2d3d 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  aspect-ratio: 1;
}
```

**Card skeleton (for entity cards):**
```svelte
<div class="skeleton-card">
  <div class="skeleton-image" style="height: 180px;"></div>
  <div style="padding: 12px;">
    <div class="skeleton-text short" style="margin-bottom: 8px;"></div>
    <div class="skeleton-text medium"></div>
  </div>
</div>
```

**Usage pattern:** Every `{#if loading}` block currently showing `<InlineLoading>` should instead show the appropriately shaped skeleton.

#### Where to Apply

| Component | Current Loading | New Skeleton Shape |
|-----------|----------------|-------------------|
| GameDataTree | SkeletonText (already OK) | Keep as-is |
| GameDataContextPanel dict tab | InlineLoading spinner | 3x text-line skeletons |
| GameDataContextPanel context tab | InlineLoading spinner | 4x text-line skeletons |
| GameDataContextPanel media tab | InlineLoading spinner | 1x image skeleton + 2x text skeletons |
| CodexEntityDetail | InlineLoading | Card skeleton (image + text) |
| CodexSearchBar results | InlineLoading | 5x small card skeletons |
| MapDetailPanel | InlineLoading | Text + mini-image skeleton |
| Entity cards grid | None (new) | 6x card skeletons in grid |

---

### 4.2 Page Transitions

When navigating between major views (Codex, Map, GameData, LDM), apply a crossfade:

Implement in the layout or page wrapper component:

```svelte
<script>
  import { fade } from 'svelte/transition';
</script>

{#key currentPage}
  <div in:fade={{ duration: 150, delay: 75 }} out:fade={{ duration: 75 }}>
    <slot/>
  </div>
{/key}
```

The `out` duration (75ms) plus `in` delay (75ms) creates a brief overlap-free crossfade.

---

### 4.3 Toast Notifications

A slide-in notification system for user feedback (copy confirmation, save success, errors).

#### Toast Store

```javascript
// lib/stores/toasts.js
import { writable } from 'svelte/store';

export const toasts = writable([]);
let toastId = 0;

export function showToast(message, type = 'info', duration = 3000) {
  const id = ++toastId;
  toasts.update(t => [...t, { id, message, type, duration }]);
  setTimeout(() => {
    toasts.update(t => t.filter(toast => toast.id !== id));
  }, duration);
}
```

#### Toast Component

```svelte
<!-- ToastContainer.svelte -->
<div class="toast-container">
  {#each $toasts as toast (toast.id)}
    <div class="toast toast-{toast.type}"
         in:fly={{ x: 300, duration: 200 }}
         out:fade={{ duration: 150 }}>
      {toast.message}
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }
  .toast {
    padding: 10px 16px;
    border-radius: 6px;
    font-size: 13px;
    color: #e8e8e8;
    pointer-events: auto;
    max-width: 320px;
    backdrop-filter: blur(8px);
  }
  .toast-success { background: rgba(36, 161, 72, 0.9); }
  .toast-error   { background: rgba(218, 30, 40, 0.9); }
  .toast-info    { background: rgba(15, 98, 254, 0.85); }
  .toast-warning { background: rgba(241, 194, 27, 0.85); color: #1e1e2e; }
</style>
```

Mount `<ToastContainer/>` in the root layout.

---

### 4.4 Keyboard Shortcuts

#### Global Search: Ctrl+K

```javascript
// In root layout or app shell
function onKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
    event.preventDefault();
    openGlobalSearch();
  }
}
```

`openGlobalSearch()` opens a command-palette-style modal:

```
┌─────────────────────────────────────┐
│ 🔍 Search entities, files, keys... │  ← Auto-focused input
├─────────────────────────────────────┤
│ Recent:                             │
│   Character_Kira (CharacterInfo)    │
│   Item_BlackstarSword (ItemInfo)    │
├─────────────────────────────────────┤
│ Results:                            │
│   ...                               │
└─────────────────────────────────────┘
```

**Styling:** Full-width modal (max 600px), centered vertically at 20% from top, dark glassmorphism background (`rgba(30,30,46,0.95)` + `backdrop-filter: blur(16px)`), dimmed overlay behind.

**Navigation:** Arrow keys to move through results, Enter to select, Escape to close.

**Search scope:** Queries `/api/ldm/gamedata/search` and `/api/ldm/codex/search` in parallel, merges results with source labels.

---

### 4.5 Dark Theme Consistency

Audit all components for One Dark Pro color consistency:

| Element | Color |
|---------|-------|
| Background (primary) | `#1e1e2e` |
| Background (elevated) | `#252536` |
| Background (surface) | `#2d2d3d` |
| Border | `#3d3d4d` |
| Text (primary) | `#e8e8e8` |
| Text (secondary) | `#8b8fa3` |
| Text (muted) | `#5c5f77` |
| Accent (blue) | `#61afef` / `#0f62fe` |
| Success (green) | `#98c379` / `#24a148` |
| Error (red) | `#e06c75` / `#da1e28` |
| Warning (yellow) | `#e5c07b` / `#f1c21b` |
| Purple | `#c678dd` / `#8b5cf6` |

Create a CSS custom properties file `theme.css` if one doesn't exist, and reference these variables throughout.

---

## Implementation Phases

### Phase 1: XML Viewer Polish (Effort: LOW-MEDIUM, WOW: HIGH)

| # | Task | Est. Hours | WOW Factor |
|---|------|-----------|------------|
| 1.1 | Smart attribute highlighting (classification + CSS) | 3 | HIGH |
| 1.2 | Hover preview tooltips (fetch + tooltip component) | 5 | VERY HIGH |
| 1.3 | Smooth animations (panel entrance, tab crossfade) | 2 | HIGH |
| 1.4 | Image shimmer → reveal animation | 1 | MEDIUM |
| 1.5 | Dictionary staggered fade-in | 1 | MEDIUM |
| 1.6 | Copy-on-click ripple effect | 1 | MEDIUM |
| | **Phase 1 Total** | **13** | |

**Deliverable:** XML viewer where every attribute is color-coded by type, cross-refs show previews on hover, and all transitions are smooth.

### Phase 2: Fantasy World Map (Effort: HIGH, WOW: EXTREME)

| # | Task | Est. Hours | WOW Factor |
|---|------|-----------|------------|
| 2.1 | Parchment background + border frame | 3 | HIGH |
| 2.2 | Compass rose + title cartouche | 2 | MEDIUM |
| 2.3 | Region polygons with hover glow | 4 | VERY HIGH |
| 2.4 | Fantasy region labels (serif font) | 1 | HIGH |
| 2.5 | Terrain indicator icons | 3 | HIGH |
| 2.6 | Custom node icons by type | 3 | VERY HIGH |
| 2.7 | Quest node pulse animation | 1 | HIGH |
| 2.8 | Click-to-zoom with smooth transition | 2 | VERY HIGH |
| 2.9 | Route danger styling + travel animation | 2 | HIGH |
| 2.10 | Mini-map with viewport rect | 3 | HIGH |
| 2.11 | Enhanced mock data (boundaries, terrain) | 2 | — |
| | **Phase 2 Total** | **26** | |

**Deliverable:** A map that looks like it belongs in a published RPG. Viewers should not believe it's a localization tool.

### Phase 3: Codex Enhancement (Effort: MEDIUM-HIGH, WOW: VERY HIGH)

| # | Task | Est. Hours | WOW Factor |
|---|------|-----------|------------|
| 3.1 | Entity cards grid layout | 3 | HIGH |
| 3.2 | Glassmorphism card styling | 2 | HIGH |
| 3.3 | Parallax image effect on hover | 2 | VERY HIGH |
| 3.4 | Staggered entrance animation | 1 | HIGH |
| 3.5 | Type badge icons | 1 | MEDIUM |
| 3.6 | Relationship graph (D3 force layout) | 6 | VERY HIGH |
| 3.7 | Graph hover highlight + click nav | 2 | HIGH |
| 3.8 | Backend: `/api/ldm/codex/relationships` | 3 | — |
| | **Phase 3 Total** | **20** | |

**Deliverable:** Codex that shows entity cards as a beautiful gallery, and a force-directed relationship graph that reveals the game world's interconnectedness.

### Phase 4: Cross-Cutting Polish (Effort: LOW, WOW: MEDIUM)

| # | Task | Est. Hours | WOW Factor |
|---|------|-----------|------------|
| 4.1 | Shimmer skeletons (replace all spinners) | 3 | MEDIUM |
| 4.2 | Page transition crossfade | 1 | MEDIUM |
| 4.3 | Toast notification system | 2 | MEDIUM |
| 4.4 | Ctrl+K global search palette | 4 | HIGH |
| 4.5 | Dark theme consistency audit | 2 | MEDIUM |
| | **Phase 4 Total** | **12** | |

**Deliverable:** Every loading state shimmers, every transition crossfades, every action gets feedback, and the whole app feels like one cohesive dark-themed product.

### Total Effort Summary

| Phase | Hours | WOW Factor | Priority |
|-------|-------|------------|----------|
| Phase 1: XML Viewer | 13 | HIGH | 1st (quick wins) |
| Phase 2: Fantasy Map | 26 | EXTREME | 2nd (showstopper) |
| Phase 3: Codex | 20 | VERY HIGH | 3rd (depth) |
| Phase 4: Polish | 12 | MEDIUM | 4th (cohesion) |
| **Total** | **71** | | |

---

## Technical Constraints

| Constraint | Rule |
|-----------|------|
| **Framework** | Svelte 5 with Runes ONLY (`$state`, `$derived`, `$effect`). No Svelte 4 syntax. |
| **UI Library** | Carbon Components for base elements (Button, Tag, Modal, etc.) |
| **State Management** | Optimistic UI mandatory — UI updates instantly, server syncs in background |
| **Styling** | CSS-only animations (no GSAP/anime.js). SVG filters for visual effects. No external image assets. |
| **Backend** | FastAPI with loguru logger. No `print()`. |
| **XML** | Newlines = `<br/>` tags. Preserve on read/write. |
| **Fonts** | System fonts + Google Fonts (Cinzel for map labels). No custom font files. |
| **D3** | Already installed (`d3-zoom`, `d3-selection`). Add `d3-force` for relationship graph. |
| **Performance** | All animations at 60fps. Tooltip delay 300ms. Shimmer on GPU (`transform`/`opacity` only). |
| **Accessibility** | Keyboard navigation maintained. `aria-label` on interactive elements. Focus visible on tab. |
| **Each loops** | ALWAYS use keys: `{#each items as item (item.id)}` |

---

## Mock Data Requirements

### Existing (v3.4)

- 3 XML files with 20 entities across characterinfo, iteminfo, knowledgeinfo
- 5 AI-generated character portraits (PNG, 370-420KB each)
- 30 TM entries (tm_id=468)
- Cross-reference web between characters, items, knowledge, factions

### New for v3.5

| Data | Format | Count | Purpose |
|------|--------|-------|---------|
| Region boundary polygons | JSON arrays of [x,y] points | 5 regions | Map polygon rendering |
| Terrain type per region | String field in region data | 5 | Terrain indicator icons |
| Route danger levels | `low`/`medium`/`high` field | 5 routes | Route color coding |
| Entity relationship edges | JSON links array | ~15-20 edges | Codex relationship graph |
| Item AI portraits | PNG, nano-banana generated | 3-5 items | Codex entity cards |
| Region thumbnail images | PNG, nano-banana generated | 3-5 regions | Map detail panel |

---

## Success Criteria

### 60-Second Demo Script

| Time | Action | Expected WOW |
|------|--------|-------------|
| 0-10s | Open GameData viewer, click a character node | Attributes light up in 5 colors. Gold keys, blue cross-refs, green editables. |
| 10-20s | Hover over a cross-ref attribute | Preview tooltip slides in with entity image and name. |
| 20-25s | Switch to Dictionary tab | Results stagger in with smooth fade. |
| 25-35s | Navigate to World Map | Fantasy parchment map with polygon regions, custom icons, compass rose. |
| 35-45s | Hover a route, click a region | Route animates, map smoothly zooms to region, detail panel slides in. |
| 45-50s | Navigate to Codex | Entity cards grid with parallax portraits, glassmorphism overlay. |
| 50-55s | Hover cards, click one | Parallax shift, card detail opens. |
| 55-60s | Click "Relationships" | Force graph reveals entity web. Hover highlights connections. |

### Measurable Criteria

1. Every click produces a visually animated response (no instant state changes without transition)
2. Cross-references are navigable in both directions (click to navigate, hover to preview)
3. Map renders 5 regions with polygon boundaries, 5 routes with danger styling, and terrain indicators
4. Codex shows at minimum 10 entity cards with images, and a relationship graph with 15+ edges
5. All loading states use shimmer skeletons (zero spinners in the demo flow)
6. Images load with shimmer → blur-reveal animation
7. Ctrl+K opens global search from any page
8. Toast notifications appear on copy, save, and error actions
9. Full demo runs without any layout shift, flash of unstyled content, or janky animation

---

## File Change Map

| File | Changes |
|------|---------|
| `locaNext/src/lib/components/ldm/GameDataTree.svelte` | Attribute classification, hover tooltips, copy ripple, accordion animation |
| `locaNext/src/lib/components/ldm/GameDataContextPanel.svelte` | Tab crossfade, staggered dict results, shimmer skeletons |
| `locaNext/src/lib/components/ldm/MapCanvas.svelte` | Parchment bg, region polygons, custom icons, terrain, compass, mini-map, route animation |
| `locaNext/src/lib/components/ldm/MapTooltip.svelte` | Enhanced tooltip with region entity counts |
| `locaNext/src/lib/components/ldm/MapDetailPanel.svelte` | Enhanced panel with entity breakdown |
| `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` | Shimmer loading, enhanced layout |
| `locaNext/src/lib/components/ldm/CodexSearchBar.svelte` | Card-style results |
| `locaNext/src/lib/components/pages/CodexPage.svelte` | Entity cards grid, relationship graph tab |
| **NEW:** `locaNext/src/lib/components/ldm/EntityCardGrid.svelte` | Card grid with parallax + glassmorphism |
| **NEW:** `locaNext/src/lib/components/ldm/RelationshipGraph.svelte` | D3 force-directed graph |
| **NEW:** `locaNext/src/lib/components/ldm/HoverPreviewTooltip.svelte` | Cross-ref preview tooltip |
| **NEW:** `locaNext/src/lib/components/common/ToastContainer.svelte` | Toast notification container |
| **NEW:** `locaNext/src/lib/components/common/GlobalSearchPalette.svelte` | Ctrl+K command palette |
| **NEW:** `locaNext/src/lib/stores/toasts.js` | Toast store |
| `server/tools/ldm/routes/gamedata.py` | Enhanced search endpoint for tooltips |
| `server/tools/ldm/routes/mapdata.py` | Enhanced map data with boundaries/terrain |
| **NEW:** `server/tools/ldm/routes/codex_relationships.py` | Relationship graph endpoint |
| **NEW:** `server/tools/ldm/services/relationship_service.py` | Cross-ref graph builder |

---

*Design spec complete. Ready for GSD phase planning and execution.*
*Last updated: 2026-03-17*
