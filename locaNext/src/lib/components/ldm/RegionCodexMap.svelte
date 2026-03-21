<script>
  /**
   * RegionCodexMap.svelte - Interactive d3-zoom SVG map rendering WorldPosition coordinates
   *
   * Renders region nodes at their (x, z) world positions with d3-zoom pan/scroll.
   * Node colors and sizes vary by node_type. Selected node gets highlight ring.
   * Parchment aesthetic copied from MapCanvas.svelte.
   *
   * Phase 49: Region Codex UI + Interactive Map (Plan 02)
   */
  import { onMount, onDestroy } from "svelte";
  import { zoom, zoomIdentity } from "d3-zoom";
  import { select } from "d3-selection";

  // Props
  let {
    regions = [],
    selectedStrkey = null,
    onNodeClick = () => {},
    onNodeHover = () => {},
    onNodeLeave = () => {}
  } = $props();

  // State
  let svgElement = $state(null);
  let transform = $state({ x: 0, y: 0, k: 1 });
  let zoomBehaviorRef = null;
  let svgSelectionRef = null;

  // Constants
  const SVG_SIZE = 1000;
  const PADDING = 50;
  const MINIMAP_SIZE = 120;
  const MINIMAP_SCALE = MINIMAP_SIZE / SVG_SIZE;

  // Node colors by node_type (matching MapCanvas pattern)
  const NODE_COLORS = {
    Main: '#0f62fe',
    Sub: '#4589ff',
    Dungeon: '#da1e28',
    Town: '#24a148',
    Fortress: '#8a3ffc',
    Wilderness: '#007d79'
  };

  function getNodeColor(nodeType) {
    return NODE_COLORS[nodeType] || '#6f6f6f';
  }

  // Derived: Only regions with world_position
  let positionedRegions = $derived(
    regions.filter(r => r.world_position && r.world_position.length >= 3)
  );

  // Derived: Compute bounds from all positioned regions
  let bounds = $derived.by(() => {
    if (positionedRegions.length === 0) {
      return { minX: 0, maxX: 1, minZ: 0, maxZ: 1 };
    }
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (const r of positionedRegions) {
      const [x, _y, z] = r.world_position;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;
    }
    // Handle edge case: all same position
    if (maxX - minX < 0.001) { minX -= 1; maxX += 1; }
    if (maxZ - minZ < 0.001) { minZ -= 1; maxZ += 1; }
    return { minX, maxX, minZ, maxZ };
  });

  /**
   * Map world X to SVG X
   */
  function mapX(wx) {
    const rangeX = bounds.maxX - bounds.minX || 1;
    return PADDING + ((wx - bounds.minX) / rangeX) * (SVG_SIZE - 2 * PADDING);
  }

  /**
   * Map world Z to SVG Y (top-down view: z maps to y)
   */
  function mapZ(wz) {
    const rangeZ = bounds.maxZ - bounds.minZ || 1;
    return PADDING + ((wz - bounds.minZ) / rangeZ) * (SVG_SIZE - 2 * PADDING);
  }

  // Derived: node positions in SVG space
  let nodePositions = $derived(
    positionedRegions.map(r => {
      const [x, _y, z] = r.world_position;
      return {
        ...r,
        svgX: mapX(x),
        svgY: mapZ(z)
      };
    })
  );

  // Derived: viewport rectangle for mini-map
  let viewportRect = $derived.by(() => {
    const svgRect = svgElement?.getBoundingClientRect();
    if (!svgRect) return null;
    const vx = (-transform.x / transform.k) * MINIMAP_SCALE;
    const vy = (-transform.y / transform.k) * MINIMAP_SCALE;
    const vw = (svgRect.width / transform.k) * MINIMAP_SCALE;
    const vh = (svgRect.height / transform.k) * MINIMAP_SCALE;
    return { x: vx, y: vy, w: Math.min(vw, MINIMAP_SIZE), h: Math.min(vh, MINIMAP_SIZE) };
  });

  /**
   * Handle node hover - pass mouse coordinates for tooltip positioning
   */
  function handleNodeHover(region, event) {
    onNodeHover(region, event.clientX, event.clientY);
  }

  onMount(() => {
    if (!svgElement) return;

    const svgSelection = select(svgElement);
    svgSelectionRef = svgSelection;

    const zoomBehavior = zoom()
      .scaleExtent([0.5, 6])
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

  onDestroy(() => {
    if (svgSelectionRef) {
      svgSelectionRef.on('.zoom', null);
      svgSelectionRef.on('dblclick.zoom', null);
    }
    if (zoomBehaviorRef) {
      zoomBehaviorRef.on('zoom', null);
    }
    svgSelectionRef = null;
    zoomBehaviorRef = null;
  });
</script>

<div class="region-map-wrapper">
  <svg
    bind:this={svgElement}
    viewBox="0 0 {SVG_SIZE} {SVG_SIZE}"
    class="region-map-canvas"
    role="img"
    aria-label="Region Codex Map"
  >
    <!-- Parchment SVG Definitions -->
    <defs>
      <filter id="rcm-parchment-noise" x="0%" y="0%" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" result="noise" />
        <feColorMatrix type="saturate" values="0" in="noise" result="grayNoise" />
        <feComponentTransfer in="grayNoise" result="alphaedNoise">
          <feFuncA type="linear" slope="0.08" intercept="0" />
        </feComponentTransfer>
        <feBlend in="SourceGraphic" in2="alphaedNoise" mode="overlay" />
      </filter>

      <filter id="rcm-text-shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="rgba(0,0,0,0.85)" />
      </filter>

      <filter id="rcm-node-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="glow" />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>

      <radialGradient id="rcm-parchment-gradient" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stop-color="#2a2010" />
        <stop offset="50%" stop-color="#221a0c" />
        <stop offset="100%" stop-color="#1a1408" />
      </radialGradient>

      <radialGradient id="rcm-vignette" cx="50%" cy="50%" r="55%">
        <stop offset="0%" stop-color="transparent" />
        <stop offset="70%" stop-color="transparent" />
        <stop offset="100%" stop-color="rgba(0,0,0,0.5)" />
      </radialGradient>
    </defs>

    <!-- Ornamental border (fixed, not affected by zoom) -->
    <rect x="4" y="4" width={SVG_SIZE - 8} height={SVG_SIZE - 8}
      fill="none" stroke="#8b6914" stroke-width="2" rx="2" opacity="0.5" class="map-border" />

    <!-- Compass rose (top-right, fixed) -->
    <g class="compass-rose" transform="translate({SVG_SIZE - 45}, 45)">
      <line x1="0" y1="-14" x2="0" y2="14" stroke="#5c4a2e" stroke-width="1" />
      <line x1="-14" y1="0" x2="14" y2="0" stroke="#5c4a2e" stroke-width="1" />
      <polygon points="0,-14 -3,-6 3,-6" fill="#8b6914" opacity="0.8" />
      <circle cx="0" cy="0" r="2" fill="#5c4a2e" />
      <text x="0" y="-18" text-anchor="middle" fill="#8b6914" font-size="8" font-weight="bold">N</text>
    </g>

    <g transform="translate({transform.x},{transform.y}) scale({transform.k})">
      <!-- Parchment background -->
      <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="#1a1408" />
      <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="url(#rcm-parchment-gradient)" />
      <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="#1a1408" opacity="0.3" filter="url(#rcm-parchment-noise)" />
      <rect x="0" y="0" width={SVG_SIZE} height={SVG_SIZE} fill="url(#rcm-vignette)" />

      <!-- Grid lines -->
      {#each [200, 400, 600, 800] as pos (pos)}
        <line x1={pos} y1="0" x2={pos} y2={SVG_SIZE} stroke="#3d321e" stroke-width="0.5" opacity="0.12" />
        <line x1="0" y1={pos} x2={SVG_SIZE} y2={pos} stroke="#3d321e" stroke-width="0.5" opacity="0.12" />
      {/each}

      <!-- Region nodes -->
      {#each nodePositions as node (node.strkey)}
        {@const isSelected = selectedStrkey === node.strkey}
        {@const color = getNodeColor(node.node_type)}
        {@const radius = isSelected ? 12 : 8}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <g
          class="region-node"
          class:selected={isSelected}
          role="button"
          tabindex="0"
          onmouseenter={(e) => handleNodeHover(node, e)}
          onmousemove={(e) => handleNodeHover(node, e)}
          onmouseleave={() => onNodeLeave()}
          onclick={() => onNodeClick(node)}
          onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onNodeClick(node); }}
        >
          <!-- Glow ring for selected -->
          {#if isSelected}
            <circle
              cx={node.svgX}
              cy={node.svgY}
              r={radius + 6}
              fill="none"
              stroke={color}
              stroke-width="2"
              opacity="0.3"
              filter="url(#rcm-node-glow)"
            />
          {/if}

          <!-- Node circle -->
          <circle
            cx={node.svgX}
            cy={node.svgY}
            r={radius}
            fill={color}
            stroke={isSelected ? '#ffffff' : 'rgba(26,20,8,0.8)'}
            stroke-width={isSelected ? 3 : 1.5}
            class="node-circle"
          />

          <!-- Label below node -->
          {#if transform.k >= 0.8}
            <text
              x={node.svgX}
              y={node.svgY + radius + 14}
              text-anchor="middle"
              fill={isSelected ? '#ffffff' : '#d4c5a0'}
              font-size={isSelected ? '12' : '10'}
              font-weight={isSelected ? '600' : '400'}
              class="node-label"
              filter="url(#rcm-text-shadow)"
            >
              {node.name}
            </text>
          {/if}
        </g>
      {/each}
    </g>
  </svg>

  <!-- Mini-map overlay -->
  <div class="mini-map">
    <svg viewBox="0 0 {MINIMAP_SIZE} {MINIMAP_SIZE}" width={MINIMAP_SIZE} height={MINIMAP_SIZE}>
      <rect width={MINIMAP_SIZE} height={MINIMAP_SIZE} fill="rgba(26,20,8,0.85)" rx="3" />
      <rect x="1" y="1" width={MINIMAP_SIZE - 2} height={MINIMAP_SIZE - 2} fill="none" stroke="rgba(212,154,92,0.3)" rx="3" />

      <!-- Node dots -->
      {#each nodePositions as node (node.strkey + '-mini')}
        <circle
          cx={node.svgX * MINIMAP_SCALE}
          cy={node.svgY * MINIMAP_SCALE}
          r={selectedStrkey === node.strkey ? 3 : 1.5}
          fill={getNodeColor(node.node_type)}
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

  {#if positionedRegions.length === 0}
    <div class="no-positions-overlay">
      <p>No regions with world positions</p>
    </div>
  {/if}
</div>

<style>
  .region-map-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .region-map-canvas {
    width: 100%;
    height: 100%;
    cursor: grab;
    background: #1a1408;
  }

  .region-map-canvas:active {
    cursor: grabbing;
  }

  .map-border {
    pointer-events: none;
  }

  .compass-rose {
    pointer-events: none;
  }

  .region-node {
    cursor: pointer;
    outline: none;
  }

  .node-circle {
    transition: r 200ms ease-out, stroke-width 200ms ease-out;
  }

  .region-node:hover .node-circle {
    filter: brightness(1.3);
  }

  .region-node:focus .node-circle {
    stroke: var(--cds-focus, #ffffff);
    stroke-width: 2.5;
  }

  .node-label {
    pointer-events: none;
    user-select: none;
    font-family: 'Georgia', 'Times New Roman', serif;
  }

  .mini-map {
    position: absolute;
    bottom: 12px;
    right: 12px;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(212, 154, 92, 0.2);
    z-index: 10;
    pointer-events: auto;
  }

  .no-positions-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: var(--cds-text-03);
    font-size: 0.875rem;
    background: rgba(0, 0, 0, 0.6);
    padding: 12px 20px;
    border-radius: 6px;
    pointer-events: none;
  }

  .no-positions-overlay p {
    margin: 0;
  }

  @media (prefers-reduced-motion: reduce) {
    .region-map-canvas,
    .region-map-canvas * {
      transition: none !important;
      animation: none !important;
    }
  }
</style>
