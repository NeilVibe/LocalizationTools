<script>
  import {
    ToastNotification,
    InlineLoading,
    Button,
    Tag
  } from "carbon-components-svelte";
  import { DataBase, ServerProxy, Cloud, CloudOffline, Renew, CloudUpload, Column, Document } from "carbon-icons-svelte";
  import { preferences } from "$lib/stores/preferences.js";
  import { currentPage, openFile, openFileInGrid, closeGrid, openTM, openTMInGrid, closeTMGrid } from "$lib/stores/navigation.js";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  // FileExplorer removed - replaced by FilesPage (Phase 10)
  import VirtualGrid from "$lib/components/ldm/VirtualGrid.svelte";
  import TMManager from "$lib/components/ldm/TMManager.svelte";
  import TMDataGrid from "$lib/components/ldm/TMDataGrid.svelte";
  import QAMenuPanel from "$lib/components/ldm/QAMenuPanel.svelte";
  import TMQAPanel from "$lib/components/ldm/TMQAPanel.svelte";
  // Phase 10: Page components
  import FilesPage from "$lib/components/pages/FilesPage.svelte";
  import TMPage from "$lib/components/pages/TMPage.svelte";
  import GridPage from "$lib/components/pages/GridPage.svelte";
  // UI-097: PreferencesModal removed - use top nav Settings > Preferences
  import GridColumnsModal from "$lib/components/GridColumnsModal.svelte";
  import ReferenceSettingsModal from "$lib/components/ReferenceSettingsModal.svelte";
  import ServerStatus from "$lib/components/ServerStatus.svelte";

  // TM Manager state
  let showTMManager = $state(false);

  // UI-097: showPreferences removed - use top nav Settings > Preferences

  // Grid columns modal state
  let showGridColumns = $state(false);

  // Reference settings modal state
  let showReferenceSettings = $state(false);

  // Server status modal state
  let showServerStatus = $state(false);

  // P2: QA Menu panel state
  let showQAMenu = $state(false);

  // Phase 1: MemoQ-style side panel state
  let sidePanelCollapsed = $state(false);
  let sidePanelWidth = $state(300);
  let sidePanelSelectedRow = $state(null);
  let sidePanelTMMatches = $state([]);
  let sidePanelQAIssues = $state([]);
  let sidePanelTMLoading = $state(false);
  let sidePanelQALoading = $state(false);

  // API base URL - centralized in api.js
  const API_BASE = getApiBase();

  // ================================
  // TEST MODE CONFIGURATION
  // ================================
  const TEST_FILES_PATH = 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\TestFilesForLocaNext';

  const LDM_TEST_CONFIG = {
    createProject: {
      name: 'Test Project ' + Date.now()
    },
    uploadTxt: {
      file: `${TEST_FILES_PATH}\\sampleofLanguageData.txt`,
      name: 'sampleofLanguageData.txt'
    },
    uploadXml: {
      file: `${TEST_FILES_PATH}\\sample_localization.xml`,
      name: 'sample_localization.xml'
    },
    uploadSmall: {
      file: `${TEST_FILES_PATH}\\SMALLTESTFILEFORQUICKSEARCH.txt`,
      name: 'SMALLTESTFILEFORQUICKSEARCH.txt'
    },
    editRow: {
      rowIndex: 0,
      newTarget: 'TEST TRANSLATION ' + Date.now(),
      newStatus: 'translated'
    }
  };

  // Test state for CDP access (bypasses Svelte reactivity)
  const _testState = {
    isProcessing: false,
    statusMessage: '',
    lastResult: null,
    testProjectId: null,
    testFileId: null
  };

  // State (Svelte 5 runes for reactivity)
  let healthStatus = $state(null);
  let loading = $state(true);
  let error = $state(null);

  // Selection state
  let projects = $state([]);
  let selectedProjectId = $state(null);
  let selectedFileId = $state(null);
  let selectedFileName = $state("");

  // P33 Phase 3: TM selection state
  let selectedTMId = $state(null);
  let selectedTMName = $state("");
  let viewMode = $state('file'); // 'file' | 'tm' - what's displayed in VirtualGrid

  // FEAT-001: Linked TM for current project (auto-add entries on confirm)
  let linkedTM = $state(null); // {tm_id, tm_name, priority} or null

  // P33 Phase 4: Connection status
  let connectionStatus = $state({
    mode: 'unknown', // 'online' | 'offline' | 'unknown'
    canSync: false,
    dbType: 'unknown'
  });

  // Component refs (Svelte 5 requires $state for bindable refs)
  let fileExplorer = $state(null);
  let virtualGrid = $state(null);

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
   * P33 Phase 4: Fetch connection status for Online/Offline badge
   */
  async function fetchConnectionStatus() {
    try {
      const response = await fetch(`${API_BASE}/api/status`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const status = await response.json();
        connectionStatus = {
          mode: status.connection_mode,
          canSync: status.can_sync,
          dbType: status.database_type
        };
        logger.info("Connection status", connectionStatus);
      }
    } catch (err) {
      connectionStatus = {
        mode: 'offline',
        canSync: false,
        dbType: 'unknown'
      };
      logger.warn("Could not fetch connection status", { error: err.message });
    }
  }

  // P33 Phase 5: Go Online state
  let goingOnline = $state(false);
  let goOnlineMessage = $state('');

  /**
   * P33 Phase 5: Attempt to go online (reconnect to PostgreSQL)
   */
  async function handleGoOnline() {
    goingOnline = true;
    goOnlineMessage = '';

    try {
      logger.apiCall("/api/go-online", "POST");
      const response = await fetch(`${API_BASE}/api/go-online`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      const result = await response.json();
      logger.info("Go online result", result);

      if (result.success) {
        if (result.action_required === 'restart') {
          goOnlineMessage = 'PostgreSQL is available! Restart the app to go online.';
          // Optionally show a toast notification
        } else {
          goOnlineMessage = 'Already online!';
          await fetchConnectionStatus(); // Refresh status
        }
      } else {
        goOnlineMessage = result.message || 'Could not connect to PostgreSQL';
      }
    } catch (err) {
      logger.error("Go online failed", { error: err.message });
      goOnlineMessage = 'Failed to check connection';
    } finally {
      goingOnline = false;
    }
  }

  /**
   * Handle file selection from explorer
   */
  function handleFileSelect(event) {
    const { fileId, file, filesState } = event.detail;
    selectedFileId = fileId;
    selectedFileName = file.name;
    // P33: Clear TM selection when file is selected
    selectedTMId = null;
    selectedTMName = "";
    viewMode = 'file';
    // Phase 10: Update navigation store to show grid view
    // Pass filesState so we can restore folder location on back
    openFileInGrid(file, filesState);
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

  /**
   * UI-095: Handle QA run from file context menu
   * Opens QAMenuPanel with the specified file and check type
   */
  function handleRunQA(event) {
    const { fileId, type, fileName } = event.detail;
    logger.userAction("QA triggered from context menu", { fileId, type, fileName });

    // Set the file context for QAMenuPanel
    selectedFileId = fileId;
    selectedFileName = fileName;

    // Open QA panel
    showQAMenu = true;
  }

  /**
   * P33 Phase 3: Handle TM selection from explorer
   */
  function handleTMSelect(event) {
    const { tmId, tm } = event.detail;
    selectedTMId = tmId;
    selectedTMName = tm.name;
    // Clear file selection when TM is selected
    selectedFileId = null;
    selectedFileName = "";
    viewMode = 'tm';
    logger.userAction("TM selected", { tmId, name: tm.name });
  }

  /**
   * Handle click on QA issue: scroll to row, highlight, and open edit modal
   */
  async function handleOpenEditModal(event) {
    const { rowId, rowNum } = event.detail;
    // openEditModalByRowId handles scroll + highlight + open modal
    if (virtualGrid) {
      await virtualGrid.openEditModalByRowId(rowId);
      logger.userAction("Opened edit modal from QA", { rowId, rowNum });
    }
    // Close QA menu after modal opens
    showQAMenu = false;
  }

  /**
   * Phase 1: Handle row selection - load TM matches and QA issues for side panel
   */
  async function handleRowSelect(event) {
    const { row } = event.detail;
    if (!row || !row.source) {
      sidePanelSelectedRow = null;
      sidePanelTMMatches = [];
      sidePanelQAIssues = [];
      return;
    }

    sidePanelSelectedRow = row;

    // Fetch TM matches and QA issues for this row in parallel
    await Promise.all([
      loadTMMatchesForRow(row),
      loadQAIssuesForRow(row)
    ]);
  }

  /**
   * Phase 1: Load TM matches for a row
   * Uses GET /api/ldm/tm/suggest endpoint (same as VirtualGrid)
   */
  async function loadTMMatchesForRow(row) {
    if (!row?.source || !selectedFileId) return;

    sidePanelTMLoading = true;
    sidePanelTMMatches = [];

    try {
      // Build query params for TM suggest endpoint
      // TM-UI-003: Use user-selected threshold from preferences
      const params = new URLSearchParams({
        source: row.source,
        threshold: $preferences.tmThreshold.toString(),
        max_results: '5'
      });

      // Use active TM from preferences if set
      if ($preferences.activeTmId) {
        params.append('tm_id', $preferences.activeTmId.toString());
      }

      // Add file context
      params.append('file_id', selectedFileId.toString());

      // Exclude current row from results
      if (row.id) {
        params.append('exclude_row_id', row.id.toString());
      }

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        sidePanelTMMatches = data.suggestions || [];
        logger.info('TM matches loaded for side panel', {
          count: sidePanelTMMatches.length,
          tmId: $preferences.activeTmId
        });
      } else {
        logger.warning('TM suggest failed', { status: response.status });
      }
    } catch (err) {
      logger.error('Failed to load TM matches', { error: err.message });
    } finally {
      sidePanelTMLoading = false;
    }
  }

  /**
   * Phase 1: Load QA issues for a row
   */
  async function loadQAIssuesForRow(row) {
    if (!row?.id) return;

    sidePanelQALoading = true;
    sidePanelQAIssues = [];

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}/qa-results`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const results = await response.json();
        sidePanelQAIssues = results.issues || [];
        logger.info('QA issues loaded for side panel', { count: sidePanelQAIssues.length });
      }
    } catch (err) {
      logger.error('Failed to load QA issues', { error: err.message });
    } finally {
      sidePanelQALoading = false;
    }
  }

  /**
   * Phase 1: Handle apply TM from side panel
   */
  function handleApplyTMFromPanel(event) {
    const match = event.detail;
    // This will be wired up in Phase 2 for inline editing
    logger.userAction('TM apply requested from side panel', { similarity: match.similarity });
    // For now, just log - in Phase 2 this will apply to the active edit cell
  }

  /**
   * Phase 2: Handle confirm translation (Ctrl+S) - marks as reviewed and adds to TM
   * Automatically adds entry to linked TM if one is configured for the project
   */
  async function handleConfirmTranslation(event) {
    const { rowId, source, target } = event.detail;
    logger.userAction('Translation confirmed (Ctrl+S)', { rowId, source: source?.substring(0, 30), target: target?.substring(0, 30) });

    // Add to linked TM if available
    if (linkedTM && linkedTM.tm_id && source && target) {
      try {
        const formData = new FormData();
        formData.append('source_text', source);
        formData.append('target_text', target);

        const response = await fetch(`${API_BASE}/api/ldm/tm/${linkedTM.tm_id}/entries`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });

        if (response.ok) {
          const result = await response.json();
          logger.success('Entry added to TM', { tmId: linkedTM.tm_id, tmName: linkedTM.tm_name, entryCount: result.entry_count });
        } else {
          const error = await response.json();
          logger.error('Failed to add entry to TM', { error: error.detail });
        }
      } catch (err) {
        logger.error('Error adding to TM', { error: err.message });
      }
    } else if (!linkedTM) {
      logger.info('No linked TM - entry not added to TM');
    }
  }

  /**
   * Phase 2: Handle dismiss QA issues (Ctrl+D)
   * Resolves all QA issues for the row via API and updates visual state
   */
  async function handleDismissQA(event) {
    const { rowId } = event.detail;
    logger.userAction('QA issues dismissed (Ctrl+D)', { rowId });

    // Get QA issues to resolve (from side panel or fetch them)
    let issuesToResolve = [];
    if (sidePanelSelectedRow && sidePanelSelectedRow.id === rowId) {
      issuesToResolve = [...sidePanelQAIssues];
    } else {
      // Fetch QA issues for this row
      try {
        const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/qa-results`, {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const results = await response.json();
          issuesToResolve = results.issues || [];
        }
      } catch (err) {
        logger.error('Failed to fetch QA issues for dismissal', { error: err.message });
        return;
      }
    }

    if (issuesToResolve.length === 0) {
      logger.info('No QA issues to dismiss', { rowId });
      return;
    }

    // Resolve each QA issue via API
    let resolvedCount = 0;
    for (const issue of issuesToResolve) {
      try {
        const response = await fetch(`${API_BASE}/api/ldm/qa-results/${issue.id}/resolve`, {
          method: 'POST',
          headers: getAuthHeaders()
        });
        if (response.ok) {
          resolvedCount++;
        }
      } catch (err) {
        logger.error('Failed to resolve QA issue', { issueId: issue.id, error: err.message });
      }
    }

    logger.success(`Dismissed ${resolvedCount}/${issuesToResolve.length} QA issues`, { rowId });

    // Clear side panel QA issues
    if (sidePanelSelectedRow && sidePanelSelectedRow.id === rowId) {
      sidePanelQAIssues = [];
    }

    // Dispatch event to update row's visual state in VirtualGrid
    // The VirtualGrid needs to update the row's qa_flag_count to 0
    if (virtualGrid) {
      virtualGrid.updateRowQAFlag(rowId, 0);
    }
  }

  // ================================
  // TEST MODE FUNCTIONS
  // ================================

  /**
   * TEST: Create a project without UI
   */
  async function testCreateProject() {
    logger.info('TEST MODE: Creating project', LDM_TEST_CONFIG.createProject);
    _testState.isProcessing = true;
    _testState.statusMessage = 'TEST: Creating project...';

    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: LDM_TEST_CONFIG.createProject.name })
      });

      if (response.ok) {
        const project = await response.json();
        _testState.testProjectId = project.id;
        selectedProjectId = project.id;
        _testState.lastResult = project;
        _testState.statusMessage = `TEST: Project created - ID: ${project.id}`;
        logger.success('TEST MODE: Project created', { id: project.id });

        // Refresh projects list
        if (fileExplorer) {
          await fileExplorer.loadProjects();
        }
      } else {
        const err = await response.json();
        _testState.statusMessage = `TEST ERROR: ${err.detail}`;
        logger.error('TEST MODE: Create project failed', { error: err.detail });
      }
    } catch (err) {
      _testState.statusMessage = `TEST ERROR: ${err.message}`;
      logger.error('TEST MODE: Create project error', { error: err.message });
    } finally {
      _testState.isProcessing = false;
    }
  }

  /**
   * TEST: Upload a file using fetch (reads from Windows path)
   */
  async function testUploadFile(configKey = 'uploadSmall') {
    const config = LDM_TEST_CONFIG[configKey];
    if (!config) {
      _testState.statusMessage = `TEST ERROR: Unknown config key: ${configKey}`;
      return;
    }

    if (!_testState.testProjectId && !selectedProjectId) {
      _testState.statusMessage = 'TEST ERROR: Create project first!';
      return;
    }

    const projectId = _testState.testProjectId || selectedProjectId;
    logger.info('TEST MODE: Uploading file', { config, projectId });
    _testState.isProcessing = true;
    _testState.statusMessage = `TEST: Uploading ${config.name}...`;

    try {
      // Fetch file from Windows filesystem via file:// protocol won't work
      // Instead, we'll create a simple test content
      let testContent;
      if (config.name.endsWith('.xml')) {
        testContent = `<?xml version="1.0" encoding="utf-8"?>
<root>
  <LocStr StringId="TEST_001" StrOrigin="테스트 문자열 1" Str="Test String 1"/>
  <LocStr StringId="TEST_002" StrOrigin="테스트 문자열 2" Str="Test String 2"/>
  <LocStr StringId="TEST_003" StrOrigin="테스트 문자열 3" Str=""/>
  <LocStr StringId="TEST_004" StrOrigin="테스트 문자열 4" Str="Test String 4"/>
  <LocStr StringId="TEST_005" StrOrigin="테스트 문자열 5" Str=""/>
</root>`;
      } else {
        // TXT format: tab-separated, cols 0-4=StringID, 5=Source, 6=Target
        testContent = `TEST_001\t\t\t\t\t테스트 문자열 1\tTest String 1
TEST_002\t\t\t\t\t테스트 문자열 2\tTest String 2
TEST_003\t\t\t\t\t테스트 문자열 3\t
TEST_004\t\t\t\t\t테스트 문자열 4\tTest String 4
TEST_005\t\t\t\t\t테스트 문자열 5\t
TEST_006\t\t\t\t\t테스트 문자열 6\tTest String 6
TEST_007\t\t\t\t\t테스트 문자열 7\t
TEST_008\t\t\t\t\t테스트 문자열 8\tTest String 8
TEST_009\t\t\t\t\t테스트 문자열 9\t
TEST_010\t\t\t\t\t테스트 문자열 10\tTest String 10`;
      }

      const blob = new Blob([testContent], { type: 'text/plain' });
      const file = new File([blob], config.name);

      const formData = new FormData();
      formData.append('project_id', projectId);
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/ldm/files/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        _testState.testFileId = result.id;
        selectedFileId = result.id;
        selectedFileName = result.name;
        _testState.lastResult = result;
        _testState.statusMessage = `TEST: File uploaded - ${result.row_count} rows`;
        logger.success('TEST MODE: File uploaded', { id: result.id, rows: result.row_count });

        // Refresh tree
        if (fileExplorer) {
          await fileExplorer.loadProjects();
        }
      } else {
        const err = await response.json();
        _testState.statusMessage = `TEST ERROR: ${err.detail}`;
        logger.error('TEST MODE: Upload failed', { error: err.detail });
      }
    } catch (err) {
      _testState.statusMessage = `TEST ERROR: ${err.message}`;
      logger.error('TEST MODE: Upload error', { error: err.message });
    } finally {
      _testState.isProcessing = false;
    }
  }

  /**
   * TEST: Select and view a file
   */
  async function testSelectFile() {
    if (!_testState.testFileId && !selectedFileId) {
      _testState.statusMessage = 'TEST ERROR: Upload file first!';
      return;
    }

    const fileId = _testState.testFileId || selectedFileId;
    logger.info('TEST MODE: Selecting file', { fileId });
    _testState.statusMessage = `TEST: Selecting file ${fileId}...`;

    selectedFileId = fileId;
    _testState.statusMessage = `TEST: File ${fileId} selected`;
    logger.success('TEST MODE: File selected', { fileId });
  }

  /**
   * TEST: Edit a row
   */
  async function testEditRow() {
    if (!selectedFileId) {
      _testState.statusMessage = 'TEST ERROR: Select file first!';
      return;
    }

    logger.info('TEST MODE: Editing row', LDM_TEST_CONFIG.editRow);
    _testState.isProcessing = true;
    _testState.statusMessage = 'TEST: Getting rows...';

    try {
      // Get rows to find first row ID
      const rowsResponse = await fetch(`${API_BASE}/api/ldm/files/${selectedFileId}/rows?page=1&limit=1`, {
        headers: getAuthHeaders()
      });

      if (!rowsResponse.ok) {
        _testState.statusMessage = 'TEST ERROR: Could not get rows';
        return;
      }

      const rowsData = await rowsResponse.json();
      if (rowsData.rows.length === 0) {
        _testState.statusMessage = 'TEST ERROR: No rows found';
        return;
      }

      const rowId = rowsData.rows[0].id;
      _testState.statusMessage = `TEST: Editing row ${rowId}...`;

      // Edit the row
      const editResponse = await fetch(`${API_BASE}/api/ldm/rows/${rowId}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target: LDM_TEST_CONFIG.editRow.newTarget,
          status: LDM_TEST_CONFIG.editRow.newStatus
        })
      });

      if (editResponse.ok) {
        const result = await editResponse.json();
        _testState.lastResult = result;
        _testState.statusMessage = `TEST: Row ${rowId} edited successfully`;
        logger.success('TEST MODE: Row edited', { rowId, target: result.target });

        // Refresh grid
        if (virtualGrid) {
          await virtualGrid.loadRows();
        }
      } else {
        const err = await editResponse.json();
        _testState.statusMessage = `TEST ERROR: ${err.detail}`;
        logger.error('TEST MODE: Edit failed', { error: err.detail });
      }
    } catch (err) {
      _testState.statusMessage = `TEST ERROR: ${err.message}`;
      logger.error('TEST MODE: Edit error', { error: err.message });
    } finally {
      _testState.isProcessing = false;
    }
  }

  /**
   * TEST: Run full test sequence
   */
  async function testFullSequence() {
    logger.info('TEST MODE: Starting full sequence');
    _testState.statusMessage = 'TEST: Running full sequence...';

    // 1. Create project
    await testCreateProject();
    if (!_testState.testProjectId) return;

    // 2. Upload file
    await testUploadFile('uploadSmall');
    if (!_testState.testFileId) return;

    // 3. Select file
    await testSelectFile();

    // 4. Edit row
    await testEditRow();

    _testState.statusMessage = 'TEST: Full sequence complete!';
    logger.success('TEST MODE: Full sequence complete');
  }

  // ================================
  // TEST MODE INTERFACE (CDP Access)
  // ================================
  if (typeof window !== 'undefined') {
    window.ldmTest = {
      // Test functions
      createProject: () => testCreateProject(),
      uploadFile: (configKey) => testUploadFile(configKey || 'uploadSmall'),
      uploadTxt: () => testUploadFile('uploadTxt'),
      uploadXml: () => testUploadFile('uploadXml'),
      selectFile: () => testSelectFile(),
      editRow: () => testEditRow(),
      fullSequence: () => testFullSequence(),

      // VirtualGrid specific tests
      goToRow: async (rowNum) => {
        if (!virtualGrid) {
          _testState.statusMessage = 'TEST ERROR: VirtualGrid not ready';
          return false;
        }
        // Trigger scroll to row via the grid's internal method
        const scrollPos = (rowNum - 1) * 40; // ROW_HEIGHT = 40
        const container = document.querySelector('.scroll-container');
        if (container) {
          container.scrollTop = scrollPos;
          _testState.statusMessage = `TEST: Scrolled to row ${rowNum}`;
          return true;
        }
        return false;
      },

      getVisibleRange: () => {
        const container = document.querySelector('.scroll-container');
        if (!container) return null;
        const scrollTop = container.scrollTop;
        const height = container.clientHeight;
        const start = Math.floor(scrollTop / 40) + 1;
        const end = Math.ceil((scrollTop + height) / 40);
        return { start, end, scrollTop, height };
      },

      // Status getter
      getStatus: () => ({
        isProcessing: _testState.isProcessing,
        statusMessage: _testState.statusMessage,
        lastResult: _testState.lastResult,
        testProjectId: _testState.testProjectId,
        testFileId: _testState.testFileId,
        // Current UI state
        selectedProjectId: selectedProjectId,
        selectedFileId: selectedFileId,
        selectedFileName: selectedFileName,
        projectCount: projects.length,
        isHealthy: healthStatus !== null,
        // VirtualGrid state
        hasVirtualGrid: virtualGrid !== null
      }),

      // Config access for debugging
      getConfig: () => LDM_TEST_CONFIG,

      // Refresh projects list
      refreshProjects: async () => {
        if (fileExplorer) {
          await fileExplorer.loadProjects();
          return true;
        }
        return false;
      }
    };

    logger.info('TEST MODE: window.ldmTest interface exposed');
  }

  // Phase 10: React to navigation changes from header dropdown
  $effect(() => {
    const page = $currentPage;
    logger.info("Navigation page changed", { page });

    // When navigating to 'files' page, clear grid selection
    if (page === 'files') {
      // User clicked "Files" in dropdown - show file explorer view
      selectedFileId = null;
      selectedFileName = "";
      viewMode = 'file';
    } else if (page === 'tm') {
      // User clicked "TM" in dropdown - switch to TM view
      viewMode = 'tm';
    }
    // 'grid' page is set when a file is opened via handleFileSelect
  });

  onMount(async () => {
    logger.component("LDM", "mounted");
    loading = true;

    await checkHealth();
    // P33 Phase 4: Fetch connection status for Online/Offline badge
    await fetchConnectionStatus();
    // FileExplorer now auto-loads projects on its own mount
    // No need to call fileExplorer.loadProjects() here

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
    <!-- Phase 10: Page-based layout -->
    <div class="ldm-pages">
      {#if $currentPage === 'files'}
        <!-- Files Page: Full-width file explorer -->
        <FilesPage
          bind:projects
          bind:selectedProjectId
          bind:selectedFileId
          bind:selectedTMId
          bind:linkedTM
          connectionMode={connectionStatus.mode}
          on:fileSelect={handleFileSelect}
          on:projectSelect={handleProjectSelect}
          on:tmSelect={handleTMSelect}
          on:manageTMs={() => showTMManager = true}
          on:uploadToServer={(e) => logger.info("Upload to server requested", e.detail)}
          on:runQA={handleRunQA}
        />
      {:else if $currentPage === 'tm'}
        <!-- TM Page: Full-width TM management -->
        <TMPage
          bind:selectedTMId
          on:tmSelect={handleTMSelect}
        />
      {:else if $currentPage === 'grid'}
        <!-- Grid Page: File viewer with side panel -->
        <GridPage
          fileId={selectedFileId}
          fileName={selectedFileName}
          {linkedTM}
          onShowGridColumns={() => showGridColumns = true}
          onShowReferenceSettings={() => showReferenceSettings = true}
          on:dismissQA={handleDismissQA}
        />
      {:else if $currentPage === 'tm-entries'}
        <!-- TM Entries Page: Full-page TM entries viewer -->
        <div class="tm-entries-page">
          <div class="tm-entries-header">
            <button class="back-button" onclick={() => closeTMGrid()}>
              ← Back to TMs
            </button>
            <h2>{$openTM?.name || 'TM Entries'}</h2>
            <span class="entry-count">{$openTM?.entry_count?.toLocaleString() || 0} entries</span>
          </div>
          <div class="tm-entries-content">
            <TMDataGrid
              tmId={$openTM?.id}
              tmName={$openTM?.name}
            />
          </div>
        </div>
      {:else}
        <!-- Fallback: Show files page -->
        <FilesPage
          bind:projects
          bind:selectedProjectId
          bind:selectedFileId
          bind:selectedTMId
          bind:linkedTM
          connectionMode={connectionStatus.mode}
          on:fileSelect={handleFileSelect}
          on:projectSelect={handleProjectSelect}
          on:tmSelect={handleTMSelect}
          on:manageTMs={() => showTMManager = true}
          on:uploadToServer={(e) => logger.info("Upload to server requested", e.detail)}
          on:runQA={handleRunQA}
        />
      {/if}
    </div>
  {/if}

  <!-- TM Manager Modal -->
  <TMManager bind:open={showTMManager} />

  <!-- Grid Columns Modal -->
  <GridColumnsModal bind:open={showGridColumns} />

  <!-- Reference Settings Modal -->
  <ReferenceSettingsModal bind:open={showReferenceSettings} />

  <!-- UI-097: PreferencesModal removed - use top nav Settings > Preferences -->

  <!-- Server Status Modal -->
  <ServerStatus bind:open={showServerStatus} />

  <!-- P2: QA Menu Panel -->
  <QAMenuPanel
    bind:open={showQAMenu}
    fileId={selectedFileId}
    fileName={selectedFileName}
    on:openEditModal={handleOpenEditModal}
  />
</div>

<style>
  .ldm-app {
    height: 100%;
    display: flex;
    flex-direction: column;
    /* UI-053 FIX: Restored overflow: hidden - required for virtual scroll height constraint */
    /* Tooltips should use position: fixed or portal rendering instead */
    overflow: hidden;
    position: relative;
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
    /* UI-053 FIX: Restored overflow: hidden - required for virtual scroll height constraint */
    overflow: hidden;
    position: relative;
    /* Ensure flex children can't exceed this container */
    min-height: 0;
  }

  /* Phase 10: Page-based layout container */
  .ldm-pages {
    display: flex;
    flex: 1;
    width: 100%;
    overflow: hidden;
    min-height: 0;
  }

  /* TM Entries Page - Full-page TM viewer */
  .tm-entries-page {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .tm-entries-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .tm-entries-header .back-button {
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    cursor: pointer;
    font-size: 0.875rem;
  }

  .tm-entries-header .back-button:hover {
    background: var(--cds-layer-hover-01);
  }

  .tm-entries-header h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .tm-entries-header .entry-count {
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .tm-entries-content {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .ldm-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Phase 1: Grid + Side Panel Layout */
  .grid-with-panel {
    flex: 1;
    display: flex;
    overflow: hidden;
    min-height: 0;
  }

  /* Ensure VirtualGrid takes remaining space */
  .grid-with-panel > :global(.virtual-grid) {
    flex: 1;
    min-width: 0;
  }

  .ldm-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    min-height: 48px;
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .toolbar-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  /* P33 Phase 5: Go Online message */
  .go-online-message {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-left: 0.5rem;
    font-style: italic;
  }

  /* BUG-027: TM View placeholder CSS removed - now using TMDataGrid */
</style>
