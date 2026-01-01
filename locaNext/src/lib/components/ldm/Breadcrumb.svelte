<script>
  /**
   * Breadcrumb.svelte - Phase 10 UI Overhaul
   *
   * Windows/SharePoint style breadcrumb navigation.
   * Shows current path and allows clicking to navigate back.
   */
  import { createEventDispatcher } from 'svelte';
  import { ChevronRight, Home } from 'carbon-icons-svelte';

  // Props
  let {
    path = []  // Array of { type, id, name } items
  } = $props();

  const dispatch = createEventDispatcher();

  /**
   * Navigate to a specific breadcrumb item
   */
  function navigateTo(index) {
    const item = path[index];
    dispatch('navigate', { index, item, path: path.slice(0, index + 1) });
  }

  /**
   * Navigate to root (Projects)
   */
  function navigateToRoot() {
    dispatch('navigate', { index: -1, item: null, path: [] });
  }
</script>

<nav class="breadcrumb" aria-label="File navigation">
  <ol class="breadcrumb-list">
    <!-- Root/Home -->
    <li class="breadcrumb-item">
      <button
        class="breadcrumb-link root"
        onclick={navigateToRoot}
        title="Go to Projects"
      >
        <Home size={16} />
        <span>Projects</span>
      </button>
    </li>

    <!-- Path items -->
    {#each path as item, index}
      <li class="breadcrumb-item">
        <ChevronRight size={16} class="breadcrumb-separator" />
        {#if index === path.length - 1}
          <!-- Current location (not clickable) -->
          <span class="breadcrumb-current">{item.name}</span>
        {:else}
          <!-- Navigable parent -->
          <button
            class="breadcrumb-link"
            onclick={() => navigateTo(index)}
            title="Go to {item.name}"
          >
            {item.name}
          </button>
        {/if}
      </li>
    {/each}
  </ol>
</nav>

<style>
  .breadcrumb {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .breadcrumb-list {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .breadcrumb-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .breadcrumb-link {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.5rem;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-link-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .breadcrumb-link:hover {
    background: var(--cds-layer-hover-01);
    text-decoration: underline;
  }

  .breadcrumb-link:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 2px;
  }

  .breadcrumb-link.root {
    color: var(--cds-text-01);
  }

  .breadcrumb-link.root:hover {
    color: var(--cds-link-primary);
  }

  .breadcrumb-separator {
    color: var(--cds-text-02);
    flex-shrink: 0;
  }

  .breadcrumb-current {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }
</style>
