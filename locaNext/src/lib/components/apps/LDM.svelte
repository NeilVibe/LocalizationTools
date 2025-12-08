<script>
  import {
    Tile,
    Button,
    InlineLoading,
    ToastNotification
  } from "carbon-components-svelte";
  import { Database, Folder, DocumentBlank, CheckmarkFilled, WarningFilled } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // State
  let healthStatus = null;
  let loading = true;
  let error = null;

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  }

  /**
   * Check LDM API health
   */
  async function checkHealth() {
    loading = true;
    error = null;

    try {
      logger.apiCall("/api/ldm/health", "GET");
      const response = await fetch(`${API_BASE}/api/ldm/health`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      healthStatus = await response.json();
      logger.success("LDM health check passed", healthStatus);
    } catch (err) {
      error = err.message;
      logger.error("LDM health check failed", { error: err.message });
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    logger.component("LDM", "mounted");
    checkHealth();
  });
</script>

<div class="ldm-container">
  <div class="ldm-header">
    <h1>
      <Database size={32} />
      LanguageData Manager
    </h1>
    <p class="subtitle">Real-time collaborative CAT tool for localization projects</p>
  </div>

  {#if error}
    <ToastNotification
      kind="error"
      title="Connection Error"
      subtitle={error}
      caption="Check if the server is running"
      lowContrast
    />
  {/if}

  <div class="status-section">
    <Tile>
      <h3>System Status</h3>
      {#if loading}
        <InlineLoading description="Checking API status..." />
      {:else if healthStatus}
        <div class="status-grid">
          <div class="status-item">
            <CheckmarkFilled size={24} style="color: var(--cds-support-02)" />
            <span>Module: {healthStatus.module}</span>
          </div>
          <div class="status-item">
            <CheckmarkFilled size={24} style="color: var(--cds-support-02)" />
            <span>Version: {healthStatus.version}</span>
          </div>
          <div class="status-item">
            {#if healthStatus.status === 'ok'}
              <CheckmarkFilled size={24} style="color: var(--cds-support-02)" />
            {:else}
              <WarningFilled size={24} style="color: var(--cds-support-03)" />
            {/if}
            <span>Status: {healthStatus.status}</span>
          </div>
        </div>

        <h4 style="margin-top: 1rem;">Features</h4>
        <div class="features-grid">
          {#each Object.entries(healthStatus.features || {}) as [feature, enabled]}
            <div class="feature-item">
              {#if enabled}
                <CheckmarkFilled size={16} style="color: var(--cds-support-02)" />
              {:else}
                <span style="color: var(--cds-text-05)">-</span>
              {/if}
              <span class:disabled={!enabled}>{feature}</span>
            </div>
          {/each}
        </div>
      {:else}
        <p>Unable to check status</p>
      {/if}
    </Tile>
  </div>

  <div class="coming-soon">
    <Tile>
      <h3>Coming in Phase 2</h3>
      <div class="feature-list">
        <div class="feature">
          <Folder size={24} />
          <div>
            <strong>File Explorer</strong>
            <p>Create projects, organize folders, upload TXT/XML files</p>
          </div>
        </div>
        <div class="feature">
          <DocumentBlank size={24} />
          <div>
            <strong>Data Grid</strong>
            <p>View and edit translation rows with virtual scrolling (500K+ rows)</p>
          </div>
        </div>
        <div class="feature">
          <Database size={24} />
          <div>
            <strong>Real-time Sync</strong>
            <p>Collaborate with team members, see changes instantly</p>
          </div>
        </div>
      </div>
    </Tile>
  </div>

  <div class="refresh-section">
    <Button kind="ghost" on:click={checkHealth} disabled={loading}>
      Refresh Status
    </Button>
  </div>
</div>

<style>
  .ldm-container {
    padding: 2rem;
    max-width: 800px;
    margin: 0 auto;
  }

  .ldm-header {
    margin-bottom: 2rem;
    text-align: center;
  }

  .ldm-header h1 {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    color: var(--cds-text-02);
    font-size: 1rem;
  }

  .status-section {
    margin-bottom: 1.5rem;
  }

  .status-grid {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .feature-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.875rem;
  }

  .feature-item .disabled {
    color: var(--cds-text-05);
  }

  .coming-soon {
    margin-bottom: 1.5rem;
  }

  .coming-soon h3 {
    margin-bottom: 1rem;
    color: var(--cds-text-02);
  }

  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .feature {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
  }

  .feature strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .feature p {
    margin: 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .refresh-section {
    text-align: center;
  }
</style>
