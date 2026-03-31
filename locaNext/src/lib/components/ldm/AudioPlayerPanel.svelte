<script>
  /**
   * AudioPlayerPanel.svelte - Audio player right panel for Audio Codex
   *
   * MDG-exact: event header + progress bar + Play/Stop/Prev/Next controls
   * + KOR/ENG script panels + metadata. Props-driven, stateless.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { Music, SkipBackFilled, SkipForwardFilled, PlayFilledAlt, StopFilledAlt } from "carbon-icons-svelte";

  let {
    audio = null,
    playing = false,
    currentTime = 0,
    duration = 0,
    onplay = () => {},
    onstop = () => {},
    onprev = () => {},
    onnext = () => {},
    onseek = () => {},
  } = $props();

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function handleProgressClick(event) {
    if (!duration) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    onseek(ratio * duration);
  }

  let progressPercent = $derived(
    duration > 0 ? (currentTime / duration) * 100 : 0
  );
</script>

<div class="player-panel">
  {#if audio}
    <!-- Event name header -->
    <div class="panel-header">
      <Music size={18} />
      <span class="event-name">{audio.event_name}</span>
      {#if duration > 0}
        <span class="duration-badge">{formatTime(duration)}</span>
      {/if}
    </div>

    <!-- Progress bar -->
    {#if audio.has_wem}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="progress-bar" onclick={handleProgressClick}>
        <div class="progress-fill" style="width: {progressPercent}%"></div>
        <div class="progress-thumb" style="left: {progressPercent}%"></div>
      </div>
      <div class="time-display">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    {/if}

    <!-- Controls -->
    <div class="controls">
      <button class="ctrl-btn" onclick={onprev} aria-label="Previous">
        <SkipBackFilled size={20} />
      </button>

      {#if playing}
        <button class="ctrl-btn primary stop" onclick={onstop} aria-label="Stop">
          <StopFilledAlt size={24} />
        </button>
      {:else}
        <button
          class="ctrl-btn primary"
          onclick={onplay}
          disabled={!audio.has_wem}
          aria-label="Play"
        >
          <PlayFilledAlt size={24} />
        </button>
      {/if}

      <button class="ctrl-btn" onclick={onnext} aria-label="Next">
        <SkipForwardFilled size={20} />
      </button>
    </div>

    <!-- KOR Script -->
    {#if audio.script_kr}
      <div class="script-section">
        <span class="section-label">Korean Script</span>
        <p class="script-text kr">{audio.script_kr}</p>
      </div>
    {/if}

    <!-- ENG Script -->
    {#if audio.script_eng}
      <div class="script-section">
        <span class="section-label">English Script</span>
        <p class="script-text eng">{audio.script_eng}</p>
      </div>
    {/if}

    <!-- Metadata -->
    <div class="meta-section">
      <span class="section-label">Details</span>
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
      {#if audio.xml_order != null}
        <div class="meta-row">
          <span class="meta-label">XML Order</span>
          <span class="meta-value">{audio.xml_order}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <Music size={32} />
      <p>Select an audio entry to see details</p>
    </div>
  {/if}
</div>

<style>
  .player-panel {
    width: 350px;
    flex-shrink: 0;
    border-left: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--cds-text-01);
  }

  .event-name {
    font-size: 0.9375rem;
    font-weight: 600;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .duration-badge {
    font-size: 0.6875rem;
    padding: 2px 8px;
    border-radius: 8px;
    background: var(--cds-layer-02);
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  /* Progress bar */
  .progress-bar {
    height: 6px;
    background: var(--cds-layer-02);
    border-radius: 3px;
    position: relative;
    cursor: pointer;
  }

  .progress-fill {
    height: 100%;
    background: var(--cds-interactive-01, #0f62fe);
    border-radius: 3px;
    transition: width 0.1s linear;
  }

  .progress-thumb {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--cds-interactive-01, #0f62fe);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    transition: left 0.1s linear;
  }

  .time-display {
    display: flex;
    justify-content: space-between;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
  }

  /* Controls */
  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 8px 0;
  }

  .ctrl-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 6px;
    border-radius: 50%;
    transition: all 0.15s;
  }

  .ctrl-btn:hover { color: var(--cds-text-01); background: var(--cds-layer-hover-01); }
  .ctrl-btn:focus { outline: 2px solid var(--cds-focus); outline-offset: 1px; }
  .ctrl-btn:disabled { color: var(--cds-disabled-03); cursor: not-allowed; }

  .ctrl-btn.primary {
    width: 44px;
    height: 44px;
    background: var(--cds-interactive-01, #0f62fe);
    color: var(--cds-text-on-color, #fff);
  }

  .ctrl-btn.primary:hover { background: var(--cds-hover-primary, #0353e9); }
  .ctrl-btn.primary:disabled { background: var(--cds-disabled-02); color: var(--cds-disabled-03); }

  .ctrl-btn.primary.stop {
    background: var(--cds-support-error, #da1e28);
  }

  .ctrl-btn.primary.stop:hover { background: var(--cds-hover-danger, #b81921); }

  /* Scripts */
  .script-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
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

  .script-text {
    margin: 0;
    line-height: 1.6;
    white-space: pre-line;
  }

  .script-text.kr { font-size: 0.9375rem; color: var(--cds-text-01); }
  .script-text.eng { font-size: 0.8125rem; color: var(--cds-text-02); }

  /* Metadata */
  .meta-section {
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
    min-width: 80px;
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

  /* Empty state */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 16px;
    color: var(--cds-text-03);
    text-align: center;
  }

  .empty-state p {
    font-size: 0.875rem;
    margin: 0;
    color: var(--cds-text-02);
  }
</style>
