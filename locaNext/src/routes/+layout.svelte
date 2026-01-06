<script>
  import "carbon-components-svelte/css/g100.css";
  import "../app.css";
  import {
    Header,
    SkipToContent,
    Content,
    Theme
  } from "carbon-components-svelte";
  import { Apps, UserAvatar, Settings, TaskComplete, Folder, DataBase } from "carbon-icons-svelte";
  // UI-001: Theme toggle removed (dark mode only) - Light, Moon icons no longer needed
  import { preferences } from "$lib/stores/preferences.js";
  import { onMount } from "svelte";
  import { currentApp, currentView, isAuthenticated, user } from "$lib/stores/app.js";
  import { currentPage, goToFiles, goToTM } from "$lib/stores/navigation.js";
  import { get } from 'svelte/store';
  import { api } from "$lib/api/client.js";
  import Login from "$lib/components/Login.svelte";
  import Launcher from "$lib/components/Launcher.svelte";
  import ChangePassword from "$lib/components/ChangePassword.svelte";
  import AboutModal from "$lib/components/AboutModal.svelte";
  import PreferencesModal from "$lib/components/PreferencesModal.svelte";
  import UpdateModal from "$lib/components/UpdateModal.svelte";
  import GlobalStatusBar from "$lib/components/GlobalStatusBar.svelte";
  import GlobalToast from "$lib/components/GlobalToast.svelte";
  import UserProfileModal from "$lib/components/UserProfileModal.svelte";
  import { logger } from "$lib/utils/logger.js";
  import { remoteLogger } from "$lib/utils/remote-logger.js";
  import { websocket } from "$lib/api/websocket.js";
  import SyncStatusPanel from "$lib/components/sync/SyncStatusPanel.svelte";
  import { initSync, cleanupSync } from "$lib/stores/sync.js";
  import { showLauncher, resetLauncher } from "$lib/stores/launcher.js";

  // Svelte 5: SvelteKit layout props
  let { data, children } = $props();

  // Svelte 5: State
  let isAppsMenuOpen = $state(false);
  let isSettingsMenuOpen = $state(false);  // Unified user/settings dropdown
  let isUserProfileOpen = $state(false); // UI-038
  let showChangePassword = $state(false);
  let showAbout = $state(false);
  let showPreferences = $state(false);
  let checkingAuth = $state(true);

  // Available apps
  // Apps menu - LDM removed since Files/TM tabs are always visible
  const apps = [
    { id: 'xlstransfer', name: 'XLSTransfer', description: 'Excel translation tools' },
    { id: 'quicksearch', name: 'QuickSearch', description: 'Dictionary search tool' },
    { id: 'krsimilar', name: 'KR Similar', description: 'Korean semantic similarity' }
  ];

  function selectApp(appId) {
    logger.userAction("App selected from menu", { app_id: appId });
    currentApp.set(appId);
    currentView.set('app');
    isAppsMenuOpen = false;
    isSettingsMenuOpen = false;
  }


  // Phase 10: LDM page navigation (clean tabs, always accessible from anywhere)
  function navigateToFiles() {
    logger.userAction("Navigate to Files page");
    // Always ensure we're in LDM app view
    currentApp.set('ldm');
    currentView.set('app');
    goToFiles();
  }

  function navigateToTM() {
    logger.userAction("Navigate to TM page");
    // Always ensure we're in LDM app view
    currentApp.set('ldm');
    currentView.set('app');
    goToTM();
  }

  function showTasks() {
    logger.userAction("Tasks view selected");
    currentView.set('tasks');
  }

  function openChangePassword() {
    logger.userAction("Change password modal opened");
    showChangePassword = true;
    isSettingsMenuOpen = false;
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

  // Close dropdown when clicking outside
  function handleGlobalClick(event) {
    // Don't close if clicking on a dropdown button or menu
    if (event.target.closest('.compact-dropdown')) {
      return;
    }
    isSettingsMenuOpen = false;
    isAppsMenuOpen = false;
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
    // P9: Reset launcher to show it again
    resetLauncher();
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

  // Svelte 5: Track if sync has been initialized (prevent double init)
  let syncInitialized = false;

  // Svelte 5: Effect - Connect websocket AND init sync when authenticated
  $effect(() => {
    if ($isAuthenticated) {
      // Connect WebSocket
      if (!websocket.isConnected()) {
        logger.info("Connecting WebSocket after authentication");
        websocket.connect();
      }
      // Initialize sync system (only once)
      if (!syncInitialized) {
        syncInitialized = true;
        logger.info("Initializing sync system after authentication");
        initSync();
      }
    } else {
      // User logged out - cleanup sync
      if (syncInitialized) {
        syncInitialized = false;
        cleanupSync();
      }
    }
  });

  onMount(() => {
    // Initialize global error monitoring
    remoteLogger.init();

    // P3: Sync system now initializes in $effect after authentication (not here)

    logger.component("Layout", "mounted");
    checkAuth();

    // UI-100: Clean up #main-content hash from URL (accessibility artifact)
    // SkipToContent adds #main-content for screen readers, but we hide it from URL
    const cleanupHash = () => {
      if (window.location.hash === '#main-content') {
        history.replaceState(null, '', window.location.pathname + window.location.search);
      }
    };
    cleanupHash(); // Clean on mount if already present
    window.addEventListener('hashchange', cleanupHash);

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
  {:else if $showLauncher}
    <!-- P9: Show launcher as first screen (handles updates + offline/online choice) -->
    <Launcher />
  {:else if !$isAuthenticated}
    <!-- Fallback login screen (rarely hit since Launcher handles login) -->
    <Login />
  {:else}
    <!-- Show main app if authenticated -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="app-wrapper" onclick={handleGlobalClick}>
    <!-- Header - LocaNext title (non-clickable, just branding) -->
    <Header
      company="LocaNext"
      platformName=""
      persistentHamburgerMenu={false}
    >
      <div slot="skip-to-content">
        <SkipToContent />
      </div>

      <!-- LDM Navigation - Always visible, works from anywhere -->
      <div class="ldm-nav-tabs">
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && ($currentPage === 'files' || $currentPage === 'grid')}
          onclick={navigateToFiles}
        >
          <Folder size={16} />
          <span>Files</span>
        </button>
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && ($currentPage === 'tm' || $currentPage === 'tm-entries')}
          onclick={navigateToTM}
        >
          <DataBase size={16} />
          <span>TM</span>
        </button>
      </div>

      <!-- Apps Menu - Clean compact dropdown -->
      <div class="compact-dropdown">
        <button class="compact-dropdown-btn" onclick={() => { isAppsMenuOpen = !isAppsMenuOpen; isSettingsMenuOpen = false; }}>
          <Apps size={20} />
          <span>Apps</span>
        </button>
        {#if isAppsMenuOpen}
          <div class="compact-dropdown-menu apps-menu">
            {#each apps as app}
              <button class="compact-dropdown-item" onclick={() => selectApp(app.id)}>
                <span class="item-title">{app.name}</span>
                <span class="item-desc">{app.description}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Tasks Button (styled like other nav items with icon) -->
      <button class="tasks-button" onclick={showTasks}>
        <TaskComplete size={20} />
        <span>Tasks</span>
      </button>

      <!-- P3: Sync Status Indicator -->
      <SyncStatusPanel />

      <!-- Settings Menu - Cogwheel with user info + settings inside -->
      <div class="compact-dropdown">
        <button class="compact-dropdown-btn" onclick={() => { isSettingsMenuOpen = !isSettingsMenuOpen; isAppsMenuOpen = false; }}>
          <Settings size={20} />
          <span>Settings</span>
        </button>
        {#if isSettingsMenuOpen}
          <div class="compact-dropdown-menu">
            <!-- User Section -->
            <button class="compact-dropdown-item user-item" onclick={() => { isUserProfileOpen = true; isSettingsMenuOpen = false; }}>
              <UserAvatar size={16} />
              <div class="user-info">
                <span class="item-title">{$user?.full_name || $user?.username || 'User'}</span>
                <span class="item-desc">{$user?.role || 'User'}</span>
              </div>
            </button>
            <div class="compact-dropdown-divider"></div>
            <!-- Settings Section -->
            <button class="compact-dropdown-item" onclick={openPreferences}>
              Preferences
            </button>
            <button class="compact-dropdown-item" onclick={openAbout}>
              About LocaNext
            </button>
            <div class="compact-dropdown-divider"></div>
            <!-- Account Section -->
            <button class="compact-dropdown-item" onclick={openChangePassword}>
              Change Password
            </button>
            <button class="compact-dropdown-item logout" onclick={handleLogout}>
              Logout
            </button>
          </div>
        {/if}
      </div>
    </Header>

    <!-- Change Password Modal -->
    <ChangePassword bind:open={showChangePassword} />

    <!-- About Modal -->
    <AboutModal bind:open={showAbout} />

    <!-- Preferences Modal -->
    <PreferencesModal bind:open={showPreferences} />

    <!-- UI-038: User Profile Modal -->
    <UserProfileModal bind:open={isUserProfileOpen} />

    <!-- Update Modal (auto-opens when update available) -->
    <UpdateModal />

    <Content>
      {@render children()}
    </Content>

    <!-- Global Status Bar (P18.5.5) - Shows active operations across all apps -->
    <GlobalStatusBar />

    <!-- Global Toast Notifications (BUG-016) - Shows operation start/complete/fail -->
    <GlobalToast />
    </div>
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

  /* Header title - non-clickable branding */
  :global(.bx--header__name) {
    cursor: default !important;
  }

  /* Compact Dropdown - Clean, minimal dropdowns */
  .compact-dropdown {
    position: relative;
    display: flex;
    align-items: center;
  }

  .compact-dropdown-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .compact-dropdown-btn:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .compact-dropdown-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .user-name {
    font-size: 0.875rem;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .compact-dropdown-menu {
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    min-width: 200px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    z-index: 9100;
    overflow: hidden;
  }


  .compact-dropdown-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s ease;
  }

  .compact-dropdown-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .compact-dropdown-item.logout {
    color: var(--cds-support-error);
  }

  .compact-dropdown-item.logout:hover {
    background: rgba(218, 30, 40, 0.1);
  }

  .compact-dropdown-item .item-title {
    font-weight: 600;
  }

  .compact-dropdown-item .item-desc {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-top: 0.125rem;
  }

  .compact-dropdown-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  /* User item with avatar */
  .compact-dropdown-item.user-item {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    background: var(--cds-layer-02);
  }

  .compact-dropdown-item.user-item .user-info {
    display: flex;
    flex-direction: column;
  }


  /* Phase 10: LDM Navigation - Clean segmented tabs */
  .ldm-nav-tabs {
    display: flex;
    align-items: center;
    margin-left: 1rem;
    background: var(--cds-layer-01);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
    overflow: hidden;
  }

  .ldm-nav-tab {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease;
    position: relative;
  }

  .ldm-nav-tab:first-child {
    border-right: 1px solid var(--cds-border-subtle-01);
  }

  .ldm-nav-tab:hover:not(.active) {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .ldm-nav-tab.active {
    background: var(--cds-interactive);
    color: var(--cds-text-on-color);
  }

  .ldm-nav-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
    z-index: 1;
  }
</style>
