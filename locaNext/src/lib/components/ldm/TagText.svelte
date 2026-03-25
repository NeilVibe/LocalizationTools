<script>
  /**
   * TagText Component
   *
   * Renders inline tag pills for 5 tag types (braced, param, escape,
   * staticinfo, desc) and delegates plain text to ColorText.
   *
   * Follows the same pattern as ColorText.svelte:
   *   - Fast path: skip detection for plain text
   *   - Reactive: uses $derived for automatic re-detection on text change
   *   - Composable: wraps ColorText for color tag support in plain segments
   */

  import { detectTags, hasTags } from '$lib/utils/tagDetector.js';
  import ColorText from './ColorText.svelte';

  let { text = '' } = $props();

  // Fast path: skip detection for plain text
  let segments = $derived(hasTags(text) ? detectTags(text) : null);

  /**
   * Apply formatGridText ONLY to plain text segments.
   * CRITICAL: Do NOT convert \n to newline here -- \n is a tag pill.
   * Only convert &lt;br/&gt; to actual newlines.
   */
  function formatPlainText(t) {
    if (!t) return '';
    return t.replace(/&lt;br\/&gt;/g, '\n');
  }
</script>

{#if segments}
  <span class="tag-text">
    {#each segments as seg, i (i)}
      {#if seg.tag}
        {#if seg.tag.type === 'combinedcolor'}
          <span
            class="tag-pill tag-combinedcolor"
            title={seg.tag.raw}
            style="background: {seg.tag.cssColor}22; color: {seg.tag.cssColor}; border: 1px solid {seg.tag.cssColor}44;"
          >
            {seg.tag.label}
          </span>
        {:else}
          <span class="tag-pill tag-{seg.tag.color}" title={seg.tag.raw}>
            {seg.tag.label}
          </span>
        {/if}
        {#if seg.tag.inner}
          <ColorText text={formatPlainText(seg.tag.inner)} />
        {/if}
      {:else}
        <ColorText text={formatPlainText(seg.text)} />
      {/if}
    {/each}
  </span>
{:else}
  <ColorText text={formatPlainText(text)} />
{/if}

<style>
  .tag-text {
    display: inline;
  }

  .tag-pill {
    display: inline;
    padding: 0 3px;
    border-radius: 2px;
    font-size: 0.8em;
    font-family: 'Consolas', 'Monaco', monospace;
    line-height: 1.2;
    vertical-align: baseline;
    white-space: nowrap;
    cursor: default;
    user-select: none;
    border: 1px solid transparent;
  }

  .tag-combinedcolor {
    font-weight: 500;
  }

  .tag-blue    { background: #1e3a5f; color: #7ec8f0; border-color: #2d5a8f; }
  .tag-purple  { background: #3d1f5c; color: #c4a0e8; border-color: #5d3f7c; }
  .tag-grey    { background: #3a3a3a; color: #b0b0b0; border-color: #555555; }
  .tag-green   { background: #1a4a2e; color: #7ed4a0; border-color: #2a6a4e; }
  .tag-orange  { background: #5c3a1a; color: #e8b070; border-color: #7c5a3a; }
</style>
