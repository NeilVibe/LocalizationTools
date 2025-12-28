<script>
  import {
    Button,
    TextInput,
    TextArea,
    Modal,
    Select,
    SelectItem,
    Slider,
    NumberInput,
    DataTable,
    Pagination,
    InlineLoading,
    ToastNotification,
    FileUploader,
    Tile,
    Toggle
  } from "carbon-components-svelte";
  import { Upload, Search, FolderOpen, TrashCan, Translate } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { telemetry } from "$lib/utils/telemetry.js";
  import { createTracker } from "$lib/utils/trackedOperation.js";
  import { serverUrl } from "$lib/stores/app.js";

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (token) {
      return { 'Authorization': `Bearer ${token}` };
    }
    return {};
  }

  // Dictionary types (from backend)
  const DICT_TYPES = ['BDO', 'BDM', 'BDC', 'CD'];

  // Svelte 5: State
  let currentDictionary = $state(null); // {dict_type, split_pairs, whole_pairs}
  let availableDictionaries = $state([]);

  // Svelte 5: Modal states
  let showCreateDictionaryModal = $state(false);
  let showLoadDictionaryModal = $state(false);
  let showExtractSimilarModal = $state(false);
  let showAutoTranslateModal = $state(false);

  // Svelte 5: Create Dictionary form
  let createDictType = $state('BDO');
  let createKrColumn = $state(5);
  let createTransColumn = $state(6);
  let createFiles = $state([]);

  // Svelte 5: Load Dictionary form
  let loadDictType = $state('BDO');

  // Svelte 5: Search form
  let searchQuery = $state('');
  let searchThreshold = $state(0.85);
  let searchTopK = $state(10);
  let searchUseWhole = $state(false);
  let searchResults = $state([]);
  let isSearching = $state(false);

  // Svelte 5: Extract Similar form
  let extractFile = $state([]);
  let extractMinCharLength = $state(50);
  let extractThreshold = $state(0.85);
  let extractFilterSameCategory = $state(true);

  // Svelte 5: Auto-Translate form
  let translateFile = $state([]);
  let translateThreshold = $state(0.85);

  // Svelte 5: Status
  let statusMessage = $state('');
  let showNotification = $state(false);
  let notificationType = $state('success');

  // Svelte 5: Processing states
  let isCreatingDictionary = $state(false);
  let isLoadingDictionary = $state(false);
  let isExtracting = $state(false);
  let isTranslating = $state(false);

  function showStatus(message, type = 'success') {
    statusMessage = message;
    notificationType = type;
    showNotification = true;
    setTimeout(() => { showNotification = false; }, 5000);
    logger.info(`Status: ${message}`, { type });
  }

  onMount(async () => {
    logger.component("KRSimilar", "mounted");
    await loadAvailableDictionaries();
  });

  // ========================================================================
  // TEST MODE - For CDP Autonomous Testing
  // ========================================================================

  const KRS_TEST_CONFIG = {
    // Load an existing dictionary for testing
    loadDictionary: {
      dictType: 'BDO'
    },
    // Test search query
    search: {
      query: '안녕하세요',
      threshold: 0.85,
      topK: 10
    }
  };

  // Test state for CDP access (bypasses Svelte reactivity)
  const _krsTestState = {
    isProcessing: false,
    statusMessage: '',
    currentDictionary: null,
    searchResults: []
  };

  // TEST: Load Dictionary (uses predefined dict_type)
  // FACTOR ARCHITECTURE: Uses createTracker for centralized progress
  async function testLoadDictionary() {
    // FACTOR: Create tracker for this operation
    const tracker = createTracker('KRSimilar', 'Load Dictionary');
    tracker.start();

    _krsTestState.isProcessing = true;
    _krsTestState.statusMessage = 'TEST: Loading KR Similar dictionary...';
    logger.info('TEST MODE: Loading KR Similar dictionary', KRS_TEST_CONFIG.loadDictionary);

    try {
      loadDictType = KRS_TEST_CONFIG.loadDictionary.dictType;

      tracker.update(25, `Loading ${loadDictType} embeddings...`);
      await loadDictionary();

      _krsTestState.currentDictionary = currentDictionary;
      const successMsg = currentDictionary
        ? `Dictionary loaded! ${currentDictionary.split_pairs} split + ${currentDictionary.whole_pairs} whole`
        : 'Dictionary load completed';
      _krsTestState.statusMessage = `TEST: ${successMsg}`;

      // FACTOR: Complete tracker
      tracker.complete(successMsg);
    } catch (error) {
      _krsTestState.statusMessage = `TEST ERROR: ${error.message}`;
      logger.error('TEST MODE: Load KR Similar dictionary failed', { error: error.message });
      // FACTOR: Fail tracker
      tracker.fail(error.message);
    } finally {
      _krsTestState.isProcessing = false;
    }
  }

  // TEST: Search (uses predefined query)
  // FACTOR ARCHITECTURE: Uses createTracker for centralized progress
  async function testSearch() {
    if (!currentDictionary) {
      _krsTestState.statusMessage = 'TEST ERROR: No dictionary loaded. Call testLoadDictionary first.';
      return;
    }

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('KRSimilar', 'Search Similar');
    tracker.start();

    _krsTestState.isProcessing = true;
    _krsTestState.statusMessage = 'TEST: Searching for similar Korean texts...';
    logger.info('TEST MODE: KR Similar search', KRS_TEST_CONFIG.search);

    try {
      searchQuery = KRS_TEST_CONFIG.search.query;
      searchThreshold = KRS_TEST_CONFIG.search.threshold;
      searchTopK = KRS_TEST_CONFIG.search.topK;

      tracker.update(50, `Finding similar to "${searchQuery.substring(0, 20)}..."...`);
      await performSearch();

      _krsTestState.searchResults = searchResults;
      const successMsg = `Search completed! ${searchResults.length} similar texts found`;
      _krsTestState.statusMessage = `TEST: ${successMsg}`;

      // FACTOR: Complete tracker
      tracker.complete(successMsg);
    } catch (error) {
      _krsTestState.statusMessage = `TEST ERROR: ${error.message}`;
      logger.error('TEST MODE: KR Similar search failed', { error: error.message });
      // FACTOR: Fail tracker
      tracker.fail(error.message);
    } finally {
      _krsTestState.isProcessing = false;
    }
  }

  // Expose test functions globally for CDP access
  if (typeof window !== 'undefined') {
    window.krSimilarTest = {
      loadDictionary: () => testLoadDictionary(),
      search: () => testSearch(),
      getStatus: () => ({
        ..._krsTestState,
        isDictionaryLoaded: !!currentDictionary,
        dictionaryInfo: currentDictionary
      }),
      _state: _krsTestState
    };
  }

  // ========================================================================
  // API CALLS
  // ========================================================================

  async function loadAvailableDictionaries() {
    try {
      const response = await fetch(`${API_BASE}/api/v2/kr-similar/list-dictionaries`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        if (response.status === 403 || response.status === 401) {
          logger.warning("Authentication required for list-dictionaries");
          availableDictionaries = [];
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      availableDictionaries = data.data?.dictionaries || [];
      logger.info(`Loaded ${availableDictionaries.length} available KR Similar dictionaries`);
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
    logger.userAction("Creating KR Similar dictionary", { dict_type: createDictType, files: createFiles.length });

    try {
      const formData = new FormData();
      for (const file of createFiles) {
        formData.append('files', file);
      }
      formData.append('dict_type', createDictType);
      formData.append('kr_column', createKrColumn);
      formData.append('trans_column', createTransColumn);

      const response = await fetch(`${API_BASE}/api/v2/kr-similar/create-dictionary`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        showStatus(`Dictionary creation started: ${createDictType}`, 'success');
        telemetry.trackOperationSuccess('KRSimilar', 'create_dictionary', startTime, {
          dict_type: createDictType,
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
      telemetry.trackOperationError('KRSimilar', 'create_dictionary', startTime, error, {
        dict_type: createDictType
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isCreatingDictionary = false;
    }
  }

  async function loadDictionary() {
    isLoadingDictionary = true;
    const startTime = Date.now();
    logger.userAction("Loading KR Similar dictionary", { dict_type: loadDictType });

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('KRSimilar', 'Load Dictionary');
    tracker.start();
    tracker.update(10, `Loading ${loadDictType} embeddings...`);

    try {
      const formData = new FormData();
      formData.append('dict_type', loadDictType);

      tracker.update(30, 'Fetching dictionary from server...');

      const response = await fetch(`${API_BASE}/api/v2/kr-similar/load-dictionary`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        currentDictionary = {
          dict_type: loadDictType,
          split_pairs: data.data?.split_pairs || 0,
          whole_pairs: data.data?.whole_pairs || 0,
          total_pairs: data.data?.total_pairs || 0
        };
        telemetry.trackOperationSuccess('KRSimilar', 'load_dictionary', startTime, {
          dict_type: loadDictType,
          total_pairs: currentDictionary.total_pairs
        });
        const successMsg = `Dictionary loaded: ${loadDictType} (${currentDictionary.total_pairs} pairs)`;
        showStatus(successMsg, 'success');
        tracker.complete(successMsg);
        showLoadDictionaryModal = false;
      } else {
        throw new Error(data.detail || 'Failed to load dictionary');
      }
    } catch (error) {
      logger.error("Dictionary load failed", { error: error.message });
      telemetry.trackOperationError('KRSimilar', 'load_dictionary', startTime, error, {
        dict_type: loadDictType
      });
      showStatus(`Error: ${error.message}`, 'error');
      tracker.fail(error.message);
    } finally {
      isLoadingDictionary = false;
    }
  }

  async function clearDictionary() {
    try {
      const response = await fetch(`${API_BASE}/api/v2/kr-similar/clear`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      const data = await response.json();

      if (response.ok) {
        currentDictionary = null;
        searchResults = [];
        showStatus('Dictionary cleared from memory', 'success');
      } else {
        throw new Error(data.detail || 'Failed to clear dictionary');
      }
    } catch (error) {
      logger.error("Clear dictionary failed", { error: error.message });
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
    logger.userAction("Performing KR Similar search", { query: searchQuery, threshold: searchThreshold, top_k: searchTopK });

    // FACTOR: Create tracker for this operation
    const tracker = createTracker('KRSimilar', 'Search');
    tracker.start();
    tracker.update(10, 'Searching for similar strings...');

    try {
      const formData = new FormData();
      formData.append('query', searchQuery);
      formData.append('threshold', searchThreshold);
      formData.append('top_k', searchTopK);
      formData.append('use_whole', searchUseWhole);

      tracker.update(30, 'Computing embeddings...');

      const response = await fetch(`${API_BASE}/api/v2/kr-similar/search`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        searchResults = data.data?.results || [];
        telemetry.trackOperationSuccess('KRSimilar', 'search', startTime, {
          threshold: searchThreshold,
          top_k: searchTopK,
          use_whole: searchUseWhole,
          results_count: searchResults.length
        });
        const successMsg = `KR Similar search completed: ${searchResults.length} results found`;
        logger.info(successMsg);
        tracker.complete(successMsg);
        if (searchResults.length === 0) {
          showStatus('No similar strings found above threshold', 'info');
        }
      } else {
        throw new Error(data.detail || 'Search failed');
      }
    } catch (error) {
      logger.error("Search failed", { error: error.message });
      telemetry.trackOperationError('KRSimilar', 'search', startTime, error, {
        threshold: searchThreshold,
        top_k: searchTopK
      });
      showStatus(`Search error: ${error.message}`, 'error');
      tracker.fail(error.message);
    } finally {
      isSearching = false;
    }
  }

  async function extractSimilar() {
    if (extractFile.length === 0) {
      showStatus('Please select a file', 'error');
      return;
    }

    isExtracting = true;
    const startTime = Date.now();
    logger.userAction("Extracting similar strings", { filename: extractFile[0].name });

    try {
      const formData = new FormData();
      formData.append('file', extractFile[0]);
      formData.append('min_char_length', extractMinCharLength);
      formData.append('similarity_threshold', extractThreshold);
      formData.append('filter_same_category', extractFilterSameCategory);

      const response = await fetch(`${API_BASE}/api/v2/kr-similar/extract-similar`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        showStatus(`Extraction started: ${extractFile[0].name}`, 'success');
        telemetry.trackOperationSuccess('KRSimilar', 'extract_similar', startTime, {
          threshold: extractThreshold,
          min_char_length: extractMinCharLength
        });
        showExtractSimilarModal = false;
        extractFile = [];
      } else {
        throw new Error(data.detail || 'Extraction failed');
      }
    } catch (error) {
      logger.error("Extraction failed", { error: error.message });
      telemetry.trackOperationError('KRSimilar', 'extract_similar', startTime, error, {
        threshold: extractThreshold
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isExtracting = false;
    }
  }

  async function autoTranslate() {
    if (translateFile.length === 0) {
      showStatus('Please select a file', 'error');
      return;
    }

    if (!currentDictionary) {
      showStatus('Please load a dictionary first', 'error');
      return;
    }

    isTranslating = true;
    const startTime = Date.now();
    logger.userAction("Auto-translating", { filename: translateFile[0].name });

    try {
      const formData = new FormData();
      formData.append('file', translateFile[0]);
      formData.append('similarity_threshold', translateThreshold);

      const response = await fetch(`${API_BASE}/api/v2/kr-similar/auto-translate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        showStatus(`Auto-translation started: ${translateFile[0].name}`, 'success');
        telemetry.trackOperationSuccess('KRSimilar', 'auto_translate', startTime, {
          threshold: translateThreshold
        });
        showAutoTranslateModal = false;
        translateFile = [];
      } else {
        throw new Error(data.detail || 'Auto-translation failed');
      }
    } catch (error) {
      logger.error("Auto-translation failed", { error: error.message });
      telemetry.trackOperationError('KRSimilar', 'auto_translate', startTime, error, {
        threshold: translateThreshold
      });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isTranslating = false;
    }
  }

  // DataTable headers
  const headers = [
    { key: 'korean', value: 'Korean Text' },
    { key: 'translation', value: 'Translation' },
    { key: 'similarity', value: 'Similarity' }
  ];

  // Svelte 5: Derived - DataTable rows
  let rows = $derived(searchResults.map((result, index) => ({
    id: index.toString(),
    korean: result.korean || result.text || '',
    translation: result.translation || '',
    similarity: result.similarity ? `${(result.similarity * 100).toFixed(1)}%` : ''
  })));
</script>

<div class="krsimilar-container">
  <!-- Notification -->
  {#if showNotification}
    <div class="notification-container">
      <ToastNotification
        kind={notificationType === 'info' ? 'info' : notificationType}
        title={notificationType === 'success' ? 'Success' : notificationType === 'error' ? 'Error' : 'Info'}
        subtitle={statusMessage}
        timeout={5000}
        on:close={() => showNotification = false}
      />
    </div>
  {/if}

  <!-- Header -->
  <div class="header">
    <h2>KR Similar - Korean Semantic Similarity</h2>
    <p class="subtitle">Find similar Korean strings using BERT embeddings</p>
  </div>

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
        icon={Search}
        on:click={() => showExtractSimilarModal = true}
      >
        Extract Similar
      </Button>

      <Button
        kind="tertiary"
        icon={Translate}
        on:click={() => showAutoTranslateModal = true}
      >
        Auto-Translate
      </Button>

      <Button
        kind="danger-tertiary"
        icon={TrashCan}
        on:click={clearDictionary}
      >
        Clear Dictionary
      </Button>
    {/if}
  </div>

  <!-- Dictionary Status -->
  <div class="status-tiles">
    <Tile class="status-tile">
      <h4>Current Dictionary</h4>
      {#if currentDictionary}
        <p><strong>{currentDictionary.dict_type}</strong></p>
        <p>Split pairs: {currentDictionary.split_pairs}</p>
        <p>Whole pairs: {currentDictionary.whole_pairs}</p>
        <p class="total">Total: {currentDictionary.total_pairs} pairs</p>
      {:else}
        <p class="empty">No dictionary loaded</p>
      {/if}
    </Tile>

    <Tile class="status-tile">
      <h4>Available Dictionaries</h4>
      {#if availableDictionaries.length > 0}
        <ul>
          {#each availableDictionaries as dict}
            <li>{dict.dict_type || dict.name}</li>
          {/each}
        </ul>
      {:else}
        <p class="empty">No dictionaries available</p>
      {/if}
    </Tile>
  </div>

  <!-- Search Interface -->
  {#if currentDictionary}
    <div class="search-section">
      <h3>Semantic Search</h3>

      <TextArea
        labelText="Search Query (Korean text)"
        placeholder="Enter Korean text to find similar strings..."
        bind:value={searchQuery}
        rows={3}
      />

      <div class="search-controls">
        <div class="slider-control">
          <Slider
            labelText="Similarity Threshold"
            min={0.5}
            max={1.0}
            step={0.05}
            bind:value={searchThreshold}
          />
          <span class="slider-value">{(searchThreshold * 100).toFixed(0)}%</span>
        </div>

        <NumberInput
          label="Max Results"
          min={1}
          max={100}
          bind:value={searchTopK}
        />

        <Toggle
          labelText="Use Whole Embeddings"
          bind:toggled={searchUseWhole}
        />
      </div>

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
        <h3>Results ({searchResults.length} found)</h3>

        <DataTable
          {headers}
          {rows}
          size="short"
        >
          <svelte:fragment slot="cell" let:row let:cell>
            {#if cell.key === 'korean'}
              <div class="result-cell korean">{cell.value}</div>
            {:else if cell.key === 'translation'}
              <div class="result-cell translation">{cell.value}</div>
            {:else if cell.key === 'similarity'}
              <div class="result-cell similarity">{cell.value}</div>
            {:else}
              {cell.value}
            {/if}
          </svelte:fragment>
        </DataTable>
      </div>
    {/if}
  {/if}

  <!-- Create Dictionary Modal -->
  <Modal
    bind:open={showCreateDictionaryModal}
    modalHeading="Create KR Similar Dictionary"
    primaryButtonText="Create"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isCreatingDictionary || createFiles.length === 0}
    on:click:button--secondary={() => showCreateDictionaryModal = false}
    on:click:button--primary={createDictionary}
  >
    <p class="modal-description">Upload language data files to create a new embeddings dictionary.</p>

    <Select labelText="Dictionary Type" bind:selected={createDictType}>
      {#each DICT_TYPES as dtype}
        <SelectItem value={dtype} text={dtype} />
      {/each}
    </Select>

    <NumberInput
      label="Korean Column Index"
      min={0}
      max={20}
      bind:value={createKrColumn}
      helperText="0-indexed column containing Korean text"
    />

    <NumberInput
      label="Translation Column Index"
      min={0}
      max={20}
      bind:value={createTransColumn}
      helperText="0-indexed column containing translation"
    />

    <FileUploader
      labelTitle="Upload files"
      labelDescription="Tab-separated language data files"
      buttonLabel="Select files"
      accept={['.txt', '.tsv']}
      multiple
      bind:files={createFiles}
    />

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
    <p class="modal-description">Select a dictionary type to load into memory.</p>

    <Select labelText="Dictionary Type" bind:selected={loadDictType}>
      {#each DICT_TYPES as dtype}
        <SelectItem value={dtype} text={dtype} />
      {/each}
    </Select>

    {#if availableDictionaries.length > 0}
      <div class="available-dicts">
        <p><strong>Available Dictionaries:</strong></p>
        <ul>
          {#each availableDictionaries as dict}
            <li>{dict.dict_type || dict.name}</li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if isLoadingDictionary}
      <InlineLoading description="Loading dictionary..." />
    {/if}
  </Modal>

  <!-- Extract Similar Modal -->
  <Modal
    bind:open={showExtractSimilarModal}
    modalHeading="Extract Similar Strings"
    primaryButtonText="Extract"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isExtracting || extractFile.length === 0}
    on:click:button--secondary={() => showExtractSimilarModal = false}
    on:click:button--primary={extractSimilar}
  >
    <p class="modal-description">Find groups of similar strings in a file for consistency checking.</p>

    <FileUploader
      labelTitle="Upload file"
      labelDescription="Tab-separated language data file"
      buttonLabel="Select file"
      accept={['.txt', '.tsv']}
      bind:files={extractFile}
    />

    <NumberInput
      label="Minimum Character Length"
      min={10}
      max={500}
      bind:value={extractMinCharLength}
      helperText="Only consider strings with at least this many characters"
    />

    <div class="slider-control-modal">
      <Slider
        labelText="Similarity Threshold"
        min={0.5}
        max={1.0}
        step={0.05}
        bind:value={extractThreshold}
      />
      <span class="slider-value">{(extractThreshold * 100).toFixed(0)}%</span>
    </div>

    <Toggle
      labelText="Filter Same Category"
      bind:toggled={extractFilterSameCategory}
    />

    {#if isExtracting}
      <InlineLoading description="Starting extraction..." />
    {/if}
  </Modal>

  <!-- Auto-Translate Modal -->
  <Modal
    bind:open={showAutoTranslateModal}
    modalHeading="Auto-Translate"
    primaryButtonText="Translate"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isTranslating || translateFile.length === 0}
    on:click:button--secondary={() => showAutoTranslateModal = false}
    on:click:button--primary={autoTranslate}
  >
    <p class="modal-description">Auto-translate a file using semantic similarity matching from the loaded dictionary.</p>

    <FileUploader
      labelTitle="Upload file"
      labelDescription="Tab-separated language data file"
      buttonLabel="Select file"
      accept={['.txt', '.tsv']}
      bind:files={translateFile}
    />

    <div class="slider-control-modal">
      <Slider
        labelText="Similarity Threshold"
        min={0.5}
        max={1.0}
        step={0.05}
        bind:value={translateThreshold}
      />
      <span class="slider-value">{(translateThreshold * 100).toFixed(0)}%</span>
    </div>

    {#if isTranslating}
      <InlineLoading description="Starting translation..." />
    {/if}
  </Modal>
</div>

<style>
  .krsimilar-container {
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

  .status-tiles :global(.bx--tile .total) {
    font-weight: 600;
    margin-top: 0.5rem;
  }

  .status-tiles :global(.bx--tile ul) {
    margin: 0.5rem 0 0 1rem;
    padding: 0;
  }

  .status-tiles :global(.bx--tile li) {
    margin: 0.25rem 0;
    font-size: 0.875rem;
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
    margin-top: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  .slider-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 250px;
  }

  .slider-control-modal {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1rem 0;
  }

  .slider-value {
    font-weight: 600;
    min-width: 3rem;
    text-align: right;
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

  .result-cell.similarity {
    font-family: monospace;
    font-weight: 600;
    color: var(--cds-support-02);
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
</style>
