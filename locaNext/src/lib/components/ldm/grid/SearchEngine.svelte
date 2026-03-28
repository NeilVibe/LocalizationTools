<script>
  /**
   * SearchEngine.svelte -- Semantic search, search config, filter orchestration.
   *
   * Phase 84 Batch 3: Extracted from VirtualGrid.svelte.
   * Owns search term state, search modes, field selection, semantic search,
   * filter/category changes, and search-related markup.
   *
   * Writes to gridState: grid.activeFilter, grid.selectedCategories, grid.rows (clear), loadedPages (clear)
   * Reads from gridState: grid
   */

  import { ChevronDown, MachineLearningModel } from "carbon-icons-svelte";
  import { Dropdown } from "carbon-components-svelte";
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import CategoryFilter from '../CategoryFilter.svelte';
  import SemanticResults from '../SemanticResults.svelte';
  import {
    grid,
    loadedPages,
    rowIndexById,
  } from './gridState.svelte.ts';

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Props via $props() (per D-05)
  let {
    fileId = null,
    fileType = "translator",
    activeTMs = [],
    // Callback to trigger row reload after filter/search change
    onSearchComplete = undefined,
    // Callback to scroll to a row by ID (e.g. semantic result click)
    onScrollToRow = undefined,
  } = $props();

  // ============================================================
  // SEARCH STATE (grid.searchTerm/searchMode/searchFields in gridState)
  // ============================================================
  let searchDebounceTimer = null;

  const filterOptions = [
    { id: "all", text: "All Rows" },
    { id: "confirmed", text: "Confirmed" },
    { id: "unconfirmed", text: "Unconfirmed" },
    { id: "qa_flagged", text: "QA Flagged" }
  ];

  // P5: Advanced Search state
  const searchModeOptions = [
    { id: "contain", text: "Contains", icon: "\u2283" },
    { id: "exact", text: "Exact", icon: "=" },
    { id: "not_contain", text: "Excludes", icon: "\u2260" },
    { id: "fuzzy", text: "Similar", icon: "\u2248" }
  ];

  const searchFieldOptions = [
    { id: "string_id", text: "ID" },
    { id: "source", text: "Source" },
    { id: "target", text: "Target" }
  ];

  let showSearchSettings = $state(false);

  // P4: Semantic search state
  let semanticResults = $state([]);
  let semanticSearchTime = $state(0);
  let semanticLoading = $state(false);

  // Search state lives in grid.searchTerm, grid.searchMode, grid.searchFields (gridState.svelte.ts)

  // ============================================================
  // SEARCH FUNCTIONS
  // ============================================================

  /** Handle search with debounce.
   * Does NOT clear rows until new results arrive — prevents blank flash.
   * Only clears loadedPages so loadRows() fetches fresh filtered data.
   */
  function handleSearch() {
    logger.info("handleSearch triggered", { searchTerm: grid.searchTerm, searchMode: grid.searchMode });
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      if (grid.searchMode === 'fuzzy') {
        performSemanticSearch();
        return;
      }
      semanticResults = [];
      semanticSearchTime = 0;

      logger.info("handleSearch executing search", { searchTerm: grid.searchTerm });
      loadedPages.clear();
      rowIndexById.clear();  // Prevent stale scroll targets after search
      // Don't clear grid.rows here — let loadRows() replace them with filtered results.
      // Clearing rows caused a blank flash while the API fetched new data.
      onSearchComplete?.();
    }, 300);
  }

  /** P4: Perform semantic search via API */
  async function performSemanticSearch() {
    const query = grid.searchTerm?.trim();
    if (!query) {
      semanticResults = [];
      semanticSearchTime = 0;
      return;
    }

    if (!activeTMs || activeTMs.length === 0) {
      semanticResults = [];
      semanticSearchTime = 0;
      logger.info("Semantic search skipped - no active TMs");
      return;
    }

    semanticLoading = true;
    try {
      const tmId = activeTMs[0].tm_id;
      const params = new URLSearchParams({
        query,
        tm_id: tmId.toString(),
        threshold: '0.5',
        max_results: '20'
      });

      logger.apiCall(`/api/ldm/semantic-search?${params}`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/semantic-search?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        semanticResults = data.results || [];
        semanticSearchTime = data.search_time_ms || 0;
        logger.info("Semantic search results", { count: semanticResults.length, timeMs: semanticSearchTime });
      } else {
        logger.error("Semantic search failed", { status: response.status });
        semanticResults = [];
      }
    } catch (err) {
      logger.error("Semantic search error", { error: err.message });
      semanticResults = [];
    } finally {
      semanticLoading = false;
    }
  }

  /** Handle semantic result selection */
  function handleSemanticResultSelect(result) {
    const matchRow = grid.rows.find(r => r && r.source === result.source_text);
    if (matchRow) {
      onScrollToRow?.(matchRow.id);
    }
    semanticResults = [];
    semanticSearchTime = 0;
    logger.userAction("Semantic result selected", { source: result.source_text?.substring(0, 30) });
  }

  function closeSemanticResults() {
    semanticResults = [];
    semanticSearchTime = 0;
  }

  /** Handle filter change */
  function handleFilterChange(event) {
    grid.activeFilter = event.detail.selectedId;
    loadedPages.clear();
    grid.rows = [];
    onSearchComplete?.();
    logger.userAction("Filter changed", { filter: grid.activeFilter });
  }

  /** Handle category filter change */
  function handleCategoryFilterChange(categories) {
    grid.selectedCategories = categories;
    loadedPages.clear();
    grid.rows = [];
    onSearchComplete?.();
    logger.userAction("Category filter changed", { categories: grid.selectedCategories });
  }

  // onScrollToRow is now received via $props() — no delegate needed (FIX-01)

  // ============================================================
  // RESET (called by parent on file change)
  // ============================================================
  export function resetSearch() {
    grid.searchTerm = "";
    semanticResults = [];
    semanticSearchTime = 0;
  }

  // ============================================================
  // EFFECT: Watch searchTerm changes ONLY (not other grid props)
  // Uses $derived to isolate searchTerm from the grid $state object.
  // Without this, ANY grid mutation (total, rows, rowsVersion) would
  // re-trigger the effect → handleSearch → loadRows → grid mutation → LOOP.
  // ============================================================
  let searchTermDerived = $derived(grid.searchTerm);

  $effect(() => {
    const term = searchTermDerived;
    if (fileId && term !== undefined) {
      handleSearch();
    }
  });
</script>

<div class="search-filter-bar">
  <!-- P5: Combined Search Control -->
  <div class="search-control">
    <!-- Mode indicator button -->
    <button
      class="search-mode-btn"
      onclick={() => showSearchSettings = !showSearchSettings}
      title="Search settings"
    >
      <span class="mode-icon">{searchModeOptions.find(m => m.id === grid.searchMode)?.icon || "\u2283"}</span>
      <ChevronDown size={12} />
    </button>

    <!-- Search input -->
    <div class="search-input-wrapper">
      <input
        type="text"
        id="ldm-search-input"
        class="search-input"
        placeholder="Search {grid.searchFields.join(', ')}..."
        value={grid.searchTerm}
        oninput={(e) => {
          grid.searchTerm = e.target.value;
        }}
      />
      {#if grid.searchTerm}
        <button
          type="button"
          class="search-clear"
          onclick={() => {
            grid.searchTerm = "";
          }}
          aria-label="Clear search"
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <path d="M12 4.7L11.3 4 8 7.3 4.7 4 4 4.7 7.3 8 4 11.3 4.7 12 8 8.7 11.3 12 12 11.3 8.7 8z"/>
          </svg>
        </button>
      {/if}
    </div>

    <!-- Settings popover -->
    {#if showSearchSettings}
      <div class="search-settings-popover">
        <div class="settings-section">
          <div class="settings-label">Mode</div>
          <div class="mode-buttons">
            {#each searchModeOptions as mode (mode.id)}
              <button
                class="mode-option {grid.searchMode === mode.id ? 'active' : ''}"
                onclick={() => { grid.searchMode = mode.id; if (grid.searchTerm) handleSearch(); }}
                title={mode.text}
              >
                <span class="mode-option-icon">{mode.icon}</span>
                <span class="mode-option-text">{mode.text}</span>
              </button>
            {/each}
          </div>
        </div>
        <div class="settings-section">
          <div class="settings-label">Fields</div>
          <div class="field-toggles">
            {#each searchFieldOptions as field (field.id)}
              <label class="field-toggle {grid.searchFields.includes(field.id) ? 'active' : ''}">
                <input
                  type="checkbox"
                  checked={grid.searchFields.includes(field.id)}
                  onchange={(e) => {
                    if (e.target.checked) {
                      grid.searchFields = [...grid.searchFields, field.id];
                    } else {
                      grid.searchFields = grid.searchFields.filter(f => f !== field.id);
                    }
                    if (grid.searchTerm) handleSearch();
                  }}
                />
                <span>{field.text}</span>
              </label>
            {/each}
          </div>
        </div>
      </div>
      <!-- Backdrop to close popover -->
      <div class="settings-backdrop" onclick={() => showSearchSettings = false}></div>
    {/if}

    <!-- P4: Semantic Search Results Overlay (fuzzy/Similar mode) -->
    {#if grid.searchMode === 'fuzzy' && (!activeTMs || activeTMs.length === 0) && grid.searchTerm?.trim()}
      <div class="semantic-no-tm">
        <MachineLearningModel size={14} />
        Assign a TM to enable semantic search
      </div>
    {/if}
    <SemanticResults
      bind:results={semanticResults}
      searchTimeMs={semanticSearchTime}
      visible={grid.searchMode === 'fuzzy' && semanticResults.length > 0}
      onSelect={handleSemanticResultSelect}
      onClose={closeSemanticResults}
    />
  </div>

  <!-- P2: Filter Dropdown -->
  <div class="filter-wrapper">
    <Dropdown
      size="sm"
      selectedId={grid.activeFilter}
      items={filterOptions}
      on:select={handleFilterChange}
      titleText=""
      hideLabel
    />
  </div>

  <!-- P16: Category Filter -->
  {#if fileType !== 'gamedev'}
    <CategoryFilter
      bind:selectedCategories={grid.selectedCategories}
      onchange={handleCategoryFilterChange}
    />
  {/if}
</div>

<style>
  /* P2: Search + Filter bar layout */
  .search-filter-bar {
    display: flex;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    align-items: center;
  }

  .filter-wrapper {
    flex: 0 0 160px;
  }

  .filter-wrapper :global(.bx--dropdown) {
    background: var(--cds-field-01);
    height: 2rem;
  }

  .filter-wrapper :global(.bx--list-box) {
    height: 2rem;
  }

  .filter-wrapper :global(.bx--list-box__field) {
    height: 2rem;
  }

  /* P5: Combined Search Control */
  .search-control {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 200px;
    position: relative;
  }

  .search-mode-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 0 8px;
    height: 2rem;
    background: var(--cds-field-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-right: none;
    border-radius: 4px 0 0 4px;
    cursor: pointer;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    transition: background 0.15s;
  }

  .search-mode-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .mode-icon {
    font-size: 1rem;
    font-weight: 500;
  }

  .search-input-wrapper {
    flex: 1;
    position: relative;
  }

  .search-input {
    width: 100%;
    height: 2rem;
    padding: 0 2rem 0 0.75rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 0 4px 4px 0;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    outline: none;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: inset 0 0 0 1px var(--cds-focus);
  }

  .search-input::placeholder {
    color: var(--cds-text-05);
  }

  .search-clear {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--cds-text-02);
    border-radius: 2px;
  }

  .search-clear:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  /* Search Settings Popover */
  .search-settings-popover {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    z-index: 1000;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    padding: 12px;
    min-width: 280px;
  }

  .settings-section {
    margin-bottom: 12px;
  }

  .settings-section:last-child {
    margin-bottom: 0;
  }

  .settings-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .mode-buttons {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
  }

  .mode-option {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--cds-text-02);
  }

  .mode-option:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .mode-option.active {
    background: var(--cds-interactive-01);
    border-color: var(--cds-interactive-01);
    color: var(--cds-text-on-color);
  }

  .mode-option-icon {
    font-size: 1rem;
    font-weight: 600;
  }

  .mode-option-text {
    font-size: 0.8rem;
  }

  .field-toggles {
    display: flex;
    gap: 6px;
  }

  .field-toggle {
    display: flex;
    align-items: center;
    padding: 6px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.8rem;
    color: var(--cds-text-02);
  }

  .field-toggle:hover {
    background: var(--cds-layer-hover-01);
  }

  .field-toggle.active {
    background: var(--cds-interactive-02);
    border-color: var(--cds-interactive-02);
    color: var(--cds-text-on-color);
  }

  .field-toggle input[type="checkbox"] {
    display: none;
  }

  .settings-backdrop {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  /* P4: Semantic search no-TM message */
  .semantic-no-tm {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 1001;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    font-size: 0.8rem;
    color: var(--cds-text-02);
  }
</style>
