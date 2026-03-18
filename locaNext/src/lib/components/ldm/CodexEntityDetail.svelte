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
  import { untrack } from "svelte";
  import { Tag, InlineLoading, Button } from "carbon-components-svelte";
  import { Music, ImageReference, Renew } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import PlaceholderImage from "./PlaceholderImage.svelte";
  import PlaceholderAudio from "./PlaceholderAudio.svelte";

  const API_BASE = getApiBase();

  // Props
  let { entity = null, onsimilar = () => {} } = $props();

  // State
  let imageError = $state(false);
  let audioError = $state(false);
  let similarItems = $state([]);
  let loadingSimilar = $state(false);

  // AI Image generation state
  let generating = $state(false);
  let genError = $state(null);
  let imageGenAvailable = $state(false);
  let aiImageUrl = $state(null);

  // TTS Voice generation state
  let generatingVoice = $state(false);
  let voiceGenError = $state(null);
  let ttsAvailable = $state(false);
  let generatedAudioUrl = $state(null);
  let voiceDuration = $state(null);

  // Check image-gen and TTS availability on mount
  onMount(() => {
    fetch(`${API_BASE}/api/ldm/codex/image-gen/status`, { headers: getAuthHeaders() })
      .then(r => r.json())
      .then(data => { imageGenAvailable = data.available; })
      .catch((err) => { logger.warning('Image gen status check failed', { error: err?.message }); imageGenAvailable = false; });

    fetch(`${API_BASE}/api/ldm/codex/tts/status`, { headers: getAuthHeaders() })
      .then(r => r.json())
      .then(data => { ttsAvailable = data.available; })
      .catch((err) => { logger.warning('TTS status check failed', { error: err?.message }); ttsAvailable = false; });
  });

  // Update aiImageUrl when entity changes
  $effect(() => {
    if (entity?.ai_image_url) {
      aiImageUrl = `${API_BASE}${entity.ai_image_url}?v=${Date.now()}`;
    } else {
      aiImageUrl = null;
    }
  });

  /**
   * Generate or regenerate AI image for current entity
   */
  async function generateImage(force = false) {
    if (!entity) return;
    generating = true;
    genError = null;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/generate-image/${entity.entity_type}/${entity.strkey}?force=${force}`,
        { method: 'POST', headers: getAuthHeaders() }
      );
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      aiImageUrl = `${API_BASE}${data.image_url}?t=${Date.now()}`;
      imageError = false;
      logger.info('AI image generated', { strkey: entity.strkey, status: data.status });
    } catch (err) {
      logger.error('AI image generation failed', { error: err.message });
      genError = err.message || 'Image generation failed';
    } finally {
      generating = false;
    }
  }

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
      ? `${API_BASE}/api/ldm/mapdata/thumbnail/${entity.image_texture}?v=${Date.now()}`
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

  // Reset image/audio/voice state when entity changes, check for cached voice
  $effect(() => {
    if (entity) {
      imageError = false;
      audioError = false;
      generatedAudioUrl = null;
      voiceDuration = null;
      voiceGenError = null;
      generatingVoice = false;

      // Check for cached TTS voice (lightweight HEAD — does NOT trigger generation)
      // Use untrack for ttsAvailable to avoid re-running when availability changes
      if (untrack(() => ttsAvailable)) {
        const capturedStrkey = entity.strkey;
        const voiceUrl = `${API_BASE}/api/ldm/codex/voice/${capturedStrkey}`;
        fetch(voiceUrl, { method: 'HEAD', headers: getAuthHeaders() })
          .then(r => {
            if (r.ok && entity?.strkey === capturedStrkey) {
              generatedAudioUrl = `${voiceUrl}?t=${Date.now()}`;
            }
          })
          .catch((err) => {
            logger.warning('TTS cache check failed', { strkey: capturedStrkey, error: err?.message });
          });
      }
    }
  });

  /**
   * Generate or regenerate TTS voice for current entity
   */
  async function generateVoice(force = false) {
    if (!entity) return;
    const targetStrkey = entity.strkey;
    generatingVoice = true;
    voiceGenError = null;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/generate-voice/${targetStrkey}?force=${force}`,
        { method: 'POST', headers: getAuthHeaders() }
      );
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      // Guard: entity may have changed during generation
      if (entity?.strkey !== targetStrkey) return;
      const data = await response.json();
      generatedAudioUrl = `${API_BASE}${data.audio_url}?t=${Date.now()}`;
      voiceDuration = data.duration_ms;
      audioError = false;
      logger.info('Voice generated', { strkey: targetStrkey, status: data.status, duration: data.duration_ms });
    } catch (err) {
      if (entity?.strkey !== targetStrkey) return;
      logger.error('Voice generation failed', { strkey: targetStrkey, error: err.message });
      voiceGenError = err.message || 'Voice generation failed';
    } finally {
      // Always reset loading state — even if entity changed mid-generation
      generatingVoice = false;
    }
  }
</script>

{#if entity}
  <div class="entity-detail">
    <div class="detail-layout">
      <!-- Left: Image -->
      <div class="detail-image">
        {#if generating}
          <div class="generating-spinner">
            <InlineLoading description="Generating..." />
          </div>
        {:else if aiImageUrl}
          <div class="ai-image-wrapper">
            <img
              src={aiImageUrl}
              alt={entity.name}
              class="entity-image"
              onerror={() => { logger.warning('AI image failed to load', { strkey: entity?.strkey }); aiImageUrl = null; }}
            />
            {#if imageGenAvailable}
              <Button
                kind="ghost"
                size="small"
                icon={Renew}
                iconDescription="Regenerate"
                class="regenerate-btn"
                onclick={() => generateImage(true)}
              >Regenerate</Button>
            {/if}
          </div>
        {:else if imageUrl && !imageError}
          <img
            src={imageUrl}
            alt={entity.name}
            class="entity-image"
            onerror={() => { imageError = true; }}
          />
        {:else}
          <div class="placeholder-wrapper">
            <PlaceholderImage entityType={entity.entity_type} entityName={entity.name} />
            {#if imageGenAvailable}
              <Button
                kind="ghost"
                size="small"
                icon={ImageReference}
                iconDescription="Generate Image"
                onclick={() => generateImage(false)}
              >Generate Image</Button>
            {/if}
          </div>
        {/if}
      </div>

      {#if genError}
        <div class="gen-error" role="alert">
          <span class="gen-error-text">Image generation failed: {genError}</span>
        </div>
      {/if}

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
            {#each CHARACTER_ATTRS as attr (attr)}
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
            {#each ITEM_ATTRS as attr (attr)}
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
      {#if generatingVoice}
        <div class="audio-section">
          <div class="section-header">
            <Music size={16} />
            <span>Voice</span>
          </div>
          <InlineLoading description="Generating voice..." />
        </div>
      {:else if generatedAudioUrl}
        <div class="audio-section">
          <div class="section-header">
            <Music size={16} />
            <span>Voice {#if voiceDuration}({(voiceDuration / 1000).toFixed(1)}s){/if}</span>
          </div>
          <audio
            controls
            preload="auto"
            class="audio-player"
            src={generatedAudioUrl}
            onerror={() => {
              logger.warning('Generated voice audio failed to play', { strkey: entity?.strkey });
              generatedAudioUrl = null;
              voiceGenError = 'Audio playback failed -- try regenerating';
            }}
          >
            Your browser does not support the audio element.
          </audio>
          {#if ttsAvailable}
            <Button
              kind="ghost"
              size="small"
              icon={Renew}
              iconDescription="Regenerate voice"
              onclick={() => generateVoice(true)}
            >Regenerate</Button>
          {/if}
        </div>
      {:else if audioUrl && !audioError}
        <div class="audio-section">
          <div class="section-header">
            <Music size={16} />
            <span>Audio</span>
          </div>
          <audio
            controls
            preload="none"
            class="audio-player"
            onerror={() => { audioError = true; logger.warning('Audio playback failed', { url: audioUrl }); }}
          >
            <source src={audioUrl} />
            Your browser does not support the audio element.
          </audio>
        </div>
      {:else if ttsAvailable}
        <div class="audio-section">
          <div class="section-header">
            <Music size={16} />
            <span>Voice</span>
          </div>
          <Button
            kind="tertiary"
            size="small"
            icon={Music}
            onclick={() => generateVoice(false)}
          >Generate Voice</Button>
        </div>
      {:else}
        <PlaceholderAudio entityName={entity.name} />
      {/if}

      {#if voiceGenError}
        <div class="gen-error" role="alert">
          <span class="gen-error-text">Voice generation failed: {voiceGenError}</span>
        </div>
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
                aria-label="View similar item: {result.entity.name}"
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
              aria-label="View related entity: {relatedKey}"
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
    max-height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
    overflow: hidden;
  }

  .gen-error {
    padding: 6px 10px;
    background: var(--cds-support-01, #da1e28);
    border-radius: 4px;
    margin-top: -8px;
  }

  .gen-error-text {
    font-size: 0.75rem;
    color: var(--cds-text-on-color, #fff);
  }

  .entity-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .generating-spinner {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 120px;
  }

  .ai-image-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .ai-image-wrapper :global(.regenerate-btn) {
    position: absolute;
    bottom: 4px;
    right: 4px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .ai-image-wrapper:hover :global(.regenerate-btn) {
    opacity: 1;
  }

  .placeholder-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
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
    overflow-wrap: break-word;
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

  .related-badge:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
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
