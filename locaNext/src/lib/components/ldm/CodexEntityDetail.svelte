<script>
  /**
   * CodexEntityDetail.svelte - Entity detail card with metadata, media, related entities
   *
   * Renders full entity details including type-specific attributes,
   * inline DDS-to-PNG image thumbnails, WEM-to-WAV audio playback,
   * and similar/related entity links.
   *
   * Phase 19: Game World Codex (Plan 02)
   */
  import { Tag, InlineLoading } from "carbon-components-svelte";
  import { Music } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import PlaceholderImage from "./PlaceholderImage.svelte";
  import PlaceholderAudio from "./PlaceholderAudio.svelte";

  const API_BASE = getApiBase();

  // Props
  let { entity = null, onsimilar = () => {} } = $props();

  // State
  let imageError = $state(false);
  let similarItems = $state([]);
  let loadingSimilar = $state(false);

  // Type badge colors
  const TYPE_COLORS = {
    character: 'purple',
    item: 'cyan',
    skill: 'magenta',
    region: 'teal',
    gimmick: 'warm-gray'
  };

  // Character-specific attribute labels
  const CHARACTER_ATTRS = ['Race', 'Job', 'Gender', 'Age'];
  // Item-specific attribute labels
  const ITEM_ATTRS = ['ItemType', 'Grade'];

  /**
   * Build image URL from texture name
   */
  let imageUrl = $derived(
    entity?.image_texture
      ? `${API_BASE}/api/ldm/mapdata/thumbnail/${entity.image_texture}`
      : null
  );

  /**
   * Build audio URL from audio key
   */
  let audioUrl = $derived(
    entity?.audio_key
      ? `${API_BASE}/api/ldm/mapdata/audio/stream/${entity.audio_key}`
      : null
  );

  /**
   * Get attribute entries, filtering out empty values
   */
  let attributeEntries = $derived(
    entity?.attributes
      ? Object.entries(entity.attributes).filter(([_, v]) => v != null && v !== '')
      : []
  );

  /**
   * Render description with br-tag handling
   */
  function renderDescription(desc) {
    if (!desc) return '';
    // Replace <br/> tags with actual line breaks for display
    return desc.replace(/<br\s*\/?>/gi, '\n');
  }

  /**
   * Fetch similar items (for item entities)
   */
  async function fetchSimilarItems() {
    if (!entity || entity.entity_type !== 'item' || !entity.name) return;

    loadingSimilar = true;
    try {
      const params = new URLSearchParams({
        q: entity.name,
        entity_type: 'item',
        limit: '5'
      });
      const response = await fetch(`${API_BASE}/api/ldm/codex/search?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        // Filter out the current entity from results
        similarItems = (data.results || []).filter(r => r.entity.strkey !== entity.strkey);
      }
    } catch (err) {
      logger.error('Failed to fetch similar items', { error: err.message });
    } finally {
      loadingSimilar = false;
    }
  }

  // Fetch similar items when entity changes (for items only)
  $effect(() => {
    if (entity?.entity_type === 'item') {
      fetchSimilarItems();
    } else {
      similarItems = [];
    }
  });

  // Reset image error when entity changes
  $effect(() => {
    if (entity) {
      imageError = false;
    }
  });
</script>

{#if entity}
  <div class="entity-detail">
    <div class="detail-layout">
      <!-- Left: Image -->
      <div class="detail-image">
        {#if imageUrl && !imageError}
          <img
            src={imageUrl}
            alt={entity.name}
            class="entity-image"
            onerror={() => { imageError = true; }}
          />
        {:else}
          <PlaceholderImage entityType={entity.entity_type} entityName={entity.name} />
        {/if}
      </div>

      <!-- Right: Metadata -->
      <div class="detail-meta">
        <div class="detail-header">
          <h2 class="entity-name">{entity.name}</h2>
          <Tag type={TYPE_COLORS[entity.entity_type] || 'gray'} size="sm">
            {entity.entity_type}
          </Tag>
        </div>

        {#if entity.description}
          <p class="entity-description">{renderDescription(entity.description)}</p>
        {/if}

        <!-- Character-specific attributes -->
        {#if entity.entity_type === 'character'}
          <div class="attr-grid">
            {#each CHARACTER_ATTRS as attr}
              {#if entity.attributes?.[attr]}
                <div class="attr-item">
                  <span class="attr-label">{attr}</span>
                  <span class="attr-value">{entity.attributes[attr]}</span>
                </div>
              {/if}
            {/each}
          </div>
        {/if}

        <!-- Item-specific attributes -->
        {#if entity.entity_type === 'item'}
          <div class="attr-grid">
            {#each ITEM_ATTRS as attr}
              {#if entity.attributes?.[attr]}
                <div class="attr-item">
                  <span class="attr-label">{attr}</span>
                  <span class="attr-value">{entity.attributes[attr]}</span>
                </div>
              {/if}
            {/each}
          </div>
        {/if}

        <!-- Generic attributes for skill/region/gimmick -->
        {#if entity.entity_type !== 'character' && entity.entity_type !== 'item' && attributeEntries.length > 0}
          <div class="attr-list">
            {#each attributeEntries as [key, value] (key)}
              <div class="attr-row">
                <span class="attr-label">{key}</span>
                <span class="attr-value">{value}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Audio section -->
    <div class="detail-section">
      {#if audioUrl}
        <div class="audio-section">
          <div class="section-header">
            <Music size={16} />
            <span>Audio</span>
          </div>
          <audio controls preload="none" class="audio-player">
            <source src={audioUrl} />
            Your browser does not support the audio element.
          </audio>
        </div>
      {:else}
        <PlaceholderAudio entityName={entity.name} />
      {/if}
    </div>

    <!-- Similar Items (item entities only) -->
    {#if entity.entity_type === 'item'}
      <div class="detail-section">
        <div class="section-header">
          <span>Similar Items</span>
        </div>
        {#if loadingSimilar}
          <InlineLoading description="Finding similar..." />
        {:else if similarItems.length > 0}
          <div class="related-list">
            {#each similarItems as result (result.entity.strkey)}
              <button
                class="related-badge"
                onclick={() => onsimilar(result.entity.strkey)}
              >
                {result.entity.name}
                <span class="similarity">{(result.similarity * 100).toFixed(0)}%</span>
              </button>
            {/each}
          </div>
        {:else}
          <span class="no-related">No similar items found</span>
        {/if}
      </div>
    {/if}

    <!-- Related Entities -->
    {#if entity.related_entities && entity.related_entities.length > 0}
      <div class="detail-section">
        <div class="section-header">
          <span>Related Entities</span>
        </div>
        <div class="related-list">
          {#each entity.related_entities as relatedKey (relatedKey)}
            <button
              class="related-badge"
              onclick={() => onsimilar(relatedKey)}
            >
              {relatedKey}
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Source file -->
    {#if entity.source_file}
      <span class="source-file">Source: {entity.source_file}</span>
    {/if}
  </div>
{/if}

<style>
  .entity-detail {
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

  .entity-description {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    margin: 0;
    white-space: pre-line;
  }

  .attr-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
    margin-top: 4px;
  }

  .attr-item, .attr-row {
    display: flex;
    gap: 8px;
    font-size: 0.8125rem;
  }

  .attr-label {
    color: var(--cds-text-03);
    min-width: 60px;
    flex-shrink: 0;
    font-weight: 500;
  }

  .attr-value {
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .attr-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 4px;
  }

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

  .audio-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .audio-player {
    width: 100%;
    height: 32px;
    filter: invert(1) hue-rotate(180deg);
    opacity: 0.85;
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

  .similarity {
    color: var(--cds-text-03);
    font-size: 0.6875rem;
  }

  .no-related {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  .source-file {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    word-break: break-all;
  }
</style>
