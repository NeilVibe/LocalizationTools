<script>
  /**
   * GridPage.svelte - Phase 10 UI Overhaul
   *
   * Full-page grid viewer for editing translation files.
   * Includes VirtualGrid and TM/QA side panel.
   */
  import { createEventDispatcher } from 'svelte';
  import { openFile, closeGrid } from '$lib/stores/navigation.js';
  import { preferences } from '$lib/stores/preferences.js';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import VirtualGrid from '$lib/components/ldm/VirtualGrid.svelte';
  import TMQAPanel from '$lib/components/ldm/TMQAPanel.svelte';
  import { Button } from 'carbon-components-svelte';
  import { ArrowLeft, Column, Document, DataBase } from 'carbon-icons-svelte';

  // Props
  let {
    fileId = null,
    fileName = '',
    linkedTM = null,
    onShowGridColumns = () => {},
    onShowReferenceSettings = () => {}
  } = $props();

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // Component refs
  let virtualGrid = $state(null);

  // Side panel state
  let sidePanelCollapsed = $state(false);
  let sidePanelWidth = $state(300);
  let sidePanelSelectedRow = $state(null);
  let sidePanelTMMatches = $state([]);
  let sidePanelQAIssues = $state([]);
  let sidePanelTMLoading = $state(false);
  let sidePanelQALoading = $state(false);

  // Active TMs state (TM Hierarchy)
  let activeTMs = $state([]);
  let activeTMsLoading = $state(false);

  /**
   * Load active TMs for the current file (TM Hierarchy cascade)
   */
  async function loadActiveTMs() {
    if (!fileId) return;

    activeTMsLoading = true;
    try {
      logger.apiCall(`/api/ldm/files/${fileId}/active-tms`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/active-tms`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      activeTMs = await response.json();
      logger.success('Active TMs loaded', { count: activeTMs.length });
    } catch (err) {
      logger.error('Failed to load active TMs', { error: err.message });
      activeTMs = [];
    } finally {
      activeTMsLoading = false;
    }
  }

  // Load active TMs when fileId changes
  $effect(() => {
    if (fileId) {
      loadActiveTMs();
    }
  });


  /**
   * Handle row selection - load TM matches
   */
  async function handleRowSelect(event) {
    const { row } = event.detail;
    sidePanelSelectedRow = row;
    sidePanelTMMatches = [];
    sidePanelQAIssues = row?.qa_issues || [];

    if (!row?.source) return;

    await loadTMMatchesForRow(row);
  }

  /**
   * Load TM matches for a row - USES HIERARCHY TMs
   */
  async function loadTMMatchesForRow(row) {
    if (!row?.source || !fileId) return;

    // Only search TM if there are active TMs from hierarchy
    if (activeTMs.length === 0) {
      sidePanelTMMatches = [];
      return;
    }

    sidePanelTMLoading = true;
    try {
      const params = new URLSearchParams({
        source: row.source,
        threshold: $preferences.tmThreshold.toString(),
        max_results: '5',
        tm_id: activeTMs[0].tm_id.toString()  // Use hierarchy TM, not preferences
      });

      // Exclude current row if it has an id
      if (row.id) {
        params.append('exclude_row_id', row.id.toString());
      }

      logger.apiCall('/api/ldm/tm/suggest', 'GET', { tm_id: activeTMs[0].tm_id });
      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      sidePanelTMMatches = data.suggestions || [];
    } catch (err) {
      logger.error('Failed to load TM matches', { error: err.message });
      sidePanelTMMatches = [];
    } finally {
      sidePanelTMLoading = false;
    }
  }

  /**
   * Apply TM suggestion from side panel
   */
  function handleApplyTMFromPanel(event) {
    const { target } = event.detail;
    if (virtualGrid && sidePanelSelectedRow) {
      virtualGrid.applyTMToRow(sidePanelSelectedRow.line_number, target);
    }
  }

  /**
   * Handle translation confirmation (auto-add to TM)
   * Uses hierarchy activeTMs - entries auto-added to first active TM
   * VirtualGrid sends: {rowId, source, target}
   */
  async function handleConfirmTranslation(event) {
    const { rowId, source, target } = event.detail;

    // Auto-add to active TM from hierarchy (not linkedTM)
    if (activeTMs.length > 0 && source && target) {
      const tmId = activeTMs[0].tm_id;
      try {
        // API uses Form data, not JSON
        const formData = new FormData();
        formData.append('source_text', source);
        formData.append('target_text', target);

        logger.apiCall(`/api/ldm/tm/${tmId}/entries`, 'POST');
        const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });

        if (response.ok) {
          logger.success('Entry auto-added to active TM', { tmId, tmName: activeTMs[0].tm_name });
        } else {
          const err = await response.json();
          logger.warning('Failed to auto-add entry to TM', { error: err.detail });
        }
      } catch (err) {
        logger.error('Failed to add entry to TM', { error: err.message });
      }
    } else if (activeTMs.length === 0) {
      logger.info('No active TM from hierarchy - entry not added to TM');
    }

    // Don't re-dispatch - GridPage handles it completely now
  }

  /**
   * Handle QA dismissal
   */
  function handleDismissQA(event) {
    dispatch('dismissQA', event.detail);
  }

  /**
   * Go back to files view
   */
  function goBack() {
    closeGrid();
  }

  // Expose virtualGrid methods
  export function getVirtualGrid() {
    return virtualGrid;
  }
</script>

<div class="grid-page">
  <!-- Grid Toolbar -->
  <div class="grid-toolbar">
    <div class="toolbar-left">
      <Button
        kind="ghost"
        size="small"
        icon={ArrowLeft}
        iconDescription="Back to Files"
        on:click={goBack}
      />
      <span class="file-name">{fileName || 'Untitled'}</span>
      {#if $openFile?.format}
        <span class="file-format">{$openFile.format.toUpperCase()}</span>
      {/if}
    </div>
    <!-- TM Indicator (TM Hierarchy) - Simple display with TM ACTIVE prefix -->
    <div class="tm-indicator" class:has-tm={activeTMs.length > 0}>
      {#if activeTMsLoading}
        <span class="tm-loading">Loading TM...</span>
      {:else if activeTMs.length > 0}
        <div class="tm-info">
          <DataBase size={16} class="tm-info-icon" />
          <span class="tm-info-label">TM ACTIVE:</span>
          <span class="tm-info-name">{activeTMs[0].tm_name}</span>
          <span class="tm-info-scope">({activeTMs[0].scope}: {activeTMs[0].scope_name})</span>
          {#if activeTMs.length > 1}
            <span class="tm-info-more">+{activeTMs.length - 1} more</span>
          {/if}
        </div>
      {:else}
        <span class="tm-none">No TM active</span>
      {/if}
    </div>

    <div class="toolbar-right">
      <Button
        kind="ghost"
        size="small"
        icon={Column}
        iconDescription="Grid Columns"
        tooltipAlignment="end"
        on:click={onShowGridColumns}
      />
      <Button
        kind="ghost"
        size="small"
        icon={Document}
        iconDescription="Reference Settings"
        tooltipAlignment="end"
        on:click={onShowReferenceSettings}
      />
    </div>
  </div>

  <!-- Grid + Side Panel -->
  <div class="grid-with-panel">
    <VirtualGrid
      bind:this={virtualGrid}
      {fileId}
      {fileName}
      {activeTMs}
      isLocalFile={$openFile?.type === 'local-file'}
      on:rowSelect={handleRowSelect}
      on:confirmTranslation={handleConfirmTranslation}
      on:dismissQA={handleDismissQA}
    />

    <TMQAPanel
      bind:collapsed={sidePanelCollapsed}
      bind:width={sidePanelWidth}
      selectedRow={sidePanelSelectedRow}
      tmMatches={sidePanelTMMatches}
      qaIssues={sidePanelQAIssues}
      tmLoading={sidePanelTMLoading}
      qaLoading={sidePanelQALoading}
      on:applyTM={handleApplyTMFromPanel}
    />
  </div>
</div>

<style>
  .grid-page {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    background: var(--cds-background);
    overflow: hidden;
  }

  .grid-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    min-height: 48px;
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .file-name {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .file-format {
    padding: 0.125rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 500;
    background: var(--cds-layer-02);
    border-radius: 2px;
    color: var(--cds-text-02);
  }

  .grid-with-panel {
    flex: 1;
    display: flex;
    width: 100%;
    overflow: hidden;
    min-height: 0;
  }

  /* TM Indicator Styles */
  .tm-indicator {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .tm-loading {
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .tm-none {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    padding: 0.25rem 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  /* TM Info - Simple display (no dropdown) */
  .tm-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 1rem;
    background: rgba(36, 161, 72, 0.15);
    border: 1px solid rgba(36, 161, 72, 0.3);
    border-radius: 4px;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  :global(.tm-info-icon) {
    color: var(--cds-support-success);
    flex-shrink: 0;
  }

  .tm-info-label {
    font-weight: 600;
    font-size: 0.6875rem;
    color: var(--cds-support-success);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .tm-info-name {
    font-weight: 500;
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tm-info-scope {
    font-size: 0.6875rem;
    color: var(--cds-text-02);
  }

  .tm-info-more {
    font-size: 0.6875rem;
    color: var(--cds-support-success);
    font-weight: 600;
    margin-left: 0.25rem;
  }
</style>
