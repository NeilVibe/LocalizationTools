<script>
  import '../app.css';
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { websocket } from '$lib/api/websocket.js';
  import { Dashboard, UserMultiple, Activity, ChartLine, Trophy, Search, Logout } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';

  const navItems = [
    { href: '/', label: 'Dashboard', icon: Dashboard },
    { href: '/users', label: 'Users', icon: UserMultiple },
    { href: '/activity', label: 'Live Activity', icon: Activity },
    { href: '/stats', label: 'Statistics', icon: ChartLine },
    { href: '/rankings', label: 'Rankings', icon: Trophy },
    { href: '/logs', label: 'Logs', icon: Search }
  ];

  let wsConnected = false;
  let unsubscribeConnected;
  let unsubscribeDisconnected;

  onMount(() => {
    logger.component("AdminLayout", "mounted");

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
    <slot />
  </main>
</div>
