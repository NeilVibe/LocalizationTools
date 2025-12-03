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
    Toggle
  } from "carbon-components-svelte";
  import { Upload, Search, FolderOpen, View, ViewOff } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  // API base URL
  const API_BASE = 'http://localhost:8888';

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

  async function loadAvailableDictionaries() {
    try {
      // Note: This endpoint requires authentication, but we'll handle that
      const response = await fetch(`${API_BASE}/api/v2/quicksearch/list-dictionaries`);

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
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        showStatus(`Dictionary creation started: ${createGame}-${createLanguage}`, 'success');
        showCreateDictionaryModal = false;
        createFiles = [];
        await loadAvailableDictionaries();
      } else {
        throw new Error(data.detail || 'Failed to create dictionary');
      }
    } catch (error) {
      logger.error("Dictionary creation failed", { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isCreatingDictionary = false;
    }
  }

  async function loadDictionary() {
    isLoadingDictionary = true;
    logger.userAction("Loading dictionary", { game: loadGame, language: loadLanguage });

    try {
      const formData = new FormData();
      formData.append('game', loadGame);
      formData.append('language', loadLanguage);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/load-dictionary`, {
        method: 'POST',
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
        showStatus(`Dictionary loaded: ${loadGame}-${loadLanguage} (${data.pairs_count} pairs)`, 'success');
        showLoadDictionaryModal = false;
      } else {
        throw new Error(data.detail || 'Failed to load dictionary');
      }
    } catch (error) {
      logger.error("Dictionary load failed", { error: error.message });
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      isLoadingDictionary = false;
    }
  }

  async function setReference() {
    isLoadingReference = true;
    logger.userAction("Setting reference dictionary", { game: refGame, language: refLanguage });

    try {
      const formData = new FormData();
      formData.append('game', refGame);
      formData.append('language', refLanguage);

      const response = await fetch(`${API_BASE}/api/v2/quicksearch/set-reference`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        referenceDictionary = { game: refGame, language: refLanguage };
        referenceEnabled = true;
        showStatus(`Reference loaded: ${refGame}-${refLanguage}`, 'success');
        showSetReferenceModal = false;

        // Also toggle reference on
        await toggleReference(true);
      } else {
        throw new Error(data.detail || 'Failed to set reference');
      }
    } catch (error) {
      logger.error("Reference load failed", { error: error.message });
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
          body: formData
        });

        const data = await response.json();

        if (response.ok) {
          searchResults = data.results || [];
          totalResults = data.total_count || 0;
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
          logger.info(`Multi-line search completed: ${totalResults} total matches`);
        } else {
          throw new Error(data.detail || 'Multi-line search failed');
        }
      }
    } catch (error) {
      logger.error("Search failed", { error: error.message });
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
    <h2>QuickSearch - Dictionary Search Tool</h2>
    <p class="subtitle">Search game translations with XML/TXT dictionary support</p>
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

  <!-- Create Dictionary Modal -->
  <Modal
    bind:open={showCreateDictionaryModal}
    modalHeading="Create Dictionary"
    primaryButtonText="Create"
    secondaryButtonText="Cancel"
    primaryButtonDisabled={isCreatingDictionary || createFiles.length === 0}
    on:click:button--secondary={() => showCreateDictionaryModal = false}
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

    <FileUploader
      labelTitle="Upload files"
      labelDescription="XML, TXT, or TSV files only"
      buttonLabel="Select files"
      accept={['.xml', '.txt', '.tsv']}
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
        <p><strong>Available Dictionaries:</strong></p>
        <ul>
          {#each availableDictionaries as dict}
            <li>{dict.game}-{dict.language} ({dict.pairs_count} pairs)</li>
          {/each}
        </ul>
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
</style>
