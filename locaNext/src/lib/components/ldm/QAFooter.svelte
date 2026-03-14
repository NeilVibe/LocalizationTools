<script>
  /**
   * QAFooter.svelte - Dedicated QA issues footer component
   *
   * Extracted from RightPanel.svelte inline QA footer.
   * Enhanced with: filtering, count badges per check_type,
   * collapsible issue list, clickable row navigation, severity borders.
   *
   * Svelte 5 runes only.
   */
  import { Tag, InlineLoading } from "carbon-components-svelte";
  import { WarningAltFilled, Checkmark, ChevronDown, ChevronUp } from "carbon-icons-svelte";

  // Props
  let {
    qaIssues = [],
    qaLoading = false,
    selectedRow = null,
    onNavigateToRow = null
  } = $props();

  // Expand/collapse state (collapsed by default)
  let expanded = $state(false);

  // Filter state
  let activeFilter = $state('all');

  // Derive unique check types from current issues
  let checkTypes = $derived.by(() => {
    const types = new Set();
    for (const issue of qaIssues) {
      if (issue.check_type) types.add(issue.check_type);
    }
    return Array.from(types);
  });

  // Derive counts per check type
  let typeCounts = $derived.by(() => {
    const counts = {};
    for (const issue of qaIssues) {
      const t = issue.check_type || 'unknown';
      counts[t] = (counts[t] || 0) + 1;
    }
    return counts;
  });

  // Derive filtered issues
  let filteredIssues = $derived(
    activeFilter === 'all'
      ? qaIssues
      : qaIssues.filter(i => i.check_type === activeFilter)
  );

  // Summary line: "3 issues (2 term, 1 line)"
  let summaryText = $derived.by(() => {
    const total = qaIssues.length;
    if (total === 0) return '';
    const parts = Object.entries(typeCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => `${count} ${type}`);
    return `${total} issue${total !== 1 ? 's' : ''} (${parts.join(', ')})`;
  });

  // Tag color mapping for check types
  function getTagType(checkType) {
    switch (checkType) {
      case 'line': return 'blue';
      case 'term': return 'teal';
      case 'pattern': return 'purple';
      default: return 'gray';
    }
  }

  function toggleExpanded() {
    expanded = !expanded;
  }

  function setFilter(type) {
    activeFilter = activeFilter === type ? 'all' : type;
  }

  function handleIssueClick(issue) {
    if (onNavigateToRow && issue.row_id) {
      onNavigateToRow(issue.row_id);
    }
  }
</script>

{#if qaIssues.length > 0 || qaLoading || selectedRow}
  <div class="qa-footer" class:expanded>
    <!-- Header (clickable to expand/collapse) -->
    <button class="qa-header" onclick={toggleExpanded}>
      <span class="qa-title">
        <WarningAltFilled size={12} />
        QA
      </span>
      {#if qaLoading}
        <InlineLoading description="" />
      {/if}
      {#if qaIssues.length > 0}
        <span class="qa-count">{qaIssues.length}</span>
        <!-- Type badges in header -->
        <span class="qa-type-badges">
          {#each checkTypes as type (type)}
            <Tag type={getTagType(type)} size="sm">{typeCounts[type]} {type}</Tag>
          {/each}
        </span>
      {/if}
      <span class="qa-expand-icon">
        {#if expanded}
          <ChevronDown size={12} />
        {:else}
          <ChevronUp size={12} />
        {/if}
      </span>
    </button>

    {#if !selectedRow}
      <!-- hidden when no row selected -->
    {:else if expanded && qaIssues.length > 0}
      <!-- Filter bar -->
      {#if checkTypes.length > 1}
        <div class="qa-filter-bar">
          <button
            class="qa-filter-btn"
            class:active={activeFilter === 'all'}
            onclick={() => { activeFilter = 'all'; }}
          >All</button>
          {#each checkTypes as type (type)}
            <button
              class="qa-filter-btn"
              class:active={activeFilter === type}
              onclick={() => setFilter(type)}
            >{type}</button>
          {/each}
        </div>
      {/if}

      <!-- Summary line -->
      <div class="qa-summary">{summaryText}</div>

      <!-- Issue list -->
      <div class="qa-items">
        {#each filteredIssues as issue (issue.id)}
          <button
            class="qa-item"
            class:error={issue.severity === 'error'}
            class:warning={issue.severity === 'warning'}
            class:clickable={!!issue.row_id}
            onclick={() => handleIssueClick(issue)}
            title={issue.row_id ? `Go to row ${issue.row_id}` : ''}
          >
            <Tag type={issue.severity === 'error' ? 'red' : 'magenta'} size="sm">
              {issue.check_type}
            </Tag>
            <div class="qa-message">{issue.message}</div>
          </button>
        {/each}
      </div>
    {:else if expanded && !qaLoading}
      <div class="qa-ok">
        <Checkmark size={12} />
        <span>No issues</span>
      </div>
    {:else if !expanded && qaIssues.length === 0 && !qaLoading}
      <div class="qa-ok-inline">
        <Checkmark size={12} />
        <span>OK</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .qa-footer {
    flex-shrink: 0;
    border-top: 1px solid var(--cds-border-subtle-01);
    padding: 6px 12px;
    max-height: 48px;
    overflow: hidden;
    transition: max-height 0.2s ease;
  }

  .qa-footer.expanded {
    max-height: 240px;
    overflow-y: auto;
  }

  .qa-header {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    border: none;
    background: transparent;
    padding: 0;
    cursor: pointer;
    color: inherit;
    font: inherit;
  }

  .qa-header:hover {
    opacity: 0.85;
  }

  .qa-title {
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
  }

  .qa-count {
    font-size: 0.625rem;
    font-weight: 600;
    background: var(--cds-support-error, #da1e28);
    color: #fff;
    padding: 0 5px;
    border-radius: 8px;
    min-width: 16px;
    text-align: center;
    flex-shrink: 0;
  }

  .qa-type-badges {
    display: flex;
    gap: 3px;
    flex-shrink: 1;
    overflow: hidden;
  }

  .qa-expand-icon {
    margin-left: auto;
    display: flex;
    align-items: center;
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  /* Filter bar */
  .qa-filter-bar {
    display: flex;
    gap: 4px;
    margin: 6px 0 4px;
  }

  .qa-filter-btn {
    font-size: 0.625rem;
    font-weight: 500;
    padding: 2px 8px;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 12px;
    background: transparent;
    color: var(--cds-text-02);
    cursor: pointer;
    text-transform: capitalize;
    transition: all 0.15s ease;
  }

  .qa-filter-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .qa-filter-btn.active {
    background: var(--cds-interactive-01);
    color: #fff;
    border-color: var(--cds-interactive-01);
  }

  /* Summary */
  .qa-summary {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    margin-bottom: 4px;
    font-style: italic;
  }

  /* Issue list */
  .qa-items {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .qa-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 6px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: none;
    font: inherit;
    text-align: left;
    width: 100%;
    cursor: default;
    transition: background 0.1s ease;
  }

  .qa-item.clickable {
    cursor: pointer;
  }

  .qa-item.clickable:hover {
    background: var(--cds-layer-hover-02, var(--cds-layer-hover-01));
  }

  .qa-item.error {
    border-left: 3px solid var(--cds-support-01);
  }

  .qa-item.warning {
    border-left: 3px solid var(--cds-support-03);
  }

  .qa-message {
    font-size: 0.6875rem;
    color: var(--cds-text-01);
    line-height: 1.4;
  }

  .qa-ok {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.6875rem;
    color: var(--cds-support-02);
    padding-top: 6px;
  }

  .qa-ok-inline {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 0.625rem;
    color: var(--cds-support-02);
    margin-left: auto;
  }
</style>
