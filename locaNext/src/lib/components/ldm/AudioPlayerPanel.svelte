<script>
  /**
   * AudioPlayerPanel.svelte - Audio player right panel for Audio Codex
   *
   * MDG-exact layout from audio_viewer.py:
   * - Event name header + duration badge
   * - KOR Script (warm cream #FFF8F0, primary, 60%)
   * - ENG Script (cool blue #F0F5FF, reference, 40%)
   * - Controls: Prev/Play/Stop/Next + Auto-play toggle + Cleanup cache
   * - Progress bar + status + file info
   * - Empty state overlay
   *
   * Phase 107→108: Full MDG audio_viewer.py graft
   */
  import { Music, SkipBackFilled, SkipForwardFilled, PlayFilledAlt, StopFilledAlt, TrashCan } from "carbon-icons-svelte";

  let {
    audio = null,
    playing = false,
    currentTime = 0,
    duration = 0,
    statusText = "",
    onplay = () => {},
    onstop = () => {},
    onprev = () => {},
    onnext = () => {},
    oncleanup = () => {},
    audioUnavailableWarning = "",
  } = $props();

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  // MDG: progress bar is display-only (no seeking — winsound doesn't support it)
  let progressPercent = $derived(
    duration > 0 ? (currentTime / duration) * 100 : 0
  );

  // MDG: derive time display text
  let timeDisplayText = $derived.by(() => {
    if (statusText) return statusText;
    if (playing && duration > 0) return `${formatTime(currentTime)} / ${formatTime(duration)}`;
    if (playing) return `Playing... ${formatTime(currentTime)}`;
    return "";
  });
</script>

<div class="player-panel">
  {#if audio}
    <!-- MDG Row 0: Header with event name + duration + availability warning -->
    <div class="panel-header">
      <Music size={18} />
      <span class="event-name">{audio.event_name}</span>
      {#if duration > 0}
        <span class="duration-badge">{formatTime(duration)}</span>
      {:else if audio.has_wem}
        <span class="duration-badge">...</span>
      {/if}
    </div>
    {#if audioUnavailableWarning}
      <div class="availability-warning">{audioUnavailableWarning}</div>
    {/if}

    <!-- MDG Row 2: KOR Script (primary — warm cream background, 60% space) -->
    <div class="script-section kor-section">
      <span class="section-label">Script Line (KOR)</span>
      <div class="script-box kor">
        {#if audio.script_kr}
          <p class="script-text">{audio.script_kr}</p>
        {:else}
          <p class="script-empty">(No Korean script)</p>
        {/if}
      </div>
    </div>

    <!-- MDG Row 3: Selected language script (replaces ENG when non-English selected) -->
    <div class="script-section eng-section">
      {#if audio.script_lang}
        <span class="section-label">Script Line ({audio.script_lang_code?.toUpperCase() || 'ENG'})</span>
        <div class="script-box eng">
          <p class="script-text">{audio.script_lang}</p>
        </div>
      {:else}
        <span class="section-label">Script Line (ENG)</span>
        <div class="script-box eng">
          {#if audio.script_eng}
            <p class="script-text">{audio.script_eng}</p>
          {:else}
            <p class="script-empty">(No English script)</p>
          {/if}
        </div>
      {/if}
    </div>

    <!-- MDG Row 4: Separator -->
    <div class="separator"></div>

    <!-- MDG Row 5: Controls — Prev/Play/Stop/Next | Auto-play | Cleanup cache -->
    <div class="controls">
      <button class="ctrl-btn" onclick={onprev} aria-label="Previous" title="Previous">
        <SkipBackFilled size={20} />
        <span class="ctrl-label">Prev</span>
      </button>

      {#if playing}
        <button class="ctrl-btn primary stop" onclick={onstop} aria-label="Stop" title="Stop">
          <StopFilledAlt size={24} />
        </button>
      {:else}
        <button
          class="ctrl-btn primary"
          onclick={onplay}
          disabled={!audio.has_wem}
          aria-label="Play"
          title="Play"
        >
          <PlayFilledAlt size={24} />
        </button>
      {/if}

      <button class="ctrl-btn" onclick={onnext} aria-label="Next" title="Next">
        <SkipForwardFilled size={20} />
        <span class="ctrl-label">Next</span>
      </button>

      <span class="ctrl-separator"></span>

      <!-- Cleanup cache button -->
      <button class="cleanup-btn" onclick={oncleanup} title="Cleanup cached WAV files">
        <TrashCan size={14} />
        <span>Cleanup cache</span>
      </button>
    </div>

    <!-- MDG Row 6: Progress bar + status -->
    {#if audio.has_wem}
      <!-- MDG: progress bar is display-only (winsound has no seek) -->
      <div class="progress-bar">
        <div class="progress-fill" style="width: {progressPercent}%"></div>
      </div>
      <div class="time-display">
        <span>{formatTime(currentTime)}</span>
        <span class="status-text" class:playing>{timeDisplayText || formatTime(duration)}</span>
      </div>
    {/if}

    <!-- MDG Row 7: File info -->
    {#if audio.wem_path}
      <div class="file-info">File: {audio.wem_path.split(/[/\\]/).pop()}</div>
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
      {#if audio.xml_order != null}
        <div class="meta-row">
          <span class="meta-label">XML Order</span>
          <span class="meta-value">{audio.xml_order}</span>
        </div>
      {/if}
    </div>
  {:else}
    <!-- MDG: Empty state overlay -->
    <div class="empty-state">
      <Music size={32} />
      <p>Select an audio entry from the list<br/>to view scripts and play audio</p>
    </div>
  {/if}
</div>

<style>
  .player-panel {
    width: 380px;
    flex-shrink: 0;
    border-left: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
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

  /* MDG: availability warning (vgmstream not found) */
  .availability-warning {
    font-size: 0.6875rem;
    color: #da1e28;
    padding: 2px 0;
  }

  /* MDG Script sections — warm cream (KOR) and cool blue (ENG) */
  .script-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .kor-section { flex: 3; min-height: 0; } /* 60% like MDG rowconfigure weight=3 */
  .eng-section { flex: 2; min-height: 0; } /* 40% like MDG rowconfigure weight=2 */

  .section-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0 2px;
  }

  .script-box {
    border-radius: 4px;
    border: 1px solid;
    padding: 12px;
    overflow-y: auto;
    line-height: 1.6;
  }

  /* MDG: warm ivory — primary content */
  .script-box.kor {
    background: #FFF8F0;
    border-color: #e0d8d0;
    color: #1a1a1a;
    font-size: 0.9375rem;
    font-family: 'Malgun Gothic', sans-serif;
    min-height: 100px;
  }

  /* MDG: cool blue-gray — reference content */
  .script-box.eng {
    background: #F0F5FF;
    border-color: #d0d8e0;
    color: #333333;
    font-size: 0.8125rem;
    font-family: 'Malgun Gothic', sans-serif;
    min-height: 70px;
  }

  .script-text {
    margin: 0;
    white-space: pre-line;
    word-break: break-word;
  }

  .script-empty {
    margin: 0;
    color: #999;
    font-style: italic;
  }

  .separator {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 2px 0;
  }

  /* MDG Controls: Prev/Play/Stop/Next | Auto-play | Cleanup cache */
  .controls {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    flex-wrap: wrap;
  }

  .ctrl-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 6px;
    border-radius: 4px;
    transition: all 0.15s;
    font-size: 0.75rem;
  }

  .ctrl-label { font-size: 0.6875rem; }

  .ctrl-btn:hover { color: var(--cds-text-01); background: var(--cds-layer-hover-01); }
  .ctrl-btn:focus { outline: 2px solid var(--cds-focus); outline-offset: 1px; }
  .ctrl-btn:disabled { color: var(--cds-disabled-03); cursor: not-allowed; }

  .ctrl-btn.primary {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--cds-interactive-01, #0f62fe);
    color: var(--cds-text-on-color, #fff);
  }

  .ctrl-btn.primary:hover { background: var(--cds-hover-primary, #0353e9); }
  .ctrl-btn.primary:disabled { background: var(--cds-disabled-02); color: var(--cds-disabled-03); }

  .ctrl-btn.primary.stop {
    background: var(--cds-support-error, #da1e28);
  }

  .ctrl-btn.primary.stop:hover { background: var(--cds-hover-danger, #b81921); }

  .ctrl-separator {
    width: 1px;
    height: 24px;
    background: var(--cds-border-subtle-01);
    margin: 0 4px;
  }

  .cleanup-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    border: none;
    background: transparent;
    color: var(--cds-text-03);
    font-size: 0.6875rem;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    margin-left: auto;
  }

  .cleanup-btn:hover { color: var(--cds-text-01); background: var(--cds-layer-hover-01); }

  /* Progress bar */
  /* MDG: progress bar is display-only (winsound has no seek) */
  .progress-bar {
    height: 6px;
    background: var(--cds-layer-02);
    border-radius: 3px;
    position: relative;
  }

  .progress-fill {
    height: 100%;
    background: var(--cds-interactive-01, #0f62fe);
    border-radius: 3px;
    transition: width 0.1s linear;
  }

  .time-display {
    display: flex;
    justify-content: space-between;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
  }

  .status-text.playing { color: #4a9; }

  /* File info (MDG Row 7) */
  .file-info {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    padding: 0 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Metadata */
  .meta-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-top: 4px;
    border-top: 1px solid var(--cds-border-subtle-01);
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

  /* Empty state (MDG overlay) */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 48px 16px;
    color: var(--cds-text-03);
    text-align: center;
    flex: 1;
  }

  .empty-state p {
    font-size: 0.875rem;
    margin: 0;
    color: var(--cds-text-02);
    line-height: 1.6;
  }
</style>
