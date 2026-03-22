<script>
  /**
   * MergeModal — Phase 59, Plan 01
   *
   * Single-page merge modal with 4-phase state machine:
   *   configure -> preview -> execute -> done
   *
   * Consumes POST /api/merge/preview (sync) and POST /api/merge/execute (SSE).
   * Uses fetch + ReadableStream for SSE (NOT native EventSource — execute is POST).
   */
  import {
    Modal,
    Button,
    RadioButtonGroup,
    RadioButton,
    Toggle,
    ProgressBar,
    InlineNotification,
    Tag
  } from "carbon-components-svelte";
  import { Merge } from "carbon-icons-svelte";
  import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";
  import { getProjectSettings } from "$lib/stores/projectSettings.js";

  // ---------------------------------------------------------------------------
  // Props
  // ---------------------------------------------------------------------------
  let {
    open = $bindable(false),
    projectId = null,
    projectName = '',
    multiLanguage = false,
    folderPath = ''
  } = $props();

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------
  const MATCH_MODES = [
    { value: 'stringid_only', label: 'StringID Only', description: 'Case-insensitive, SCRIPT/ALL filter' },
    { value: 'strict', label: 'StringID + StrOrigin', description: 'Strict 2-key with nospace fallback' },
    { value: 'strorigin_filename', label: 'StrOrigin + FileName 2PASS', description: '3-tuple then 2-tuple fallback' }
  ];

  const LANGUAGE_MAP = {
    'FRE': 'French', 'ENG': 'English', 'GER': 'German',
    'SPA': 'Spanish', 'ITA': 'Italian', 'JPN': 'Japanese',
    'KOR': 'Korean', 'CHN': 'Chinese', 'RUS': 'Russian',
    'POR': 'Portuguese', 'TUR': 'Turkish', 'ARA': 'Arabic',
    'MULTI': 'Multi-Language'
  };

  // ---------------------------------------------------------------------------
  // State machine
  // ---------------------------------------------------------------------------
  let phase = $state('configure'); // 'configure' | 'preview' | 'execute' | 'done'

  // Configure state
  let matchMode = $state('strict');
  let onlyUntranslated = $state(false);
  let stringidAllCategories = $state(false);

  // Path state (auto-filled from project settings)
  let sourcePath = $state('');
  let targetPath = $state('');
  let pathsConfigured = $state(false);

  // Preview state
  let previewLoading = $state(false);
  let previewResult = $state(null);
  let previewError = $state('');

  // Execute state
  let progressMessages = $state([]);
  let executing = $state(false);
  let progressPercent = $state(0);

  // Done state
  let mergeResult = $state(null);

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  let showCategoryFilter = $derived(matchMode === 'stringid_only');

  let detectedLanguage = $derived.by(() => {
    if (multiLanguage) return 'Multi-Language';
    if (!projectName) return null;
    const suffix = projectName.split('_').pop()?.toUpperCase();
    return LANGUAGE_MAP[suffix] || suffix || null;
  });

  let modalHeading = $derived.by(() => {
    let heading = 'Merge to LOCDEV';
    if (detectedLanguage) {
      heading += ` — ${detectedLanguage}`;
    }
    return heading;
  });

  let hasPreviewErrors = $derived(
    previewResult?.errors?.length > 0
  );

  // ---------------------------------------------------------------------------
  // Reset on open
  // ---------------------------------------------------------------------------
  $effect(() => {
    if (open) {
      phase = 'configure';
      matchMode = 'strict';
      onlyUntranslated = false;
      stringidAllCategories = false;
      previewResult = null;
      previewLoading = false;
      previewError = '';
      progressMessages = [];
      executing = false;
      progressPercent = 0;
      mergeResult = null;

      // Auto-fill paths from project settings
      if (projectId) {
        const settings = getProjectSettings(projectId);
        sourcePath = settings.exportPath || '';
        targetPath = settings.locPath || '';
        pathsConfigured = !!(sourcePath && targetPath);
      } else {
        sourcePath = '';
        targetPath = '';
        pathsConfigured = false;
      }
    }
  });

  // ---------------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------------
  function buildRequestBody() {
    return {
      source_path: sourcePath,
      target_path: targetPath,
      export_path: sourcePath,
      match_mode: matchMode,
      only_untranslated: onlyUntranslated,
      stringid_all_categories: stringidAllCategories,
      multi_language: multiLanguage
    };
  }

  // ---------------------------------------------------------------------------
  // Preview (dry-run)
  // ---------------------------------------------------------------------------
  async function runPreview() {
    previewLoading = true;
    previewError = '';
    previewResult = null;
    phase = 'preview';

    try {
      const API_BASE = getApiBase();
      const response = await fetch(`${API_BASE}/api/merge/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(buildRequestBody())
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        previewError = errData.detail || errData.error || `Server error: ${response.status}`;
        return;
      }

      previewResult = await response.json();
    } catch (err) {
      previewError = `Failed to reach server: ${err.message}`;
    } finally {
      previewLoading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Execute (SSE streaming via fetch + ReadableStream)
  // ---------------------------------------------------------------------------
  async function executeMerge() {
    executing = true;
    progressMessages = [];
    progressPercent = 0;
    phase = 'execute';

    const filesExpected = previewResult?.files_processed || 1;
    let filesProcessed = 0;

    try {
      const API_BASE = getApiBase();
      const response = await fetch(`${API_BASE}/api/merge/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(buildRequestBody())
      });

      if (!response.ok) {
        if (response.status === 409) {
          progressMessages = [...progressMessages, '[Error] A merge is already in progress'];
          executing = false;
          return;
        }
        const errData = await response.json().catch(() => ({}));
        progressMessages = [...progressMessages, `[Error] ${errData.detail || errData.error || response.status}`];
        executing = false;
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            handleSSEEvent(currentEvent, data);
            currentEvent = 'message'; // Reset after processing

            // Update progress estimate
            if (currentEvent === 'progress') {
              filesProcessed++;
              progressPercent = Math.min(
                (filesProcessed / filesExpected) * 100,
                95
              );
            }
          }
          // Empty lines and other prefixes are ignored
        }
      }
    } catch (err) {
      progressMessages = [...progressMessages, `[Error] Connection lost: ${err.message}`];
    } finally {
      executing = false;
    }
  }

  function handleSSEEvent(eventType, data) {
    switch (eventType) {
      case 'progress':
        progressMessages = [...progressMessages, data];
        // Estimate progress from file processing messages
        if (previewResult?.files_processed) {
          const count = progressMessages.filter(m => m.startsWith('Processing ')).length;
          progressPercent = Math.min((count / previewResult.files_processed) * 100, 95);
        }
        break;
      case 'log': {
        try {
          const logData = JSON.parse(data);
          const prefix = logData.level === 'error' ? '[ERROR]' :
                         logData.level === 'warning' ? '[WARN]' : '[INFO]';
          progressMessages = [...progressMessages, `${prefix} ${logData.message}`];
        } catch {
          progressMessages = [...progressMessages, data];
        }
        break;
      }
      case 'complete': {
        try {
          mergeResult = JSON.parse(data);
        } catch {
          mergeResult = {};
        }
        progressPercent = 100;
        phase = 'done';
        break;
      }
      case 'error':
        progressMessages = [...progressMessages, `[ERROR] ${data}`];
        executing = false;
        break;
      case 'ping':
        // Keepalive — ignore
        break;
      default:
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  function goBackToConfigure() {
    phase = 'configure';
    previewResult = null;
    previewError = '';
  }

  function handleClose() {
    open = false;
  }
</script>

<Modal
  bind:open
  modalHeading={modalHeading}
  passiveModal={phase === 'execute'}
  size="lg"
  hasForm
  preventCloseOnClickOutside={phase === 'execute'}
  onclose={handleClose}
>
  <div class="merge-modal" slot="default" >
    <!-- Language badge -->
    {#if detectedLanguage}
      <div class="language-badge">
        <Tag type="blue" size="sm">
          <Merge size={14} />
          {detectedLanguage}
        </Tag>
      </div>
    {/if}

    <!-- ================================================================== -->
    <!-- PHASE: Configure                                                    -->
    <!-- ================================================================== -->
    {#if phase === 'configure'}
      <div class="phase-configure">
        <!-- Path warning -->
        {#if !pathsConfigured}
          <InlineNotification
            kind="warning"
            title="Paths not configured"
            subtitle="LOC PATH and EXPORT PATH must be set in Project Settings before merging."
            hideCloseButton
            lowContrast
          />
        {:else}
          <div class="path-summary">
            <div class="path-row">
              <span class="path-label">Source (Export):</span>
              <span class="path-value">{sourcePath}</span>
            </div>
            <div class="path-row">
              <span class="path-label">Target (LOCDEV):</span>
              <span class="path-value">{targetPath}</span>
            </div>
          </div>
        {/if}

        <!-- Match Mode -->
        <div class="config-section">
          <h4>Match Type</h4>
          <RadioButtonGroup
            bind:selected={matchMode}
            legendText="How to match source entries to target entries"
          >
            {#each MATCH_MODES as mode (mode.value)}
              <RadioButton
                value={mode.value}
                labelText="{mode.label} — {mode.description}"
              />
            {/each}
          </RadioButtonGroup>
        </div>

        <!-- Scope toggle -->
        <div class="config-section">
          <h4>Scope</h4>
          <Toggle
            bind:toggled={onlyUntranslated}
            labelText="Only Untranslated"
            labelA="All entries"
            labelB="Untranslated only"
          />
        </div>

        <!-- Category filter (conditional on StringID Only) -->
        {#if showCategoryFilter}
          <div class="config-section">
            <h4>Category Filter</h4>
            <Toggle
              bind:toggled={stringidAllCategories}
              labelText="All Categories (SCRIPT+ALL)"
              labelA="Default categories"
              labelB="All categories"
            />
          </div>
        {/if}

        <!-- Actions -->
        <div class="modal-actions">
          <Button
            kind="primary"
            disabled={!pathsConfigured}
            onclick={runPreview}
          >
            Preview Merge
          </Button>
          <Button kind="secondary" onclick={handleClose}>
            Cancel
          </Button>
        </div>
      </div>

    <!-- ================================================================== -->
    <!-- PHASE: Preview                                                      -->
    <!-- ================================================================== -->
    {:else if phase === 'preview'}
      <div class="phase-preview">
        {#if previewLoading}
          <div class="loading-area">
            <ProgressBar helperText="Running dry-run preview..." />
          </div>
        {:else if previewError}
          <InlineNotification
            kind="error"
            title="Preview failed"
            subtitle={previewError}
            hideCloseButton
            lowContrast
          />
        {:else if previewResult}
          <!-- Summary table -->
          <div class="preview-summary">
            <h4>Preview Results</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-value">{previewResult.files_processed ?? 0}</span>
                <span class="stat-label">Files Processed</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{previewResult.total_matched ?? 0}</span>
                <span class="stat-label">Entries Matched</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{previewResult.total_not_found ?? 0}</span>
                <span class="stat-label">Not Found</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{previewResult.total_skipped ?? 0}</span>
                <span class="stat-label">Skipped</span>
              </div>
              {#if previewResult.total_skipped_translated > 0}
                <div class="stat-item">
                  <span class="stat-value">{previewResult.total_skipped_translated}</span>
                  <span class="stat-label">Skipped (Translated)</span>
                </div>
              {/if}
              {#if previewResult.total_corrections > 0}
                <div class="stat-item">
                  <span class="stat-value">{previewResult.total_corrections}</span>
                  <span class="stat-label">Corrections</span>
                </div>
              {/if}
            </div>
          </div>

          <!-- Multi-language breakdown -->
          {#if previewResult.per_language && previewResult.scan}
            <div class="multi-lang-section">
              <h4>Per-Language Breakdown</h4>
              <table class="lang-table">
                <thead>
                  <tr>
                    <th>Language</th>
                    <th>Files</th>
                    <th>Matched</th>
                  </tr>
                </thead>
                <tbody>
                  {#each Object.keys(previewResult.per_language) as lang (lang)}
                    <tr>
                      <td>{LANGUAGE_MAP[lang.toUpperCase()] || lang}</td>
                      <td>{previewResult.scan?.[lang]?.files ?? '—'}</td>
                      <td>{previewResult.per_language[lang]?.matched ?? 0}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}

          <!-- Overwrite warnings -->
          {#if previewResult.overwrite_warnings?.length > 0}
            <div class="warnings-section">
              {#each previewResult.overwrite_warnings as warning (warning)}
                <InlineNotification
                  kind="warning"
                  title="Overwrite"
                  subtitle={warning}
                  hideCloseButton
                  lowContrast
                />
              {/each}
            </div>
          {/if}

          <!-- Errors -->
          {#if previewResult.errors?.length > 0}
            <div class="errors-section">
              {#each previewResult.errors as error (error)}
                <InlineNotification
                  kind="error"
                  title="Error"
                  subtitle={error}
                  hideCloseButton
                  lowContrast
                />
              {/each}
            </div>
          {/if}
        {/if}

        <!-- Actions -->
        <div class="modal-actions">
          <Button kind="secondary" onclick={goBackToConfigure}>
            Back
          </Button>
          <Button
            kind="danger"
            disabled={previewLoading || hasPreviewErrors || !previewResult}
            onclick={executeMerge}
          >
            Execute Merge
          </Button>
        </div>
      </div>

    <!-- ================================================================== -->
    <!-- PHASE: Execute                                                      -->
    <!-- ================================================================== -->
    {:else if phase === 'execute'}
      <div class="phase-execute">
        <ProgressBar
          value={progressPercent}
          max={100}
          labelText="Merging files..."
          helperText={executing ? `${Math.round(progressPercent)}% complete` : 'Finishing...'}
        />

        <div class="progress-log">
          {#each progressMessages as msg, i (i)}
            <div class="log-entry" class:log-error={msg.startsWith('[ERROR]')} class:log-warn={msg.startsWith('[WARN]')}>
              {msg}
            </div>
          {/each}
        </div>

        {#if !executing && phase === 'execute'}
          <div class="modal-actions">
            <Button kind="secondary" onclick={goBackToConfigure}>
              Back to Configure
            </Button>
          </div>
        {/if}
      </div>

    <!-- ================================================================== -->
    <!-- PHASE: Done                                                         -->
    <!-- ================================================================== -->
    {:else if phase === 'done'}
      <div class="phase-done">
        <InlineNotification
          kind="success"
          title="Merge Complete"
          subtitle="All files have been processed successfully."
          hideCloseButton
          lowContrast
        />

        {#if mergeResult}
          <div class="result-summary">
            <h4>Summary</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-value">{mergeResult.total_matched ?? 0}</span>
                <span class="stat-label">Matched</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{mergeResult.total_updated ?? 0}</span>
                <span class="stat-label">Updated</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{mergeResult.total_not_found ?? 0}</span>
                <span class="stat-label">Not Found</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{mergeResult.total_skipped ?? 0}</span>
                <span class="stat-label">Skipped</span>
              </div>
              {#if mergeResult.total_skipped_translated > 0}
                <div class="stat-item">
                  <span class="stat-value">{mergeResult.total_skipped_translated}</span>
                  <span class="stat-label">Skipped (Translated)</span>
                </div>
              {/if}
            </div>
          </div>

          <!-- Multi-language result breakdown -->
          {#if mergeResult.per_language}
            <div class="multi-lang-section">
              <h4>Per-Language Results</h4>
              <table class="lang-table">
                <thead>
                  <tr>
                    <th>Language</th>
                    <th>Matched</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {#each Object.keys(mergeResult.per_language) as lang (lang)}
                    <tr>
                      <td>{LANGUAGE_MAP[lang.toUpperCase()] || lang}</td>
                      <td>{mergeResult.per_language[lang]?.matched ?? 0}</td>
                      <td>{mergeResult.per_language[lang]?.updated ?? 0}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        {/if}

        <!-- Progress log (collapsed) -->
        {#if progressMessages.length > 0}
          <details class="log-details">
            <summary>View execution log ({progressMessages.length} messages)</summary>
            <div class="progress-log">
              {#each progressMessages as msg, i (i)}
                <div class="log-entry" class:log-error={msg.startsWith('[ERROR]')} class:log-warn={msg.startsWith('[WARN]')}>
                  {msg}
                </div>
              {/each}
            </div>
          </details>
        {/if}

        <div class="modal-actions">
          <Button kind="primary" onclick={handleClose}>
            Close
          </Button>
        </div>
      </div>
    {/if}
  </div>
</Modal>

<style>
  .merge-modal {
    padding: 0.5rem 0;
  }

  .language-badge {
    margin-bottom: 1rem;
  }

  .language-badge :global(.bx--tag) {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  /* Path summary */
  .path-summary {
    background: var(--cds-ui-02, #262626);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
  }

  .path-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
    font-size: 0.8125rem;
  }

  .path-row:last-child {
    margin-bottom: 0;
  }

  .path-label {
    font-weight: 600;
    color: var(--cds-text-02, #c6c6c6);
    white-space: nowrap;
  }

  .path-value {
    color: var(--cds-text-01, #f4f4f4);
    word-break: break-all;
  }

  /* Config sections */
  .config-section {
    margin-bottom: 1.25rem;
  }

  .config-section h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
  }

  /* Stats grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.75rem;
    margin: 0.75rem 0;
  }

  .stat-item {
    background: var(--cds-ui-02, #262626);
    border-radius: 4px;
    padding: 0.75rem;
    text-align: center;
  }

  .stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--cds-text-01, #f4f4f4);
  }

  .stat-label {
    display: block;
    font-size: 0.75rem;
    color: var(--cds-text-02, #c6c6c6);
    margin-top: 0.25rem;
  }

  /* Multi-language table */
  .multi-lang-section {
    margin: 1rem 0;
  }

  .multi-lang-section h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
  }

  .lang-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8125rem;
  }

  .lang-table th,
  .lang-table td {
    padding: 0.5rem 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--cds-ui-03, #393939);
  }

  .lang-table th {
    font-weight: 600;
    color: var(--cds-text-02, #c6c6c6);
  }

  .lang-table td {
    color: var(--cds-text-01, #f4f4f4);
  }

  /* Warnings and errors sections */
  .warnings-section,
  .errors-section {
    margin: 0.75rem 0;
  }

  /* Progress log */
  .progress-log {
    max-height: 300px;
    overflow-y: auto;
    background: var(--cds-ui-01, #161616);
    border: 1px solid var(--cds-ui-03, #393939);
    border-radius: 4px;
    padding: 0.5rem;
    margin: 0.75rem 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    line-height: 1.4;
  }

  .log-entry {
    padding: 0.125rem 0.25rem;
    color: var(--cds-text-02, #c6c6c6);
  }

  .log-error {
    color: var(--cds-support-01, #fa4d56);
  }

  .log-warn {
    color: var(--cds-support-03, #f1c21b);
  }

  /* Log details (done phase) */
  .log-details {
    margin: 1rem 0;
  }

  .log-details summary {
    cursor: pointer;
    font-size: 0.8125rem;
    color: var(--cds-link-01, #78a9ff);
    margin-bottom: 0.5rem;
  }

  /* Loading area */
  .loading-area {
    padding: 2rem 0;
  }

  /* Preview/result summary headings */
  .preview-summary h4,
  .result-summary h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
  }

  /* Actions */
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-ui-03, #393939);
  }
</style>
