<script>
  /**
   * EXPLORER-004: Explorer Search Component
   * Full recursive search like "Everything" - fully interactive!
   * Right-click context menu, Ctrl+C/X/V, Delete - all operations available
   *
   * SVELTE 5 RUNES: $state, $props with callback props (no createEventDispatcher)
   */
  import { Search, Close, Document, Folder, DataBase, App, Copy, Cut, TrashCan, Launch } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';

  let {
    apiBase = '',
    isOfflineMode = false,  // P9: When true, only search local files
    onnavigate = () => {},
    oncopy = () => {},
    oncut = () => {},
    ondelete = () => {}
  } = $props();

  let query = $state('');
  let results = $state([]);
  let resultCount = $state(0);
  let showDropdown = $state(false);
  let loading = $state(false);
  let searchTimeout = null;
  let inputRef = null;
  let selectedIndex = $state(-1);

  // Context menu state
  let showContextMenu = $state(false);
  let contextMenuX = $state(0);
  let contextMenuY = $state(0);
  let contextMenuItem = $state(null);

  function getAuthHeaders() {
    // BUG-044 FIX: Was using wrong key 'token' instead of 'auth_token'
    const token = localStorage.getItem('auth_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  async function search(q) {
    if (q.length < 1) {
      results = [];
      resultCount = 0;
      showDropdown = false;
      return;
    }

    loading = true;
    try {
      // P9: In offline mode, only search local files
      const mode = isOfflineMode ? 'offline' : 'online';
      const response = await fetch(`${apiBase}/api/ldm/search?q=${encodeURIComponent(q)}&mode=${mode}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        results = data.results || [];
        resultCount = data.count || 0;
        showDropdown = results.length > 0;
        selectedIndex = -1;
      } else {
        results = [];
        resultCount = 0;
        showDropdown = false;
      }
    } catch (err) {
      logger.error('Search error', { error: err.message });
      results = [];
      resultCount = 0;
      showDropdown = false;
    } finally {
      loading = false;
    }
  }

  function debouncedSearch(q) {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => search(q), 150);
  }

  function handleInput(e) {
    query = e.target.value;
    debouncedSearch(query);
  }

  function handleSelect(result) {
    onnavigate(result.path);
    closeSearch();
    logger.info('Teleporting to', { path: result.pathString });
  }

  function closeSearch() {
    showDropdown = false;
    query = '';
    results = [];
    resultCount = 0;
    selectedIndex = -1;
    showContextMenu = false;
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (showContextMenu) {
        showContextMenu = false;
      } else {
        closeSearch();
        inputRef?.blur();
      }
      return;
    }

    if (!showDropdown || results.length === 0) return;

    const selected = selectedIndex >= 0 ? results[selectedIndex] : null;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % results.length;
      scrollToSelected();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIndex = selectedIndex <= 0 ? results.length - 1 : selectedIndex - 1;
      scrollToSelected();
    } else if (e.key === 'Enter' && selected) {
      e.preventDefault();
      handleSelect(selected);
    } else if (e.key === 'Delete' && selected) {
      e.preventDefault();
      handleDelete(selected);
    } else if ((e.ctrlKey || e.metaKey) && selected) {
      if (e.key === 'c') {
        e.preventDefault();
        handleCopy(selected);
      } else if (e.key === 'x') {
        e.preventDefault();
        handleCut(selected);
      }
    }
  }

  function scrollToSelected() {
    setTimeout(() => {
      const el = document.querySelector('.search-result.selected');
      el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }, 0);
  }

  // Context menu handlers
  function handleContextMenu(e, result) {
    e.preventDefault();
    e.stopPropagation();
    contextMenuItem = result;
    contextMenuX = e.clientX;
    contextMenuY = e.clientY;
    showContextMenu = true;
    selectedIndex = results.indexOf(result);
  }

  function closeContextMenu() {
    showContextMenu = false;
    contextMenuItem = null;
  }

  // Actions - call parent callbacks (Svelte 5 pattern)
  function handleCopy(item) {
    oncopy(item);
    logger.info('Copied', { name: item.name });
    closeContextMenu();
  }

  function handleCut(item) {
    oncut(item);
    logger.info('Cut', { name: item.name });
    closeContextMenu();
  }

  function handleDelete(item) {
    ondelete(item);
    // OPTIMISTIC: Remove from results immediately
    results = results.filter(r => !(r.id === item.id && r.type === item.type));
    resultCount = results.length;
    closeContextMenu();
  }

  function handleOpenLocation(item) {
    // Navigate to parent folder, not the item itself
    const parentPath = item.path.slice(0, -1);
    if (parentPath.length > 0) {
      onnavigate(parentPath);
    } else {
      onnavigate([]);
    }
    closeSearch();
  }

  function getIcon(type) {
    switch (type) {
      case 'platform': return App;
      case 'project': return DataBase;
      case 'folder': return Folder;
      case 'file': return Document;
      default: return Document;
    }
  }

  function getTypeColor(type) {
    switch (type) {
      case 'platform': return '#8b5cf6';
      case 'project': return '#3b82f6';
      case 'folder': return '#f59e0b';
      case 'file': return '#10b981';
      default: return '#6b7280';
    }
  }

  function highlightMatch(text, q) {
    if (!q) return text;
    const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  // Close context menu on outside click
  function handleWindowClick(e) {
    if (showContextMenu) {
      showContextMenu = false;
    }
  }
</script>

<svelte:window onclick={handleWindowClick} />

<div class="explorer-search">
  <div class="search-container" class:has-results={showDropdown}>
    <div class="search-icon">
      {#if loading}
        <div class="spinner"></div>
      {:else}
        <Search size={20} />
      {/if}
    </div>

    <input
      bind:this={inputRef}
      type="text"
      placeholder="Search everything... (right-click for actions)"
      value={query}
      oninput={handleInput}
      onkeydown={handleKeydown}
      onfocus={() => { if (results.length > 0) showDropdown = true; }}
    />

    {#if query}
      <button class="clear-btn" onclick={closeSearch} title="Clear (Esc)">
        <Close size={16} />
      </button>
    {/if}
  </div>

  {#if showDropdown}
    <div class="search-dropdown">
      <div class="results-header">
        <span class="results-count">{resultCount} result{resultCount !== 1 ? 's' : ''}</span>
        <span class="results-hint">↑↓ Enter | Right-click for menu | Ctrl+C/X Del</span>
      </div>

      <div class="results-list">
        {#each results as result, i (`${result.type}-${result.id}`)}
          <button
            class="search-result"
            class:selected={i === selectedIndex}
            onclick={() => handleSelect(result)}
            oncontextmenu={(e) => handleContextMenu(e, result)}
            onmouseenter={() => selectedIndex = i}
          >
            <div class="result-icon" style="background: {getTypeColor(result.type)}15; color: {getTypeColor(result.type)}">
              <svelte:component this={getIcon(result.type)} size={20} />
            </div>

            <div class="result-content">
              <div class="result-name">
                {@html highlightMatch(result.name, query)}
              </div>
              <div class="result-path">
                {result.pathString}
              </div>
            </div>

            <div class="result-type" style="background: {getTypeColor(result.type)}; color: white">
              {result.type}
            </div>
          </button>
        {/each}
      </div>

      {#if results.length === 0 && query.length >= 1 && !loading}
        <div class="no-results">
          <Search size={32} />
          <span>No results for "{query}"</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Context Menu -->
  {#if showContextMenu && contextMenuItem}
    <div
      class="context-menu"
      style="left: {contextMenuX}px; top: {contextMenuY}px;"
      onclick={(e) => e.stopPropagation()}
    >
      <button class="context-menu-item" onclick={() => handleSelect(contextMenuItem)}>
        <Launch size={16} /> Open
      </button>
      <button class="context-menu-item" onclick={() => handleOpenLocation(contextMenuItem)}>
        <Folder size={16} /> Open Location
      </button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item" onclick={() => handleCopy(contextMenuItem)}>
        <Copy size={16} /> Copy
      </button>
      <button class="context-menu-item" onclick={() => handleCut(contextMenuItem)}>
        <Cut size={16} /> Cut
      </button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={() => handleDelete(contextMenuItem)}>
        <TrashCan size={16} /> Delete
      </button>
    </div>
  {/if}
</div>

<style>
  .explorer-search {
    position: relative;
    width: 100%;
    max-width: 700px;
  }

  .search-container {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 18px;
    background: var(--cds-field-02, #f4f4f4);
    border: 2px solid transparent;
    border-radius: 10px;
    transition: all 0.15s ease;
  }

  .search-container:focus-within {
    background: var(--cds-field-01, #ffffff);
    border-color: var(--cds-interactive-01, #0f62fe);
    box-shadow: 0 4px 24px rgba(15, 98, 254, 0.12);
  }

  .search-container.has-results {
    border-radius: 10px 10px 0 0;
    border-bottom-color: transparent;
  }

  .search-icon {
    color: var(--cds-text-02, #525252);
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--cds-text-03, #a8a8a8);
    border-top-color: var(--cds-interactive-01, #0f62fe);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 15px;
    color: var(--cds-text-01, #161616);
    outline: none;
  }

  input::placeholder {
    color: var(--cds-text-03, #a8a8a8);
  }

  .clear-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    padding: 0;
    background: var(--cds-ui-03, #e0e0e0);
    border: none;
    border-radius: 50%;
    color: var(--cds-text-02, #525252);
    cursor: pointer;
    transition: all 0.1s ease;
  }

  .clear-btn:hover {
    background: var(--cds-ui-04, #8d8d8d);
    color: white;
  }

  .search-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--cds-ui-01, #ffffff);
    border: 2px solid var(--cds-interactive-01, #0f62fe);
    border-top: 1px solid var(--cds-ui-03, #e0e0e0);
    border-radius: 0 0 10px 10px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    overflow: hidden;
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background: var(--cds-ui-02, #f4f4f4);
    border-bottom: 1px solid var(--cds-ui-03, #e0e0e0);
  }

  .results-count {
    font-size: 12px;
    font-weight: 600;
    color: var(--cds-text-02, #525252);
  }

  .results-hint {
    font-size: 11px;
    color: var(--cds-text-03, #a8a8a8);
  }

  .results-list {
    max-height: 400px;
    overflow-y: auto;
  }

  .search-result {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 16px;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--cds-ui-03, #e0e0e0);
    cursor: pointer;
    text-align: left;
    transition: background 0.1s ease;
  }

  .search-result:last-child {
    border-bottom: none;
  }

  .search-result:hover,
  .search-result.selected {
    background: var(--cds-hover-ui, #e8e8e8);
  }

  .search-result.selected {
    background: var(--cds-selected-ui, #dde1e6);
  }

  .result-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .result-content {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .result-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--cds-text-01, #161616);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-name :global(mark) {
    background: #fef08a;
    color: inherit;
    padding: 0 2px;
    border-radius: 2px;
  }

  .result-path {
    font-size: 12px;
    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
    color: var(--cds-text-03, #6f6f6f);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
  }

  .result-type {
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .no-results {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 32px 20px;
    color: var(--cds-text-03, #a8a8a8);
  }

  .no-results span {
    font-size: 14px;
  }

  /* Context Menu */
  .context-menu {
    position: fixed;
    background: var(--cds-ui-01, #ffffff);
    border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    padding: 4px 0;
    z-index: 2000;
    min-width: 160px;
  }

  .context-menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 14px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 13px;
    color: var(--cds-text-01, #161616);
    text-align: left;
    transition: background 0.1s;
  }

  .context-menu-item:hover {
    background: var(--cds-hover-ui, #e8e8e8);
  }

  .context-menu-item.danger {
    color: var(--cds-danger-01, #da1e28);
  }

  .context-menu-item.danger:hover {
    background: #fff1f1;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01, #e0e0e0);
    margin: 4px 0;
  }
</style>
