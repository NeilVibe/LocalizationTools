<script>
  /**
   * MapCanvas.svelte - Interactive SVG world map with d3-zoom
   *
   * Renders region polygons, node icons, route connections, and Korean labels
   * on a parchment-textured canvas with pan/zoom interaction.
   *
   * Phase 20: Interactive World Map (Plan 02)
   * Phase 38: Fantasy World Map (Plan 01 parchment + Plan 02 polygons/icons)
   */
  import { onMount } from "svelte";
  import { zoom, zoomIdentity } from "d3-zoom";
  import { select } from "d3-selection";
  import { getNodeIcon } from "./MapIcons.svelte";

  // Props
  let {
    nodes = [],
    routes = [],
    bounds = {},
    onNodeHover = () => {},
    onNodeLeave = () => {},
    onNodeClick = () => {}
  } = $props();

  // State
  let svgElement = $state(null);
  let transform = $state({ x: 0, y: 0, k: 1 });
  let hoveredRoute = $state(null);
  let hoveredRegion = $state(null);
  let zoomBehaviorRef = $state(null);
  let svgSelectionRef = $state(null);

  // Constants
  const SVG_SIZE = 1000;
  const PADDING = 50;

  // Route danger level colors
  const DANGER_COLORS = {
    1: '#24a148',  // safe - green
    2: '#f1c21b',  // moderate - amber
    3: '#da1e28',  // dangerous - red
  };

  function getDangerColor(level) {
    return DANGER_COLORS[level] || '#6f6f6f';
  }

  // Node colors by region_type
  const NODE_COLORS = {
    Main: '#0f62fe',
    Sub: '#4589ff',
    Dungeon: '#da1e28',
    Town: '#24a148',
    Fortress: '#8a3ffc',
    Wilderness: '#007d79'
  };

  // Node radius by region_type
  const NODE_RADIUS = {
    Main: 10,
    Sub: 7,
    Dungeon: 7,
    Town: 9,
    Fortress: 8,
    Wilderness: 7
  };

  /**
   * Map world coordinates to SVG space using linear scale
   */
  function worldToSvg(worldX, worldZ) {
    const minX = bounds.min_x ?? 0;
    const maxX = bounds.max_x ?? 1;
    const minZ = bounds.min_z ?? 0;
    const maxZ = bounds.max_z ?? 1;

    const rangeX = maxX - minX || 1;
    const rangeZ = maxZ - minZ || 1;

    const svgX = PADDING + ((worldX - minX) / rangeX) * (SVG_SIZE - 2 * PADDING);
    const svgY = PADDING + ((worldZ - minZ) / rangeZ) * (SVG_SIZE - 2 * PADDING);

    return { x: svgX, y: svgY };
  }

  /**
   * Get color for a node based on region_type
   */
  function getNodeColor(regionType) {
    return NODE_COLORS[regionType] || '#525252';
  }

  /**
   * Get radius for a node based on region_type
   */
  function getNodeRadius(regionType) {
    return NODE_RADIUS[regionType] || 7;
  }

  /**
   * Build polyline points string for a route
   */
  function getRoutePoints(route) {
    const fromNode = nodes.find(n => n.strkey === route.from_node);
    const toNode = nodes.find(n => n.strkey === route.to_node);
    if (!fromNode || !toNode) return '';

    const points = [];
    const start = worldToSvg(fromNode.x, fromNode.z);
    points.push(`${start.x},${start.y}`);

    // Add waypoints
    if (route.waypoints) {
      for (const wp of route.waypoints) {
        const svgPt = worldToSvg(wp.x, wp.z);
        points.push(`${svgPt.x},${svgPt.y}`);
      }
    }

    const end = worldToSvg(toNode.x, toNode.z);
    points.push(`${end.x},${end.y}`);

    return points.join(' ');
  }

  /** Convert polyline points string "x1,y1 x2,y2 ..." to SVG path "M x1 y1 L x2 y2 ..." */
  function polylineToPath(points) {
    const pairs = points.split(' ').filter(Boolean);
    if (pairs.length === 0) return '';
    return 'M ' + pairs.map((p, i) => {
      const [x, y] = p.split(',');
      return i === 0 ? `${x} ${y}` : `L ${x} ${y}`;
    }).join(' ');
  }

  /** Get midpoint of a route for label positioning */
  function getRouteMidpoint(route) {
    const fromNode = nodes.find(n => n.strkey === route.from_node);
    const toNode = nodes.find(n => n.strkey === route.to_node);
    if (!fromNode || !toNode) return { x: 0, y: 0 };
    const start = worldToSvg(fromNode.x, fromNode.z);
    const end = worldToSvg(toNode.x, toNode.z);
    return { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
  }

  /** Smooth zoom-to-fit on a region node (500ms ease-out-quart) */
  function zoomToRegion(node) {
    if (!svgSelectionRef || !zoomBehaviorRef) return;

    const svgPos = worldToSvg(node.x, node.z);
    const svgRect = svgElement?.getBoundingClientRect();
    if (!svgRect) return;
    const scale = 2.5;

    // Center the node in the viewport
    const tx = svgRect.width / 2 - svgPos.x * scale;
    const ty = svgRect.height / 2 - svgPos.y * scale;

    const newTransform = zoomIdentity.translate(tx, ty).scale(scale);

    svgSelectionRef
      .transition()
      .duration(500)
      .ease(t => {
        // ease-out-quart: 1 - (1-t)^4
        return 1 - Math.pow(1 - t, 4);
      })
      .call(zoomBehaviorRef.transform, newTransform);
  }

  // Derived: viewport rectangle for mini-map
  let viewportRect = $derived.by(() => {
    const svgRect = svgElement?.getBoundingClientRect();
    if (!svgRect) return null;
    const miniScale = 150 / SVG_SIZE;
    const vx = (-transform.x / transform.k) * miniScale;
    const vy = (-transform.y / transform.k) * miniScale;
    const vw = (svgRect.width / transform.k) * miniScale;
    const vh = (svgRect.height / transform.k) * miniScale;
    return { x: vx, y: vy, w: Math.min(vw, 150), h: Math.min(vh, 150) };
  });

  /**
   * Handle node hover - pass mouse coordinates for tooltip positioning
   */
  function handleNodeHover(node, event) {
    onNodeHover(node, event.clientX, event.clientY);
  }

  /**
   * Handle node mouse move - update tooltip position
   */
  function handleNodeMove(node, event) {
    onNodeHover(node, event.clientX, event.clientY);
  }

  // Derived: node positions mapped to SVG space
  let nodePositions = $derived(
    nodes.map(node => ({
      ...node,
      svgPos: worldToSvg(node.x, node.z)
    }))
  );

  // Derived: region polygon data (nodes that have polygon_points)
  let polygonData = $derived(
    nodes.filter(n => n.polygon_points && n.polygon_points.length >= 3).map(node => {
      const svgPoints = node.polygon_points.map(([wx, wz]) => {
        const p = worldToSvg(wx, wz);
        return `${p.x},${p.y}`;
      }).join(' ');

      const center = node.center_x != null && node.center_y != null
        ? worldToSvg(node.center_x, node.center_y)
        : worldToSvg(node.x, node.z);

      return { ...node, svgPoints, center };
    })
  );

  // Grid lines for visual reference
  let gridLines = $derived(
    Array.from({ length: 5 }, (_, i) => (i + 1) * 200)
  );

  onMount(() => {
    if (!svgElement) return;

    const svgSelection = select(svgElement);
    svgSelectionRef = svgSelection;

    const zoomBehavior = zoom()
      .scaleExtent([0.5, 4])
      .on('zoom', (event) => {
        transform = {
          x: event.transform.x,
          y: event.transform.y,
          k: event.transform.k
        };
      });
    zoomBehaviorRef = zoomBehavior;

    svgSelection.call(zoomBehavior);

    // Double-click resets zoom
    svgSelection.on('dblclick.zoom', () => {
      svgSelection
        .transition()
        .duration(300)
        .call(zoomBehavior.transform, zoomIdentity);
    });
  });
</script>

<div class="map-canvas-wrapper">
<svg
  bind:this={svgElement}
  viewBox="0 0 {SVG_SIZE} {SVG_SIZE}"
  class="map-canvas"
  role="img"
  aria-label="Interactive World Map"
>
  <!-- Parchment SVG Definitions -->
  <defs>
    <!-- Parchment noise texture -->
    <filter id="parchment-noise" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" result="noise" />
      <feColorMatrix type="saturate" values="0" in="noise" result="grayNoise" />
      <feComponentTransfer in="grayNoise" result="alphaedNoise">
        <feFuncA type="linear" slope="0.08" intercept="0" />
      </feComponentTransfer>
      <feBlend in="SourceGraphic" in2="alphaedNoise" mode="overlay" />
    </filter>

    <!-- Region glow filter -->
    <filter id="region-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="glow" />
      <feMerge>
        <feMergeNode in="glow" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <!-- Parchment warm gradient -->
    <radialGradient id="parchment-gradient" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="#2a2010" />
      <stop offset="50%" stop-color="#221a0c" />
      <stop offset="100%" stop-color="#1a1408" />
    </radialGradient>

    <!-- Route direction arrow marker -->
    <marker id="route-arrow" viewBox="0 0 10 10" refX="5" refY="5"
      markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(212,154,92,0.6)" />
    </marker>

    <!-- Vignette edges -->
    <radialGradient id="vignette" cx="50%" cy="50%" r="55%">
      <stop offset="0%" stop-color="transparent" />
      <stop offset="70%" stop-color="transparent" />
      <stop offset="100%" stop-color="rgba(0,0,0,0.5)" />
    </radialGradient>
  </defs>

  <!-- Ornamental border (fixed, not affected by zoom) -->
  <rect x="4" y="4" width={SVG_SIZE - 8} height={SVG_SIZE - 8}
    fill="none" stroke="#5c4a2e" stroke-width="2" rx="2" class="map-border-outer" />
  <rect x="10" y="10" width={SVG_SIZE - 20} height={SVG_SIZE - 20}
    fill="none" stroke="#3d321e" stroke-width="1" rx="1" class="map-border-inner" />

  <!-- Compass rose corners (fixed) -->
  <!-- Top-left -->
  <g class="compass-corner" transform="translate(20, 20)">
    <line x1="0" y1="0" x2="20" y2="0" stroke="#5c4a2e" stroke-width="1.5" />
    <line x1="0" y1="0" x2="0" y2="20" stroke="#5c4a2e" stroke-width="1.5" />
    <circle cx="0" cy="0" r="3" fill="#5c4a2e" />
  </g>
  <!-- Top-right -->
  <g class="compass-corner" transform="translate({SVG_SIZE - 20}, 20)">
    <line x1="0" y1="0" x2="-20" y2="0" stroke="#5c4a2e" stroke-width="1.5" />
    <line x1="0" y1="0" x2="0" y2="20" stroke="#5c4a2e" stroke-width="1.5" />
    <circle cx="0" cy="0" r="3" fill="#5c4a2e" />
  </g>
  <!-- Bottom-left -->
  <g class="compass-corner" transform="translate(20, {SVG_SIZE - 20})">
    <line x1="0" y1="0" x2="20" y2="0" stroke="#5c4a2e" stroke-width="1.5" />
    <line x1="0" y1="0" x2="0" y2="-20" stroke="#5c4a2e" stroke-width="1.5" />
    <circle cx="0" cy="0" r="3" fill="#5c4a2e" />
  </g>
  <!-- Bottom-right -->
  <g class="compass-corner" transform="translate({SVG_SIZE - 20}, {SVG_SIZE - 20})">
    <line x1="0" y1="0" x2="-20" y2="0" stroke="#5c4a2e" stroke-width="1.5" />
    <line x1="0" y1="0" x2="0" y2="-20" stroke="#5c4a2e" stroke-width="1.5" />
    <circle cx="0" cy="0" r="3" fill="#5c4a2e" />
  </g>

  <!-- Compass rose indicator (top-right area, fixed) -->
  <g class="compass-rose" transform="translate({SVG_SIZE - 55}, 55)">
    <!-- N-S-E-W lines -->
    <line x1="0" y1="-18" x2="0" y2="18" stroke="#5c4a2e" stroke-width="1" />
    <line x1="-18" y1="0" x2="18" y2="0" stroke="#5c4a2e" stroke-width="1" />
    <!-- Diagonal lines -->
    <line x1="-10" y1="-10" x2="10" y2="10" stroke="#3d321e" stroke-width="0.5" />
    <line x1="10" y1="-10" x2="-10" y2="10" stroke="#3d321e" stroke-width="0.5" />
    <!-- N pointer -->
    <polygon points="0,-18 -4,-8 4,-8" fill="#8b6914" opacity="0.8" />
    <!-- Center -->
    <circle cx="0" cy="0" r="3" fill="#5c4a2e" />
    <circle cx="0" cy="0" r="1.5" fill="#8b6914" />
    <!-- N label -->
    <text x="0" y="-22" text-anchor="middle" fill="#8b6914" font-size="9" font-weight="bold">N</text>
  </g>

  <g transform="translate({transform.x},{transform.y}) scale({transform.k})">
    <!-- Parchment background layers -->
    <!-- Base dark sepia -->
    <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="#1a1408" />
    <!-- Warm gradient overlay -->
    <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="url(#parchment-gradient)" />
    <!-- Noise texture overlay -->
    <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="#1a1408" opacity="0.3" filter="url(#parchment-noise)" />
    <!-- Vignette -->
    <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="url(#vignette)" />

    <!-- Grid lines (parchment-tinted) -->
    {#each gridLines as pos}
      <line
        x1={pos} y1="0" x2={pos} y2={SVG_SIZE}
        stroke="#3d321e"
        stroke-width="0.5"
        opacity="0.25"
      />
      <line
        x1="0" y1={pos} x2={SVG_SIZE} y2={pos}
        stroke="#3d321e"
        stroke-width="0.5"
        opacity="0.25"
      />
    {/each}

    <!-- Region polygons (rendered between grid and routes) -->
    {#each polygonData as region (region.strkey)}
      <g class="region-polygon"
         class:hovered={hoveredRegion === region.strkey}
         onmouseenter={() => hoveredRegion = region.strkey}
         onmouseleave={() => hoveredRegion = null}
         role="button"
         tabindex="0"
         onclick={() => onNodeClick(region)}
         onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onNodeClick(region); }}
      >
        <!-- Polygon fill -->
        <polygon
          points={region.svgPoints}
          fill={getNodeColor(region.region_type)}
          fill-opacity={hoveredRegion === region.strkey ? 0.3 : 0.12}
          stroke={getNodeColor(region.region_type)}
          stroke-opacity={hoveredRegion === region.strkey ? 0.6 : 0.3}
          stroke-width={hoveredRegion === region.strkey ? 2 : 1}
          filter={hoveredRegion === region.strkey ? 'url(#region-glow)' : 'none'}
          style="transition: fill-opacity 200ms ease-out, stroke-opacity 200ms ease-out, stroke-width 200ms ease-out;"
        />

        <!-- Korean region name at center -->
        <text
          x={region.center.x}
          y={region.center.y}
          text-anchor="middle"
          dominant-baseline="middle"
          fill="rgba(240,184,120,0.9)"
          font-size="13"
          font-weight="600"
          class="region-name-label"
          style="text-shadow: 0 0 6px rgba(212,154,92,0.5), 0 1px 2px rgba(0,0,0,0.8);"
        >
          {region.name_kr || region.name}
        </text>
      </g>
    {/each}

    <!-- Routes with danger coloring and hover animation -->
    {#each routes as route, i (`route-${route.from_node}-${route.to_node}-${i}`)}
      {@const points = getRoutePoints(route)}
      {@const dangerColor = getDangerColor(route.danger_level || 1)}
      {@const isHovered = hoveredRoute === i}
      {#if points}
        {@const pathD = polylineToPath(points)}
        <g class="route-group"
           onmouseenter={() => hoveredRoute = i}
           onmouseleave={() => hoveredRoute = null}
        >
          <!-- Hit area (wider, invisible) -->
          <path d={pathD} fill="none" stroke="transparent" stroke-width="12" />

          <!-- Visible route line -->
          <path
            d={pathD}
            fill="none"
            stroke={dangerColor}
            stroke-width={isHovered ? 3 : 2}
            stroke-dasharray={isHovered ? "8 4" : "6 3"}
            stroke-linecap="round"
            opacity={isHovered ? 0.9 : 0.5}
            marker-mid="url(#route-arrow)"
            class="route-path"
            class:route-animated={isHovered}
            style="transition: stroke-width 200ms ease-out, opacity 200ms ease-out;"
          />

          <!-- Travel info label on hover -->
          {#if isHovered && route.travel_time}
            {@const midPoint = getRouteMidpoint(route)}
            <text
              x={midPoint.x} y={midPoint.y - 10}
              text-anchor="middle" fill="rgba(240,184,120,0.9)"
              font-size="10" font-weight="500"
              style="text-shadow: 0 1px 3px rgba(0,0,0,0.9);"
              class="route-label"
            >
              {route.travel_time}
            </text>
          {/if}
        </g>
      {/if}
    {/each}

    <!-- Nodes (icon markers replacing plain circles) -->
    {#each nodePositions as node (node.strkey)}
      {@const icon = getNodeIcon(node.region_type)}
      {@const iconScale = icon.size / 24}
      {@const halfSize = icon.size / 2}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <g
        class="map-node"
        role="button"
        tabindex="0"
        onmouseenter={(e) => handleNodeHover(node, e)}
        onmousemove={(e) => handleNodeMove(node, e)}
        onmouseleave={() => onNodeLeave()}
        onclick={() => { zoomToRegion(node); onNodeClick(node); }}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onNodeClick(node); }}
      >
        <!-- Icon background glow -->
        <circle
          cx={node.svgPos.x}
          cy={node.svgPos.y}
          r={halfSize + 3}
          fill={getNodeColor(node.region_type)}
          opacity="0.2"
          class="icon-glow"
        />

        <!-- Icon marker -->
        <g transform="translate({node.svgPos.x - halfSize},{node.svgPos.y - halfSize}) scale({iconScale})">
          <rect width="24" height="24" fill="rgba(26,20,8,0.7)" rx="4" />
          <path d={icon.path} fill={getNodeColor(node.region_type)} />
        </g>

        <!-- Label -->
        <text
          x={node.svgPos.x}
          y={node.svgPos.y + halfSize + 14}
          text-anchor="middle"
          fill="#d4c5a0"
          font-size="11"
          font-weight="500"
          class="node-label"
        >
          {node.name}
        </text>
      </g>
    {/each}
  </g>
</svg>

<!-- Mini-map overlay -->
<div class="mini-map">
  <svg viewBox="0 0 150 150" width="150" height="150">
    <rect width="150" height="150" fill="rgba(26,20,8,0.85)" rx="4" />
    <rect x="1" y="1" width="148" height="148" fill="none" stroke="rgba(212,154,92,0.3)" rx="4" />

    <!-- Simplified region shapes -->
    {#each polygonData as region (region.strkey + '-mini')}
      {@const miniPoints = region.polygon_points?.map(([wx, wz]) => {
        const p = worldToSvg(wx, wz);
        return `${p.x * 150/SVG_SIZE},${p.y * 150/SVG_SIZE}`;
      }).join(' ') || ''}
      {#if miniPoints}
        <polygon points={miniPoints}
          fill={getNodeColor(region.region_type)} fill-opacity="0.3"
          stroke={getNodeColor(region.region_type)} stroke-opacity="0.5" stroke-width="0.5" />
      {/if}
    {/each}

    <!-- Node dots -->
    {#each nodePositions as node (node.strkey + '-mini')}
      <circle
        cx={node.svgPos.x * 150/SVG_SIZE}
        cy={node.svgPos.y * 150/SVG_SIZE}
        r="2"
        fill={getNodeColor(node.region_type)}
      />
    {/each}

    <!-- Viewport rectangle -->
    {#if viewportRect}
      <rect
        x={viewportRect.x} y={viewportRect.y}
        width={viewportRect.w} height={viewportRect.h}
        fill="none" stroke="rgba(240,184,120,0.6)" stroke-width="1"
      />
    {/if}
  </svg>
</div>
</div>

<style>
  .map-canvas {
    width: 100%;
    height: 100%;
    cursor: grab;
    background: #1a1408;
  }

  .map-canvas:active {
    cursor: grabbing;
  }

  .map-border-outer,
  .map-border-inner {
    pointer-events: none;
  }

  .compass-corner,
  .compass-rose {
    pointer-events: none;
  }

  /* Region polygon styles */
  .region-polygon {
    cursor: pointer;
    outline: none;
  }

  .region-polygon:focus polygon {
    stroke: var(--cds-focus, #ffffff);
    stroke-width: 2.5;
  }

  .region-name-label {
    pointer-events: none;
    user-select: none;
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  }

  /* Node icon styles */
  .map-node {
    cursor: pointer;
    outline: none;
  }

  .icon-glow {
    transition: opacity 200ms ease-out;
  }

  .map-node:hover .icon-glow {
    opacity: 0.4;
  }

  .map-node:focus {
    outline: none;
  }

  .map-node:focus .icon-glow {
    opacity: 0.5;
    stroke: var(--cds-focus, #ffffff);
    stroke-width: 2;
  }

  .node-label {
    pointer-events: none;
    user-select: none;
    font-family: 'Georgia', 'Times New Roman', serif;
  }

  /* Map canvas wrapper for mini-map positioning */
  .map-canvas-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
  }

  /* Route animations */
  .route-path {
    pointer-events: none;
  }

  .route-group {
    cursor: pointer;
  }

  .route-animated {
    animation: routeFlow 1.5s linear infinite;
  }

  @keyframes routeFlow {
    to {
      stroke-dashoffset: -24;
    }
  }

  .route-label {
    pointer-events: none;
    user-select: none;
  }

  /* Mini-map */
  .mini-map {
    position: absolute;
    bottom: 16px;
    right: 16px;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(212, 154, 92, 0.25);
    z-index: 10;
    pointer-events: auto;
  }

  @media (prefers-reduced-motion: reduce) {
    .map-canvas,
    .map-canvas * {
      transition: none !important;
      animation: none !important;
    }

    .route-animated {
      animation: none;
    }
  }
</style>
