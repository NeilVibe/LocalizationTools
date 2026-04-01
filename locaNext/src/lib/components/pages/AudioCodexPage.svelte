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

  // ── Tree panel resize ──
  let treeWidth = $state(280);
  let isTreeResizing = $state(false);
  let treeResizeStartX = $state(0);
  let treeResizeStartWidth = $state(0);

  function startTreeResize(event) {
    event.preventDefault();
    isTreeResizing = true;
    treeResizeStartX = event.clientX;
    treeResizeStartWidth = treeWidth;
    document.addEventListener('mousemove', handleTreeResize);
    document.addEventListener('mouseup', stopTreeResize);
  }

  function handleTreeResize(event) {
    if (!isTreeResizing) return;
    const delta = event.clientX - treeResizeStartX;
    treeWidth = Math.max(200, Math.min(800, treeResizeStartWidth + delta));
  }

  function stopTreeResize() {
    isTreeResizing = false;
    document.removeEventListener('mousemove', handleTreeResize);
    document.removeEventListener('mouseup', stopTreeResize);
  }

  // ── State ──
  // $state.raw for bulk data arrays — avoids 100K+ proxy overhead (same pattern as language data grid)
  let categories = $state([]);
  let allItems = $state.raw([]);
  let activeCategory = $state(null);
  let searchQuery = $state("");
  let matchType = $state("contains"); // MDG: Contains/Exact/Fuzzy (search_panel.py Row 2)
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
  let statusText = $state("");

  // MDG-exact: playback via backend winsound (no browser <audio> element)
  let pollId = null;

  // ── Derived: client-side filtered items ──
  // MDG PRIORITY: search query OVERRIDES category (app.py:897-900).
  // When query exists → search ALL items, ignore category.
  // When query is empty → use category filter.
  let filteredItems = $derived.by(() => {
    if (searchQuery) {
      // MDG: _on_search() ignores category when query is non-empty
      const q = searchQuery.toLowerCase();
      return allItems.filter((item) => {
        const searchable = `${item.event_name || ""} ${item.script_kr || ""} ${item.script_eng || ""} ${item.string_id || ""}`.toLowerCase();
        if (matchType === "exact") {
          // MDG: exact match on any field
          return (item.event_name || "").toLowerCase() === q
            || (item.script_kr || "").toLowerCase() === q
            || (item.script_eng || "").toLowerCase() === q
            || (item.string_id || "").toLowerCase() === q;
        }
        // MDG default: "contains" — substring match
        return searchable.includes(q);
      });
    }
    // No search: use category filter (MDG: _on_category_select)
    return allItems.filter((item) => {
      if (activeCategory && item.export_path && !item.export_path.startsWith(activeCategory)) return false;
      if (activeCategory && !item.export_path) return false;
      return true;
    });
  });

  // ── Playback status polling (MDG: timer-based progress) ──
  let destroyed = false;

  function startStatusPolling() {
    stopStatusPolling();
    async function poll() {
      if (destroyed || !playingEvent) return;
      try {
        const res = await fetch(`${API_BASE}/api/ldm/codex/audio/playback-status`, { headers: getAuthHeaders() });
        if (res.ok) {
          const status = await res.json();
          if (status.is_playing) {
            currentTime = status.elapsed || 0;
            duration = status.duration || 0;
            pollId = setTimeout(poll, 200);
          } else {
            // Playback ended naturally (winsound finished)
            playingEvent = null;
            currentTime = 0;
            duration = 0;
          }
        }
      } catch {
        // Ignore polling errors
      }
    }
    pollId = setTimeout(poll, 200);
  }

  function stopStatusPolling() {
    if (pollId) {
      clearTimeout(pollId);
      pollId = null;
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

  async function handlePlay(eventName) {
    // If a different event, select it first
    if (eventName && eventName !== selectedEvent) {
      selectedEvent = eventName;
      fetchAudioDetail(eventName);
    }
    const target = eventName || selectedEvent;
    if (!target) return;

    try {
      // MDG-exact: POST play → backend converts WEM→WAV → winsound.PlaySound()
      const res = await fetch(
        `${API_BASE}/api/ldm/codex/audio/play/${encodeURIComponent(target)}?language=${selectedLanguage}`,
        { method: "POST", headers: getAuthHeaders() }
      );
      if (res.ok) {
        playingEvent = target;
        currentTime = 0;
        duration = 0;
        startStatusPolling();
      } else {
        const err = await res.json().catch(() => ({ detail: "Play failed" }));
        logger.error("Audio play failed", { error: err.detail, event: target });
      }
    } catch (err) {
      logger.error("Audio play request failed", { error: err.message });
    }
  }

  async function handleStop() {
    stopStatusPolling();
    try {
      // MDG-exact: POST stop → winsound.PlaySound(None, SND_PURGE)
      await fetch(`${API_BASE}/api/ldm/codex/audio/stop`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
    } catch {
      // Ignore stop errors
    }
    playingEvent = null;
    currentTime = 0;
    duration = 0;
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

  async function handleLanguageChange(event) {
    const lang = event.target.value;
    selectedLanguage = lang;
    await handleStop();
    selectedAudio = null;
    selectedEvent = null;
    fetchAllItems();
  }

  // MDG: cleanup cached WAV files
  async function handleCleanup() {
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/audio/cleanup`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        statusText = `Cleaned ${data.count || 0} cached files`;
        setTimeout(() => { statusText = ""; }, 3000);
      }
    } catch (err) {
      logger.error("Cleanup failed", { error: err.message });
      statusText = "Cleanup failed";
      setTimeout(() => { statusText = ""; }, 3000);
    }
  }

  // ── MDG keyboard shortcuts: Space=toggle play/stop, Left/Right=prev/next ──
  function handleKeyDown(event) {
    // Skip if user is typing in search/input
    const tag = event.target?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;

    if (event.key === " ") {
      event.preventDefault();
      if (playingEvent) {
        handleStop();
      } else if (selectedEvent) {
        handlePlay(selectedEvent);
      }
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      handlePrev();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      handleNext();
    }
  }

  onMount(() => {
    fetchCategories();
    fetchAllItems();
    // MDG: global keyboard shortcuts for audio mode
    document.addEventListener("keydown", handleKeyDown);
  });

  onDestroy(() => {
    destroyed = true;
    stopStatusPolling();
    stopTreeResize();
    document.removeEventListener("keydown", handleKeyDown);
    // Stop backend playback on page leave
    fetch(`${API_BASE}/api/ldm/codex/audio/stop`, {
      method: "POST",
      headers: getAuthHeaders(),
    }).catch(() => {});
  });
</script>

<!-- MDG-exact: No browser <audio> element. Playback via backend winsound. -->
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

      <!-- MDG Row 2: Match type selector (search_panel.py) -->
      <div class="match-type-selector">
        <span class="match-label">Match:</span>
        <label class="match-radio">
          <input type="radio" name="matchType" value="contains" bind:group={matchType} />
          <span>Contains</span>
        </label>
        <label class="match-radio">
          <input type="radio" name="matchType" value="exact" bind:group={matchType} />
          <span>Exact</span>
        </label>
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
    <div class="three-panel" class:tree-resizing={isTreeResizing}>
      <!-- LEFT: Export Tree -->
      <div style="width: {treeWidth}px; flex-shrink: 0;">
        <AudioExportTree
          {categories}
          {activeCategory}
          {totalEvents}
          onselect={(path) => { activeCategory = path; }}
        />
      </div>

      <!-- Resize handle between tree and grid -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="tree-resize-handle" onmousedown={startTreeResize}></div>

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
        />
      {/if}

      <!-- RIGHT: Audio Player Panel (MDG audio_viewer.py layout) -->
      <AudioPlayerPanel
        audio={selectedAudio}
        playing={playingEvent != null}
        {currentTime}
        {duration}
        {statusText}
        onplay={() => handlePlay(selectedEvent)}
        onstop={handleStop}
        onprev={handlePrev}
        onnext={handleNext}
        oncleanup={handleCleanup}
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

  /* MDG search_panel.py Row 2: Match type radios */
  .match-type-selector {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .match-label { font-weight: 500; white-space: nowrap; }

  .match-radio {
    display: flex;
    align-items: center;
    gap: 3px;
    cursor: pointer;
    font-size: 0.75rem;
  }

  .match-radio input { cursor: pointer; margin: 0; }

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

  .tree-resize-handle {
    width: 5px;
    flex-shrink: 0;
    cursor: col-resize;
    background: transparent;
    border-right: 1px solid var(--cds-border-subtle-01);
    transition: background 0.15s;
  }

  .tree-resize-handle:hover {
    background: var(--cds-interactive-01, #0f62fe);
  }

  .three-panel.tree-resizing {
    cursor: col-resize;
    user-select: none;
  }

  .three-panel.tree-resizing .tree-resize-handle {
    background: var(--cds-interactive-01, #0f62fe);
  }
</style>
