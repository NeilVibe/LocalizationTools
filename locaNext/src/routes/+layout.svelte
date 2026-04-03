<script>
  import "carbon-components-svelte/css/g100.css";
  import "../app.css";
  import {
    Header,
    SkipToContent,
    Content,
    Theme
  } from "carbon-components-svelte";
  import { Apps, UserAvatar, Settings, TaskComplete, Folder, DataBase, GameConsole, Book, Earth, Catalog, UserMultiple, Music, Map, Merge, Dashboard, ChevronDown, Flash, Notebook, Idea } from "carbon-icons-svelte";
  // UI-001: Theme toggle removed (dark mode only) - Light, Moon icons no longer needed
  import { preferences } from "$lib/stores/preferences.js";
  import { onMount } from "svelte";
  import { currentApp, currentView, isAuthenticated, user } from "$lib/stores/app.js";
  import { currentPage, goToFiles, goToTM, goToGameDev, goToWorldMap, goToItemCodex, goToCharacterCodex, goToAudioCodex, goToRegionCodex, goToQuestCodex, goToSkillCodex, goToGimmickCodex, goToKnowledgeCodex, goToStatus, selectedProject } from "$lib/stores/navigation.js";
  import { get } from 'svelte/store';
  import { api } from "$lib/api/client.js";
  import Login from "$lib/components/Login.svelte";
  import Launcher from "$lib/components/Launcher.svelte";
  import ChangePassword from "$lib/components/ChangePassword.svelte";
  import AboutModal from "$lib/components/AboutModal.svelte";
  import PreferencesModal from "$lib/components/PreferencesModal.svelte";
  import ServerSettingsModal from "$lib/components/ServerSettingsModal.svelte";
  import BranchDriveSettingsModal from "$lib/components/BranchDriveSettingsModal.svelte";
  import MergeModal from "$lib/components/ldm/MergeModal.svelte";
  import UpdateModal from "$lib/components/UpdateModal.svelte";
  import GlobalStatusBar from "$lib/components/GlobalStatusBar.svelte";
  import ToastContainer from "$lib/components/common/ToastContainer.svelte";
  import UserProfileModal from "$lib/components/UserProfileModal.svelte";
  import { logger } from "$lib/utils/logger.js";
  import { addToast, removeToast } from "$lib/stores/toastStore.js";
  import { remoteLogger } from "$lib/utils/remote-logger.js";
  import { websocket } from "$lib/api/websocket.js";
  import SyncStatusPanel from "$lib/components/sync/SyncStatusPanel.svelte";
  import { initSync, cleanupSync } from "$lib/stores/sync.js";
  import { showLauncher, resetLauncher } from "$lib/stores/launcher.js";
  import CommandPalette from "$lib/components/common/CommandPalette.svelte";
  import PageTransition from "$lib/components/common/PageTransition.svelte";

  // Svelte 5: SvelteKit layout props
  let { data, children } = $props();

  // Svelte 5: State
  let isAppsMenuOpen = $state(false);
  let isSettingsMenuOpen = $state(false);  // Unified user/settings dropdown
  let isUserProfileOpen = $state(false); // UI-038
  let showChangePassword = $state(false);
  let showAbout = $state(false);
  let showPreferences = $state(false);
  let showServerSettings = $state(false);
  let showBranchDrive = $state(false);
  // Phase 59: Merge modal state
  let showMergeModal = $state(false);
  let mergeMultiLanguage = $state(false);
  let mergeFolderPath = $state('');
  let checkingAuth = $state(true);
  let isCodexMenuOpen = $state(false);

  // MegaIndex auto-build with toast notifications
  async function triggerMegaIndexBuild() {
    try {
      const { getApiBase, getAuthHeaders } = await import('$lib/utils/api.js');
      const API = getApiBase();

      // Check if already built
      const statusRes = await fetch(`${API}/api/ldm/mega/status`, { headers: getAuthHeaders() });
      if (!statusRes.ok) {
        logger.warning(`MegaIndex status check failed: ${statusRes.status}`);
        return;
      }
      const status = await statusRes.json();
      if (status.built) {
        logger.info(`MegaIndex already built: ${status.total_entries || 0} entries`);
        return;
      }

      // Not built — trigger build with toast
      const buildingToast = addToast({ message: 'Building game data index (textures, audio, entities)...', kind: 'info', title: 'MegaIndex', duration: 0 });

      const buildRes = await fetch(`${API}/api/ldm/mega/build`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger_reason: 'Initial login' })
      });

      // Dismiss the "building" toast
      if (buildingToast > 0) removeToast(buildingToast);

      if (buildRes.ok) {
        const result = await buildRes.json();
        const count = result.total_entities || result.total_entries || result.entity_count || 0;
        const time = result.build_time ? `${result.build_time.toFixed(1)}s` : '';
        if (count > 0) {
          addToast({ message: `${count} entries indexed ${time ? `in ${time}` : ''}`, kind: 'success', title: 'MegaIndex Ready', duration: 5000 });
        } else {
          addToast({ message: 'No game data found — configure Perforce paths in Settings', kind: 'warning', title: 'MegaIndex', duration: 8000 });
        }
      } else {
        const err = await buildRes.json().catch(() => ({}));
        addToast({ message: err.detail || 'Build failed — check path settings', kind: 'warning', title: 'MegaIndex', duration: 8000 });
      }
    } catch (e) {
      logger.warning(`MegaIndex auto-build failed: ${e.message}`);
      addToast({ message: 'Index build skipped — will retry next session', kind: 'info', title: 'MegaIndex', duration: 3000 });
    }
  }

  // Model2Vec status check
  async function checkModel2VecStatus() {
    try {
      const { getApiBase, getAuthHeaders } = await import('$lib/utils/api.js');
      const API = getApiBase();
      const res = await fetch(`${API}/api/ldm/system-status`, { headers: getAuthHeaders() });
      if (res.ok) {
        const status = await res.json();
        const m2v = status.model2vec;
        if (m2v && m2v.status === 'loaded') {
          addToast({ message: `Model2Vec ready (${m2v.dimension}-dim)`, kind: 'success', title: 'AI Models', duration: 3000 });
        } else if (m2v && m2v.status === 'not_found') {
          addToast({ message: 'Place Model2Vec/ folder next to LocaNext.exe for fuzzy TM matching', kind: 'warning', title: 'Model2Vec Missing', duration: 10000 });
        }
      }
    } catch (e) {
      // System status not available yet, skip
    }
  }

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

  // Phase 18: Game Dev navigation
  function navigateToGameDev() {
    logger.userAction("Navigate to Game Dev page");
    currentApp.set('ldm');
    currentView.set('app');
    goToGameDev();
  }

  // Phase 20: World Map navigation
  function navigateToWorldMap() {
    logger.userAction("Navigate to World Map page");
    currentApp.set('ldm');
    currentView.set('app');
    goToWorldMap();
  }

  // Phase 46: Item Codex navigation
  function navigateToItemCodex() {
    logger.userAction("Navigate to Item Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToItemCodex();
  }

  // Phase 47: Character Codex navigation
  function navigateToCharacterCodex() {
    logger.userAction("Navigate to Character Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToCharacterCodex();
  }

  // Phase 48: Audio Codex navigation
  function navigateToAudioCodex() {
    logger.userAction("Navigate to Audio Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToAudioCodex();
  }

  // Phase 49: Region Codex navigation
  function navigateToRegionCodex() {
    logger.userAction("Navigate to Region Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToRegionCodex();
  }

  // Phase 102: Quest Codex navigation
  function navigateToQuestCodex() {
    logger.userAction("Navigate to Quest Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToQuestCodex();
  }

  // Phase 102: Skill Codex navigation
  function navigateToSkillCodex() {
    logger.userAction("Navigate to Skill Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToSkillCodex();
  }

  // Phase 102: Gimmick Codex navigation
  function navigateToGimmickCodex() {
    logger.userAction("Navigate to Gimmick Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToGimmickCodex();
  }

  // Phase 102: Knowledge Codex navigation
  function navigateToKnowledgeCodex() {
    logger.userAction("Navigate to Knowledge Codex page");
    currentApp.set('ldm');
    currentView.set('app');
    goToKnowledgeCodex();
  }

  // System Status navigation
  function navigateToStatus() {
    logger.userAction("Navigate to Status page");
    currentApp.set('ldm');
    currentView.set('app');
    goToStatus();
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

  function openServerSettings() {
    logger.userAction("Server settings modal opened");
    showServerSettings = true;
    isSettingsMenuOpen = false;
  }

  function openBranchDrive() {
    logger.userAction("Branch/Drive settings opened");
    showBranchDrive = true;
    isSettingsMenuOpen = false;
  }

  // Phase 59: Open merge modal (single-project mode)
  function openMerge() {
    if (!$selectedProject) {
      logger.warning("No project selected — cannot open merge modal");
      return;
    }
    logger.userAction("Merge modal opened", { projectId: $selectedProject.id });
    mergeMultiLanguage = false;
    mergeFolderPath = '';
    showMergeModal = true;
  }

  // Phase 59: Open merge modal (multi-language folder mode, triggered by FilesPage context menu)
  function openMergeFolder(folderPath) {
    if (!$selectedProject) return;
    logger.userAction("Merge folder modal opened", { projectId: $selectedProject.id, folderPath });
    mergeMultiLanguage = true;
    mergeFolderPath = folderPath;
    showMergeModal = true;
  }

  // Close dropdown when clicking outside
  function handleGlobalClick(event) {
    // Always close codex dropdown if clicking outside it (before other checks)
    if (isCodexMenuOpen && !event.target.closest('.codex-dropdown')) {
      isCodexMenuOpen = false;
    }
    // Don't close settings/apps if clicking on a dropdown button or menu
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

        // Auto-trigger MegaIndex build if not already built
        triggerMegaIndexBuild();

        // Check Model2Vec status and notify user
        checkModel2VecStatus();
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
    // Phase 111: Frontend ALWAYS talks to localhost:8888 (own local backend).
    // The backend handles DB routing internally via the factory pattern.
    // Clear any stale remote server URL from previous Option B behavior.
    const staleRemote = localStorage.getItem('locanext_remote_server');
    if (staleRemote) {
      logger.info("Cleared stale remote server URL from localStorage (Phase 111)", { url: staleRemote });
      localStorage.removeItem('locanext_remote_server');
    }

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

    // Phase 59: Listen for merge folder events from FilesPage context menu
    function handleMergeFolderEvent(e) {
      openMergeFolder(e.detail.folderPath);
    }
    window.addEventListener('merge-folder-to-locdev', handleMergeFolderEvent);

    // Pre-login server settings (Launcher dispatches this event)
    function handleOpenServerSettings() { showServerSettings = true; }
    window.addEventListener('open-server-settings', handleOpenServerSettings);

    return () => {
      window.removeEventListener('merge-folder-to-locdev', handleMergeFolderEvent);
      window.removeEventListener('open-server-settings', handleOpenServerSettings);
    };
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
          <span>Localization Data</span>
        </button>
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && ($currentPage === 'tm' || $currentPage === 'tm-entries')}
          onclick={navigateToTM}
        >
          <DataBase size={16} />
          <span>TM</span>
        </button>
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && $currentPage === 'gamedev'}
          onclick={navigateToGameDev}
        >
          <GameConsole size={16} />
          <span>Game Data</span>
        </button>
        <!-- Phase 102: Codex dropdown (replaces 5 separate buttons) -->
        <div class="codex-dropdown">
          <button
            class="ldm-nav-tab"
            class:active={$currentApp === 'ldm' && ['codex', 'item-codex', 'character-codex', 'audio-codex', 'region-codex', 'quest-codex', 'skill-codex', 'gimmick-codex', 'knowledge-codex'].includes($currentPage)}
            onclick={() => { isCodexMenuOpen = !isCodexMenuOpen; }}
          >
            <Book size={16} />
            <span>Codex</span>
            <ChevronDown size={12} />
          </button>
          {#if isCodexMenuOpen}
            <div class="codex-dropdown-menu">
              <button class="codex-dropdown-item" class:active={$currentPage === 'item-codex'} onclick={() => { navigateToItemCodex(); isCodexMenuOpen = false; }}>
                <Catalog size={14} /> Items
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'character-codex'} onclick={() => { navigateToCharacterCodex(); isCodexMenuOpen = false; }}>
                <UserMultiple size={14} /> Characters
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'audio-codex'} onclick={() => { navigateToAudioCodex(); isCodexMenuOpen = false; }}>
                <Music size={14} /> Audio
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'region-codex'} onclick={() => { navigateToRegionCodex(); isCodexMenuOpen = false; }}>
                <Map size={14} /> Regions
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'quest-codex'} onclick={() => { navigateToQuestCodex(); isCodexMenuOpen = false; }}>
                <TaskComplete size={14} /> Quests
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'skill-codex'} onclick={() => { navigateToSkillCodex(); isCodexMenuOpen = false; }}>
                <Flash size={14} /> Skills
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'gimmick-codex'} onclick={() => { navigateToGimmickCodex(); isCodexMenuOpen = false; }}>
                <Idea size={14} /> Gimmicks
              </button>
              <button class="codex-dropdown-item" class:active={$currentPage === 'knowledge-codex'} onclick={() => { navigateToKnowledgeCodex(); isCodexMenuOpen = false; }}>
                <Notebook size={14} /> Knowledge
              </button>
            </div>
          {/if}
        </div>
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && $currentPage === 'worldmap'}
          onclick={navigateToWorldMap}
        >
          <Earth size={16} />
          <span>Map</span>
        </button>
        <button
          class="ldm-nav-tab"
          class:active={$currentApp === 'ldm' && $currentPage === 'status'}
          onclick={navigateToStatus}
        >
          <Dashboard size={16} />
          <span>Status</span>
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
            <hr class="dropdown-divider" />
            <button class="compact-dropdown-item" onclick={() => { openMerge(); isAppsMenuOpen = false; }} disabled={!$selectedProject}>
              <span class="item-title">Merge to LOCDEV</span>
              <span class="item-desc">Transfer translations to target XML</span>
            </button>
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
            <button class="compact-dropdown-item" onclick={openBranchDrive}>
              Perforce Branch &amp; Drive
            </button>
            <button class="compact-dropdown-item" onclick={openServerSettings}>
              Server Connection
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

    <!-- Phase 59: Merge Modal -->
    <MergeModal bind:open={showMergeModal} projectId={$selectedProject?.id} projectName={$selectedProject?.name || ''} multiLanguage={mergeMultiLanguage} folderPath={mergeFolderPath} />

    <!-- UI-038: User Profile Modal -->
    <UserProfileModal bind:open={isUserProfileOpen} />

    <!-- Update Modal (auto-opens when update available) -->
    <UpdateModal />

    <Content>
      <PageTransition>{@render children()}</PageTransition>
    </Content>

    <!-- Global Status Bar (P18.5.5) - Shows active operations across all apps -->
    <GlobalStatusBar />

    <!-- Phase 40: Redesigned Toast Notifications with slide-in + progress bar -->
    <ToastContainer />

    <!-- Phase 40: Global Ctrl+K Command Palette -->
    <CommandPalette />
    </div>
  {/if}

  <!-- Server Settings Modal (OUTSIDE auth gate — accessible from Launcher pre-login) -->
  <ServerSettingsModal bind:open={showServerSettings} />
  <BranchDriveSettingsModal bind:open={showBranchDrive} />
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
    background: var(--cds-layer-hover-01);
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

  .ldm-nav-tab:not(:last-child) {
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

  /* Phase 102: Codex dropdown */
  .codex-dropdown {
    position: relative;
    display: inline-flex;
  }

  .codex-dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 9000;
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 0.25rem 0;
    min-width: 160px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  .codex-dropdown-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.5rem 1rem;
    background: none;
    border: none;
    color: var(--cds-text-primary, #f4f4f4);
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
  }

  .codex-dropdown-item:hover {
    background: var(--cds-layer-hover-01, #353535);
  }

  .codex-dropdown-item.active {
    background: var(--cds-layer-selected-01, #393939);
    color: var(--cds-link-primary, #78a9ff);
  }
</style>
