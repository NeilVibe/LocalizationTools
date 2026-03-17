<script>
  /**
   * MapDetailPanel.svelte - Fantasy-styled detail panel for selected world map node
   *
   * Right-side panel showing region info with warm copper/sepia aesthetic,
   * danger level badges, Korean names, NPC list, entity counts,
   * and Codex navigation links.
   *
   * Phase 38: Fantasy World Map (Plan 03)
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
        <h2 class="panel-title">{node.name_kr || node.name}</h2>
        {#if node.name_en}
          <span class="panel-subtitle">{node.name_en}</span>
        {/if}
        <div class="header-badges">
          <Tag type={TYPE_TAG_COLORS[node.region_type] || 'gray'} size="sm">
            {node.region_type}
          </Tag>
          {#if node.danger_level}
            <span class="danger-badge danger-{node.danger_level}">
              {#if node.danger_level === 1}Safe
              {:else if node.danger_level === 2}Moderate
              {:else}Dangerous
              {/if}
            </span>
          {/if}
        </div>
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
          {#each node.npcs as npc (npc)}
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
          {#each entityEntries as [type, count] (type)}
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
    background: linear-gradient(180deg, rgba(42, 31, 14, 0.95) 0%, rgba(26, 20, 8, 0.98) 100%);
    border-left: 1px solid rgba(212, 154, 92, 0.25);
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    transform: translateX(0);
    transition: transform 300ms cubic-bezier(0.25, 1, 0.5, 1);
  }

  .panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid rgba(212, 154, 92, 0.2);
    background: rgba(212, 154, 92, 0.05);
    flex-shrink: 0;
  }

  .header-info {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    flex: 1;
    min-width: 0;
  }

  .header-badges {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .panel-title {
    font-size: 1.125rem;
    font-weight: 700;
    color: rgba(240, 184, 120, 0.95);
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    margin: 0;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .panel-subtitle {
    font-size: 0.75rem;
    color: rgba(212, 154, 92, 0.6);
    font-style: italic;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: rgba(212, 154, 92, 0.6);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 150ms ease-out, background 150ms ease-out;
  }

  .close-btn:hover {
    color: rgba(240, 184, 120, 0.9);
    background: rgba(212, 154, 92, 0.1);
  }

  .close-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .panel-section {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid rgba(212, 154, 92, 0.1);
  }

  .section-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(212, 154, 92, 0.7);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 0.5rem 0;
  }

  .section-text {
    margin: 0;
    font-size: 0.8125rem;
    color: rgba(240, 184, 120, 0.75);
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
    color: rgba(240, 184, 120, 0.8);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background 0.15s ease-out, color 0.15s ease-out;
    word-break: break-word;
    overflow-wrap: break-word;
  }

  .npc-link:hover {
    color: rgba(240, 184, 120, 1);
    background: rgba(212, 154, 92, 0.1);
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
    background: rgba(212, 154, 92, 0.08);
    border: 1px solid rgba(212, 154, 92, 0.15);
    border-radius: 0.25rem;
    color: rgba(240, 184, 120, 0.75);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background 0.15s ease-out, border-color 0.15s ease-out;
  }

  .entity-count-item:hover {
    background: rgba(212, 154, 92, 0.15);
    border-color: rgba(212, 154, 92, 0.3);
  }

  .entity-count-item:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .count-number {
    font-weight: 700;
    font-size: 0.875rem;
    color: rgba(240, 184, 120, 0.9);
  }

  .count-type {
    text-transform: capitalize;
  }

  .danger-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    border-radius: 10px;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .danger-1 {
    background: rgba(36, 161, 72, 0.15);
    color: #24a148;
    border: 1px solid rgba(36, 161, 72, 0.3);
  }

  .danger-2 {
    background: rgba(241, 194, 27, 0.15);
    color: #f1c21b;
    border: 1px solid rgba(241, 194, 27, 0.3);
  }

  .danger-3 {
    background: rgba(218, 30, 40, 0.15);
    color: #da1e28;
    border: 1px solid rgba(218, 30, 40, 0.3);
  }

  .coordinates {
    display: flex;
    gap: 1rem;
    font-size: 0.8125rem;
    color: rgba(212, 154, 92, 0.6);
    font-family: monospace;
  }

  .panel-footer {
    padding: 1rem;
    flex-shrink: 0;
    margin-top: auto;
  }
</style>
