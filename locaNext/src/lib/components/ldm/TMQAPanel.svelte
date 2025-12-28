<script>
  /**
   * TMQAPanel.svelte - Side panel for TM matches and QA issues
   * Phase 1 of MemoQ-style non-modal editing
   *
   * Features:
   * - Resizable width (drag handle on left edge)
   * - Collapsible (show/hide button)
   * - TM matches display with metadata
   * - QA issues display (future)
   */
  import { Tag, InlineLoading } from "carbon-components-svelte";
  import { ChevronLeft, ChevronRight, WarningAltFilled } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  const dispatch = createEventDispatcher();

  // Props
  let {
    selectedRow = $bindable(null),
    tmMatches = $bindable([]),
    qaIssues = $bindable([]),
    tmLoading = false,
    qaLoading = false,
    collapsed = $bindable(false),
    width = $bindable(300)
  } = $props();

  // Resize state
  let isResizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartWidth = $state(300);
  const MIN_WIDTH = 200;
  const MAX_WIDTH = 500;

  function startResize(e) {
    isResizing = true;
    resizeStartX = e.clientX;
    resizeStartWidth = width;

    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function handleResize(e) {
    if (!isResizing) return;

    // Moving left = larger panel (negative delta = positive width change)
    const delta = resizeStartX - e.clientX;
    const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, resizeStartWidth + delta));
    width = newWidth;
  }

  function stopResize() {
    isResizing = false;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    logger.userAction('Resized TM/QA panel', { width });
  }

  function toggleCollapse() {
    collapsed = !collapsed;
    logger.userAction('Toggled TM/QA panel', { collapsed });
  }

  function handleApplyTM(match) {
    dispatch('applyTM', match);
    logger.userAction('Apply TM from side panel', { similarity: match.similarity });
  }
</script>

<div class="tmqa-panel" class:collapsed style="width: {collapsed ? '40px' : `${width}px`};">
  <!-- Resize handle (left edge) -->
  {#if !collapsed}
    <div
      class="resize-handle"
      onmousedown={startResize}
      role="separator"
      aria-label="Resize panel"
    ></div>
  {/if}

  <!-- Collapse/Expand button -->
  <button class="collapse-btn" onclick={toggleCollapse} title={collapsed ? 'Expand panel' : 'Collapse panel'}>
    {#if collapsed}
      <ChevronLeft size={16} />
    {:else}
      <ChevronRight size={16} />
    {/if}
  </button>

  {#if !collapsed}
    <div class="panel-content">
      <!-- TM Matches Section -->
      <div class="section tm-section">
        <div class="section-header">
          <span class="section-title">TM MATCHES</span>
          {#if tmLoading}
            <InlineLoading description="" />
          {/if}
        </div>

        <div class="section-body">
          {#if !selectedRow}
            <div class="empty-msg">Select a row to see TM matches</div>
          {:else if tmMatches.length > 0}
            {#each tmMatches as match, idx}
              <button
                class="tm-item"
                onclick={() => handleApplyTM(match)}
                title="Click to apply this translation"
              >
                <div class="tm-item-header">
                  <Tag type="teal" size="sm">{Math.round(match.similarity * 100)}%</Tag>
                  {#if idx === 0}
                    <span class="tm-hint">Tab to apply</span>
                  {/if}
                </div>
                <div class="tm-item-source">{match.source}</div>
                <div class="tm-item-target">{match.target}</div>
                {#if match.source_type || match.created_by}
                  <div class="tm-item-meta">
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
          {:else if !tmLoading}
            <div class="empty-msg">No TM matches found</div>
          {/if}
        </div>
      </div>

      <!-- QA Issues Section -->
      <div class="section qa-section">
        <div class="section-header">
          <span class="section-title">
            <WarningAltFilled size={14} />
            QA ISSUES
          </span>
          {#if qaLoading}
            <InlineLoading description="" />
          {/if}
        </div>

        <div class="section-body">
          {#if !selectedRow}
            <div class="empty-msg">Select a row to see QA issues</div>
          {:else if qaIssues.length > 0}
            {#each qaIssues as issue}
              <div class="qa-item" class:error={issue.severity === 'error'} class:warning={issue.severity === 'warning'}>
                <Tag type={issue.severity === 'error' ? 'red' : 'magenta'} size="sm">
                  {issue.check_type}
                </Tag>
                <div class="qa-message">{issue.message}</div>
              </div>
            {/each}
          {:else if !qaLoading}
            <div class="empty-msg success">No QA issues</div>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .tmqa-panel {
    display: flex;
    flex-direction: column;
    background: var(--cds-layer-01);
    border-left: 1px solid var(--cds-border-subtle-01);
    position: relative;
    transition: width 0.15s ease;
    overflow: hidden;
  }

  .tmqa-panel.collapsed {
    min-width: 40px;
    max-width: 40px;
  }

  /* Resize handle */
  .resize-handle {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    cursor: col-resize;
    background: transparent;
    z-index: 10;
  }

  .resize-handle:hover {
    background: var(--cds-interactive-01);
  }

  /* Collapse button */
  .collapse-btn {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 24px;
    height: 24px;
    border: none;
    background: var(--cds-layer-02);
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--cds-text-01);
    z-index: 5;
  }

  .collapse-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  /* Panel content */
  .panel-content {
    display: flex;
    flex-direction: column;
    padding: 40px 12px 12px 16px;
    overflow-y: auto;
    flex: 1;
    gap: 16px;
  }

  /* Sections */
  .section {
    display: flex;
    flex-direction: column;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .section-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .section-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* TM Items */
  .tm-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    width: 100%;
  }

  .tm-item:hover {
    background: var(--cds-layer-hover-02);
    border-color: var(--cds-interactive-01);
  }

  .tm-item-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tm-hint {
    font-size: 0.625rem;
    color: var(--cds-text-02);
    background: var(--cds-layer-01);
    padding: 2px 4px;
    border-radius: 2px;
  }

  .tm-item-source {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .tm-item-target {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  .tm-item-meta {
    display: flex;
    gap: 8px;
    font-size: 0.625rem;
    color: var(--cds-text-02);
    margin-top: 4px;
  }

  .meta-tag {
    background: var(--cds-layer-01);
    padding: 1px 4px;
    border-radius: 2px;
  }

  .meta-user {
    font-style: italic;
  }

  /* QA Items */
  .qa-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .qa-item.error {
    border-left: 3px solid var(--cds-support-01);
  }

  .qa-item.warning {
    border-left: 3px solid var(--cds-support-03);
  }

  .qa-message {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    line-height: 1.4;
  }

  /* Empty states */
  .empty-msg {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-style: italic;
    padding: 8px;
    text-align: center;
  }

  .empty-msg.success {
    color: var(--cds-support-02);
  }
</style>
