<script>
  /**
   * AICapabilityBadges - Visual status badges for AI engine availability.
   *
   * Phase 45: Shows green/red/yellow dots for each AI engine.
   * Uses Svelte 5 Runes only ($state, $derived).
   */
  import {
    aiCapabilities,
    refreshCapabilities,
  } from "$lib/stores/aiCapabilityStore.svelte.ts";

  // Engine display configuration
  const engines = [
    { key: "embeddings", label: "Model2Vec Embeddings", icon: "cube" },
    { key: "semantic_search", label: "FAISS Semantic Search", icon: "search" },
    { key: "ai_summary", label: "Ollama AI Summary", icon: "chat" },
    { key: "tts", label: "Qwen TTS Voice", icon: "volume" },
    { key: "image_gen", label: "Image Generation", icon: "image" },
  ];

  let refreshing = $state(false);

  // Derived counts
  let availableCount = $derived(
    engines.filter((e) => aiCapabilities[e.key] === "available").length,
  );
  let totalCount = $derived(engines.length);

  async function handleRefresh() {
    refreshing = true;
    await refreshCapabilities();
    refreshing = false;
  }

  function getStatusColor(status) {
    switch (status) {
      case "available":
        return "var(--cds-support-02, #42be65)";
      case "unavailable":
        return "var(--cds-support-01, #fa4d56)";
      case "checking":
        return "var(--cds-support-03, #f1c21b)";
      default:
        return "var(--cds-text-03, #6f6f6f)";
    }
  }

  function getStatusLabel(status) {
    switch (status) {
      case "available":
        return "Available";
      case "unavailable":
        return "Unavailable";
      case "checking":
        return "Checking...";
      default:
        return "Unknown";
    }
  }
</script>

<div class="ai-capabilities-card">
  <div class="card-header">
    <h4>AI Engine Status</h4>
    <div class="header-right">
      <span class="engine-count">{availableCount}/{totalCount} active</span>
      <button
        class="refresh-btn"
        onclick={handleRefresh}
        disabled={refreshing}
        title="Refresh AI engine status"
      >
        <svg
          class="refresh-icon"
          class:spinning={refreshing}
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path
            d="M13.9 2.1A7 7 0 0 0 2 8h1.5a5.5 5.5 0 0 1 9.6-3.6L11 6.5h4V2.5l-1.1 1.1zM2.1 13.9A7 7 0 0 0 14 8h-1.5a5.5 5.5 0 0 1-9.6 3.6L5 9.5H1v4l1.1-1.1z"
          />
        </svg>
        {refreshing ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  </div>

  {#if aiCapabilities.light_mode}
    <div class="light-mode-badge">
      <span class="dot" style="background-color: var(--cds-support-04, #4589ff);"
      ></span>
      <span class="badge-text">Light Build Mode</span>
      <span class="badge-hint">Model2Vec only, no Qwen/torch</span>
    </div>
  {/if}

  <div class="engine-list">
    {#each engines as engine (engine.key)}
      {@const status = aiCapabilities[engine.key]}
      <div class="engine-row">
        <span class="dot" style="background-color: {getStatusColor(status)};"></span>
        <span class="engine-label">{engine.label}</span>
        <span class="engine-status" style="color: {getStatusColor(status)};">
          {getStatusLabel(status)}
        </span>
      </div>
    {/each}
  </div>

  {#if aiCapabilities.last_check > 0}
    <div class="last-check">
      Last checked: {new Date(aiCapabilities.last_check * 1000).toLocaleTimeString()}
    </div>
  {/if}
</div>

<style>
  .ai-capabilities-card {
    background: var(--cds-ui-01, #262626);
    border: 1px solid var(--cds-ui-03, #393939);
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .card-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .engine-count {
    font-size: 0.75rem;
    color: var(--cds-text-02, #c6c6c6);
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    background: transparent;
    border: 1px solid var(--cds-ui-04, #525252);
    color: var(--cds-text-02, #c6c6c6);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .refresh-btn:hover:not(:disabled) {
    background: var(--cds-ui-03, #393939);
    color: var(--cds-text-01, #f4f4f4);
  }

  .refresh-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .refresh-icon {
    flex-shrink: 0;
  }

  .spinning {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .light-mode-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    background: color-mix(in srgb, var(--cds-support-04, #4589ff) 15%, transparent);
    border-radius: 4px;
    margin-bottom: 0.75rem;
  }

  .badge-text {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--cds-support-04, #4589ff);
  }

  .badge-hint {
    font-size: 0.75rem;
    color: var(--cds-text-03, #6f6f6f);
    margin-left: auto;
  }

  .engine-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .engine-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .engine-label {
    font-size: 0.8125rem;
    color: var(--cds-text-01, #f4f4f4);
    flex: 1;
  }

  .engine-status {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: capitalize;
  }

  .last-check {
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--cds-ui-03, #393939);
    font-size: 0.6875rem;
    color: var(--cds-text-03, #6f6f6f);
  }
</style>
