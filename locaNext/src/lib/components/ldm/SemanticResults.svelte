<script>
  /**
   * SemanticResults.svelte - Dropdown overlay for semantic search results
   *
   * Shows similarity-scored results from Model2Vec semantic search.
   * Renders as absolute-positioned dropdown below the search bar.
   * Supports keyboard navigation (Escape to close).
   */
  import { MachineLearningModel } from "carbon-icons-svelte";

  // Props (Svelte 5 runes)
  let {
    results = $bindable([]),
    searchTimeMs = 0,
    visible = false,
    onSelect = () => {},
    onClose = () => {}
  } = $props();

  // Derived: sorted results (highest similarity first)
  let sortedResults = $derived(
    [...results].sort((a, b) => b.similarity - a.similarity)
  );

  /**
   * Get color for similarity score badge
   * Matches TMTab color system: green >= 100%, yellow >= 75%, orange >= 50%
   */
  function getScoreColor(similarity) {
    const pct = similarity * 100;
    if (pct >= 100) return '#24a148';  // Green - exact
    if (pct >= 75) return '#c6a300';   // Yellow - high fuzzy
    if (pct >= 50) return '#ff832b';   // Orange - fuzzy
    return '#da1e28';                  // Red - low
  }

  /**
   * Get label for similarity tier
   */
  function getScoreLabel(similarity) {
    const pct = similarity * 100;
    if (pct >= 100) return 'Exact';
    if (pct >= 75) return 'High';
    if (pct >= 50) return 'Fuzzy';
    return 'Low';
  }

  /**
   * Truncate text for display
   */
  function truncate(text, maxLen = 60) {
    if (!text) return '';
    return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
  }

  /**
   * Handle keyboard events (Escape to close)
   */
  function handleKeydown(event) {
    if (event.key === 'Escape') {
      onClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if visible && sortedResults.length > 0}
  <!-- Backdrop to close on click outside -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="semantic-backdrop" onclick={onClose}></div>

  <div class="semantic-results" role="listbox" aria-label="Semantic search results">
    <div class="results-header">
      <MachineLearningModel size={14} />
      <span class="results-title">Semantic Results</span>
      <span class="results-count">{sortedResults.length} match{sortedResults.length !== 1 ? 'es' : ''}</span>
    </div>

    <div class="results-list">
      {#each sortedResults as result, i (i)}
        {@const scoreColor = getScoreColor(result.similarity)}
        {@const scorePct = Math.round(result.similarity * 100)}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
          class="result-row"
          role="option"
          tabindex="0"
          onclick={() => onSelect(result)}
        >
          <div class="result-score" style="background: {scoreColor};">
            {scorePct}%
          </div>
          <div class="result-texts">
            <div class="result-source">{truncate(result.source_text)}</div>
            <div class="result-target">{truncate(result.target_text)}</div>
          </div>
          <div class="result-tier" title={getScoreLabel(result.similarity)}>
            {result.match_type || getScoreLabel(result.similarity)}
          </div>
        </div>
      {/each}
    </div>

    {#if searchTimeMs > 0}
      <div class="results-footer">
        Found {sortedResults.length} results in {searchTimeMs.toFixed(0)}ms
      </div>
    {/if}
  </div>
{/if}

<style>
  .semantic-backdrop {
    position: fixed;
    inset: 0;
    z-index: 998;
  }

  .semantic-results {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 1001;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
    max-height: 360px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .results-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    font-size: 0.75rem;
  }

  .results-title {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .results-count {
    margin-left: auto;
    color: var(--cds-text-03);
  }

  .results-list {
    overflow-y: auto;
    flex: 1;
  }

  .result-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    cursor: pointer;
    transition: background 0.1s;
    border-bottom: 1px solid var(--cds-border-subtle-00);
  }

  .result-row:hover {
    background: var(--cds-layer-hover-01);
  }

  .result-row:last-child {
    border-bottom: none;
  }

  .result-score {
    flex: 0 0 auto;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #fff;
    min-width: 42px;
    text-align: center;
  }

  .result-texts {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .result-source {
    font-size: 0.8rem;
    color: var(--cds-text-02);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-target {
    font-size: 0.8rem;
    color: var(--cds-text-01);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-tier {
    flex: 0 0 auto;
    font-size: 0.65rem;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .results-footer {
    padding: 6px 12px;
    border-top: 1px solid var(--cds-border-subtle-01);
    font-size: 0.7rem;
    color: var(--cds-text-03);
    text-align: center;
    background: var(--cds-layer-02);
  }
</style>
