<script>
  import {
    Button,
    TextInput,
    TextArea,
    Modal,
    Select,
    SelectItem,
    RadioButtonGroup,
    RadioButton,
    DataTable,
    Toolbar,
    ToolbarContent,
    ToolbarSearch,
    Pagination,
    InlineLoading,
    ToastNotification,
    FileUploader,
    Tile,
    Toggle,
    Tabs,
    Tab,
    TabContent,
    Accordion,
    AccordionItem,
    NumberInput,
    Checkbox,
    ProgressBar
  } from "carbon-components-svelte";
  import { Upload, Search, FolderOpen, View, ViewOff, DocumentExport, CheckmarkOutline, WarningAlt, CharacterPatterns, StringInteger } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { api } from "$lib/api/client.js";
  import { telemetry } from "$lib/utils/telemetry.js";

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  }

  // Games and Languages (from original QuickSearch)
  const GAMES = ['BDO', 'BDM', 'BDC', 'CD'];
  const LANGUAGES = ['DE', 'IT', 'PL', 'EN', 'ES', 'SP', 'FR', 'ID', 'JP', 'PT', 'RU', 'TR', 'TH', 'TW', 'CH'];

  // State
  let currentDictionary = null; // {game, language, pairs_count}
  let referenceDictionary = null; // {game, language}
  let referenceEnabled = false;
  let availableDictionaries = [];

  // Modal states
  let showCreateDictionaryModal = false;
  let showLoadDictionaryModal = false;
  let showSetReferenceModal = false;

  // Create Dictionary form
  let createGame = 'BDO';
  let createLanguage = 'EN';
  let createFiles = [];
  let sourceMode = 'files'; // 'files' or 'folder'
  let selectedFolderPath = '';
  let folderFilesCount = 0;

  // Load Dictionary form
  let loadGame = 'BDO';
  let loadLanguage = 'EN';

  // Reference Dictionary form
  let refGame = 'BDO';
  let refLanguage = 'EN';

  // Search
  let searchQuery = '';
  let matchType = 'contains'; // 'contains' or 'exact'
  let searchMode = 'one-line'; // 'one-line' or 'multi-line'
  let searchResults = [];
  let totalResults = 0;
  let currentPage = 1;
  let pageSize = 50;
  let isSearching = false;

  // Status
  let statusMessage = '';
  let showNotification = false;
  let notificationType = 'success';

  // Processing states
  let isCreatingDictionary = false;
  let isLoadingDictionary = false;
  let isLoadingReference = false;

  // Tab state
  let activeTab = 0;

  // ============================================================================
  // QA TOOLS STATE
  // ============================================================================

  // QA Tool Files
  let qaFiles = [];
  let qaGlossaryFiles = [];

  // Extract Glossary options
  let qaFilterSentences = true;
  let qaGlossaryLengthThreshold = 15;
  let qaMinOccurrence = 2;
  let qaSortMethod = 'alphabetical';

  // Line Check options
  let qaLineCheckFilterSentences = true;
  let qaLineCheckThreshold = 15;

  // Term Check options
  let qaTermCheckFilterSentences = true;
  let qaTermCheckThreshold = 15;
  let qaMaxIssuesPerTerm = 6;

  // Character Count options
  let qaSymbolSet = 'BDO';
  let qaCustomSymbols = '';

  // QA Processing states
  let qaIsProcessing = false;
  let qaProgress = 0;
  let qaProgressMessage = '';
  let qaCurrentOperation = null;

  // QA Results
  let qaGlossaryResults = null;
  let qaLineCheckResults = null;
  let qaTermCheckResults = null;
  let qaPatternCheckResults = null;
  let qaCharCountResults = null;

  function showStatus(message, type = 'success') {
    statusMessage = message;
    notificationType = type;
    showNotification = true;
    setTimeout(() => { showNotification = false; }, 5000);
    logger.info(`Status: ${message}`, { type });
  }

  onMount(async () => {
    logger.component("QuickSearch", "mounted");
    await loadAvailableDictionaries();
  });

  // ========================================================================
  // API CALLS
  // ========================================================================

  // Check if running in Electron
  const isElectron = typeof window !== 'undefined' && window.electron;

  async function selectFolder() {
    if (!isElectron) {
      showStatus('Folder selection requires Electron desktop app', 'error');
      return;
    }

    try {
      const folderPath = await window.electron.selectFolder({
        title: 'Select Folder Containing XML/TXT Files'
      });

      if (!folderPath) {
        logger.info('Folder selection cancelled');
        return;
      }

      selectedFolderPath = folderPath;
      logger.info('Folder selected', { folderPath });

      // Collect files from folder
      const result = await window.electron.collectFolderFiles({
        folderPath,
        extensions: ['.xml', '.txt', '.tsv']
      });

      if (result.success) {
        folderFilesCount = result.files.length;
        // Convert base64 files to File objects for upload
        createFiles = result.files.map(f => {
          const binaryStr = atob(f.content);
          const bytes = new Uint8Array(binaryStr.length);
          for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
          }
          return new File([bytes], f.name, { type: 'application/octet-stream' });
        });
        logger.success(`Found ${folderFilesCount} files in folder`);
        showStatus(`Found ${folderFilesCount} XML/TXT/TSV files in folder`, 'success');
      } else {
        showStatus(`Error: ${result.error}`, 'error');
      }
    } catch (error) {
      logger.error('Folder selection failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    }
  }

  async function loadAvailableDictionaries() {
    try {
      // Note: This endpoint requires authentication
      const response = await fetch(`${API_BASE}/api/v2/quicksearch/list-dictionaries`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        if (response.status === 403) {
          logger.warning("Authentication required for list-dictionaries");
          availableDictionaries = [];
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      availableDictionaries = data.dictionaries || [];
      logger.info(`Loaded ${availableDictionaries.length} available dictionaries`);
    } catch (error) {
      logger.error("Failed to load available dictionaries", { error: error.message });
    }
  }

  async function createDictionary() {
    if (createFiles.length === 0) {
      showStatus('Please select files to upload', 'error');
      return;
    }

    isCreatingDictionary = true;
    const startTime = Date.now();
    logger.userAction("Creating dictionary", { game: createGame, language: createLanguage, files: createFiles.length });

    try {
      const formData = new FormData();
      for (const file of createFiles) {
        formData.append('files', file);
      }
      formData.append('game', createGame);
      formData.append('language', createLanguage);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/create-dictionary`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        showStatus(`Dictionary creation started: ${createGame}-${createLanguage}`, 'success');
        telemetry.trackOperationSuccess('QuickSearch', 'create_dictionary', startTime, {
          game: createGame,
          language: createLanguage,
          files_count: createFiles.length
        });
        showCreateDictionaryModal = false;
        createFiles = [];
        await loadAvailableDictionaries();
      } else {
        throw new Error(data.detail || 'Failed to create dictionary');
      }
    } catch (error) {
      logger.error("Dictionary creation failed", { error: error.message });
      telemetry.trackOperationError('QuickSearch', 'create_dictionary', startTime, error, {
        game: createGame,
        language: createLanguage
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isCreatingDictionary = false;
    }
  }

  async function loadDictionary() {
    isLoadingDictionary = true;
    const startTime = Date.now();
    logger.userAction("Loading dictionary", { game: loadGame, language: loadLanguage });

    try {
      const formData = new FormData();
      formData.append('game', loadGame);
      formData.append('language', loadLanguage);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/load-dictionary`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        currentDictionary = {
          game: loadGame,
          language: loadLanguage,
          pairs_count: data.pairs_count,
          creation_date: data.creation_date
        };
        telemetry.trackOperationSuccess('QuickSearch', 'load_dictionary', startTime, {
          game: loadGame,
          language: loadLanguage,
          pairs_count: data.pairs_count
        });
        showStatus(`Dictionary loaded: ${loadGame}-${loadLanguage} (${data.pairs_count} pairs)`, 'success');
        showLoadDictionaryModal = false;
      } else {
        throw new Error(data.detail || 'Failed to load dictionary');
      }
    } catch (error) {
      logger.error("Dictionary load failed", { error: error.message });
      telemetry.trackOperationError('QuickSearch', 'load_dictionary', startTime, error, {
        game: loadGame,
        language: loadLanguage
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isLoadingDictionary = false;
    }
  }

  async function setReference() {
    isLoadingReference = true;
    const startTime = Date.now();
    logger.userAction("Setting reference dictionary", { game: refGame, language: refLanguage });

    try {
      const formData = new FormData();
      formData.append('game', refGame);
      formData.append('language', refLanguage);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/set-reference`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        referenceDictionary = { game: refGame, language: refLanguage };
        referenceEnabled = true;
        telemetry.trackOperationSuccess('QuickSearch', 'set_reference', startTime, {
          game: refGame,
          language: refLanguage
        });
        showStatus(`Reference loaded: ${refGame}-${refLanguage}`, 'success');
        showSetReferenceModal = false;

        // Also toggle reference on
        await toggleReference(true);
      } else {
        throw new Error(data.detail || 'Failed to set reference');
      }
    } catch (error) {
      logger.error("Reference load failed", { error: error.message });
      telemetry.trackOperationError('QuickSearch', 'set_reference', startTime, error, {
        game: refGame,
        language: refLanguage
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isLoadingReference = false;
    }
  }

  async function toggleReference(enabled) {
    try {
      const formData = new FormData();
      formData.append('enabled', enabled);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/toggle-reference`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        referenceEnabled = enabled;
        logger.info(`Reference ${enabled ? 'enabled' : 'disabled'}`);

        // Re-run search if we have results
        if (searchResults.length > 0) {
          await performSearch();
        }
      } else {
        throw new Error(data.detail || 'Failed to toggle reference');
      }
    } catch (error) {
      logger.error("Toggle reference failed", { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    }
  }

  async function performSearch() {
    if (!searchQuery.trim()) {
      showStatus('Please enter a search query', 'error');
      return;
    }

    if (!currentDictionary) {
      showStatus('Please load a dictionary first', 'error');
      return;
    }

    isSearching = true;
    const startTime = Date.now();
    logger.userAction("Performing search", { query: searchQuery, match_type: matchType, mode: searchMode });

    try {
      const formData = new FormData();
      const startIndex = (currentPage - 1) * pageSize;

      if (searchMode === 'one-line') {
        formData.append('query', searchQuery);
        formData.append('match_type', matchType);
        formData.append('start_index', startIndex);
        formData.append('limit', pageSize);

        const response = await fetch(`${API_BASE}/api/v2/quicksearch/search`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });

        const data = await response.json();

        if (response.ok) {
          searchResults = data.results || [];
          totalResults = data.total_count || 0;
          telemetry.trackOperationSuccess('QuickSearch', 'search', startTime, {
            mode: 'one-line',
            match_type: matchType,
            results_count: totalResults
          });
          logger.info(`Search completed: ${totalResults} results found`);
        } else {
          throw new Error(data.detail || 'Search failed');
        }
      } else {
        // Multi-line search
        const queries = searchQuery.split('\n').filter(q => q.trim());
        formData.append('queries', JSON.stringify(queries));
        formData.append('match_type', matchType);
        formData.append('limit', pageSize);

        const response = await fetch(`${API_BASE}/api/v2/quicksearch/search-multiline`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });

        const data = await response.json();

        if (response.ok) {
          // Flatten multi-line results
          searchResults = [];
          for (const item of data.results || []) {
            for (const match of item.matches) {
              searchResults.push({
                ...match,
                query_line: item.line
              });
            }
          }
          totalResults = searchResults.length;
          telemetry.trackOperationSuccess('QuickSearch', 'search', startTime, {
            mode: 'multi-line',
            match_type: matchType,
            queries_count: queries.length,
            results_count: totalResults
          });
          logger.info(`Multi-line search completed: ${totalResults} total matches`);
        } else {
          throw new Error(data.detail || 'Multi-line search failed');
        }
      }
    } catch (error) {
      logger.error("Search failed", { error: error.message });
      telemetry.trackOperationError('QuickSearch', 'search', startTime, error, {
        mode: searchMode,
        match_type: matchType
      });
      showStatus(`Search error: ${error.message}`, 'error');
    } finally {
      isSearching = false;
    }
  }

  // DataTable headers
  $: headers = referenceEnabled
    ? [
        { key: 'korean', value: 'Korean' },
        { key: 'translation', value: 'Translation' },
        { key: 'reference', value: 'Reference' },
        { key: 'string_id', value: 'String ID' }
      ]
    : [
        { key: 'korean', value: 'Korean' },
        { key: 'translation', value: 'Translation' },
        { key: 'string_id', value: 'String ID' }
      ];

  // DataTable rows
  $: rows = searchResults.map((result, index) => ({
    id: index.toString(),
    ...result
  }));

  // Pagination
  $: totalPages = Math.ceil(totalResults / pageSize);

  function handlePageChange(event) {
    currentPage = event.detail.page;
    performSearch();
  }

  // ============================================================================
  // QA TOOLS FUNCTIONS
  // ============================================================================

  async function pollOperationStatus(operationId) {
    const maxAttempts = 120; // 2 minutes max
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      try {
        const response = await fetch(`${API_BASE}/api/progress/operations/${operationId}`, {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const status = await response.json();
          qaProgress = status.progress || 0;
          qaProgressMessage = status.message || 'Processing...';

          if (status.status === 'completed') {
            return { success: true, result: status.result };
          } else if (status.status === 'failed') {
            return { success: false, error: status.error_message || 'Operation failed' };
          }
        }
      } catch (e) {
        logger.error('Error polling operation', { error: e.message });
      }
    }
    return { success: false, error: 'Operation timed out' };
  }

  async function runQAExtractGlossary() {
    if (qaFiles.length === 0) {
      showStatus('Please select files first', 'error');
      return;
    }

    qaIsProcessing = true;
    qaCurrentOperation = 'extract-glossary';
    qaProgress = 0;
    qaProgressMessage = 'Starting glossary extraction...';
    qaGlossaryResults = null;

    try {
      const formData = new FormData();
      for (const file of qaFiles) {
        formData.append('files', file);
      }
      formData.append('filter_sentences', qaFilterSentences);
      formData.append('glossary_length_threshold', qaGlossaryLengthThreshold);
      formData.append('min_occurrence', qaMinOccurrence);
      formData.append('sort_method', qaSortMethod);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/qa/extract-glossary`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.operation_id) {
        const result = await pollOperationStatus(data.operation_id);
        if (result.success) {
          qaGlossaryResults = result.result;
          showStatus(`Extracted ${qaGlossaryResults.total_terms} glossary terms`, 'success');
          logger.info('Glossary extraction complete', { terms: qaGlossaryResults.total_terms });
        } else {
          showStatus(result.error, 'error');
        }
      } else {
        showStatus(data.detail || 'Failed to start extraction', 'error');
      }
    } catch (error) {
      logger.error('Glossary extraction failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      qaIsProcessing = false;
      qaCurrentOperation = null;
    }
  }

  async function runQALineCheck() {
    if (qaFiles.length === 0) {
      showStatus('Please select files first', 'error');
      return;
    }

    qaIsProcessing = true;
    qaCurrentOperation = 'line-check';
    qaProgress = 0;
    qaProgressMessage = 'Starting line check...';
    qaLineCheckResults = null;

    try {
      const formData = new FormData();
      for (const file of qaFiles) {
        formData.append('files', file);
      }
      if (qaGlossaryFiles.length > 0) {
        for (const file of qaGlossaryFiles) {
          formData.append('glossary_files', file);
        }
      }
      formData.append('filter_sentences', qaLineCheckFilterSentences);
      formData.append('glossary_length_threshold', qaLineCheckThreshold);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/qa/line-check`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.operation_id) {
        const result = await pollOperationStatus(data.operation_id);
        if (result.success) {
          qaLineCheckResults = result.result;
          showStatus(`Found ${qaLineCheckResults.inconsistent_count} inconsistent entries`, 'success');
        } else {
          showStatus(result.error, 'error');
        }
      } else {
        showStatus(data.detail || 'Failed to start line check', 'error');
      }
    } catch (error) {
      logger.error('Line check failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      qaIsProcessing = false;
      qaCurrentOperation = null;
    }
  }

  async function runQATermCheck() {
    if (qaFiles.length === 0) {
      showStatus('Please select files first', 'error');
      return;
    }

    qaIsProcessing = true;
    qaCurrentOperation = 'term-check';
    qaProgress = 0;
    qaProgressMessage = 'Starting term check...';
    qaTermCheckResults = null;

    try {
      const formData = new FormData();
      for (const file of qaFiles) {
        formData.append('files', file);
      }
      if (qaGlossaryFiles.length > 0) {
        for (const file of qaGlossaryFiles) {
          formData.append('glossary_files', file);
        }
      }
      formData.append('filter_sentences', qaTermCheckFilterSentences);
      formData.append('glossary_length_threshold', qaTermCheckThreshold);
      formData.append('max_issues_per_term', qaMaxIssuesPerTerm);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/qa/term-check`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.operation_id) {
        const result = await pollOperationStatus(data.operation_id);
        if (result.success) {
          qaTermCheckResults = result.result;
          showStatus(`Found ${qaTermCheckResults.issues_count} terms with missing translations`, 'success');
        } else {
          showStatus(result.error, 'error');
        }
      } else {
        showStatus(data.detail || 'Failed to start term check', 'error');
      }
    } catch (error) {
      logger.error('Term check failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      qaIsProcessing = false;
      qaCurrentOperation = null;
    }
  }

  async function runQAPatternCheck() {
    if (qaFiles.length === 0) {
      showStatus('Please select files first', 'error');
      return;
    }

    qaIsProcessing = true;
    qaCurrentOperation = 'pattern-check';
    qaProgress = 0;
    qaProgressMessage = 'Starting pattern check...';
    qaPatternCheckResults = null;

    try {
      const formData = new FormData();
      for (const file of qaFiles) {
        formData.append('files', file);
      }

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/qa/pattern-check`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.operation_id) {
        const result = await pollOperationStatus(data.operation_id);
        if (result.success) {
          qaPatternCheckResults = result.result;
          showStatus(`Found ${qaPatternCheckResults.mismatch_count} pattern mismatches`, 'success');
        } else {
          showStatus(result.error, 'error');
        }
      } else {
        showStatus(data.detail || 'Failed to start pattern check', 'error');
      }
    } catch (error) {
      logger.error('Pattern check failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      qaIsProcessing = false;
      qaCurrentOperation = null;
    }
  }

  async function runQACharacterCount() {
    if (qaFiles.length === 0) {
      showStatus('Please select files first', 'error');
      return;
    }

    qaIsProcessing = true;
    qaCurrentOperation = 'character-count';
    qaProgress = 0;
    qaProgressMessage = 'Starting character count check...';
    qaCharCountResults = null;

    try {
      const formData = new FormData();
      for (const file of qaFiles) {
        formData.append('files', file);
      }
      formData.append('symbol_set', qaSymbolSet);
      if (qaCustomSymbols.trim()) {
        formData.append('custom_symbols', qaCustomSymbols.trim());
      }

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/qa/character-count`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.operation_id) {
        const result = await pollOperationStatus(data.operation_id);
        if (result.success) {
          qaCharCountResults = result.result;
          showStatus(`Found ${qaCharCountResults.mismatch_count} character count mismatches`, 'success');
        } else {
          showStatus(result.error, 'error');
        }
      } else {
        showStatus(data.detail || 'Failed to start character count check', 'error');
      }
    } catch (error) {
      logger.error('Character count check failed', { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      qaIsProcessing = false;
      qaCurrentOperation = null;
    }
  }

  function clearQAResults() {
    qaGlossaryResults = null;
    qaLineCheckResults = null;
    qaTermCheckResults = null;
    qaPatternCheckResults = null;
    qaCharCountResults = null;
    qaFiles = [];
    qaGlossaryFiles = [];
  }

  function exportQAResults(type) {
    let data = null;
    let filename = '';

    switch (type) {
      case 'glossary':
        if (!qaGlossaryResults) return;
        data = qaGlossaryResults.glossary.map(g => `${g.korean}\t${g.translation}\t${g.occurrence_count}`).join('\n');
        filename = 'glossary_export.txt';
        break;
      case 'line-check':
        if (!qaLineCheckResults) return;
        data = qaLineCheckResults.inconsistent_entries.map(e =>
          `${e.source}\n${e.translations.map(t => `  -> ${t.translation} (${t.files.join(', ')})`).join('\n')}`
        ).join('\n\n');
        filename = 'line_check_export.txt';
        break;
      case 'term-check':
        if (!qaTermCheckResults) return;
        data = qaTermCheckResults.issues.map(i =>
          `[${i.korean_term}] Expected: ${i.expected_translation}\n${i.issues.map(iss => `  - ${iss.source} -> ${iss.translation}`).join('\n')}`
        ).join('\n\n');
        filename = 'term_check_export.txt';
        break;
      case 'pattern-check':
        if (!qaPatternCheckResults) return;
        data = qaPatternCheckResults.mismatches.map(m =>
          `Source: ${m.source}\nTranslation: ${m.translation}\nSource patterns: ${m.source_patterns.join(', ')}\nTrans patterns: ${m.translation_patterns.join(', ')}`
        ).join('\n\n');
        filename = 'pattern_check_export.txt';
        break;
      case 'char-count':
        if (!qaCharCountResults) return;
        data = qaCharCountResults.mismatches.map(m =>
          `[${m.mismatched_symbol}] Source(${m.source_count}) vs Trans(${m.translation_count})\n  ${m.source}\n  ${m.translation}`
        ).join('\n\n');
        filename = 'char_count_export.txt';
        break;
    }

    if (data) {
      const blob = new Blob([data], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      showStatus(`Exported ${filename}`, 'success');
    }
  }
</script>

<div class="quicksearch-container">
  <!-- Notification -->
  {#if showNotification}
    <div class="notification-container">
      <ToastNotification
        kind={notificationType}
        title={notificationType === 'success' ? 'Success' : 'Error'}
        subtitle={statusMessage}
        timeout={5000}
        on:close={() => showNotification = false}
      />
    </div>
  {/if}

  <!-- Header -->
  <div class="header">
    <h2>QuickSearch</h2>
    <p class="subtitle">Dictionary Search & QA Tools</p>
  </div>

  <!-- Tabs -->
  <Tabs bind:selected={activeTab}>
    <Tab label="Dictionary Search" />
    <Tab label="Glossary Checker" />
    <svelte:fragment slot="content">
      <!-- Tab 1: Dictionary Search -->
      <TabContent>
        <!-- Action Buttons -->
  <div class="action-buttons">
    <Button
      kind="primary"
      icon={Upload}
      on:click={() => showCreateDictionaryModal = true}
    >
      Create Dictionary
    </Button>

    <Button
      kind="secondary"
      icon={FolderOpen}
      on:click={() => showLoadDictionaryModal = true}
    >
      Load Dictionary
    </Button>

    {#if currentDictionary}
      <Button
        kind="tertiary"
        icon={FolderOpen}
        on:click={() => showSetReferenceModal = true}
      >
        Set Reference
      </Button>

      {#if referenceDictionary}
        <Toggle
          labelText={referenceEnabled ? "Reference: ON" : "Reference: OFF"}
          toggled={referenceEnabled}
          on:toggle={(e) => toggleReference(e.detail.toggled)}
        />
      {/if}
    {/if}
  </div>

  <!-- Dictionary Status -->
  <div class="status-tiles">
    <Tile class="status-tile">
      <h4>Current Dictionary</h4>
      {#if currentDictionary}
        <p><strong>{currentDictionary.game}-{currentDictionary.language}</strong></p>
        <p>{currentDictionary.pairs_count} pairs</p>
        <p class="small">Created: {currentDictionary.creation_date}</p>
      {:else}
        <p class="empty">No dictionary loaded</p>
      {/if}
    </Tile>

    {#if referenceDictionary}
      <Tile class="status-tile">
        <h4>Reference Dictionary</h4>
        <p><strong>{referenceDictionary.game}-{referenceDictionary.language}</strong></p>
        <p class="small">Status: {referenceEnabled ? 'Enabled' : 'Disabled'}</p>
      </Tile>
    {/if}
  </div>

  <!-- Search Interface -->
  {#if currentDictionary}
    <div class="search-section">
      <h3>Search</h3>

      <div class="search-controls">
        <RadioButtonGroup
          legendText="Search Mode"
          bind:selected={searchMode}
        >
          <RadioButton labelText="One Line" value="one-line" />
          <RadioButton labelText="Multi Line" value="multi-line" />
        </RadioButtonGroup>

        <RadioButtonGroup
          legendText="Match Type"
          bind:selected={matchType}
        >
          <RadioButton labelText="Contains" value="contains" />
          <RadioButton labelText="Exact Match" value="exact" />
        </RadioButtonGroup>
      </div>

      {#if searchMode === 'one-line'}
        <TextInput
          labelText="Search Query"
          placeholder="Enter Korean or Translation text..."
          bind:value={searchQuery}
          on:keydown={(e) => e.key === 'Enter' && performSearch()}
        />
      {:else}
        <TextArea
          labelText="Search Queries (one per line)"
          placeholder="Enter one query per line..."
          bind:value={searchQuery}
          rows={5}
        />
      {/if}

      <div class="search-button-row">
        <Button
          kind="primary"
          icon={Search}
          disabled={isSearching || !searchQuery.trim()}
          on:click={performSearch}
        >
          {isSearching ? 'Searching...' : 'Search'}
        </Button>
      </div>
    </div>

    <!-- Results -->
    {#if searchResults.length > 0}
      <div class="results-section">
        <h3>Results ({totalResults} found)</h3>

        <DataTable
          {headers}
          {rows}
          size="short"
        >
          <svelte:fragment slot="cell" let:row let:cell>
            {#if cell.key === 'korean'}
              <div class="result-cell korean">{cell.value || ''}</div>
            {:else if cell.key === 'translation'}
              <div class="result-cell translation">{cell.value || ''}</div>
            {:else if cell.key === 'reference'}
              <div class="result-cell reference">{cell.value || '—'}</div>
            {:else if cell.key === 'string_id'}
              <div class="result-cell string-id">{cell.value || ''}</div>
            {:else}
              {cell.value}
            {/if}
          </svelte:fragment>
        </DataTable>

        {#if totalPages > 1}
          <Pagination
            bind:page={currentPage}
            totalItems={totalResults}
            pageSize={pageSize}
            pageSizes={[25, 50, 100]}
            on:update={handlePageChange}
          />
        {/if}
      </div>
    {/if}
  {/if}
      </TabContent>

      <!-- Tab 2: Glossary Checker (QA Tools) -->
      <TabContent>
        <div class="qa-tools-container">
          <div class="qa-header">
            <h3>Glossary Checker - QA Tools</h3>
            <p>Quality assurance tools for translation consistency checking</p>
          </div>

          <!-- File Selection -->
          <div class="qa-file-section">
            <div class="qa-file-upload">
              <FileUploader
                labelTitle="Source Files"
                labelDescription="Select XML, TXT, or TSV files to check"
                buttonLabel="Select Files"
                accept={['.xml', '.txt', '.tsv']}
                multiple
                bind:files={qaFiles}
              />
              {#if qaFiles.length > 0}
                <p class="file-count">{qaFiles.length} file(s) selected</p>
              {/if}
            </div>

            <div class="qa-file-upload">
              <FileUploader
                labelTitle="Glossary Files (Optional)"
                labelDescription="Custom glossary files for Line/Term check"
                buttonLabel="Select Glossary"
                accept={['.xml', '.txt', '.tsv']}
                multiple
                bind:files={qaGlossaryFiles}
              />
              {#if qaGlossaryFiles.length > 0}
                <p class="file-count">{qaGlossaryFiles.length} glossary file(s) selected</p>
              {/if}
            </div>

            <Button kind="ghost" size="small" on:click={clearQAResults}>Clear All</Button>
          </div>

          <!-- Progress Bar -->
          {#if qaIsProcessing}
            <div class="qa-progress">
              <ProgressBar value={qaProgress} max={100} labelText={qaProgressMessage} />
            </div>
          {/if}

          <!-- QA Tools Accordion -->
          <Accordion>
            <!-- Extract Glossary -->
            <AccordionItem title="Extract Glossary" open>
              <div class="qa-tool-content">
                <p class="tool-description">Build a glossary from source files. Filters short terms that appear multiple times.</p>

                <div class="qa-options">
                  <Checkbox bind:checked={qaFilterSentences} labelText="Filter sentences (skip entries ending with . ? !)" />
                  <NumberInput
                    label="Max source length"
                    bind:value={qaGlossaryLengthThreshold}
                    min={5}
                    max={50}
                    step={1}
                  />
                  <NumberInput
                    label="Min occurrence"
                    bind:value={qaMinOccurrence}
                    min={1}
                    max={10}
                    step={1}
                  />
                  <Select labelText="Sort by" bind:selected={qaSortMethod}>
                    <SelectItem value="alphabetical" text="Alphabetical" />
                    <SelectItem value="length" text="Length" />
                    <SelectItem value="frequency" text="Frequency" />
                  </Select>
                </div>

                <div class="qa-actions">
                  <Button
                    kind="primary"
                    disabled={qaIsProcessing || qaFiles.length === 0}
                    on:click={runQAExtractGlossary}
                  >
                    {qaIsProcessing && qaCurrentOperation === 'extract-glossary' ? 'Extracting...' : 'Extract Glossary'}
                  </Button>
                  {#if qaGlossaryResults}
                    <Button kind="ghost" icon={DocumentExport} on:click={() => exportQAResults('glossary')}>Export</Button>
                  {/if}
                </div>

                {#if qaGlossaryResults}
                  <div class="qa-results">
                    <h4>Results: {qaGlossaryResults.total_terms} terms extracted</h4>
                    <div class="results-table">
                      <table>
                        <thead>
                          <tr><th>Korean</th><th>Translation</th><th>Count</th></tr>
                        </thead>
                        <tbody>
                          {#each qaGlossaryResults.glossary.slice(0, 50) as item}
                            <tr>
                              <td>{item.korean}</td>
                              <td>{item.translation}</td>
                              <td>{item.occurrence_count}</td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                      {#if qaGlossaryResults.glossary.length > 50}
                        <p class="more-results">Showing 50 of {qaGlossaryResults.glossary.length} results. Export for full list.</p>
                      {/if}
                    </div>
                  </div>
                {/if}
              </div>
            </AccordionItem>

            <!-- Line Check -->
            <AccordionItem title="Line Check">
              <div class="qa-tool-content">
                <p class="tool-description">Find inconsistent translations - same source text with different translations.</p>

                <div class="qa-options">
                  <Checkbox bind:checked={qaLineCheckFilterSentences} labelText="Filter sentences" />
                  <NumberInput
                    label="Max source length"
                    bind:value={qaLineCheckThreshold}
                    min={5}
                    max={50}
                    step={1}
                  />
                </div>

                <div class="qa-actions">
                  <Button
                    kind="primary"
                    disabled={qaIsProcessing || qaFiles.length === 0}
                    on:click={runQALineCheck}
                  >
                    {qaIsProcessing && qaCurrentOperation === 'line-check' ? 'Checking...' : 'Run Line Check'}
                  </Button>
                  {#if qaLineCheckResults}
                    <Button kind="ghost" icon={DocumentExport} on:click={() => exportQAResults('line-check')}>Export</Button>
                  {/if}
                </div>

                {#if qaLineCheckResults}
                  <div class="qa-results">
                    <h4>Found {qaLineCheckResults.inconsistent_count} inconsistent entries</h4>
                    <div class="results-list">
                      {#each qaLineCheckResults.inconsistent_entries.slice(0, 20) as entry}
                        <div class="inconsistent-entry">
                          <div class="source-text">{entry.source}</div>
                          <div class="translations">
                            {#each entry.translations as trans}
                              <div class="translation-variant">
                                <span class="arrow">→</span>
                                <span class="trans-text">{trans.translation}</span>
                                <span class="files">({trans.files.join(', ')})</span>
                              </div>
                            {/each}
                          </div>
                        </div>
                      {/each}
                      {#if qaLineCheckResults.inconsistent_entries.length > 20}
                        <p class="more-results">Showing 20 of {qaLineCheckResults.inconsistent_count} results.</p>
                      {/if}
                    </div>
                  </div>
                {/if}
              </div>
            </AccordionItem>

            <!-- Term Check -->
            <AccordionItem title="Term Check">
              <div class="qa-tool-content">
                <p class="tool-description">Find glossary terms that appear in source but are missing from translation.</p>

                <div class="qa-options">
                  <Checkbox bind:checked={qaTermCheckFilterSentences} labelText="Filter sentences" />
                  <NumberInput
                    label="Max source length"
                    bind:value={qaTermCheckThreshold}
                    min={5}
                    max={50}
                    step={1}
                  />
                  <NumberInput
                    label="Max issues per term"
                    bind:value={qaMaxIssuesPerTerm}
                    min={1}
                    max={20}
                    step={1}
                  />
                </div>

                <div class="qa-actions">
                  <Button
                    kind="primary"
                    disabled={qaIsProcessing || qaFiles.length === 0}
                    on:click={runQATermCheck}
                  >
                    {qaIsProcessing && qaCurrentOperation === 'term-check' ? 'Checking...' : 'Run Term Check'}
                  </Button>
                  {#if qaTermCheckResults}
                    <Button kind="ghost" icon={DocumentExport} on:click={() => exportQAResults('term-check')}>Export</Button>
                  {/if}
                </div>

                {#if qaTermCheckResults}
                  <div class="qa-results">
                    <h4>Found {qaTermCheckResults.issues_count} terms with issues</h4>
                    <div class="results-list">
                      {#each qaTermCheckResults.issues.slice(0, 15) as issue}
                        <div class="term-issue">
                          <div class="term-header">
                            <span class="korean-term">{issue.korean_term}</span>
                            <span class="expected">Expected: {issue.expected_translation}</span>
                          </div>
                          <div class="issue-list">
                            {#each issue.issues.slice(0, 3) as iss}
                              <div class="issue-item">
                                <div class="issue-source">{iss.source}</div>
                                <div class="issue-trans">→ {iss.translation}</div>
                              </div>
                            {/each}
                            {#if issue.issues.length > 3}
                              <p class="more-issues">+{issue.issues.length - 3} more...</p>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              </div>
            </AccordionItem>

            <!-- Pattern Check -->
            <AccordionItem title="Pattern Check">
              <div class="qa-tool-content">
                <p class="tool-description">Check if {'{code}'} patterns in source match patterns in translation.</p>

                <div class="qa-actions">
                  <Button
                    kind="primary"
                    disabled={qaIsProcessing || qaFiles.length === 0}
                    on:click={runQAPatternCheck}
                  >
                    {qaIsProcessing && qaCurrentOperation === 'pattern-check' ? 'Checking...' : 'Run Pattern Check'}
                  </Button>
                  {#if qaPatternCheckResults}
                    <Button kind="ghost" icon={DocumentExport} on:click={() => exportQAResults('pattern-check')}>Export</Button>
                  {/if}
                </div>

                {#if qaPatternCheckResults}
                  <div class="qa-results">
                    <h4>Found {qaPatternCheckResults.mismatch_count} pattern mismatches</h4>
                    <div class="results-list">
                      {#each qaPatternCheckResults.mismatches.slice(0, 20) as mismatch}
                        <div class="pattern-mismatch">
                          <div class="pattern-source">
                            <strong>Source:</strong> {mismatch.source}
                            <span class="patterns">[{mismatch.source_patterns.join(', ')}]</span>
                          </div>
                          <div class="pattern-trans">
                            <strong>Trans:</strong> {mismatch.translation}
                            <span class="patterns">[{mismatch.translation_patterns.join(', ')}]</span>
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              </div>
            </AccordionItem>

            <!-- Character Count -->
            <AccordionItem title="Character Count">
              <div class="qa-tool-content">
                <p class="tool-description">Check if special character counts match between source and translation.</p>

                <div class="qa-options">
                  <Select labelText="Symbol Set" bind:selected={qaSymbolSet}>
                    <SelectItem value="BDO" text="BDO: curly braces" />
                    <SelectItem value="BDM" text="BDM: ▶ curly braces 🔗 |" />
                  </Select>
                  <TextInput
                    labelText="Custom Symbols (optional)"
                    placeholder="Enter each symbol to check"
                    bind:value={qaCustomSymbols}
                  />
                </div>

                <div class="qa-actions">
                  <Button
                    kind="primary"
                    disabled={qaIsProcessing || qaFiles.length === 0}
                    on:click={runQACharacterCount}
                  >
                    {qaIsProcessing && qaCurrentOperation === 'character-count' ? 'Checking...' : 'Run Character Count'}
                  </Button>
                  {#if qaCharCountResults}
                    <Button kind="ghost" icon={DocumentExport} on:click={() => exportQAResults('char-count')}>Export</Button>
                  {/if}
                </div>

                {#if qaCharCountResults}
                  <div class="qa-results">
                    <h4>Found {qaCharCountResults.mismatch_count} character count mismatches</h4>
                    <p class="symbols-checked">Symbols checked: {qaCharCountResults.symbols_checked.join(' ')}</p>
                    <div class="results-list">
                      {#each qaCharCountResults.mismatches.slice(0, 20) as mismatch}
                        <div class="char-mismatch">
                          <div class="mismatch-symbol">
                            <span class="symbol">{mismatch.mismatched_symbol}</span>
                            Source: {mismatch.source_count} | Trans: {mismatch.translation_count}
                          </div>
                          <div class="mismatch-source">{mismatch.source}</div>
                          <div class="mismatch-trans">→ {mismatch.translation}</div>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              </div>
            </AccordionItem>
          </Accordion>
        </div>
      </TabContent>
    </svelte:fragment>
  </Tabs>

  <!-- Create Dictionary Modal -->
  <Modal
    bind:open={showCreateDictionaryModal}
    modalHeading="Create Dictionary"
    primaryButtonText="Create"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isCreatingDictionary || createFiles.length === 0}
    on:click:button--secondary={() => { showCreateDictionaryModal = false; sourceMode = 'files'; createFiles = []; selectedFolderPath = ''; folderFilesCount = 0; }}
    on:click:button--primary={createDictionary}
  >
    <p class="modal-description">Upload XML, TXT, or TSV files to create a new dictionary.</p>

    <Select labelText="Game" bind:selected={createGame}>
      {#each GAMES as game}
        <SelectItem value={game} text={game} />
      {/each}
    </Select>

    <Select labelText="Language" bind:selected={createLanguage}>
      {#each LANGUAGES as lang}
        <SelectItem value={lang} text={lang} />
      {/each}
    </Select>

    <RadioButtonGroup
      legendText="Source Selection Mode"
      bind:selected={sourceMode}
      on:change={() => { createFiles = []; selectedFolderPath = ''; folderFilesCount = 0; }}
    >
      <RadioButton labelText="Select Files (XML/TXT)" value="files" />
      <RadioButton labelText="Select Folder (recursive)" value="folder" />
    </RadioButtonGroup>

    {#if sourceMode === 'files'}
      <FileUploader
        labelTitle="Upload files"
        labelDescription="XML, TXT, or TSV files only"
        buttonLabel="Select files"
        accept={['.xml', '.txt', '.tsv']}
        multiple
        bind:files={createFiles}
      />
    {:else}
      <div class="folder-selection">
        <Button kind="secondary" icon={FolderOpen} on:click={selectFolder}>
          Select Folder
        </Button>
        {#if selectedFolderPath}
          <p class="folder-path">{selectedFolderPath}</p>
          <p class="folder-count">{folderFilesCount} XML/TXT/TSV files found</p>
        {:else}
          <p class="folder-hint">Select a folder to recursively scan for XML, TXT, and TSV files</p>
        {/if}
      </div>
    {/if}

    {#if isCreatingDictionary}
      <InlineLoading description="Creating dictionary..." />
    {/if}
  </Modal>

  <!-- Load Dictionary Modal -->
  <Modal
    bind:open={showLoadDictionaryModal}
    modalHeading="Load Dictionary"
    primaryButtonText="Load"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isLoadingDictionary}
    on:click:button--secondary={() => showLoadDictionaryModal = false}
    on:click:button--primary={loadDictionary}
  >
    <p class="modal-description">Select a game and language to load an existing dictionary.</p>

    <Select labelText="Game" bind:selected={loadGame}>
      {#each GAMES as game}
        <SelectItem value={game} text={game} />
      {/each}
    </Select>

    <Select labelText="Language" bind:selected={loadLanguage}>
      {#each LANGUAGES as lang}
        <SelectItem value={lang} text={lang} />
      {/each}
    </Select>

    {#if availableDictionaries.length > 0}
      <div class="available-dicts">
        <p><strong>Available Dictionaries:</strong> (click to select)</p>
        <div class="dict-list">
          {#each availableDictionaries as dict}
            <button
              class="dict-item"
              class:selected={loadGame === dict.game && loadLanguage === dict.language}
              on:click={() => { loadGame = dict.game; loadLanguage = dict.language; }}
            >
              <span class="dict-name">{dict.game}-{dict.language}</span>
              <span class="dict-count">{dict.pairs_count} pairs</span>
            </button>
          {/each}
        </div>
      </div>
    {:else}
      <div class="no-dicts">
        <p>No dictionaries available. Create one first using the "Create Dictionary" button.</p>
      </div>
    {/if}

    {#if isLoadingDictionary}
      <InlineLoading description="Loading dictionary..." />
    {/if}
  </Modal>

  <!-- Set Reference Modal -->
  <Modal
    bind:open={showSetReferenceModal}
    modalHeading="Set Reference Dictionary"
    primaryButtonText="Load"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isLoadingReference}
    on:click:button--secondary={() => showSetReferenceModal = false}
    on:click:button--primary={setReference}
  >
    <p class="modal-description">Load a reference dictionary for comparison.</p>

    <Select labelText="Game" bind:selected={refGame}>
      {#each GAMES as game}
        <SelectItem value={game} text={game} />
      {/each}
    </Select>

    <Select labelText="Language" bind:selected={refLanguage}>
      {#each LANGUAGES as lang}
        <SelectItem value={lang} text={lang} />
      {/each}
    </Select>

    {#if isLoadingReference}
      <InlineLoading description="Loading reference..." />
    {/if}
  </Modal>
</div>

<style>
  .quicksearch-container {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .notification-container {
    position: fixed;
    top: 4rem;
    right: 1rem;
    z-index: 9000;
  }

  .header {
    margin-bottom: 2rem;
  }

  .header h2 {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
  }

  .subtitle {
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .action-buttons {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    align-items: center;
  }

  .status-tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .status-tiles :global(.bx--tile h4) {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin-bottom: 0.5rem;
  }

  .status-tiles :global(.bx--tile p) {
    margin: 0.25rem 0;
    color: var(--cds-text-01);
  }

  .status-tiles :global(.bx--tile .empty) {
    color: var(--cds-text-03);
    font-style: italic;
  }

  .status-tiles :global(.bx--tile .small) {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .search-section {
    background: var(--cds-ui-01);
    padding: 1.5rem;
    border-radius: 4px;
    margin-bottom: 2rem;
  }

  .search-section h3 {
    font-size: 1.25rem;
    margin-bottom: 1rem;
    color: var(--cds-text-01);
  }

  .search-controls {
    display: flex;
    gap: 2rem;
    margin-bottom: 1rem;
  }

  .search-button-row {
    margin-top: 1rem;
  }

  .results-section {
    background: var(--cds-ui-01);
    padding: 1.5rem;
    border-radius: 4px;
  }

  .results-section h3 {
    font-size: 1.25rem;
    margin-bottom: 1rem;
    color: var(--cds-text-01);
  }

  .result-cell {
    padding: 0.5rem;
    word-wrap: break-word;
  }

  .result-cell.korean {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .result-cell.translation {
    color: var(--cds-text-01);
  }

  .result-cell.reference {
    color: var(--cds-text-02);
    font-style: italic;
  }

  .result-cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .modal-description {
    margin-bottom: 1rem;
    color: var(--cds-text-02);
  }

  .available-dicts {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--cds-ui-02);
    border-radius: 4px;
  }

  .available-dicts ul {
    margin: 0.5rem 0 0 1.5rem;
    padding: 0;
  }

  .available-dicts li {
    margin: 0.25rem 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .dict-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .dict-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--cds-ui-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .dict-item:hover {
    background: var(--cds-ui-03);
    border-color: var(--cds-interactive-04);
  }

  .dict-item.selected {
    background: var(--cds-interactive-02);
    border-color: var(--cds-interactive-04);
  }

  .dict-name {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .dict-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .no-dicts {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--cds-ui-02);
    border-radius: 4px;
    text-align: center;
  }

  .no-dicts p {
    color: var(--cds-text-03);
    font-style: italic;
    margin: 0;
  }

  .folder-selection {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--cds-ui-02);
    border-radius: 4px;
  }

  .folder-path {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-01);
    word-break: break-all;
    font-family: monospace;
  }

  .folder-count {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: var(--cds-support-success);
    font-weight: 500;
  }

  .folder-hint {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  /* ============================================================================
   * QA TOOLS STYLES
   * ============================================================================ */

  .qa-tools-container {
    padding: 1rem 0;
  }

  .qa-header {
    margin-bottom: 1.5rem;
  }

  .qa-header h3 {
    font-size: 1.25rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
  }

  .qa-header p {
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .qa-file-section {
    display: flex;
    gap: 2rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 1rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
  }

  .qa-file-upload {
    flex: 1;
    min-width: 250px;
  }

  .file-count {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-support-success);
    font-weight: 500;
  }

  .qa-progress {
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
  }

  .qa-tool-content {
    padding: 0.5rem 0;
  }

  .tool-description {
    color: var(--cds-text-02);
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  .qa-options {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1rem;
    align-items: flex-end;
  }

  .qa-options :global(.bx--number) {
    max-width: 150px;
  }

  .qa-options :global(.bx--select) {
    max-width: 180px;
  }

  .qa-actions {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    align-items: center;
  }

  .qa-results {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--cds-ui-02);
    border-radius: 4px;
  }

  .qa-results h4 {
    font-size: 1rem;
    margin-bottom: 1rem;
    color: var(--cds-text-01);
  }

  .results-table {
    overflow-x: auto;
  }

  .results-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .results-table th,
  .results-table td {
    padding: 0.5rem;
    text-align: left;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .results-table th {
    font-weight: 600;
    color: var(--cds-text-01);
    background: var(--cds-ui-03);
  }

  .results-table td {
    color: var(--cds-text-02);
  }

  .more-results {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  /* Line Check Results */
  .inconsistent-entry {
    padding: 0.75rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    border-left: 3px solid var(--cds-support-warning);
  }

  .source-text {
    font-weight: 500;
    color: var(--cds-text-01);
    margin-bottom: 0.5rem;
  }

  .translations {
    margin-left: 1rem;
  }

  .translation-variant {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
    font-size: 0.875rem;
  }

  .arrow {
    color: var(--cds-text-03);
  }

  .trans-text {
    color: var(--cds-text-02);
  }

  .files {
    color: var(--cds-text-03);
    font-size: 0.75rem;
  }

  /* Term Check Results */
  .term-issue {
    padding: 0.75rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    border-left: 3px solid var(--cds-support-error);
  }

  .term-header {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }

  .korean-term {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .expected {
    color: var(--cds-support-success);
    font-size: 0.875rem;
  }

  .issue-list {
    margin-left: 1rem;
  }

  .issue-item {
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
  }

  .issue-source {
    color: var(--cds-text-02);
  }

  .issue-trans {
    color: var(--cds-text-03);
    margin-left: 1rem;
  }

  .more-issues {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  /* Pattern Check Results */
  .pattern-mismatch {
    padding: 0.75rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    border-left: 3px solid var(--cds-interactive-04);
    font-size: 0.875rem;
  }

  .pattern-source,
  .pattern-trans {
    margin-bottom: 0.25rem;
    color: var(--cds-text-02);
  }

  .patterns {
    margin-left: 0.5rem;
    color: var(--cds-interactive-04);
    font-family: monospace;
    font-size: 0.75rem;
  }

  /* Character Count Results */
  .char-mismatch {
    padding: 0.75rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    border-left: 3px solid var(--cds-support-info);
    font-size: 0.875rem;
  }

  .mismatch-symbol {
    font-weight: 500;
    color: var(--cds-text-01);
    margin-bottom: 0.5rem;
  }

  .mismatch-symbol .symbol {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    background: var(--cds-interactive-02);
    border-radius: 2px;
    margin-right: 0.5rem;
    font-family: monospace;
  }

  .mismatch-source {
    color: var(--cds-text-02);
  }

  .mismatch-trans {
    color: var(--cds-text-03);
    margin-left: 1rem;
  }

  .symbols-checked {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin-bottom: 1rem;
    font-family: monospace;
  }
</style>
