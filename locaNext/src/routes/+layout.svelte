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
  import { Apps, UserAvatar, Settings, TaskComplete, Light, Moon } from "carbon-icons-svelte";
  import { preferences, theme } from "$lib/stores/preferences.js";
  import { onMount } from "svelte";
  import { currentApp, currentView, isAuthenticated, user } from "$lib/stores/app.js";
  import { get } from 'svelte/store';
  import { api } from "$lib/api/client.js";
  import Login from "$lib/components/Login.svelte";
  import ChangePassword from "$lib/components/ChangePassword.svelte";
  import AboutModal from "$lib/components/AboutModal.svelte";
  import PreferencesModal from "$lib/components/PreferencesModal.svelte";
  import UpdateModal from "$lib/components/UpdateModal.svelte";
  import GlobalStatusBar from "$lib/components/GlobalStatusBar.svelte";
  import { logger } from "$lib/utils/logger.js";
  import { remoteLogger } from "$lib/utils/remote-logger.js";
  import { websocket } from "$lib/api/websocket.js";

  // Svelte 5: SvelteKit layout props
  let { data, children } = $props();

  // Svelte 5: State
  let isAppsMenuOpen = $state(false);
  let isSettingsMenuOpen = $state(false);
  let isUserMenuOpen = $state(false);
  let showChangePassword = $state(false);
  let showAbout = $state(false);
  let showPreferences = $state(false);
  let checkingAuth = $state(true);

  // Available apps
  const apps = [
    { id: 'xlstransfer', name: 'XLSTransfer', description: 'Excel translation tools' },
    { id: 'quicksearch', name: 'QuickSearch', description: 'Dictionary search tool' },
    { id: 'krsimilar', name: 'KR Similar', description: 'Korean semantic similarity' },
    { id: 'ldm', name: 'LDM', description: 'LanguageData Manager - CAT tool' }
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

  function openChangePassword() {
    logger.userAction("Change password modal opened");
    showChangePassword = true;
    isUserMenuOpen = false;
  }

  function openAbout() {
    logger.userAction("About modal opened");
    showAbout = true;
    isSettingsMenuOpen = false;
  }

  function openPreferences() {
    logger.userAction("Preferences modal opened");
    showPreferences = true;
    isSettingsMenuOpen = false;
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

  // Svelte 5: Effect - Connect websocket when authenticated
  $effect(() => {
    if ($isAuthenticated && !websocket.isConnected()) {
      logger.info("Connecting WebSocket after authentication");
      websocket.connect();
    }
  });

  onMount(() => {
    // Initialize global error monitoring
    remoteLogger.init();

    logger.component("Layout", "mounted");
    checkAuth();

    // TEST MODE: Expose navigation helper for CDP testing
    // This allows automated tests to navigate between apps without DOM clicks
    window.navTest = {
      /**
       * Navigate to a specific app
       * @param {string} appId - One of: xlstransfer, quicksearch, krsimilar, ldm
       */
      goToApp: (appId) => {
        const validApps = ['xlstransfer', 'quicksearch', 'krsimilar', 'ldm'];
        if (!validApps.includes(appId)) {
          return { success: false, error: `Invalid app: ${appId}. Valid: ${validApps.join(', ')}` };
        }
        currentApp.set(appId);
        currentView.set('app');
        logger.info("Test navigation", { app: appId });
        return { success: true, app: appId };
      },
      /**
       * Navigate to tasks view
       */
      goToTasks: () => {
        currentView.set('tasks');
        return { success: true, view: 'tasks' };
      },
      /**
       * Get current navigation state (uses svelte/store get)
       */
      getState: () => {
        return {
          app: get(currentApp),
          view: get(currentView),
          authenticated: get(isAuthenticated)
        };
      }
    };
    logger.info("Test navigation helper exposed on window.navTest");
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

      <!-- Tasks Button (styled like other nav items with icon) -->
      <button class="tasks-button" onclick={showTasks}>
        <TaskComplete size={20} />
        <span>Tasks</span>
      </button>

      <!-- Theme Toggle Button -->
      <button
        class="theme-toggle-button"
        onclick={() => preferences.toggleTheme()}
        title={$theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      >
        {#if $theme === 'dark'}
          <Light size={20} />
        {:else}
          <Moon size={20} />
        {/if}
      </button>

      <!-- Settings Dropdown -->
      <HeaderAction
        bind:isOpen={isSettingsMenuOpen}
        icon={Settings}
        closeIcon={Settings}
        text="Settings"
      >
        <HeaderPanelLinks>
          <HeaderPanelLink on:click={openAbout}>
            About LocaNext
          </HeaderPanelLink>
          <HeaderPanelDivider />
          <HeaderPanelLink on:click={openPreferences}>
            Preferences
          </HeaderPanelLink>
        </HeaderPanelLinks>
      </HeaderAction>

      <!-- User Menu -->
      <HeaderAction
        bind:isOpen={isUserMenuOpen}
        icon={UserAvatar}
        closeIcon={UserAvatar}
        text={$user?.username || "User"}
      >
        <HeaderPanelLinks>
          <HeaderPanelLink>
            <div style="font-weight: 600;">{$user?.full_name || $user?.username || 'User'}</div>
            <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;">
              {$user?.email || 'No email'}
            </div>
          </HeaderPanelLink>
          <HeaderPanelDivider />
          <HeaderPanelLink on:click={openChangePassword}>
            Change Password
          </HeaderPanelLink>
          <HeaderPanelDivider />
          <HeaderPanelLink on:click={handleLogout}>
            Logout
          </HeaderPanelLink>
        </HeaderPanelLinks>
      </HeaderAction>
    </Header>

    <!-- Change Password Modal -->
    <ChangePassword bind:open={showChangePassword} />

    <!-- About Modal -->
    <AboutModal bind:open={showAbout} />

    <!-- Preferences Modal -->
    <PreferencesModal bind:open={showPreferences} />

    <!-- Update Modal (auto-opens when update available) -->
    <UpdateModal />

    <Content>
      {@render children()}
    </Content>

    <!-- Global Status Bar (P18.5.5) - Shows active operations across all apps -->
    <GlobalStatusBar />
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

  /* Tasks button styling to match Carbon header actions */
  .tasks-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.875rem 1rem;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    cursor: pointer;
    height: 48px;
    transition: background 0.15s ease;
  }

  .tasks-button:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .tasks-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  /* Theme toggle button */
  .theme-toggle-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.875rem;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    height: 48px;
    width: 48px;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .theme-toggle-button:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .theme-toggle-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
