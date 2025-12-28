<script>
  import {
    Button,
    Tag,
    InlineLoading,
    ContentSwitcher,
    Switch,
    InlineNotification
  } from "carbon-components-svelte";
  import { Close, WarningAltFilled, Renew, ArrowRight, StopFilled } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";

  const dispatch = createEventDispatcher();

  // API base URL (constant - doesn't change at runtime)
  const API_BASE = get(serverUrl);

  // Props
  let { open = $bindable(false), fileId = null, fileName = "" } = $props();

  // State
  let loading = $state(false);
  let runningFullQa = $state(false);
  let summary = $state(null);
  let issues = $state([]);
  let selectedCheckType = $state(0); // Index for ContentSwitcher
  let errorMessage = $state(null); // UI-visible error state

  // Timeout for API calls (30 seconds)
  const API_TIMEOUT_MS = 30000;

  // Check types with labels
  const checkTypes = [
    { id: "all", label: "All" },
    { id: "pattern", label: "Pattern" },
    { id: "line", label: "Line" },
    { id: "term", label: "Term" }
  ];

  // Safe getter for current check type
  function getCurrentCheckType() {
    const index = selectedCheckType ?? 0;
    const type = checkTypes[index];
    return type?.id ?? "all";
  }

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Cancel running operations (for close button)
  function cancelOperations() {
    loading = false;
    runningFullQa = false;
  }

  // Simple fetch with timeout
  async function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  // Load QA summary for file
  async function loadSummary() {
    if (!fileId) return;
    loading = true;
    errorMessage = null;

    try {
      const response = await fetchWithTimeout(`${API_BASE}/api/ldm/files/${fileId}/qa-summary`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        summary = await response.json();
        logger.info("QA summary loaded", { fileId, total: summary.total });
      } else {
        throw new Error(`Server returned ${response.status}`);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        logger.info("QA summary request aborted");
      } else {
        const msg = err.message.includes('abort') ? 'Request timed out' : err.message;
        errorMessage = `Failed to load summary: ${msg}`;
        logger.error("Failed to load QA summary", { error: err.message });
      }
    } finally {
      loading = false;
    }
  }

  // Load QA issues (optionally filtered by check type)
  async function loadIssues(checkType = null) {
    if (!fileId) return;
    loading = true;
    errorMessage = null;

    try {
      let url = `${API_BASE}/api/ldm/files/${fileId}/qa-results`;
      if (checkType && checkType !== 'all') {
        url += `?check_type=${checkType}`;
      }

      const response = await fetchWithTimeout(url, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        issues = data.issues || [];
        logger.info("QA issues loaded", { fileId, count: issues.length, checkType });
      } else {
        throw new Error(`Server returned ${response.status}`);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        logger.info("QA issues request aborted");
      } else {
        const msg = err.message.includes('abort') ? 'Request timed out' : err.message;
        errorMessage = `Failed to load issues: ${msg}`;
        logger.error("Failed to load QA issues", { error: err.message });
      }
    } finally {
      loading = false;
    }
  }

  // Run full file QA check
  async function runFullQA() {
    if (!fileId) return;
    runningFullQa = true;
    errorMessage = null;

    try {
      const response = await fetchWithTimeout(`${API_BASE}/api/ldm/files/${fileId}/check-qa`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          checks: ["line", "pattern", "term"],
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
        await loadIssues(getCurrentCheckType());
      } else {
        throw new Error(`Server returned ${response.status}`);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        logger.info("Full QA check aborted");
      } else {
        const msg = err.message.includes('abort') ? 'Request timed out (30s)' : err.message;
        errorMessage = `QA check failed: ${msg}`;
        logger.error("Full QA check failed", { error: err.message });
      }
    } finally {
      runningFullQa = false;
    }
  }

  // Handle check type switch
  function handleCheckTypeChange(event) {
    selectedCheckType = event.detail.index ?? 0;
    loadIssues(getCurrentCheckType());
  }

  // Click on issue: scroll to row, highlight, and open edit modal
  function handleIssueClick(rowId, rowNum) {
    dispatch('openEditModal', { rowId, rowNum });
    logger.userAction("Open row from QA menu", { rowId, rowNum });
  }

  // Close panel - always works
  function closePanel() {
    cancelOperations();
    errorMessage = null;
    open = false;
  }

  // Get severity color
  function getSeverityType(severity) {
    return severity === 'error' ? 'red' : 'magenta';
  }

  // Dismiss error message
  function dismissError() {
    errorMessage = null;
  }

  // Retry loading after error
  function retryLoad() {
    errorMessage = null;
    loadSummary();
    loadIssues(getCurrentCheckType());
  }

  // Load data when file changes or panel opens
  $effect(() => {
    if (open && fileId) {
      loadSummary();
      loadIssues(getCurrentCheckType());
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
      <div class="qa-actions">
        {#if runningFullQa}
          <Button
            kind="danger-tertiary"
            size="small"
            icon={StopFilled}
            iconDescription="Cancel QA Check"
            on:click={cancelOperations}
          >
            Cancel
          </Button>
        {:else}
          <Button
            kind="tertiary"
            size="small"
            icon={Renew}
            iconDescription="Run Full QA"
            disabled={loading}
            on:click={runFullQA}
          >
            Run Full QA
          </Button>
        {/if}
      </div>
    </div>

    <!-- Error notification -->
    {#if errorMessage}
      <div class="qa-error">
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={errorMessage}
          lowContrast
          on:close={dismissError}
        />
        <Button
          kind="ghost"
          size="small"
          icon={Renew}
          on:click={retryLoad}
        >
          Retry
        </Button>
      </div>
    {/if}

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
        <div class="summary-card" class:has-issues={summary.line > 0}>
          <span class="count">{summary.line}</span>
          <span class="label">Line</span>
        </div>
        <div class="summary-card" class:has-issues={summary.term > 0}>
          <span class="count">{summary.term}</span>
          <span class="label">Term</span>
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
            onclick={() => handleIssueClick(issue.row_id, issue.row_num)}
            title="Click to edit row"
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

  .qa-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .qa-error {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-02);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .qa-error :global(.bx--inline-notification) {
    max-width: none;
    flex: 1;
    margin: 0;
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
