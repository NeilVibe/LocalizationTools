<script>
  /**
   * ContextTab.svelte - AI Context tab for entity display
   *
   * Fetches detected entities from ContextService when user selects a row.
   * Shows character metadata, location images, audio samples, and highlighted
   * detected terms. Graceful degradation when service not configured.
   *
   * Phase 5.1: Contextual Intelligence & QA Engine (Plan 05)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { MachineLearningModel, SettingsAdjust, WarningAlt } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import EntityCard from "$lib/components/ldm/EntityCard.svelte";

  const API_BASE = getApiBase();

  // Props
  let { selectedRow = null } = $props();

  // State
  let entities = $state([]);
  let detectedTerms = $state([]);
  let loading = $state(false);
  let error = $state(null);
  let notConfigured = $state(false);
  let aiSummary = $state(null);
  let aiStatus = $state(null);

  // Fetch context when selected row changes (with AbortController for cleanup)
  $effect(() => {
    const stringId = selectedRow?.string_id;
    if (!stringId) {
      entities = [];
      detectedTerms = [];
      error = null;
      notConfigured = false;
      aiSummary = null;
      aiStatus = null;
      return;
    }

    loading = true;
    error = null;
    notConfigured = false;

    const controller = new AbortController();
    const sourceText = selectedRow?.source || selectedRow?.eng || '';
    const params = sourceText ? `?source_text=${encodeURIComponent(sourceText)}` : '';

    fetch(`${API_BASE}/api/ldm/context/${encodeURIComponent(stringId)}${params}`, {
      headers: getAuthHeaders(),
      signal: controller.signal
    })
      .then(async (response) => {
        if (response.ok) {
          const data = await response.json();
          entities = data.entities || [];
          detectedTerms = data.detected_in_text || [];
          aiSummary = data.ai_summary || null;
          aiStatus = data.ai_status || null;
        } else if (response.status === 404) {
          entities = [];
          detectedTerms = [];
          aiSummary = null;
          aiStatus = null;
        } else if (response.status === 503) {
          notConfigured = true;
          entities = [];
          detectedTerms = [];
          aiSummary = null;
          aiStatus = null;
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        logger.error('Failed to fetch entity context', { error: err.message });
        error = err.message;
        entities = [];
        detectedTerms = [];
        aiSummary = null;
        aiStatus = null;
      })
      .finally(() => {
        loading = false;
      });

    return () => controller.abort();
  });

  // Build highlighted source text from detected terms
  let highlightedSource = $derived.by(() => {
    const source = selectedRow?.source || selectedRow?.eng || '';
    if (!source || detectedTerms.length === 0) return null;

    // Sort by start position descending for safe insertion
    const sorted = [...detectedTerms].sort((a, b) => a.start - b.start);
    const parts = [];
    let cursor = 0;

    for (const term of sorted) {
      if (term.start > cursor) {
        parts.push({ text: source.slice(cursor, term.start), highlight: false });
      }
      parts.push({ text: source.slice(term.start, term.end), highlight: true, type: term.entity_type });
      cursor = term.end;
    }
    if (cursor < source.length) {
      parts.push({ text: source.slice(cursor), highlight: false });
    }
    return parts;
  });
</script>

<div class="context-tab">
  {#if loading}
    <div class="context-tab-loading" data-testid="context-tab-loading">
      <InlineLoading description="Detecting entities..." />
    </div>
  {:else if !selectedRow}
    <div class="context-tab-empty" data-testid="context-tab-empty">
      <MachineLearningModel size={32} />
      <span class="empty-title">No Row Selected</span>
      <span class="empty-desc">Select a row in the grid to view entity context</span>
    </div>
  {:else if notConfigured}
    <div class="context-tab-empty" data-testid="context-tab-not-configured">
      <SettingsAdjust size={32} />
      <span class="empty-title">Context Not Configured</span>
      <span class="empty-desc">Configure branch/drive in Settings to enable entity context detection</span>
    </div>
  {:else if error}
    <div class="context-tab-empty" data-testid="context-tab-error">
      <MachineLearningModel size={32} />
      <span class="empty-title">Error Loading Context</span>
      <span class="empty-desc">{error}</span>
    </div>
  {:else if entities.length === 0}
    <div class="context-tab-empty" data-testid="context-tab-no-entities">
      <MachineLearningModel size={32} />
      <span class="empty-title">No Entities Detected</span>
      <span class="empty-desc">No character, location, or item entities found in this segment</span>
    </div>
  {:else}
    <div class="context-results" data-testid="context-tab-results">
      <!-- Highlighted source text -->
      {#if highlightedSource}
        <div class="detected-text" data-testid="context-tab-highlights">
          <span class="detected-label">Detected in text</span>
          <p class="source-text">
            {#each highlightedSource as part, i (i)}
              {#if part.highlight}
                <mark class="entity-highlight entity-{part.type}">{part.text}</mark>
              {:else}
                {part.text}
              {/if}
            {/each}
          </p>
        </div>
      {/if}

      <!-- Entity cards -->
      <div class="entity-list">
        <span class="entity-count">{entities.length} {entities.length === 1 ? 'entity' : 'entities'}</span>
        {#each entities as entity (entity.strkey || entity.name + entity.entity_type)}
          <EntityCard {entity} />
        {/each}
      </div>

      <!-- AI Summary -->
      {#if aiStatus === 'unavailable' || aiStatus === 'error'}
        <div class="ai-badge-unavailable" data-testid="ai-unavailable-badge">
          <WarningAlt size={14} />
          <span>{aiStatus === 'error' ? 'AI summary failed' : 'AI unavailable'}</span>
        </div>
      {:else if aiSummary}
        <div class="ai-summary-section" data-testid="ai-summary">
          <span class="ai-label">AI Summary</span>
          <p class="ai-text">{aiSummary}</p>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .context-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .context-tab-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
  }

  .context-tab-empty {
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

  .context-results {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* Detected text with highlights */
  .detected-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .detected-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .source-text {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    line-height: 1.6;
    margin: 0;
  }

  .entity-highlight {
    background: rgba(161, 98, 255, 0.2);
    color: var(--cds-text-01);
    border-radius: 2px;
    padding: 0 2px;
    font-weight: 500;
  }

  .entity-highlight.entity-character {
    background: rgba(161, 98, 255, 0.2);
  }

  .entity-highlight.entity-location {
    background: rgba(0, 157, 154, 0.2);
  }

  .entity-highlight.entity-item {
    background: rgba(0, 189, 212, 0.2);
  }

  .entity-highlight.entity-skill {
    background: rgba(238, 83, 139, 0.2);
  }

  /* Entity list */
  .entity-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .entity-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-weight: 500;
  }

  /* AI Summary section */
  .ai-summary-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .ai-badge-unavailable {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    padding: 6px 8px;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .ai-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .ai-text {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    line-height: 1.5;
    margin: 0;
    white-space: pre-line;
  }
</style>
