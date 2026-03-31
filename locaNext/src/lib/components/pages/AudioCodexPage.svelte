<script>
  /**
   * AudioCodexPage.svelte - Audio Codex MDG-style 3-panel layout
   *
   * Orchestrator: owns all state, wires AudioExportTree (left),
   * AudioResultGrid (center), AudioPlayerPanel (right).
   * Hidden <audio> element for programmatic playback + progress bar.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Music, Search } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import AudioExportTree from "$lib/components/ldm/AudioExportTree.svelte";
  import AudioResultGrid from "$lib/components/ldm/AudioResultGrid.svelte";
  import AudioPlayerPanel from "$lib/components/ldm/AudioPlayerPanel.svelte";
  import { onMount, onDestroy } from "svelte";

  const API_BASE = getApiBase();

  // ── State ──
  // $state.raw for bulk data arrays — avoids 100K+ proxy overhead (same pattern as language data grid)
  let categories = $state([]);
  let allItems = $state.raw([]);
  let activeCategory = $state(null);
  let searchQuery = $state("");
  let selectedEvent = $state(null);
  let selectedAudio = $state(null);
  let playingEvent = $state(null);
  let selectedLanguage = $state("eng");
  let currentTime = $state(0);
  let duration = $state(0);
  let totalEvents = $state(0);
  let loadingCategories = $state(true);
  let loadingList = $state(true);
  let apiError = $state(null);

  // Hidden audio element ref
  let audioEl = $state(null);
  let rafId = null;

  // ── Derived: client-side filtered items ──
  let filteredItems = $derived.by(() => {
    return allItems.filter((item) => {
      if (activeCategory && item.export_path && !item.export_path.startsWith(activeCategory)) return false;
      if (activeCategory && !item.export_path) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = `${item.event_name || ""} ${item.script_kr || ""} ${item.script_eng || ""} ${item.string_id || ""}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  });

  // ── Audio progress loop ──
  let destroyed = false;

  function startProgressLoop() {
    stopProgressLoop(); // Kill any orphaned loop first
    function tick() {
      if (destroyed) return;
      if (audioEl && !audioEl.paused) {
        currentTime = audioEl.currentTime;
        duration = audioEl.duration || 0;
        rafId = requestAnimationFrame(tick);
      }
    }
    rafId = requestAnimationFrame(tick);
  }

  function stopProgressLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  // ── API calls ──
  async function fetchCategories() {
    loadingCategories = true;
    apiError = null;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/audio/categories`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      categories = data.categories || [];
      totalEvents = data.total_events || 0;
      logger.info("Audio Codex categories loaded", { count: categories.length, totalEvents });
    } catch (err) {
      logger.error("Failed to fetch audio categories", { error: err.message });
      apiError = "Audio Codex unavailable — ensure gamedata folder is configured";
    } finally {
      loadingCategories = false;
    }
  }

  async function fetchAllItems() {
    loadingList = true;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/audio?language=${selectedLanguage}`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allItems = data.items || [];
      logger.info("Audio Codex bulk loaded", { total: allItems.length, language: selectedLanguage });
    } catch (err) {
      logger.error("Failed to fetch audio items", { error: err.message });
      apiError = "Failed to load audio entries";
    } finally {
      loadingList = false;
    }
  }

  async function fetchAudioDetail(eventName) {
    try {
      const res = await fetch(
        `${API_BASE}/api/ldm/codex/audio/${encodeURIComponent(eventName)}?language=${selectedLanguage}`,
        { headers: getAuthHeaders() }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      selectedAudio = await res.json();
    } catch (err) {
      logger.error("Failed to fetch audio detail", { error: err.message, eventName });
      selectedAudio = null; // Clear stale data on failure
    }
  }

  // ── Handlers ──
  function handleRowSelect(eventName) {
    selectedEvent = eventName;
    fetchAudioDetail(eventName);
  }

  function handlePlay(eventName) {
    // If a different event, select it first
    if (eventName && eventName !== selectedEvent) {
      selectedEvent = eventName;
      fetchAudioDetail(eventName);
    }
    const target = eventName || selectedEvent;
    if (!target) return;

    playingEvent = target;
    if (audioEl) {
      audioEl.src = `${API_BASE}/api/ldm/codex/audio/stream/${encodeURIComponent(target)}?language=${selectedLanguage}&v=${Date.now()}`;
      audioEl.load();
      audioEl.play().catch((err) => {
        logger.error("Audio play failed", { error: err.message });
        playingEvent = null;
      });
      startProgressLoop();
    }
  }

  function handleStop() {
    if (audioEl) {
      audioEl.pause();
      audioEl.currentTime = 0;
    }
    playingEvent = null;
    currentTime = 0;
    stopProgressLoop();
  }

  function handleSeek(time) {
    if (audioEl) {
      audioEl.currentTime = time;
      currentTime = time;
    }
  }

  function navigateByOffset(offset) {
    const idx = filteredItems.findIndex((i) => i.event_name === selectedEvent);
    if (idx === -1) return; // Nothing selected
    const nextIdx = (idx + offset + filteredItems.length) % filteredItems.length;
    const item = filteredItems[nextIdx];
    if (item) {
      handleStop();
      handleRowSelect(item.event_name);
    }
  }

  function handlePrev() { navigateByOffset(-1); }
  function handleNext() { navigateByOffset(1); }

  function handleAudioEnded() {
    playingEvent = null;
    currentTime = 0;
    duration = 0;
    stopProgressLoop();
  }

  function handleLanguageChange(event) {
    const lang = event.target.value;
    selectedLanguage = lang;
    handleStop();
    selectedAudio = null;
    selectedEvent = null;
    fetchAllItems();
  }

  onMount(() => {
    fetchCategories();
    fetchAllItems();
  });

  onDestroy(() => {
    destroyed = true;
    stopProgressLoop();
    if (audioEl) {
      audioEl.pause();
      audioEl.src = "";
    }
  });
</script>

<!-- Hidden audio element for programmatic control -->
<audio
  bind:this={audioEl}
  preload="auto"
  onended={handleAudioEnded}
  onerror={(e) => {
    const code = audioEl?.error?.code;
    const msg = audioEl?.error?.message || "Unknown audio error";
    logger.error("Audio playback error", { code, message: msg, event: playingEvent });
    playingEvent = null;
    stopProgressLoop();
  }}
  ondurationchange={() => { if (audioEl) duration = audioEl.duration || 0; }}
></audio>

<div class="audio-codex-page">
  <!-- Header -->
  <div class="page-header-bar">
    <PageHeader icon={Music} title="Audio Codex" />
    <div class="header-controls">
      <!-- Language selector -->
      <div class="lang-select">
        <label for="audio-lang">Language:</label>
        <select id="audio-lang" value={selectedLanguage} onchange={handleLanguageChange}>
          <option value="eng">English (US)</option>
          <option value="kor">Korean</option>
          <option value="zho-cn">Chinese (PRC)</option>
        </select>
      </div>

      <!-- Search bar -->
      <div class="search-wrapper">
        <Search size={16} />
        <input
          type="search"
          placeholder="Search event name, script, StringId..."
          bind:value={searchQuery}
          class="search-input"
          aria-label="Search audio entries"
        />
        <span class="result-count">{filteredItems.length}</span>
      </div>
    </div>
  </div>

  {#if apiError}
    <div class="state-container">
      <ErrorState message={apiError} onretry={() => { fetchCategories(); fetchAllItems(); }} />
    </div>
  {:else if loadingCategories}
    <div class="state-container">
      <InlineLoading description="Loading audio categories..." />
    </div>
  {:else}
    <div class="three-panel">
      <!-- LEFT: Export Tree -->
      <AudioExportTree
        {categories}
        {activeCategory}
        {totalEvents}
        onselect={(path) => { activeCategory = path; }}
      />

      <!-- CENTER: Result Grid -->
      {#if loadingList}
        <div class="loading-center">
          <InlineLoading description="Loading audio entries..." />
        </div>
      {:else}
        <AudioResultGrid
          items={filteredItems}
          {selectedEvent}
          {playingEvent}
          onselect={handleRowSelect}
          onplay={handlePlay}
          onstop={handleStop}
        />
      {/if}

      <!-- RIGHT: Audio Player Panel -->
      <AudioPlayerPanel
        audio={selectedAudio}
        playing={playingEvent != null}
        {currentTime}
        {duration}
        onplay={() => handlePlay(selectedEvent)}
        onstop={handleStop}
        onprev={handlePrev}
        onnext={handleNext}
        onseek={handleSeek}
      />
    </div>
  {/if}
</div>

<style>
  .audio-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .page-header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-right: 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .lang-select {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .lang-select label { font-weight: 500; white-space: nowrap; }

  .lang-select select {
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    padding: 4px 8px;
  }

  .search-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-03);
    min-width: 280px;
  }

  .search-wrapper:focus-within {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    outline: none;
  }

  .search-input::placeholder { color: var(--cds-text-03); }

  .result-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
  }

  .state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 32px;
  }

  .three-panel {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .loading-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
