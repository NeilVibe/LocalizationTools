<script>
  import {
    ToastNotification,
    InlineLoading
  } from "carbon-components-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import FileExplorer from "$lib/components/ldm/FileExplorer.svelte";
  import DataGrid from "$lib/components/ldm/DataGrid.svelte";

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // State
  let healthStatus = null;
  let loading = true;
  let error = null;

  // Selection state
  let projects = [];
  let selectedProjectId = null;
  let selectedFileId = null;
  let selectedFileName = "";

  // Component refs
  let fileExplorer;
  let dataGrid;

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  /**
   * Check LDM API health
   */
  async function checkHealth() {
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
      return true;
    } catch (err) {
      error = err.message;
      logger.error("LDM health check failed", { error: err.message });
      return false;
    }
  }

  /**
   * Handle file selection from explorer
   */
  function handleFileSelect(event) {
    const { fileId, file } = event.detail;
    selectedFileId = fileId;
    selectedFileName = file.name;
    logger.userAction("File selected", { fileId, name: file.name });
  }

  /**
   * Handle project selection
   */
  function handleProjectSelect(event) {
    const { projectId } = event.detail;
    selectedProjectId = projectId;
    selectedFileId = null;
    selectedFileName = "";
    logger.userAction("Project selected", { projectId });
  }

  onMount(async () => {
    logger.component("LDM", "mounted");
    loading = true;

    const healthy = await checkHealth();
    if (healthy && fileExplorer) {
      await fileExplorer.loadProjects();
    }

    loading = false;
  });
</script>

<div class="ldm-app">
  {#if error}
    <div class="error-banner">
      <ToastNotification
        kind="error"
        title="Connection Error"
        subtitle={error}
        caption="Check if the server is running"
        lowContrast
        hideCloseButton
      />
    </div>
  {:else if loading}
    <div class="loading-state">
      <InlineLoading description="Connecting to LDM..." />
    </div>
  {:else}
    <div class="ldm-layout">
      <!-- File Explorer Sidebar -->
      <FileExplorer
        bind:this={fileExplorer}
        bind:projects
        bind:selectedProjectId
        bind:selectedFileId
        on:fileSelect={handleFileSelect}
        on:projectSelect={handleProjectSelect}
      />

      <!-- Data Grid Main Area -->
      <DataGrid
        bind:this={dataGrid}
        fileId={selectedFileId}
        fileName={selectedFileName}
      />
    </div>
  {/if}
</div>

<style>
  .ldm-app {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .error-banner {
    padding: 1rem;
  }

  .loading-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
  }

  .ldm-layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
</style>
