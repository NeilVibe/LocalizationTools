<script>
  /**
   * AudioCodexDetail.svelte - Audio entry detail panel
   *
   * Shows full script text (KOR + ENG), event name, StringId, WEM path,
   * export path, and full-width audio player with WAV streaming.
   *
   * Phase 48: Audio Codex UI (Plan 02)
   */
  import { Music } from "carbon-icons-svelte";
  import { getApiBase } from "$lib/utils/api.js";

  const API_BASE = getApiBase();

  // Props
  let { audio = null, onback = null } = $props();

  /**
   * Build stream URL with cache-bust for Chrome
   */
  function getStreamUrl(eventName) {
    return `${API_BASE}/api/ldm/codex/audio/stream/${encodeURIComponent(eventName)}?v=${Date.now()}`;
  }
</script>

{#if audio}
  <div class="audio-detail">
    <!-- Event name header -->
    <div class="detail-header">
      <Music size={20} />
      <h2 class="detail-event-name">{audio.event_name}</h2>
    </div>

    <!-- Audio player -->
    {#if audio.has_wem}
      <div class="player-section">
        {#key audio.event_name}
          <audio
            controls
            preload="none"
            class="detail-audio-player"
            crossorigin="anonymous"
            src={getStreamUrl(audio.event_name)}
          >
            Your browser does not support the audio element.
          </audio>
        {/key}
      </div>
    {:else}
      <div class="no-audio">
        <span>No audio file available for this event</span>
      </div>
    {/if}

    <!-- Script text section -->
    {#if audio.script_kr || audio.script_eng}
      <div class="script-section">
        <span class="section-label">Script</span>
        {#if audio.script_kr}
          <p class="script-kr">{audio.script_kr}</p>
        {/if}
        {#if audio.script_eng}
          <p class="script-eng">{audio.script_eng}</p>
        {/if}
      </div>
    {/if}

    <!-- Metadata section -->
    <div class="metadata-section">
      <span class="section-label">Details</span>
      <div class="meta-grid">
        {#if audio.string_id}
          <div class="meta-row">
            <span class="meta-label">StringId</span>
            <span class="meta-value">{audio.string_id}</span>
          </div>
        {/if}
        {#if audio.export_path}
          <div class="meta-row">
            <span class="meta-label">Category</span>
            <span class="meta-value">{audio.export_path}</span>
          </div>
        {/if}
        {#if audio.wem_path}
          <div class="meta-row">
            <span class="meta-label">WEM Path</span>
            <span class="meta-value mono">{audio.wem_path}</span>
          </div>
        {/if}
        {#if audio.xml_order !== null && audio.xml_order !== undefined}
          <div class="meta-row">
            <span class="meta-label">XML Order</span>
            <span class="meta-value">{audio.xml_order}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .audio-detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .detail-header {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--cds-text-01);
  }

  .detail-event-name {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
    word-break: break-word;
  }

  /* Audio player */
  .player-section {
    background: var(--cds-layer-02);
    border-radius: 4px;
    padding: 12px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .detail-audio-player {
    width: 100%;
    height: 40px;
    filter: invert(1) hue-rotate(180deg);
    opacity: 0.85;
  }

  .no-audio {
    padding: 12px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
    color: var(--cds-text-03);
    font-size: 0.8125rem;
    text-align: center;
  }

  /* Script section */
  .script-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .section-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .script-kr {
    font-size: 0.9375rem;
    color: var(--cds-text-01);
    line-height: 1.6;
    margin: 0;
    white-space: pre-line;
  }

  .script-eng {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    margin: 0;
    white-space: pre-line;
  }

  /* Metadata section */
  .metadata-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .meta-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .meta-row {
    display: flex;
    gap: 12px;
    font-size: 0.8125rem;
  }

  .meta-label {
    color: var(--cds-text-03);
    min-width: 90px;
    flex-shrink: 0;
    font-weight: 500;
  }

  .meta-value {
    color: var(--cds-text-01);
    word-break: break-all;
  }

  .meta-value.mono {
    font-family: monospace;
    font-size: 0.75rem;
  }
</style>
