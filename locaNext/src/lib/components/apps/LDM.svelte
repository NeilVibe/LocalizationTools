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
        if (dataGrid) {
          await dataGrid.loadRows();
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
        isHealthy: healthStatus !== null
      }),

      // Config access for debugging
      getConfig: () => LDM_TEST_CONFIG
    };

    logger.info('TEST MODE: window.ldmTest interface exposed');
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
