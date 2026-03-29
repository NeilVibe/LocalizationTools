<script>
  /**
   * CodexSearchBar.svelte - Semantic search input with results dropdown
   *
   * Debounced search against /api/ldm/codex/search with AbortController
   * for cancelling in-flight requests on new input.
   *
   * Phase 19: Game World Codex (Plan 02)
   */
  import { Search, InlineLoading, Tag } from "carbon-components-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  // Props
  let { onresult = () => {} } = $props();

  // State
  let query = $state('');
  let results = $state([]);
  let loading = $state(false);
  let showDropdown = $state(false);
  let noResults = $state(false);

  // Internal (not reactive)
  let abortController = null;
  let debounceTimer = null;

  // Type badge colors (matching EntityCard pattern)
  const TYPE_COLORS = {
    character: 'purple',
    item: 'cyan',
    skill: 'magenta',
    region: 'teal',
    gimmick: 'warm-gray'
  };

  /**
   * Debounced search handler
   */
  function handleInput(e) {
    query = e.target?.value ?? e?.detail ?? '';

    // Clear previous debounce
    if (debounceTimer) clearTimeout(debounceTimer);

    // Cancel in-flight request
    if (abortController) {
      abortController.abort();
      abortController = null;
    }

    if (!query || query.length < 2) {
      results = [];
      showDropdown = false;
      noResults = false;
      loading = false;
      return;
    }

    loading = true;
    showDropdown = true;
    noResults = false;

    debounceTimer = setTimeout(() => fetchResults(query), 200);
  }

  /**
   * Fetch search results from codex API
   */
  async function fetchResults(searchQuery) {
    abortController = new AbortController();

    try {
      const params = new URLSearchParams({ q: searchQuery, limit: '10' });
      const response = await fetch(`${API_BASE}/api/ldm/codex/search?${params}`, {
        headers: getAuthHeaders(),
        signal: abortController.signal
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      results = data.results || [];
      noResults = results.length === 0;
      logger.info('Codex search results', { query: searchQuery, count: results.length });
    } catch (err) {
      if (err.name === 'AbortError') return; // Expected cancellation
      logger.error('Codex search failed', { error: err.message });
      results = [];
      noResults = true;
    } finally {
      loading = false;
    }
  }

  /**
   * Select a result
   */
  function selectResult(result) {
    onresult(result.entity);
    showDropdown = false;
    query = result.entity.name || '';
  }

  /**
   * Handle blur - close dropdown after short delay (allow click)
   */
  function handleBlur() {
    setTimeout(() => { showDropdown = false; }, 200);
  }
</script>

<div class="codex-search-bar">
  <Search
    placeholder="Search entities by name or description..."
    bind:value={query}
    oninput={handleInput}
    onclear={() => { query = ''; results = []; showDropdown = false; noResults = false; }}
    onfocus={() => { if (results.length > 0) showDropdown = true; }}
    onblur={handleBlur}
    size="lg"
  />

  {#if loading}
    <div class="search-progress" aria-hidden="true"></div>
  {/if}

  {#if showDropdown}
    <div class="search-dropdown" role="listbox" aria-label="Search results">
      {#if loading}
        <div class="search-state" role="status" aria-live="polite">
          <InlineLoading description="Searching entities..." />
        </div>
      {:else if noResults}
        <div class="search-state" role="status" aria-live="polite">
          <span class="no-results">No matching entities found -- try a different search term</span>
        </div>
      {:else}
        {#each results as result (result.entity.strkey)}
          <button
            class="search-result"
            role="option"
            aria-selected="false"
            aria-label="{result.entity.name} ({result.entity.entity_type}) -- {(result.similarity * 100).toFixed(0)}% match"
            onclick={() => selectResult(result)}
          >
            <div class="result-info">
              <span class="result-name">{result.entity.name}</span>
              <Tag type={TYPE_COLORS[result.entity.entity_type] || 'gray'} size="sm">
                {result.entity.entity_type}
              </Tag>
            </div>
            <span class="result-score">{(result.similarity * 100).toFixed(0)}%</span>
          </button>
        {/each}
      {/if}
    </div>
  {/if}
</div>

<style>
  .codex-search-bar {
    position: relative;
    width: 100%;
  }

  .search-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--cds-interactive-01, #0f62fe);
    animation: search-progress-pulse 1s ease-in-out infinite;
    z-index: 101;
  }

  @keyframes search-progress-pulse {
    0%, 100% { opacity: 0.3; transform: scaleX(0.3); transform-origin: left; }
    50% { opacity: 1; transform: scaleX(1); transform-origin: left; }
  }

  .search-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-top: none;
    border-radius: 0 0 var(--card-radius, 4px) var(--card-radius, 4px);
    max-height: 400px;
    overflow-y: auto;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: dropdown-slide 0.15s ease-out;
  }

  @keyframes dropdown-slide {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .search-state {
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .no-results {
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .search-result {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 10px 16px;
    border: none;
    background: transparent;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .search-result:hover {
    background: var(--cds-layer-hover-02);
  }

  .search-result:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .search-result:last-child {
    border-bottom: none;
  }

  .result-info {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  .result-name {
    font-size: 0.875rem;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .result-score {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    flex-shrink: 0;
    margin-left: 8px;
  }
</style>
