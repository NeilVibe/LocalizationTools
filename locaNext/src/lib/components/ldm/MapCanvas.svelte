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
  <g transform="translate({transform.x},{transform.y}) scale({transform.k})">
    <!-- Background -->
    <rect
      x="0" y="0"
      width={SVG_SIZE} height={SVG_SIZE}
      fill="var(--cds-background, #161616)"
    />

    <!-- Grid lines -->
    {#each gridLines as pos}
      <line
        x1={pos} y1="0" x2={pos} y2={SVG_SIZE}
        stroke="var(--cds-border-subtle-01, #353535)"
        stroke-width="0.5"
        opacity="0.3"
      />
      <line
        x1="0" y1={pos} x2={SVG_SIZE} y2={pos}
        stroke="var(--cds-border-subtle-01, #353535)"
        stroke-width="0.5"
        opacity="0.3"
      />
    {/each}

    <!-- Routes (dashed polylines) -->
    {#each routes as route, i (`${route.from_node}-${route.to_node}-${i}`)}
      {@const points = getRoutePoints(route)}
      {#if points}
        <polyline
          {points}
          fill="none"
          stroke="var(--cds-border-strong-01, #6f6f6f)"
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
          />
        {/if}

        <!-- Node circle -->
        <circle
          cx={node.svgPos.x}
          cy={node.svgPos.y}
          r={getNodeRadius(node.region_type)}
          fill={getNodeColor(node.region_type)}
          stroke="var(--cds-text-01, #f4f4f4)"
          stroke-width="1.5"
          class="node-circle"
        />

        <!-- Label -->
        <text
          x={node.svgPos.x}
          y={node.svgPos.y - getNodeRadius(node.region_type) - 6}
          text-anchor="middle"
          fill="var(--cds-text-01, #f4f4f4)"
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
    background: var(--cds-background);
  }

  .map-canvas:active {
    cursor: grabbing;
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
    stroke: var(--cds-focus, #ffffff);
    stroke-width: 3;
  }

  .node-label {
    pointer-events: none;
    user-select: none;
  }
</style>
