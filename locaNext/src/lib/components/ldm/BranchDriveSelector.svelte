<script>
  /**
   * BranchDriveSelector.svelte - Always-visible inline Branch+Drive selector
   *
   * Replicates QACompiler's top-bar pattern: two dropdowns + status indicator.
   * PATH-01: Branch dropdown with 5 branches (mainline, cd_beta, cd_alpha, cd_delta, cd_lambda)
   * PATH-02: Drive dropdown with 5 drives (C, D, E, F, G)
   * PATH-03: Real-time path validation on mount and every change
   * PATH-04: Persists selection to localStorage via preferences store
   */
  import { preferences } from '$lib/stores/preferences.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { logger } from '$lib/utils/logger.js';
  import { get } from 'svelte/store';

  const API_BASE = getApiBase();

  const KNOWN_BRANCHES = ['mainline', 'cd_beta', 'cd_alpha', 'cd_delta', 'cd_lambda'];
  const KNOWN_DRIVES = ['C', 'D', 'E', 'F', 'G'];

  // Reactive state from preferences (PATH-04: load persisted values)
  let branch = $state(get(preferences).mdgBranch || 'cd_beta');
  let drive = $state(get(preferences).mdgDrive || 'D');

  // Validation state
  let pathStatus = $state({ ok: false, missing: [], loading: true });
  let rebuilding = $state(false);

  // PATH-03: Configure + Validate on mount
  // On mount: configure backend with saved prefs (NO rebuild — +layout.svelte
  // handles the initial build on login). Only user-driven dropdown changes trigger rebuild.
  import { onMount, onDestroy } from 'svelte';
  import { websocket } from '$lib/api/websocket.js';

  let unsubComplete = null;
  let unsubFailed = null;
  let rebuildTimer = null;

  onMount(async () => {
    // Configure backend with saved prefs, then validate (NO rebuild trigger)
    await configureAndValidate();

    // Listen for MegaIndex build completion to clear rebuilding indicator
    unsubComplete = websocket.on('operation_complete', (data) => {
      if (data.tool_name === 'MegaIndex') {
        rebuilding = false;
        if (rebuildTimer) { clearTimeout(rebuildTimer); rebuildTimer = null; }
        logger.info(`MegaIndex build complete: ${data.current_step || 'done'}`);
      }
    });
    unsubFailed = websocket.on('operation_failed', (data) => {
      if (data.tool_name === 'MegaIndex') {
        rebuilding = false;
        if (rebuildTimer) { clearTimeout(rebuildTimer); rebuildTimer = null; }
        logger.error(`MegaIndex build failed: ${data.error_message || 'unknown'}`);
      }
    });
  });

  onDestroy(() => {
    if (unsubComplete) unsubComplete();
    if (unsubFailed) unsubFailed();
    if (rebuildTimer) { clearTimeout(rebuildTimer); rebuildTimer = null; }
  });

  /**
   * Configure-only: sync saved prefs to backend + validate.
   * Does NOT trigger MegaIndex rebuild (initial build handled by +layout.svelte).
   */
  async function configureAndValidate() {
    preferences.setBranchDrive(branch, drive);
    try {
      await fetch(`${API_BASE}/api/ldm/mapdata/paths/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ branch, drive }),
      });
    } catch (err) {
      logger.warning('Path configure request failed (offline?)', { error: err.message });
    }
    await validatePaths();
  }

  /**
   * Handle user-driven branch or drive change:
   * 1. Save to preferences (PATH-04)
   * 2. Configure backend (POST /mapdata/paths/configure) — triggers MegaIndex REBUILD
   * 3. Validate paths (GET /mapdata/paths/validate)
   */
  async function onSelectionChange() {
    // PATH-04: persist to localStorage
    preferences.setBranchDrive(branch, drive);

    // Configure backend with new branch/drive — triggers MegaIndex REBUILD
    rebuilding = true;
    if (rebuildTimer) { clearTimeout(rebuildTimer); rebuildTimer = null; }
    try {
      const res = await fetch(`${API_BASE}/api/ldm/mapdata/paths/configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({ branch, drive }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        logger.error('Path configure failed', { detail: data.detail });
        rebuilding = false;
      } else {
        // Rebuild runs async — Task Manager shows progress.
        // Fallback timeout polls status if WebSocket event is missed.
        rebuildTimer = setTimeout(async () => {
          if (rebuilding) {
            try {
              const statusRes = await fetch(`${API_BASE}/api/ldm/mega/status`, { headers: getAuthHeaders() });
              if (statusRes.ok) {
                const data = await statusRes.json();
                if (data.built) {
                  rebuilding = false;
                  logger.warn('MegaIndex build completed but WebSocket event was missed');
                }
              }
            } catch { /* ignore — will retry or user can check Task Manager */ }
          }
        }, 120000);
        logger.info(`MegaIndex REBUILD triggered for ${drive}:/${branch}`);
      }
    } catch (err) {
      logger.warning('Path configure request failed (offline?)', { error: err.message });
      rebuilding = false;
    }

    // PATH-03: validate after every change
    await validatePaths();
  }

  /**
   * Check which resolved Perforce paths exist on disk.
   * Calls GET /mapdata/paths/validate.
   */
  async function validatePaths() {
    pathStatus = { ...pathStatus, loading: true };
    try {
      const res = await fetch(`${API_BASE}/api/ldm/mapdata/paths/validate`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        pathStatus = { ok: data.ok, missing: data.missing, loading: false };
      } else {
        pathStatus = { ok: false, missing: ['API error'], loading: false };
      }
    } catch (err) {
      pathStatus = { ok: false, missing: ['Server unavailable'], loading: false };
    }
  }
</script>

<div class="branch-drive-selector">
  <div class="selector-group">
    <label class="selector-label" for="branch-select">Branch</label>
    <select id="branch-select" class="selector-dropdown" bind:value={branch} onchange={onSelectionChange}>
      {#each KNOWN_BRANCHES as b (b)}
        <option value={b}>{b}</option>
      {/each}
    </select>
  </div>

  <div class="selector-group">
    <label class="selector-label" for="drive-select">Drive</label>
    <select id="drive-select" class="selector-dropdown drive-select" bind:value={drive} onchange={onSelectionChange}>
      {#each KNOWN_DRIVES as d (d)}
        <option value={d}>{d}:</option>
      {/each}
    </select>
  </div>

  <span
    class="path-status"
    class:ok={pathStatus.ok && !rebuilding}
    class:error={!pathStatus.ok && !pathStatus.loading && !rebuilding}
    class:loading={pathStatus.loading}
    class:rebuilding={rebuilding}
    title={rebuilding ? 'MegaIndex rebuilding — check Task Manager' : pathStatus.missing.length > 0 ? `Missing: ${pathStatus.missing.join(', ')}` : 'All critical paths found'}
  >
    {#if rebuilding}
      REBUILDING...
    {:else if pathStatus.loading}
      ...
    {:else if pathStatus.ok}
      PATHS OK
    {:else}
      PATHS NOT FOUND ({pathStatus.missing.length})
    {/if}
  </span>
</div>

<style>
  .branch-drive-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
  }

  .selector-group {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .selector-label {
    color: var(--cds-text-02);
    font-size: 0.6875rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.32px;
    white-space: nowrap;
  }

  .selector-dropdown {
    background: var(--cds-field-01);
    color: var(--cds-text-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 2px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-family: inherit;
    cursor: pointer;
    appearance: auto;
  }

  .selector-dropdown:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .drive-select {
    width: 3.5rem;
  }

  .path-status {
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.32px;
    padding: 0.125rem 0.5rem;
    border-radius: 2px;
    white-space: nowrap;
  }

  .path-status.ok {
    color: #42be65;
    background: rgba(66, 190, 101, 0.1);
  }

  .path-status.error {
    color: #fa4d56;
    background: rgba(250, 77, 86, 0.1);
  }

  .path-status.loading {
    color: var(--cds-text-03);
  }

  .path-status.rebuilding {
    color: #4589ff;
    background: rgba(69, 137, 255, 0.1);
    animation: pulse-rebuild 1.5s ease-in-out infinite;
  }

  @keyframes pulse-rebuild {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>
