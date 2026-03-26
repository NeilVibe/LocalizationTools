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

  // PATH-03: Validate on mount
  $effect(() => {
    validatePaths();
  });

  /**
   * Handle branch or drive change:
   * 1. Save to preferences (PATH-04)
   * 2. Configure backend (POST /mapdata/paths/configure)
   * 3. Validate paths (GET /mapdata/paths/validate)
   */
  async function onSelectionChange() {
    // PATH-04: persist to localStorage
    preferences.setBranchDrive(branch, drive);

    // Configure backend with new branch/drive
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
      }
    } catch (err) {
      logger.warn('Path configure request failed (offline?)', { error: err.message });
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
    <label class="selector-label">Branch</label>
    <select class="selector-dropdown" bind:value={branch} onchange={onSelectionChange}>
      {#each KNOWN_BRANCHES as b (b)}
        <option value={b}>{b}</option>
      {/each}
    </select>
  </div>

  <div class="selector-group">
    <label class="selector-label">Drive</label>
    <select class="selector-dropdown drive-select" bind:value={drive} onchange={onSelectionChange}>
      {#each KNOWN_DRIVES as d (d)}
        <option value={d}>{d}:</option>
      {/each}
    </select>
  </div>

  <span
    class="path-status"
    class:ok={pathStatus.ok}
    class:error={!pathStatus.ok && !pathStatus.loading}
    class:loading={pathStatus.loading}
    title={pathStatus.missing.length > 0 ? `Missing: ${pathStatus.missing.join(', ')}` : 'All critical paths found'}
  >
    {#if pathStatus.loading}
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
</style>
