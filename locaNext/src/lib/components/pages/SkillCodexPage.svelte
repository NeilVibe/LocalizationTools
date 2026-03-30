<script>
  /**
   * SkillCodexPage.svelte - Skill Codex encyclopedia page
   *
   * Browse, search, and inspect game skills with card grid,
   * client-side filtering, and detail panel.
   *
   * Phase 102: New codex page (bulk load, no pagination)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Flash, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  // State
  let allSkills = $state([]);
  let loading = $state(true);
  let searchQuery = $state('');
  let selectedSkill = $state(null);
  let detailLoading = $state(false);
  let apiError = $state(null);

  // Derived: client-side filtered skills by search
  let filteredSkills = $derived.by(() => {
    return allSkills.filter(item => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      const searchable = `${item.name_kr || ''} ${item.name_translated || ''} ${item.strkey || ''} ${item.desc_kr || ''}`.toLowerCase();
      return searchable.includes(q);
    });
  });

  async function fetchAll() {
    loading = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/skills`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      allSkills = data.items || [];
      logger.info('Skill Codex loaded', { count: allSkills.length });
    } catch (err) {
      logger.error('Failed to load skills', { error: err.message });
      apiError = 'Skill Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loading = false;
    }
  }

  async function fetchDetail(strkey) {
    detailLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/skills/${strkey}`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedSkill = await response.json();
    } catch (err) {
      logger.error('Failed to load skill detail', { error: err.message });
    } finally {
      detailLoading = false;
    }
  }

  onMount(() => { fetchAll(); });
</script>

<div class="codex-page">
  <PageHeader title="Skill Codex" icon={Flash} subtitle="{allSkills.length} skills loaded" />

  <div class="codex-toolbar">
    <div class="codex-search">
      <input type="text" placeholder="Search skills..." bind:value={searchQuery} />
      {#if searchQuery}
        <button class="clear-btn" onclick={() => { searchQuery = ''; }}>Clear</button>
      {/if}
    </div>
  </div>

  {#if apiError}
    <ErrorState message={apiError} />
  {:else if selectedSkill}
    <div class="codex-detail">
      <button class="back-btn" onclick={() => { selectedSkill = null; }}>
        <ArrowLeft size={16} /> Back to list
      </button>
      {#if detailLoading}
        <InlineLoading description="Loading skill detail..." />
      {:else}
        <h3>{selectedSkill.name_kr || selectedSkill.strkey}</h3>
        {#if selectedSkill.image_urls?.length}
          <div class="detail-images">
            {#each selectedSkill.image_urls as url (url)}
              <img src={url} alt={selectedSkill.name_kr || selectedSkill.strkey} class="card-img" />
            {/each}
          </div>
        {/if}
        {#if selectedSkill.name_translated}<p class="translated">{selectedSkill.name_translated}</p>{/if}
        {#if selectedSkill.desc_kr}<p class="desc">{selectedSkill.desc_kr}</p>{/if}
        <div class="meta">
          {#if selectedSkill.learn_knowledge_key}
            <div class="meta-item">
              <span class="meta-label">Learn Knowledge:</span>
              <span class="meta-value">{selectedSkill.learn_knowledge_key}</span>
            </div>
          {/if}
          {#if selectedSkill.source_file}
            <div class="meta-item">
              <span class="meta-label">Source:</span>
              <span class="meta-value">{selectedSkill.source_file}</span>
            </div>
          {/if}
          <span class="strkey">{selectedSkill.strkey}</span>
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
    <div class="codex-count">{filteredSkills.length} skills</div>
    <div class="codex-grid">
      {#each filteredSkills as skill (skill.strkey)}
        <button class="codex-card" onclick={() => fetchDetail(skill.strkey)}>
          {#if skill.image_urls?.length}
            <div class="card-images">
              {#each skill.image_urls as url (url)}
                <img src={url} alt={skill.name_kr || skill.strkey} class="card-img" />
              {/each}
            </div>
          {/if}
          <div class="card-body">
            <div class="card-name">{skill.name_kr || skill.strkey}</div>
            {#if skill.name_translated}<div class="card-translated">{skill.name_translated}</div>{/if}
            {#if skill.desc_kr}<div class="card-desc">{skill.desc_kr.slice(0, 80)}{skill.desc_kr.length > 80 ? '...' : ''}</div>{/if}
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
