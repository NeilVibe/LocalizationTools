<script>
  /**
   * NamingPanel.svelte - Debounced naming suggestions panel
   *
   * Shows similar entity names (via FAISS) and AI naming suggestions (via Qwen3)
   * when editing a Name field in Game Dev mode. Uses 500ms debounce + AbortController
   * to prevent request flooding.
   *
   * Phase 21: AI Naming Coherence + Placeholders (Plan 02)
   */
  import { InlineLoading, Tag } from "carbon-components-svelte";
  import { WarningAlt } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  // Props
  let { editingName = '', entityType = '', onApply = null } = $props();

  // State
  let similarNames = $state([]);
  let aiSuggestions = $state([]);
  let loading = $state(false);
  let status = $state('idle');

  // Internal (not reactive UI state)
  let abortController = null;
  let debounceTimer = null;

  /**
   * Get confidence color (same thresholds as AISuggestionsTab)
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
   * Handle clicking a suggestion -- copy to clipboard (respects AINAME-03: never auto-replace)
   */
  async function handleApply(name) {
    if (onApply) {
      onApply(name);
    } else {
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(name);
        logger.userAction('Name copied to clipboard', { name });
      } catch {
        logger.warning('Clipboard copy failed', { name });
      }
    }
  }

  // Debounced fetch on editingName changes
  $effect(() => {
    const name = editingName;
    const type = entityType;

    // Cancel previous
    if (abortController) abortController.abort();
    if (debounceTimer) clearTimeout(debounceTimer);

    if (!name || name.length < 2) {
      similarNames = [];
      aiSuggestions = [];
      loading = false;
      status = 'idle';
      return;
    }

    loading = true;

    debounceTimer = setTimeout(() => {
      const controller = new AbortController();
      abortController = controller;

      const params = new URLSearchParams({ name });
      const url = `${API_BASE}/api/ldm/naming/suggest/${encodeURIComponent(type || 'character')}?${params}`;

      fetch(url, {
        headers: getAuthHeaders(),
        signal: controller.signal
      })
        .then(async (response) => {
          if (response.ok) {
            const data = await response.json();
            similarNames = data.similar_names || [];
            aiSuggestions = data.suggestions || [];
            status = data.status || 'ok';
          } else if (response.status === 503) {
            similarNames = [];
            aiSuggestions = [];
            status = 'unavailable';
          } else {
            throw new Error(`HTTP ${response.status}`);
          }
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;
          logger.error('Failed to fetch naming suggestions', { error: err.message });
          similarNames = [];
          aiSuggestions = [];
          status = 'error';
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            loading = false;
          }
        });
    }, 500);

    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      if (abortController) abortController.abort();
      loading = false;
    };
  });
</script>

<div class="naming-panel">
  <div class="panel-header">
    <span class="panel-title">Naming Suggestions</span>
    {#if loading}
      <span role="status" aria-live="polite">
        <InlineLoading description="Searching for similar names..." />
      </span>
    {/if}
  </div>

  {#if status === 'unavailable'}
    <div class="panel-info">
      <WarningAlt size={14} />
      <span>AI unavailable -- showing similar names only</span>
    </div>
  {/if}

  {#if status === 'error'}
    <div class="panel-empty" role="alert" aria-live="assertive">Could not load naming suggestions -- check your connection or try again.</div>
  {:else if !loading && !editingName}
    <div class="panel-empty">Select a Name field to see naming suggestions</div>
  {:else if !loading && editingName && editingName.length < 2}
    <div class="panel-empty">Type at least 2 characters to search for similar names</div>
  {:else if !loading && similarNames.length === 0 && aiSuggestions.length === 0 && status !== 'idle'}
    <div class="panel-empty">No similar names found -- this name appears to be unique</div>
  {/if}

  <!-- Similar Names section -->
  {#if similarNames.length > 0}
    <div class="panel-section">
      <span class="section-label">Similar Names</span>
      <div class="tags-list">
        {#each similarNames as item (item.strkey)}
          <button class="name-tag" onclick={() => handleApply(item.name)} title="Click to apply: {item.name}">
            <span class="name-text">{item.name}</span>
            <span class="similarity-badge">{Math.round(item.similarity * 100)}%</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- AI Suggestions section -->
  {#if aiSuggestions.length > 0}
    <div class="panel-section">
      <span class="section-label">AI Suggestions</span>
      <div class="suggestions-list">
        {#each aiSuggestions as suggestion (suggestion.name)}
          {@const color = getConfidenceColor(suggestion.confidence)}
          {@const label = getConfidenceLabel(suggestion.confidence)}
          <button class="suggestion-item" onclick={() => handleApply(suggestion.name)} title="Click to apply: {suggestion.name}">
            <div class="suggestion-header">
              <span class="suggestion-name">{suggestion.name}</span>
              <span class="confidence-badge" style="background: {color};">{Math.round(suggestion.confidence * 100)}% {label}</span>
            </div>
            {#if suggestion.reasoning}
              <span class="suggestion-reasoning">{suggestion.reasoning}</span>
            {/if}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .naming-panel {
    max-height: 200px;
    overflow-y: auto;
    border-top: 1px solid var(--cds-border-subtle);
    padding: 8px 12px;
    background: var(--cds-layer-01);
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  .panel-title {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .panel-info {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: var(--cds-text-03);
    margin-bottom: 6px;
  }

  .panel-empty {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
    padding: 4px 0;
  }

  .panel-section {
    margin-bottom: 8px;
  }

  .section-label {
    display: block;
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .tags-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .name-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 12px;
    cursor: pointer;
    font-size: 0.75rem;
    color: var(--cds-text-01);
    transition: background 0.15s, border-color 0.15s;
  }

  .name-tag:hover {
    background: var(--cds-layer-hover-02);
    border-color: var(--cds-interactive-01);
  }

  .name-tag:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .name-text {
    font-weight: 500;
  }

  .similarity-badge {
    font-size: 0.625rem;
    color: var(--cds-text-03);
  }

  .suggestions-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .suggestion-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px 8px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    width: 100%;
    transition: border-color 0.15s;
  }

  .suggestion-item:hover {
    border-color: var(--cds-interactive-01);
  }

  .suggestion-item:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .suggestion-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .suggestion-name {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--cds-text-01);
    overflow-wrap: break-word;
  }

  .confidence-badge {
    display: inline-flex;
    padding: 1px 6px;
    border-radius: 8px;
    font-size: 0.625rem;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
  }

  .suggestion-reasoning {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-style: italic;
    line-height: 1.3;
    overflow-wrap: break-word;
  }
</style>
