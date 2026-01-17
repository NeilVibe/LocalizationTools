<script>
  import {
    Modal,
    Button,
    ProgressBar,
    InlineNotification,
    Tag
  } from "carbon-components-svelte";
  import { Renew, Checkmark, Close, Download, Restart, Rocket, Flash } from "carbon-icons-svelte";
  import { onMount, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);

  // Svelte 5: Modal state
  let open = $state(false);
  let updateState = $state('idle'); // 'idle' | 'checking' | 'available' | 'downloading' | 'downloaded' | 'error'

  // Svelte 5: Update mode
  let updateMode = $state('full'); // 'patch' | 'full'
  let patchAvailable = $state(false);

  // Svelte 5: Update info
  let updateInfo = $state({
    version: '',
    releaseNotes: '',
    releaseDate: ''
  });

  // Svelte 5: Patch update components
  let patchComponents = $state([]);
  let totalPatchSize = $state(0);
  let fullInstallerSize = $state(624 * 1024 * 1024); // ~624 MB

  // Svelte 5: Download progress
  let progress = $state({
    percent: 0,
    transferred: 0,
    total: 0,
    bytesPerSecond: 0,
    currentComponent: ''
  });

  // Svelte 5: Error state
  let errorMessage = $state('');

  // Svelte 5: Current version (from backend health)
  let currentVersion = $state('');

  // Calculate savings percentage
  let savingsPercent = $derived(
    totalPatchSize > 0 ? Math.round((1 - totalPatchSize / fullInstallerSize) * 100) : 97
  );

  // Fetch current version on mount AND check for pending updates
  onMount(async () => {
    // Get current version from backend
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (response.ok) {
        const health = await response.json();
        currentVersion = health.version || '';
        logger.info('UpdateModal: Got current version', { version: currentVersion });
      }
    } catch (err) {
      logger.warning('UpdateModal: Could not fetch current version', { error: err.message });
    }

    // Check for Electron update API
    if (typeof window !== 'undefined' && window.electronUpdate) {
      // CRITICAL: Check for pending updates FIRST (solves race condition)
      try {
        const state = await window.electronUpdate.getUpdateState();
        logger.info('UpdateModal: Got update state on mount', state);

        if (state.hasUpdate) {
          updateInfo = {
            version: state.updateInfo?.version || '',
            releaseNotes: state.updateInfo?.releaseNotes || '',
            releaseDate: state.updateInfo?.releaseDate || ''
          };
          updateState = state.state;
          open = true;

          // Check for patch update availability
          await checkPatchUpdate();
        }
      } catch (err) {
        logger.warning('UpdateModal: Could not get update state', { error: err.message });
      }

      // Register event listeners
      window.electronUpdate.onUpdateAvailable(handleUpdateAvailable);
      window.electronUpdate.onUpdateProgress(handleUpdateProgress);
      window.electronUpdate.onUpdateDownloaded(handleUpdateDownloaded);
      window.electronUpdate.onUpdateError(handleUpdateError);

      // Patch update progress listener
      if (window.electronUpdate.onPatchProgress) {
        window.electronUpdate.onPatchProgress(handlePatchProgress);
      }

      logger.info('UpdateModal: Registered update event listeners');
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined' && window.electronUpdate) {
      window.electronUpdate.removeListeners();
      logger.info('UpdateModal: Cleaned up update event listeners');
    }
  });

  // Check if patch update is available
  async function checkPatchUpdate() {
    logger.info('UpdateModal: Checking for patch update...');

    if (!window.electronUpdate?.checkPatchUpdate) {
      logger.warning('UpdateModal: checkPatchUpdate API not available');
      patchAvailable = false;
      return;
    }

    try {
      const result = await window.electronUpdate.checkPatchUpdate();
      logger.info('UpdateModal: Patch check result', {
        success: result.success,
        available: result.available,
        reason: result.reason,
        version: result.version,
        updateCount: result.updates?.length,
        totalSize: result.totalSize,
        error: result.error
      });

      if (result.success && result.available) {
        patchAvailable = true;
        updateMode = 'patch';
        patchComponents = result.updates || [];
        totalPatchSize = result.totalSize || 0;
        logger.success('UpdateModal: PATCH UPDATE AVAILABLE!', {
          components: patchComponents.map(c => c.name),
          size: formatBytes(totalPatchSize),
          savings: savingsPercent + '%'
        });
      } else {
        patchAvailable = false;
        updateMode = 'full';
        logger.info('UpdateModal: No patch available, will use full update', {
          reason: result.reason,
          error: result.error
        });
      }
    } catch (err) {
      patchAvailable = false;
      updateMode = 'full';
      logger.error('UpdateModal: Patch check EXCEPTION', {
        error: err.message,
        stack: err.stack?.split('\n').slice(0, 3).join(' | ')
      });
    }
  }

  function handleUpdateAvailable(info) {
    logger.info('UpdateModal: Update available', info);
    updateInfo = {
      version: info.version || '',
      releaseNotes: info.releaseNotes || '',
      releaseDate: info.releaseDate || ''
    };
    updateState = 'available';
    open = true;

    // Check for patch updates when update is available
    checkPatchUpdate();
  }

  function handleUpdateProgress(progressObj) {
    progress = {
      percent: progressObj.percent || 0,
      transferred: progressObj.transferred || 0,
      total: progressObj.total || 0,
      bytesPerSecond: progressObj.bytesPerSecond || 0,
      currentComponent: ''
    };
    updateState = 'downloading';
  }

  function handlePatchProgress(progressObj) {
    progress = {
      percent: progressObj.overallProgress || 0,
      transferred: progressObj.transferred || 0,
      total: progressObj.total || 0,
      bytesPerSecond: 0,
      currentComponent: progressObj.component || ''
    };
    updateState = 'downloading';
  }

  function handleUpdateDownloaded(info) {
    logger.success('UpdateModal: Update downloaded', info);
    updateInfo = {
      ...updateInfo,
      version: info.version || updateInfo.version
    };
    updateState = 'downloaded';
  }

  function handleUpdateError(err) {
    logger.error('UpdateModal: Update error', { error: err });
    errorMessage = typeof err === 'string' ? err : (err.message || 'Unknown error');
    updateState = 'error';
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatSpeed(bytesPerSecond) {
    return formatBytes(bytesPerSecond) + '/s';
  }

  function formatTimeRemaining() {
    if (progress.bytesPerSecond <= 0 || progress.total <= 0) return '';
    const remaining = progress.total - progress.transferred;
    const seconds = Math.ceil(remaining / progress.bytesPerSecond);
    if (seconds < 60) return `~${seconds}s remaining`;
    const minutes = Math.floor(seconds / 60);
    return `~${minutes}m remaining`;
  }

  async function handleDownload() {
    logger.userAction('User clicked download update', { mode: updateMode });
    updateState = 'downloading';

    if (updateMode === 'patch' && patchAvailable && window.electronUpdate?.applyPatchUpdate) {
      // Use patch update (LAUNCHER-style)
      try {
        const result = await window.electronUpdate.applyPatchUpdate(patchComponents);
        if (result.success) {
          updateState = 'downloaded';
        } else if (result.partial) {
          // Some components failed - offer full update
          logger.warning('Patch update partial failure, falling back to full');
          updateMode = 'full';
          patchAvailable = false;
          window.electronUpdate.downloadUpdate();
        } else {
          handleUpdateError(result.error || 'Patch update failed');
        }
      } catch (err) {
        // Fallback to full update
        logger.warning('Patch update failed, falling back to full', { error: err.message });
        updateMode = 'full';
        patchAvailable = false;
        window.electronUpdate.downloadUpdate();
      }
    } else {
      // Full update
      window.electronUpdate?.downloadUpdate();
    }
  }

  function handleRestartNow() {
    logger.userAction('User clicked restart now', { mode: updateMode });

    if (updateMode === 'patch') {
      // PATCH update: Use restartApp which handles pending file swaps
      logger.info('Using restartApp for PATCH update');
      window.electronUpdate?.restartApp?.() || window.electronUpdate?.quitAndInstall();
    } else {
      // FULL update: Use quitAndInstall (runs NSIS installer)
      logger.info('Using quitAndInstall for FULL update');
      window.electronUpdate?.quitAndInstall();
    }
  }

  function handleLater() {
    logger.userAction('User clicked update later');
    open = false;
  }

  function handleClose() {
    if (updateState === 'downloading') return;
    open = false;
  }
</script>

<Modal
  bind:open
  modalHeading="Update Available"
  hasForm
  primaryButtonText={updateState === 'downloaded' ? 'Restart Now' : updateState === 'available' ? 'Download Update' : ''}
  secondaryButtonText={updateState === 'downloading' ? '' : 'Later'}
  primaryButtonDisabled={updateState === 'downloading' || updateState === 'error'}
  on:click:button--primary={() => updateState === 'downloaded' ? handleRestartNow() : handleDownload()}
  on:click:button--secondary={handleLater}
  on:close={handleClose}
  preventCloseOnClickOutside={updateState === 'downloading'}
  size="sm"
>
  <div class="update-content">
    <!-- Header with version info -->
    <div class="version-info">
      <div class="version-badge">
        <Tag type="green" size="sm">New</Tag>
        <span class="new-version">v{updateInfo.version}</span>
      </div>
      {#if currentVersion}
        <p class="current-version">You have v{currentVersion}</p>
      {/if}
    </div>

    <!-- State: Available -->
    {#if updateState === 'available'}
      <div class="update-message">
        <!-- Patch update banner -->
        {#if patchAvailable && patchComponents.length > 0}
          <div class="patch-banner">
            <div class="patch-header">
              <Flash size={20} />
              <span>Smart Update</span>
              <Tag type="cyan" size="sm">{savingsPercent}% smaller</Tag>
            </div>
            <p class="patch-description">
              Only downloading changed components
            </p>
            <div class="size-comparison">
              <div class="size-item patch-size">
                <span class="size-label">This update</span>
                <span class="size-value">{formatBytes(totalPatchSize)}</span>
              </div>
              <div class="size-divider">vs</div>
              <div class="size-item full-size">
                <span class="size-label">Full installer</span>
                <span class="size-value crossed">{formatBytes(fullInstallerSize)}</span>
              </div>
            </div>
            <div class="components-list">
              {#each patchComponents as component}
                <div class="component-item">
                  <Checkmark size={16} />
                  <span class="component-name">{component.description || component.name}</span>
                  <span class="component-size">{formatBytes(component.size)}</span>
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <p>A new version of LocaNext is ready to download.</p>
        {/if}

        {#if updateInfo.releaseNotes}
          <div class="release-notes">
            <h4>What's New:</h4>
            <div class="notes-content">
              {updateInfo.releaseNotes}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- State: Downloading -->
    {#if updateState === 'downloading'}
      <div class="download-progress">
        {#if updateMode === 'patch' && progress.currentComponent}
          <div class="current-component">
            <Flash size={16} />
            <span>Updating: {progress.currentComponent}</span>
          </div>
        {/if}
        <ProgressBar
          value={progress.percent}
          labelText={updateMode === 'patch' ? 'Applying smart update...' : 'Downloading update...'}
          helperText="{formatBytes(progress.transferred)} / {formatBytes(progress.total)}"
        />
        <div class="progress-details">
          {#if progress.bytesPerSecond > 0}
            <span class="speed">{formatSpeed(progress.bytesPerSecond)}</span>
            <span class="time-remaining">{formatTimeRemaining()}</span>
          {:else}
            <span class="speed">Processing...</span>
          {/if}
        </div>
      </div>
    {/if}

    <!-- State: Downloaded -->
    {#if updateState === 'downloaded'}
      <InlineNotification
        kind="success"
        title="Ready to install"
        subtitle={updateMode === 'patch' ? 'Smart update applied! Restart to activate.' : 'The update has been downloaded.'}
        hideCloseButton
      />
      {#if updateMode === 'patch'}
        <div class="patch-success">
          <Rocket size={24} />
          <p>Updated in record time! Only {formatBytes(totalPatchSize)} downloaded.</p>
        </div>
      {/if}
      <p class="restart-note">
        The application will close and restart automatically.
      </p>
    {/if}

    <!-- State: Error -->
    {#if updateState === 'error'}
      <InlineNotification
        kind="error"
        title="Update failed"
        subtitle={errorMessage}
        hideCloseButton
      />
      <p class="error-note">
        Please check your internet connection and try again later.
      </p>
    {/if}
  </div>
</Modal>

<style>
  .update-content {
    padding: 0.5rem 0;
  }

  .version-info {
    text-align: center;
    margin-bottom: 1.5rem;
  }

  .version-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .new-version {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .current-version {
    margin: 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .update-message p {
    margin: 0 0 1rem 0;
    color: var(--cds-text-01);
  }

  /* Patch update banner */
  .patch-banner {
    background: linear-gradient(135deg, var(--cds-layer-01) 0%, var(--cds-layer-02) 100%);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .patch-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
    font-weight: 600;
  }

  .patch-header :global(svg) {
    color: var(--cds-support-warning);
  }

  .patch-description {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .size-comparison {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 6px;
  }

  .size-item {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .size-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .size-value {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .size-value.crossed {
    text-decoration: line-through;
    opacity: 0.5;
  }

  .patch-size .size-value {
    color: var(--cds-support-success);
  }

  .size-divider {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .components-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .component-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .component-item :global(svg) {
    color: var(--cds-support-success);
  }

  .component-name {
    flex: 1;
  }

  .component-size {
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .release-notes {
    background: var(--cds-layer-01);
    padding: 1rem;
    border-radius: 4px;
    margin-top: 1rem;
  }

  .release-notes h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .notes-content {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .download-progress {
    margin: 1rem 0;
  }

  .current-component {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .current-component :global(svg) {
    color: var(--cds-support-warning);
  }

  .progress-details {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .speed {
    font-weight: 500;
  }

  .time-remaining {
    opacity: 0.8;
  }

  .patch-success {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    margin: 1rem 0;
    padding: 1rem;
    background: var(--cds-layer-01);
    border-radius: 6px;
    color: var(--cds-support-success);
  }

  .patch-success p {
    margin: 0;
    color: var(--cds-text-01);
  }

  .restart-note,
  .error-note {
    margin: 1rem 0 0 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  :global(.bx--inline-notification) {
    margin: 1rem 0;
  }

  :global(.bx--progress-bar) {
    margin-bottom: 0;
  }
</style>
