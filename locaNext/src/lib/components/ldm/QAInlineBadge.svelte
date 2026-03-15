<script>
  /**
   * QAInlineBadge - Inline QA indicator for grid rows
   *
   * P16-02: Shows a colored badge with QA issue count.
   * Click to expand popover with issue details and dismiss buttons.
   * Svelte 5 runes only.
   */
  import { Tag } from "carbon-components-svelte";
  import { WarningAltFilled, WarningFilled, InformationFilled, Close } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";

  const API_BASE = getApiBase();

  // Props (Svelte 5 runes)
  let { qaFlagCount = 0, rowId = 0, onDismiss = undefined } = $props();

  // Internal state
  let expanded = $state(false);
  let issues = $state([]);
  let loading = $state(false);
  let localCount = $state(0);

  // Sync localCount with prop
  $effect(() => {
    localCount = qaFlagCount;
  });

  /**
   * Get severity color for badge
   */
  function getBadgeColor() {
    if (localCount >= 3) return "red";
    if (localCount >= 1) return "magenta";
    return "gray";
  }

  /**
   * Get severity icon component based on severity level
   */
  function getSeverityIcon(severity) {
    if (severity === "error") return WarningAltFilled;
    if (severity === "warning") return WarningFilled;
    return InformationFilled;
  }

  /**
   * Get severity CSS class
   */
  function getSeverityClass(severity) {
    if (severity === "error") return "severity-error";
    if (severity === "warning") return "severity-warning";
    return "severity-info";
  }

  /**
   * Toggle expanded state and fetch issues on first expand
   */
  async function toggleExpand(event) {
    event.stopPropagation();
    event.preventDefault();

    if (expanded) {
      expanded = false;
      return;
    }

    expanded = true;
    await fetchIssues();
  }

  /**
   * Fetch QA results for this row
   */
  async function fetchIssues() {
    if (!rowId) return;
    loading = true;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/qa-results`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        issues = data.issues || [];
        logger.info("QA inline issues loaded", { rowId, count: issues.length });
      } else {
        logger.error("Failed to fetch QA results", { rowId, status: response.status });
      }
    } catch (err) {
      logger.error("QA inline fetch error", { rowId, error: err.message });
    } finally {
      loading = false;
    }
  }

  /**
   * Dismiss/resolve a single QA issue
   */
  async function dismissIssue(event, issueId) {
    event.stopPropagation();
    event.preventDefault();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/qa-results/${issueId}/resolve`, {
        method: "POST",
        headers: getAuthHeaders()
      });

      if (response.ok) {
        // Optimistic removal from local list
        issues = issues.filter(i => i.id !== issueId);
        localCount = Math.max(0, localCount - 1);

        // Notify parent to update row data
        onDismiss?.(rowId);

        logger.info("QA issue dismissed inline", { rowId, issueId });
      } else {
        logger.error("Failed to dismiss QA issue", { issueId, status: response.status });
      }
    } catch (err) {
      logger.error("QA dismiss error", { issueId, error: err.message });
    }
  }

  /**
   * Close popover (click outside handler calls this)
   */
  function closePopover() {
    expanded = false;
  }

  /**
   * Handle click outside to close popover
   */
  function handleClickOutside(event) {
    // Close if click is outside the badge container
    const target = event.target;
    const container = event.currentTarget?.closest?.('.qa-inline-badge');
    if (!container?.contains(target)) {
      closePopover();
    }
  }

  /**
   * Truncate message to max chars
   */
  function truncate(text, maxLen = 80) {
    if (!text || text.length <= maxLen) return text;
    return text.substring(0, maxLen) + "...";
  }
</script>

{#if localCount > 0}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <span
    class="qa-inline-badge"
    onclick={toggleExpand}
    onkeydown={(e) => e.key === "Enter" && toggleExpand(e)}
    role="button"
    tabindex="0"
    title="{localCount} QA issue(s) - click to view"
  >
    <Tag type={getBadgeColor()} size="sm">
      {localCount}
    </Tag>

    {#if expanded}
      <!-- Popover backdrop for click-outside -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="qa-popover-backdrop"
        onclick={(e) => { e.stopPropagation(); closePopover(); }}
        onkeydown={(e) => e.key === "Escape" && closePopover()}
      ></div>

      <!-- Popover -->
      <div class="qa-popover" onclick={(e) => e.stopPropagation()} role="dialog" aria-label="QA Issues">
        <div class="qa-popover-header">
          <span class="qa-popover-title">QA Issues ({issues.length})</span>
          <button class="qa-popover-close" onclick={(e) => { e.stopPropagation(); closePopover(); }} aria-label="Close">
            <Close size={14} />
          </button>
        </div>

        <div class="qa-popover-content">
          {#if loading}
            <div class="qa-popover-loading">Loading...</div>
          {:else if issues.length === 0}
            <div class="qa-popover-empty">No unresolved issues</div>
          {:else}
            {#each issues as issue (issue.id)}
              <div class="qa-popover-issue {getSeverityClass(issue.severity)}">
                <div class="issue-row">
                  <span class="issue-severity-icon">
                    {#if issue.severity === "error"}
                      <WarningAltFilled size={14} />
                    {:else if issue.severity === "warning"}
                      <WarningFilled size={14} />
                    {:else}
                      <InformationFilled size={14} />
                    {/if}
                  </span>
                  <span class="issue-type">{issue.check_type}</span>
                  <button
                    class="issue-dismiss"
                    onclick={(e) => dismissIssue(e, issue.id)}
                    title="Dismiss this issue"
                    aria-label="Dismiss issue"
                  >
                    <Close size={12} />
                  </button>
                </div>
                <div class="issue-text">{truncate(issue.message)}</div>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    {/if}
  </span>
{/if}

<style>
  .qa-inline-badge {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    z-index: 2;
  }

  .qa-popover-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 99;
  }

  .qa-popover {
    position: absolute;
    top: 100%;
    right: 0;
    width: 300px;
    max-height: 280px;
    background: var(--cds-layer-02, #fff);
    border: 1px solid var(--cds-border-subtle-01, #ddd);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    z-index: 100;
    display: flex;
    flex-direction: column;
    margin-top: 4px;
  }

  .qa-popover-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01, #ddd);
    background: var(--cds-layer-accent-01, #f4f4f4);
  }

  .qa-popover-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .qa-popover-close {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--cds-icon-01);
    padding: 2px;
    display: flex;
    align-items: center;
  }

  .qa-popover-close:hover {
    color: var(--cds-text-01);
  }

  .qa-popover-content {
    overflow-y: auto;
    max-height: 220px;
    padding: 0.5rem;
  }

  .qa-popover-loading,
  .qa-popover-empty {
    padding: 1rem;
    text-align: center;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .qa-popover-issue {
    padding: 0.5rem;
    margin-bottom: 0.375rem;
    border-radius: 3px;
    border-left: 3px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01, #f9f9f9);
  }

  .qa-popover-issue.severity-error {
    border-left-color: var(--cds-support-01, #da1e28);
    background: rgba(218, 30, 40, 0.06);
  }

  .qa-popover-issue.severity-warning {
    border-left-color: var(--cds-support-03, #f1c21b);
    background: rgba(241, 194, 27, 0.06);
  }

  .qa-popover-issue.severity-info {
    border-left-color: var(--cds-support-04, #4589ff);
    background: rgba(69, 137, 255, 0.06);
  }

  .issue-row {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.25rem;
  }

  .issue-severity-icon {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .severity-error .issue-severity-icon {
    color: var(--cds-support-01, #da1e28);
  }

  .severity-warning .issue-severity-icon {
    color: var(--cds-support-03, #f1c21b);
  }

  .severity-info .issue-severity-icon {
    color: var(--cds-support-04, #4589ff);
  }

  .issue-type {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--cds-text-02);
  }

  .issue-dismiss {
    margin-left: auto;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--cds-icon-02, #999);
    padding: 2px;
    display: flex;
    align-items: center;
    opacity: 0.6;
    transition: opacity 0.15s;
  }

  .issue-dismiss:hover {
    opacity: 1;
    color: var(--cds-support-01, #da1e28);
  }

  .issue-text {
    font-size: 0.6875rem;
    color: var(--cds-text-01);
    line-height: 1.35;
    word-break: break-word;
  }
</style>
