<script>
  /**
   * CharacterCodexDetail.svelte - Character detail panel with knowledge resolution tabs
   *
   * Shows character metadata (Race/Gender/Age/Job), DDS image, and tabbed knowledge resolution:
   * - Knowledge tab: Pass 0 (shared key siblings) + Pass 1 (direct key)
   * - Related tab: Pass 2 (name-matched knowledge)
   * - Attributes tab: use_macro raw value
   * - Info tab: Technical metadata (strkey, knowledge key, source file, use_macro)
   *
   * Phase 47: Character Codex UI (Plan 02)
   */
  import { Tag } from "carbon-components-svelte";
  import { getApiBase } from "$lib/utils/api.js";
  import PlaceholderImage from "$lib/components/ldm/PlaceholderImage.svelte";

  const API_BASE = getApiBase();

  // Props
  let { character = null, onback = () => {}, onsimilar = () => {} } = $props();

  // State
  let activeTab = $state("knowledge");
  let imageError = $state(false);

  // Reset state when character changes
  $effect(() => {
    if (character) {
      activeTab = "knowledge";
      imageError = false;
    }
  });

  // Derived tab counts
  let knowledgeCount = $derived(
    (character?.knowledge_pass_0?.length || 0) + (character?.knowledge_pass_1?.length || 0)
  );
  let relatedCount = $derived(character?.knowledge_pass_2?.length || 0);
  let attributeCount = $derived(character?.use_macro ? 1 : 0);

  // Tab definitions
  let tabs = $derived([
    { id: "knowledge", label: "Knowledge", count: knowledgeCount },
    { id: "related", label: "Related", count: relatedCount },
    { id: "attributes", label: "Attributes", count: attributeCount },
    { id: "info", label: "Info", count: null }
  ]);

  /**
   * Render description with br-tag handling
   */
  function renderDescription(desc) {
    if (!desc) return '';
    return desc.replace(/<br\s*\/?>/gi, '\n');
  }

  /**
   * Strip known prefixes from attribute values for cleaner display
   */
  function stripPrefix(value, prefix) {
    if (!value) return '';
    if (value.startsWith(prefix)) return value.slice(prefix.length);
    return value;
  }
</script>

{#if character}
  <div class="character-detail">
    <!-- Top: Image + Metadata -->
    <div class="detail-layout">
      <!-- Left: Image -->
      <div class="detail-image">
        {#if character.image_url && !imageError}
          <img
            src="{API_BASE}{character.image_url}?v={Date.now()}"
            alt={character.name_kr}
            class="entity-image"
            onerror={() => { imageError = true; }}
          />
        {:else}
          <div class="placeholder-wrapper">
            <PlaceholderImage entityType="character" entityName={character.name_kr} />
          </div>
        {/if}
      </div>

      <!-- Right: Metadata -->
      <div class="detail-meta">
        <div class="detail-header">
          <h2 class="entity-name">{character.name_kr}</h2>
          <Tag type="teal" size="sm">character</Tag>
        </div>

        {#if character.name_translated}
          <p class="entity-subtitle">{character.name_translated}</p>
        {/if}

        {#if character.desc_kr}
          <p class="entity-description">{renderDescription(character.desc_kr)}</p>
        {/if}

        <!-- Character-specific metadata badges -->
        <div class="meta-badges">
          {#if character.category}
            <div class="meta-row">
              <span class="meta-label">Category</span>
              <Tag type="magenta" size="sm">{character.category}</Tag>
            </div>
          {/if}
          {#if character.race}
            <div class="meta-row">
              <span class="meta-label">Race</span>
              <Tag type="teal" size="sm">{character.race}</Tag>
            </div>
          {/if}
          {#if character.gender}
            <div class="meta-row">
              <span class="meta-label">Gender</span>
              <Tag type="purple" size="sm">{character.gender}</Tag>
            </div>
          {/if}
          {#if character.age}
            <div class="meta-row">
              <span class="meta-label">Age</span>
              <Tag type="warm-gray" size="sm">{stripPrefix(character.age, 'Age_')}</Tag>
            </div>
          {/if}
          {#if character.job}
            <div class="meta-row">
              <span class="meta-label">Job</span>
              <Tag type="cyan" size="sm">{stripPrefix(character.job, 'Job_')}</Tag>
            </div>
          {/if}
        </div>
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
          {#if character.knowledge_pass_0 && character.knowledge_pass_0.length > 0}
            <div class="pass-section">
              <h4 class="pass-header">Pass 0 -- Shared Key Siblings</h4>
              {#each character.knowledge_pass_0 as entry, i (i)}
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
          {#if character.knowledge_pass_1 && character.knowledge_pass_1.length > 0}
            <div class="pass-section">
              <h4 class="pass-header">Pass 1 -- Direct KnowledgeKey</h4>
              {#each character.knowledge_pass_1 as entry, i (i)}
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
          {#each character.knowledge_pass_2 as entry, i (i)}
            <div class="knowledge-card">
              <span class="knowledge-name">{entry.name}</span>
              {#if entry.desc}
                <span class="knowledge-desc">{renderDescription(entry.desc)}</span>
              {/if}
              <span class="knowledge-source">{entry.source}</span>
            </div>
          {/each}
        {/if}
      {:else if activeTab === "attributes"}
        {#if attributeCount === 0}
          <p class="no-entries">No attribute data available</p>
        {:else}
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Use Macro</span>
              <span class="info-value source-file">{character.use_macro}</span>
            </div>
          </div>
        {/if}
      {:else if activeTab === "info"}
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">StrKey</span>
            <span class="info-value">{character.strkey}</span>
          </div>
          {#if character.knowledge_key}
            <div class="info-row">
              <span class="info-label">Knowledge Key</span>
              <span class="info-value">{character.knowledge_key}</span>
            </div>
          {/if}
          {#if character.source_file}
            <div class="info-row">
              <span class="info-label">Source File</span>
              <span class="info-value source-file">{character.source_file}</span>
            </div>
          {/if}
          {#if character.use_macro}
            <div class="info-row">
              <span class="info-label">Use Macro</span>
              <span class="info-value source-file">{character.use_macro}</span>
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Related Entities -->
    {#if character.related_entities && character.related_entities.length > 0}
      <div class="detail-section">
        <div class="section-header">
          <span>Related Entities</span>
        </div>
        <div class="related-list">
          {#each character.related_entities as relatedKey (relatedKey)}
            <button
              class="related-badge"
              onclick={() => onsimilar(relatedKey)}
              aria-label="View related entity: {relatedKey}"
            >
              {relatedKey}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .character-detail {
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
    width: 160px;
    min-height: 120px;
    max-height: 160px;
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

  .entity-description {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    margin: 0;
    white-space: pre-line;
    overflow-wrap: break-word;
  }

  .meta-badges {
    display: flex;
    flex-direction: column;
    gap: 4px;
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
    min-width: 60px;
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
    min-height: 80px;
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
    gap: 4px;
    padding: 4px 10px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 12px;
    color: var(--cds-text-01);
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s;
  }

  .related-badge:hover {
    background: var(--cds-layer-hover-02);
  }

  .related-badge:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }
</style>
