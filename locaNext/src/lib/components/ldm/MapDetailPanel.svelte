<script>
  /**
   * MapDetailPanel.svelte - Detail panel for selected world map node
   *
   * Right-side panel showing region info with Codex navigation links.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  let { node = null, onClose = () => {} } = $props();
</script>

{#if node}
  <div class="map-detail-panel">
    <div class="panel-header">
      <span class="panel-title">{node.name}</span>
      <button class="close-btn" onclick={onClose}>X</button>
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
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .panel-title {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .close-btn {
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 4px 8px;
  }

  .close-btn:hover {
    color: var(--cds-text-01);
  }
</style>
