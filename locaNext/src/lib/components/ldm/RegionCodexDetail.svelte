<script>
  /**
   * RegionCodexDetail.svelte - Region detail panel with knowledge tabs
   *
   * Shows region metadata (name, node_type, WorldPosition, faction breadcrumb),
   * image, description, and tabbed knowledge resolution passes.
   *
   * Phase 49: Region Codex UI + Interactive Map (Plan 02)
   */
  import { Tag } from "carbon-components-svelte";
  import { getApiBase } from "$lib/utils/api.js";
  import PlaceholderImage from "$lib/components/ldm/PlaceholderImage.svelte";

  const API_BASE = getApiBase();

  // Props
  let { region = null, onback = () => {} } = $props();

  // State
  let activeTab = $state("knowledge");
  let imageError = $state(false);

  // Reset state when region changes
  $effect(() => {
    if (region) {
      activeTab = "knowledge";
      imageError = false;
    }
  });

  // Node type color mapping
  const NODE_TYPE_COLORS = {
    Main: 'blue',
    Sub: 'teal',
    Dungeon: 'red',
    Town: 'green',
    Fortress: 'purple',
    Wilderness: 'cyan'
  };

  function getTagType(nodeType) {
    return NODE_TYPE_COLORS[nodeType] || 'warm-gray';
  }

  // Derived tab counts
  let knowledgeCount = $derived(
    (region?.knowledge_pass_0?.length || 0) + (region?.knowledge_pass_1?.length || 0)
  );
  let relatedCount = $derived(region?.knowledge_pass_2?.length || 0);

  // Tab definitions
  let tabs = $derived([
    { id: "knowledge", label: "Knowledge", count: knowledgeCount },
    { id: "related", label: "Related", count: relatedCount },
    { id: "info", label: "Info", count: null }
  ]);

  /**
   * Format WorldPosition to 1 decimal
   */
  function formatPosition(pos) {
    if (!pos || pos.length < 3) return null;
    return `(${pos[0].toFixed(1)}, ${pos[1].toFixed(1)}, ${pos[2].toFixed(1)})`;
  }

  /**
   * Render description with br-tag handling
   */
  function renderDescription(desc) {
    if (!desc) return '';
    return desc.replace(/<br\s*\/?>/gi, '\n');
  }
</script>

{#if region}
  <div class="region-detail">
    <!-- Top: Image + Metadata -->
    <div class="detail-layout">
      <!-- Left: Image -->
      <div class="detail-image">
        {#if region.image_url && !imageError}
          <img
            src="{API_BASE}{region.image_url}?v={Date.now()}"
            alt={region.name_kr}
            class="entity-image"
            onerror={() => { imageError = true; }}
          />
        {:else}
          <div class="placeholder-wrapper">
            <PlaceholderImage entityType="region" entityName={region.name_kr} />
          </div>
        {/if}
      </div>

      <!-- Right: Metadata -->
      <div class="detail-meta">
        <div class="detail-header">
          <h2 class="entity-name">{region.display_name || region.name_kr}</h2>
          {#if region.node_type}
            <Tag type={getTagType(region.node_type)} size="sm">{region.node_type}</Tag>
          {/if}
        </div>

        {#if region.name_translated}
          <p class="entity-subtitle">{region.name_translated}</p>
        {/if}

        <!-- Faction breadcrumb -->
        {#if region.faction_group_name || region.faction_name}
          <div class="faction-breadcrumb">
            {#if region.faction_group_name}
              <span class="breadcrumb-segment">{region.faction_group_name}</span>
            {/if}
            {#if region.faction_group_name && region.faction_name}
              <span class="breadcrumb-separator">&gt;</span>
            {/if}
            {#if region.faction_name}
              <span class="breadcrumb-segment">{region.faction_name}</span>
            {/if}
          </div>
        {/if}

        <!-- WorldPosition -->
        {#if region.world_position}
          <div class="meta-row">
            <span class="meta-label">Position</span>
            <span class="meta-value mono">{formatPosition(region.world_position)}</span>
          </div>
        {/if}

        {#if region.desc_kr}
          <p class="entity-description">{renderDescription(region.desc_kr)}</p>
        {/if}
      </div>
    </div>

    <!-- Knowledge Resolution Tabs -->
    <div class="knowledge-tabs" role="tablist" aria-label="Knowledge resolution tabs">
      {#each tabs as tab (tab.id)}
        <button
          class="knowledge-tab"
          class:active={activeTab === tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          onclick={() => { activeTab = tab.id; }}
        >
          {tab.label}
          {#if tab.count !== null}
            <span class="tab-count">({tab.count})</span>
          {/if}
        </button>
      {/each}
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      {#if activeTab === "knowledge"}
        {#if knowledgeCount === 0}
          <p class="no-entries">No knowledge entries</p>
        {:else}
          {#if region.knowledge_pass_0 && region.knowledge_pass_0.length > 0}
            <div class="pass-section">
              <h4 class="pass-header">Pass 0 -- Shared Key Siblings</h4>
              {#each region.knowledge_pass_0 as entry, i (i)}
                <div class="knowledge-card">
                  <span class="knowledge-name">{entry.name}</span>
                  {#if entry.desc}
                    <span class="knowledge-desc">{renderDescription(entry.desc)}</span>
                  {/if}
                  <span class="knowledge-source">{entry.source}</span>
                </div>
              {/each}
            </div>
          {/if}
          {#if region.knowledge_pass_1 && region.knowledge_pass_1.length > 0}
            <div class="pass-section">
              <h4 class="pass-header">Pass 1 -- Direct KnowledgeKey</h4>
              {#each region.knowledge_pass_1 as entry, i (i)}
                <div class="knowledge-card">
                  <span class="knowledge-name">{entry.name}</span>
                  {#if entry.desc}
                    <span class="knowledge-desc">{renderDescription(entry.desc)}</span>
                  {/if}
                  <span class="knowledge-source">{entry.source}</span>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      {:else if activeTab === "related"}
        {#if relatedCount === 0}
          <p class="no-entries">No related knowledge entries</p>
        {:else}
          {#each region.knowledge_pass_2 as entry, i (i)}
            <div class="knowledge-card">
              <span class="knowledge-name">{entry.name}</span>
              {#if entry.desc}
                <span class="knowledge-desc">{renderDescription(entry.desc)}</span>
              {/if}
              <span class="knowledge-source">{entry.source}</span>
            </div>
          {/each}
        {/if}
      {:else if activeTab === "info"}
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">StrKey</span>
            <span class="info-value">{region.strkey}</span>
          </div>
          {#if region.knowledge_key}
            <div class="info-row">
              <span class="info-label">Knowledge Key</span>
              <span class="info-value">{region.knowledge_key}</span>
            </div>
          {/if}
          {#if region.node_type}
            <div class="info-row">
              <span class="info-label">Node Type</span>
              <span class="info-value">{region.node_type}</span>
            </div>
          {/if}
          {#if region.faction_name}
            <div class="info-row">
              <span class="info-label">Faction</span>
              <span class="info-value">{region.faction_name}</span>
            </div>
          {/if}
          {#if region.faction_group_name}
            <div class="info-row">
              <span class="info-label">Faction Group</span>
              <span class="info-value">{region.faction_group_name}</span>
            </div>
          {/if}
          {#if region.world_position}
            <div class="info-row">
              <span class="info-label">World Position</span>
              <span class="info-value mono">{formatPosition(region.world_position)}</span>
            </div>
          {/if}
          {#if region.source_file}
            <div class="info-row">
              <span class="info-label">Source File</span>
              <span class="info-value source-file">{region.source_file}</span>
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Related Entities -->
    {#if region.related_entities && region.related_entities.length > 0}
      <div class="detail-section">
        <div class="section-header">
          <span>Related Entities ({region.related_entities.length})</span>
        </div>
        <div class="related-list">
          {#each region.related_entities as relatedKey (relatedKey)}
            <span class="related-badge">{relatedKey}</span>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .region-detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .detail-layout {
    display: flex;
    gap: 16px;
  }

  .detail-image {
    flex-shrink: 0;
    width: 140px;
    min-height: 100px;
    max-height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
    overflow: hidden;
  }

  .entity-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .placeholder-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  .detail-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .detail-header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .entity-name {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--cds-text-01);
    margin: 0;
    word-break: break-word;
  }

  .entity-subtitle {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin: 0;
    font-style: italic;
  }

  .faction-breadcrumb {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .breadcrumb-separator {
    color: var(--cds-text-03);
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8125rem;
  }

  .meta-label {
    color: var(--cds-text-03);
    font-weight: 500;
  }

  .meta-value.mono {
    font-family: monospace;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .entity-description {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    margin: 0;
    white-space: pre-line;
    overflow-wrap: break-word;
  }

  /* Knowledge Tabs */
  .knowledge-tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid var(--cds-border-subtle-01);
  }

  .knowledge-tab {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 14px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    white-space: nowrap;
    transition: all 0.15s;
  }

  .knowledge-tab:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .knowledge-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .knowledge-tab.active {
    color: var(--cds-text-01);
    border-bottom-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 600;
  }

  .tab-count {
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .tab-content {
    min-height: 60px;
  }

  .no-entries {
    color: var(--cds-text-03);
    font-size: 0.8125rem;
    font-style: italic;
    padding: 12px 0;
    margin: 0;
  }

  /* Knowledge Cards */
  .pass-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
  }

  .pass-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .knowledge-card {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 12px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
  }

  .knowledge-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .knowledge-desc {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    line-height: 1.4;
    white-space: pre-line;
  }

  .knowledge-source {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    word-break: break-all;
  }

  /* Info Tab */
  .info-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .info-row {
    display: flex;
    gap: 12px;
    font-size: 0.8125rem;
  }

  .info-label {
    color: var(--cds-text-03);
    min-width: 110px;
    flex-shrink: 0;
    font-weight: 500;
  }

  .info-value {
    color: var(--cds-text-01);
    word-break: break-all;
  }

  .source-file {
    font-family: monospace;
    font-size: 0.75rem;
  }

  /* Related Entities */
  .detail-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .related-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .related-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 12px;
    color: var(--cds-text-01);
    font-size: 0.75rem;
  }
</style>
