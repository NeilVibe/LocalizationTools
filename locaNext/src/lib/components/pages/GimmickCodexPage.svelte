<script>
  /**
   * GimmickCodexPage.svelte - Gimmick Codex encyclopedia page
   *
   * Browse, search, and inspect game gimmicks with card grid,
   * client-side filtering, and detail panel. Shows seal_desc when present.
   *
   * Phase 102: New codex page (bulk load, no pagination)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { GameWireless, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  // State
  let allGimmicks = $state([]);
  let loading = $state(true);
  let searchQuery = $state('');
  let selectedGimmick = $state(null);
  let detailLoading = $state(false);
  let apiError = $state(null);

  // Derived: client-side filtered gimmicks by search
  let filteredGimmicks = $derived.by(() => {
    return allGimmicks.filter(item => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      const searchable = `${item.name_kr || ''} ${item.name_translated || ''} ${item.strkey || ''} ${item.desc_kr || ''} ${item.seal_desc || ''}`.toLowerCase();
      return searchable.includes(q);
    });
  });

  async function fetchAll() {
    loading = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/gimmicks`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      allGimmicks = data.items || [];
      logger.info('Gimmick Codex loaded', { count: allGimmicks.length });
    } catch (err) {
      logger.error('Failed to load gimmicks', { error: err.message });
      apiError = 'Gimmick Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loading = false;
    }
  }

  async function fetchDetail(strkey) {
    detailLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/gimmicks/${strkey}`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedGimmick = await response.json();
    } catch (err) {
      logger.error('Failed to load gimmick detail', { error: err.message });
    } finally {
      detailLoading = false;
    }
  }

  onMount(() => { fetchAll(); });
</script>

<div class="codex-page">
  <PageHeader title="Gimmick Codex" icon={GameWireless} subtitle="{allGimmicks.length} gimmicks loaded" />

  <div class="codex-toolbar">
    <div class="codex-search">
      <input type="text" placeholder="Search gimmicks..." bind:value={searchQuery} />
      {#if searchQuery}
        <button class="clear-btn" onclick={() => { searchQuery = ''; }}>Clear</button>
      {/if}
    </div>
  </div>

  {#if apiError}
    <ErrorState message={apiError} />
  {:else if selectedGimmick}
    <div class="codex-detail">
      <button class="back-btn" onclick={() => { selectedGimmick = null; }}>
        <ArrowLeft size={16} /> Back to list
      </button>
      {#if detailLoading}
        <InlineLoading description="Loading gimmick detail..." />
      {:else}
        <h3>{selectedGimmick.name_kr || selectedGimmick.strkey}</h3>
        {#if selectedGimmick.image_urls?.length}
          <div class="detail-images">
            {#each selectedGimmick.image_urls as url (url)}
              <img src={url} alt={selectedGimmick.name_kr || selectedGimmick.strkey} class="card-img" />
            {/each}
          </div>
        {/if}
        {#if selectedGimmick.name_translated}<p class="translated">{selectedGimmick.name_translated}</p>{/if}
        {#if selectedGimmick.desc_kr}<p class="desc">{selectedGimmick.desc_kr}</p>{/if}
        {#if selectedGimmick.seal_desc}
          <div class="seal-section">
            <span class="seal-label">Seal Description:</span>
            <p class="seal-desc">{selectedGimmick.seal_desc}</p>
          </div>
        {/if}
        <div class="meta">
          {#if selectedGimmick.source_file}
            <div class="meta-item">
              <span class="meta-label">Source:</span>
              <span class="meta-value">{selectedGimmick.source_file}</span>
            </div>
          {/if}
          <span class="strkey">{selectedGimmick.strkey}</span>
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
    <div class="codex-count">{filteredGimmicks.length} gimmicks</div>
    <div class="codex-grid">
      {#each filteredGimmicks as gimmick (gimmick.strkey)}
        <button class="codex-card" onclick={() => fetchDetail(gimmick.strkey)}>
          {#if gimmick.image_urls?.length}
            <div class="card-images">
              {#each gimmick.image_urls as url (url)}
                <img src={url} alt={gimmick.name_kr || gimmick.strkey} class="card-img" />
              {/each}
            </div>
          {/if}
          <div class="card-body">
            <div class="card-name">{gimmick.name_kr || gimmick.strkey}</div>
            {#if gimmick.name_translated}<div class="card-translated">{gimmick.name_translated}</div>{/if}
            {#if gimmick.desc_kr}<div class="card-desc">{gimmick.desc_kr.slice(0, 80)}{gimmick.desc_kr.length > 80 ? '...' : ''}</div>{/if}
            {#if gimmick.seal_desc}<div class="card-seal">{gimmick.seal_desc.slice(0, 60)}{gimmick.seal_desc.length > 60 ? '...' : ''}</div>{/if}
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
  .card-seal { font-size: 0.6875rem; color: var(--cds-support-info, #4589ff); margin-top: 0.125rem; font-style: italic; }
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
  .seal-section { margin-bottom: 1rem; }
  .seal-label { font-size: 0.8125rem; color: var(--cds-text-secondary, #c6c6c6); font-weight: 600; }
  .seal-desc { color: var(--cds-support-info, #4589ff); margin: 0.25rem 0 0; white-space: pre-wrap; font-style: italic; }
  .meta { display: flex; flex-direction: column; gap: 0.5rem; }
  .meta-item { display: flex; gap: 0.5rem; font-size: 0.8125rem; }
  .meta-label { color: var(--cds-text-secondary, #c6c6c6); }
  .meta-value { color: var(--cds-text-primary, #f4f4f4); font-family: monospace; }
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
