<script>
  import '../app.css';
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { websocket } from '$lib/api/websocket.js';
  import adminAPI from '$lib/api/client.js';
  import { Dashboard, UserMultiple, Activity, ChartLine, Trophy, Search, Logout, WatsonHealthStackedScrolling_1 as Telemetry, DataBase, Meter } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';

  // Svelte 5: Get children slot
  let { children } = $props();

  const navItems = [
    { href: '/', label: 'Overview', icon: Dashboard },
    { href: '/users', label: 'Users', icon: UserMultiple },
    { href: '/stats', label: 'Stats & Rankings', icon: ChartLine },
    { href: '/telemetry', label: 'Telemetry', icon: Telemetry },
    { href: '/logs', label: 'Activity Logs', icon: Activity },
    { href: '/database', label: 'Database', icon: DataBase },
    { href: '/server', label: 'Server', icon: Meter }
  ];

  // Svelte 5: Reactive state
  let wsConnected = $state(false);
  let isAuthenticated = $state(false);

  // Non-reactive cleanup functions
  let unsubscribeConnected;
  let unsubscribeDisconnected;

  // Auto-login for internal admin dashboard
  // Uses IP-lock admin: localhost gets automatic admin rights from health endpoint
  async function ensureAuthenticated() {
    // Check if we already have a valid token
    const existingToken = localStorage.getItem('admin_token');
    if (existingToken) {
      try {
        await adminAPI.getCurrentUser();
        isAuthenticated = true;
        logger.success("Using existing admin token");
        return;
      } catch (e) {
        // Token invalid, try health endpoint
        logger.warning("Existing token invalid, re-authenticating");
      }
    }

    // IP-lock admin: get token from dedicated endpoints
    const baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8888/api/v2').replace(/\/api\/v2$/, '');

    // Step 1: Check health for auto_token (SQLite mode) or origin admin flag
    try {
      const healthResp = await fetch(`${baseUrl}/health`);
      const health = await healthResp.json();

      // SQLite mode: use auto_token directly
      if (health.auto_token) {
        adminAPI.saveToken(health.auto_token);
        isAuthenticated = true;
        logger.success("Auto-authenticated via SQLite auto_token");
        return;
      }

      // LAN server mode: request admin token via POST (IP-lock)
      if (health.is_origin_admin) {
        const tokenResp = await fetch(`${baseUrl}/api/origin-admin-token`, { method: 'POST' });
        if (tokenResp.ok) {
          const tokenData = await tokenResp.json();
          if (tokenData.admin_token) {
            adminAPI.saveToken(tokenData.admin_token);
            isAuthenticated = true;
            logger.success("IP-lock admin: authenticated via origin-admin-token");
            return;
          }
        }
      }
    } catch (e) {
      logger.warning("Auto-authentication failed", e.message);
    }

    // No auto-auth available — dashboard requires manual login or setup
    logger.error("Authentication failed — run LAN server setup first or check PostgreSQL");
  }

  onMount(() => {
    logger.component("AdminLayout", "mounted");

    // Ensure we're authenticated for admin operations
    ensureAuthenticated();

    // Monitor WebSocket connection status
    logger.info("Setting up WebSocket connection monitoring");

    unsubscribeConnected = websocket.on('connected', () => {
      wsConnected = true;
      logger.success("WebSocket connected - Live updates active");
    });

    unsubscribeDisconnected = websocket.on('disconnected', () => {
      wsConnected = false;
      logger.warning("WebSocket disconnected - Attempting to reconnect");
    });

    // Check initial connection state
    wsConnected = websocket.isConnected();
    logger.info("WebSocket initial state", { connected: wsConnected });
  });

  onDestroy(() => {
    logger.component("AdminLayout", "destroyed");
    logger.info("Cleaning up WebSocket subscriptions");

    if (unsubscribeConnected) unsubscribeConnected();
    if (unsubscribeDisconnected) unsubscribeDisconnected();
  });
</script>

<div class="admin-layout">
  <aside class="admin-sidebar">
    <div style="padding: 1.5rem; border-bottom: 1px solid var(--cds-border-subtle-01);">
      <h2 style="font-size: 1.25rem; font-weight: 600; color: var(--cds-text-01);">LocaNext Admin</h2>
      <p style="font-size: 0.875rem; color: var(--cds-text-03); margin-top: 0.25rem;">Dashboard</p>
    </div>

    <nav style="padding: 1rem 0; flex: 1;">
      {#each navItems as item}
        <a
          href={item.href}
          class="nav-link"
          class:active={$page.url.pathname === item.href}
        >
          <svelte:component this={item.icon} size={20} />
          {item.label}
        </a>
      {/each}
    </nav>

    <div style="padding: 1rem; border-top: 1px solid var(--cds-border-subtle-01);">
      <div style="padding: 0.75rem 1rem; margin-bottom: 0.5rem; font-size: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
        <span style="display: inline-block; width: 8px; height: 8px; background: {wsConnected ? '#24a148' : '#8d8d8d'}; border-radius: 50%; {wsConnected ? 'animation: pulse 2s infinite;' : ''}"></span>
        <span style="color: var(--cds-text-03);">
          {wsConnected ? 'Live Updates Active' : 'Connecting...'}
        </span>
      </div>
      <button class="nav-link w-full" style="border: none; cursor: pointer;">
        <Logout size={20} />
        Logout
      </button>
    </div>
  </aside>

  <main class="admin-main">
    {#if isAuthenticated}
      {@render children()}
    {:else}
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; gap: 1rem; color: #c6c6c6;">
        <h2>Authentication Required</h2>
        <p>Could not authenticate with the server. Ensure PostgreSQL is running and LAN server setup is complete.</p>
        <button onclick={ensureAuthenticated} style="padding: 0.5rem 1.5rem; background: #0f62fe; color: white; border: none; border-radius: 4px; cursor: pointer;">
          Retry
        </button>
      </div>
    {/if}
  </main>
</div>
