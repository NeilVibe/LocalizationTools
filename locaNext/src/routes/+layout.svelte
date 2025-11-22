<script>
  import "carbon-components-svelte/css/g100.css";
  import "../app.css";
  import {
    Header,
    HeaderNav,
    HeaderNavItem,
    HeaderAction,
    HeaderPanelLinks,
    HeaderPanelDivider,
    HeaderPanelLink,
    SkipToContent,
    Content,
    Theme
  } from "carbon-components-svelte";
  import { Apps } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { currentApp, currentView, isAuthenticated, user } from "$lib/stores/app.js";
  import { api } from "$lib/api/client.js";
  import Login from "$lib/components/Login.svelte";
  import { logger } from "$lib/utils/logger.js";
  import { remoteLogger } from "$lib/utils/remote-logger.js";
  import { websocket } from "$lib/api/websocket.js";

  // Accept SvelteKit layout props to avoid warnings
  export let data = {};
  export let params = {};

  let isAppsMenuOpen = false;
  let checkingAuth = true;

  // Available apps
  const apps = [
    { id: 'xlstransfer', name: 'XLSTransfer', description: 'Excel translation tools' },
    { id: 'quicksearch', name: 'QuickSearch', description: 'Dictionary search tool' },
    { id: 'wordcount', name: 'WordCountMaster', description: 'Word count tracking and comparison' }
  ];

  function selectApp(appId) {
    logger.userAction("App selected from menu", { app_id: appId });
    currentApp.set(appId);
    currentView.set('app');
    isAppsMenuOpen = false;
  }

  function showTasks() {
    logger.userAction("Tasks view selected");
    currentView.set('tasks');
  }

  /**
   * Logout user
   */
  function handleLogout() {
    logger.userAction("User logout", { username: $user?.username || "unknown" });
    api.clearAuth();
    isAuthenticated.set(false);
    user.set(null);
    websocket.disconnect();
    logger.info("User logged out successfully");
  }

  /**
   * Check if user is already authenticated
   */
  async function checkAuth() {
    const startTime = performance.now();
    checkingAuth = true;

    logger.info("Checking authentication status");

    // Check if token exists
    const token = api.getToken();
    if (!token) {
      logger.info("No authentication token found - showing login");
      checkingAuth = false;
      return;
    }

    logger.info("Token found - verifying with server");

    // Verify token is still valid by fetching current user
    try {
      logger.apiCall("/api/users/me", "GET");
      const currentUser = await api.getCurrentUser();

      const elapsed = performance.now() - startTime;

      user.set(currentUser);
      isAuthenticated.set(true);

      logger.success("Authentication verified", {
        username: currentUser.username,
        role: currentUser.role,
        elapsed_ms: elapsed.toFixed(2)
      });
    } catch (error) {
      const elapsed = performance.now() - startTime;

      logger.error("Authentication check failed", {
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });

      api.clearAuth();
    } finally {
      checkingAuth = false;
    }
  }

  // Connect websocket when authenticated
  $: if ($isAuthenticated && !websocket.isConnected()) {
    logger.info("Connecting WebSocket after authentication");
    websocket.connect();
  }

  onMount(() => {
    // Initialize global error monitoring
    remoteLogger.init();

    logger.component("Layout", "mounted");
    checkAuth();
  });
</script>

<Theme theme="g100">
  {#if checkingAuth}
    <!-- Loading state while checking authentication -->
    <div class="auth-loading">
      <p>Loading...</p>
    </div>
  {:else if !$isAuthenticated}
    <!-- Show login screen if not authenticated -->
    <Login />
  {:else}
    <!-- Show main app if authenticated -->
    <Header
      company="LocaNext"
      platformName=""
      persistentHamburgerMenu={false}
    >
      <div slot="skip-to-content">
        <SkipToContent />
      </div>

      <!-- Apps Dropdown -->
      <HeaderAction
        bind:isOpen={isAppsMenuOpen}
        icon={Apps}
        closeIcon={Apps}
        text="Apps"
      >
        <HeaderPanelLinks>
          {#each apps as app}
            <HeaderPanelLink on:click={() => selectApp(app.id)}>
              {app.name}
              <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;">
                {app.description}
              </div>
            </HeaderPanelLink>
            <HeaderPanelDivider />
          {/each}
        </HeaderPanelLinks>
      </HeaderAction>

      <!-- Tasks Button -->
      <HeaderNavItem
        on:click={showTasks}
        text="Tasks"
      />

      <!-- Logout Button -->
      <HeaderNavItem
        on:click={handleLogout}
        text="Logout"
      />
    </Header>

    <Content>
      <slot />
    </Content>
  {/if}
</Theme>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  :global(.bx--content) {
    background: var(--cds-background);
    height: calc(100vh - 48px);
    overflow-y: auto;
    padding: 0;
  }

  .auth-loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background: var(--cds-background);
    color: var(--cds-text-02);
  }

  .auth-loading p {
    font-size: 1.125rem;
  }
</style>
