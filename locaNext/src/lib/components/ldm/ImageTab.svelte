<script>
  /**
   * ImageTab.svelte - Image context display for MapData integration
   *
   * Shows thumbnail + metadata when image context exists for selected row,
   * graceful empty state otherwise. Fetches from MapData API on row change.
   *
   * Phase 5: Visual Polish and Integration (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Image } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  const API_BASE = getApiBase();

  // Props
  let { selectedRow = null } = $props();

  // State
  let imageContext = $state(null);
  let loading = $state(false);
  let error = $state(null);

  // Fetch image context when selected row changes
  $effect(() => {
    const stringId = selectedRow?.string_id;
    if (!stringId) {
      imageContext = null;
      error = null;
      return;
    }

    loading = true;
    error = null;

    fetch(`${API_BASE}/api/ldm/mapdata/image/${encodeURIComponent(stringId)}`, {
      headers: getAuthHeaders()
    })
      .then(async (response) => {
        if (response.ok) {
          imageContext = await response.json();
        } else if (response.status === 404) {
          imageContext = null;
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      })
      .catch((err) => {
        logger.error('Failed to fetch image context', { error: err.message });
        error = err.message;
        imageContext = null;
      })
      .finally(() => {
        loading = false;
      });
  });
</script>

<div class="image-tab">
  {#if loading}
    <div class="image-tab-loading" data-testid="image-tab-loading">
      <InlineLoading description="Loading image context..." />
    </div>
  {:else if !selectedRow}
    <div class="image-tab-empty" data-testid="image-tab-empty">
      <Image size={32} />
      <span class="empty-title">No Row Selected</span>
      <span class="empty-desc">Select a row in the grid to view image context</span>
    </div>
  {:else if imageContext && imageContext.has_image}
    <div class="image-context" data-testid="image-tab-thumbnail">
      <div class="thumbnail-wrapper">
        <img
          src={imageContext.thumbnail_url}
          alt={imageContext.texture_name}
          class="thumbnail"
          onerror={(e) => { e.target.style.display = 'none'; }}
        />
      </div>
      <div class="image-meta">
        <span class="texture-name">{imageContext.texture_name}</span>
        <span class="dds-path">{imageContext.dds_path}</span>
      </div>
    </div>
  {:else if error}
    <div class="image-tab-empty" data-testid="image-tab-empty">
      <Image size={32} />
      <span class="empty-title">Error Loading Image</span>
      <span class="empty-desc">{error}</span>
    </div>
  {:else}
    <div class="image-tab-empty" data-testid="image-tab-empty">
      <Image size={32} />
      <span class="empty-title">No Image Context</span>
      <span class="empty-desc">No image data available for this segment</span>
    </div>
  {/if}
</div>

<style>
  .image-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .image-tab-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
  }

  .image-tab-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 3rem 1rem;
    color: var(--cds-text-03);
    text-align: center;
  }

  .empty-title {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-02);
  }

  .empty-desc {
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .image-context {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .thumbnail-wrapper {
    border-radius: 4px;
    overflow: hidden;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
  }

  .thumbnail {
    width: 100%;
    display: block;
    object-fit: contain;
    max-height: 240px;
  }

  .image-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .texture-name {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .dds-path {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    word-break: break-all;
  }
</style>
