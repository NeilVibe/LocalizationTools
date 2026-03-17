<script>
  /**
   * MapCanvas.svelte - Interactive SVG world map with d3-zoom
   *
   * Renders region nodes at WorldPosition coordinates with pan/zoom,
   * route connections as dashed polylines, and color-coded node circles.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  import { onMount } from "svelte";
  import { zoom, zoomIdentity } from "d3-zoom";
  import { select } from "d3-selection";

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

  // Constants
  const SVG_SIZE = 1000;
  const PADDING = 50;

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

  // Grid lines for visual reference
  let gridLines = $derived(
    Array.from({ length: 5 }, (_, i) => (i + 1) * 200)
  );

  onMount(() => {
    if (!svgElement) return;

    const svgSelection = select(svgElement);

    const zoomBehavior = zoom()
      .scaleExtent([0.5, 4])
      .on('zoom', (event) => {
        transform = {
          x: event.transform.x,
          y: event.transform.y,
          k: event.transform.k
        };
      });

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

    <!-- Routes (dashed polylines) -->
    {#each routes as route, i (`${route.from_node}-${route.to_node}-${i}`)}
      {@const points = getRoutePoints(route)}
      {#if points}
        <polyline
          {points}
          fill="none"
          stroke="#8b7355"
          stroke-width="1.5"
          stroke-dasharray="6 3"
          opacity="0.5"
        />
      {/if}
    {/each}

    <!-- Nodes -->
    {#each nodePositions as node (node.strkey)}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <g
        class="map-node"
        role="button"
        tabindex="0"
        onmouseenter={(e) => handleNodeHover(node, e)}
        onmousemove={(e) => handleNodeMove(node, e)}
        onmouseleave={() => onNodeLeave()}
        onclick={() => onNodeClick(node)}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onNodeClick(node); }}
      >
        <!-- Glow effect for Main nodes -->
        {#if node.region_type === 'Main'}
          <circle
            cx={node.svgPos.x}
            cy={node.svgPos.y}
            r={getNodeRadius(node.region_type) + 4}
            fill={getNodeColor(node.region_type)}
            opacity="0.15"
            filter="url(#region-glow)"
          />
        {/if}

        <!-- Node circle -->
        <circle
          cx={node.svgPos.x}
          cy={node.svgPos.y}
          r={getNodeRadius(node.region_type)}
          fill={getNodeColor(node.region_type)}
          stroke="#d4c5a0"
          stroke-width="1.5"
          class="node-circle"
        />

        <!-- Label -->
        <text
          x={node.svgPos.x}
          y={node.svgPos.y - getNodeRadius(node.region_type) - 6}
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

  .map-node {
    cursor: pointer;
    outline: none;
  }

  .map-node:hover .node-circle,
  .map-node:focus .node-circle {
    stroke-width: 2.5;
    filter: brightness(1.2);
  }

  .map-node:focus {
    outline: none;
  }

  .map-node:focus .node-circle {
    stroke: #f0e6c8;
    stroke-width: 3;
  }

  .node-label {
    pointer-events: none;
    user-select: none;
    font-family: 'Georgia', 'Times New Roman', serif;
  }

  @media (prefers-reduced-motion: reduce) {
    .map-canvas,
    .map-canvas * {
      transition: none !important;
      animation: none !important;
    }
  }
</style>
