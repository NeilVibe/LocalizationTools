<script>
  /**
   * MapDetailPanel.svelte - Detail panel for selected world map node
   *
   * Right-side panel showing region info, NPC list, entity counts,
   * and Codex navigation links.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  import { Tag, Button } from "carbon-components-svelte";
  import { Close, Book } from "carbon-icons-svelte";
  import { goToCodex } from "$lib/stores/navigation.js";

  let { node = null, onClose = () => {} } = $props();

  // Region type colors for Carbon Tag
  const TYPE_TAG_COLORS = {
    Main: 'blue',
    Sub: 'cyan',
    Dungeon: 'red',
    Town: 'green',
    Fortress: 'purple',
    Wilderness: 'teal'
  };

  /**
   * Clean description (replace br tags with line breaks)
   */
  function cleanDescription(text) {
    if (!text) return '';
    return text.replace(/<br\s*\/?>/gi, '\n');
  }

  /**
   * Navigate to Codex page
   */
  function openInCodex() {
    goToCodex();
  }

  /**
   * Navigate to Codex for a specific NPC
   */
  function navigateToNPC(npcName) {
    goToCodex(npcName);
  }

  /**
   * Format entity type counts as entries
   */
  let entityEntries = $derived(
    node?.entity_type_counts
      ? Object.entries(node.entity_type_counts).filter(([, count]) => count > 0)
      : []
  );
</script>

{#if node}
  <div class="map-detail-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-info">
        <h2 class="panel-title">{node.name}</h2>
        <Tag type={TYPE_TAG_COLORS[node.region_type] || 'gray'} size="sm">
          {node.region_type}
        </Tag>
      </div>
      <button class="close-btn" onclick={onClose} aria-label="Close panel">
        <Close size={20} />
      </button>
    </div>

    <!-- Description -->
    {#if node.description}
      <div class="panel-section">
        <h3 class="section-title">Description</h3>
        <p class="section-text">{cleanDescription(node.description)}</p>
      </div>
    {/if}

    <!-- NPCs -->
    {#if node.npcs && node.npcs.length > 0}
      <div class="panel-section">
        <h3 class="section-title">NPCs ({node.npcs.length})</h3>
        <ul class="npc-list">
          {#each node.npcs as npc}
            <li>
              <button class="npc-link" onclick={() => navigateToNPC(npc)}>
                {npc}
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    <!-- Entity Counts -->
    {#if entityEntries.length > 0}
      <div class="panel-section">
        <h3 class="section-title">Entities</h3>
        <div class="entity-counts">
          {#each entityEntries as [type, count]}
            <button class="entity-count-item" onclick={openInCodex} aria-label="View {count} {type}{count !== 1 ? 's' : ''} in Codex">
              <span class="count-number">{count}</span>
              <span class="count-type">{type}{count !== 1 ? 's' : ''}</span>
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Coordinates -->
    <div class="panel-section">
      <h3 class="section-title">Position</h3>
      <div class="coordinates">
        <span>X: {node.x?.toFixed(1)}</span>
        <span>Z: {node.z?.toFixed(1)}</span>
      </div>
    </div>

    <!-- Open in Codex Button -->
    <div class="panel-footer">
      <Button
        kind="primary"
        size="small"
        icon={Book}
        onclick={openInCodex}
      >
        Open in Codex
      </Button>
    </div>
  </div>
{/if}

<style>
  .map-detail-panel {
    width: 320px;
    background: var(--cds-layer-01, #262626);
    border-left: 1px solid var(--cds-border-subtle-01, #353535);
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }

  .panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .header-info {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    flex: 1;
    min-width: 0;
  }

  .panel-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
    margin: 0;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-btn:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .close-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .panel-section {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .section-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 0.5rem 0;
  }

  .section-text {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.5;
    white-space: pre-line;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .npc-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .npc-link {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    color: var(--cds-link-01, #78a9ff);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background 0.15s;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .npc-link:hover {
    background: var(--cds-layer-hover-01);
    text-decoration: underline;
  }

  .npc-link:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .entity-counts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .entity-count-item {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 0.25rem;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .entity-count-item:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-interactive-01, #0f62fe);
  }

  .entity-count-item:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .count-number {
    font-weight: 700;
    font-size: 0.875rem;
    color: var(--cds-interactive-01, #0f62fe);
  }

  .count-type {
    text-transform: capitalize;
  }

  .coordinates {
    display: flex;
    gap: 1rem;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    font-family: monospace;
  }

  .panel-footer {
    padding: 1rem;
    flex-shrink: 0;
    margin-top: auto;
  }
</style>
