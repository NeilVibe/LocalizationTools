<script>
  import {
    Button,
    TextInput,
    Modal,
    Checkbox,
    Select,
    SelectItem,
    InlineLoading,
    ToastNotification
  } from "carbon-components-svelte";
  import { onMount } from "svelte";
  import { get } from "svelte/store";
  import { api } from "$lib/api/client.js";
  import { serverUrl } from "$lib/stores/app.js";

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);
  import { logger } from "$lib/utils/logger.js";
  import { remoteLogger } from "$lib/utils/remote-logger.js";
  import { websocket } from "$lib/api/websocket.js";
  import { telemetry } from "$lib/utils/telemetry.js";
  import { createTracker, parseProgress } from "$lib/utils/trackedOperation.js";

  // Check if running in Electron (Svelte 5 state)
  let isElectron = $state(false);
  let pythonToolsPath = $state('');

  onMount(async () => {
    logger.component("XLSTransfer", "mounted", { mode: isElectron ? "electron" : "browser" });

    if (typeof window !== 'undefined' && window.electron) {
      isElectron = true;
      const paths = await window.electron.getPaths();
      pythonToolsPath = paths.pythonToolsPath;

      logger.info("XLSTransfer initialized in Electron mode", {
        pythonToolsPath: pythonToolsPath
      });
    } else {
      logger.info("XLSTransfer initialized in Browser mode");
    }
  });

  // Status states (Svelte 5)
  let isProcessing = $state(false);
  let statusMessage = $state('');
  let showNotification = $state(false);
  let notificationType = $state('success');

  // Dictionary loading state (Svelte 5)
  let isDictionaryLoaded = $state(false);
  let isTransferEnabled = $state(false);

  // Threshold value (최소 일치율) (Svelte 5)
  let threshold = $state('0.99');

  // Global stop flag (Svelte 5)
  let stopProcessing = $state(false);

  // Upload settings modal state (Svelte 5)
  let showUploadSettings = $state(false);
  let uploadSettingsFiles = $state([]);
  let uploadSettingsOperationType = $state('');
  let uploadSettingsData = $state([]);

  // File input references for browser mode
  let fileInputCreateDict;
  let fileInputTransferClose;
  let fileInputTransferExcel;

  // ============================================
  // TEST MODE - For autonomous CDP testing
  // ============================================
  const TEST_FILES_PATH = 'D:\\TestFilesForLocaNext';
  const TEST_CONFIG = {
    createDictionary: {
      // GlossaryUploadTestFile.xlsx: 100 rows, 2 columns (KR + FR) - fast for testing
      // For large tests, use TESTSMALL.xlsx (22917 rows, ~15min)
      file: `${TEST_FILES_PATH}\\GlossaryUploadTestFile.xlsx`,
      sheet: 'Sheet1',
      krColumn: 'A',
      transColumn: 'B'
    },
    translateExcel: {
      // Use a file with KR text to translate (single column is OK for translation target)
      file: `${TEST_FILES_PATH}\\translationTEST.xlsx`,
      sheet: 'Sheet1',
      krColumn: 'A',
      transColumn: 'B'
    },
    transferToClose: {
      file: `${TEST_FILES_PATH}\\closetotest.txt`
    }
  };

  // Test state tracking (explicit object for CDP access - bypasses Svelte reactivity issues)
  const _testState = {
    isProcessing: false,
    statusMessage: '',
    isDictionaryLoaded: false,
    isTransferEnabled: false
  };

  // Expose test functions globally for CDP access
  if (typeof window !== 'undefined') {
    window.xlsTransferTest = {
      createDictionary: () => testCreateDictionary(),
      loadDictionary: () => loadDictionary(),
      translateExcel: () => testTranslateExcel(),
      transferToClose: () => testTransferToClose(),
      // Use explicit state object for reliable CDP access
      getStatus: () => ({ ..._testState }),
      // Also expose direct access to state for updates
      _state: _testState
    };
  }

  // TEST: Create Dictionary (skips file dialog, with progress streaming)
  // FACTOR ARCHITECTURE: Uses createTracker for centralized progress
  async function testCreateDictionary() {
    logger.info("TEST MODE: Creating dictionary with test file", TEST_CONFIG.createDictionary);

    if (!isElectron) {
      showStatus('Test mode requires Electron', 'error');
      return;
    }

    const testFile = TEST_CONFIG.createDictionary.file;

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('XLSTransfer', 'Create Dictionary');
    tracker.start();

    // Update both Svelte state AND test state object for CDP access
    isProcessing = true;
    statusMessage = 'TEST: Starting dictionary creation...';
    _testState.isProcessing = true;
    _testState.statusMessage = 'TEST: Starting dictionary creation...';

    // Build selections directly (skip file dialog and modal)
    const selections = {
      [testFile]: {
        [TEST_CONFIG.createDictionary.sheet]: {
          kr_column: TEST_CONFIG.createDictionary.krColumn,
          trans_column: TEST_CONFIG.createDictionary.transColumn
        }
      }
    };

    logger.info("TEST MODE: Executing create_dictionary with selections", selections);

    // FACTOR: Progress handler using centralized parseProgress
    const progressHandler = (data) => {
      if (data.type === 'stderr' && data.data) {
        const parsed = parseProgress(data.data);
        if (parsed && parsed.message) {
          // Update BOTH Svelte state and test state object
          statusMessage = `TEST: ${parsed.message}`;
          _testState.statusMessage = `TEST: ${parsed.message}`;

          // FACTOR: Update tracker with parsed progress
          tracker.update(parsed.progress || 0, parsed.message);

          logger.info("TEST PROGRESS", { message: parsed.message, progress: parsed.progress });
        }
      }
    };

    // Register progress listener
    window.electron.onPythonOutput(progressHandler);

    try {
      const startTime = performance.now();

      const result = await window.electron.executePython({
        scriptPath: `${pythonToolsPath}/xlstransfer/process_operation.py`,
        args: ['create_dictionary', JSON.stringify(selections), threshold]
      });

      const elapsed = performance.now() - startTime;

      if (result.success) {
        // Parse output if JSON
        let output = result.output;
        try {
          output = JSON.parse(result.output);
        } catch (e) { /* not JSON */ }

        // Mark dictionary as loaded on success - update BOTH states
        isDictionaryLoaded = true;
        isTransferEnabled = true;
        _testState.isDictionaryLoaded = true;
        _testState.isTransferEnabled = true;

        const successMsg = `Dictionary created! ${output?.split_entries || 0} split + ${output?.whole_entries || 0} whole entries (${(elapsed/1000).toFixed(1)}s)`;
        statusMessage = `TEST: ${successMsg}`;
        _testState.statusMessage = `TEST: ${successMsg}`;

        // FACTOR: Complete tracker with metadata
        tracker.complete(successMsg, {
          filename: selections.length > 0 ? selections[0].split('/').pop() : 'dictionary',
          rowCount: (output?.split_entries || 0) + (output?.whole_entries || 0)
        });

        logger.success("TEST MODE: Dictionary created", { elapsed_ms: elapsed.toFixed(2), output });
        showStatus(`TEST: ${successMsg}`, 'success');
      } else {
        const errorMsg = `Failed: ${result.error}`;
        statusMessage = `TEST FAILED: ${result.error}`;
        _testState.statusMessage = `TEST FAILED: ${result.error}`;

        // FACTOR: Fail tracker
        tracker.fail(errorMsg);

        logger.error("TEST MODE: Dictionary creation failed", { error: result.error });
        showStatus(`TEST FAILED: ${result.error}`, 'error');
      }
    } catch (error) {
      const errorMsg = `Error: ${error.message}`;
      statusMessage = `TEST ERROR: ${error.message}`;
      _testState.statusMessage = `TEST ERROR: ${error.message}`;

      // FACTOR: Fail tracker
      tracker.fail(errorMsg);

      logger.error("TEST MODE: Exception", { error: error.message });
      showStatus(`TEST ERROR: ${error.message}`, 'error');
    } finally {
      isProcessing = false;
      _testState.isProcessing = false;
      // Remove progress listener
      window.electron.offPythonOutput();
    }
  }

  // TEST: Translate Excel (skips file dialog)
  // FACTOR ARCHITECTURE: Uses createTracker for centralized progress
  async function testTranslateExcel() {
    logger.info("TEST MODE: Translating Excel with test file", TEST_CONFIG.translateExcel);

    if (!isDictionaryLoaded) {
      showStatus('Load dictionary first!', 'error');
      return;
    }

    const testFile = TEST_CONFIG.translateExcel.file;

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('XLSTransfer', 'Translate Excel');
    tracker.start();

    isProcessing = true;
    statusMessage = 'TEST MODE: Translating Excel...';

    const selections = {
      [testFile]: {
        [TEST_CONFIG.translateExcel.sheet]: {
          kr_column: TEST_CONFIG.translateExcel.krColumn,
          trans_column: TEST_CONFIG.translateExcel.transColumn
        }
      }
    };

    // FACTOR: Progress handler using centralized parseProgress
    const progressHandler = (data) => {
      if (data.type === 'stderr' && data.data) {
        const parsed = parseProgress(data.data);
        if (parsed && parsed.message) {
          statusMessage = `TEST: ${parsed.message}`;
          tracker.update(parsed.progress || 0, parsed.message);
        }
      }
    };

    window.electron.onPythonOutput(progressHandler);

    try {
      const startTime = performance.now();

      const result = await window.electron.executePython({
        scriptPath: `${pythonToolsPath}/xlstransfer/process_operation.py`,
        args: ['translate_excel', JSON.stringify(selections), threshold]
      });

      const elapsed = performance.now() - startTime;

      if (result.success) {
        const successMsg = `Excel translated! (${(elapsed/1000).toFixed(1)}s)`;
        tracker.complete(successMsg);
        logger.success("TEST MODE: Excel translated", { elapsed_ms: elapsed.toFixed(2) });
        showStatus(`TEST: ${successMsg}`, 'success');
      } else {
        tracker.fail(result.error);
        logger.error("TEST MODE: Excel translation failed", { error: result.error });
        showStatus(`TEST FAILED: ${result.error}`, 'error');
      }
    } catch (error) {
      tracker.fail(error.message);
      logger.error("TEST MODE: Exception", { error: error.message });
      showStatus(`TEST ERROR: ${error.message}`, 'error');
    } finally {
      isProcessing = false;
      window.electron.offPythonOutput();
    }
  }

  // TEST: Transfer to Close (skips file dialog)
  // FACTOR ARCHITECTURE: Uses createTracker for centralized progress
  async function testTransferToClose() {
    logger.info("TEST MODE: Transfer to Close with test file", TEST_CONFIG.transferToClose);

    if (!isDictionaryLoaded) {
      showStatus('Load dictionary first!', 'error');
      return;
    }

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('XLSTransfer', 'Transfer to Close');
    tracker.start();

    isProcessing = true;
    statusMessage = 'TEST MODE: Translating text file...';

    // FACTOR: Progress handler using centralized parseProgress
    const progressHandler = (data) => {
      if (data.type === 'stderr' && data.data) {
        const parsed = parseProgress(data.data);
        if (parsed && parsed.message) {
          statusMessage = `TEST: ${parsed.message}`;
          tracker.update(parsed.progress || 0, parsed.message);
        }
      }
    };

    window.electron.onPythonOutput(progressHandler);

    try {
      const startTime = performance.now();

      const result = await window.electron.executePython({
        scriptPath: `${pythonToolsPath}/xlstransfer/translate_file.py`,
        args: [TEST_CONFIG.transferToClose.file, threshold]
      });

      const elapsed = performance.now() - startTime;

      if (result.success) {
        const successMsg = `File translated! (${(elapsed/1000).toFixed(1)}s)`;
        tracker.complete(successMsg);
        logger.success("TEST MODE: File translated", { elapsed_ms: elapsed.toFixed(2) });
        showStatus(`TEST: ${successMsg}`, 'success');
      } else {
        tracker.fail(result.error);
        logger.error("TEST MODE: File translation failed", { error: result.error });
        showStatus(`TEST FAILED: ${result.error}`, 'error');
      }
    } catch (error) {
      tracker.fail(error.message);
      logger.error("TEST MODE: Exception", { error: error.message });
      showStatus(`TEST ERROR: ${error.message}`, 'error');
    } finally {
      isProcessing = false;
      window.electron.offPythonOutput();
    }
  }

  function showStatus(message, type = 'success') {
    statusMessage = message;
    notificationType = type;
    showNotification = true;
    setTimeout(() => { showNotification = false; }, 5000);
  }

  // 1. Create dictionary
  async function createDictionary() {
    logger.userAction("Create Dictionary button clicked", { mode: isElectron ? "electron" : "browser" });

    if (isElectron) {
      // Electron mode: use file dialog
      try {
        logger.info("Opening file dialog for dictionary creation");

        const files = await window.electron.selectFiles({
          title: 'Select Excel Files',
          filters: [{ name: 'Excel files', extensions: ['xlsx', 'xls'] }],
          properties: ['openFile', 'multiSelections']
        });

        if (!files || files.length === 0) {
          logger.warning("No files selected for dictionary creation");
          showStatus('No files selected', 'error');
          return;
        }

        logger.info("Files selected for dictionary creation", {
          file_count: files.length,
          filenames: files.map(f => f.split('/').pop())
        });

        // Show immediate feedback
        isProcessing = true;
        statusMessage = 'Loading sheet info...';

        // Open upload settings GUI
        openUploadSettingsGUI(files, 'create_dictionary');

      } catch (error) {
        logger.error("Dictionary creation failed in Electron mode", {
          error: error.message,
          error_type: error.name
        });
        showStatus(error.message, 'error');
      }
    } else {
      // Browser mode: trigger file input
      logger.info("Triggering file input for dictionary creation (browser mode)");
      fileInputCreateDict.click();
    }
  }

  // Handle file selection in browser mode for creating dictionary
  async function handleCreateDictFiles(event) {
    const files = event.target.files;

    logger.info("Files selected for dictionary creation (browser)", {
      file_count: files.length,
      filenames: Array.from(files).map(f => f.name)
    });

    if (!files || files.length === 0) {
      logger.warning("No files selected");
      showStatus('No files selected', 'error');
      return;
    }

    // Show immediate feedback
    isProcessing = true;
    statusMessage = 'Loading sheet info...';

    // Open upload settings GUI (same as Electron mode)
    // Convert FileList to Array and store as File objects with path property
    const fileArray = Array.from(files).map(file => {
      // For browser mode, use file name as path
      Object.defineProperty(file, 'path', {
        value: file.name,
        writable: false
      });
      return file;
    });

    openUploadSettingsGUI(fileArray, 'create_dictionary');
  }

  // OLD BROWSER CODE - REMOVED, now uses Upload Settings Modal
  /*
  async function handleCreateDictFiles_OLD(event) {
    const startTime = performance.now();
    const files = event.target.files;

    if (!files || files.length === 0) {
      showStatus('No files selected', 'error');
      return;
    }

    isProcessing = true;
    statusMessage = 'Creating dictionary...';

    try {
      const result = await api.xlsTransferCreateDictionary(files);

      const elapsed = performance.now() - startTime;

      if (result.success || result.status === 'success') {
        logger.success("Dictionary created successfully", {
          kr_count: result.kr_count,
          files_processed: result.files_processed || files.length,
          elapsed_ms: elapsed.toFixed(2)
        });
        showStatus(`Dictionary created! ${result.kr_count} Korean-English pairs`, 'success');
      } else {
        logger.error("Dictionary creation failed", {
          message: result.message,
          elapsed_ms: elapsed.toFixed(2)
        });
        showStatus(result.message || 'Failed to create dictionary', 'error');
      }
    } catch (error) {
      const elapsed = performance.now() - startTime;
      logger.error("Dictionary creation error", {
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });
      showStatus(error.message, 'error');
    } finally {
      isProcessing = false;
      // Reset file input
      event.target.value = '';
    }
  }
  */

  // 2. Load dictionary
  async function loadDictionary() {
    const startTime = performance.now();
    logger.userAction("Load Dictionary button clicked", { mode: isElectron ? "electron" : "browser" });

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('XLSTransfer', 'Load Dictionary');
    tracker.start();

    isProcessing = true;
    statusMessage = 'Loading dictionary...';
    tracker.update(10, 'Loading dictionary...');

    try {
      if (isElectron) {
        // Electron mode: use Python script
        logger.info("Loading dictionary via Python script (Electron mode)", {
          scriptPath: `${pythonToolsPath}/xlstransfer/load_dictionary.py`
        });

        tracker.update(30, 'Executing Python script...');

        const result = await window.electron.executePython({
          scriptPath: `${pythonToolsPath}/xlstransfer/load_dictionary.py`,
          args: []
        });

        const elapsed = performance.now() - startTime;

        if (result.success) {
          isDictionaryLoaded = true;
          isTransferEnabled = true;
          logger.success("Dictionary loaded successfully (Electron)", {
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationSuccess('XLSTransfer', 'load_dictionary', startTime, {
            mode: 'electron'
          });
          const successMsg = 'Dictionary loaded successfully! Transfer buttons enabled.';
          showStatus(successMsg, 'success');
          tracker.complete(successMsg, { filename: 'Dictionary (Electron)' });
        } else {
          logger.error("Dictionary load failed (Electron)", {
            error: result.error,
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationError('XLSTransfer', 'load_dictionary', startTime,
            new Error(result.error || 'Failed to load dictionary'), { mode: 'electron' });
          const errorMsg = result.error || 'Failed to load dictionary';
          showStatus(errorMsg, 'error');
          tracker.fail(errorMsg);
        }
      } else {
        // Browser mode: use API
        logger.apiCall("/api/v2/xlstransfer/test/load-dictionary", "POST");
        tracker.update(30, 'Calling API...');

        const result = await api.xlsTransferLoadDictionary();

        const elapsed = performance.now() - startTime;

        if (result.success || result.status === 'success') {
          isDictionaryLoaded = true;
          isTransferEnabled = true;
          logger.success("Dictionary loaded successfully (Browser)", {
            total_pairs: result.total_pairs,
            split_pairs: result.split_pairs,
            whole_pairs: result.whole_pairs,
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationSuccess('XLSTransfer', 'load_dictionary', startTime, {
            mode: 'browser',
            total_pairs: result.total_pairs
          });
          const successMsg = `Dictionary loaded! ${result.total_pairs || 0} pairs ready.`;
          showStatus(successMsg, 'success');
          tracker.complete(successMsg, {
            filename: 'Dictionary (API)',
            pairs: result.total_pairs || 0
          });
        } else {
          logger.error("Dictionary load failed (Browser)", {
            message: result.message,
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationError('XLSTransfer', 'load_dictionary', startTime,
            new Error(result.message || 'Failed to load dictionary'), { mode: 'browser' });
          const errorMsg = result.message || 'Failed to load dictionary';
          showStatus(errorMsg, 'error');
          tracker.fail(errorMsg);
        }
      }
    } catch (error) {
      const elapsed = performance.now() - startTime;
      logger.error("Dictionary load error", {
        error: error.message,
        error_type: error.name,
        mode: isElectron ? "electron" : "browser",
        elapsed_ms: elapsed.toFixed(2)
      });
      telemetry.trackOperationError('XLSTransfer', 'load_dictionary', startTime, error, {
        mode: isElectron ? 'electron' : 'browser'
      });
      showStatus(error.message, 'error');
      tracker.fail(error.message);
    } finally {
      isProcessing = false;
    }
  }

  // 3. Transfer to Close (.txt file translation)
  async function transferToClose() {
    logger.userAction("Transfer to Close button clicked", {
      mode: isElectron ? "electron" : "browser",
      dictionary_loaded: isDictionaryLoaded
    });

    if (!isDictionaryLoaded) {
      logger.warning("Transfer to Close blocked - dictionary not loaded");
      showStatus('Please load dictionary first', 'error');
      return;
    }

    if (isElectron) {
      // Electron mode: use file dialog
      try {
        logger.info("Opening file dialog for .txt file translation");

        const files = await window.electron.selectFiles({
          title: 'Select .txt File',
          filters: [{ name: 'Text files', extensions: ['txt'] }],
          properties: ['openFile']
        });

        if (!files || files.length === 0) {
          logger.warning("No file selected for translation");
          showStatus('No file selected', 'error');
          return;
        }

        logger.file("selected", files[0].split('/').pop(), { type: "txt", threshold: threshold });

        // FACTOR: Create tracker for this operation
        const tracker = createTracker('XLSTransfer', 'Transfer to Close');
        tracker.start();

        isProcessing = true;
        stopProcessing = false;
        statusMessage = 'Translating file...';
        tracker.update(10, 'Translating file...');

        const startTime = performance.now();

        // FACTOR: Progress handler for Python stderr
        const progressHandler = (data) => {
          if (data.type === 'stderr' && data.data) {
            const parsed = parseProgress(data.data);
            if (parsed && parsed.message) {
              statusMessage = parsed.message;
              tracker.update(parsed.progress || 50, parsed.message);
            }
          }
        };
        window.electron.onPythonOutput(progressHandler);

        const result = await window.electron.executePython({
          scriptPath: `${pythonToolsPath}/xlstransfer/translate_file.py`,
          args: [files[0], threshold]
        });

        window.electron.offPythonOutput(progressHandler);

        const elapsed = performance.now() - startTime;

        if (result.success) {
          logger.success("File translation completed (Electron)", {
            filename: files[0].split('/').pop(),
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationSuccess('XLSTransfer', 'transfer_to_close', startTime, {
            mode: 'electron',
            threshold: parseFloat(threshold)
          });
          const successMsg = 'Translation completed!';
          showStatus(successMsg, 'success');
          tracker.complete(successMsg);
        } else {
          logger.error("File translation failed (Electron)", {
            error: result.error,
            filename: files[0].split('/').pop(),
            elapsed_ms: elapsed.toFixed(2)
          });
          telemetry.trackOperationError('XLSTransfer', 'transfer_to_close', startTime,
            new Error(result.error || 'Translation failed'), { mode: 'electron' });
          const errorMsg = result.error || 'Translation failed';
          showStatus(errorMsg, 'error');
          tracker.fail(errorMsg);
        }
      } catch (error) {
        logger.error("Transfer to Close error (Electron)", {
          error: error.message,
          error_type: error.name
        });
        telemetry.trackOperationError('XLSTransfer', 'transfer_to_close', Date.now(), error, {
          mode: 'electron'
        });
        showStatus(error.message, 'error');
      } finally {
        isProcessing = false;
      }
    } else {
      // Browser mode: trigger file input
      logger.info("Triggering file input for .txt translation (browser mode)");
      fileInputTransferClose.click();
    }
  }

  // Handle file selection in browser mode for Transfer to Close
  async function handleTransferCloseFile(event) {
    const startTime = performance.now();
    const files = event.target.files;

    logger.file("selected", files[0]?.name || "unknown", {
      type: "txt",
      size: files[0]?.size,
      threshold: threshold
    });

    if (!files || files.length === 0) {
      logger.warning("No file selected for translation");
      showStatus('No file selected', 'error');
      return;
    }

    isProcessing = true;
    statusMessage = 'Translating file...';

    try {
      logger.apiCall("/api/v2/xlstransfer/test/translate-file", "POST", {
        filename: files[0].name,
        file_type: "txt",
        threshold: parseFloat(threshold)
      });

      const result = await api.xlsTransferTranslateFile(files[0], parseFloat(threshold));

      const elapsed = performance.now() - startTime;

      if (result.success || result.status === 'success') {
        logger.success("File translation completed (Browser)", {
          filename: files[0].name,
          lines_translated: result.lines_translated,
          matches_found: result.matches_found,
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationSuccess('XLSTransfer', 'transfer_to_close', startTime, {
          mode: 'browser',
          threshold: parseFloat(threshold),
          lines_translated: result.lines_translated,
          matches_found: result.matches_found
        });
        showStatus('Translation completed!', 'success');

        // If there's a download URL, trigger download
        if (result.output_file || result.download_url) {
          const downloadUrl = `${api.baseURL}${result.download_url || result.output_file}`;
          logger.file("download", result.filename || 'translated_file.txt');

          const a = document.createElement('a');
          a.href = downloadUrl;
          a.download = result.filename || 'translated_file.txt';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      } else {
        logger.error("File translation failed (Browser)", {
          filename: files[0].name,
          message: result.message,
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationError('XLSTransfer', 'transfer_to_close', startTime,
          new Error(result.message || 'Translation failed'), { mode: 'browser' });
        showStatus(result.message || 'Translation failed', 'error');
      }
    } catch (error) {
      const elapsed = performance.now() - startTime;
      logger.error("Transfer to Close error (Browser)", {
        filename: files[0].name,
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });
      telemetry.trackOperationError('XLSTransfer', 'transfer_to_close', startTime, error, {
        mode: 'browser'
      });
      showStatus(error.message, 'error');
    } finally {
      isProcessing = false;
      // Reset file input
      event.target.value = '';
    }
  }

  // 4. STOP button
  function stopProcessingFunction() {
    logger.userAction("STOP button clicked", { isProcessing: isProcessing });
    stopProcessing = true;
    logger.warning("Processing stopped by user");
    showStatus('Process stopped', 'info');
  }

  // 5. Transfer to Excel
  async function transferToExcel() {
    logger.userAction("Transfer to Excel button clicked", {
      mode: isElectron ? "electron" : "browser",
      dictionary_loaded: isDictionaryLoaded
    });

    if (!isDictionaryLoaded) {
      logger.warning("Transfer to Excel blocked - dictionary not loaded");
      showStatus('Please load dictionary first', 'error');
      return;
    }

    if (isElectron) {
      // Electron mode: use file dialog and upload settings GUI
      try {
        logger.info("Opening file dialog for Excel file translation");

        const files = await window.electron.selectFiles({
          title: 'Select Excel Files',
          filters: [{ name: 'Excel files', extensions: ['xlsx', 'xls'] }],
          properties: ['openFile', 'multiSelections']
        });

        if (!files || files.length === 0) {
          logger.warning("No files selected for Excel translation");
          showStatus('No files selected', 'error');
          return;
        }

        logger.info("Files selected for Excel translation", {
          file_count: files.length,
          filenames: files.map(f => f.split('/').pop())
        });

        // Show immediate feedback
        isProcessing = true;
        statusMessage = 'Loading sheet info...';

        // Open upload settings GUI
        openUploadSettingsGUI(files, 'translate_excel');

      } catch (error) {
        logger.error("Transfer to Excel error (Electron)", {
          error: error.message,
          error_type: error.name
        });
        showStatus(error.message, 'error');
      }
    } else {
      // Browser mode: trigger file input
      logger.info("Triggering file input for Excel translation (browser mode)");
      fileInputTransferExcel.click();
    }
  }

  // Handle file selection in browser mode for Transfer to Excel
  async function handleTransferExcelFile(event) {
    const files = Array.from(event.target.files);

    logger.file("selected", files[0]?.name || "unknown", {
      type: "excel",
      size: files[0]?.size,
      file_count: files.length
    });

    if (!files || files.length === 0) {
      logger.warning("No file selected for Excel translation");
      showStatus('No file selected', 'error');
      return;
    }

    // Clear file input so same file can be selected again
    event.target.value = '';

    // Show immediate feedback
    isProcessing = true;
    statusMessage = 'Loading sheet info...';

    // Open Upload Settings GUI for sheet/column selection
    logger.info("Opening upload settings GUI for Excel translation", {
      file_count: files.length,
      filenames: files.map(f => f.name)
    });

    await openUploadSettingsGUI(files, 'translate_excel');
  }

  // 6. Check Newlines
  async function checkNewlines() {
    logger.userAction("Check Newlines button clicked");

    if (!isElectron) {
      logger.warning("Check Newlines blocked - Electron mode required");
      showStatus('Must run in Electron app', 'error');
      return;
    }

    try {
      logger.info("Opening file dialog for newlines check");

      const files = await window.electron.selectFiles({
        title: 'Select Excel Files',
        filters: [{ name: 'Excel files', extensions: ['xlsx', 'xls'] }],
        properties: ['openFile', 'multiSelections']
      });

      if (!files || files.length === 0) {
        logger.warning("No files selected for newlines check");
        showStatus('No files selected', 'error');
        return;
      }

      logger.info("Files selected for newlines check", {
        file_count: files.length,
        filenames: files.map(f => f.split('/').pop())
      });

      // Show immediate feedback
      isProcessing = true;
      statusMessage = 'Loading sheet info...';

      // Open upload settings GUI
      openUploadSettingsGUI(files, 'check_newlines');

    } catch (error) {
      logger.error("Check Newlines error", {
        error: error.message,
        error_type: error.name
      });
      showStatus(error.message, 'error');
    }
  }

  // 7. Combine Excel Files
  async function combineExcelFiles() {
    logger.userAction("Combine Excel Files button clicked");

    if (!isElectron) {
      logger.warning("Combine Excel Files blocked - Electron mode required");
      showStatus('Must run in Electron app', 'error');
      return;
    }

    try {
      logger.info("Opening file dialog for Excel combine");

      const files = await window.electron.selectFiles({
        title: 'Select Excel Files',
        filters: [{ name: 'Excel files', extensions: ['xlsx', 'xls'] }],
        properties: ['openFile', 'multiSelections']
      });

      if (!files || files.length === 0) {
        logger.warning("No files selected for Excel combine");
        showStatus('No files selected', 'error');
        return;
      }

      logger.info("Files selected for Excel combine", {
        file_count: files.length,
        filenames: files.map(f => f.split('/').pop())
      });

      // Show immediate feedback
      isProcessing = true;
      statusMessage = 'Loading sheet info...';

      // Open upload settings GUI
      openUploadSettingsGUI(files, 'combine_excel');

    } catch (error) {
      logger.error("Combine Excel Files error", {
        error: error.message,
        error_type: error.name
      });
      showStatus(error.message, 'error');
    }
  }

  // 8. Newline Auto Adapt
  async function newlineAutoAdapt() {
    logger.userAction("Newline Auto Adapt button clicked");

    if (!isElectron) {
      logger.warning("Newline Auto Adapt blocked - Electron mode required");
      showStatus('Must run in Electron app', 'error');
      return;
    }

    try {
      logger.info("Opening file dialog for newline auto adapt");

      const files = await window.electron.selectFiles({
        title: 'Select Excel Files',
        filters: [{ name: 'Excel files', extensions: ['xlsx', 'xls'] }],
        properties: ['openFile', 'multiSelections']
      });

      if (!files || files.length === 0) {
        logger.warning("No files selected for newline auto adapt");
        showStatus('No files selected', 'error');
        return;
      }

      logger.info("Files selected for newline auto adapt", {
        file_count: files.length,
        filenames: files.map(f => f.split('/').pop())
      });

      // Show immediate feedback
      isProcessing = true;
      statusMessage = 'Loading sheet info...';

      // Open upload settings GUI
      openUploadSettingsGUI(files, 'newline_auto_adapt');

    } catch (error) {
      logger.error("Newline Auto Adapt error", {
        error: error.message,
        error_type: error.name
      });
      showStatus(error.message, 'error');
    }
  }

  // 9. Simple Excel Transfer
  async function simpleExcelTransfer() {
    logger.userAction("Simple Excel Transfer button clicked");

    if (!isElectron) {
      logger.warning("Simple Excel Transfer blocked - Electron mode required");
      showStatus('Must run in Electron app', 'error');
      return;
    }

    try {
      const startTime = performance.now();

      isProcessing = true;
      statusMessage = 'Starting Simple Excel Transfer...';

      logger.info("Starting Simple Excel Transfer", {
        scriptPath: `${pythonToolsPath}/xlstransfer/simple_transfer.py`
      });

      const result = await window.electron.executePython({
        scriptPath: `${pythonToolsPath}/xlstransfer/simple_transfer.py`,
        args: []
      });

      const elapsed = performance.now() - startTime;

      if (result.success) {
        logger.success("Simple Excel Transfer completed", {
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationSuccess('XLSTransfer', 'simple_excel_transfer', startTime, {
          mode: 'electron'
        });
        showStatus('Simple Excel Transfer completed!', 'success');
      } else {
        logger.error("Simple Excel Transfer failed", {
          error: result.error,
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationError('XLSTransfer', 'simple_excel_transfer', startTime,
          new Error(result.error || 'Transfer failed'), { mode: 'electron' });
        showStatus(result.error || 'Transfer failed', 'error');
      }
    } catch (error) {
      logger.error("Simple Excel Transfer error", {
        error: error.message,
        error_type: error.name
      });
      telemetry.trackOperationError('XLSTransfer', 'simple_excel_transfer', startTime, error, {
        mode: 'electron'
      });
      showStatus(error.message, 'error');
    } finally {
      isProcessing = false;
    }
  }

  // Upload Settings GUI (for sheet and column selection)
  // DUAL MODE: Works in both Electron and Browser
  /**
   * Close upload settings modal
   * Note: Data is cleared when modal reopens in openUploadSettingsGUI()
   */
  function closeUploadSettings() {
    logger.info("Closing upload settings modal");
    showUploadSettings = false;
  }

  async function openUploadSettingsGUI(files, operationType) {
    logger.info("Opening upload settings GUI", {
      file_count: files.length,
      operation_type: operationType,
      mode: isElectron ? "electron" : "browser"
    });

    uploadSettingsFiles = files;
    uploadSettingsOperationType = operationType;

    // Get sheet names for each file
    uploadSettingsData = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        let sheetInfo;
        const fileName = isElectron ? file.split('/').pop() : file.name;

        // Update status message with progress
        statusMessage = `Loading sheet info... (${i + 1}/${files.length}) ${fileName}`;

        logger.info("Reading sheet info from file", {
          filename: fileName,
          mode: isElectron ? "electron" : "browser"
        });

        if (isElectron) {
          // Electron mode: Call Python script via IPC
          const ipcResult = await window.electron.executePython({
            scriptPath: `${pythonToolsPath}/xlstransfer/get_sheets.py`,
            args: [file]
          });

          // Parse the JSON output from Python script
          if (ipcResult.success && ipcResult.output) {
            try {
              sheetInfo = JSON.parse(ipcResult.output);
            } catch (parseError) {
              logger.error("Failed to parse Python output as JSON", {
                output: ipcResult.output,
                error: parseError.message
              });
              sheetInfo = { success: false, error: `Invalid JSON response: ${parseError.message}` };
            }
          } else {
            sheetInfo = { success: false, error: ipcResult.error || 'Python script failed' };
          }
        } else {
          // Browser mode: Call API endpoint
          sheetInfo = await api.xlsTransferGetSheets(file);
        }

        remoteLogger.info("SHEET INFO RESPONSE", { sheetInfo, fileName, isElectron });

        if (sheetInfo.success && sheetInfo.sheets && Array.isArray(sheetInfo.sheets)) {
          logger.success("Sheet info retrieved", {
            filename: fileName,
            sheet_count: sheetInfo.sheets.length,
            sheets: sheetInfo.sheets
          });

          const fileDataEntry = {
            fileName: fileName,
            filePath: isElectron ? file : file.name,
            fileObject: isElectron ? null : file, // Store File object for browser mode
            sheets: sheetInfo.sheets.map(sheet => ({
              name: sheet,
              selected: false,
              krColumn: '',
              transColumn: ''
            }))
          };

          remoteLogger.info("PUSHING TO uploadSettingsData", { fileDataEntry });
          uploadSettingsData = [...uploadSettingsData, fileDataEntry];
          remoteLogger.info("uploadSettingsData AFTER PUSH", { uploadSettingsData: uploadSettingsData.map(d => ({fileName: d.fileName, sheetCount: d.sheets.length})) });
        } else {
          const errorMsg = !sheetInfo.success
            ? `Failed to read file: ${sheetInfo.error || 'Unknown error'}`
            : !sheetInfo.sheets
            ? 'No sheets found in response - invalid file or API error'
            : 'Invalid sheet data format';
          remoteLogger.error("sheetInfo validation failed", { sheetInfo, errorMsg });
          logger.error("Sheet info validation failed", { filename: fileName, error: errorMsg });
          isProcessing = false;
          showStatus(`Error: ${errorMsg}`, 'error');
          return;
        }
      } catch (error) {
        const fileName = isElectron ? file.split('/').pop() : file.name;
        logger.error("Error reading sheet info", {
          filename: fileName,
          error: error.message,
          error_type: error.name
        });
        isProcessing = false;
        showStatus(`Error reading ${fileName}: ${error.message}`, 'error');
        return;
      }
    }

    remoteLogger.info("BEFORE OPENING MODAL", {
      uploadSettingsDataLength: uploadSettingsData.length,
      uploadSettingsData: uploadSettingsData.map(d => ({fileName: d.fileName, sheetCount: d.sheets.length})),
      showUploadSettings
    });

    // Clear processing state - modal is ready
    isProcessing = false;
    showUploadSettings = true;

    remoteLogger.info("AFTER SETTING showUploadSettings = true");
    logger.info("Upload settings GUI opened successfully", {
      files_loaded: uploadSettingsData.length
    });
  }

  async function executeUploadSettings() {
    logger.info("Executing upload settings", {
      operation_type: uploadSettingsOperationType
    });

    // Validate selections
    let hasSelection = false;
    let selectedSheetCount = 0;
    for (const fileData of uploadSettingsData) {
      for (const sheet of fileData.sheets) {
        if (sheet.selected) {
          hasSelection = true;
          selectedSheetCount++;
          if (!sheet.krColumn || !sheet.transColumn) {
            logger.warning("Validation failed - missing column letters", {
              filename: fileData.fileName,
              sheet: sheet.name
            });
            showStatus('Please enter both column letters for selected sheets', 'error');
            return;
          }
          if (!/^[A-Za-z]+$/.test(sheet.krColumn) || !/^[A-Za-z]+$/.test(sheet.transColumn)) {
            logger.warning("Validation failed - invalid column letter", {
              filename: fileData.fileName,
              sheet: sheet.name,
              krColumn: sheet.krColumn,
              transColumn: sheet.transColumn
            });
            showStatus('Invalid column letter', 'error');
            return;
          }
        }
      }
    }

    if (!hasSelection) {
      logger.warning("Validation failed - no sheets selected");
      showStatus('Please select at least one sheet', 'error');
      return;
    }

    logger.info("Upload settings validated", {
      selected_sheets: selectedSheetCount
    });

    // Build selections object
    const selections = {};
    for (const fileData of uploadSettingsData) {
      const fileSelections = {};
      for (const sheet of fileData.sheets) {
        if (sheet.selected) {
          fileSelections[sheet.name] = {
            kr_column: sheet.krColumn.toUpperCase(),
            trans_column: sheet.transColumn.toUpperCase()
          };
        }
      }
      if (Object.keys(fileSelections).length > 0) {
        selections[fileData.fileName] = fileSelections;  // Use fileName for both modes
      }
    }

    // Close modal
    closeUploadSettings();

    // FACTOR: Create tracker for this operation
    const operationName = uploadSettingsOperationType === 'create_dictionary' ? 'Create Dictionary' :
                          uploadSettingsOperationType === 'translate_excel' ? 'Translate Excel' :
                          uploadSettingsOperationType;
    const tracker = createTracker('XLSTransfer', operationName);
    tracker.start();

    // Execute the operation
    const startTime = performance.now();
    isProcessing = true;
    stopProcessing = false;
    statusMessage = `Processing ${uploadSettingsOperationType}...`;
    tracker.update(10, `Processing ${uploadSettingsOperationType}...`);

    try {
      let result;

      if (isElectron) {
        // Electron mode: Execute Python script via IPC
        logger.info("Executing operation via Python script (Electron)", {
          operation_type: uploadSettingsOperationType,
          files_count: Object.keys(selections).length,
          threshold: threshold
        });

        tracker.update(20, 'Preparing file selections...');

        // For Electron, build selections with full file paths
        const electronSelections = {};
        for (const fileData of uploadSettingsData) {
          const fileSelections = {};
          for (const sheet of fileData.sheets) {
            if (sheet.selected) {
              fileSelections[sheet.name] = {
                kr_column: sheet.krColumn.toUpperCase(),
                trans_column: sheet.transColumn.toUpperCase()
              };
            }
          }
          if (Object.keys(fileSelections).length > 0) {
            electronSelections[fileData.filePath] = fileSelections;  // Use full path for Electron
          }
        }

        tracker.update(30, 'Executing Python script...');

        // FACTOR: Progress handler for Python stderr
        const progressHandler = (data) => {
          if (data.type === 'stderr' && data.data) {
            const parsed = parseProgress(data.data);
            if (parsed && parsed.message) {
              statusMessage = parsed.message;
              tracker.update(parsed.progress || 50, parsed.message);
            }
          }
        };
        window.electron.onPythonOutput(progressHandler);

        result = await window.electron.executePython({
          scriptPath: `${pythonToolsPath}/xlstransfer/process_operation.py`,
          args: [uploadSettingsOperationType, JSON.stringify(electronSelections), threshold]
        });

        window.electron.offPythonOutput(progressHandler);
      } else {
        // Browser mode: Call API
        logger.info("Executing operation via API (Browser)", {
          operation_type: uploadSettingsOperationType,
          files_count: Object.keys(selections).length,
          threshold: threshold
        });

        // Collect File objects
        const files = uploadSettingsData.map(fd => fd.fileObject).filter(f => f !== null);

        if (uploadSettingsOperationType === 'create_dictionary') {
          result = await api.xlsTransferCreateDictionary(files, selections);
        } else if (uploadSettingsOperationType === 'translate_excel') {
          // Call translate-excel endpoint with selections
          logger.info("Calling translate-excel API with selections", {
            files_count: files.length,
            threshold: threshold
          });

          const apiResult = await api.xlsTransferTranslateExcel(files, selections, threshold);

          // Check if async operation
          if (apiResult.async) {
            // Background operation - show processing status
            logger.info("Async operation started", {
              operation_id: apiResult.operation_id,
              operation_name: apiResult.operation_name
            });

            showStatus('Translation started - processing in background...', 'info');

            // Listen for WebSocket completion
            const unsubscribe = websocket.on('operation_complete', async (data) => {
              if (data.operation_id === apiResult.operation_id) {
                logger.success("Operation completed via WebSocket", {
                  operation_id: data.operation_id
                });

                // Stop listening
                unsubscribe();

                // Download file from download endpoint
                try {
                  const token = localStorage.getItem('auth_token');
                  const downloadResponse = await fetch(
                    `${API_BASE}/api/download/operation/${data.operation_id}`,
                    {
                      headers: { 'Authorization': `Bearer ${token}` }
                    }
                  );

                  if (downloadResponse.ok) {
                    const blob = await downloadResponse.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = files[0].name.replace('.xlsx', '_translated.xlsx');
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    logger.success("File downloaded successfully", {
                      filename: a.download
                    });

                    showStatus('Translation completed and file downloaded!', 'success');
                  } else {
                    throw new Error(`Download failed: ${downloadResponse.status}`);
                  }
                } catch (downloadError) {
                  logger.error("File download failed", {
                    error: downloadError.message
                  });
                  showStatus('Translation completed but download failed', 'error');
                }
              }
            });

            // Return early - don't show success yet
            return;
          }

          // Sync operation - download immediately (blob returned)
          const url = window.URL.createObjectURL(apiResult);
          const a = document.createElement('a');
          a.href = url;
          a.download = files[0].name.replace('.xlsx', '_translated.xlsx');
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);

          result = {
            success: true,
            message: 'Excel file translated and downloaded successfully'
          };

          logger.success("Excel translation completed and file downloaded", {
            filename: a.download
          });
        } else {
          // For other operations, we'd need additional API endpoints
          throw new Error(`Browser mode not yet implemented for ${uploadSettingsOperationType}`);
        }
      }

      const elapsed = performance.now() - startTime;

      if (result.success) {
        logger.success("Operation completed successfully", {
          operation_type: uploadSettingsOperationType,
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationSuccess('XLSTransfer', uploadSettingsOperationType, startTime, {
          mode: isElectron ? 'electron' : 'browser',
          files_count: Object.keys(selections).length
        });

        // Auto-open output folder in Electron mode
        if (isElectron && result.output_dir) {
          logger.info("Auto-opening output folder", { output_dir: result.output_dir });
          window.electron.showItemInFolder(result.output_dir);
        }

        // FACTOR: Complete with appropriate success message
        if (uploadSettingsOperationType === 'create_dictionary') {
          const successMsg = 'Dictionary created! You can now click "Load dictionary" to use it.';
          logger.info("Dictionary created - ready for loading");
          showStatus(successMsg, 'success');
          tracker.complete(successMsg);
        } else if (uploadSettingsOperationType === 'translate_excel') {
          const successMsg = 'Excel file translated and downloaded successfully!';
          showStatus(successMsg, 'success');
          tracker.complete(successMsg);
        } else {
          const successMsg = `${uploadSettingsOperationType} completed successfully!`;
          showStatus(successMsg, 'success');
          tracker.complete(successMsg);
        }
      } else {
        logger.error("Operation failed", {
          operation_type: uploadSettingsOperationType,
          error: result.error,
          elapsed_ms: elapsed.toFixed(2)
        });
        telemetry.trackOperationError('XLSTransfer', uploadSettingsOperationType, startTime,
          new Error(result.error || 'Operation failed'), {
            mode: isElectron ? 'electron' : 'browser',
            files_count: Object.keys(selections).length
          });
        const errorMsg = result.error || 'Operation failed';
        showStatus(errorMsg, 'error');
        tracker.fail(errorMsg);
      }
    } catch (error) {
      const elapsed = performance.now() - startTime;
      logger.error("Operation execution error", {
        operation_type: uploadSettingsOperationType,
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });
      telemetry.trackOperationError('XLSTransfer', uploadSettingsOperationType, startTime, error, {
        mode: isElectron ? 'electron' : 'browser'
      });
      showStatus(error.message, 'error');
      tracker.fail(error.message);
    } finally {
      isProcessing = false;
    }
  }
</script>

<div class="xlstransfer-container">
  <div class="header">
    <h1>XLS Transfer - by Neil (ver. 0225)</h1>
  </div>

  <!-- Hidden file inputs for browser mode -->
  <input
    type="file"
    bind:this={fileInputCreateDict}
    on:change={handleCreateDictFiles}
    accept=".xlsx,.xls"
    multiple
    style="display: none;"
  />
  <input
    type="file"
    bind:this={fileInputTransferClose}
    on:change={handleTransferCloseFile}
    accept=".txt"
    style="display: none;"
  />
  <input
    type="file"
    bind:this={fileInputTransferExcel}
    on:change={handleTransferExcelFile}
    accept=".xlsx,.xls"
    style="display: none;"
  />

  <div class="button-frame">
    <!-- Button 1: Create dictionary -->
    <Button on:click={createDictionary} kind="secondary" size="default">
      Create dictionary
    </Button>

    <!-- Button 2: Load dictionary -->
    <Button
      on:click={loadDictionary}
      kind="secondary"
      size="default"
      class={isDictionaryLoaded ? 'loaded' : ''}
    >
      Load dictionary
    </Button>

    <!-- Button 3: Transfer to Close (initially disabled) -->
    <Button
      on:click={transferToClose}
      kind="secondary"
      size="default"
      disabled={!isTransferEnabled}
    >
      Transfer to Close
    </Button>

    <!-- Threshold entry with Korean label -->
    <div class="threshold-container">
      <label for="threshold">최소 일치율</label>
      <TextInput
        id="threshold"
        bind:value={threshold}
        size="sm"
        placeholder="0.99"
      />
    </div>

    <!-- Button 4: STOP -->
    <Button on:click={stopProcessingFunction} kind="danger" size="default">
      STOP
    </Button>

    <!-- Button 5: Transfer to Excel (initially disabled) -->
    <Button
      on:click={transferToExcel}
      kind="secondary"
      size="default"
      disabled={!isTransferEnabled}
    >
      Transfer to Excel
    </Button>

    <!-- Button 6: Check Newlines -->
    <Button on:click={checkNewlines} kind="secondary" size="default">
      Check Newlines
    </Button>

    <!-- Button 7: Combine Excel Files -->
    <Button on:click={combineExcelFiles} kind="secondary" size="default">
      Combine Excel Files
    </Button>

    <!-- Button 8: Newline Auto Adapt -->
    <Button on:click={newlineAutoAdapt} kind="secondary" size="default">
      Newline Auto Adapt
    </Button>

    <!-- Button 9: Simple Excel Transfer -->
    <Button on:click={simpleExcelTransfer} kind="secondary" size="default">
      Simple Excel Transfer
    </Button>
  </div>

  <!-- Upload Settings Modal -->
  <Modal
    bind:open={showUploadSettings}
    modalHeading="Upload Settings"
    primaryButtonText="OK"
    secondaryButtonText="Cancel"
    on:click:button--secondary={closeUploadSettings}
    on:click:button--primary={executeUploadSettings}
    size="lg"
  >
    <div class="upload-settings">
      {#each uploadSettingsData as fileData}
        <div class="file-section">
          <h3>{fileData.fileName}</h3>
          {#each fileData.sheets as sheet}
            <div class="sheet-row">
              <Checkbox
                bind:checked={sheet.selected}
                labelText={sheet.name}
              />
              {#if sheet.selected}
                <div class="column-inputs">
                  <TextInput
                    bind:value={sheet.krColumn}
                    size="sm"
                    placeholder="A"
                    labelText="KR Column"
                  />
                  <TextInput
                    bind:value={sheet.transColumn}
                    size="sm"
                    placeholder="B"
                    labelText="Translation Column"
                  />
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/each}
    </div>
  </Modal>

  <!-- Status Notifications -->
  {#if isProcessing}
    <div class="status-container">
      <InlineLoading description={statusMessage} />
    </div>
  {/if}

  {#if showNotification}
    <div class="notification-container">
      <ToastNotification
        kind={notificationType}
        title={notificationType === 'success' ? 'Success' : notificationType === 'error' ? 'Error' : notificationType === 'info' ? 'Info' : 'Warning'}
        subtitle={statusMessage}
        timeout={5000}
        on:close={() => showNotification = false}
      />
    </div>
  {/if}
</div>

<style>
  .xlstransfer-container {
    padding: 2rem;
    height: 100%;
    max-width: 600px;
    margin: 0 auto;
  }

  .header {
    margin-bottom: 2rem;
    text-align: center;
  }

  .header h1 {
    font-size: 1.5rem;
    color: var(--cds-text-01);
  }

  .button-frame {
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }

  .button-frame :global(.bx--btn) {
    width: 100%;
    justify-content: center;
  }

  .button-frame :global(.bx--btn.loaded) {
    background-color: green;
  }

  .threshold-container {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
  }

  .threshold-container label {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .threshold-container :global(.bx--text-input) {
    max-width: 100px;
  }

  .upload-settings {
    max-height: 60vh;
    overflow-y: auto;
  }

  .file-section {
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .file-section h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
    color: var(--cds-text-01);
  }

  .sheet-row {
    margin-bottom: 1rem;
  }

  .column-inputs {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: 2rem;
    margin-top: 0.5rem;
  }

  .column-inputs :global(.bx--label) {
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .column-inputs :global(.bx--text-input) {
    max-width: 60px;
  }

  .status-container {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: var(--cds-ui-01);
    padding: 1rem 1.5rem;
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
    z-index: 9999;
  }

  .notification-container {
    position: fixed;
    top: 4rem;
    right: 1rem;
    z-index: 10000;
    max-width: 400px;
  }
</style>
