<script>
  /**
   * QuestCodexPage.svelte - Quest Codex encyclopedia page
   *
   * Browse, search, and inspect game quests with card grid, type/subtype tabs,
   * client-side filtering, and detail panel.
   *
   * Phase 102: New codex page (bulk load, no pagination)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Task, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  const QUEST_TYPES = ['main', 'faction', 'challenge', 'minigame'];
  const FACTION_SUBTYPES = ['daily', 'region', 'politics', 'others'];

  // State
  let allQuests = $state([]);
  let loading = $state(true);
  let searchQuery = $state('');
  let activeType = $state('');
  let activeSubtype = $state('');
  let selectedQuest = $state(null);
  let detailLoading = $state(false);
  let apiError = $state(null);

  // Derived: client-side filtered quests by type + subtype + search
  let filteredQuests = $derived.by(() => {
    return allQuests.filter(q => {
      if (activeType && q.quest_type !== activeType) return false;
      if (activeSubtype && q.quest_subtype !== activeSubtype) return false;
      if (searchQuery) {
        const s = searchQuery.toLowerCase();
        const searchable = `${q.name_kr || ''} ${q.name_translated || ''} ${q.strkey || ''} ${q.desc_kr || ''}`.toLowerCase();
        if (!searchable.includes(s)) return false;
      }
      return true;
    });
  });

  async function fetchAll() {
    loading = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/quests`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      allQuests = data.items || [];
      logger.info('Quest Codex loaded', { count: allQuests.length });
    } catch (err) {
      logger.error('Failed to load quests', { error: err.message });
      apiError = 'Quest Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loading = false;
    }
  }

  async function fetchDetail(strkey) {
    detailLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/quests/${strkey}`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedQuest = await response.json();
    } catch (err) {
      logger.error('Failed to load quest detail', { error: err.message });
    } finally {
      detailLoading = false;
    }
  }

  function selectType(type) {
    activeType = activeType === type ? '' : type;
    activeSubtype = '';
  }

  function selectSubtype(subtype) {
    activeSubtype = activeSubtype === subtype ? '' : subtype;
  }

  onMount(() => { fetchAll(); });
</script>

<div class="codex-page">
  <PageHeader title="Quest Codex" icon={Task} subtitle="{allQuests.length} quests loaded" />

  <div class="codex-toolbar">
    <div class="codex-search">
      <input type="text" placeholder="Search quests..." bind:value={searchQuery} />
      {#if searchQuery}
        <button class="clear-btn" onclick={() => { searchQuery = ''; }}>Clear</button>
      {/if}
    </div>
  </div>

  <div class="codex-tabs">
    <button class="tab" class:active={!activeType} onclick={() => { activeType = ''; activeSubtype = ''; }}>
      All ({allQuests.length})
    </button>
    {#each QUEST_TYPES as type (type)}
      {@const count = allQuests.filter(q => q.quest_type === type).length}
      <button class="tab" class:active={activeType === type} onclick={() => selectType(type)}>
        {type.charAt(0).toUpperCase() + type.slice(1)} ({count})
      </button>
    {/each}
  </div>

  {#if activeType === 'faction'}
    <div class="codex-subtabs">
      <button class="subtab" class:active={!activeSubtype} onclick={() => { activeSubtype = ''; }}>All</button>
      {#each FACTION_SUBTYPES as sub (sub)}
        {@const count = allQuests.filter(q => q.quest_type === 'faction' && q.quest_subtype === sub).length}
        <button class="subtab" class:active={activeSubtype === sub} onclick={() => selectSubtype(sub)}>
          {sub.charAt(0).toUpperCase() + sub.slice(1)} ({count})
        </button>
      {/each}
    </div>
  {/if}

  {#if apiError}
    <ErrorState message={apiError} />
  {:else if selectedQuest}
    <div class="codex-detail">
      <button class="back-btn" onclick={() => { selectedQuest = null; }}>
        <ArrowLeft size={16} /> Back to list
      </button>
      {#if detailLoading}
        <InlineLoading description="Loading quest detail..." />
      {:else}
        <h3>{selectedQuest.name_kr || selectedQuest.strkey}</h3>
        {#if selectedQuest.image_urls?.length}
          <div class="detail-images">
            {#each selectedQuest.image_urls as url (url)}
              <img src={url} alt={selectedQuest.name_kr || selectedQuest.strkey} class="card-img" />
            {/each}
          </div>
        {/if}
        {#if selectedQuest.name_translated}<p class="translated">{selectedQuest.name_translated}</p>{/if}
        {#if selectedQuest.desc_kr}<p class="desc">{selectedQuest.desc_kr}</p>{/if}
        <div class="meta">
          {#if selectedQuest.quest_type}<span class="badge">{selectedQuest.quest_type}</span>{/if}
          {#if selectedQuest.quest_subtype}<span class="badge sub">{selectedQuest.quest_subtype}</span>{/if}
          <span class="strkey">{selectedQuest.strkey}</span>
        </div>
      {/if}
    </div>
  {:else if loading}
    <div class="skeleton-grid">
      {#each Array(12) as _, i (i)}
        <SkeletonCard />
      {/each}
    </div>
  {:else}
    <div class="codex-count">{filteredQuests.length} quests</div>
    <div class="codex-grid">
      {#each filteredQuests as quest (quest.strkey)}
        <button class="codex-card" onclick={() => fetchDetail(quest.strkey)}>
          {#if quest.image_urls?.length}
            <div class="card-images">
              {#each quest.image_urls as url (url)}
                <img src={url} alt={quest.name_kr || quest.strkey} class="card-img" />
              {/each}
            </div>
          {/if}
          <div class="card-body">
            <div class="card-name">{quest.name_kr || quest.strkey}</div>
            {#if quest.name_translated}<div class="card-translated">{quest.name_translated}</div>{/if}
            <div class="card-meta">
              {#if quest.quest_type}<span class="badge small">{quest.quest_type}</span>{/if}
              {#if quest.quest_subtype}<span class="badge small sub">{quest.quest_subtype}</span>{/if}
            </div>
            {#if quest.desc_kr}<div class="card-desc">{quest.desc_kr.slice(0, 80)}{quest.desc_kr.length > 80 ? '...' : ''}</div>{/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .codex-page {
    padding: 1rem;
    height: 100%;
    overflow-y: auto;
    background: var(--cds-background, #161616);
    color: var(--cds-text-primary, #f4f4f4);
  }
  .codex-toolbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }
  .codex-search {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 0.375rem 0.75rem;
    flex: 1;
    max-width: 400px;
  }
  .codex-search input {
    flex: 1;
    background: none;
    border: none;
    color: var(--cds-text-primary, #f4f4f4);
    font-size: 0.875rem;
    outline: none;
  }
  .clear-btn {
    background: none;
    border: none;
    color: var(--cds-text-secondary, #c6c6c6);
    cursor: pointer;
    padding: 0.125rem 0.375rem;
    font-size: 0.75rem;
  }
  .codex-tabs, .codex-subtabs {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }
  .tab, .subtab {
    padding: 0.375rem 0.75rem;
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    color: var(--cds-text-primary, #f4f4f4);
    font-size: 0.8125rem;
    cursor: pointer;
  }
  .tab.active, .subtab.active {
    background: var(--cds-layer-selected-01, #393939);
    border-color: var(--cds-link-primary, #78a9ff);
    color: var(--cds-link-primary, #78a9ff);
  }
  .codex-count {
    font-size: 0.8125rem;
    color: var(--cds-text-secondary, #c6c6c6);
    margin-bottom: 0.5rem;
  }
  .skeleton-grid, .codex-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.75rem;
  }
  .codex-card {
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 0.75rem;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-primary, #f4f4f4);
    width: 100%;
  }
  .codex-card:hover { border-color: var(--cds-link-primary, #78a9ff); }
  .card-body { display: flex; flex-direction: column; gap: 0.25rem; }
  .card-name { font-weight: 600; font-size: 0.875rem; }
  .card-translated { font-size: 0.8125rem; color: var(--cds-text-secondary, #c6c6c6); }
  .card-desc { font-size: 0.75rem; color: var(--cds-text-helper, #8d8d8d); margin-top: 0.25rem; }
  .card-meta { display: flex; gap: 0.25rem; flex-wrap: wrap; }
  .badge {
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    background: var(--cds-interactive, #4589ff);
    color: white;
  }
  .badge.sub { background: var(--cds-support-info, #4589ff); opacity: 0.8; }
  .badge.small { font-size: 0.6875rem; padding: 0.0625rem 0.375rem; }
  .codex-detail {
    background: var(--cds-layer-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #393939);
    border-radius: 4px;
    padding: 1.5rem;
  }
  .back-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    background: none;
    border: none;
    color: var(--cds-link-primary, #78a9ff);
    cursor: pointer;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }
  .codex-detail h3 { margin: 0 0 0.5rem; }
  .translated { color: var(--cds-text-secondary, #c6c6c6); margin: 0 0 0.5rem; }
  .desc { color: var(--cds-text-primary, #f4f4f4); margin: 0 0 1rem; white-space: pre-wrap; }
  .meta { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .strkey { font-family: monospace; font-size: 0.75rem; color: var(--cds-text-helper, #8d8d8d); }
  .card-images {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.5rem;
  }
  .card-images .card-img {
    width: 100%;
    height: auto;
    max-height: 120px;
    object-fit: cover;
    border-radius: 2px;
  }
  .detail-images {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.5rem;
  }
  .detail-images .card-img {
    width: 100%;
    height: auto;
    max-height: 200px;
    object-fit: cover;
    border-radius: 2px;
  }
</style>
