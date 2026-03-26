<script>
  /**
   * RightPanel.svelte - Tabbed side panel replacing TMQAPanel
   *
   * Tabs: TM | Image | Audio | AI Context | AI Suggest
   * QA issues shown as persistent footer (always visible regardless of tab).
   * Preserves resize and collapse behavior from TMQAPanel.
   */
  import { onDestroy } from "svelte";
  import {
    ChevronLeft,
    ChevronRight,
    DataBase,
    Image,
    Music,
    MachineLearningModel,
    AiRecommend
  } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import TMTab from "$lib/components/ldm/TMTab.svelte";
  import ImageTab from "$lib/components/ldm/ImageTab.svelte";
  import AudioTab from "$lib/components/ldm/AudioTab.svelte";
  import ContextTab from "$lib/components/ldm/ContextTab.svelte";
  import AISuggestionsTab from "$lib/components/ldm/AISuggestionsTab.svelte";
  import QAFooter from "$lib/components/ldm/QAFooter.svelte";

  // Props — data props are read-only (owned by GridPage), UI props are $bindable
  let {
    selectedRow = null,
    tmMatches = [],
    qaIssues = [],
    tmLoading = false,
    qaLoading = false,
    contextResults = [],
    contextLoading = false,
    collapsed = $bindable(false),   // RightPanel owns collapse state
    width = $bindable(300),         // RightPanel owns width state
    leverageStats = null,
    // Callback props (Svelte 5 pattern)
    onApplyTM = undefined,
    onApplySuggestion = undefined,
    onNavigateToRow = undefined
  } = $props();

  // Tab state
  let activeTab = $state('tm');

  const tabs = [
    { id: 'tm', label: 'TM', icon: DataBase },
    { id: 'image', label: 'Image', icon: Image },
    { id: 'audio', label: 'Audio', icon: Music },
    { id: 'context', label: 'AI Context', icon: MachineLearningModel },
    { id: 'ai-suggest', label: 'AI Suggest', icon: AiRecommend }
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

  // Cleanup document listeners if component unmounts during resize
  onDestroy(() => {
    if (isResizing) {
      document.removeEventListener('mousemove', handleResize);
      document.removeEventListener('mouseup', stopResize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  function toggleCollapse() {
    collapsed = !collapsed;
    logger.userAction('Toggled right panel', { collapsed });
  }

  function handleApplyTM(data) {
    onApplyTM?.(data);
  }

  function handleApplySuggestion(data) {
    onApplySuggestion?.(data);
  }
</script>

<div class="right-panel" class:collapsed style="width: {collapsed ? '40px' : `${width}px`};">
  <!-- Resize handle -->
  {#if !collapsed}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
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
            <tab.icon size={14} />
            <span class="tab-label">{tab.label}</span>
          </button>
        {/each}
      </div>

      <!-- Tab content -->
      {#key activeTab}
      <div class="tab-content">
        {#if activeTab === 'tm'}
          <TMTab
            {selectedRow}
            {tmMatches}
            {tmLoading}
            {leverageStats}
            {contextResults}
            {contextLoading}
            onApplyTM={handleApplyTM}
          />
        {:else if activeTab === 'image'}
          <ImageTab {selectedRow} />
        {:else if activeTab === 'audio'}
          <AudioTab {selectedRow} />
        {:else if activeTab === 'context'}
          <ContextTab {selectedRow} />
        {:else if activeTab === 'ai-suggest'}
          <AISuggestionsTab {selectedRow} onApplySuggestion={handleApplySuggestion} />
        {/if}
      </div>
      {/key}

      <!-- QA Issues (persistent footer - always visible) -->
      <QAFooter
        {qaIssues}
        {qaLoading}
        {selectedRow}
        onNavigateToRow={(rowId) => onNavigateToRow?.({ rowId })}
      />
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

  /* QA Footer - styles moved to QAFooter.svelte component */
</style>
