<script>
  /**
   * RightPanel.svelte - Tabbed side panel replacing TMQAPanel
   *
   * Tabs: TM | Image | Audio | AI Context
   * QA issues shown as persistent footer (always visible regardless of tab).
   * Preserves resize and collapse behavior from TMQAPanel.
   */
  import { Tag, InlineLoading } from "carbon-components-svelte";
  import {
    ChevronLeft,
    ChevronRight,
    WarningAltFilled,
    Checkmark,
    DataBase,
    Image,
    Music,
    MachineLearningModel
  } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import TMTab from "$lib/components/ldm/TMTab.svelte";
  import ImageTab from "$lib/components/ldm/ImageTab.svelte";
  import AudioTab from "$lib/components/ldm/AudioTab.svelte";

  const dispatch = createEventDispatcher();

  // Props (same as TMQAPanel for backward compat)
  let {
    selectedRow = $bindable(null),
    tmMatches = $bindable([]),
    qaIssues = $bindable([]),
    tmLoading = false,
    qaLoading = false,
    collapsed = $bindable(false),
    width = $bindable(300),
    leverageStats = null
  } = $props();

  // Tab state
  let activeTab = $state('tm');

  const tabs = [
    { id: 'tm', label: 'TM', icon: DataBase },
    { id: 'image', label: 'Image', icon: Image },
    { id: 'audio', label: 'Audio', icon: Music },
    { id: 'context', label: 'AI Context', icon: MachineLearningModel }
  ];

  // Resize state (copied from TMQAPanel)
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
    logger.userAction('Resized right panel', { width });
  }

  function toggleCollapse() {
    collapsed = !collapsed;
    logger.userAction('Toggled right panel', { collapsed });
  }

  function handleApplyTM(event) {
    dispatch('applyTM', event.detail);
  }
</script>

<div class="right-panel" class:collapsed style="width: {collapsed ? '40px' : `${width}px`};">
  <!-- Resize handle -->
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
      <!-- Tab bar -->
      <div class="tab-bar" data-testid="right-panel-tabs">
        {#each tabs as tab (tab.id)}
          <button
            class="tab-btn"
            class:active={activeTab === tab.id}
            onclick={() => { activeTab = tab.id; }}
            title={tab.label}
            data-testid="tab-{tab.id}"
          >
            <svelte:component this={tab.icon} size={14} />
            <span class="tab-label">{tab.label}</span>
          </button>
        {/each}
      </div>

      <!-- Tab content -->
      {#key activeTab}
      <div class="tab-content">
        {#if activeTab === 'tm'}
          <TMTab
            bind:selectedRow={selectedRow}
            bind:tmMatches={tmMatches}
            bind:tmLoading={tmLoading}
            {leverageStats}
            on:applyTM={handleApplyTM}
          />
        {:else if activeTab === 'image'}
          <ImageTab {selectedRow} />
        {:else if activeTab === 'audio'}
          <AudioTab {selectedRow} />
        {:else if activeTab === 'context'}
          <div class="placeholder-tab">
            <MachineLearningModel size={32} />
            <span class="placeholder-title">AI Context</span>
            <span class="placeholder-desc">Coming in Phase 5.1</span>
          </div>
        {/if}
      </div>
      {/key}

      <!-- QA Issues (persistent footer - always visible) -->
      {#if qaIssues.length > 0 || qaLoading || selectedRow}
        <div class="qa-footer">
          <div class="qa-header">
            <span class="qa-title">
              <WarningAltFilled size={12} />
              QA
            </span>
            {#if qaLoading}
              <InlineLoading description="" />
            {/if}
            {#if qaIssues.length > 0}
              <span class="qa-count">{qaIssues.length}</span>
            {/if}
          </div>

          {#if !selectedRow}
            <!-- hidden when no row selected, footer only shows when relevant -->
          {:else if qaIssues.length > 0}
            <div class="qa-items">
              {#each qaIssues as issue (issue.id)}
                <div class="qa-item" class:error={issue.severity === 'error'} class:warning={issue.severity === 'warning'}>
                  <Tag type={issue.severity === 'error' ? 'red' : 'magenta'} size="sm">
                    {issue.check_type}
                  </Tag>
                  <div class="qa-message">{issue.message}</div>
                </div>
              {/each}
            </div>
          {:else if !qaLoading}
            <div class="qa-ok">
              <Checkmark size={12} />
              <span>No issues</span>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .right-panel {
    display: flex;
    flex-direction: column;
    background: var(--cds-layer-01);
    border-left: 1px solid var(--cds-border-subtle-01);
    position: relative;
    transition: width 0.15s ease;
    overflow: hidden;
  }

  .right-panel.collapsed {
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
    transition: background 0.15s ease;
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
    padding-top: 40px;
    overflow: hidden;
    flex: 1;
  }

  /* Tab bar */
  .tab-bar {
    display: flex;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    padding: 0 12px;
    flex-shrink: 0;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 10px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.6875rem;
    font-weight: 500;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s ease, border-color 0.15s ease;
    white-space: nowrap;
  }

  .tab-btn:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .tab-btn.active {
    color: var(--cds-interactive-01);
    border-bottom-color: var(--cds-interactive-01);
  }

  .tab-label {
    display: inline;
  }

  /* At narrow widths, hide tab labels */
  @container (max-width: 240px) {
    .tab-label {
      display: none;
    }
  }

  /* Tab content area */
  .tab-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    min-height: 0;
    animation: tabFadeIn 0.15s ease;
  }

  @keyframes tabFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Placeholder tabs */
  .placeholder-tab {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 3rem 1rem;
    color: var(--cds-text-03);
    text-align: center;
  }

  .placeholder-title {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-02);
  }

  .placeholder-desc {
    font-size: 0.75rem;
    font-style: italic;
  }

  /* QA Footer */
  .qa-footer {
    flex-shrink: 0;
    border-top: 1px solid var(--cds-border-subtle-01);
    padding: 8px 12px;
    max-height: 140px;
    overflow-y: auto;
  }

  .qa-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
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
  }

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
  }
</style>
