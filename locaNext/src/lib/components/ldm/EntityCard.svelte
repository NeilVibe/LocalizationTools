<script>
  /**
   * EntityCard.svelte - Reusable entity display card
   *
   * Shows entity metadata (character/location/item/skill) with optional
   * image thumbnail and audio player. Used by ContextTab.
   *
   * Phase 5.1: Contextual Intelligence & QA Engine (Plan 05)
   */
  import { Music } from "carbon-icons-svelte";
  import { Tag } from "carbon-components-svelte";

  // Props
  let { entity = null } = $props();

  // Type badge colors
  const TYPE_COLORS = {
    character: { kind: 'purple' },
    location: { kind: 'teal' },
    item: { kind: 'cyan' },
    skill: { kind: 'magenta' }
  };

  let tagKind = $derived(TYPE_COLORS[entity?.entity_type]?.kind || 'gray');

  // Metadata keys to display (filter out nulls/undefined)
  let metadataEntries = $derived(
    entity?.metadata
      ? Object.entries(entity.metadata).filter(([_, v]) => v != null && v !== '')
      : []
  );
</script>

<div class="entity-card" data-testid="entity-card">
  <!-- Header: name + type badge -->
  <div class="entity-header">
    <span class="entity-name">{entity?.name || 'Unknown'}</span>
    <Tag type={tagKind} size="sm">{entity?.entity_type || 'unknown'}</Tag>
  </div>

  <!-- Image thumbnail -->
  {#if entity?.image?.has_image && entity.image.thumbnail_url}
    <div class="entity-thumbnail">
      <img
        src={entity.image.thumbnail_url}
        alt={entity.image.texture_name || entity.name}
        class="thumbnail"
        onerror={(e) => { e.target.style.display = 'none'; }}
      />
    </div>
  {/if}

  <!-- Audio player -->
  {#if entity?.audio?.wem_path}
    <div class="entity-audio">
      <div class="audio-header">
        <Music size={12} />
        <span class="audio-event">{entity.audio.event_name || 'Audio'}</span>
      </div>
      <audio controls preload="none" class="audio-player">
        <source src={entity.audio.wem_path} />
        Your browser does not support the audio element.
      </audio>
      {#if entity.audio.script_kr || entity.audio.script_eng}
        <div class="audio-script">
          {#if entity.audio.script_kr}
            <p class="script-kr">{entity.audio.script_kr}</p>
          {/if}
          {#if entity.audio.script_eng}
            <p class="script-eng">{entity.audio.script_eng}</p>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Metadata key-value pairs -->
  {#if metadataEntries.length > 0}
    <div class="entity-metadata">
      {#each metadataEntries as [key, value] (key)}
        <div class="meta-row">
          <span class="meta-key">{key}</span>
          <span class="meta-value">{value}</span>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Source file -->
  {#if entity?.source_file}
    <span class="source-file">{entity.source_file}</span>
  {/if}
</div>

<style>
  .entity-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
  }

  .entity-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .entity-name {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .entity-thumbnail {
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .thumbnail {
    width: 100%;
    display: block;
    object-fit: contain;
    max-height: 80px;
    background: var(--cds-layer-01);
  }

  .entity-audio {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .audio-header {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--cds-text-02);
  }

  .audio-event {
    font-size: 0.6875rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .audio-player {
    width: 100%;
    height: 28px;
    filter: invert(1) hue-rotate(180deg);
    opacity: 0.85;
  }

  .audio-script {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 4px 6px;
    background: var(--cds-layer-01);
    border-radius: 3px;
  }

  .script-kr {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    line-height: 1.4;
    margin: 0;
  }

  .script-eng {
    font-size: 0.6875rem;
    color: var(--cds-text-02);
    line-height: 1.4;
    margin: 0;
  }

  .entity-metadata {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meta-row {
    display: flex;
    gap: 8px;
    font-size: 0.6875rem;
  }

  .meta-key {
    color: var(--cds-text-03);
    text-transform: capitalize;
    min-width: 48px;
    flex-shrink: 0;
  }

  .meta-value {
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source-file {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    word-break: break-all;
    margin-top: 2px;
  }
</style>
