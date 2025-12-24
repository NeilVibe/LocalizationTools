<script>
  import {
    Button,
    Tag,
    InlineLoading,
    ContentSwitcher,
    Switch
  } from "carbon-components-svelte";
  import { Close, WarningAltFilled, Renew, ArrowRight } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";

  const dispatch = createEventDispatcher();

  // Svelte 5: Derived - API base URL
  let API_BASE = $derived(get(serverUrl));

  // Props
  let { open = $bindable(false), fileId = null, fileName = "" } = $props();

  // State
  let loading = $state(false);
  let runningFullQa = $state(false);
  let summary = $state(null);
  let issues = $state([]);
  let selectedCheckType = $state(0); // Index for ContentSwitcher

  // Check types with labels
  const checkTypes = [
    { id: "all", label: "All" },
    { id: "pattern", label: "Pattern" },
    { id: "character", label: "Character" },
    { id: "line", label: "Line" }
  ];

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load QA summary for file
  async function loadSummary() {
    if (!fileId) return;
    loading = true;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/qa-summary`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        summary = await response.json();
        logger.info("QA summary loaded", { fileId, total: summary.total });
      }
    } catch (err) {
      logger.error("Failed to load QA summary", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load QA issues (optionally filtered by check type)
  async function loadIssues(checkType = null) {
    if (!fileId) return;
    loading = true;

    try {
      let url = `${API_BASE}/api/ldm/files/${fileId}/qa-results`;
      if (checkType && checkType !== 'all') {
        url += `?check_type=${checkType}`;
      }

      const response = await fetch(url, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        issues = data.issues || [];
        logger.info("QA issues loaded", { fileId, count: issues.length, checkType });
      }
    } catch (err) {
      logger.error("Failed to load QA issues", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Run full file QA check
  async function runFullQA() {
    if (!fileId) return;
    runningFullQa = true;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/check-qa`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          checks: ["line", "pattern", "character"],
          force: true
        })
      });

      if (response.ok) {
        const result = await response.json();
        logger.success("Full QA check complete", {
          fileId,
          rowsChecked: result.rows_checked,
          issuesFound: result.total_issues
        });

        // Refresh data
        await loadSummary();
        await loadIssues(checkTypes[selectedCheckType].id);
      }
    } catch (err) {
      logger.error("Full QA check failed", { error: err.message });
    } finally {
      runningFullQa = false;
    }
  }

  // Handle check type switch
  function handleCheckTypeChange(event) {
    selectedCheckType = event.detail.index;
    const checkType = checkTypes[selectedCheckType].id;
    loadIssues(checkType);
  }

  // Jump to row in grid
  function goToRow(rowId, rowNum) {
    dispatch('goToRow', { rowId, rowNum });
    logger.userAction("Jump to row from QA menu", { rowId, rowNum });
  }

  // Close panel
  function closePanel() {
    open = false;
  }

  // Get severity color
  function getSeverityType(severity) {
    return severity === 'error' ? 'red' : 'magenta';
  }

  // Load data when file changes or panel opens
  $effect(() => {
    if (open && fileId) {
      loadSummary();
      loadIssues(checkTypes[selectedCheckType].id);
    }
  });
</script>

{#if open}
  <!-- Backdrop -->
  <div
    class="qa-panel-backdrop"
    onclick={closePanel}
    onkeydown={(e) => e.key === 'Escape' && closePanel()}
    role="presentation"
  ></div>

  <!-- Slide-out panel -->
  <div class="qa-panel" role="dialog" aria-label="QA Menu">
    <!-- Header -->
    <div class="qa-panel-header">
      <div class="header-title">
        <WarningAltFilled size={20} />
        <h3>QA Report</h3>
      </div>
      <Button
        kind="ghost"
        size="small"
        icon={Close}
        iconDescription="Close"
        on:click={closePanel}
      />
    </div>

    <!-- File info -->
    <div class="qa-file-info">
      <span class="file-name">{fileName || `File #${fileId}`}</span>
      <Button
        kind="tertiary"
        size="small"
        icon={Renew}
        iconDescription="Run Full QA"
        disabled={runningFullQa}
        on:click={runFullQA}
      >
        {runningFullQa ? 'Checking...' : 'Run Full QA'}
      </Button>
    </div>

    <!-- Summary Cards -->
    {#if summary}
      <div class="qa-summary">
        <div class="summary-card" class:has-issues={summary.total > 0}>
          <span class="count">{summary.total}</span>
          <span class="label">Total</span>
        </div>
        <div class="summary-card" class:has-issues={summary.pattern > 0}>
          <span class="count">{summary.pattern}</span>
          <span class="label">Pattern</span>
        </div>
        <div class="summary-card" class:has-issues={summary.character > 0}>
          <span class="count">{summary.character}</span>
          <span class="label">Character</span>
        </div>
        <div class="summary-card" class:has-issues={summary.line > 0}>
          <span class="count">{summary.line}</span>
          <span class="label">Line</span>
        </div>
      </div>
    {:else if loading}
      <div class="qa-loading">
        <InlineLoading description="Loading summary..." />
      </div>
    {/if}

    <!-- Check type filter -->
    <div class="qa-filter">
      <ContentSwitcher
        selectedIndex={selectedCheckType}
        on:change={handleCheckTypeChange}
      >
        {#each checkTypes as type}
          <Switch text={type.label} />
        {/each}
      </ContentSwitcher>
    </div>

    <!-- Issues list -->
    <div class="qa-issues-list">
      {#if loading}
        <div class="issues-loading">
          <InlineLoading description="Loading issues..." />
        </div>
      {:else if issues.length === 0}
        <div class="no-issues">
          <WarningAltFilled size={24} />
          <p>No issues found</p>
        </div>
      {:else}
        {#each issues as issue}
          <button
            class="issue-item"
            onclick={() => goToRow(issue.row_id, issue.row_num)}
          >
            <div class="issue-header">
              <Tag type={getSeverityType(issue.severity)} size="sm">
                {issue.check_type}
              </Tag>
              <span class="row-num">Row {issue.row_num}</span>
              <ArrowRight size={14} class="go-icon" />
            </div>
            <div class="issue-message">{issue.message}</div>
            {#if issue.source}
              <div class="issue-source" title={issue.source}>
                {issue.source.length > 60 ? issue.source.substring(0, 60) + '...' : issue.source}
              </div>
            {/if}
          </button>
        {/each}
      {/if}
    </div>

    <!-- Footer with last checked -->
    {#if summary?.last_checked}
      <div class="qa-footer">
        Last checked: {new Date(summary.last_checked).toLocaleString()}
      </div>
    {/if}
  </div>
{/if}

<style>
  .qa-panel-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 9998;
  }

  .qa-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    max-width: 90vw;
    height: 100%;
    background: var(--cds-layer-01);
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.2);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .qa-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-accent-01);
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--cds-text-01);
  }

  .header-title h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .qa-file-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-02);
  }

  .file-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }

  .qa-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    padding: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .summary-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.75rem 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .summary-card.has-issues {
    background: rgba(218, 30, 40, 0.08);
    border-color: rgba(218, 30, 40, 0.3);
  }

  .summary-card .count {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .summary-card.has-issues .count {
    color: var(--cds-support-01, #da1e28);
  }

  .summary-card .label {
    font-size: 0.625rem;
    text-transform: uppercase;
    color: var(--cds-text-02);
    margin-top: 0.25rem;
  }

  .qa-loading {
    padding: 2rem;
    display: flex;
    justify-content: center;
  }

  .qa-filter {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .qa-issues-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .issues-loading {
    padding: 2rem;
    display: flex;
    justify-content: center;
  }

  .no-issues {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    color: var(--cds-text-02);
    gap: 0.5rem;
  }

  .no-issues p {
    margin: 0;
    font-style: italic;
  }

  .issue-item {
    display: block;
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    background: var(--cds-layer-01);
    text-align: left;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, transform 0.1s;
  }

  .issue-item:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-interactive);
    transform: translateX(-2px);
  }

  .issue-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .row-num {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-left: auto;
  }

  .issue-header :global(.go-icon) {
    color: var(--cds-icon-02);
    opacity: 0;
    transition: opacity 0.15s;
  }

  .issue-item:hover .issue-header :global(.go-icon) {
    opacity: 1;
  }

  .issue-message {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.4;
    margin-bottom: 0.25rem;
  }

  .issue-source {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .qa-footer {
    padding: 0.75rem 1rem;
    border-top: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-02);
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-align: center;
  }
</style>
