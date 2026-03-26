<script>
  /**
   * GridPage.svelte - Phase 10 UI Overhaul
   *
   * Full-page grid viewer for editing translation files.
   * Includes VirtualGrid and TM/QA side panel.
   */
  import { onDestroy } from 'svelte';
  import { openFile, closeGrid } from '$lib/stores/navigation.js';
  import { preferences } from '$lib/stores/preferences.js';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import VirtualGrid from '$lib/components/ldm/VirtualGrid.svelte';
  import RightPanel from '$lib/components/ldm/RightPanel.svelte';
  import { Button, InlineLoading } from 'carbon-components-svelte';
  import { ArrowLeft, Column, Document, DataBase } from 'carbon-icons-svelte';

  // Props
  let {
    fileId: propFileId = null,
    fileName: propFileName = '',
    linkedTM = null,
    onShowGridColumns = () => {},
    onShowReferenceSettings = () => {},
    onShowBranchDriveSettings = () => {},
    onDismissQA = undefined
  } = $props();

  // Derive fileId/fileName from prop OR openFile store (fixes bind cleanup race condition)
  // When FilesPage unmounts, its $bindable cleanup can reset the prop to null.
  // The openFile store is the authoritative source set by openFileInGrid().
  let fileId = $derived(propFileId ?? $openFile?.id ?? null);
  let fileName = $derived(propFileName || $openFile?.name || $openFile?.original_filename || '');

  // Derive file type from openFile store (Dual UI Mode - Phase 08)
  let fileType = $derived($openFile?.file_type || 'translator');
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

  // AC Context results (Phase 88)
  let sidePanelContextResults = $state([]);
  let sidePanelContextLoading = $state(false);

  // Active TMs state (TM Hierarchy)
  let activeTMs = $state([]);
  let activeTMsLoading = $state(false);

  // Leverage stats
  let leverageStats = $state(null);

  // AbortController for cancelling in-flight fetches
  let fetchController = null;
  let contextAbortController = null;

  /**
   * Load active TMs for the current file (TM Hierarchy cascade)
   */
  async function loadActiveTMs(signal) {
    if (!fileId) return;

    activeTMsLoading = true;
    try {
      logger.apiCall(`/api/ldm/files/${fileId}/active-tms`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/active-tms`, {
        headers: getAuthHeaders(),
        signal
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      activeTMs = await response.json();
      logger.success('Active TMs loaded', { count: activeTMs.length });
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.error('Failed to load active TMs', { error: err.message });
      activeTMs = [];
    } finally {
      activeTMsLoading = false;
    }
  }

  /**
   * Load leverage stats for the current file (non-blocking)
   */
  async function loadLeverageStats(signal) {
    if (!fileId) return;

    try {
      logger.apiCall(`/api/ldm/files/${fileId}/leverage`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/leverage`, {
        headers: getAuthHeaders(),
        signal
      });

      if (!response.ok) {
        logger.warning('Failed to load leverage stats', { status: response.status });
        return;
      }

      leverageStats = await response.json();
      logger.success('Leverage stats loaded', { exact: leverageStats.exact_pct, fuzzy: leverageStats.fuzzy_pct, new: leverageStats.new_pct });
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.warning('Leverage stats unavailable', { error: err.message });
      leverageStats = null;
    }
  }

  // Load active TMs and leverage when fileId changes
  $effect(() => {
    if (fileId) {
      fetchController?.abort();
      fetchController = new AbortController();
      const { signal } = fetchController;
      loadActiveTMs(signal);
      loadLeverageStats(signal);
    }
    return () => { fetchController?.abort(); };
  });


  // Debounce timer for TM loading on rapid row selection
  let tmDebounceTimer = null;

  // Cleanup on destroy
  onDestroy(() => {
    clearTimeout(tmDebounceTimer);
    fetchController?.abort();
    contextAbortController?.abort();
  });

  /**
   * Handle row selection - load TM matches (debounced)
   */
  async function handleRowSelect(data) {
    const { row } = data;
    sidePanelSelectedRow = row;
    sidePanelTMMatches = [];
    sidePanelContextResults = [];
    sidePanelQAIssues = row?.qa_issues || [];

    if (!row?.source) return;

    // Debounce TM loading to avoid API spam on rapid row navigation
    clearTimeout(tmDebounceTimer);
    tmDebounceTimer = setTimeout(() => loadTMMatchesForRow(row), 200);

    // AC context search (AbortController handles rapid-click cancellation)
    loadContextForRow(row);
  }

  /**
   * Load TM matches for a row - USES HIERARCHY TMs, falls back to project-row search
   */
  async function loadTMMatchesForRow(row) {
    if (!row?.source || !fileId) return;

    sidePanelTMLoading = true;
    try {
      const params = new URLSearchParams({
        source: row.source,
        threshold: $preferences.tmThreshold.toString(),
        max_results: '10',
        file_id: fileId.toString()
      });

      // If active TMs exist, search via TM entries; otherwise fall back to project-row search
      if (activeTMs.length > 0) {
        // TM hierarchy search — use first active TM
        params.append('tm_id', activeTMs[0].tm_id.toString());
      } else {
        // Fallback: search project rows for similar texts (no tm_id = project-row mode)
        const projectId = $openFile?.project_id;
        if (projectId) params.append('project_id', projectId.toString());
        if (row.id) params.append('exclude_row_id', row.id.toString());
      }

      logger.apiCall('/api/ldm/tm/suggest', 'GET', { file_id: fileId, hasTM: activeTMs.length > 0 });
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
   * Load AC context results for a row (Phase 88)
   * Uses AbortController to cancel stale requests on rapid row clicking.
   */
  async function loadContextForRow(row) {
    if (!row?.source || activeTMs.length === 0) return;

    // Abort previous context request
    contextAbortController?.abort();
    contextAbortController = new AbortController();

    sidePanelContextLoading = true;
    try {
      logger.apiCall('/api/ldm/tm/context', 'POST', { tm_id: activeTMs[0].tm_id });
      const response = await fetch(`${API_BASE}/api/ldm/tm/context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          source: row.source,
          tm_id: activeTMs[0].tm_id,
          max_results: 10
        }),
        signal: contextAbortController.signal
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      sidePanelContextResults = data.results || [];
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.error('Failed to load context results', { error: err.message });
      sidePanelContextResults = [];
    } finally {
      sidePanelContextLoading = false;
    }
  }

  /**
   * Apply TM suggestion from side panel
   */
  function handleApplyTMFromPanel(data) {
    const { target } = data;
    if (virtualGrid && sidePanelSelectedRow) {
      virtualGrid.applyTMToRow(sidePanelSelectedRow.line_number, target);
    }
  }

  /**
   * Apply AI suggestion from side panel
   */
  function handleApplySuggestionFromPanel(data) {
    const { target } = data;
    if (virtualGrid && sidePanelSelectedRow) {
      virtualGrid.applyTMToRow(sidePanelSelectedRow.line_number, target);
      logger.userAction('Applied AI suggestion from panel', { row: sidePanelSelectedRow.line_number });
    }
  }

  /**
   * Handle translation confirmation (auto-add to TM)
   * Uses hierarchy activeTMs - entries auto-added to first active TM
   * VirtualGrid sends: {rowId, source, target}
   */
  async function handleConfirmTranslation(data) {
    const { rowId, source, target } = data;

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
  function handleDismissQA(data) {
    onDismissQA?.(data);
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

  export function openEditModalByRowId(rowId) {
    return virtualGrid?.openEditModalByRowId(rowId);
  }

  export function updateRowQAFlag(rowId, count) {
    virtualGrid?.updateRowQAFlag(rowId, count);
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
        onclick={goBack}
      />
      <span class="file-name">{fileName || 'Untitled'}</span>
      {#if $openFile?.format}
        <span class="file-format">{$openFile.format.toUpperCase()}</span>
      {/if}
    </div>
    <!-- TM Indicator (TM Hierarchy) - Simple display with TM ACTIVE prefix -->
    <div class="tm-indicator" class:has-tm={activeTMs.length > 0}>
      {#if activeTMsLoading}
        <span class="tm-loading"><InlineLoading description="Loading TM..." /></span>
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
        onclick={onShowGridColumns}
      />
      <Button
        kind="ghost"
        size="small"
        icon={Document}
        iconDescription="Reference Settings"
        tooltipAlignment="end"
        onclick={onShowReferenceSettings}
      />
      <Button
        kind="ghost"
        size="small"
        icon={DataBase}
        iconDescription="Branch & Drive Settings"
        tooltipAlignment="end"
        onclick={onShowBranchDriveSettings}
      />
    </div>
  </div>

  <!-- Grid + Side Panel -->
  <div class="grid-with-panel">
    <VirtualGrid
      bind:this={virtualGrid}
      {fileId}
      {fileName}
      {fileType}
      {activeTMs}
      isLocalFile={$openFile?.type === 'local-file'}
      onRowSelect={handleRowSelect}
      onConfirmTranslation={handleConfirmTranslation}
      onDismissQA={handleDismissQA}
    />

    <RightPanel
      bind:collapsed={sidePanelCollapsed}
      bind:width={sidePanelWidth}
      selectedRow={sidePanelSelectedRow}
      tmMatches={sidePanelTMMatches}
      qaIssues={sidePanelQAIssues}
      tmLoading={sidePanelTMLoading}
      qaLoading={sidePanelQALoading}
      contextResults={sidePanelContextResults}
      contextLoading={sidePanelContextLoading}
      {leverageStats}
      onApplyTM={handleApplyTMFromPanel}
      onApplySuggestion={handleApplySuggestionFromPanel}
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
    display: flex;
    align-items: center;
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
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-left: 3px solid var(--cds-support-success);
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
