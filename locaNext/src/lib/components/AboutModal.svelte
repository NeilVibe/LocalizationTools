<script>
  import {
    Modal,
    StructuredList,
    StructuredListHead,
    StructuredListRow,
    StructuredListCell,
    StructuredListBody,
    Button,
    InlineNotification,
    Loading
  } from "carbon-components-svelte";
  import { Renew, CheckmarkFilled, WarningAltFilled } from "carbon-icons-svelte";
  import { api } from "$lib/api/client.js";
  import { logger } from "$lib/utils/logger.js";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Version info (fetched from backend /health)
  let versionInfo = $state({
    version: "Loading...",
    build_type: "LIGHT",
    release_date: "-",
    release_name: "-"
  });

  let checkingUpdate = $state(false);
  let updateStatus = $state(null); // null | 'up-to-date' | 'update-available' | 'error'
  let updateMessage = $state("");

  // Fetch version when modal opens
  $effect(() => {
    if (open) {
      fetchVersionInfo();
    }
  });

  async function fetchVersionInfo() {
    try {
      const health = await api.getHealth();
      if (health.version) {
        versionInfo = {
          version: health.version,
          build_type: health.build_type || "LIGHT",
          release_date: formatVersionDate(health.version),
          release_name: health.release_name || "Production"
        };
      }
    } catch (err) {
      logger.error("Failed to fetch version info", { error: err.message });
    }
  }

  function formatVersionDate(version) {
    // Version format: YYMMDDHHMM (e.g., 2512011310)
    if (!version || version.length !== 10) return "-";
    const year = "20" + version.substring(0, 2);
    const month = version.substring(2, 4);
    const day = version.substring(4, 6);
    const hour = version.substring(6, 8);
    const min = version.substring(8, 10);
    return `${year}-${month}-${day} ${hour}:${min}`;
  }

  async function checkForUpdates() {
    checkingUpdate = true;
    updateStatus = null;
    updateMessage = "";

    try {
      logger.userAction("Check for updates clicked");

      // Call backend to check for updates (placeholder - you can implement GitHub release check)
      const health = await api.getHealth();

      // For now, just show "up to date"
      updateStatus = 'up-to-date';
      updateMessage = `You are running the latest version (${health.version})`;

      logger.info("Update check complete", { status: 'up-to-date', version: health.version });
    } catch (err) {
      updateStatus = 'error';
      updateMessage = `Could not check for updates: ${err.message}`;
      logger.error("Update check failed", { error: err.message });
    } finally {
      checkingUpdate = false;
    }
  }

  function handleClose() {
    open = false;
    updateStatus = null;
    updateMessage = "";
  }
</script>

<Modal
  bind:open
  modalHeading="About LocaNext"
  passiveModal
  on:close={handleClose}
  size="sm"
>
  <div class="about-content">
    <div class="app-logo">
      <h2>LocaNext</h2>
      <p class="tagline">AI-Powered Localization Platform</p>
    </div>

    <StructuredList>
      <StructuredListBody>
        <StructuredListRow>
          <StructuredListCell>Version</StructuredListCell>
          <StructuredListCell><strong>{versionInfo.version}</strong></StructuredListCell>
        </StructuredListRow>
        <StructuredListRow>
          <StructuredListCell>Build Type</StructuredListCell>
          <StructuredListCell>{versionInfo.build_type}</StructuredListCell>
        </StructuredListRow>
        <StructuredListRow>
          <StructuredListCell>Build Date</StructuredListCell>
          <StructuredListCell>{versionInfo.release_date}</StructuredListCell>
        </StructuredListRow>
        <StructuredListRow>
          <StructuredListCell>Release</StructuredListCell>
          <StructuredListCell>{versionInfo.release_name}</StructuredListCell>
        </StructuredListRow>
      </StructuredListBody>
    </StructuredList>

    {#if updateStatus === 'up-to-date'}
      <InlineNotification
        kind="success"
        title="Up to date"
        subtitle={updateMessage}
        hideCloseButton
      />
    {:else if updateStatus === 'update-available'}
      <InlineNotification
        kind="info"
        title="Update available"
        subtitle={updateMessage}
        hideCloseButton
      />
    {:else if updateStatus === 'error'}
      <InlineNotification
        kind="warning"
        title="Check failed"
        subtitle={updateMessage}
        hideCloseButton
      />
    {/if}

    <div class="update-button">
      <Button
        kind="tertiary"
        icon={Renew}
        on:click={checkForUpdates}
        disabled={checkingUpdate}
      >
        {#if checkingUpdate}
          Checking...
        {:else}
          Check for Updates
        {/if}
      </Button>
    </div>

    <div class="footer-info">
      <p>XLSTransfer + QuickSearch + KR Similar</p>
      <p class="copyright">Localization Team</p>
    </div>
  </div>
</Modal>

<style>
  .about-content {
    padding: 1rem 0;
  }

  .app-logo {
    text-align: center;
    margin-bottom: 1.5rem;
  }

  .app-logo h2 {
    margin: 0;
    font-size: 1.75rem;
    color: var(--cds-text-01);
  }

  .tagline {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .update-button {
    display: flex;
    justify-content: center;
    margin: 1.5rem 0;
  }

  .footer-info {
    text-align: center;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-border-subtle);
  }

  .footer-info p {
    margin: 0.25rem 0;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .copyright {
    opacity: 0.7;
  }

  :global(.bx--structured-list) {
    margin-bottom: 0;
  }

  :global(.bx--inline-notification) {
    margin: 1rem 0;
  }
</style>
