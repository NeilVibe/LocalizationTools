<script>
  import {
    Modal,
    Button,
    ProgressBar,
    InlineNotification,
    Tag
  } from "carbon-components-svelte";
  import { Renew, Checkmark, Close, Download, Restart } from "carbon-icons-svelte";
  import { onMount, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);

  // Svelte 5: Modal state
  let open = $state(false);
  let updateState = $state('idle'); // 'idle' | 'checking' | 'available' | 'downloading' | 'downloaded' | 'error'

  // Svelte 5: Update info
  let updateInfo = $state({
    version: '',
    releaseNotes: '',
    releaseDate: ''
  });

  // Svelte 5: Download progress
  let progress = $state({
    percent: 0,
    transferred: 0,
    total: 0,
    bytesPerSecond: 0
  });

  // Svelte 5: Error state
  let errorMessage = $state('');

  // Svelte 5: Current version (from backend health)
  let currentVersion = $state('');

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
      // Main process may have already found an update before this component mounted
      try {
        const state = await window.electronUpdate.getUpdateState();
        logger.info('UpdateModal: Got update state on mount', state);

        if (state.hasUpdate) {
          // Update was already found before we mounted - show modal immediately
          updateInfo = {
            version: state.updateInfo?.version || '',
            releaseNotes: state.updateInfo?.releaseNotes || '',
            releaseDate: state.updateInfo?.releaseDate || ''
          };
          updateState = state.state; // 'available' or 'downloaded'
          open = true;
          logger.info('UpdateModal: Found pending update, showing modal', { version: state.updateInfo?.version });
        }
      } catch (err) {
        logger.warning('UpdateModal: Could not get update state', { error: err.message });
      }

      // Register event listeners for future updates
      window.electronUpdate.onUpdateAvailable(handleUpdateAvailable);
      window.electronUpdate.onUpdateProgress(handleUpdateProgress);
      window.electronUpdate.onUpdateDownloaded(handleUpdateDownloaded);
      window.electronUpdate.onUpdateError(handleUpdateError);
      logger.info('UpdateModal: Registered update event listeners');
    }
  });

  onDestroy(() => {
    // Clean up all update event listeners
    if (typeof window !== 'undefined' && window.electronUpdate) {
      window.electronUpdate.removeListeners();
      logger.info('UpdateModal: Cleaned up update event listeners');
    }
  });

  function handleUpdateAvailable(info) {
    logger.info('UpdateModal: Update available', info);
    updateInfo = {
      version: info.version || '',
      releaseNotes: info.releaseNotes || '',
      releaseDate: info.releaseDate || ''
    };
    updateState = 'available';
    open = true;
  }

  function handleUpdateProgress(progressObj) {
    logger.info('UpdateModal: Download progress', { percent: progressObj.percent?.toFixed(1) });
    progress = {
      percent: progressObj.percent || 0,
      transferred: progressObj.transferred || 0,
      total: progressObj.total || 0,
      bytesPerSecond: progressObj.bytesPerSecond || 0
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

  function handleDownload() {
    logger.userAction('User clicked download update');
    if (window.electronUpdate) {
      window.electronUpdate.downloadUpdate();
    }
    updateState = 'downloading';
  }

  function handleRestartNow() {
    logger.userAction('User clicked restart now');
    if (window.electronUpdate) {
      window.electronUpdate.quitAndInstall();
    }
  }

  function handleLater() {
    logger.userAction('User clicked update later');
    open = false;
  }

  function handleClose() {
    if (updateState === 'downloading') {
      // Don't allow closing during download
      return;
    }
    open = false;
  }

  // Format version date (YYMMDDHHMM -> readable)
  function formatVersionDate(version) {
    if (!version || version.length !== 10) return '';
    const year = '20' + version.substring(0, 2);
    const month = version.substring(2, 4);
    const day = version.substring(4, 6);
    return `${year}-${month}-${day}`;
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
        <p>A new version of LocaNext is ready to download.</p>
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
        <ProgressBar
          value={progress.percent}
          labelText="Downloading update..."
          helperText="{formatBytes(progress.transferred)} / {formatBytes(progress.total)}"
        />
        <div class="progress-details">
          <span class="speed">{formatSpeed(progress.bytesPerSecond)}</span>
          <span class="time-remaining">{formatTimeRemaining()}</span>
        </div>
      </div>
    {/if}

    <!-- State: Downloaded -->
    {#if updateState === 'downloaded'}
      <InlineNotification
        kind="success"
        title="Ready to install"
        subtitle="The update has been downloaded. Restart to apply."
        hideCloseButton
      />
      <p class="restart-note">
        The application will close and restart automatically to install the update.
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
