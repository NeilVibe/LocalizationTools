<script>
  /**
   * AudioTab.svelte - Audio context display for MapData integration
   *
   * Shows audio player + script text when audio context exists for selected row,
   * graceful empty state otherwise. Fetches from MapData API on row change.
   *
   * Phase 5: Visual Polish and Integration (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Music } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  // Props
  let { selectedRow = null } = $props();

  // State
  let audioContext = $state(null);
  let loading = $state(false);
  let error = $state(null);

  // Fetch audio context when selected row changes
  $effect(() => {
    const stringId = selectedRow?.string_id;
    if (!stringId) {
      audioContext = null;
      error = null;
      return;
    }

    loading = true;
    error = null;

    fetch(`${API_BASE}/api/ldm/mapdata/audio/${encodeURIComponent(stringId)}`, {
      headers: getAuthHeaders()
    })
      .then(async (response) => {
        if (response.ok) {
          audioContext = await response.json();
        } else if (response.status === 404) {
          audioContext = null;
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      })
      .catch((err) => {
        logger.error('Failed to fetch audio context', { error: err.message });
        error = err.message;
        audioContext = null;
      })
      .finally(() => {
        loading = false;
      });
  });

  /**
   * Format duration as mm:ss
   */
  function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
</script>

<div class="audio-tab">
  {#if loading}
    <div class="audio-tab-loading" data-testid="audio-tab-loading">
      <InlineLoading description="Loading audio context..." />
    </div>
  {:else if !selectedRow}
    <div class="audio-tab-empty" data-testid="audio-tab-empty">
      <Music size={32} />
      <span class="empty-title">No Row Selected</span>
      <span class="empty-desc">Select a row in the grid to view audio context</span>
    </div>
  {:else if audioContext}
    <div class="audio-context" data-testid="audio-tab-player">
      <!-- Event name header -->
      <div class="event-header">
        <Music size={16} />
        <span class="event-name">{audioContext.event_name}</span>
        {#if audioContext.duration_seconds}
          <span class="duration">{formatDuration(audioContext.duration_seconds)}</span>
        {/if}
      </div>

      <!-- Audio player -->
      <div class="player-wrapper">
        <audio controls preload="none" class="audio-player">
          <source src="{audioContext.wem_path}" />
          Your browser does not support the audio element.
        </audio>
      </div>

      <!-- Script text -->
      {#if audioContext.script_kr || audioContext.script_eng}
        <div class="script-section" data-testid="audio-tab-script">
          <span class="script-label">Script</span>
          {#if audioContext.script_kr}
            <p class="script-kr">{audioContext.script_kr}</p>
          {/if}
          {#if audioContext.script_eng}
            <p class="script-eng">{audioContext.script_eng}</p>
          {/if}
        </div>
      {/if}

      <!-- WEM path -->
      <span class="wem-path">{audioContext.wem_path}</span>
    </div>
  {:else if error}
    <div class="audio-tab-empty" data-testid="audio-tab-empty">
      <Music size={32} />
      <span class="empty-title">Error Loading Audio</span>
      <span class="empty-desc">{error}</span>
    </div>
  {:else}
    <div class="audio-tab-empty" data-testid="audio-tab-empty">
      <Music size={32} />
      <span class="empty-title">No Audio Context</span>
      <span class="empty-desc">No audio data available for this segment</span>
    </div>
  {/if}
</div>

<style>
  .audio-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .audio-tab-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
  }

  .audio-tab-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 3rem 1rem;
    color: var(--cds-text-03);
    text-align: center;
  }

  .empty-title {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-02);
  }

  .empty-desc {
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .audio-context {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .event-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--cds-text-01);
  }

  .event-name {
    font-size: 0.75rem;
    font-weight: 500;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .duration {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-variant-numeric: tabular-nums;
  }

  .player-wrapper {
    background: var(--cds-layer-02);
    border-radius: 4px;
    padding: 8px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .audio-player {
    width: 100%;
    height: 32px;
    filter: invert(1) hue-rotate(180deg);
    opacity: 0.85;
  }

  .script-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .script-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .script-kr {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.5;
    margin: 0;
  }

  .script-eng {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    margin: 0;
  }

  .wem-path {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    word-break: break-all;
  }
</style>
