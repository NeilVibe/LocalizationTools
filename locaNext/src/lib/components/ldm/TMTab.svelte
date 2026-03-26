<script>
  /**
   * TMTab.svelte - TM matches display with color-coded percentages and word-level diff
   *
   * Features:
   * - Color-coded percentage badges (green=exact, yellow=high fuzzy, orange=fuzzy, red=low)
   * - Word-level diff highlighting for fuzzy matches
   * - Korean syllable-level diff granularity
   * - Loading/empty states
   * - Apply TM on click (dispatches applyTM event)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Search, Checkmark } from "carbon-icons-svelte";
  import { computeWordDiff } from "$lib/utils/wordDiff.js";
  import { logger } from "$lib/utils/logger.js";

  // Props — read-only data from GridPage, callbacks for actions
  let {
    selectedRow = null,
    tmMatches = [],
    tmLoading = false,
    leverageStats = null,
    onApplyTM = undefined
  } = $props();

  /**
   * Get color info for a match score
   * @param {number} score - similarity score 0-1
   */
  function getMatchColor(score) {
    if (score >= 1.0) {
      return { color: 'var(--cds-support-success, #24a148)', label: 'Exact', type: 'green' };
    } else if (score >= 0.92) {
      return { color: 'var(--cds-support-success, #24a148)', label: 'High', type: 'green' };
    } else if (score >= 0.75) {
      return { color: 'var(--cds-support-warning, #c6a300)', label: 'Fuzzy', type: 'yellow' };
    } else if (score >= 0.62) {
      return { color: 'var(--cds-support-caution-minor, #ff832b)', label: 'Low Fuzzy', type: 'orange' };
    } else {
      return { color: 'var(--cds-support-error, #da1e28)', label: 'Below Threshold', type: 'red' };
    }
  }

  /**
   * Apply a TM match
   */
  function handleApplyTM(match) {
    onApplyTM?.(match);
    logger.userAction('Apply TM from TMTab', { similarity: match.similarity });
  }

  /**
   * Compute diff tokens for a fuzzy match source vs current source
   * Returns { original, match } arrays with type annotations
   */
  function getDiffTokens(match) {
    if (!selectedRow?.source || !match.source) return null;
    if (match.similarity >= 1.0) return null; // No diff for exact matches
    return computeWordDiff(selectedRow.source, match.source);
  }
</script>

<div class="tm-tab">
  <!-- Leverage stats bar -->
  {#if leverageStats}
    <div class="leverage-section" data-testid="leverage-stats">
      {#if leverageStats.total === 0}
        <div class="leverage-empty">No segments to analyze</div>
      {:else}
        <div class="leverage-bar">
          {#if leverageStats.exact_pct > 0}
            <div class="leverage-segment exact" style="width: {leverageStats.exact_pct}%;" title="Exact: {leverageStats.exact_pct}%"></div>
          {/if}
          {#if leverageStats.fuzzy_pct > 0}
            <div class="leverage-segment fuzzy" style="width: {leverageStats.fuzzy_pct}%;" title="Fuzzy: {leverageStats.fuzzy_pct}%"></div>
          {/if}
          {#if leverageStats.new_pct > 0}
            <div class="leverage-segment new" style="width: {leverageStats.new_pct}%;" title="New: {leverageStats.new_pct}%"></div>
          {/if}
        </div>
        <div class="leverage-text">
          {leverageStats.exact_pct}% exact | {leverageStats.fuzzy_pct}% fuzzy | {leverageStats.new_pct}% new
        </div>
      {/if}
    </div>
  {/if}

  {#if tmLoading}
    <div class="tm-loading">
      <InlineLoading description="Searching TM..." />
    </div>
  {:else if !selectedRow}
    <div class="empty-msg">
      <Search size={16} />
      <span>Select a segment to see TM matches</span>
    </div>
  {:else if tmMatches.length > 0}
    <div class="tm-matches">
      {#each tmMatches as match, idx (match.row_id || match.entry_id || idx)}
        {@const colorInfo = getMatchColor(match.similarity)}
        {@const diff = getDiffTokens(match)}
        <button
          class="tm-match-card"
          onclick={() => handleApplyTM(match)}
          title="Click to apply this translation"
        >
          <div class="tm-match-header">
            <span
              class="match-badge"
              style="background: {colorInfo.color};"
            >
              {Math.round(match.similarity * 100)}%
            </span>
            <span class="match-label" style="color: {colorInfo.color};">{colorInfo.label}</span>
            {#if idx === 0}
              <span class="tm-hint">Tab to apply</span>
            {/if}
          </div>

          <!-- Source text with diff highlighting for fuzzy matches -->
          <div class="tm-source">
            <span class="field-label">Source:</span>
            {#if diff}
              <span class="diff-text">
                {#each diff.match as token, i (i)}
                  {#if token.type === 'added'}
                    <span class="diff-added">{token.text}</span>
                  {:else}
                    <span class="diff-same">{token.text}</span>
                  {/if}
                {/each}
              </span>
            {:else}
              <span class="source-text">{match.source}</span>
            {/if}
          </div>

          <!-- Current source diff (what's in current row but not in TM) -->
          {#if diff}
            <div class="tm-source-current">
              <span class="field-label">Current:</span>
              <span class="diff-text">
                {#each diff.original as token, i (i)}
                  {#if token.type === 'removed'}
                    <span class="diff-removed">{token.text}</span>
                  {:else}
                    <span class="diff-same">{token.text}</span>
                  {/if}
                {/each}
              </span>
            </div>
          {/if}

          <!-- Target text -->
          <div class="tm-target">
            <span class="field-label">Target:</span>
            <span class="target-text">{match.target}</span>
          </div>

          <!-- Metadata -->
          {#if match.tm_name || match.source_type || match.created_by}
            <div class="tm-meta">
              {#if match.tm_name}
                <span class="meta-tm">{match.tm_name}</span>
              {/if}
              {#if match.source_type}
                <span class="meta-tag">{match.source_type}</span>
              {/if}
              {#if match.created_by}
                <span class="meta-user">by {match.created_by}</span>
              {/if}
            </div>
          {/if}
        </button>
      {/each}
    </div>
  {:else}
    <div class="empty-msg muted">
      <Search size={16} />
      <span>No TM matches found</span>
    </div>
  {/if}
</div>

<style>
  .tm-tab {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
  }

  /* Leverage stats bar */
  .leverage-section {
    padding: 8px 0 10px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    margin-bottom: 8px;
    flex-shrink: 0;
  }

  .leverage-bar {
    display: flex;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    background: var(--cds-layer-02);
  }

  .leverage-segment {
    transition: width 0.3s ease;
  }

  .leverage-segment.exact {
    background: #24a148;
  }

  .leverage-segment.fuzzy {
    background: #c6a300;
  }

  .leverage-segment.new {
    background: var(--cds-text-05, #6f6f6f);
  }

  .leverage-text {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    margin-top: 4px;
    text-align: center;
    letter-spacing: 0.2px;
  }

  .leverage-empty {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    text-align: center;
    font-style: italic;
  }

  .tm-loading {
    display: flex;
    justify-content: center;
    padding: 1.5rem;
  }

  .tm-matches {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Match card */
  .tm-match-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    width: 100%;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .tm-match-card:hover {
    border-color: var(--cds-interactive-01);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  }

  /* Header with badge */
  .tm-match-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .match-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 600;
    color: #fff;
    letter-spacing: 0.3px;
    line-height: 1;
  }

  .match-label {
    font-size: 0.75rem;
    font-weight: 500;
  }

  .tm-hint {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-01);
    padding: 1px 6px;
    border-radius: 3px;
    margin-left: auto;
  }

  /* Field labels */
  .field-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-right: 4px;
    flex-shrink: 0;
  }

  /* Source and target text */
  .tm-source,
  .tm-source-current,
  .tm-target {
    display: flex;
    align-items: baseline;
    font-size: 0.75rem;
    line-height: 1.5;
    overflow: hidden;
  }

  .source-text {
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .target-text {
    color: var(--cds-text-01);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  /* Diff highlighting */
  .diff-text {
    display: inline;
    word-break: break-word;
  }

  .diff-same {
    color: var(--cds-text-02);
  }

  .diff-added {
    background: rgba(36, 161, 72, 0.2);
    color: #24a148;
    border-radius: 2px;
    padding: 0 1px;
  }

  .diff-removed {
    background: rgba(218, 30, 40, 0.15);
    color: #da1e28;
    text-decoration: line-through;
    border-radius: 2px;
    padding: 0 1px;
  }

  /* Metadata */
  .tm-meta {
    display: flex;
    gap: 6px;
    font-size: 0.625rem;
    color: var(--cds-text-03);
    margin-top: 2px;
    flex-wrap: wrap;
  }

  .meta-tm {
    background: var(--cds-support-info, #4589ff);
    color: #fff;
    padding: 1px 5px;
    border-radius: 3px;
    font-weight: 500;
  }

  .meta-tag {
    background: var(--cds-layer-01);
    padding: 1px 5px;
    border-radius: 3px;
  }

  .meta-user {
    font-style: italic;
  }

  /* Empty states */
  .empty-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-style: italic;
    padding: 2rem 1rem;
    text-align: center;
  }

  .empty-msg.muted {
    opacity: 0.7;
  }
</style>
