<script>
  import { Modal } from "carbon-components-svelte";
  import { api } from "$lib/api/client.js";
  import { logger } from "$lib/utils/logger.js";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Version info (fetched from backend /health or Electron API)
  let version = $state("Loading...");
  let buildDate = $state("-");
  let buildType = $state("");

  // Fetch version when modal opens
  $effect(() => {
    if (open) {
      fetchVersionInfo();
    }
  });

  async function fetchVersionInfo() {
    try {
      // Try Electron API first (most accurate for desktop app)
      if (window.electronAPI?.getVersion) {
        const electronVersion = await window.electronAPI.getVersion();
        if (electronVersion) {
          version = electronVersion;
          buildDate = formatVersionDate(electronVersion);
          return;
        }
      }

      // Fallback to backend /health
      const health = await api.getHealth();
      if (health.version) {
        version = health.version;
        buildDate = formatVersionDate(health.version);
        buildType = health.build_type || "";
      }
    } catch (err) {
      logger.error("Failed to fetch version info", { error: err.message });
      version = "Unknown";
    }
  }

  function formatVersionDate(v) {
    // Version format: YYMMDDHHMM (e.g., 2512011310) or YY.DDD.HHMM (e.g., 26.329.0300)
    if (!v) return "-";
    // Handle dot-separated format: YY.DDD.HHMM
    if (v.includes('.')) {
      const parts = v.split('.');
      if (parts.length === 3) {
        const year = "20" + parts[0];
        const dayOfYear = parseInt(parts[1], 10);
        const time = parts[2];
        const d = new Date(parseInt(year), 0);
        d.setDate(dayOfYear);
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hour = time.substring(0, 2);
        const min = time.substring(2, 4);
        return `${year}-${month}-${day} ${hour}:${min}`;
      }
    }
    // Handle compact format: YYMMDDHHMM
    if (v.length === 10 && !isNaN(v)) {
      const year = "20" + v.substring(0, 2);
      const month = v.substring(2, 4);
      const day = v.substring(4, 6);
      const hour = v.substring(6, 8);
      const min = v.substring(8, 10);
      return `${year}-${month}-${day} ${hour}:${min}`;
    }
    return "-";
  }

  function handleClose() {
    open = false;
  }
</script>

<Modal
  bind:open
  modalHeading="About LocaNext"
  passiveModal
  onclose={handleClose}
  size="sm"
>
  <div class="about-content">
    <div class="app-logo">
      <h2>LocaNext</h2>
      <p class="tagline">Desktop Localization Platform</p>
    </div>

    <div class="version-info">
      <div class="version-row">
        <span class="version-label">Version</span>
        <span class="version-value">{version}</span>
      </div>
      {#if buildDate !== "-"}
        <div class="version-row">
          <span class="version-label">Build Date</span>
          <span class="version-value">{buildDate}</span>
        </div>
      {/if}
      {#if buildType}
        <div class="version-row">
          <span class="version-label">Build</span>
          <span class="version-value">{buildType}</span>
        </div>
      {/if}
    </div>

    <div class="footer-info">
      <p class="creator">Created by Neil Schmitt</p>
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

  .version-info {
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1.5rem;
  }

  .version-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.375rem 0;
    font-size: 0.875rem;
  }

  .version-row + .version-row {
    border-top: 1px solid var(--cds-border-subtle-01, #393939);
  }

  .version-label {
    color: var(--cds-text-03, #6f6f6f);
  }

  .version-value {
    color: var(--cds-text-01, #f4f4f4);
    font-weight: 600;
  }

  .footer-info {
    text-align: center;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-border-subtle);
  }

  .creator {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    font-weight: 500;
  }
</style>
