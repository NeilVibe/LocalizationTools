<script>
  /**
   * AISuggestionsTab.svelte - AI Translation Suggestions panel tab
   *
   * Fetches ranked AI translation suggestions from Ollama/Qwen3 backend
   * when user selects a segment. Shows confidence badges, click-to-apply.
   * Debounced fetch with AbortController prevents request flooding.
   *
   * Phase 17: AI Translation Suggestions (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { MachineLearningModel, WarningAlt } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  // Props
  let { selectedRow = null, onApplySuggestion = () => {} } = $props();

  // State
  let suggestions = $state([]);
  let loading = $state(false);
  let status = $state(null);
  let error = $state(null);

  // Internal refs (not reactive state needed for UI)
  let abortController = null;
  let debounceTimer = null;

  /**
   * Get confidence color and label
   */
  function getConfidenceColor(confidence) {
    if (confidence >= 0.85) return '#24a148';
    if (confidence >= 0.60) return '#c6a300';
    return '#ff832b';
  }

  function getConfidenceLabel(confidence) {
    if (confidence >= 0.85) return 'High';
    if (confidence >= 0.60) return 'Medium';
    return 'Low';
  }

  /**
   * Apply a suggestion to the translation field
   */
  function handleApplySuggestion(suggestion) {
    onApplySuggestion({ target: suggestion.text });
    logger.userAction('Apply AI suggestion', { confidence: suggestion.confidence });
  }

  // Debounced fetch on row selection change
  $effect(() => {
    const stringId = selectedRow?.string_id;

    // Cancel previous requests
    if (abortController) abortController.abort();
    if (debounceTimer) clearTimeout(debounceTimer);

    if (!stringId) {
      suggestions = [];
      status = null;
      error = null;
      loading = false;
      return;
    }

    loading = true;
    error = null;

    debounceTimer = setTimeout(() => {
      const controller = new AbortController();
      abortController = controller;

      const sourceText = selectedRow?.source || selectedRow?.eng || '';
      const params = new URLSearchParams();
      if (sourceText) params.set('source_text', sourceText);
      params.set('target_lang', 'KR');

      const url = `${API_BASE}/api/ldm/ai-suggestions/${encodeURIComponent(stringId)}?${params.toString()}`;

      fetch(url, {
        headers: getAuthHeaders(),
        signal: controller.signal
      })
        .then(async (response) => {
          if (response.ok) {
            const data = await response.json();
            suggestions = data.suggestions || [];
            status = data.status || 'generated';
          } else if (response.status === 503) {
            suggestions = [];
            status = 'unavailable';
          } else {
            throw new Error(`HTTP ${response.status}`);
          }
        })
        .catch((err) => {
          if (err.name === 'AbortError') return; // Expected during rapid navigation
          logger.error('Failed to fetch AI suggestions', { error: err.message });
          error = err.message;
          status = 'error';
          suggestions = [];
        })
        .finally(() => {
          // Only clear loading if this controller wasn't aborted
          if (!controller.signal.aborted) {
            loading = false;
          }
        });
    }, 500);

    // Cleanup on effect re-run
    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      loading = false;
    };
  });
</script>

<div class="ai-suggestions-tab">
  {#if loading}
    <div class="suggestions-loading" data-testid="ai-suggestions-loading">
      <InlineLoading description="Generating suggestions..." />
    </div>
  {:else if !selectedRow}
    <div class="suggestions-empty" data-testid="ai-suggestions-empty">
      <MachineLearningModel size={32} />
      <span class="empty-title">No Row Selected</span>
      <span class="empty-desc">Select a segment to see AI suggestions</span>
    </div>
  {:else if status === 'unavailable'}
    <div class="suggestions-empty" data-testid="ai-suggestions-unavailable">
      <WarningAlt size={32} />
      <span class="empty-title">AI Unavailable</span>
      <span class="empty-desc">Ollama service is not running. Start Ollama to enable AI suggestions.</span>
    </div>
  {:else if error}
    <div class="suggestions-empty" data-testid="ai-suggestions-error">
      <WarningAlt size={32} />
      <span class="empty-title">Error</span>
      <span class="empty-desc">{error}</span>
    </div>
  {:else if suggestions.length === 0}
    <div class="suggestions-empty" data-testid="ai-suggestions-no-results">
      <MachineLearningModel size={32} />
      <span class="empty-title">No Suggestions</span>
      <span class="empty-desc">No AI suggestions available for this segment</span>
    </div>
  {:else}
    <div class="suggestions-list" data-testid="ai-suggestions-results">
      {#each suggestions as suggestion (suggestion.text)}
        {@const color = getConfidenceColor(suggestion.confidence)}
        {@const label = getConfidenceLabel(suggestion.confidence)}
        <button
          class="suggestion-card"
          onclick={() => handleApplySuggestion(suggestion)}
          title="Click to apply this suggestion"
          data-testid="ai-suggestion-card"
        >
          <div class="suggestion-header">
            <span class="confidence-badge" style="background: {color};">
              {Math.round(suggestion.confidence * 100)}%
            </span>
            <span class="confidence-label" style="color: {color};">{label}</span>
          </div>
          <div class="suggestion-text">{suggestion.text}</div>
          {#if suggestion.reasoning}
            <div class="suggestion-reasoning">{suggestion.reasoning}</div>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .ai-suggestions-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .suggestions-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
  }

  .suggestions-empty {
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

  .suggestions-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Suggestion card */
  .suggestion-card {
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

  .suggestion-card:hover {
    border-color: var(--cds-interactive-01);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  }

  /* Header with confidence badge */
  .suggestion-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .confidence-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.6875rem;
    font-weight: 600;
    color: #fff;
    letter-spacing: 0.3px;
  }

  .confidence-label {
    font-size: 0.6875rem;
    font-weight: 500;
  }

  /* Suggestion text */
  .suggestion-text {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    font-weight: 500;
    line-height: 1.5;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  /* Reasoning */
  .suggestion-reasoning {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-style: italic;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
</style>
