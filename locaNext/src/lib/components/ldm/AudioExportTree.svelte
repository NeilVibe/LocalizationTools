<script>
  /**
   * AudioExportTree.svelte - Category hierarchy sidebar for Audio Codex
   *
   * MDG-exact behavior: hierarchical export_path tree with collapsible nodes,
   * count badges, auto-expand first 2 levels. Props-driven, stateless.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { ChevronRight, ChevronDown } from "carbon-icons-svelte";

  let {
    categories = [],
    activeCategory = null,
    totalEvents = 0,
    onselect = () => {},
  } = $props();

  // Track expanded nodes — auto-expand first 2 levels on mount
  let expandedPaths = $state(new Set());
  let initialized = false; // Plain var, NOT $state — avoids $effect re-trigger

  $effect(() => {
    if (categories.length > 0 && !initialized) {
      const paths = new Set();
      for (const cat of categories) {
        paths.add(cat.full_path);
        if (cat.children) {
          for (const child of cat.children) {
            paths.add(child.full_path);
          }
        }
      }
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

</script>

<aside class="export-tree" aria-label="Audio categories">
  <div class="tree-header">
    <span class="tree-title">Categories</span>
  </div>

  <!-- All root node -->
  <button
    class="tree-node depth-0"
    class:active={activeCategory === null}
    onclick={() => onselect(null)}
    aria-label="All audio entries ({totalEvents})"
  >
    <span class="tree-spacer"></span>
    <span class="tree-name">All</span>
    <span class="tree-count">{totalEvents}</span>
  </button>

  <!-- Recursive tree rendering (3 levels max like MDG) -->
  {#each categories as cat (cat.full_path)}
    {@const expanded = expandedPaths.has(cat.full_path)}
    {@const hasKids = cat.children && cat.children.length > 0}
    <button
      class="tree-node depth-0"
      class:active={activeCategory === cat.full_path}
      onclick={() => onselect(cat.full_path)}
    >
      {#if hasKids}
        <span
          class="tree-toggle"
          role="button"
          tabindex="0"
          onclick={(e) => toggleExpand(cat.full_path, e)}
          onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(cat.full_path, e); } }}
        >
          {#if expanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
        </span>
      {:else}
        <span class="tree-spacer"></span>
      {/if}
      <span class="tree-name">{cat.name}</span>
      <span class="tree-count">{cat.count}</span>
    </button>

    {#if expanded && hasKids}
      {#each cat.children as child (child.full_path)}
        {@const childExpanded = expandedPaths.has(child.full_path)}
        {@const childHasKids = child.children && child.children.length > 0}
        <button
          class="tree-node depth-1"
          class:active={activeCategory === child.full_path}
          onclick={() => onselect(child.full_path)}
        >
          {#if childHasKids}
            <span
              class="tree-toggle"
              role="button"
              tabindex="0"
              onclick={(e) => toggleExpand(child.full_path, e)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(child.full_path, e); } }}
            >
              {#if childExpanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
            </span>
          {:else}
            <span class="tree-spacer"></span>
          {/if}
          <span class="tree-name">{child.name}</span>
          <span class="tree-count">{child.count}</span>
        </button>

        {#if childExpanded && childHasKids}
          {#each child.children as grandchild (grandchild.full_path)}
            <button
              class="tree-node depth-2"
              class:active={activeCategory === grandchild.full_path}
              onclick={() => onselect(grandchild.full_path)}
            >
              <span class="tree-spacer"></span>
              <span class="tree-name">{grandchild.name}</span>
              <span class="tree-count">{grandchild.count}</span>
            </button>
          {/each}
        {/if}
      {/each}
    {/if}
  {/each}
</aside>

<style>
  .export-tree {
    width: 100%;
    height: 100%;
    background: var(--cds-layer-01);
    overflow-y: auto;
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

  .tree-node.depth-0 { padding-left: 12px; }
  .tree-node.depth-1 { padding-left: 28px; }
  .tree-node.depth-2 { padding-left: 44px; }

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
</style>
