<script>
  /**
   * AudioExportTree.svelte - Category hierarchy sidebar for Audio Codex
   *
   * MDG-exact: truly recursive export_path tree (unlimited depth),
   * collapsible nodes, count badges, auto-expand first 2 levels,
   * right-click context menu (Expand All / Collapse All).
   *
   * Phase 107→108: Recursive tree graft from MDG export_tree.py
   */
  import { ChevronRight, ChevronDown } from "carbon-icons-svelte";

  let {
    categories = [],
    activeCategory = null,
    totalEvents = 0,
    onselect = () => {},
  } = $props();

  const AUTO_EXPAND_DEPTH = 0; // Start fully collapsed — user drills down by clicking

  // Track expanded nodes — auto-expand first N levels on mount
  let expandedPaths = $state(new Set());
  let initialized = false;

  // Recursively collect all paths up to AUTO_EXPAND_DEPTH
  function collectExpandPaths(nodes, depth, out) {
    for (const node of nodes) {
      if (depth < AUTO_EXPAND_DEPTH) {
        out.add(node.full_path);
      }
      if (node.children?.length) {
        collectExpandPaths(node.children, depth + 1, out);
      }
    }
  }

  $effect(() => {
    if (categories.length > 0 && !initialized) {
      const paths = new Set();
      collectExpandPaths(categories, 0, paths);
      expandedPaths = paths;
      initialized = true;
    }
  });

  function toggleExpand(fullPath, event) {
    event.stopPropagation();
    const next = new Set(expandedPaths);
    if (next.has(fullPath)) {
      next.delete(fullPath);
    } else {
      next.add(fullPath);
    }
    expandedPaths = next;
  }

  // ── Context menu: Expand All / Collapse All (MDG right-click) ──
  let contextMenuVisible = $state(false);
  let contextMenuX = $state(0);
  let contextMenuY = $state(0);

  function handleContextMenu(event) {
    event.preventDefault();
    contextMenuX = event.clientX;
    contextMenuY = event.clientY;
    contextMenuVisible = true;
    // Close on next click anywhere
    const close = () => { contextMenuVisible = false; document.removeEventListener('click', close); };
    document.addEventListener('click', close);
  }

  function collectAllPaths(nodes, out) {
    for (const node of nodes) {
      out.add(node.full_path);
      if (node.children?.length) collectAllPaths(node.children, out);
    }
  }

  function expandAll() {
    const paths = new Set();
    collectAllPaths(categories, paths);
    expandedPaths = paths;
    contextMenuVisible = false;
  }

  function collapseAll() {
    // MDG: collapse all EXCEPT root categories (keep first level open)
    expandedPaths = new Set();
    contextMenuVisible = false;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<aside class="export-tree" aria-label="Audio categories" oncontextmenu={handleContextMenu}>
  <div class="tree-header">
    <span class="tree-title">Export Categories</span>
  </div>

  <!-- All root node (MDG: "All Audio (N)") -->
  <button
    class="tree-node"
    class:active={activeCategory === null}
    style="padding-left: 12px"
    onclick={() => onselect(null)}
    aria-label="All audio entries ({totalEvents})"
  >
    <span class="tree-spacer"></span>
    <span class="tree-name">All Audio</span>
    <span class="tree-count">{totalEvents.toLocaleString()}</span>
  </button>

  <!-- Truly recursive tree rendering (unlimited depth, like MDG _insert_children) -->
  {#snippet treeNode(node, depth)}
    {@const expanded = expandedPaths.has(node.full_path)}
    {@const hasKids = node.children && node.children.length > 0}
    <button
      class="tree-node"
      class:active={activeCategory === node.full_path}
      style="padding-left: {12 + depth * 16}px"
      onclick={() => onselect(node.full_path)}
    >
      {#if hasKids}
        <span
          class="tree-toggle"
          role="button"
          tabindex="0"
          onclick={(e) => toggleExpand(node.full_path, e)}
          onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(node.full_path, e); } }}
        >
          {#if expanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
        </span>
      {:else}
        <span class="tree-spacer"></span>
      {/if}
      <span class="tree-name">{node.name}</span>
      <span class="tree-count">{node.count.toLocaleString()}</span>
    </button>

    {#if expanded && hasKids}
      <!-- MDG: sorted(children.keys()) — alphabetical sort at render time -->
      {#each [...node.children].sort((a, b) => a.name.localeCompare(b.name)) as child (child.full_path)}
        {@render treeNode(child, depth + 1)}
      {/each}
    {/if}
  {/snippet}

  <!-- MDG: root categories sorted alphabetically -->
  {#each [...categories].sort((a, b) => a.name.localeCompare(b.name)) as cat (cat.full_path)}
    {@render treeNode(cat, 0)}
  {/each}
</aside>

<!-- Context menu (MDG: right-click Expand All / Collapse All) -->
{#if contextMenuVisible}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="context-menu" style="left: {contextMenuX}px; top: {contextMenuY}px">
    <button class="context-item" onclick={expandAll}>Expand All</button>
    <button class="context-item" onclick={collapseAll}>Collapse All</button>
  </div>
{/if}

<style>
  .export-tree {
    width: 100%;
    height: 100%;
    background: var(--cds-layer-01);
    overflow-y: auto;
    overflow-x: auto; /* MDG: horizontal scrollbar for wide category names */
    display: flex;
    flex-direction: column;
  }

  .tree-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .tree-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    padding: 8px 12px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
    border-left: 3px solid transparent;
  }

  /* Depth handled via inline style: padding-left: 12 + depth*16 px */

  .tree-node:hover { background: var(--cds-layer-hover-01); color: var(--cds-text-01); }
  .tree-node:focus { outline: 2px solid var(--cds-focus); outline-offset: -2px; }
  .tree-node.active {
    background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1));
    color: var(--cds-text-01);
    border-left-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 500;
  }

  .tree-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--cds-text-03);
    cursor: pointer;
    flex-shrink: 0;
    width: 18px;
    height: 18px;
  }

  .tree-toggle:hover { color: var(--cds-text-01); }

  .tree-spacer {
    display: inline-block;
    width: 18px;
    flex-shrink: 0;
  }

  .tree-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tree-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  /* Context menu (MDG: right-click Expand All / Collapse All) */
  .context-menu {
    position: fixed;
    z-index: 9999;
    background: var(--cds-layer-02, #fff);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    min-width: 140px;
    padding: 4px 0;
  }

  .context-item {
    display: block;
    width: 100%;
    padding: 8px 16px;
    border: none;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    text-align: left;
    cursor: pointer;
  }

  .context-item:hover {
    background: var(--cds-layer-hover-01);
  }
</style>
