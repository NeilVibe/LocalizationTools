<script>
  /**
   * CharacterCodexPage.svelte - Character Codex encyclopedia page
   *
   * Browse, search, and inspect game characters with card grid, category tabs,
   * client-side filtering, and knowledge resolution detail panel.
   *
   * Phase 102: Bulk load conversion (no pagination)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { UserMultiple, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import CharacterCodexDetail from "$lib/components/ldm/CharacterCodexDetail.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  // State
  let categories = $state([]);
  let activeCategory = $state(null);
  let allCharacters = $state([]);
  let selectedCharacter = $state(null);
  let searchQuery = $state("");
  let loadingCategories = $state(true);
  let loadingList = $state(true);
  let loadingDetail = $state(false);
  let apiError = $state(null);
  let failedImages = $state(new Set());

  // Derived: total character count for "All" tab
  let allCharacterCount = $derived(
    categories.reduce((sum, c) => sum + (c.count || 0), 0)
  );

  // Derived: client-side filtered characters by category + search
  let filteredCharacters = $derived.by(() => {
    return allCharacters.filter(char => {
      if (activeCategory && char.category !== activeCategory) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = `${char.name_kr || ''} ${char.name_translated || ''} ${char.strkey || ''} ${char.race || ''} ${char.gender || ''} ${char.desc_kr || ''}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  });

  /**
   * Fetch filename-based character categories for tab navigation
   */
  async function fetchCategories() {
    loadingCategories = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/characters/categories`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      categories = data.categories || [];
      logger.info('Character Codex categories loaded', { count: categories.length, totalCharacters: data.total_characters });
    } catch (err) {
      logger.error('Failed to fetch character categories', { error: err.message });
      apiError = 'Character Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingCategories = false;
    }
  }

  /**
   * Fetch all characters in a single request (bulk load)
   */
  async function fetchAllCharacters() {
    loadingList = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/characters`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      allCharacters = data.characters || [];
      logger.info('Character Codex bulk loaded', { total: allCharacters.length });
    } catch (err) {
      logger.error('Failed to fetch characters', { error: err.message });
      apiError = 'Failed to load characters';
    } finally {
      loadingList = false;
    }
  }

  /**
   * Fetch full character detail by strkey
   */
  async function fetchCharacterDetail(strkey) {
    loadingDetail = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/characters/${encodeURIComponent(strkey)}`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedCharacter = await response.json();
      logger.info('Character detail loaded', { strkey });
    } catch (err) {
      logger.error('Failed to fetch character detail', { error: err.message, strkey });
    } finally {
      loadingDetail = false;
    }
  }

  /**
   * Handle category tab selection
   */
  function selectCategory(categoryName) {
    activeCategory = categoryName;
    selectedCharacter = null;
  }

  /**
   * Handle card click -- open detail panel
   */
  function selectCard(character) {
    fetchCharacterDetail(character.strkey);
  }

  /**
   * Navigate to related entity in detail panel
   */
  function handleSimilarNavigation(strkey) {
    fetchCharacterDetail(strkey);
  }

  /**
   * Back to card grid from detail view
   */
  function clearSelection() {
    selectedCharacter = null;
  }

  /**
   * Transform CharacterCardResponse to CodexCard entity shape
   */
  function toCardEntity(char) {
    const badges = [char.race, char.gender].filter(Boolean).join(' / ');
    return {
      strkey: char.strkey,
      name: char.name_kr,
      entity_type: 'character',
      description: char.name_translated
        ? char.name_translated + (badges ? ' (' + badges + ')' : '')
        : badges || char.desc_kr || '',
      image_texture: null,
      ai_image_url: char.image_urls?.length ? char.image_urls[0] : null,
      ai_image_urls: char.image_urls || [],
      related_entities: []
    };
  }

  onMount(() => {
    fetchCategories();
    fetchAllCharacters();
  });
</script>

<div class="character-codex-page">
  <!-- Header -->
  <PageHeader icon={UserMultiple} title="Character Codex" />

  <!-- Search Bar -->
  <div class="character-codex-search">
    <input
      type="search"
      placeholder="Search characters by name, StrKey, race, or job..."
      bind:value={searchQuery}
      class="search-input"
      aria-label="Search characters"
    />
  </div>

  {#if apiError}
    <div class="character-codex-state-container">
      <ErrorState message={apiError} onretry={() => { fetchCategories(); fetchAllCharacters(); }} />
    </div>
  {:else if loadingCategories}
    <div class="character-codex-loading" role="status" aria-live="polite">
      <InlineLoading description="Loading character categories..." />
    </div>
  {:else}
    <!-- Category Tabs -->
    <div class="character-codex-tabs" role="tablist" aria-label="Character category tabs">
      <button
        class="character-codex-tab"
        class:active={activeCategory === null}
        role="tab"
        aria-selected={activeCategory === null}
        onclick={() => selectCategory(null)}
      >
        <span class="tab-label">All</span>
        <span class="tab-count">{allCharacterCount}</span>
      </button>
      {#each categories as cat (cat.category)}
        <button
          class="character-codex-tab"
          class:active={activeCategory === cat.category}
          role="tab"
          aria-selected={activeCategory === cat.category}
          aria-label="{cat.category} ({cat.count})"
          onclick={() => selectCategory(cat.category)}
        >
          <span class="tab-label">{cat.category}</span>
          <span class="tab-count">{cat.count}</span>
        </button>
      {/each}
    </div>

    <!-- Content Area -->
    <div class="character-codex-content">
      {#if selectedCharacter}
        <!-- Detail View -->
        <div class="detail-view">
          <button class="back-btn" onclick={clearSelection} aria-label="Back to character list">
            <ArrowLeft size={16} />
            <span>Back to list</span>
          </button>
          {#if loadingDetail}
            <InlineLoading description="Loading character details..." />
          {:else}
            <CharacterCodexDetail
              character={selectedCharacter}
              onback={clearSelection}
              onsimilar={handleSimilarNavigation}
            />
          {/if}
        </div>
      {:else if loadingList}
        <div class="entity-grid">
          <SkeletonCard count={12} />
        </div>
      {:else}
        <!-- Card Grid -->
        <div class="entity-grid">
          {#each filteredCharacters as char (char.strkey)}
            <CodexCard
              entity={toCardEntity(char)}
              index={filteredCharacters.indexOf(char)}
              apiBase={API_BASE}
              {failedImages}
              onclick={() => selectCard(char)}
              onfailimage={(key) => {
                const next = new Set(failedImages);
                next.add(key);
                failedImages = next;
              }}
            />
          {/each}

          {#if filteredCharacters.length === 0 && !loadingList}
            <div class="no-entities">
              <p>No characters found{searchQuery ? ` matching "${searchQuery}"` : ''}{activeCategory ? ` in "${activeCategory}"` : ''} -- ensure gamedata files are loaded and indexed.</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .character-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .character-codex-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .character-codex-search {
    padding: 16px 16px 12px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .search-input {
    width: 100%;
    padding: 8px 12px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .search-input::placeholder {
    color: var(--cds-text-03);
  }

  .character-codex-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  .character-codex-tabs {
    display: flex;
    gap: 0;
    padding: 0 16px;
    background: var(--cds-layer-01);
    border-bottom: 2px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
    overflow-x: auto;
  }

  .character-codex-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    white-space: nowrap;
    transition: all 0.15s;
  }

  .character-codex-tab:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .character-codex-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .character-codex-tab.active {
    color: var(--cds-text-01);
    border-bottom-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 600;
  }

  .tab-count {
    font-size: 0.75rem;
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
  }

  .character-codex-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--page-content-padding, 16px);
    min-height: 0;
  }

  .detail-view {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    cursor: pointer;
    align-self: flex-start;
    transition: background 0.15s;
  }

  .back-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .back-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .entity-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
  }

  .no-entities {
    grid-column: 1 / -1;
    text-align: center;
    padding: 32px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

</style>
