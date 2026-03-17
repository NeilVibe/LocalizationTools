<script>
  /**
   * CodexRelationshipGraph.svelte - D3 force-directed entity relationship graph
   *
   * Renders entity nodes colored by type with typed relationship links.
   * Supports zoom, pan, drag, and hover highlighting.
   *
   * Phase 39: Codex Cards + Relationship Graph (Plan 02)
   */
  import { onMount } from "svelte";
  import { select } from "d3-selection";
  import { zoom, zoomIdentity } from "d3-zoom";
  import { forceSimulation, forceManyBody, forceLink, forceCenter, forceCollide } from "d3-force";
  import { drag } from "d3-drag";
  import { InlineLoading } from "carbon-components-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  let { onentityclick = () => {} } = $props();

  let container = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let hoveredNodeId = $state(null);
  let simulation = null;

  const NODE_COLORS = {
    character: '#a56eff',
    item: '#33b1ff',
    skill: '#ee5396',
    region: '#009d9a',
    gimmick: '#878d96',
  };

  const LINK_STYLES = {
    owns:       { color: '#33b1ff', dash: '',       width: 2 },
    knows:      { color: '#24a148', dash: '6,3',    width: 2 },
    member_of:  { color: '#a56eff', dash: '',       width: 1.5 },
    located_in: { color: '#009d9a', dash: '3,3',    width: 1.5 },
    enemy_of:   { color: '#da1e28', dash: '',       width: 2 },
    related:    { color: '#6f6f6f', dash: '4,2',    width: 1 },
  };

  // Cleanup simulation on destroy
  $effect(() => {
    return () => {
      if (simulation) simulation.stop();
    };
  });

  onMount(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/relationships`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      if (data.nodes.length === 0) {
        loading = false;
        error = 'No entities found -- ensure gamedata is indexed.';
        return;
      }

      // Defer to next frame so flex layout has settled and container has height
      requestAnimationFrame(() => initGraph(data.nodes, data.links));
    } catch (err) {
      logger.error('Failed to fetch relationships', { error: err.message });
      error = 'Failed to load relationship data: ' + err.message;
      loading = false;
    }
  });

  function initGraph(nodes, links) {
    const width = container.clientWidth;
    const height = container.clientHeight || 600;
    const cx = width / 2;
    const cy = height / 2;

    // Set initial node positions in a circle around center
    const angleStep = (2 * Math.PI) / nodes.length;
    const radius = Math.min(width, height) * 0.3;
    nodes.forEach((node, i) => {
      node.x = cx + radius * Math.cos(angleStep * i);
      node.y = cy + radius * Math.sin(angleStep * i);
    });

    // Clear previous
    select(container).select('svg').remove();

    const svg = select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('background', 'transparent');

    const g = svg.append('g');

    // Zoom
    const zoomBehavior = zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoomBehavior);

    // Connection count for node sizing
    const connectionCount = {};
    links.forEach(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      connectionCount[sid] = (connectionCount[sid] || 0) + 1;
      connectionCount[tid] = (connectionCount[tid] || 0) + 1;
    });

    // Force simulation
    simulation = forceSimulation(nodes)
      .force("link", forceLink(links).id(d => d.id).distance(120).strength(0.5))
      .force("charge", forceManyBody().strength(-300))
      .force("center", forceCenter(cx, cy))
      .force("collision", forceCollide(40))
      .alpha(1)
      .alphaDecay(0.02);

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => LINK_STYLES[d.rel_type]?.color || '#6f6f6f')
      .attr('stroke-width', d => LINK_STYLES[d.rel_type]?.width || 1)
      .attr('stroke-dasharray', d => LINK_STYLES[d.rel_type]?.dash || '')
      .attr('opacity', 0.6);

    // Node groups
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded)
      );

    // Node circles
    node.append('circle')
      .attr('r', d => Math.min(8 + (connectionCount[d.id] || 0) * 2, 24))
      .attr('fill', d => NODE_COLORS[d.entity_type] || '#6f6f6f')
      .attr('stroke', 'rgba(255,255,255,0.3)')
      .attr('stroke-width', 1.5);

    // Node labels
    node.append('text')
      .text(d => d.name.length > 12 ? d.name.slice(0, 12) + '...' : d.name)
      .attr('dy', d => Math.min(8 + (connectionCount[d.id] || 0) * 2, 24) + 14)
      .attr('text-anchor', 'middle')
      .attr('fill', 'var(--cds-text-02, #c6c6c6)')
      .attr('font-size', '10px')
      .attr('pointer-events', 'none');

    // Hover interactions
    node.on('mouseenter', function(event, d) {
      hoveredNodeId = d.id;
      const connected = new Set([d.id]);
      links.forEach(l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source;
        const tid = typeof l.target === 'object' ? l.target.id : l.target;
        if (sid === d.id) connected.add(tid);
        if (tid === d.id) connected.add(sid);
      });
      // Dim unconnected nodes
      node.select('circle')
        .transition().duration(200)
        .attr('opacity', n => connected.has(n.id) ? 1 : 0.2);
      node.select('text')
        .transition().duration(200)
        .attr('opacity', n => connected.has(n.id) ? 1 : 0.2);
      // Dim unconnected links
      link.transition().duration(200)
        .attr('opacity', l => {
          const sid = typeof l.source === 'object' ? l.source.id : l.source;
          const tid = typeof l.target === 'object' ? l.target.id : l.target;
          return (sid === d.id || tid === d.id) ? 0.8 : 0.1;
        });
    });

    node.on('mouseleave', function() {
      hoveredNodeId = null;
      node.select('circle').transition().duration(200).attr('opacity', 1);
      node.select('text').transition().duration(200).attr('opacity', 1);
      link.transition().duration(200).attr('opacity', 0.6);
    });

    // Click to navigate
    node.on('click', function(event, d) {
      onentityclick(d.id);
    });

    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    loading = false;
  }

  function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
</script>

<div class="relationship-graph" bind:this={container}>
  {#if loading}
    <div class="graph-loading"><InlineLoading description="Building relationship graph..." /></div>
  {/if}
  {#if error}
    <div class="graph-error">{error}</div>
  {/if}
  <div class="graph-legend">
    <div class="legend-title">Relationships</div>
    {#each Object.entries(LINK_STYLES) as [type, style] (type)}
      <div class="legend-item">
        <svg width="24" height="2"><line x1="0" y1="1" x2="24" y2="1" stroke={style.color} stroke-width={style.width} stroke-dasharray={style.dash} /></svg>
        <span>{type.replace('_', ' ')}</span>
      </div>
    {/each}
    <div class="legend-title" style="margin-top: 6px;">Entity Types</div>
    {#each Object.entries(NODE_COLORS) as [type, color] (type)}
      <div class="legend-item">
        <svg width="10" height="10"><circle cx="5" cy="5" r="5" fill={color} /></svg>
        <span>{type}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .relationship-graph {
    position: relative;
    flex: 1;
    min-height: 400px;
    width: 100%;
    overflow: hidden;
  }

  .relationship-graph :global(svg) {
    display: block;
    width: 100%;
    height: 100%;
  }

  .graph-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 1;
  }

  .graph-error {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: var(--cds-text-error, #da1e28);
    font-size: 0.875rem;
    text-align: center;
    padding: 16px;
  }

  .graph-legend {
    position: absolute;
    bottom: 12px;
    left: 12px;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 8px;
    padding: 8px 12px;
    z-index: 2;
    pointer-events: none;
  }

  .legend-title {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 2px;
  }

  .legend-item span {
    font-size: 0.6875rem;
    color: var(--cds-text-02, #c6c6c6);
    text-transform: capitalize;
  }
</style>
