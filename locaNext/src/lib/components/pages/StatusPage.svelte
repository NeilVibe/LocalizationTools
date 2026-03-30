<script>
  import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  let statusData = $state(null);
  let loading = $state(true);
  let errorMsg = $state(null);
  let lastUpdated = $state(null);

  async function fetchStatus() {
    try {
      loading = true;
      const base = getApiBase();
      const res = await fetch(`${base}/api/ldm/system-status`, {
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      statusData = await res.json();
      lastUpdated = new Date();
      errorMsg = null;
    } catch (e) {
      logger.error("[StatusPage] Failed to fetch system status:", e);
      errorMsg = e.message;
    } finally {
      loading = false;
    }
  }

  // Fetch on mount, auto-refresh every 30s
  let refreshInterval;
  $effect(() => {
    fetchStatus();
    refreshInterval = setInterval(fetchStatus, 30000);
    return () => clearInterval(refreshInterval);
  });

  /**
   * Map a raw status string to a severity level.
   */
  function getSeverity(status) {
    if (!status) return "error";
    const s = status.toLowerCase();
    if (["loaded", "installed", "available", "connected", "built", "ok"].includes(s)) return "success";
    if (["found_not_loaded", "not_built", "fallback", "unknown"].includes(s)) return "warning";
    return "error";
  }

  /**
   * Build the card list from statusData.
   */
  let cards = $derived(buildCards(statusData));

  function buildCards(data) {
    if (!data) return [];
    const list = [];

    // Server
    if (data.server) {
      list.push({
        id: "server",
        title: "Server",
        status: "ok",
        severity: "success",
        details: [
          { label: "Database Mode", value: data.server.mode },
          { label: "Platform", value: data.server.platform },
          { label: "Python", value: data.server.python_version },
        ]
      });
    }

    // Model2Vec
    if (data.model2vec) {
      const m = data.model2vec;
      const details = [{ label: "Status", value: m.status }];
      if (m.dimension) details.push({ label: "Dimension", value: String(m.dimension) });
      if (m.name) details.push({ label: "Model", value: m.name });
      if (m.path) details.push({ label: "Path", value: m.path });
      if (m.hint) details.push({ label: "Hint", value: m.hint });
      if (m.error) details.push({ label: "Error", value: m.error });
      list.push({
        id: "model2vec",
        title: "Model2Vec Embeddings",
        status: m.status,
        severity: getSeverity(m.status),
        details
      });
    }

    // MegaIndex
    if (data.mega_index) {
      const mi = data.mega_index;
      const details = [
        { label: "Status", value: mi.status },
      ];
      // Per-type entry counts if available
      if (mi.counts) {
        const c = mi.counts;
        if (c.knowledge) details.push({ label: "Knowledge", value: c.knowledge.toLocaleString() });
        if (c.characters) details.push({ label: "Characters", value: c.characters.toLocaleString() });
        if (c.items) details.push({ label: "Items", value: c.items.toLocaleString() });
        if (c.regions) details.push({ label: "Regions", value: c.regions.toLocaleString() });
        if (c.factions) details.push({ label: "Factions", value: c.factions.toLocaleString() });
        if (c.skills) details.push({ label: "Skills", value: c.skills.toLocaleString() });
        if (c.gimmicks) details.push({ label: "Gimmicks", value: c.gimmicks.toLocaleString() });
        if (c.dds) details.push({ label: "DDS Textures", value: c.dds.toLocaleString() });
        if (c.wem) details.push({ label: "WEM Audio", value: c.wem.toLocaleString() });
        if (c.strorigins) details.push({ label: "StrOrigins", value: c.strorigins.toLocaleString() });
      } else if (mi.entries != null) {
        details.push({ label: "Total Entries", value: String(mi.entries?.toLocaleString?.() ?? mi.entries ?? 0) });
      }
      if (mi.build_time) details.push({ label: "Build Time", value: `${mi.build_time}s` });
      if (mi.error) details.push({ label: "Error", value: mi.error });
      list.push({
        id: "mega_index",
        title: "MegaIndex",
        status: mi.status,
        severity: getSeverity(mi.status),
        details
      });
    }

    // Qwen AI
    if (data.qwen) {
      list.push({
        id: "qwen",
        title: "Qwen AI Engine",
        status: data.qwen.status,
        severity: getSeverity(data.qwen.status),
        details: [{ label: "Status", value: data.qwen.status }]
      });
    }

    // ahocorasick
    if (data.ahocorasick) {
      list.push({
        id: "ahocorasick",
        title: "Aho-Corasick",
        status: data.ahocorasick.status,
        severity: getSeverity(data.ahocorasick.status),
        details: [{ label: "Status", value: data.ahocorasick.status }]
      });
    }

    // WebSocket
    if (data.websocket) {
      list.push({
        id: "websocket",
        title: "WebSocket",
        status: data.websocket.status,
        severity: getSeverity(data.websocket.status),
        details: [{ label: "Status", value: data.websocket.status }]
      });
    }

    // Database
    if (data.database) {
      const db = data.database;
      const dbDetails = [
        { label: "Mode", value: db.mode || "unknown" },
      ];
      if (db.table_count) dbDetails.push({ label: "Tables", value: String(db.table_count) });
      if (db.total_rows) dbDetails.push({ label: "Total Rows", value: db.total_rows.toLocaleString() });
      list.push({
        id: "database",
        title: "Database",
        status: db.mode || "unknown",
        severity: getSeverity(db.mode === "postgresql" ? "connected" : "fallback"),
        details: dbDetails
      });
    }

    // Version
    if (data.version) {
      list.push({
        id: "version",
        title: "Version",
        status: "ok",
        severity: "success",
        details: [
          { label: "App Version", value: data.version },
          { label: "Build", value: data.build || "unknown" },
        ]
      });
    }

    return list;
  }

  function formatTime(date) {
    if (!date) return "--";
    return date.toLocaleTimeString();
  }
</script>

<div class="status-page">
  <div class="status-header">
    <h2>System Status</h2>
    <div class="header-meta">
      {#if lastUpdated}
        <span class="last-updated">Last updated: {formatTime(lastUpdated)}</span>
      {/if}
      <button class="refresh-btn" onclick={fetchStatus} disabled={loading}>
        {loading ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  </div>

  {#if errorMsg && !statusData}
    <div class="error-banner">
      <span class="dot dot--error"></span>
      <span>Failed to load system status: {errorMsg}</span>
    </div>
  {/if}

  {#if loading && !statusData}
    <div class="loading-state">Loading system status...</div>
  {:else if cards.length > 0}
    <div class="cards-grid">
      {#each cards as card (card.id)}
        <div class="status-card">
          <div class="card-header">
            <span class="dot dot--{card.severity}"></span>
            <h3>{card.title}</h3>
            <span class="badge badge--{card.severity}">{card.status}</span>
          </div>
          <div class="card-body">
            {#each card.details as detail (detail.label)}
              <div class="detail-row">
                <span class="detail-label">{detail.label}</span>
                <span class="detail-value">{detail.value}</span>
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <div class="status-footer">
    <span>Auto-refresh: every 30 seconds</span>
  </div>
</div>

<style>
  .status-page {
    padding: 1.5rem 2rem;
    height: 100%;
    overflow-y: auto;
    color: var(--cds-text-01, #f4f4f4);
  }

  .status-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
  }

  .status-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    color: var(--cds-text-01, #f4f4f4);
  }

  .header-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .last-updated {
    font-size: 0.75rem;
    color: var(--cds-text-03, #6f6f6f);
  }

  .refresh-btn {
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    color: var(--cds-text-01, #f4f4f4);
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s;
  }

  .refresh-btn:hover:not(:disabled) {
    background: var(--cds-layer-hover-01, #353535);
  }

  .refresh-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-banner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(218, 30, 40, 0.1);
    border-left: 3px solid var(--cds-support-error, #da1e28);
    margin-bottom: 1rem;
    font-size: 0.8125rem;
  }

  .loading-state {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: var(--cds-text-03, #6f6f6f);
    font-size: 0.875rem;
  }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
  }

  .status-card {
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    padding: 0;
    transition: border-color 0.15s;
  }

  .status-card:hover {
    border-color: var(--cds-border-strong-01, #6f6f6f);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01, #393939);
  }

  .card-header h3 {
    font-size: 0.875rem;
    font-weight: 600;
    margin: 0;
    flex: 1;
    color: var(--cds-text-01, #f4f4f4);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dot--success {
    background-color: var(--cds-support-success, #24a148);
  }

  .dot--warning {
    background-color: var(--cds-support-warning, #f1c21b);
  }

  .dot--error {
    background-color: var(--cds-support-error, #da1e28);
  }

  .badge {
    font-size: 0.6875rem;
    padding: 0.125rem 0.5rem;
    border-radius: 10px;
    text-transform: uppercase;
    font-weight: 500;
    letter-spacing: 0.02em;
  }

  .badge--success {
    background: rgba(36, 161, 72, 0.15);
    color: var(--cds-support-success, #24a148);
  }

  .badge--warning {
    background: rgba(241, 194, 27, 0.15);
    color: var(--cds-support-warning, #f1c21b);
  }

  .badge--error {
    background: rgba(218, 30, 40, 0.15);
    color: var(--cds-support-error, #da1e28);
  }

  .card-body {
    padding: 0.75rem 1rem;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.25rem 0;
    font-size: 0.8125rem;
  }

  .detail-row + .detail-row {
    border-top: 1px solid var(--cds-border-subtle-01, #393939);
  }

  .detail-label {
    color: var(--cds-text-03, #6f6f6f);
    font-weight: 400;
  }

  .detail-value {
    color: var(--cds-text-01, #f4f4f4);
    font-weight: 500;
    text-align: right;
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .status-footer {
    margin-top: 1.5rem;
    font-size: 0.6875rem;
    color: var(--cds-text-03, #6f6f6f);
    text-align: center;
  }
</style>
